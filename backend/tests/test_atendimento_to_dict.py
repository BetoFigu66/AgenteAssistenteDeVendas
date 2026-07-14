"""Regressão da Fase H (H1): `Atendimento.to_dict()` precisa serializar `fase` — ficou de
fora quando a coluna foi adicionada na Fase A, e o painel (REQ-010) depende dela para
exibir a fase da conversa."""

from database import Database
from models import FaseAtendimento
from services import atendimentos as atendimentos_svc
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.identificador import criar_contato_sem_empresa


def test_to_dict_inclui_fase():
    telefone = "5511999983001"
    database = Database()
    with database.get_session() as db:
        try:
            contato = criar_contato_sem_empresa(db, telefone, nome="Teste H1")
            atendimento = atendimentos_svc.obter_ou_criar_atendimento(db, contato)

            dado = atendimento.to_dict()

            assert "fase" in dado
            assert dado["fase"] == FaseAtendimento.ESCLARECENDO.value
        finally:
            db.commit()
            apagar_dados_telefone(db, telefone)
            db.commit()
