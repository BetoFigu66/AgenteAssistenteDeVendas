"""Mensagem recebida sem texto no `POST /webhook` (caso da mensagem só com mídia).

A Twilio entrega foto, áudio e documento com `NumMedia>0` e `Body` vazio. Enquanto o
`Body` era obrigatório na assinatura do endpoint, o FastAPI devolvia 422 para a Twilio
e a mensagem do cliente se perdia: nem registro, nem resposta.

O que se verifica aqui: o webhook aceita a mensagem, grava a linha no histórico (com
marcador que distingue "só mídia" de "vazia de verdade") e não inventa resposta nenhuma
sobre um conteúdo que o sistema não leu.
"""

from xml.etree import ElementTree

import pytest
from database import Database
from models import Mensagem, ModoExecucao, OrigemMensagem
from services.canal.factory import obter_canal
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.parametro_service import MODO_EXECUCAO, ParametroService


@pytest.fixture(autouse=True)
def _canal_limpo():
    obter_canal.cache_clear()
    yield
    obter_canal.cache_clear()


@pytest.fixture(autouse=True)
def _execucao_normal():
    """Modo mais permissivo de propósito: se alguma resposta fosse gerada para uma
    mensagem sem texto, é aqui que ela apareceria no TwiML."""
    database = Database()
    with database.get_session() as session:
        ParametroService(session).set(MODO_EXECUCAO, ModoExecucao.EXECUCAO_NORMAL.value)
        session.commit()


def _limpar(telefone):
    database = Database()
    with database.get_session() as session:
        apagar_dados_telefone(session, telefone)
        session.commit()


def _mensagens(telefone, origem):
    """Conteúdos das mensagens do telefone, em ordem de gravação.

    Devolve strings e não entidades: a sessão fecha ao sair do `with` e qualquer
    acesso posterior daria `DetachedInstanceError`.
    """
    database = Database()
    with database.get_session() as session:
        return [
            m.conteudo
            for m in session.query(Mensagem)
            .filter_by(telefone=telefone, origem=origem)
            .order_by(Mensagem.id.asc())
            .all()
        ]


def _assert_twiml_vazio(resposta):
    """200 com TwiML bem formado e sem `<Message>` — nada sai para o cliente."""
    assert resposta.status_code == 200, resposta.text
    raiz = ElementTree.fromstring(resposta.text)
    assert raiz.tag == "Response"
    assert list(raiz) == []


def test_body_vazio_com_midia_e_aceito_e_registrado():
    """Mensagem só com mídia: 200, TwiML vazio e a mensagem do cliente no histórico."""
    import main
    from fastapi.testclient import TestClient

    telefone = "5511999977001"
    try:
        with TestClient(main.app) as client:
            resposta = client.post(
                "/webhook",
                data={"From": f"whatsapp:{telefone}", "Body": "", "NumMedia": "2"},
            )
        _assert_twiml_vazio(resposta)

        recebidas = _mensagens(telefone, OrigemMensagem.USER)
        assert len(recebidas) == 1
        # O marcador diz o que de fato chegou, sem afirmar nada sobre o conteúdo da mídia.
        assert "mídia recebida sem texto" in recebidas[0]
        assert "2 anexo" in recebidas[0]

        # Nenhuma resposta automática: o sistema não leu a mídia e não finge que leu.
        assert _mensagens(telefone, OrigemMensagem.SYSTEM) == []
    finally:
        _limpar(telefone)


def test_body_vazio_sem_midia_e_aceito_e_registrado():
    """Mensagem vazia de verdade (`NumMedia=0`): também é aceita e registrada, com
    marcador diferente — `NumMedia` é o que permite separar os dois casos."""
    import main
    from fastapi.testclient import TestClient

    telefone = "5511999977002"
    try:
        with TestClient(main.app) as client:
            resposta = client.post(
                "/webhook",
                data={"From": f"whatsapp:{telefone}", "Body": "", "NumMedia": "0"},
            )
        _assert_twiml_vazio(resposta)

        recebidas = _mensagens(telefone, OrigemMensagem.USER)
        assert len(recebidas) == 1
        assert "sem conteúdo" in recebidas[0]
        assert "anexo" not in recebidas[0]

        assert _mensagens(telefone, OrigemMensagem.SYSTEM) == []
    finally:
        _limpar(telefone)


def test_campo_body_ausente_nao_devolve_422():
    """A Twilio pode nem mandar o campo. Antes isso era 422; agora vale como sem texto."""
    import main
    from fastapi.testclient import TestClient

    telefone = "5511999977003"
    try:
        with TestClient(main.app) as client:
            resposta = client.post("/webhook", data={"From": f"whatsapp:{telefone}", "NumMedia": "1"})
        _assert_twiml_vazio(resposta)
        assert len(_mensagens(telefone, OrigemMensagem.USER)) == 1
    finally:
        _limpar(telefone)


def test_chamada_da_twilio_com_midia_tambem_e_registrada(monkeypatch):
    """Com `AccountSid` (chamada real da Twilio) o comportamento é o mesmo: registra e
    devolve TwiML vazio. O caminho local não é privilegiado aqui porque não há resposta
    gerada para nenhum dos dois lerem."""
    import main
    from config import settings
    from fastapi.testclient import TestClient

    telefone = "5511999977004"
    monkeypatch.setattr(settings, "CANAL_SAIDA", "simulado")
    try:
        with TestClient(main.app) as client:
            resposta = client.post(
                "/webhook",
                data={
                    "From": f"whatsapp:{telefone}",
                    "Body": "",
                    "NumMedia": "1",
                    "AccountSid": "AC_real",
                    "MessageSid": "SM_midia_teste_001",
                },
            )
        _assert_twiml_vazio(resposta)

        recebidas = _mensagens(telefone, OrigemMensagem.USER)
        assert len(recebidas) == 1
        assert "mídia recebida sem texto" in recebidas[0]
    finally:
        _limpar(telefone)


def test_num_media_invalido_conta_como_sem_midia():
    """`NumMedia` vem como string de formulário: lixo não pode derrubar o webhook."""
    import main
    from fastapi.testclient import TestClient

    telefone = "5511999977005"
    try:
        with TestClient(main.app) as client:
            resposta = client.post(
                "/webhook",
                data={"From": f"whatsapp:{telefone}", "Body": "   ", "NumMedia": "nao-e-numero"},
            )
        _assert_twiml_vazio(resposta)

        recebidas = _mensagens(telefone, OrigemMensagem.USER)
        assert len(recebidas) == 1
        assert "sem conteúdo" in recebidas[0]
    finally:
        _limpar(telefone)


def test_falha_ao_registrar_nao_vira_500_para_a_twilio(monkeypatch):
    """Registrar é o único efeito deste caminho, mas falhar nele não pode virar 500.

    A Twilio não reentrega webhook por padrão: um 500 só produz o erro 11200 no console
    dela e a mensagem do cliente se perde em silêncio, que é o sintoma que este caminho
    existe para evitar. Com o banco indisponível o melhor possível é a degradação já
    conhecida do modo HUMANO: 200 com TwiML vazio e o erro no log.
    """
    import main
    from fastapi.testclient import TestClient

    def _explodir(*args, **kwargs):
        raise RuntimeError("banco indisponível")

    monkeypatch.setattr(main, "_registrar_mensagem_sem_texto", _explodir)

    with TestClient(main.app) as client:
        resposta = client.post(
            "/webhook",
            data={
                "From": "whatsapp:5511999977006",
                "Body": "",
                "NumMedia": "1",
                "AccountSid": "AC_real",
            },
        )

    _assert_twiml_vazio(resposta)


# ---------------------------------------------------------------------------
# Vínculo com contato/atendimento e reply-to
#
# Os testes acima usam telefones novos, então `identificar_por_telefone(...).contato`
# devolve `None` em todos e a parte que de fato tem regra (vincular ao atendimento
# ativo, resolver o SID citado) nunca chegava a rodar.
# ---------------------------------------------------------------------------


def _preparar_contato_com_atendimento(telefone):
    """Cria contato e atendimento ativo preexistentes e devolve o id do atendimento."""
    from services.atendimentos import obter_ou_criar_atendimento
    from services.identificador import criar_contato_sem_empresa

    database = Database()
    with database.get_session() as session:
        contato = criar_contato_sem_empresa(session, telefone)
        atendimento = obter_ou_criar_atendimento(session, contato)
        session.commit()
        return contato.id, atendimento.id


def _ultima_mensagem_recebida(telefone):
    """Última mensagem do cliente como dicionário (a sessão fecha ao sair do `with`)."""
    database = Database()
    with database.get_session() as session:
        m = (
            session.query(Mensagem)
            .filter_by(telefone=telefone, origem=OrigemMensagem.USER)
            .order_by(Mensagem.id.desc())
            .first()
        )
        assert m is not None, "nenhuma mensagem do cliente foi registrada"
        return {
            "id": m.id,
            "contato_id": m.contato_id,
            "atendimento_id": m.atendimento_id,
            "resposta_a_mensagem_id": m.resposta_a_mensagem_id,
            "resposta_a_message_sid": m.resposta_a_message_sid,
            "timestamp": m.timestamp,
        }


def _atendimento(atendimento_id):
    from models import Atendimento

    database = Database()
    with database.get_session() as session:
        a = session.query(Atendimento).filter_by(id=atendimento_id).first()
        assert a is not None
        return {"ultima_mensagem_at": a.ultima_mensagem_at}


def _gravar_mensagem_do_sistema(telefone, message_sid):
    """Grava uma resposta nossa já com SID, como o `statusCallback` faria."""
    database = Database()
    with database.get_session() as session:
        m = Mensagem(
            telefone=telefone,
            conteudo="Posso ajudar?",
            origem=OrigemMensagem.SYSTEM,
            message_sid=message_sid,
        )
        session.add(m)
        session.commit()
        return m.id


def test_midia_de_contato_com_atendimento_ativo_entra_no_atendimento():
    """Contato e atendimento preexistentes: a mídia aparece dentro do atendimento, e não
    só no histórico por telefone, e conta como atividade recente do cliente (a janela de
    continuação do REQ-016 lê `ultima_mensagem_at`)."""
    import main
    from fastapi.testclient import TestClient

    telefone = "5511999977010"
    try:
        contato_id, atendimento_id = _preparar_contato_com_atendimento(telefone)
        assert _atendimento(atendimento_id)["ultima_mensagem_at"] is None

        with TestClient(main.app) as client:
            resposta = client.post(
                "/webhook",
                data={"From": f"whatsapp:{telefone}", "Body": "", "NumMedia": "1"},
            )
        _assert_twiml_vazio(resposta)

        msg = _ultima_mensagem_recebida(telefone)
        assert msg["contato_id"] == contato_id
        assert msg["atendimento_id"] == atendimento_id
        assert _atendimento(atendimento_id)["ultima_mensagem_at"] == msg["timestamp"]
    finally:
        _limpar(telefone)


def test_midia_de_contato_sem_atendimento_ativo_fica_so_no_contato():
    """Contato existe mas não há atendimento ativo: vincula o contato e para por aí.
    Criar atendimento a partir de uma mídia que não sabemos ler seria decidir demais
    com informação de menos."""
    import main
    from fastapi.testclient import TestClient
    from services.identificador import criar_contato_sem_empresa

    telefone = "5511999977011"
    try:
        database = Database()
        with database.get_session() as session:
            contato = criar_contato_sem_empresa(session, telefone)
            session.commit()
            contato_id = contato.id

        with TestClient(main.app) as client:
            resposta = client.post(
                "/webhook",
                data={"From": f"whatsapp:{telefone}", "Body": "", "NumMedia": "1"},
            )
        _assert_twiml_vazio(resposta)

        msg = _ultima_mensagem_recebida(telefone)
        assert msg["contato_id"] == contato_id
        assert msg["atendimento_id"] is None
    finally:
        _limpar(telefone)


def test_reply_to_resolve_quando_o_sid_citado_e_da_mesma_conversa():
    """Mídia enviada com o "Responder" do WhatsApp citando uma resposta nossa: o SID
    citado resolve para a mensagem original, e o valor cru fica guardado do mesmo jeito."""
    import main
    from fastapi.testclient import TestClient

    telefone = "5511999977012"
    sid_citado = "SM_reply_to_mesma_conversa"
    try:
        _preparar_contato_com_atendimento(telefone)
        mensagem_citada_id = _gravar_mensagem_do_sistema(telefone, sid_citado)

        with TestClient(main.app) as client:
            resposta = client.post(
                "/webhook",
                data={
                    "From": f"whatsapp:{telefone}",
                    "Body": "",
                    "NumMedia": "1",
                    "AccountSid": "AC_real",
                    "OriginalRepliedMessageSid": sid_citado,
                },
            )
        _assert_twiml_vazio(resposta)

        msg = _ultima_mensagem_recebida(telefone)
        assert msg["resposta_a_mensagem_id"] == mensagem_citada_id
        assert msg["resposta_a_message_sid"] == sid_citado
    finally:
        _limpar(telefone)


def test_reply_to_nao_resolve_sid_de_outra_conversa():
    """O SID chega por um POST público: sem o filtro por telefone, apontar para a
    mensagem de outro cliente seria só trocar um valor no formulário. Não resolvendo, o
    SID cru continua gravado — é o que distingue "não citou nada" de "citou algo que não
    conhecemos"."""
    import main
    from fastapi.testclient import TestClient

    telefone = "5511999977013"
    telefone_alheio = "5511999977014"
    sid_alheio = "SM_reply_to_outra_conversa"
    try:
        _gravar_mensagem_do_sistema(telefone_alheio, sid_alheio)

        with TestClient(main.app) as client:
            resposta = client.post(
                "/webhook",
                data={
                    "From": f"whatsapp:{telefone}",
                    "Body": "",
                    "NumMedia": "1",
                    "AccountSid": "AC_real",
                    "OriginalRepliedMessageSid": sid_alheio,
                },
            )
        _assert_twiml_vazio(resposta)

        msg = _ultima_mensagem_recebida(telefone)
        assert msg["resposta_a_mensagem_id"] is None
        assert msg["resposta_a_message_sid"] == sid_alheio
    finally:
        _limpar(telefone)
        _limpar(telefone_alheio)


def test_captura_de_payload_grava_o_formulario_cru(tmp_path, monkeypatch):
    """A captura existe para virar fixture: precisa gravar o formulário como ele chegou.

    Ligada por `TWILIO_CAPTURAR_PAYLOADS`, desligada por padrão. Grava antes de qualquer
    processamento, então um erro no cérebro não faz perder o payload, que é justamente o que
    se quer preservar enquanto a conta trial existe.
    """
    import json as _json

    import main
    from fastapi.testclient import TestClient

    destino = tmp_path / "payloads.jsonl"
    monkeypatch.setattr(main.settings, "TWILIO_CAPTURAR_PAYLOADS", True)
    monkeypatch.setattr(main.settings, "TWILIO_CAPTURA_ARQUIVO", str(destino))

    telefone = "5511999977010"
    try:
        with TestClient(main.app) as cliente:
            cliente.post(
                "/webhook",
                data={
                    "From": f"whatsapp:+{telefone}",
                    "Body": "oi",
                    "AccountSid": "ACtestefake",
                    "NumMedia": "0",
                    "CampoQueNaoConhecemos": "valor",
                },
            )

        linhas = destino.read_text(encoding="utf-8").strip().splitlines()
        assert len(linhas) == 1
        registro = _json.loads(linhas[0])
        assert registro["endpoint"] == "/webhook"
        # O ponto do mecanismo: campo que o nosso código não declara também é preservado.
        # É exatamente o que faria descobrir que a Twilio manda algo que ignoramos.
        assert registro["form"]["CampoQueNaoConhecemos"] == "valor"
        assert registro["form"]["Body"] == "oi"
        assert "recebido_em" in registro
    finally:
        _limpar(telefone)


def test_captura_desligada_por_padrao_nao_cria_arquivo(tmp_path, monkeypatch):
    """Instrumentação ligada sem querer em produção grava telefone de cliente em disco."""
    import main
    from fastapi.testclient import TestClient

    destino = tmp_path / "nao_deve_existir.jsonl"
    monkeypatch.setattr(main.settings, "TWILIO_CAPTURA_ARQUIVO", str(destino))
    assert main.settings.TWILIO_CAPTURAR_PAYLOADS is False

    telefone = "5511999977011"
    try:
        with TestClient(main.app) as cliente:
            cliente.post("/webhook", data={"From": f"whatsapp:+{telefone}", "Body": "oi"})
        assert not destino.exists()
    finally:
        _limpar(telefone)
