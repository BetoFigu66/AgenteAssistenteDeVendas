"""
Interface base para provedores de embeddings.
Permite trocar de provider (OpenAI, Ollama local, etc.) sem alterar codigo cliente.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class EmbeddingResponse:
    """Resposta padronizada de uma chamada de embeddings."""
    embeddings: List[List[float]]
    modelo: str
    dimensoes: int
    tokens_input: Optional[int] = None
    extra: dict = field(default_factory=dict)


class EmbeddingProvider(ABC):
    """
    Interface abstrata para provedores de embeddings.

    Implementacoes concretas: OpenAIEmbeddingProvider, etc.

    Contrato:
        - `embed()` recebe um lote de textos e retorna um EmbeddingResponse com a
          lista de vetores na mesma ordem dos textos de entrada.
        - `embed_um()` e um atalho para embutir um unico texto.
        - `dimensoes` deve refletir a dimensao do modelo configurado
          (ex: 1536 para text-embedding-3-small).
    """

    @abstractmethod
    async def embed(self, textos: List[str]) -> EmbeddingResponse:
        """
        Gera embeddings para um lote de textos.

        Args:
            textos: Lista de strings a embutir (nao vazia).

        Returns:
            EmbeddingResponse com vetores na mesma ordem dos textos.
        """
        ...

    async def embed_um(self, texto: str) -> List[float]:
        """Atalho para embutir um unico texto."""
        resposta = await self.embed([texto])
        return resposta.embeddings[0]

    @property
    @abstractmethod
    def nome(self) -> str:
        """Identificador do provedor (ex: 'openai')."""
        ...

    @property
    @abstractmethod
    def modelo(self) -> str:
        """Nome do modelo de embeddings em uso."""
        ...

    @property
    @abstractmethod
    def dimensoes(self) -> int:
        """Dimensao do vetor gerado pelo modelo."""
        ...
