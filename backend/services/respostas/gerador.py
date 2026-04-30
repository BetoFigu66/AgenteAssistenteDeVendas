"""
Gerador de respostas - híbrido (templates + LLM para personalização).

Fluxo:
1. Escolhe template baseado em intenção + estado da negociação
2. Preenche com contexto (nome, empresa, etc.)
3. Opcionalmente personaliza via LLM para tom mais natural
"""
import logging
from dataclasses import dataclass, field
from typing import Optional

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
            template_nome: Nome identificador do template para auditoria
                          (ex: "SAUDACAO_NOVO_CONTATO"). Se None, tenta inferir.
        
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


def _nome_template(template_str: str) -> Optional[str]:
    """Tenta inferir o nome de um template pelo seu conteúdo (reverse lookup)."""
    for nome in dir(T):
        if nome.isupper() and getattr(T, nome) is template_str:
            return nome
    return None
