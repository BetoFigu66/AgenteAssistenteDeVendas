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
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit

import httpx
from config import settings
from utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)

# Referências fortes às tarefas em andamento: sem isso o asyncio pode coletar a tarefa
# antes de ela terminar (ver a documentação de `asyncio.create_task`).
_tarefas: set[asyncio.Task] = set()

# Tudo o que vem do formulário é dado de fora, e o webhook é público. O `MessageSid` vira
# nome de arquivo, então só passa no formato da Twilio (senão `../` escreveria fora da
# pasta). E a credencial só vai para a própria API da Twilio: seguir qualquer `MediaUrl`
# entregaria a API Key a quem forjasse o formulário, além de abrir a rede local (SSRF).
_SID_VALIDO = re.compile(r"^(MM|SM)[0-9a-f]{32}$")
_HOST_PERMITIDO = "api.twilio.com"
# O WhatsApp aceita até 10 anexos por mensagem; o teto de tamanho fica acima do maior
# anexo que o WhatsApp permite (100 MB para documento) só o bastante para não encher disco.
_MAX_MIDIAS = 10
_MAX_BYTES = 110 * 1024 * 1024

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
    extensao = _EXTENSOES_FIXAS.get(tipo) or mimetypes.guess_extension(tipo) or ".bin"
    return extensao if re.fullmatch(r"\.[a-z0-9]{1,8}", extensao) else ".bin"


def _url_da_twilio(url: str) -> bool:
    partes = urlsplit(url)
    return partes.scheme == "https" and partes.hostname == _HOST_PERMITIDO


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
    message_sid = formulario.get("MessageSid") or ""
    if not _SID_VALIDO.match(message_sid):
        logger.warning("[CapturaMidia] MessageSid fora do formato, download ignorado")
        return []
    quantidade = min(quantidade, _MAX_MIDIAS)

    pasta = (pasta or Path(settings.TWILIO_CAPTURA_MIDIAS_PASTA)).resolve()
    pasta.mkdir(parents=True, exist_ok=True)
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
                if not _url_da_twilio(url):
                    raise ValueError(f"MediaUrl{i} fora de https://{_HOST_PERMITIDO}")
                conteudo, status, status_com_auth = await _baixar(cliente, url)
                registro["status_http"] = status
                if status_com_auth is not None:
                    registro["status_http_com_auth"] = status_com_auth
                destino = (pasta / f"{message_sid}_{i}{_extensao(content_type)}").resolve()
                if not destino.is_relative_to(pasta):
                    raise ValueError("destino fora da pasta de mídias")
                destino.write_bytes(conteudo)
                registro.update({"arquivo": destino.name, "bytes": len(conteudo)})
            except Exception as e:
                if isinstance(e, _FalhaDownload):
                    registro["status_http"] = e.status
                    if e.status_com_auth is not None:
                        registro["status_http_com_auth"] = e.status_com_auth
                registro["erro"] = f"{type(e).__name__}: {e}"
                logger.warning("[CapturaMidia] falha no anexo %s de %s: %s", i, message_sid, e)
            _registrar_no_indice(pasta, registro)
            registros.append(registro)
    return registros


class _FalhaDownload(Exception):
    def __init__(self, motivo: str, status: Optional[int] = None, status_com_auth: Optional[int] = None):
        super().__init__(motivo)
        self.status = status
        self.status_com_auth = status_com_auth


async def _baixar(cliente: httpx.AsyncClient, url: str) -> tuple[bytes, int, Optional[int]]:
    """Baixa em stream com teto de tamanho. Devolve (conteúdo, status, status com auth).

    Na conta trial a API de mídia responde 20003 ("not available on a Trial account") para
    chamada autenticada; a URL do `MediaUrl{i}` é servida sem autenticação quando a conta
    não exige, então um 401/403 com credencial ganha uma segunda tentativa sem ela. O
    redirecionamento para o armazenamento (outro host) não leva a credencial: o httpx a
    remove quando a origem muda.
    """
    tentativas = [httpx.USE_CLIENT_DEFAULT, None] if cliente.auth is not None else [None]
    status_com_auth = None
    for auth in tentativas:
        async with cliente.stream("GET", url, auth=auth) as resposta:
            if resposta.status_code in (401, 403) and auth is not None:
                status_com_auth = resposta.status_code
                continue
            if resposta.status_code >= 400:
                raise _FalhaDownload(f"HTTP {resposta.status_code}", resposta.status_code, status_com_auth)
            partes, total = [], 0
            async for bloco in resposta.aiter_bytes():
                total += len(bloco)
                if total > _MAX_BYTES:
                    raise _FalhaDownload(f"anexo acima de {_MAX_BYTES} bytes", resposta.status_code, status_com_auth)
                partes.append(bloco)
            return b"".join(partes), resposta.status_code, status_com_auth
    raise _FalhaDownload("recusado com e sem credencial", status_com_auth, status_com_auth)


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
