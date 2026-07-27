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
from services.processador import ProcessadorMensagem
from sqlalchemy.orm import Session


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
            modelo = _criar_modelo_teste(
                session, produto, "TESTE-ATTR-001", "Modelo Teste Atributo",
                {"tecnologia_leitura": "biometria"},
            )
            atendimento = _setup_atendimento(session, telefone, produto)
            resultado = _resultado({"tecnologia_leitura": "biometria"})

            res = asyncio.run(processador._tentar_resolver_modelo(session, atendimento, resultado))
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

            res = asyncio.run(processador._tentar_resolver_modelo(session, atendimento, resultado))
            assert res is True  # True = tentou mas não resolveu
            assert atendimento.itens[0].modelo_id is None
        finally:
            _cleanup_telefone(session, telefone)
