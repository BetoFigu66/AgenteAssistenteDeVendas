"""Download dos anexos da Twilio durante a captura de payloads (conta trial expirando).

Os formulários abaixo usam os nomes de campo confirmados pela colheita de 25/09
(`NumMedia`, `MediaUrl{i}`, `MediaContentType{i}`). O webhook é público, então parte dos
testes é sobre formulário forjado: SID que tenta sair da pasta, URL fora da Twilio.
"""

import asyncio
import json

import httpx
from services.canal import captura_midia
from services.canal.captura_midia import baixar_midias

SID = "MM" + "0" * 31 + "1"
SID2 = "MM" + "0" * 31 + "2"
BASE = "https://api.twilio.com/2010-04-01/Accounts/ACx/Messages"


def _rodar(formulario, pasta, handler):
    return asyncio.run(baixar_midias(formulario, pasta=pasta, transport=httpx.MockTransport(handler)))


def _form(sid=SID, url=None, content_type="image/jpeg", num="1"):
    return {
        "MessageSid": sid,
        "NumMedia": num,
        "MediaUrl0": url or f"{BASE}/{sid}/Media/ME0",
        "MediaContentType0": content_type,
    }


def test_baixa_cada_anexo_com_extensao_do_content_type(tmp_path):
    def handler(request):
        return httpx.Response(200, content=b"conteudo-" + request.url.path.encode()[-3:])

    formulario = {
        "MessageSid": SID,
        "NumMedia": "2",
        "MediaUrl0": f"{BASE}/{SID}/Media/ME0",
        "MediaContentType0": "image/jpeg",
        "MediaUrl1": f"{BASE}/{SID}/Media/ME1",
        "MediaContentType1": "audio/ogg",
    }
    registros = _rodar(formulario, tmp_path, handler)

    assert [r["arquivo"] for r in registros] == [f"{SID}_0.jpg", f"{SID}_1.ogg"]
    assert (tmp_path / f"{SID}_0.jpg").read_bytes() == b"conteudo-ME0"
    indice = [json.loads(linha) for linha in (tmp_path / "indice.jsonl").read_text().splitlines()]
    assert len(indice) == 2 and all("erro" not in r for r in indice)


def test_falha_http_vai_para_o_indice_sem_derrubar(tmp_path):
    registros = _rodar(_form(content_type="image/png"), tmp_path, lambda request: httpx.Response(404))

    assert registros[0]["status_http"] == 404
    assert "erro" in registros[0]
    assert not (tmp_path / f"{SID}_0.png").exists()


def test_sem_midia_nao_faz_nada(tmp_path):
    def handler(request):
        raise AssertionError("não deveria chamar a rede")

    assert _rodar({"NumMedia": "0", "MessageSid": SID}, tmp_path, handler) == []
    assert _rodar({"NumMedia": "lixo", "MessageSid": SID}, tmp_path, handler) == []
    assert not (tmp_path / "indice.jsonl").exists()


def test_401_com_credencial_tenta_de_novo_sem(tmp_path, monkeypatch):
    """Conta trial: a chamada autenticada é recusada (20003), a anônima pode passar."""
    monkeypatch.setattr(captura_midia, "_credenciais", lambda: ("SKx", "segredo"))

    def handler(request):
        if "authorization" in request.headers:
            return httpx.Response(401)
        return httpx.Response(200, content=b"foto")

    registros = _rodar(_form(sid=SID2), tmp_path, handler)

    assert registros[0]["status_http_com_auth"] == 401
    assert registros[0]["status_http"] == 200
    assert (tmp_path / f"{SID2}_0.jpg").read_bytes() == b"foto"


def test_sid_forjado_nao_escreve_fora_da_pasta(tmp_path):
    """O `MessageSid` vira nome de arquivo: `../` não pode sair da pasta."""
    pasta = tmp_path / "midias"

    def handler(request):
        raise AssertionError("não deveria chamar a rede")

    formulario = _form(sid="../fora_da_pasta", content_type="text/x-python")
    assert _rodar(formulario, pasta, handler) == []
    assert list(tmp_path.rglob("fora_da_pasta*")) == []


def test_url_fora_da_twilio_nao_recebe_credencial(tmp_path, monkeypatch):
    """Formulário forjado com `MediaUrl` para outro host: nenhuma requisição sai, então a
    API Key não vaza e não há acesso à rede local."""
    monkeypatch.setattr(captura_midia, "_credenciais", lambda: ("SKx", "segredo"))
    chamadas = []

    def handler(request):
        chamadas.append(request)
        return httpx.Response(200, content=b"x")

    for url in ("https://evil.example/ME0", "http://api.twilio.com/ME0", "http://127.0.0.1:5433/"):
        registros = _rodar(_form(url=url), tmp_path, handler)
        assert "erro" in registros[0]

    assert chamadas == []


def test_anexo_acima_do_teto_e_descartado(tmp_path, monkeypatch):
    monkeypatch.setattr(captura_midia, "_MAX_BYTES", 10)
    registros = _rodar(_form(), tmp_path, lambda request: httpx.Response(200, content=b"x" * 11))

    assert "erro" in registros[0]
    assert not (tmp_path / f"{SID}_0.jpg").exists()


def test_num_media_exagerado_e_limitado(tmp_path):
    chamadas = []

    def handler(request):
        chamadas.append(request)
        return httpx.Response(200, content=b"x")

    formulario = {"MessageSid": SID, "NumMedia": "500"}
    for i in range(20):
        formulario[f"MediaUrl{i}"] = f"{BASE}/{SID}/Media/ME{i}"
        formulario[f"MediaContentType{i}"] = "image/jpeg"
    _rodar(formulario, tmp_path, handler)

    assert len(chamadas) == captura_midia._MAX_MIDIAS
