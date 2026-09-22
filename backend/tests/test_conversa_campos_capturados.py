"""Campos já capturados no topo da conversa (REQ-010.7B).

O risco coberto aqui é vazar estado interno do motor para a tela do operador:
`AtendimentoInfo` é chave-valor livre e guarda marcadores de controle junto com dado
de negócio. O filtro é por lista de permissão (o catálogo de campos), então estes
testes exercitam justamente chaves internas que não podem aparecer.
"""

import pytest
from database import Database
from models import AtendimentoInfo, Contato
from services.atendimentos import obter_ou_criar_atendimento
from services.dev_limpeza_telefone import apagar_dados_telefone


@pytest.fixture
def db_session():
    database = Database()
    with database.get_session() as session:
        yield session


def _limpar(db_session, telefone):
    db_session.commit()
    apagar_dados_telefone(db_session, telefone)
    db_session.commit()


def _preparar(db_session, telefone, infos):
    contato = Contato(telefone=telefone, nome="Cliente Campos Capturados")
    db_session.add(contato)
    db_session.commit()
    db_session.refresh(contato)

    atendimento = obter_ou_criar_atendimento(db_session, contato)
    for chave, valor in infos:
        db_session.add(AtendimentoInfo(atendimento_id=atendimento.id, chave=chave, valor=valor))
    db_session.commit()
    return atendimento


def _campos(client, telefone) -> list:
    r = client.get(f"/api/conversa/{telefone}")
    assert r.status_code == 200, r.text
    return r.json()["atendimento"]["campos_capturados"]


def test_campos_capturados_traz_valor_e_rotulo_do_catalogo(client, db_session):
    telefone = "5511999985201"
    try:
        _preparar(
            db_session,
            telefone,
            [
                ("tipos_produto", "relogio_ponto"),
                ("software_controle_ponto", "Domínio"),
            ],
        )

        campos = _campos(client, telefone)
        por_chave = {c["chave"]: c for c in campos}
        assert "software_controle_ponto" in por_chave
        assert por_chave["software_controle_ponto"]["valor"] == "Domínio"
        assert por_chave["software_controle_ponto"]["id_catalogo"] == "CAMPO-software-ponto"
        assert por_chave["software_controle_ponto"]["pergunta"]
    finally:
        _limpar(db_session, telefone)


def test_chaves_de_controle_interno_nao_vazam_para_a_tela(client, db_session):
    """Marcadores do motor, contadores e resultado de consulta de crédito ficam fora."""
    telefone = "5511999985202"
    internas = [
        ("pergunta_prioritaria_chave", "faixa_funcionarios"),
        ("homologado_software__perguntado", "true"),
        ("modelo_tentativas_falhas", "2"),
        ("resumo_finalizando_apresentado", "true"),
        ("consulta_credito_realizada", "false"),
        ("consulta_credito_provedor", "nenhum"),
        ("restricao_financeira", "false"),
    ]
    try:
        _preparar(
            db_session,
            telefone,
            [("tipos_produto", "relogio_ponto"), ("software_controle_ponto", "nenhum")] + internas,
        )

        chaves = {c["chave"] for c in _campos(client, telefone)}
        assert chaves == {"software_controle_ponto"}
        for chave, _ in internas:
            assert chave not in chaves
    finally:
        _limpar(db_session, telefone)


def test_so_aparecem_campos_aplicaveis_ao_produto(client, db_session):
    """`software_controle_acesso` não se aplica a relógio de ponto, mesmo capturado."""
    telefone = "5511999985203"
    try:
        _preparar(
            db_session,
            telefone,
            [
                ("tipos_produto", "relogio_ponto"),
                ("software_controle_ponto", "TOTVS"),
                ("software_controle_acesso", "EVO"),
            ],
        )

        chaves = {c["chave"] for c in _campos(client, telefone)}
        assert "software_controle_ponto" in chaves
        assert "software_controle_acesso" not in chaves
    finally:
        _limpar(db_session, telefone)


def test_sem_tipo_de_produto_identificado_lista_fica_vazia(client, db_session):
    """Sem produto não há catálogo aplicável, então não há o que mostrar."""
    telefone = "5511999985204"
    try:
        _preparar(db_session, telefone, [("nome_contato", "Fulano")])
        assert _campos(client, telefone) == []
    finally:
        _limpar(db_session, telefone)


def test_valor_em_branco_nao_conta_como_capturado(client, db_session):
    telefone = "5511999985205"
    try:
        _preparar(
            db_session,
            telefone,
            [("tipos_produto", "relogio_ponto"), ("software_controle_ponto", "   ")],
        )
        assert _campos(client, telefone) == []
    finally:
        _limpar(db_session, telefone)
