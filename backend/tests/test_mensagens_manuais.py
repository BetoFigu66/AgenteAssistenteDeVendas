"""Testes de `POST /api/atendimentos/{id}/mensagens-manuais` (REQ-008.5).

É o caminho da resposta manual do operador quando o atendimento está em
`ModoOperacao.HUMANO`: a mensagem nasce com `origem=SYSTEM` e já aprovada (quem
digitou é o próprio autor, não há nada a aprovar depois) e vai para o canal de
saída configurado.

O caso que mais importa aqui é o da entrega que falha: a decisão humana já
aconteceu, então o registro tem que sobreviver, e o motivo da não entrega tem
que ficar visível em `erro_envio`. Falha de entrega nunca vira erro HTTP.
"""

import pytest
from database import Database
from models import Mensagem, OrigemMensagem, User
from services import atendimentos as svc_atendimentos
from services.canal.base import CanalSaida, ResultadoEnvio
from services.canal.factory import obter_canal
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.identificador import criar_contato_sem_empresa


@pytest.fixture
def db_session():
    database = Database()
    with database.get_session() as session:
        yield session


@pytest.fixture(autouse=True)
def _canal_limpo():
    """A factory é `lru_cache`: sem limpar, o canal de um teste vaza para o próximo."""
    obter_canal.cache_clear()
    yield
    obter_canal.cache_clear()


def _limpar(db_session, telefone):
    db_session.commit()
    apagar_dados_telefone(db_session, telefone)
    db_session.commit()


def _novo_atendimento_id(db_session, telefone) -> int:
    """Cria contato + atendimento e commita: o endpoint lê em outra sessão."""
    contato = criar_contato_sem_empresa(db_session, telefone, nome=None)
    atendimento = svc_atendimentos.obter_ou_criar_atendimento(db_session, contato)
    db_session.commit()
    return atendimento.id


def _mensagens_saida(db_session, telefone):
    db_session.expire_all()
    return (
        db_session.query(Mensagem)
        .filter_by(telefone=telefone, origem=OrigemMensagem.SYSTEM)
        .order_by(Mensagem.id.asc())
        .all()
    )


def _id_usuario_logado(db_session) -> int:
    return db_session.query(User).filter_by(login="pytest_runner").first().id


class _CanalFalho(CanalSaida):
    """Canal que tenta entregar e falha, como o WhatsApp fora da janela de 24h."""

    nome = "falho"
    entrega_real = True

    def enviar(self, telefone, texto, *, mensagem_id=None):
        return ResultadoEnvio(entregue=False, erro="Twilio 63016: fora da janela de 24h")


class _CanalEntregador(CanalSaida):
    """Canal que entrega de verdade — para checar o lado feliz do contrato."""

    nome = "entregador"
    entrega_real = True

    def __init__(self):
        self.enviados = []

    def enviar(self, telefone, texto, *, mensagem_id=None):
        self.enviados.append((telefone, texto, mensagem_id))
        return ResultadoEnvio(entregue=True, message_sid=f"SM_manual_{mensagem_id}")


# ---------------------------------------------------------------------------
# Registro da mensagem
# ---------------------------------------------------------------------------


def test_mensagem_manual_nasce_aprovada_pelo_operador_logado(client, db_session):
    telefone = "+5511999955001"
    try:
        atendimento_id = _novo_atendimento_id(db_session, telefone)

        r = client.post(
            f"/api/atendimentos/{atendimento_id}/mensagens-manuais",
            json={"conteudo": "  Bom dia, já verifiquei aqui.  "},
        )
        assert r.status_code == 201, r.text
        corpo = r.json()

        assert corpo["origem"] == OrigemMensagem.SYSTEM.value
        # O espaço das pontas é aparado antes de gravar.
        assert corpo["conteudo"] == "Bom dia, já verifiquei aqui."
        assert corpo["atendimento_id"] == atendimento_id
        assert corpo["telefone"] == telefone
        # Já aprovada: o operador logado é o autor, não existe fila de aprovação.
        assert corpo["aprovador_id"] == _id_usuario_logado(db_session)
        assert corpo["timestamp_aprovacao"] is not None
        assert corpo["pendente_aprovacao"] is False

        gravadas = _mensagens_saida(db_session, telefone)
        assert len(gravadas) == 1
        assert gravadas[0].id == corpo["id"]
        assert gravadas[0].aprovador_id == _id_usuario_logado(db_session)
    finally:
        _limpar(db_session, telefone)


@pytest.mark.parametrize("conteudo", ["", "   ", "\n\t "])
def test_conteudo_vazio_ou_so_espacos_e_rejeitado(client, db_session, conteudo):
    telefone = "+5511999955002"
    try:
        atendimento_id = _novo_atendimento_id(db_session, telefone)

        r = client.post(
            f"/api/atendimentos/{atendimento_id}/mensagens-manuais",
            json={"conteudo": conteudo},
        )
        assert r.status_code == 400
        assert _mensagens_saida(db_session, telefone) == []
    finally:
        _limpar(db_session, telefone)


def test_atendimento_inexistente_devolve_404(client):
    r = client.post(
        "/api/atendimentos/999999999/mensagens-manuais",
        json={"conteudo": "Mensagem para atendimento que não existe"},
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Entrega
# ---------------------------------------------------------------------------


def test_canal_simulado_registra_mas_nao_entrega(client, db_session, monkeypatch):
    """Default do projeto: nada chega ao cliente, e isso não é falha.

    `entregue=False` com `erro_envio=None` é o terceiro estado do `ResultadoEnvio`,
    o que costuma ser esquecido: não entregou porque o canal não entrega.
    """
    telefone = "+5511999955003"
    monkeypatch.setattr("config.settings.CANAL_SAIDA", "simulado")
    try:
        atendimento_id = _novo_atendimento_id(db_session, telefone)

        r = client.post(
            f"/api/atendimentos/{atendimento_id}/mensagens-manuais",
            json={"conteudo": "Resposta manual do operador"},
        )
        assert r.status_code == 201, r.text
        corpo = r.json()

        assert corpo["entregue"] is False
        assert corpo["erro_envio"] is None
        assert corpo["timestamp_envio"] is None
        assert corpo["message_sid"] is None

        gravada = _mensagens_saida(db_session, telefone)[0]
        assert gravada.timestamp_envio is None
        assert gravada.erro_envio is None
    finally:
        _limpar(db_session, telefone)


def test_canal_que_entrega_marca_envio_e_sid(client, db_session, monkeypatch):
    telefone = "+5511999955004"
    canal = _CanalEntregador()
    monkeypatch.setattr("services.envio.obter_canal", lambda: canal)
    try:
        atendimento_id = _novo_atendimento_id(db_session, telefone)

        r = client.post(
            f"/api/atendimentos/{atendimento_id}/mensagens-manuais",
            json={"conteudo": "Segue o orçamento por aqui"},
        )
        assert r.status_code == 201, r.text
        corpo = r.json()

        assert corpo["entregue"] is True
        assert corpo["erro_envio"] is None
        assert canal.enviados == [(telefone, "Segue o orçamento por aqui", corpo["id"])]

        gravada = _mensagens_saida(db_session, telefone)[0]
        assert gravada.timestamp_envio is not None
        assert gravada.message_sid == f"SM_manual_{corpo['id']}"
    finally:
        _limpar(db_session, telefone)


def test_falha_de_entrega_nao_desfaz_o_registro(client, db_session, monkeypatch):
    """O caso que justifica o `entregar_mensagem` não levantar exceção.

    O operador digitou e mandou: isso aconteceu de verdade e precisa ficar no banco,
    aprovado, com o motivo da não entrega ao lado. Virar HTTP 500 perderia as duas
    informações de uma vez.
    """
    telefone = "+5511999955005"
    monkeypatch.setattr("services.envio.obter_canal", _CanalFalho)
    try:
        atendimento_id = _novo_atendimento_id(db_session, telefone)

        r = client.post(
            f"/api/atendimentos/{atendimento_id}/mensagens-manuais",
            json={"conteudo": "Consegue confirmar a quantidade?"},
        )
        assert r.status_code == 201, r.text
        corpo = r.json()

        assert corpo["entregue"] is False
        assert "63016" in corpo["erro_envio"]
        assert corpo["timestamp_envio"] is None
        # A decisão humana continua registrada apesar da falha de entrega.
        assert corpo["aprovador_id"] == _id_usuario_logado(db_session)
        assert corpo["timestamp_aprovacao"] is not None

        gravadas = _mensagens_saida(db_session, telefone)
        assert len(gravadas) == 1
        assert gravadas[0].conteudo == "Consegue confirmar a quantidade?"
        assert "63016" in gravadas[0].erro_envio
        assert gravadas[0].timestamp_envio is None
        assert gravadas[0].aprovador_id == _id_usuario_logado(db_session)
    finally:
        _limpar(db_session, telefone)
