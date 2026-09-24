"""Limpeza por telefone remove a empresa órfã, mas nunca a compartilhada (achado B4).

A limpeza apagava contato, atendimento e mensagens e deixava a `Empresa` criada pela
consulta de CNPJ de pé. Na rodada seguinte, um cenário de "CNPJ novo" passava a
exercitar em silêncio o caminho de "empresa já conhecida", e a suíte quebrava com
violação de unicidade em `ix_empresas_cnpj`.

A remoção é condicional de propósito: a mesma empresa pode estar ligada a contatos e
atendimentos de OUTRO telefone (dois funcionários escrevendo de celulares diferentes),
e apagá-la junto destruiria dado de outra conversa. Este arquivo fixa as duas metades da
regra e a ordem de remoção exigida pelas FKs not-null de `atividades_empresa` e
`socios_empresa`.
"""

import pytest
from database import Database
from models import (
    Atendimento,
    AtividadeEmpresa,
    Contato,
    Empresa,
    FaseAtendimento,
    SocioEmpresa,
    StatusAtendimento,
)
from services.dev_limpeza_telefone import apagar_dados_telefone

_TELEFONE = "+5511999944001"
_TELEFONE_OUTRO = "+5511999944002"
_CNPJ = "99.888.777/0001-66"


@pytest.fixture
def db_session():
    database = Database()
    with database.get_session() as session:
        yield session


def _limpar_tudo(db):
    """Estado inicial conhecido: apaga os dois telefones e a empresa residual."""
    db.commit()
    apagar_dados_telefone(db, _TELEFONE)
    apagar_dados_telefone(db, _TELEFONE_OUTRO)
    db.commit()
    empresa = db.query(Empresa).filter_by(cnpj=_CNPJ).first()
    if empresa:
        db.query(AtividadeEmpresa).filter_by(empresa_id=empresa.id).delete()
        db.query(SocioEmpresa).filter_by(empresa_id=empresa.id).delete()
        db.query(Contato).filter_by(empresa_id=empresa.id).delete()
        db.query(Atendimento).filter_by(empresa_id=empresa.id).delete()
        db.query(Empresa).filter_by(id=empresa.id).delete()
        db.commit()


def _criar_empresa(db) -> Empresa:
    empresa = Empresa(cnpj=_CNPJ, nome="Empresa de Teste B4 Ltda")
    db.add(empresa)
    db.flush()
    db.add(AtividadeEmpresa(empresa_id=empresa.id, codigo="4321-5/00", descricao="Teste", is_principal=True))
    db.add(SocioEmpresa(empresa_id=empresa.id, nome="Sócio de Teste", qualificacao="Administrador"))
    db.flush()
    return empresa


def _criar_contato_com_atendimento(db, telefone: str, empresa: Empresa) -> Contato:
    contato = Contato(telefone=telefone, nome=f"Contato {telefone}", empresa_id=empresa.id)
    db.add(contato)
    db.flush()
    atendimento = Atendimento(
        contato_id=contato.id,
        empresa_id=empresa.id,
        numero_atendimento_cliente=1,
        status=StatusAtendimento.ATIVO,
        fase=FaseAtendimento.ESCLARECENDO,
    )
    db.add(atendimento)
    db.flush()
    return contato


def test_empresa_exclusiva_do_telefone_e_removida(db_session):
    """Nada mais aponta para a empresa: ela e suas dependentes saem junto."""
    try:
        _limpar_tudo(db_session)
        empresa = _criar_empresa(db_session)
        empresa_id = empresa.id
        _criar_contato_com_atendimento(db_session, _TELEFONE, empresa)
        db_session.commit()

        resultado = apagar_dados_telefone(db_session, _TELEFONE)
        db_session.commit()

        assert resultado["removidos"]["empresas"] == 1
        assert resultado["removidos"]["atividades_empresa"] == 1
        assert resultado["removidos"]["socios_empresa"] == 1
        assert resultado["empresa_ids_removidas"] == [empresa_id]
        assert resultado["empresa_ids_preservadas"] == []

        assert db_session.query(Empresa).filter_by(id=empresa_id).first() is None
        assert db_session.query(AtividadeEmpresa).filter_by(empresa_id=empresa_id).count() == 0
        assert db_session.query(SocioEmpresa).filter_by(empresa_id=empresa_id).count() == 0
    finally:
        db_session.rollback()
        _limpar_tudo(db_session)


def test_empresa_compartilhada_com_outro_contato_nao_e_removida(db_session):
    """O caso que torna a remoção incondicional inaceitável: apagar a empresa aqui
    destruiria o vínculo do telefone que não foi limpo."""
    try:
        _limpar_tudo(db_session)
        empresa = _criar_empresa(db_session)
        empresa_id = empresa.id
        _criar_contato_com_atendimento(db_session, _TELEFONE, empresa)
        _criar_contato_com_atendimento(db_session, _TELEFONE_OUTRO, empresa)
        db_session.commit()

        resultado = apagar_dados_telefone(db_session, _TELEFONE)
        db_session.commit()

        assert resultado["removidos"]["empresas"] == 0
        assert resultado["removidos"]["atividades_empresa"] == 0
        assert resultado["removidos"]["socios_empresa"] == 0
        assert resultado["empresa_ids_removidas"] == []
        assert resultado["empresa_ids_preservadas"] == [empresa_id]

        assert db_session.query(Empresa).filter_by(id=empresa_id).first() is not None
        # O contato do outro telefone continua de pé e ainda apontando para a empresa.
        outro = db_session.query(Contato).filter_by(telefone=_TELEFONE_OUTRO).first()
        assert outro is not None and outro.empresa_id == empresa_id
        # E o contato limpo realmente saiu, para o teste não passar por não ter limpado nada.
        assert db_session.query(Contato).filter_by(telefone=_TELEFONE).first() is None
    finally:
        db_session.rollback()
        _limpar_tudo(db_session)


def test_limpeza_nao_viola_fk_das_dependentes_da_empresa(db_session):
    """Regressão da ordem: `atividades_empresa`/`socios_empresa` têm FK not-null para
    `empresas`. Invertendo a ordem, o commit estoura IntegrityError em vez de passar."""
    try:
        _limpar_tudo(db_session)
        empresa = _criar_empresa(db_session)
        empresa_id = empresa.id
        _criar_contato_com_atendimento(db_session, _TELEFONE, empresa)
        db_session.commit()

        apagar_dados_telefone(db_session, _TELEFONE)
        db_session.commit()  # é aqui que a FK reclamaria se a ordem estivesse errada

        assert db_session.query(Empresa).filter_by(id=empresa_id).first() is None
    finally:
        db_session.rollback()
        _limpar_tudo(db_session)


def test_telefone_sem_empresa_nao_quebra_nem_inventa_contagem(db_session):
    """Contato sem empresa (PF ou ainda não identificado): as chaves novas existem e
    valem zero, para o formato de `removidos` continuar estável."""
    try:
        _limpar_tudo(db_session)
        contato = Contato(telefone=_TELEFONE, nome="Sem empresa")
        db_session.add(contato)
        db_session.commit()

        resultado = apagar_dados_telefone(db_session, _TELEFONE)
        db_session.commit()

        assert resultado["removidos"]["empresas"] == 0
        assert resultado["removidos"]["atividades_empresa"] == 0
        assert resultado["removidos"]["socios_empresa"] == 0
        assert resultado["removidos"]["contatos"] == 1
        # `main.py` soma os valores de `removidos` para decidir o 404: todos int.
        assert all(isinstance(v, int) for v in resultado["removidos"].values())
    finally:
        db_session.rollback()
        _limpar_tudo(db_session)
