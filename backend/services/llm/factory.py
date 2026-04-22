"""
Factory para instanciar o LLMProvider configurado.
Permite trocar de provider alterando apenas a variável LLM_PROVIDER no .env.
"""
from functools import lru_cache

from config import settings

from .base import LLMProvider
from .groq_provider import GroqProvider


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    """
    Retorna a instância singleton do LLMProvider configurado.
    
    Providers suportados (configurar via LLM_PROVIDER):
        - groq (padrão)
        - openai (TODO)
        - gemini (TODO)
        - ollama (TODO)
    
    Raises:
        ValueError: Se o provider configurado não for suportado.
    """
    provider = (settings.LLM_PROVIDER or "groq").lower()
    
    if provider == "groq":
        return GroqProvider(
            api_key=settings.LLM_API_KEY or "",
            modelo=settings.LLM_MODEL,
            temperatura_padrao=settings.LLM_TEMPERATURE,
        )
    
    # Placeholders para futuras implementações
    if provider == "openai":
        raise NotImplementedError("OpenAIProvider ainda não implementado")
    if provider == "gemini":
        raise NotImplementedError("GeminiProvider ainda não implementado")
    if provider == "ollama":
        raise NotImplementedError("OllamaProvider ainda não implementado")
    
    raise ValueError(
        f"LLM_PROVIDER '{provider}' não suportado. "
        f"Opções: groq, openai, gemini, ollama"
    )
