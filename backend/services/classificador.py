"""
Classificador de intenções de mensagens (híbrido: regras + LLM).

Estratégia:
1. Tenta classificar via regras/regex (rápido, determinístico)
2. Se regras não tiverem confiança, usa LLM

Também extrai entidades: CNPJ, CPF, data de nascimento, nome, quantidades, tipos de produto,
software de controle de ponto, tipo de leitor mencionado e faixa de funcionários (MVP Continuidade).
"""

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from services.cpf.validacao import extrair_cpfs, formatar_cpf, normalizar_cpf, parse_data_nascimento
from services.llm import LLMProvider

logger = logging.getLogger(__name__)


class NivelConfianca(str, Enum):
    """Nível qualitativo de confiança do classificador."""

    ALTA = "alta"
    MEDIA = "media"
    BAIXA = "baixa"


class Intencao(str, Enum):
    """Intenções reconhecidas pelo classificador."""

    SAUDACAO = "saudacao"
    FORNECER_CNPJ = "fornecer_cnpj"
    FORNECER_CPF = "fornecer_cpf"
    FORNECER_NOME = "fornecer_nome"
    FORNECER_DATA_NASCIMENTO = "fornecer_data_nascimento"
    CONFIRMAR = "confirmar"
    NEGAR = "negar"
    PEDIR_ORCAMENTO = "pedir_orcamento"
    PEDIR_CATALOGO = "pedir_catalogo"
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
    cpfs: List[str] = field(default_factory=list)
    datas_nascimento: List[str] = field(default_factory=list)  # ISO yyyy-mm-dd
    nomes: List[str] = field(default_factory=list)
    tipos_produto: List[str] = field(default_factory=list)  # ex: "catraca", "relogio_ponto"
    quantidades: List[int] = field(default_factory=list)
    emails: List[str] = field(default_factory=list)
    # MVP Continuidade (Fase D — extração passiva em Esclarecendo):
    software_ponto: Optional[str] = None  # nome normalizado, ex.: "Domínio" (CAMPO-software-ponto)
    tipo_leitor_mencionado: Optional[str] = None  # ex.: "biometria"/"facial"/"cartao"/"cartografico"/"eletronico"
    faixa_funcionarios: Optional[int] = None  # nº de funcionários mencionado (CAMPO-faixa-funcionarios)


@dataclass
class ResultadoClassificacao:
    """Resultado da classificação de uma mensagem.

    `intencoes` substitui o antigo campo único `intencao` (motor de roteamento
    Intenção×Fase→Ações) — nunca vazia (mínimo `[DESCONHECIDO]`), coleta TODAS as
    intenções que bateram na mensagem, não só a de maior prioridade.
    """

    intencoes: List[Intencao]
    confianca: float  # 0.0 a 1.0
    confianca_nivel: NivelConfianca
    entidades: EntidadesExtraidas
    origem: str  # "regra" ou "llm"
    raw_llm: Optional[dict] = None
    llm_latencia_ms: Optional[int] = None
    llm_tokens_input: Optional[int] = None
    llm_tokens_output: Optional[int] = None

    @property
    def intencao_principal(self) -> Intencao:
        """A intenção de maior prioridade — só para auditoria/exibição simples
        (ex.: coluna `ProcessamentoMensagem.intencao`). O roteamento de verdade usa
        `intencoes` (todas), nunca este atalho."""
        return self.intencoes[0] if self.intencoes else Intencao.DESCONHECIDO


def _calcular_nivel_confianca(
    confianca: float,
    alta_min: float = 0.70,
    baixa_max: float = 0.40,
) -> NivelConfianca:
    """
    Converte um score numérico em nível qualitativo.

    Defaults preservam o comportamento histórico (0.70/0.40) para chamadores que não
    passam limiares — `classificar()` recebe os valores efetivos de quem tiver acesso
    ao `ParametroService` (REQ-014, Fase 7); este módulo permanece sem dependência de
    banco.
    """
    if confianca >= alta_min:
        return NivelConfianca.ALTA
    if confianca >= baixa_max:
        return NivelConfianca.MEDIA
    return NivelConfianca.BAIXA


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
        # REQ-003.11 — checada antes de PERGUNTAR_PRODUTO: "catálogo de catracas" não pode
        # cair só na resposta genérica de dúvida sobre produto.
        Intencao.PEDIR_CATALOGO,
        re.compile(r"\bcat[aá]logo\b", re.IGNORECASE),
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

_REGEX_DATA_ISOLADA = re.compile(r"\b\d{1,2}[/\-.]\d{1,2}[/\-.]\d{4}\b")

# Palavras que não devem ser confundidas com nome próprio quando o regex capturar.
# Não aplicada em _limpar_nome (ver docstring) — mantida caso sirva para outra
# validação futura (ex.: rejeitar entidades antes de chegar ao regex de nome).
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
    "cpf",
    "nascimento",
}


def _extrair_nome_sem_gatilho(texto: str, cpfs: List[str], cnpjs: List[str]) -> Optional[str]:
    """
    Infere nome quando o cliente informa documento + data sem gatilho explícito.

    Ex.: "Jose Roberto 07198942806, 17/06/1966" → "Jose Roberto"
    """
    if not texto or (not cpfs and not cnpjs):
        return None

    restante = texto
    for cpf in cpfs:
        limpo = normalizar_cpf(cpf)
        restante = re.sub(re.escape(limpo), " ", restante)
        if len(limpo) == 11:
            restante = restante.replace(formatar_cpf(limpo), " ")

    for cnpj in cnpjs:
        limpo = re.sub(r"\D", "", cnpj)
        if len(limpo) == 14:
            restante = re.sub(re.escape(limpo), " ", restante)
            fmt = f"{limpo[:2]}.{limpo[2:5]}.{limpo[5:8]}/{limpo[8:12]}-{limpo[12:]}"
            restante = restante.replace(fmt, " ")

    restante = _REGEX_DATA_ISOLADA.sub(" ", restante)
    restante = re.sub(
        r"\b(cpf|cnpj|nascimento|data\s+de\s+nascimento|nasc\.?)\b",
        " ",
        restante,
        flags=re.IGNORECASE,
    )
    restante = re.sub(r"[,;]+", " ", restante)
    restante = re.sub(r"\s+", " ", restante).strip()

    if not restante:
        return None
    return _limpar_nome(restante)


def _limpar_nome(bruto: str) -> Optional[str]:
    """Normaliza e capitaliza um nome extraído pelo regex.

    Não filtra por `_STOPWORDS_NOME` aqui: nomes reais têm conectores como
    "da"/"de"/"do" (ex.: "João da Silva"), que colidem com a mesma lista
    usada para rejeitar falsos positivos tipo "a empresa Inforrel". Essa
    rejeição já é garantida pelo próprio `_REGEX_NOME` (exige 2+ letras por
    palavra capturada, então "a" isolado nunca entra na captura).
    """
    if not bruto:
        return None
    partes = [p.strip(".,;:!?") for p in bruto.split()]
    partes = [p for p in partes if p]
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

# D3 (MVP Continuidade): softwares de controle de ponto conhecidos — pré-preenche
# CAMPO-software-ponto quando o cliente já cita o nome espontaneamente em Esclarecendo.
_SOFTWARES_PONTO_CONHECIDOS = {
    "dominio": "Domínio",
    "domínio": "Domínio",
    "alterdata": "Alterdata",
    "totvs": "TOTVS",
    "senior sistemas": "Senior",
    "senior": "Senior",
    "sênior": "Senior",
    "secullum": "Secullum",
    "ahgora": "Ahgora",
    "rh bravo": "RH Bravo",
}

# D4 (MVP Continuidade): tecnologia de leitura mencionada espontaneamente (CAMPO-modelo).
# É um sinal cru para a Fase F resolver depois em uma linha real do catálogo (Modelo) —
# não grava direto em ItemAtendimento.produto_id (ver CampoDef.destino em catalogo_campos.py).
_TIPO_LEITOR_PALAVRAS = {
    "biometrico": "biometria",
    "biométrico": "biometria",
    "biometria": "biometria",
    "reconhecimento facial": "facial",
    "facial": "facial",
    "cartografico": "cartografico",
    "cartográfico": "cartografico",
    "eletronico": "eletronico",
    "eletrônico": "eletronico",
    "cartao": "cartao",
    "cartão": "cartao",
}

# D4: "80 funcionários" / "uns 50 colaboradores" — distinto de _REGEX_QUANTIDADE
# (que é sobre unidades de equipamento, não pessoas).
_REGEX_FUNCIONARIOS = re.compile(
    r"\b(\d{1,5})\s*(?:funcion[áa]rios?|colaboradores?|pessoas?|empregados?)\b",
    re.IGNORECASE,
)


def extrair_entidades(texto: str) -> EntidadesExtraidas:
    """Extrai CNPJs, CPFs, datas de nascimento, emails, quantidades e tipos de produto via regex."""
    if not texto:
        return EntidadesExtraidas()

    cnpjs = _REGEX_CNPJ.findall(texto)
    cpfs = extrair_cpfs(texto)
    emails = _REGEX_EMAIL.findall(texto)

    data_nasc = parse_data_nascimento(texto)
    datas_nascimento = [data_nasc.isoformat()] if data_nasc else []

    # Quantidades (pega apenas números razoáveis: 1-9999)
    quantidades = [int(m.group(1)) for m in _REGEX_QUANTIDADE.finditer(texto) if 1 <= int(m.group(1)) <= 9999]

    texto_lower = texto.lower()
    tipos_produto = []
    for palavra, tipo in _TIPOS_PRODUTO_PALAVRAS.items():
        if palavra in texto_lower and tipo not in tipos_produto:
            tipos_produto.append(tipo)

    # D3: software de controle de ponto mencionado espontaneamente.
    software_ponto = next(
        (nome for palavra, nome in _SOFTWARES_PONTO_CONHECIDOS.items() if palavra in texto_lower),
        None,
    )

    # D4: tecnologia de leitura mencionada espontaneamente (sinal cru para a Fase F resolver).
    tipo_leitor_mencionado = next(
        (tipo for palavra, tipo in _TIPO_LEITOR_PALAVRAS.items() if palavra in texto_lower),
        None,
    )

    # D4: faixa de funcionários mencionada espontaneamente.
    _match_funcionarios = _REGEX_FUNCIONARIOS.search(texto)
    faixa_funcionarios = int(_match_funcionarios.group(1)) if _match_funcionarios else None

    # Extração de nomes via gatilhos ("meu nome é X", "me chamo X", ...)
    nomes: List[str] = []
    for match in _REGEX_NOME.finditer(texto):
        nome = _limpar_nome(match.group(1))
        if nome and nome not in nomes:
            nomes.append(nome)

    # PF/PJ: nome antes ou depois do documento, sem gatilho explícito
    if not nomes and (cpfs or cnpjs):
        nome_livre = _extrair_nome_sem_gatilho(texto, cpfs, cnpjs)
        if nome_livre and nome_livre not in nomes:
            nomes.append(nome_livre)

    return EntidadesExtraidas(
        cnpjs=cnpjs,
        cpfs=cpfs,
        datas_nascimento=datas_nascimento,
        nomes=nomes,
        emails=emails,
        quantidades=quantidades,
        tipos_produto=tipos_produto,
        software_ponto=software_ponto,
        tipo_leitor_mencionado=tipo_leitor_mencionado,
        faixa_funcionarios=faixa_funcionarios,
    )


def classificar_por_regras(texto: str) -> list[tuple[Intencao, float]]:
    """
    Classifica a intenção usando regras/regex.

    Coleta TODAS as regras que baterem (não só a primeira) — motor de roteamento
    Intenção×Fase→Ações precisa saber de toda intenção presente na mensagem, não só a
    de maior prioridade (ex.: "Bom dia, quero orçamento" não pode perder a intenção de
    orçamento só porque a saudação bateu primeiro).

    Returns:
        Lista de (Intencao, confianca). Se nada bateu, retorna [(DESCONHECIDO, 0.0)].
    """
    if not texto or not texto.strip():
        return [(Intencao.DESCONHECIDO, 0.0)]

    matches: list[tuple[Intencao, float]] = []

    # Documento fiscal: CNPJ tem prioridade sobre CPF
    if _REGEX_CNPJ.search(texto):
        matches.append((Intencao.FORNECER_CNPJ, 0.9))
    else:
        cpfs = extrair_cpfs(texto)
        if cpfs:
            matches.append((Intencao.FORNECER_CPF, 0.9))

    for intencao, padrao in _REGRAS_INTENCAO:
        if padrao.search(texto):
            matches.append((intencao, 0.75))

    return matches or [(Intencao.DESCONHECIDO, 0.0)]


def _finalizar_intencoes(
    matches: list[tuple[Intencao, float]],
    entidades: EntidadesExtraidas,
) -> List[Intencao]:
    """Ordena os matches por confiança (desc), deduplica, e acrescenta as intenções
    derivadas de entidades (nome, data de nascimento) — sempre visíveis para o motor de
    Ações, independente do caminho (regra ou LLM) que classificou a intenção principal.
    """
    ordenados = sorted(matches, key=lambda par: par[1], reverse=True)
    intencoes: List[Intencao] = []
    for intencao, _ in ordenados:
        if intencao not in intencoes:
            intencoes.append(intencao)

    if entidades.nomes and Intencao.FORNECER_NOME not in intencoes:
        intencoes.append(Intencao.FORNECER_NOME)
    if entidades.datas_nascimento and Intencao.FORNECER_DATA_NASCIMENTO not in intencoes:
        intencoes.append(Intencao.FORNECER_DATA_NASCIMENTO)

    if len(intencoes) > 1 and Intencao.DESCONHECIDO in intencoes:
        intencoes.remove(Intencao.DESCONHECIDO)

    return intencoes or [Intencao.DESCONHECIDO]


# =============================================================================
# Classificação por LLM
# =============================================================================

_PROMPT_SISTEMA_CLASSIFICADOR = "Você é um classificador de mensagens para um assistente de vendas via WhatsApp com" \
"""IA da empresa Inforrel, que vende catracas e relógios de ponto.

Classifique a mensagem do cliente em UMA das intenções:
- saudacao: cumprimentos
- fornecer_cnpj: cliente informou CNPJ
- fornecer_cpf: cliente informou CPF
- fornecer_nome: cliente informou seu nome
- confirmar: resposta afirmativa a uma pergunta
- negar: resposta negativa a uma pergunta
- pedir_orcamento: solicita orçamento/cotação
- pedir_catalogo: pede o catálogo de produtos (ex: "tem catálogo?", "me manda o catálogo")
- perguntar_preco: pergunta quanto custa
- perguntar_produto: pergunta sobre produtos/modelos
- perguntar_prazo: pergunta sobre prazo de entrega
- aprovar_orcamento: aprova orçamento já enviado
- reprovar_orcamento: recusa orçamento
- reclamar: reclamação/problema com produto
- escalar_humano: pede para falar com atendente
- fora_contexto: assunto não relacionado
- desconhecido: intenção não clara

Extraia também entidades mencionadas: cnpjs, cpfs, datas_nascimento (yyyy-mm-dd), nomes (pessoas),
tipos_produto (catraca, relogio_ponto), quantidades (números), emails.

Responda APENAS com JSON neste formato:
{
  "intencao": "<uma das opções>",
  "confianca": <0.0 a 1.0>,
  "entidades": {
    "cnpjs": [],
    "cpfs": [],
    "datas_nascimento": [],
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
        cpfs=[str(c) for c in ent.get("cpfs") or []],
        datas_nascimento=[str(d) for d in ent.get("datas_nascimento") or []],
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
    limiares_confianca: Optional[dict] = None,
) -> ResultadoClassificacao:
    """
    Classifica a mensagem de forma híbrida: primeiro regras, depois LLM.

    Args:
        texto: Texto da mensagem
        llm: Provedor LLM (opcional, se None só usa regras)
        contexto: Contexto adicional para a LLM
        limiares_confianca: dict opcional `{"alta_min": float, "baixa_max": float}`
            (ex.: `ParametroService.limiares_classificador()`) — quando `None`, usa os
            defaults históricos de `_calcular_nivel_confianca` (REQ-014, Fase 7).

    Returns:
        ResultadoClassificacao com intenção, confiança, entidades e origem.
    """
    kwargs_nivel = (
        {"alta_min": limiares_confianca["alta_min"], "baixa_max": limiares_confianca["baixa_max"]}
        if limiares_confianca
        else {}
    )
    entidades_regra = extrair_entidades(texto)
    matches_regra = classificar_por_regras(texto)
    confianca_regra = max(c for _, c in matches_regra)

    # Se regras têm alta confiança, usa direto
    if confianca_regra >= LIMITE_CONFIANCA_REGRAS:
        intencoes = _finalizar_intencoes(matches_regra, entidades_regra)
        logger.debug(f"[Classificador] Usando regra: {[i.value for i in intencoes]} (confiança={confianca_regra})")
        return ResultadoClassificacao(
            intencoes=intencoes,
            confianca=confianca_regra,
            confianca_nivel=_calcular_nivel_confianca(confianca_regra, **kwargs_nivel),
            entidades=entidades_regra,
            origem="regra",
        )

    # Caso contrário, tenta LLM
    if llm is None:
        intencoes = _finalizar_intencoes(matches_regra, entidades_regra)
        return ResultadoClassificacao(
            intencoes=intencoes,
            confianca=confianca_regra,
            confianca_nivel=_calcular_nivel_confianca(confianca_regra, **kwargs_nivel),
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
        cpfs=list({*entidades_regra.cpfs, *entidades_llm.cpfs}),
        datas_nascimento=list({*entidades_regra.datas_nascimento, *entidades_llm.datas_nascimento}),
        nomes=nomes_combinados,
        tipos_produto=list({*entidades_regra.tipos_produto, *entidades_llm.tipos_produto}),
        quantidades=entidades_regra.quantidades or entidades_llm.quantidades,
        emails=list({*entidades_regra.emails, *entidades_llm.emails}),
        # A LLM ainda não é solicitada a extrair estas 3 (MVP Continuidade, Fase D) —
        # só a regra as popula por enquanto, então usar sempre a da regra.
        software_ponto=entidades_regra.software_ponto or entidades_llm.software_ponto,
        tipo_leitor_mencionado=entidades_regra.tipo_leitor_mencionado or entidades_llm.tipo_leitor_mencionado,
        faixa_funcionarios=(
            entidades_regra.faixa_funcionarios
            if entidades_regra.faixa_funcionarios is not None
            else entidades_llm.faixa_funcionarios
        ),
    )

    intencoes = _finalizar_intencoes([(intencao_llm, confianca_llm)], entidades_final)
    logger.debug(f"[Classificador] Usando LLM: {[i.value for i in intencoes]} (confiança={confianca_llm},"
        " latência={latencia_ms}ms)")

    return ResultadoClassificacao(
        intencoes=intencoes,
        confianca=confianca_llm,
        confianca_nivel=_calcular_nivel_confianca(confianca_llm, **kwargs_nivel),
        entidades=entidades_final,
        origem="llm",
        raw_llm=raw,
        llm_latencia_ms=latencia_ms,
    )
