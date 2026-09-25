"""Baixa os anexos que a Twilio aponta em `MediaUrl{i}` durante a captura de payloads.

Por que isto existe: o payload traz só o link, e o arquivo fica no armazenamento da Twilio
enquanto a conta existir. Com a conta trial perto de expirar, o link morre junto; baixar na
hora é a única forma de guardar exemplos reais de foto, áudio, PDF e figurinha.

Mesma regra da captura de payload: é instrumentação, nunca pode custar a mensagem do
cliente. Por isso roda em segundo plano (a Twilio corta o webhook em 15 s) e toda falha é
registrada no índice em vez de subir.
"""

import asyncio
import json
import logging
import mimetypes
from pathlib import Path
from typing import Optional

import httpx
from config import settings
from utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)

# Referências fortes às tarefas em andamento: sem isso o asyncio pode coletar a tarefa
# antes de ela terminar (ver a documentação de `asyncio.create_task`).
_tarefas: set[asyncio.Task] = set()

_EXTENSOES_FIXAS = {
    # `mimetypes` não conhece ou devolve extensão estranha para estes.
    "audio/ogg": ".ogg",
    "image/webp": ".webp",
    "image/jpeg": ".jpg",
    "text/vcard": ".vcf",
    "text/x-vcard": ".vcf",
}


def _credenciais() -> Optional[tuple[str, str]]:
    """API Key primeiro (é o que o `.env` desta conta tem), Auth Token como alternativa."""
    if settings.TWILIO_API_KEY_SID and settings.TWILIO_API_KEY_SECRET:
        return (settings.TWILIO_API_KEY_SID, settings.TWILIO_API_KEY_SECRET)
    if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
        return (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    return None


def _extensao(content_type: str) -> str:
    tipo = (content_type or "").split(";")[0].strip().lower()
    return _EXTENSOES_FIXAS.get(tipo) or mimetypes.guess_extension(tipo) or ".bin"


def _registrar_no_indice(pasta: Path, registro: dict) -> None:
    with (pasta / "indice.jsonl").open("a", encoding="utf-8") as arquivo:
        arquivo.write(json.dumps(registro, ensure_ascii=False) + "\n")


async def baixar_midias(
    formulario: dict,
    pasta: Optional[Path] = None,
    transport: Optional[httpx.AsyncBaseTransport] = None,
) -> list[dict]:
    """Baixa cada `MediaUrl{i}` do formulário e devolve um registro por anexo.

    `transport` existe para os testes injetarem um `httpx.MockTransport`.
    """
    try:
        quantidade = int(formulario.get("NumMedia") or 0)
    except (TypeError, ValueError):
        quantidade = 0
    if quantidade <= 0:
        return []

    pasta = pasta or Path(settings.TWILIO_CAPTURA_MIDIAS_PASTA)
    pasta.mkdir(parents=True, exist_ok=True)
    message_sid = formulario.get("MessageSid") or "sem_sid"
    registros = []

    async with httpx.AsyncClient(
        auth=_credenciais(), follow_redirects=True, timeout=30.0, transport=transport
    ) as cliente:
        for i in range(quantidade):
            url = formulario.get(f"MediaUrl{i}")
            content_type = formulario.get(f"MediaContentType{i}") or ""
            registro = {
                "baixado_em": utc_now().isoformat(),
                "message_sid": message_sid,
                "indice": i,
                "url": url,
                "content_type": content_type,
            }
            try:
                if not url:
                    raise ValueError(f"MediaUrl{i} ausente com NumMedia={quantidade}")
                resposta = await cliente.get(url)
                if resposta.status_code in (401, 403) and cliente.auth is not None:
                    # Na conta trial a API de mídia responde 20003 ("not available on a
                    # Trial account") para chamada autenticada. A URL do `MediaUrl{i}` é
                    # servida sem autenticação quando a conta não exige, então vale tentar.
                    registro["status_http_com_auth"] = resposta.status_code
                    resposta = await cliente.get(url, auth=None)
                registro["status_http"] = resposta.status_code
                resposta.raise_for_status()
                content_type = content_type or resposta.headers.get("content-type", "")
                destino = pasta / f"{message_sid}_{i}{_extensao(content_type)}"
                destino.write_bytes(resposta.content)
                registro.update({"arquivo": destino.name, "bytes": len(resposta.content)})
            except Exception as e:
                registro["erro"] = f"{type(e).__name__}: {e}"
                logger.warning("[CapturaMidia] falha no anexo %s de %s: %s", i, message_sid, e)
            _registrar_no_indice(pasta, registro)
            registros.append(registro)
    return registros


def agendar_download(formulario: dict) -> None:
    """Dispara o download em segundo plano, sem segurar a resposta do webhook."""

    async def _rodar():
        try:
            await baixar_midias(formulario)
        except Exception:
            logger.exception("[CapturaMidia] falha geral (ignorada de propósito)")

    tarefa = asyncio.create_task(_rodar())
    _tarefas.add(tarefa)
    tarefa.add_done_callback(_tarefas.discard)
