"""Testes da resolução de modelo usando atributos adicionais genéricos (D6)."""

import asyncio

import pytest
from database import Database
from models import (
    Atendimento,
    AtendimentoInfo,
    AtributoAdicionalModelo,
    Contato,
    FaseAtendimento,
    ItemAtendimento,
    Modelo,
    ModoOperacao,
    Produto,
    StatusAtendimento,
)
from services.atendimentos import proximo_numero_atendimento_cliente
from services.classificador import EntidadesExtraidas, ResultadoClassificacao
from services.conversacao.acoes import ContextoAcao
from services.conversacao.estados.finalizando import FINALIZANDO
from services.processador import ProcessadorMensagem
from sqlalchemy.orm import Session


def _ctx(processador: ProcessadorMensagem, session: Session, telefone: str, atendimento: Atendimento,
         resultado: ResultadoClassificacao) -> ContextoAcao:
    """`_tentar_resolver_modelo` virou `FinalizandoState._resolver_modelo(ctx)` (Etapa 1 do
    redesenho State pattern) — monta um `ContextoAcao` mínimo, mesmo padrão de
    `tests/test_motor_acoes.py::_ctx()` (identificação não é usada por este método)."""
    return ContextoAcao(
        db=session,
        telefone=telefone,
        conteudo="",
        identificacao=object(),
        resultado_class=resultado,
        processador=processador,
        atendimento=atendimento,
    )


@pytest.fixture
def processador():
    return ProcessadorMensagem()


def _session():
    db = Database()
    return db.get_session()


def _cleanup_telefone(session: Session, telefone: str) -> None:
    """Remove contato e atendimentos relacionados ao telefone de teste."""
    contato = session.query(Contato).filter(Contato.telefone == telefone).first()
    if not contato:
        return
    for atendimento in list(contato.atendimentos):
        session.query(ItemAtendimento).filter(ItemAtendimento.atendimento_id == atendimento.id).delete(
            synchronize_session=False
        )
        session.query(AtendimentoInfo).filter(AtendimentoInfo.atendimento_id == atendimento.id).delete(
            synchronize_session=False
        )
        session.delete(atendimento)
    session.delete(contato)
    session.commit()


def _setup_atendimento(session: Session, telefone: str, produto: Produto) -> Atendimento:
    _cleanup_telefone(session, telefone)
    contato = Contato(telefone=telefone, nome="Teste")
    session.add(contato)
    session.flush()
    numero = proximo_numero_atendimento_cliente(session, contato.id)
    atendimento = Atendimento(
        contato_id=contato.id,
        status=StatusAtendimento.ATIVO,
        fase=FaseAtendimento.FINALIZANDO,
        modo_operacao=ModoOperacao.AGENTE,
        numero_atendimento_cliente=numero,
    )
    session.add(atendimento)
    session.flush()
    session.add(AtendimentoInfo(atendimento_id=atendimento.id, chave="tipos_produto", valor="relogio_ponto"))
    session.add(ItemAtendimento(atendimento_id=atendimento.id, produto_id=produto.id, quantidade=1))
    session.commit()
    return atendimento


def _criar_modelo_teste(session: Session, produto: Produto, codigo: str, descricao: str, atributos: dict[str, str]):
    antigo = session.query(Modelo).filter_by(codigo=codigo).first()
    if antigo:
        session.delete(antigo)
        session.commit()
    modelo = Modelo(
        produto_id=produto.id,
        codigo=codigo,
        descricao=descricao,
        ativo=True,
    )
    session.add(modelo)
    session.flush()
    for chave, valor in atributos.items():
        session.add(AtributoAdicionalModelo(modelo_id=modelo.id, chave=chave, valor=valor))
    session.commit()
    return modelo


def _resultado(atributos: dict[str, str]) -> ResultadoClassificacao:
    return ResultadoClassificacao(
        intencoes=[],
        confianca=1.0,
        confianca_nivel="alta",
        entidades=EntidadesExtraidas(
            tipos_produto=["relogio_ponto"],
            atributos=atributos,
        ),
        origem="regra",
    )


def _produto_teste(session: Session, descricao: str) -> Produto:
    produto = session.query(Produto).filter_by(descricao=descricao).first()
    if produto is None:
        produto = Produto(descricao=descricao, ativo=True)
        session.add(produto)
        session.flush()
    return produto


def test_resolve_modelo_por_atributo_tecnologia_leitura(processador):
    telefone = "55119999999001"
    with _session() as session:
        try:
            produto = _produto_teste(session, "Produto Teste Atributos D6")
            _criar_modelo_teste(
                session, produto, "TESTE-ATTR-001", "Modelo Teste Atributo",
                {"tecnologia_leitura": "biometria"},
            )
            atendimento = _setup_atendimento(session, telefone, produto)
            resultado = _resultado({"tecnologia_leitura": "biometria"})

            ctx = _ctx(processador, session, telefone, atendimento, resultado)
            res = asyncio.run(FINALIZANDO._resolver_modelo(ctx))
            assert res is False  # False = resolvido
            assert atendimento.itens[0].modelo_id is not None
        finally:
            _cleanup_telefone(session, telefone)


def test_nao_resolve_modelo_quando_atributo_nao_casa(processador):
    telefone = "55119999999002"
    with _session() as session:
        try:
            produto = _produto_teste(session, "Produto Teste Atributos D6 2")
            _criar_modelo_teste(
                session, produto, "TESTE-ATTR-002", "Modelo Teste Cartão",
                {"tecnologia_leitura": "cartao"},
            )
            atendimento = _setup_atendimento(session, telefone, produto)
            # Atributo inexistente no catálogo de teste.
            resultado = _resultado({"tecnologia_leitura": "nao_existe_xyz"})

            ctx = _ctx(processador, session, telefone, atendimento, resultado)
            res = asyncio.run(FINALIZANDO._resolver_modelo(ctx))
            assert res is True  # True = tentou mas não resolveu
            assert atendimento.itens[0].modelo_id is None
        finally:
            _cleanup_telefone(session, telefone)


def test_nao_resolve_modelo_sem_nenhum_sinal_mesmo_com_produto_ja_conhecido(processador):
    """Regressão: sem marca/aplicação/atributo na mensagem, `_tentar_resolver_modelo` não
    pode escolher um modelo arbitrário (`.first()`) só porque o tipo de produto já é
    conhecido — precisa continuar pedindo esclarecimento."""
    telefone = "55119999999003"
    with _session() as session:
        try:
            produto = _produto_teste(session, "Produto Teste Sem Sinal")
            _criar_modelo_teste(
                session, produto, "TESTE-SEM-SINAL-001", "Modelo A",
                {"tecnologia_leitura": "biometria"},
            )
            _criar_modelo_teste(
                session, produto, "TESTE-SEM-SINAL-002", "Modelo B",
                {"tecnologia_leitura": "facial"},
            )
            atendimento = _setup_atendimento(session, telefone, produto)
            # Nenhum sinal (marca/aplicação/atributo) na entidade extraída da mensagem.
            resultado = _resultado({})

            ctx = _ctx(processador, session, telefone, atendimento, resultado)
            res = asyncio.run(FINALIZANDO._resolver_modelo(ctx))
            assert res is False  # False = não tentou (mensagem não trouxe sinal)
            assert atendimento.itens[0].modelo_id is None
        finally:
            _cleanup_telefone(session, telefone)


def test_resolve_modelo_restrito_ao_produto_do_item_ja_criado(processador):
    """Regressão: a resolução de modelo deve ficar restrita ao produto_id do item já
    existente no atendimento, mesmo que outro produto do catálogo também tenha um
    modelo com o mesmo atributo pedido (a versão anterior derivava produto_ids por
    matching fuzzy de texto, podendo casar com o produto errado)."""
    telefone = "55119999999004"
    with _session() as session:
        try:
            produto_correto = _produto_teste(session, "Produto Teste Dup A")
            produto_errado = _produto_teste(session, "Produto Teste Dup B")
            modelo_correto = _criar_modelo_teste(
                session, produto_correto, "TESTE-DUP-001", "Modelo Correto",
                {"tecnologia_leitura": "biometria"},
            )
            _criar_modelo_teste(
                session, produto_errado, "TESTE-DUP-002", "Modelo Errado",
                {"tecnologia_leitura": "biometria"},
            )
            atendimento = _setup_atendimento(session, telefone, produto_correto)
            resultado = _resultado({"tecnologia_leitura": "biometria"})

            ctx = _ctx(processador, session, telefone, atendimento, resultado)
            res = asyncio.run(FINALIZANDO._resolver_modelo(ctx))
            assert res is False  # resolvido
            assert atendimento.itens[0].modelo_id == modelo_correto.id
            assert atendimento.itens[0].produto_id == produto_correto.id
        finally:
            _cleanup_telefone(session, telefone)
