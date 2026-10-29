"""
Implementação de LLMProvider para qualquer API compatível com a da OpenAI
(`/chat/completions`): OpenAI, Ollama, Cloudflare Workers AI, OpenRouter, Gemini (endpoint
de compatibilidade), Groq e outros. Muda só o endereço (`LLM_BASE_URL`), a chave e o modelo.

Dois cuidados que o provedor da Groq não precisava:

- **Modo JSON:** nem todo serviço aceita `response_format={"type": "json_object"}`. Se o
  pedido com ele for recusado, repete uma vez sem ele, e daí em diante não manda mais. A
  resposta é lida de forma tolerante (bloco ```json, texto em volta do objeto).
- **Tempo de espera:** o cliente da OpenAI espera até 10 minutos por padrão, e a resposta
  sai dentro do webhook do WhatsApp. Aqui o padrão é `LLM_TIMEOUT_SEGUNDOS`, com uma
  nova tentativa só.
"""

import json
import logging
import re
from typing import Optional

import httpx
from openai import AsyncOpenAI, BadRequestError

from .base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)

# Endereços conhecidos, para `LLM_PROVIDER` dispensar o `LLM_BASE_URL`. A Cloudflare não
# entra: o endereço dela leva o id da conta (`.../accounts/{id}/ai/v1`).
BASE_URLS_CONHECIDAS = {
    "openai": None,  # padrão do próprio cliente
    "ollama": "http://localhost:11434/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "groq_compativel": "https://api.groq.com/openai/v1",
}

# Serviços que não exigem chave (rodam na máquina).
SEM_CHAVE = {"ollama"}

_BLOCO_JSON = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extrair_json(conteudo: str) -> dict:
    """O objeto JSON da resposta, aceitando bloco ```json e texto em volta."""
    texto = (conteudo or "").strip()
    bloco = _BLOCO_JSON.search(texto)
    if bloco:
        texto = bloco.group(1).strip()
    try:
        valor = json.loads(texto)
    except json.JSONDecodeError:
        inicio, fim = texto.find("{"), texto.rfind("}")
        if inicio == -1 or fim <= inicio:
            raise ValueError(f"Resposta da LLM não é JSON válido: {conteudo[:200]!r}") from None
        try:
            valor = json.loads(texto[inicio : fim + 1])
        except json.JSONDecodeError as e:
            raise ValueError(f"Resposta da LLM não é JSON válido: {e}") from e
    if not isinstance(valor, dict):
        raise ValueError("Resposta da LLM é JSON, mas não é um objeto")
    return valor


class OpenAICompativelProvider(LLMProvider):
    """Provedor LLM para APIs compatíveis com a da OpenAI."""

    def __init__(
        self,
        *,
        nome: str,
        modelo: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperatura_padrao: float = 0.3,
        timeout_segundos: float = 30.0,
        modo_json: bool = True,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        if not api_key and nome not in SEM_CHAVE:
            raise ValueError(f"Chave do provedor '{nome}' não configurada (LLM_API_KEY)")
        if not modelo:
            raise ValueError("Modelo não configurado (LLM_MODEL)")
        self._nome = nome
        self._modelo = modelo
        self._temperatura_padrao = temperatura_padrao
        self._modo_json = modo_json
        self._client = AsyncOpenAI(
            # O cliente exige uma chave; serviço local aceita qualquer texto.
            api_key=api_key or "sem-chave",
            base_url=base_url,
            timeout=timeout_segundos,
            max_retries=1,
            http_client=http_client,
        )

    @property
    def nome(self) -> str:
        return self._nome

    def _mensagens(self, prompt_sistema: str, prompt_usuario: str) -> list:
        return [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": prompt_usuario},
        ]

    async def completar(
        self,
        prompt_sistema: str,
        prompt_usuario: str,
        temperatura: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        temp = temperatura if temperatura is not None else self._temperatura_padrao
        logger.debug(f"[{self._nome}] completar() modelo={self._modelo} temp={temp}")
        resposta = await self._client.chat.completions.create(
            model=self._modelo,
            messages=self._mensagens(prompt_sistema, prompt_usuario),
            temperature=temp,
            max_tokens=max_tokens,
        )
        return LLMResponse(
            conteudo=resposta.choices[0].message.content or "",
            modelo=resposta.model or self._modelo,
            tokens_input=resposta.usage.prompt_tokens if resposta.usage else None,
            tokens_output=resposta.usage.completion_tokens if resposta.usage else None,
        )

    async def completar_json(
        self,
        prompt_sistema: str,
        prompt_usuario: str,
        temperatura: Optional[float] = None,
    ) -> dict:
        temp = temperatura if temperatura is not None else self._temperatura_padrao
        argumentos = {
            "model": self._modelo,
            "messages": self._mensagens(prompt_sistema, prompt_usuario),
            "temperature": temp,
        }
        if self._modo_json:
            try:
                resposta = await self._client.chat.completions.create(
                    **argumentos, response_format={"type": "json_object"}
                )
                return extrair_json(resposta.choices[0].message.content or "{}")
            except BadRequestError as e:
                if "response_format" not in str(e) and "json" not in str(e).lower():
                    raise
                logger.warning(f"[{self._nome}] modo JSON recusado, seguindo sem ele: {e}")
                self._modo_json = False
        resposta = await self._client.chat.completions.create(**argumentos)
        return extrair_json(resposta.choices[0].message.content or "{}")
