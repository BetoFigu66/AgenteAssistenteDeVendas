"""
Implementacao de EmbeddingProvider para OpenAI.
https://platform.openai.com/docs/guides/embeddings
"""

import logging
from typing import List

from openai import AsyncOpenAI

from .base import EmbeddingProvider, EmbeddingResponse

logger = logging.getLogger(__name__)


# Dimensoes padrao dos modelos OpenAI de embedding mais usados.
# Usado apenas como fallback quando a dimensao nao e inferida da primeira chamada.
_DIMENSOES_PADRAO = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Provedor de embeddings usando a API da OpenAI."""

    def __init__(
        self,
        api_key: str,
        modelo: str = "text-embedding-3-small",
        dimensoes: int | None = None,
    ):
        if not api_key:
            raise ValueError("OpenAI API key nao configurada (EMBEDDING_API_KEY)")

        self._client = AsyncOpenAI(api_key=api_key)
        self._modelo = modelo
        self._dimensoes = dimensoes or _DIMENSOES_PADRAO.get(modelo, 1536)

    @property
    def nome(self) -> str:
        return "openai"

    @property
    def modelo(self) -> str:
        return self._modelo

    @property
    def dimensoes(self) -> int:
        return self._dimensoes

    async def embed(self, textos: List[str]) -> EmbeddingResponse:
        if not textos:
            raise ValueError("Lista de textos nao pode ser vazia")

        # Checagem leve: OpenAI retorna erro 400 para inputs vazios.
        textos_sanitizados = [t if (t and t.strip()) else " " for t in textos]

        logger.debug(
            "[OpenAIEmbedding] embed() modelo=%s qtd=%d",
            self._modelo,
            len(textos_sanitizados),
        )

        resposta = await self._client.embeddings.create(
            model=self._modelo,
            input=textos_sanitizados,
        )

        # Ordena pelo indice para garantir a mesma ordem dos textos de entrada.
        dados_ordenados = sorted(resposta.data, key=lambda d: d.index)
        vetores = [list(d.embedding) for d in dados_ordenados]

        # Ajusta a dimensao observada, caso o modelo retorne algo diferente
        # do padrao conhecido (ex: modelo customizado).
        if vetores and len(vetores[0]) != self._dimensoes:
            logger.warning(
                "[OpenAIEmbedding] dimensao observada %d difere da esperada %d",
                len(vetores[0]),
                self._dimensoes,
            )
            self._dimensoes = len(vetores[0])

        tokens_input = None
        if getattr(resposta, "usage", None) is not None:
            tokens_input = resposta.usage.prompt_tokens

        return EmbeddingResponse(
            embeddings=vetores,
            modelo=resposta.model,
            dimensoes=self._dimensoes,
            tokens_input=tokens_input,
        )
