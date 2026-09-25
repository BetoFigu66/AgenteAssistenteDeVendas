"""Download dos anexos da Twilio durante a captura de payloads (conta trial expirando).

Os formulários abaixo usam os nomes de campo da documentação da Twilio (`NumMedia`,
`MediaUrl{i}`, `MediaContentType{i}`); a colheita real vai confirmá-los.
"""

import asyncio
import json

import httpx
from services.canal.captura_midia import baixar_midias


def _rodar(formulario, pasta, handler):
    return asyncio.run(baixar_midias(formulario, pasta=pasta, transport=httpx.MockTransport(handler)))


def test_baixa_cada_anexo_com_extensao_do_content_type(tmp_path):
    def handler(request):
        return httpx.Response(200, content=b"conteudo-" + request.url.path.encode())

    formulario = {
        "MessageSid": "MM123",
        "NumMedia": "2",
        "MediaUrl0": "https://api.twilio.com/Media/ME0",
        "MediaContentType0": "image/jpeg",
        "MediaUrl1": "https://api.twilio.com/Media/ME1",
        "MediaContentType1": "audio/ogg",
    }
    registros = _rodar(formulario, tmp_path, handler)

    assert [r["arquivo"] for r in registros] == ["MM123_0.jpg", "MM123_1.ogg"]
    assert (tmp_path / "MM123_0.jpg").read_bytes() == b"conteudo-/Media/ME0"
    indice = [json.loads(linha) for linha in (tmp_path / "indice.jsonl").read_text().splitlines()]
    assert len(indice) == 2 and all("erro" not in r for r in indice)


def test_falha_http_vai_para_o_indice_sem_derrubar(tmp_path):
    formulario = {"MessageSid": "MM9", "NumMedia": "1", "MediaUrl0": "https://x/ME", "MediaContentType0": "image/png"}
    registros = _rodar(formulario, tmp_path, lambda request: httpx.Response(401))

    assert registros[0]["status_http"] == 401
    assert "erro" in registros[0]
    assert not (tmp_path / "MM9_0.png").exists()


def test_sem_midia_nao_faz_nada(tmp_path):
    def handler(request):
        raise AssertionError("não deveria chamar a rede")

    assert _rodar({"NumMedia": "0"}, tmp_path, handler) == []
    assert _rodar({"NumMedia": "lixo"}, tmp_path, handler) == []
    assert not (tmp_path / "indice.jsonl").exists()


def test_401_com_credencial_tenta_de_novo_sem(tmp_path, monkeypatch):
    """Conta trial: a chamada autenticada é recusada (20003), a anônima pode passar."""
    monkeypatch.setattr("services.canal.captura_midia._credenciais", lambda: ("SKx", "segredo"))

    def handler(request):
        if "authorization" in request.headers:
            return httpx.Response(401)
        return httpx.Response(200, content=b"foto")

    formulario = {"MessageSid": "MM7", "NumMedia": "1", "MediaUrl0": "https://x/ME", "MediaContentType0": "image/jpeg"}
    registros = _rodar(formulario, tmp_path, handler)

    assert registros[0]["status_http_com_auth"] == 401
    assert registros[0]["status_http"] == 200
    assert (tmp_path / "MM7_0.jpg").read_bytes() == b"foto"
