"""
Factory para instanciar o EmbeddingProvider configurado.
Permite trocar de provider alterando apenas EMBEDDING_PROVIDER no .env.
"""
from functools import lru_cache

from config import settings

from .base import EmbeddingProvider
from .openai_provider import OpenAIEmbeddingProvider


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    """
    Retorna a instancia singleton do EmbeddingProvider configurado.

    Providers suportados (via EMBEDDING_PROVIDER):
        - openai (padrao, modelo text-embedding-3-small)
        - ollama (TODO, embeddings locais)

    Raises:
        ValueError: Se o provider configurado nao for suportado.
    """
    provider = (settings.EMBEDDING_PROVIDER or "openai").lower()

    if provider == "openai":
        return OpenAIEmbeddingProvider(
            api_key=settings.EMBEDDING_API_KEY or "",
            modelo=settings.EMBEDDING_MODEL,
        )

    if provider == "ollama":
        raise NotImplementedError(
            "OllamaEmbeddingProvider ainda nao implementado"
        )

    raise ValueError(
        f"EMBEDDING_PROVIDER '{provider}' nao suportado. "
        f"Opcoes: openai, ollama"
    )
