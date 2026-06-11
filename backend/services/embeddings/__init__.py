"""Modulo de integracao com provedores de embeddings vetoriais."""

from .base import EmbeddingProvider, EmbeddingResponse
from .factory import get_embedding_provider

__all__ = [
    "EmbeddingProvider",
    "EmbeddingResponse",
    "get_embedding_provider",
]
