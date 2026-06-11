"""
Implementação de LLMProvider para Groq.
https://console.groq.com
"""

import json
import logging
from typing import Optional

from groq import AsyncGroq

from .base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class GroqProvider(LLMProvider):
    """Provedor LLM usando a API Groq (rápido e com tier gratuito)."""

    def __init__(
        self,
        api_key: str,
        modelo: str = "llama-3.1-8b-instant",
        temperatura_padrao: float = 0.3,
    ):
        if not api_key:
            raise ValueError("Groq API key não configurada (LLM_API_KEY)")

        self._client = AsyncGroq(api_key=api_key)
        self._modelo = modelo
        self._temperatura_padrao = temperatura_padrao

    @property
    def nome(self) -> str:
        return "groq"

    async def completar(
        self,
        prompt_sistema: str,
        prompt_usuario: str,
        temperatura: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Envia prompt e retorna resposta em texto livre."""
        temp = temperatura if temperatura is not None else self._temperatura_padrao

        logger.debug(f"[Groq] completar() modelo={self._modelo} temp={temp}")

        resposta = await self._client.chat.completions.create(
            model=self._modelo,
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": prompt_usuario},
            ],
            temperature=temp,
            max_tokens=max_tokens,
        )

        return LLMResponse(
            conteudo=resposta.choices[0].message.content or "",
            modelo=resposta.model,
            tokens_input=resposta.usage.prompt_tokens if resposta.usage else None,
            tokens_output=resposta.usage.completion_tokens if resposta.usage else None,
        )

    async def completar_json(
        self,
        prompt_sistema: str,
        prompt_usuario: str,
        temperatura: Optional[float] = None,
    ) -> dict:
        """Envia prompt e exige resposta em JSON."""
        temp = temperatura if temperatura is not None else self._temperatura_padrao

        logger.debug(f"[Groq] completar_json() modelo={self._modelo}")

        # Groq suporta response_format JSON
        resposta = await self._client.chat.completions.create(
            model=self._modelo,
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": prompt_usuario},
            ],
            temperature=temp,
            response_format={"type": "json_object"},
        )

        conteudo = resposta.choices[0].message.content or "{}"

        try:
            return json.loads(conteudo)
        except json.JSONDecodeError as e:
            logger.error(f"[Groq] JSON inválido retornado: {conteudo[:200]}")
            raise ValueError(f"Resposta da LLM não é JSON válido: {e}") from e
