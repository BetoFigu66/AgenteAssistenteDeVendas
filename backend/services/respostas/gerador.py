"""
Gerador de respostas - híbrido (catálogo estruturado + LLM para personalização).

Fluxo:
1. Resolve mensagem pelo ID estável (catalogo.py)
2. Aplica transformers e preenche placeholders
3. Opcionalmente personaliza via LLM para tom mais natural
"""

import logging
from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence, Tuple, Union

from services.llm import LLMProvider

from .catalogo import MensagemId, renderizar_mensagem

logger = logging.getLogger(__name__)

ParteMensagem = Tuple[Union[MensagemId, int], Optional[dict]]


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
    # --- Fallback REQ-003.7/REQ-004.9 (Fase 6, REQ-005) ---
    fallback_req003: bool = False
    resultado_fallback: Optional[str] = None
    justificativa_curta: Optional[str] = None


_PROMPT_SISTEMA_PERSONALIZACAO = \
"""Você é um assistente de vendas via WhatsApp com IA da Inforrel (catracas e relógios de ponto).

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


_PROMPT_SISTEMA_RAG_BASE = \
"""Você é o assistente de vendas via WhatsApp da Inforrel (catracas, relógios de ponto e controle de acesso).

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
    "- Você pode sugerir uma opção de produto quando os trechos deixarem claro que ela faz sentido, sempre "
    'com linguagem cautelosa (ex: "uma opção que pode fazer sentido é...") e oferecendo confirmação com um vendedor.'
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
        mensagem_id: Union[MensagemId, int],
        contexto: Optional[dict] = None,
        personalizar: bool = False,
        mensagem_cliente: Optional[str] = None,
    ) -> RespostaGerada:
        """
        Gera uma resposta a partir de um ID do catálogo.

        Args:
            mensagem_id: ID estável da mensagem (MensagemId).
            contexto: Dict com variáveis para transformers e placeholders.
            personalizar: Se True, passa pela LLM para suavizar o tom.
            mensagem_cliente: Mensagem original do cliente (para contexto à LLM).

        Returns:
            RespostaGerada com texto e metadados.
        """
        resposta_base, codigo = renderizar_mensagem(mensagem_id, contexto)

        if not personalizar or not self._usar_llm:
            return RespostaGerada(texto=resposta_base, template_usado=codigo)

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
                template_usado=codigo,
                personalizado_via_llm=True,
                llm_tokens_input=resultado.tokens_input,
                llm_tokens_output=resultado.tokens_output,
            )
        except Exception as e:
            logger.warning(f"[Gerador] Falha ao personalizar via LLM, usando template: {e}")
            return RespostaGerada(texto=resposta_base, template_usado=codigo)

    async def gerar_composta(
        self,
        partes: Sequence[ParteMensagem],
        separador: str = "\n\n",
        personalizar: bool = False,
        mensagem_cliente: Optional[str] = None,
    ) -> RespostaGerada:
        """
        Compõe várias mensagens do catálogo numa única resposta.

        template_usado registra os códigos unidos por '+' (ex: SAUDACAO_NOVO_CONTATO+PEDIR_TIPO_PRODUTO).
        """
        textos: list[str] = []
        codigos: list[str] = []
        for mensagem_id, contexto in partes:
            texto, codigo = renderizar_mensagem(mensagem_id, contexto)
            textos.append(texto)
            codigos.append(codigo)

        resposta_base = separador.join(textos)
        codigo_composto = "+".join(codigos)

        if not personalizar or not self._usar_llm:
            return RespostaGerada(texto=resposta_base, template_usado=codigo_composto)

        prompt_usuario = f"Resposta padrão base: {resposta_base}"
        if mensagem_cliente:
            prompt_usuario = f"Mensagem do cliente: {mensagem_cliente}\n\n{prompt_usuario}"

        try:
            resultado = await self._llm.completar(
                prompt_sistema=_PROMPT_SISTEMA_PERSONALIZACAO,
                prompt_usuario=prompt_usuario,
                temperatura=0.5,
                max_tokens=400,
            )
            texto_final = resultado.conteudo.strip() or resposta_base
            return RespostaGerada(
                texto=texto_final,
                template_usado=codigo_composto,
                personalizado_via_llm=True,
                llm_tokens_input=resultado.tokens_input,
                llm_tokens_output=resultado.tokens_output,
            )
        except Exception as e:
            logger.warning(f"[Gerador] Falha ao personalizar composta via LLM: {e}")
            return RespostaGerada(texto=resposta_base, template_usado=codigo_composto)

    async def gerar_com_rag(
        self,
        pergunta_cliente: str,
        trechos: List[Any],
        permitir_sugestao_produto: bool = False,
        template_fallback: Union[MensagemId, int] = MensagemId.PRODUTO_SEM_CONTEXTO,
    ) -> RespostaGerada:
        """
        Gera resposta usando trechos recuperados da RAG como unico contexto factual.

        Args:
            pergunta_cliente: Mensagem original do cliente.
            trechos: Lista de `DocumentoRecuperado` (ou objetos com `titulo`, `conteudo`, `score`, `metadados`).
                Quando vazia, retorna o template de fallback.
            permitir_sugestao_produto: Se True, o prompt libera sugestao cautelosa de modelo; se False,
            pede apenas explicacao + coleta.
            template_fallback: ID do catálogo usado quando `trechos` e vazia ou LLM indisponivel.

        Returns:
            `RespostaGerada` com metadata de RAG preenchida.
        """
        texto_fallback, codigo_fallback = renderizar_mensagem(template_fallback)
        trechos_meta = [_trecho_para_metadata(t) for t in (trechos or [])]
        score_max = max((t["score"] for t in trechos_meta), default=None)

        if not trechos or not self._usar_llm:
            if not trechos:
                logger.info("[Gerador] RAG sem trechos; usando fallback %s", codigo_fallback)
            else:
                logger.info("[Gerador] RAG sem LLM disponivel; usando fallback %s", codigo_fallback)
            return RespostaGerada(
                texto=texto_fallback,
                template_usado=codigo_fallback,
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
                    texto=texto_fallback,
                    template_usado=codigo_fallback,
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
                texto=texto_fallback,
                template_usado=codigo_fallback,
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
