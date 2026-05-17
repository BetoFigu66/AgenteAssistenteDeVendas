"""
Gerador de respostas - híbrido (templates + LLM para personalização).

Fluxo:
1. Escolhe template baseado em intenção + estado da negociação
2. Preenche com contexto (nome, empresa, etc.)
3. Opcionalmente personaliza via LLM para tom mais natural
"""
import logging
from dataclasses import dataclass, field
from typing import Any, List, Optional

from services.llm import LLMProvider

from . import templates as T

logger = logging.getLogger(__name__)


@dataclass
class RespostaGerada:
    """Resposta gerada + metadados para auditoria/debug."""
    texto: str
    template_usado: Optional[str] = None
    personalizado_via_llm: bool = False
    llm_tokens_input: Optional[int] = None
    llm_tokens_output: Optional[int] = None
    # --- RAG ---
    rag_utilizada: bool = False
    trechos_rag: List[dict] = field(default_factory=list)
    rag_score_maximo: Optional[float] = None


_PROMPT_SISTEMA_PERSONALIZACAO = """Você é um assistente de vendas via WhatsApp com IA da Inforrel (catracas e relógios de ponto).

Regras OBRIGATÓRIAS:
- Responda em português brasileiro, tom cordial e profissional
- Respostas CURTAS (máx 3 linhas), adequadas para WhatsApp
- NUNCA prometa prazo de entrega
- NUNCA negocie desconto
- Para compatibilidade com sistemas de terceiros, oriente validar com o fornecedor do software
- Se não tiver certeza, ofereça escalar para atendente humano
- Não invente informações sobre produtos/preços que não foram fornecidas
- Use no máximo 1 emoji por resposta

Você vai receber uma resposta padrão como base e deve personalizá-la mantendo o sentido."""


_PROMPT_SISTEMA_RAG_BASE = """Você é o assistente de vendas via WhatsApp da Inforrel (catracas, relógios de ponto e controle de acesso).

Regras OBRIGATÓRIAS:
- Responda em português brasileiro, tom cordial e profissional.
- Resposta CURTA (máx 3 linhas), adequada para WhatsApp.
- Use SOMENTE as informações presentes nos TRECHOS DO CATÁLOGO abaixo.
- Se a informação necessária não estiver nos trechos, diga que vai encaminhar para validação com um atendente humano.
- NUNCA invente preço, prazo de entrega, compatibilidade com sistemas de terceiros ou disponibilidade.
- Para compatibilidade com sistemas de terceiros, oriente validar tecnicamente antes de fechar.
- Nunca prometa prazo de entrega.
- Use no máximo 1 emoji por resposta."""

_REGRA_SUGESTAO_ON = (
    "- Você pode sugerir uma opção de produto quando os trechos deixarem claro que ela faz sentido, "
    "sempre com linguagem cautelosa (ex: \"uma opção que pode fazer sentido é...\") e oferecendo confirmação com um vendedor."
)
_REGRA_SUGESTAO_OFF = (
    "- NÃO sugira um modelo específico como recomendação. Apenas explique as opções mencionadas nos trechos"
    " e colete informações para que um vendedor humano confirme a melhor configuração."
)


class GeradorRespostas:
    """Gera respostas para o cliente com base na intenção e contexto."""
    
    def __init__(self, llm: Optional[LLMProvider] = None, usar_llm: bool = True):
        self._llm = llm
        self._usar_llm = usar_llm and llm is not None
    
    async def gerar(
        self,
        template: str,
        contexto: Optional[dict] = None,
        personalizar: bool = False,
        mensagem_cliente: Optional[str] = None,
        template_nome: Optional[str] = None,
    ) -> RespostaGerada:
        """
        Gera uma resposta a partir de um template.
        
        Args:
            template: String de template (veja templates.py)
            contexto: Dict com variáveis para preencher o template
            personalizar: Se True, passa pela LLM para suavizar o tom
            mensagem_cliente: Mensagem original do cliente (para contexto à LLM)
            template_nome: Nome identificador do template para auditoria (ex: "SAUDACAO_NOVO_CONTATO"). Se None, tenta inferir.
        
        Returns:
            RespostaGerada com texto e metadados.
        """
        contexto = contexto or {}
        resposta_base = T.formatar(template, **contexto)
        nome = template_nome or _nome_template(template)
        
        if not personalizar or not self._usar_llm:
            return RespostaGerada(texto=resposta_base, template_usado=nome)
        
        prompt_usuario = f"Resposta padrão base: {resposta_base}"
        if mensagem_cliente:
            prompt_usuario = f"Mensagem do cliente: {mensagem_cliente}\n\n{prompt_usuario}"
        
        try:
            resultado = await self._llm.completar(
                prompt_sistema=_PROMPT_SISTEMA_PERSONALIZACAO,
                prompt_usuario=prompt_usuario,
                temperatura=0.5,
                max_tokens=300,
            )
            texto_final = resultado.conteudo.strip() or resposta_base
            return RespostaGerada(
                texto=texto_final,
                template_usado=nome,
                personalizado_via_llm=True,
                llm_tokens_input=resultado.tokens_input,
                llm_tokens_output=resultado.tokens_output,
            )
        except Exception as e:
            logger.warning(f"[Gerador] Falha ao personalizar via LLM, usando template: {e}")
            return RespostaGerada(texto=resposta_base, template_usado=nome)

    async def gerar_com_rag(
        self,
        pergunta_cliente: str,
        trechos: List[Any],
        permitir_sugestao_produto: bool = False,
        template_fallback: str = T.PRODUTO_SEM_CONTEXTO,
        template_fallback_nome: str = "PRODUTO_SEM_CONTEXTO",
    ) -> RespostaGerada:
        """
        Gera resposta usando trechos recuperados da RAG como unico contexto factual.

        Args:
            pergunta_cliente: Mensagem original do cliente.
            trechos: Lista de `DocumentoRecuperado` (ou objetos com `titulo`, `conteudo`, `score`, `metadados`). 
                Quando vazia, retorna o template de fallback.
            permitir_sugestao_produto: Se True, o prompt libera sugestao cautelosa de modelo; se False, pede apenas explicacao + coleta.
            template_fallback: Template usado quando `trechos` e vazia ou quando a LLM nao esta disponivel.
            template_fallback_nome: Nome do template de fallback para auditoria.

        Returns:
            `RespostaGerada` com metadata de RAG preenchida.
        """
        trechos_meta = [_trecho_para_metadata(t) for t in (trechos or [])]
        score_max = max((t["score"] for t in trechos_meta), default=None)

        # Sem trechos ou sem LLM: cai no template de fallback seguro.
        if not trechos or not self._usar_llm:
            if not trechos:
                logger.info("[Gerador] RAG sem trechos; usando fallback %s", template_fallback_nome)
            else:
                logger.info("[Gerador] RAG sem LLM disponivel; usando fallback %s", template_fallback_nome)
            return RespostaGerada(
                texto=template_fallback,
                template_usado=template_fallback_nome,
                rag_utilizada=bool(trechos),
                trechos_rag=trechos_meta,
                rag_score_maximo=score_max,
            )

        prompt_sistema = _montar_prompt_sistema_rag(permitir_sugestao_produto)
        prompt_usuario = _montar_prompt_usuario_rag(pergunta_cliente, trechos)

        try:
            resultado = await self._llm.completar(
                prompt_sistema=prompt_sistema,
                prompt_usuario=prompt_usuario,
                temperatura=0.2,
                max_tokens=350,
            )
            texto_final = (resultado.conteudo or "").strip()
            if not texto_final:
                logger.warning("[Gerador] LLM retornou vazio na RAG; usando fallback")
                return RespostaGerada(
                    texto=template_fallback,
                    template_usado=template_fallback_nome,
                    rag_utilizada=True,
                    trechos_rag=trechos_meta,
                    rag_score_maximo=score_max,
                )
            return RespostaGerada(
                texto=texto_final,
                template_usado="RAG_PRODUTO",
                personalizado_via_llm=True,
                llm_tokens_input=resultado.tokens_input,
                llm_tokens_output=resultado.tokens_output,
                rag_utilizada=True,
                trechos_rag=trechos_meta,
                rag_score_maximo=score_max,
            )
        except Exception as e:
            logger.warning(f"[Gerador] Falha ao gerar resposta com RAG: {e}")
            return RespostaGerada(
                texto=template_fallback,
                template_usado=template_fallback_nome,
                rag_utilizada=True,
                trechos_rag=trechos_meta,
                rag_score_maximo=score_max,
            )


def _montar_prompt_sistema_rag(permitir_sugestao: bool) -> str:
    regra_sugestao = _REGRA_SUGESTAO_ON if permitir_sugestao else _REGRA_SUGESTAO_OFF
    return f"{_PROMPT_SISTEMA_RAG_BASE}\n{regra_sugestao}"


def _montar_prompt_usuario_rag(pergunta: str, trechos: List[Any]) -> str:
    linhas = ["TRECHOS DO CATÁLOGO:"]
    for i, t in enumerate(trechos, start=1):
        titulo = getattr(t, "titulo", "") or ""
        conteudo = getattr(t, "conteudo", "") or ""
        meta = getattr(t, "metadados", None) or {}
        url = meta.get("url") if isinstance(meta, dict) else None
        cabecalho = f"[{i}] {titulo}".strip()
        if url:
            cabecalho += f" — {url}"
        linhas.append(cabecalho)
        linhas.append(conteudo.strip())
        linhas.append("")
    linhas.append("PERGUNTA DO CLIENTE:")
    linhas.append(pergunta.strip())
    return "\n".join(linhas).strip()


def _trecho_para_metadata(trecho: Any) -> dict:
    """Extrai um dict resumido de um DocumentoRecuperado para auditoria."""
    meta = getattr(trecho, "metadados", None) or {}
    url = meta.get("url") if isinstance(meta, dict) else None
    return {
        "id": getattr(trecho, "id", None),
        "id_externo": getattr(trecho, "id_externo", None),
        "tipo": getattr(trecho, "tipo", None),
        "titulo": getattr(trecho, "titulo", None),
        "score": float(getattr(trecho, "score", 0.0) or 0.0),
        "distancia": float(getattr(trecho, "distancia", 0.0) or 0.0),
        "url": url,
    }


def _nome_template(template_str: str) -> Optional[str]:
    """Tenta inferir o nome de um template pelo seu conteúdo (reverse lookup)."""
    for nome in dir(T):
        if nome.isupper() and getattr(T, nome) is template_str:
            return nome
    return None
