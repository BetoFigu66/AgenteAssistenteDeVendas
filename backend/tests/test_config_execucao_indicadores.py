"""Indicadores de promoção para `execucao_normal` (REQ-011.18).

O ponto destes testes é a separação entre decisão humana e carimbo automático: em
`execucao_normal` o próprio sistema preenche `aprovador_id` com um usuário sentinela,
e misturar isso com aprovação de gente produziria exatamente o número tranquilizador
que o requisito quer evitar.

As asserções são sobre **deltas**, nunca sobre valores absolutos: o endpoint agrega
todas as mensagens do banco na janela, e o banco de desenvolvimento tem histórico de
outras conversas.
"""

from datetime import timedelta

import pytest
from database import Database
from models import Mensagem, OrigemMensagem, User
from services.dev_limpeza_telefone import apagar_dados_telefone

# Mesmo nome que `main.py` usa para separar carimbo automático de decisão humana.
# Importado da fonte (processador) nos dois lados, para não haver literal duplicado
# capaz de divergir em silêncio.
from services.processador import _USER_SISTEMA_NOME
from utils.datetime_utils import utc_now


@pytest.fixture
def db_session():
    database = Database()
    with database.get_session() as session:
        yield session


def _limpar(db_session, telefone):
    db_session.commit()
    apagar_dados_telefone(db_session, telefone)
    db_session.commit()


def _criar_mensagem_system(db_session, telefone, *, timestamp=None) -> int:
    msg = Mensagem(
        telefone=telefone,
        conteudo="Resposta gerada pela IA",
        origem=OrigemMensagem.SYSTEM,
    )
    if timestamp is not None:
        msg.timestamp = timestamp
    db_session.add(msg)
    db_session.commit()
    db_session.refresh(msg)
    return msg.id


def _obter_user_sistema(db_session) -> User:
    """Usuário sentinela que o processador usa ao auto-aprovar em `execucao_normal`."""
    user = db_session.query(User).filter_by(nome=_USER_SISTEMA_NOME).first()
    if user is None:
        user = User(nome=_USER_SISTEMA_NOME)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


def _indicadores(client, dias=7) -> dict:
    r = client.get(f"/api/config/execucao/indicadores?dias={dias}")
    assert r.status_code == 200, r.text
    return r.json()


def test_carimbo_automatico_nao_entra_na_conta_de_aprovadas(client, db_session):
    """Auto-aprovação do sistema fica num balde próprio, fora da taxa humana."""
    telefone = "5511999987101"
    try:
        antes = _indicadores(client)

        sistema_user = _obter_user_sistema(db_session)
        mensagem_id = _criar_mensagem_system(db_session, telefone)
        msg = db_session.query(Mensagem).filter_by(id=mensagem_id).first()
        msg.aprovador_id = sistema_user.id
        msg.timestamp_aprovacao = utc_now()
        db_session.commit()

        depois = _indicadores(client)
        assert depois["auto_aprovadas_pelo_sistema"] == antes["auto_aprovadas_pelo_sistema"] + 1
        assert depois["aprovadas_por_humano"] == antes["aprovadas_por_humano"]
        assert depois["decididas_por_humano"] == antes["decididas_por_humano"]
        assert depois["pendentes"] == antes["pendentes"]
    finally:
        _limpar(db_session, telefone)


def test_aprovacao_humana_conta_como_aprovada(client, db_session):
    telefone = "5511999987102"
    try:
        antes = _indicadores(client)

        mensagem_id = _criar_mensagem_system(db_session, telefone)
        r = client.post(f"/api/mensagens/{mensagem_id}/aprovar", json={})
        assert r.status_code == 200, r.text

        depois = _indicadores(client)
        assert depois["aprovadas_por_humano"] == antes["aprovadas_por_humano"] + 1
        assert depois["reprovadas_por_humano"] == antes["reprovadas_por_humano"]
        assert depois["auto_aprovadas_pelo_sistema"] == antes["auto_aprovadas_pelo_sistema"]
    finally:
        _limpar(db_session, telefone)


def test_reprovacao_conta_como_reprovada_e_nao_como_aprovada(client, db_session):
    """Aprovar e reprovar gravam o mesmo `aprovador_id`; quem separa é o report."""
    telefone = "5511999987103"
    try:
        antes = _indicadores(client)

        mensagem_id = _criar_mensagem_system(db_session, telefone)
        r = client.post(
            f"/api/mensagens/{mensagem_id}/reprovar",
            json={"justificativa": "Resposta com informação errada"},
        )
        assert r.status_code == 201, r.text

        depois = _indicadores(client)
        assert depois["reprovadas_por_humano"] == antes["reprovadas_por_humano"] + 1
        assert depois["aprovadas_por_humano"] == antes["aprovadas_por_humano"]
        assert depois["decididas_por_humano"] == antes["decididas_por_humano"] + 1
    finally:
        _limpar(db_session, telefone)


def test_mensagem_pendente_nao_conta_como_decidida(client, db_session):
    telefone = "5511999987104"
    try:
        antes = _indicadores(client)

        _criar_mensagem_system(db_session, telefone)

        depois = _indicadores(client)
        assert depois["pendentes"] == antes["pendentes"] + 1
        assert depois["decididas_por_humano"] == antes["decididas_por_humano"]
        assert depois["total_geradas"] == antes["total_geradas"] + 1
    finally:
        _limpar(db_session, telefone)


def test_baldes_particionam_a_coorte_da_janela(client, db_session):
    """Invariantes estruturais: os baldes fecham com o total e entre si."""
    telefone = "5511999987105"
    try:
        _criar_mensagem_system(db_session, telefone)
        body = _indicadores(client)

        assert body["total_geradas"] == (
            body["pendentes"] + body["auto_aprovadas_pelo_sistema"] + body["decididas_por_humano"]
        )
        assert body["decididas_por_humano"] == (body["aprovadas_por_humano"] + body["reprovadas_por_humano"])
        if body["decididas_por_humano"]:
            esperado = round(body["aprovadas_por_humano"] / body["decididas_por_humano"], 4)
            assert body["taxa_aprovacao_humana"] == esperado
        else:
            assert body["taxa_aprovacao_humana"] is None
    finally:
        _limpar(db_session, telefone)


def test_janela_ignora_mensagem_anterior_ao_periodo(client, db_session):
    telefone = "5511999987106"
    try:
        antes = _indicadores(client, dias=7)

        _criar_mensagem_system(db_session, telefone, timestamp=utc_now() - timedelta(days=30))

        depois = _indicadores(client, dias=7)
        assert depois["total_geradas"] == antes["total_geradas"]

        # A mesma mensagem aparece quando a janela é larga o bastante.
        largo = _indicadores(client, dias=60)
        assert largo["total_geradas"] >= depois["total_geradas"] + 1
    finally:
        _limpar(db_session, telefone)


@pytest.mark.parametrize("dias", [0, -1, 366])
def test_dias_fora_do_intervalo_retorna_400(client, dias):
    r = client.get(f"/api/config/execucao/indicadores?dias={dias}")
    assert r.status_code == 400
