"""
Interface base para provedores de LLM.
Permite trocar de LLM (Groq, OpenAI, Gemini, Ollama) sem alterar código cliente.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMResponse:
    """Resposta padronizada de uma LLM."""

    conteudo: str
    modelo: str
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    extra: dict = field(default_factory=dict)


class LLMProvider(ABC):
    """
    Interface abstrata para provedores de LLM.

    Implementações concretas: GroqProvider, OpenAIProvider, etc.
    """

    @abstractmethod
    async def completar(
        self,
        prompt_sistema: str,
        prompt_usuario: str,
        temperatura: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Envia um prompt e retorna a completion.

        Args:
            prompt_sistema: Instruções/persona para a LLM
            prompt_usuario: Mensagem/pergunta do usuário
            temperatura: Controle de aleatoriedade (0.0 - 1.0)
            max_tokens: Limite de tokens na resposta

        Returns:
            LLMResponse com conteúdo e metadados.
        """
        ...

    @abstractmethod
    async def completar_json(
        self,
        prompt_sistema: str,
        prompt_usuario: str,
        temperatura: Optional[float] = None,
    ) -> dict:
        """
        Envia um prompt e exige que a resposta seja um JSON válido.
        Útil para classificação estruturada e extração de entidades.

        Returns:
            Dicionário parseado da resposta.
        """
        ...

    @property
    @abstractmethod
    def nome(self) -> str:
        """Identificador do provedor (ex: 'groq', 'openai')."""
        ...
