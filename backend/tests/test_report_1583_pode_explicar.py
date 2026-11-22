"""Report #1583: "não conheço, pode explicar?" em resposta a "Você conhece esses catracas?".

O bot tinha feito duas perguntas (conhece as marcas? / faixa de pessoas). O cliente
respondeu à primeira pedindo explicação, e o bot só repetiu a segunda: o "pode explicar?"
solto não era lido como pedido de detalhes (a regra exigia "explicar mais/melhor"), as
regras ficavam sem intenção, o LLM devolvia só NEGAR e a dúvida se perdia.

Ponta a ponta via `processar()`, no mesmo padrão de `test_processador_nome_perfil.py`.
"""

import asyncio

import pytest
from database import Database
from models import AtendimentoInfo, Contato, ModoExecucao, ProcessamentoMensagem
from services.classificador import Intencao, classificar_por_regras, pedido_de_detalhes
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.parametro_service import ParametroService
from services.processador import ProcessadorMensagem

# CPF sintético válido (passa no dígito verificador), sem relação com pessoa real.
_CPF_SINTETICO = "52998224725"
_PERGUNTA_FAIXA = "Qual a faixa de pessoas que vão usar a catraca?"


@pytest.mark.parametrize(
    "texto",
    [
        "não conheço, pode explicar?",
        "Não conheço. Poderia me explicar?",
        "não, me explica?",
        "consegue explicar?",
    ],
)
def test_pode_explicar_solto_e_pedido_de_detalhes(texto):
    assert pedido_de_detalhes(texto)
    assert Intencao.PERGUNTAR_PRODUTO in [i for i, _ in classificar_por_regras(texto)]


@pytest.fixture
def db_session(monkeypatch):
    monkeypatch.setattr(ParametroService, "modo_execucao", lambda self: ModoExecucao.EXECUCAO_NORMAL)
    database = Database()
    with database.get_session() as session:
        yield session
        session.rollback()


def _limpar(db_session, telefone):
    db_session.commit()
    apagar_dados_telefone(db_session, telefone)
    db_session.commit()


def test_nao_conheco_pode_explicar_responde_a_duvida(db_session):
    telefone = "+5500900001583"
    processador = ProcessadorMensagem()
    _limpar(db_session, telefone)
    try:
        for texto in ("olá", f"Maria Cristina CPF {_CPF_SINTETICO}", "quais catracas vocês trabalham?"):
            asyncio.run(processador.processar(db_session, telefone, texto))
        resultado = asyncio.run(processador.processar(db_session, telefone, "não conheço, pode explicar?"))

        proc = db_session.get(ProcessamentoMensagem, resultado.processamento_id)
        assert Intencao.PERGUNTAR_PRODUTO.value in proc.intencoes
        # A dúvida é respondida (a base não tem trecho para "catraca", então o catálogo
        # explica a linha) e só depois a pergunta da faixa volta.
        assert proc.template_usado.startswith("MODELOS_DO_PRODUTO")
        assert "Control-ID" in resultado.resposta or "Topdata" in resultado.resposta
        assert resultado.partes_resposta[-1].endswith(_PERGUNTA_FAIXA)

        db_session.expire_all()
        contato = db_session.query(Contato).filter_by(telefone=telefone).first()
        info = (
            db_session.query(AtendimentoInfo)
            .filter(
                AtendimentoInfo.atendimento_id == contato.atendimentos[0].id,
                AtendimentoInfo.chave == "conhece_marcas",
            )
            .first()
        )
        assert info is not None and info.valor == "não"
        print("\nRESPOSTA:", resultado.resposta, "\nTEMPLATE:", proc.template_usado)
    finally:
        _limpar(db_session, telefone)
