"""
Classificador de intenções de mensagens (híbrido: regras + LLM).

Estratégia:
1. Tenta classificar via regras/regex (rápido, determinístico)
2. Se regras não tiverem confiança, usa LLM

Também extrai entidades: CNPJ, nome, quantidades, tipos de produto.
"""

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from services.llm import LLMProvider

logger = logging.getLogger(__name__)


class Intencao(str, Enum):
    """Intenções reconhecidas pelo classificador."""

    SAUDACAO = "saudacao"
    FORNECER_CNPJ = "fornecer_cnpj"
    FORNECER_NOME = "fornecer_nome"
    CONFIRMAR = "confirmar"
    NEGAR = "negar"
    PEDIR_ORCAMENTO = "pedir_orcamento"
    PERGUNTAR_PRECO = "perguntar_preco"
    PERGUNTAR_PRODUTO = "perguntar_produto"
    PERGUNTAR_PRAZO = "perguntar_prazo"
    APROVAR_ORCAMENTO = "aprovar_orcamento"
    REPROVAR_ORCAMENTO = "reprovar_orcamento"
    RECLAMAR = "reclamar"
    ESCALAR_HUMANO = "escalar_humano"
    FORA_CONTEXTO = "fora_contexto"
    DESCONHECIDO = "desconhecido"


@dataclass
class EntidadesExtraidas:
    """Entidades extraídas de uma mensagem."""

    cnpjs: List[str] = field(default_factory=list)
    nomes: List[str] = field(default_factory=list)
    tipos_produto: List[str] = field(default_factory=list)  # ex: "catraca", "relogio_ponto"
    quantidades: List[int] = field(default_factory=list)
    emails: List[str] = field(default_factory=list)


@dataclass
class ResultadoClassificacao:
    """Resultado da classificação de uma mensagem."""

    intencao: Intencao
    confianca: float  # 0.0 a 1.0
    entidades: EntidadesExtraidas
    origem: str  # "regra" ou "llm"
    raw_llm: Optional[dict] = None
    llm_latencia_ms: Optional[int] = None
    llm_tokens_input: Optional[int] = None
    llm_tokens_output: Optional[int] = None


# =============================================================================
# Classificação por Regras
# =============================================================================

_REGRAS_INTENCAO: list[tuple[Intencao, re.Pattern]] = [
    (
        Intencao.SAUDACAO,
        re.compile(
            r"\b(oi|ol[aá]|bom\s+dia|boa\s+tarde|boa\s+noite|e\s*a[ií]|hey|hi|hello|salve)\b",
            re.IGNORECASE,
        ),
    ),
    (
        Intencao.ESCALAR_HUMANO,
        re.compile(
            r"\b(atendente|humano|pessoa|vendedor(a)?|gerente|falar\s+com\s+algu[eé]m)\b",
            re.IGNORECASE,
        ),
    ),
    (
        Intencao.APROVAR_ORCAMENTO,
        re.compile(
            r"\b(aprovad[oa]|pode\s+fechar|fechad[oa]|pode\s+mandar|confirmo\s+o\s+or[çc]amento)\b",
            re.IGNORECASE,
        ),
    ),
    (
        Intencao.REPROVAR_ORCAMENTO,
        re.compile(
            r"\b(n[aã]o\s+vamos\s+fechar|desistimos|recusado|n[aã]o\s+aprovado)\b",
            re.IGNORECASE,
        ),
    ),
    (
        Intencao.RECLAMAR,
        re.compile(
            r"\b(reclama[çc][aã]o|problema|defeito|n[aã]o\s+funciona|quebrou|parou\s+de\s+funcionar)\b",
            re.IGNORECASE,
        ),
    ),
    (
        Intencao.PEDIR_ORCAMENTO,
        re.compile(
            r"\b(or[çc]amento|cota[çc][aã]o|quanto\s+sai|quanto\s+custa|pre[çc]o)\b",
            re.IGNORECASE,
        ),
    ),
    (
        Intencao.PERGUNTAR_PRAZO,
        re.compile(
            r"\b(prazo|entrega|quando\s+(chega|entrega|recebo)|em\s+quantos?\s+dias)\b",
            re.IGNORECASE,
        ),
    ),
    (
        Intencao.PERGUNTAR_PRODUTO,
        re.compile(
            r"\b(catraca|rel[oó]gio\s+de\s+ponto|biom[eé]trico|cart[aã]o|facial|modelo)\b",
            re.IGNORECASE,
        ),
    ),
    (
        Intencao.CONFIRMAR,
        re.compile(
            r"^\s*(sim|isso|correto|confirmo|ok|certo|isso\s+mesmo|exato|perfeito)\s*[.!]?\s*$",
            re.IGNORECASE,
        ),
    ),
    (
        Intencao.NEGAR,
        re.compile(
            r"^\s*(n[aã]o|nao|errado|incorreto)\s*[.!]?\s*$",
            re.IGNORECASE,
        ),
    ),
]


_REGEX_CNPJ = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")
_REGEX_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_REGEX_QUANTIDADE = re.compile(r"\b(\d{1,4})\s*(unidades?|un|pe[çc]as?|pcs)?\b", re.IGNORECASE)

# Captura um nome próprio após gatilhos como "meu nome é ...", "sou o/a ...", "me chamo ...".
# O grupo de nome aceita 1 a 4 palavras iniciadas por maiúscula (ou palavras
# simples em minúsculo — melhor ter falso-positivo aqui do que perder o nome).
_REGEX_NOME = re.compile(
    r"(?:meu\s+nome\s+[ée]|me\s+chamo|sou\s+(?:o|a)|aqui\s+[ée]\s+(?:o|a)|"
    r"pode\s+me\s+chamar\s+de|[ée]\s+o\s+|chamo[-\s]me)\s+"
    r"([A-Za-zÀ-ÿ]{2,}(?:\s+[A-Za-zÀ-ÿ]{2,}){0,3})",
    re.IGNORECASE,
)

# Palavras que não devem ser confundidas com nome próprio quando o regex capturar.
_STOPWORDS_NOME = {
    "e",
    "o",
    "a",
    "meu",
    "minha",
    "seu",
    "sua",
    "nome",
    "da",
    "de",
    "do",
    "empresa",
    "inforrel",
    "cnpj",
    "pessoa",
    "cliente",
}


def _limpar_nome(bruto: str) -> Optional[str]:
    """Normaliza e valida um nome extraído pelo regex."""
    if not bruto:
        return None
    partes = [p.strip(".,;:!?") for p in bruto.split()]
    partes = [p for p in partes if p and p.lower() not in _STOPWORDS_NOME]
    if not partes:
        return None
    # Capitaliza cada parte ("beto figueiredo" -> "Beto Figueiredo").
    return " ".join(p.capitalize() for p in partes)


_TIPOS_PRODUTO_PALAVRAS = {
    "catraca": "catraca",
    "catracas": "catraca",
    "relogio de ponto": "relogio_ponto",
    "relógio de ponto": "relogio_ponto",
    "relógios de ponto": "relogio_ponto",
    "ponto eletronico": "relogio_ponto",
    "ponto eletrônico": "relogio_ponto",
    "rep": "relogio_ponto",
}


def extrair_entidades(texto: str) -> EntidadesExtraidas:
    """Extrai CNPJs, emails, quantidades e tipos de produto via regex."""
    if not texto:
        return EntidadesExtraidas()

    cnpjs = _REGEX_CNPJ.findall(texto)
    emails = _REGEX_EMAIL.findall(texto)

    # Quantidades (pega apenas números razoáveis: 1-9999)
    quantidades = [int(m.group(1)) for m in _REGEX_QUANTIDADE.finditer(texto) if 1 <= int(m.group(1)) <= 9999]

    texto_lower = texto.lower()
    tipos_produto = []
    for palavra, tipo in _TIPOS_PRODUTO_PALAVRAS.items():
        if palavra in texto_lower and tipo not in tipos_produto:
            tipos_produto.append(tipo)

    # Extração de nomes via gatilhos ("meu nome é X", "me chamo X", ...)
    nomes: List[str] = []
    for match in _REGEX_NOME.finditer(texto):
        nome = _limpar_nome(match.group(1))
        if nome and nome not in nomes:
            nomes.append(nome)

    return EntidadesExtraidas(
        cnpjs=cnpjs,
        nomes=nomes,
        emails=emails,
        quantidades=quantidades,
        tipos_produto=tipos_produto,
    )


def classificar_por_regras(texto: str) -> tuple[Intencao, float]:
    """
    Classifica a intenção usando regras/regex.

    Returns:
        Tupla (Intencao, confianca). Se não achou, retorna (DESCONHECIDO, 0.0).
    """
    if not texto or not texto.strip():
        return Intencao.DESCONHECIDO, 0.0

    # Se a mensagem contém CNPJ, prioriza FORNECER_CNPJ
    if _REGEX_CNPJ.search(texto):
        return Intencao.FORNECER_CNPJ, 0.9

    for intencao, padrao in _REGRAS_INTENCAO:
        if padrao.search(texto):
            return intencao, 0.75

    return Intencao.DESCONHECIDO, 0.0


# =============================================================================
# Classificação por LLM
# =============================================================================

_PROMPT_SISTEMA_CLASSIFICADOR = "Você é um classificador de mensagens para um assistente de vendas via WhatsApp com" \
"""IA da empresa Inforrel, que vende catracas e relógios de ponto.

Classifique a mensagem do cliente em UMA das intenções:
- saudacao: cumprimentos
- fornecer_cnpj: cliente informou CNPJ
- fornecer_nome: cliente informou seu nome
- confirmar: resposta afirmativa a uma pergunta
- negar: resposta negativa a uma pergunta
- pedir_orcamento: solicita orçamento/cotação
- perguntar_preco: pergunta quanto custa
- perguntar_produto: pergunta sobre produtos/modelos
- perguntar_prazo: pergunta sobre prazo de entrega
- aprovar_orcamento: aprova orçamento já enviado
- reprovar_orcamento: recusa orçamento
- reclamar: reclamação/problema com produto
- escalar_humano: pede para falar com atendente
- fora_contexto: assunto não relacionado
- desconhecido: intenção não clara

Extraia também entidades mencionadas: cnpjs, nomes (pessoas), tipos_produto (catraca, relogio_ponto), 
quantidades (números), emails.

Responda APENAS com JSON neste formato:
{
  "intencao": "<uma das opções>",
  "confianca": <0.0 a 1.0>,
  "entidades": {
    "cnpjs": [],
    "nomes": [],
    "tipos_produto": [],
    "quantidades": [],
    "emails": []
  }
}"""


async def classificar_por_llm(
    texto: str,
    llm: LLMProvider,
    contexto: Optional[str] = None,
) -> tuple[Intencao, float, EntidadesExtraidas, dict, int]:
    """
    Classifica a mensagem usando LLM.

    Returns:
        Tupla (Intencao, confianca, EntidadesExtraidas, raw_json, latencia_ms).
    """
    prompt_usuario = f"Mensagem do cliente: {texto}"
    if contexto:
        prompt_usuario = f"Contexto anterior: {contexto}\n\n{prompt_usuario}"

    inicio = time.monotonic()
    try:
        resultado = await llm.completar_json(
            prompt_sistema=_PROMPT_SISTEMA_CLASSIFICADOR,
            prompt_usuario=prompt_usuario,
            temperatura=0.1,
        )
    except Exception as e:
        logger.error(f"[Classificador] Erro na LLM: {e}")
        latencia_ms = int((time.monotonic() - inicio) * 1000)
        return Intencao.DESCONHECIDO, 0.0, EntidadesExtraidas(), {}, latencia_ms

    latencia_ms = int((time.monotonic() - inicio) * 1000)

    # Parse
    try:
        intencao = Intencao(resultado.get("intencao", "desconhecido"))
    except ValueError:
        intencao = Intencao.DESCONHECIDO

    confianca = float(resultado.get("confianca", 0.0))

    ent = resultado.get("entidades") or {}
    entidades = EntidadesExtraidas(
        cnpjs=[str(c) for c in ent.get("cnpjs") or []],
        nomes=[str(n) for n in ent.get("nomes") or []],
        tipos_produto=[str(t) for t in ent.get("tipos_produto") or []],
        quantidades=[int(q) for q in ent.get("quantidades") or [] if str(q).isdigit()],
        emails=[str(e) for e in ent.get("emails") or []],
    )

    return intencao, confianca, entidades, resultado, latencia_ms


# =============================================================================
# Classificador Híbrido (ponto de entrada)
# =============================================================================

LIMITE_CONFIANCA_REGRAS = 0.7


async def classificar(
    texto: str,
    llm: Optional[LLMProvider] = None,
    contexto: Optional[str] = None,
) -> ResultadoClassificacao:
    """
    Classifica a mensagem de forma híbrida: primeiro regras, depois LLM.

    Args:
        texto: Texto da mensagem
        llm: Provedor LLM (opcional, se None só usa regras)
        contexto: Contexto adicional para a LLM

    Returns:
        ResultadoClassificacao com intenção, confiança, entidades e origem.
    """
    entidades_regra = extrair_entidades(texto)
    intencao_regra, confianca_regra = classificar_por_regras(texto)

    # Se regras têm alta confiança, usa direto
    if confianca_regra >= LIMITE_CONFIANCA_REGRAS:
        logger.debug(f"[Classificador] Usando regra: {intencao_regra.value} (confiança={confianca_regra})")
        return ResultadoClassificacao(
            intencao=intencao_regra,
            confianca=confianca_regra,
            entidades=entidades_regra,
            origem="regra",
        )

    # Caso contrário, tenta LLM
    if llm is None:
        return ResultadoClassificacao(
            intencao=intencao_regra,
            confianca=confianca_regra,
            entidades=entidades_regra,
            origem="regra",
        )

    intencao_llm, confianca_llm, entidades_llm, raw, latencia_ms = await classificar_por_llm(texto, llm, contexto)

    # Combina entidades de regras + LLM (regras são mais confiáveis para CNPJ/email;
    # para nomes, regra e LLM se complementam — mantém os dois).
    nomes_combinados: List[str] = []
    for n in [*entidades_regra.nomes, *entidades_llm.nomes]:
        if n and n not in nomes_combinados:
            nomes_combinados.append(n)
    entidades_final = EntidadesExtraidas(
        cnpjs=list({*entidades_regra.cnpjs, *entidades_llm.cnpjs}),
        nomes=nomes_combinados,
        tipos_produto=list({*entidades_regra.tipos_produto, *entidades_llm.tipos_produto}),
        quantidades=entidades_regra.quantidades or entidades_llm.quantidades,
        emails=list({*entidades_regra.emails, *entidades_llm.emails}),
    )

    logger.debug(f"[Classificador] Usando LLM: {intencao_llm.value} (confiança={confianca_llm}," 
        " latência={latencia_ms}ms)")

    return ResultadoClassificacao(
        intencao=intencao_llm,
        confianca=confianca_llm,
        entidades=entidades_final,
        origem="llm",
        raw_llm=raw,
        llm_latencia_ms=latencia_ms,
    )
