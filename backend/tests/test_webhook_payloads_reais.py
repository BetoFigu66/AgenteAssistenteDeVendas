"""`POST /webhook` e `/webhook/status` alimentados com formulários REAIS da Twilio.

Os demais testes de webhook montam o formulário à mão, com os campos que supomos que a
Twilio manda. Estes usam a colheita de 25/09 (`tests/fixtures/twilio/`, anonimizada),
então provam o comportamento contra o que a Twilio de fato envia para cada tipo de
mensagem do WhatsApp. Foi essa colheita que revelou os dois bugs cobertos aqui: o
documento chega com o nome do arquivo no `Body` (e ia ao cérebro como pergunta do
cliente) e a localização chega com `Body` vazio e as coordenadas em campos próprios
(e virava "mensagem sem conteúdo").

Mensagem de texto vai ao cérebro, e o cérebro é trocado por um dublê que só registra
com o que foi chamado: o que se prova aqui é a triagem do webhook, e o texto longo
cairia na LLM de verdade.
"""

import json
from pathlib import Path
from xml.etree import ElementTree

import pytest
from database import Database
from models import Mensagem, OrigemMensagem
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.processador import ResultadoProcessamento

_PASTA_FIXTURES = Path(__file__).parent / "fixtures" / "twilio"

# Telefone fictício da anonimização, o mesmo em todas as fixtures.
_TELEFONE = "+5511900000001"


def _fixture(nome):
    return json.loads((_PASTA_FIXTURES / f"{nome}.json").read_text(encoding="utf-8"))


def _limpar():
    database = Database()
    with database.get_session() as session:
        apagar_dados_telefone(session, _TELEFONE)
        session.commit()


@pytest.fixture(autouse=True)
def _telefone_limpo():
    """Limpa antes também: os `MessageSid` das fixtures são fixos, e uma linha que
    sobrasse de uma rodada interrompida faria a idempotência barrar o teste seguinte."""
    _limpar()
    yield
    _limpar()


@pytest.fixture
def cerebro(monkeypatch):
    """Dublê de `_processar_via_cerebro`: registra as chamadas e não gera resposta
    (TwiML vazio, como no modo HUMANO)."""
    import main

    chamadas = []

    async def _dubla(
        telefone,
        conteudo,
        message_sid,
        responde_a_message_sid=None,
        responde_a_mensagem_id=None,
        nome_perfil=None,
    ):
        chamadas.append(
            {
                "telefone": telefone,
                "conteudo": conteudo,
                "message_sid": message_sid,
                "responde_a_message_sid": responde_a_message_sid,
                "nome_perfil": nome_perfil,
            }
        )
        return ResultadoProcessamento(resposta="")

    monkeypatch.setattr(main, "_processar_via_cerebro", _dubla)
    return chamadas


def _postar(nome, **kwargs):
    import main
    from fastapi.testclient import TestClient

    registro = _fixture(nome)
    with TestClient(main.app) as client:
        return client.post(registro["endpoint"], data=registro["form"], **kwargs)


def _assert_twiml_vazio(resposta):
    assert resposta.status_code == 200, resposta.text
    raiz = ElementTree.fromstring(resposta.text)
    assert raiz.tag == "Response"
    assert list(raiz) == []


def _recebidas():
    database = Database()
    with database.get_session() as session:
        return [
            {"conteudo": m.conteudo, "message_sid": m.message_sid}
            for m in session.query(Mensagem)
            .filter_by(telefone=_TELEFONE, origem=OrigemMensagem.USER)
            .order_by(Mensagem.id.asc())
            .all()
        ]


# ---------------------------------------------------------------------------
# Texto: vai ao cérebro, com o `Body` intacto
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "nome",
    ["texto_simples", "texto_emoji", "texto_acentuacao", "texto_longo", "foto_com_legenda"],
)
def test_texto_vai_ao_cerebro_com_body_intacto(nome, cerebro):
    """Emoji, acentuação e texto longo chegam ao cérebro byte a byte como a Twilio
    mandou. Foto com legenda também vai: a legenda é texto que o cliente escreveu."""
    form = _fixture(nome)["form"]

    resposta = _postar(nome)

    _assert_twiml_vazio(resposta)
    assert len(cerebro) == 1
    assert cerebro[0]["conteudo"] == form["Body"]
    assert cerebro[0]["message_sid"] == form["MessageSid"]
    assert cerebro[0]["telefone"] == _TELEFONE
    # Vai cru: a validação do nome é do `processar()`, não do webhook.
    assert cerebro[0]["nome_perfil"] == form["ProfileName"]


def test_texto_longo_chega_inteiro():
    """Guarda da própria fixture: o texto longo tem que continuar longo e com as quebras
    de linha, senão o teste acima deixa de provar alguma coisa."""
    body = _fixture("texto_longo")["form"]["Body"]
    assert len(body) > 1000
    assert "\n" in body and "—" in body and "ç" in body


def test_reply_to_repassa_o_sid_citado_ao_cerebro(cerebro):
    """A resposta citada chega com `OriginalRepliedMessageSid`, e é o SID da nossa
    mensagem cujos callbacks estão em `status_*.json`. O webhook repassa esse SID; quem
    resolve para a mensagem é o processador."""
    form = _fixture("texto_reply_to")["form"]
    sid_citado = _fixture("status_sent")["form"]["MessageSid"]
    assert form["OriginalRepliedMessageSid"] == sid_citado

    _assert_twiml_vazio(_postar("texto_reply_to"))

    assert len(cerebro) == 1
    assert cerebro[0]["conteudo"] == form["Body"]
    assert cerebro[0]["responde_a_message_sid"] == sid_citado


# ---------------------------------------------------------------------------
# Sem texto do cliente: registra com marcador e não aciona o cérebro
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("nome", "marcador_esperado"),
    [
        ("foto_sem_legenda", "[mídia recebida sem texto: 1 anexo(s)]"),
        ("audio", "[mídia recebida sem texto: 1 anexo(s)]"),
        ("contato", "[mídia recebida sem texto: 1 anexo(s)]"),
        ("documento_encaminhado", "[documento recebido: 3c9a7e21-5b4d-4f18-9a62-0e8d4b7c1f35_assinado.pdf]"),
        ("localizacao", "[localização: -23.5505199, -46.6333094]"),
    ],
)
def test_sem_texto_do_cliente_registra_marcador_e_nao_aciona_cerebro(nome, marcador_esperado, cerebro):
    form = _fixture(nome)["form"]

    _assert_twiml_vazio(_postar(nome))

    assert cerebro == []
    assert _recebidas() == [{"conteudo": marcador_esperado, "message_sid": form["MessageSid"]}]


def test_documento_nao_e_tratado_como_texto_apesar_do_body(cerebro):
    """O bug de 25/09: o `Body` do documento é o nome do arquivo, e o bot respondia a
    ele. É o `MessageType` que separa, não o `Body`."""
    form = _fixture("documento_encaminhado")["form"]
    assert form["MessageType"] == "document"
    assert form["Body"].endswith(".pdf")

    _assert_twiml_vazio(_postar("documento_encaminhado"))

    assert cerebro == []


def test_localizacao_real_chega_sem_body_e_sem_midia():
    """Guarda da fixture: é esta forma que fazia a localização virar "sem conteúdo"."""
    form = _fixture("localizacao")["form"]
    assert form["MessageType"] == "location"
    assert form["NumMedia"] == "0"
    assert form["Body"] == ""
    assert form["Latitude"] and form["Longitude"]


def test_sem_message_type_body_com_cara_de_arquivo_continua_indo_ao_cerebro(cerebro):
    """Testador e simulador mandam só `From`/`Body`. Sem `MessageType` não há como saber
    que é documento, e o comportamento anterior tem que se manter."""
    import main
    from fastapi.testclient import TestClient

    with TestClient(main.app) as client:
        resposta = client.post("/webhook", data={"From": f"whatsapp:{_TELEFONE}", "Body": "contrato.pdf"})

    _assert_twiml_vazio(resposta)
    assert [c["conteudo"] for c in cerebro] == ["contrato.pdf"]


@pytest.mark.parametrize(
    ("argumentos", "esperado"),
    [
        # Localização sem coordenadas ainda é localização: não cai em "sem conteúdo".
        (("location", "", "0", None, None), "[localização recebida sem coordenadas]"),
        (("document", "", "1", None, None), "[documento recebido]"),
        (("DOCUMENT", "  nota.pdf ", "1", None, None), "[documento recebido: nota.pdf]"),
        ((None, "oi", "0", None, None), None),
        ((None, "", None, None, None), "[mensagem recebida sem conteúdo]"),
        (("tipo_novo", "", "0", None, None), "[mensagem recebida sem conteúdo]"),
    ],
)
def test_conteudo_sem_texto_casos_de_borda(argumentos, esperado):
    import main

    assert main._conteudo_sem_texto(*argumentos) == esperado


# ---------------------------------------------------------------------------
# Idempotência por `MessageSid`
# ---------------------------------------------------------------------------


def test_reentrega_da_mesma_mensagem_sem_texto_nao_duplica(cerebro, monkeypatch):
    """Conta as chamadas ao registro, e não só as linhas: sem a idempotência a segunda
    gravação também não passaria (`message_sid` é unique), mas por erro de constraint
    engolido no log, que não é o comportamento que se quer."""
    import main

    original = main._registrar_mensagem_sem_texto
    registros = []

    def _espiao(*args, **kwargs):
        registros.append(args)
        return original(*args, **kwargs)

    monkeypatch.setattr(main, "_registrar_mensagem_sem_texto", _espiao)

    _assert_twiml_vazio(_postar("audio"))
    _assert_twiml_vazio(_postar("audio"))

    assert len(registros) == 1
    assert len(_recebidas()) == 1


def test_message_sid_ja_gravado_nao_aciona_o_cerebro(cerebro):
    """Mensagem de texto reentregue: o cérebro não roda de novo, então não sai uma
    segunda resposta ao cliente."""
    form = _fixture("texto_simples")["form"]
    database = Database()
    with database.get_session() as session:
        session.add(
            Mensagem(
                telefone=_TELEFONE,
                conteudo=form["Body"],
                origem=OrigemMensagem.USER,
                message_sid=form["MessageSid"],
            )
        )
        session.commit()

    _assert_twiml_vazio(_postar("texto_simples"))

    assert cerebro == []
    assert len(_recebidas()) == 1


def test_chamada_local_sem_message_sid_nunca_e_barrada(cerebro):
    import main
    from fastapi.testclient import TestClient

    with TestClient(main.app) as client:
        for _ in range(2):
            _assert_twiml_vazio(client.post("/webhook", data={"From": f"whatsapp:{_TELEFONE}", "Body": "oi"}))

    assert len(cerebro) == 2


# ---------------------------------------------------------------------------
# `/webhook/status`: os três callbacks reais de uma mensagem nossa
# ---------------------------------------------------------------------------


def test_callbacks_de_status_reais_gravam_o_sid_uma_vez():
    """sent, delivered e read chegam com o mesmo SID: a primeira grava, as outras não
    mexem, e nenhuma marca erro de envio."""
    database = Database()
    with database.get_session() as session:
        nossa = Mensagem(telefone=_TELEFONE, conteudo="Posso ajudar?", origem=OrigemMensagem.SYSTEM)
        session.add(nossa)
        session.commit()
        mensagem_id = nossa.id

    sid = _fixture("status_sent")["form"]["MessageSid"]
    for nome in ("status_sent", "status_delivered", "status_read"):
        assert _fixture(nome)["form"]["MessageSid"] == sid
        resposta = _postar(nome, params={"mensagem_id": mensagem_id})
        assert resposta.status_code == 200, resposta.text
        assert resposta.json() == {"status": "ok"}

    with database.get_session() as session:
        m = session.query(Mensagem).filter_by(id=mensagem_id).one()
        assert m.message_sid == sid
        assert m.erro_envio is None


# ---------------------------------------------------------------------------
# Download de anexos: só depois da assinatura e da idempotência
# ---------------------------------------------------------------------------


@pytest.fixture
def espiao_download(monkeypatch, tmp_path):
    import main
    from config import settings

    monkeypatch.setattr(settings, "TWILIO_CAPTURAR_PAYLOADS", True)
    monkeypatch.setattr(settings, "TWILIO_CAPTURA_ARQUIVO", str(tmp_path / "payloads.jsonl"))
    chamadas = []
    monkeypatch.setattr(main, "agendar_download_midias", lambda formulario: chamadas.append(formulario))
    return chamadas


def test_download_de_anexo_e_agendado_para_chamada_da_twilio(espiao_download):
    resposta = _postar("foto_sem_legenda")

    _assert_twiml_vazio(resposta)
    assert len(espiao_download) == 1
    assert espiao_download[0]["MediaUrl0"] == _fixture("foto_sem_legenda")["form"]["MediaUrl0"]


def test_assinatura_invalida_nao_dispara_download(espiao_download, monkeypatch):
    """Antes a captura agendava o download antes de conferir a assinatura: uma requisição
    forjada acionava o download e só depois levava a recusa."""
    from config import settings

    monkeypatch.setattr(settings, "TWILIO_VALIDAR_ASSINATURA", True)
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "token-de-teste")

    resposta = _postar("foto_sem_legenda", headers={"X-Twilio-Signature": "forjada"})

    assert resposta.status_code in (403, 503)
    assert espiao_download == []


def test_reentrega_nao_baixa_de_novo(espiao_download):
    _postar("foto_sem_legenda")
    _postar("foto_sem_legenda")

    assert len(espiao_download) == 1
