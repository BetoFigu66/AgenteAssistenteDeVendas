"""
Factory para instanciar o LLMProvider configurado.
Permite trocar de provider alterando apenas a variável LLM_PROVIDER no .env.
"""

from functools import lru_cache

from config import settings

from .base import LLMProvider
from .groq_provider import GroqProvider
from .openai_compativel_provider import BASE_URLS_CONHECIDAS, OpenAICompativelProvider

_EXIGEM_BASE_URL = ("cloudflare", "openai_compativel")


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    """
    Retorna a instância singleton do LLMProvider configurado.

    Providers suportados (configurar via LLM_PROVIDER):
        - groq (padrão, SDK da Groq)
        - openai, ollama, openrouter, gemini, groq_compativel: API compatível com a da
          OpenAI, com endereço já conhecido (`LLM_BASE_URL` opcional)
        - cloudflare, openai_compativel: API compatível com a da OpenAI, com
          `LLM_BASE_URL` obrigatório (na Cloudflare, o endereço leva o id da conta)

    Raises:
        ValueError: Se o provider não for suportado ou faltar configuração.
    """
    provider = (settings.LLM_PROVIDER or "groq").lower()

    if provider == "groq":
        return GroqProvider(
            api_key=settings.LLM_API_KEY or "",
            modelo=settings.LLM_MODEL,
            temperatura_padrao=settings.LLM_TEMPERATURE,
        )

    if provider in BASE_URLS_CONHECIDAS or provider in _EXIGEM_BASE_URL:
        base_url = settings.LLM_BASE_URL or BASE_URLS_CONHECIDAS.get(provider)
        if provider in _EXIGEM_BASE_URL and not base_url:
            raise ValueError(f"LLM_PROVIDER '{provider}' exige LLM_BASE_URL")
        return OpenAICompativelProvider(
            nome=provider,
            modelo=settings.LLM_MODEL,
            api_key=settings.LLM_API_KEY,
            base_url=base_url,
            temperatura_padrao=settings.LLM_TEMPERATURE,
            timeout_segundos=settings.LLM_TIMEOUT_SEGUNDOS,
            modo_json=settings.LLM_MODO_JSON,
        )

    suportados = ", ".join(["groq", *BASE_URLS_CONHECIDAS, *_EXIGEM_BASE_URL])
    raise ValueError(f"LLM_PROVIDER '{provider}' não suportado. Opções: {suportados}")
