"""Testes de `RetrievalService` (REQ-003.2) — cobertura zero antes desta Fase 3.

Usa a base real (mesma convenção dos demais testes deste projeto: não mocka o banco,
só o `EmbeddingProvider`) — insere documentos temporários em `documentos_conhecimento`
com vetores sintéticos e controláveis (não depende de embeddings reais de rede), e limpa
tudo ao final. Vetores ortogonais/idênticos dão similaridade de cosseno previsível
(1.0 ou 0.0), o que permite testar de forma determinística: ordenação por score, filtro de
`score_minimo`, `top_k`, filtro por `tipo`/`tipos` e `apenas_ativos`.

Não há pytest-asyncio instalado no projeto — corrotinas rodam via `asyncio.run(...)`.
"""

import asyncio

import pytest
from config import settings
from database import Database
from models import DocumentoConhecimento
from services.rag.retrieval import RetrievalService
from sqlalchemy import create_engine

_DIM = 1536
_PREFIXO_TESTE = "test_retrieval_service:"


def _vetor_base(indice: int) -> list[float]:
    """Vetor "one-hot" — dá cosseno 1.0 contra si mesmo e 0.0 contra outro índice."""
    v = [0.0] * _DIM
    v[indice] = 1.0
    return v


class _EmbeddingProviderFake:
    """Ignora o texto da query e sempre devolve o vetor configurado no teste —
    o objetivo aqui é testar a consulta SQL/filtros do `RetrievalService`, não a
    qualidade semântica de um embedding real."""

    def __init__(self, vetor: list[float]):
        self._vetor = vetor

    async def embed_um(self, texto: str) -> list[float]:
        return self._vetor

    async def embed(self, textos):
        raise NotImplementedError

    @property
    def nome(self) -> str:
        return "fake"

    @property
    def modelo(self) -> str:
        return "fake-model"

    @property
    def dimensoes(self) -> int:
        return _DIM


@pytest.fixture
def engine():
    return create_engine(settings.DATABASE_URL, future=True)


@pytest.fixture
def db_session():
    database = Database()
    with database.get_session() as session:
        yield session


def _criar_doc(db_session, *, sufixo, tipo, embedding, ativo=True):
    doc = DocumentoConhecimento(
        id_externo=f"{_PREFIXO_TESTE}{sufixo}",
        id_documento_origem=f"{_PREFIXO_TESTE}origem",
        tipo=tipo,
        titulo=f"Documento de teste {sufixo}",
        conteudo="Conteúdo de teste.",
        metadados={},
        conteudo_hash=f"hash-{sufixo}",
        embedding=embedding,
        ativo=ativo,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc


def _limpar(db_session):
    db_session.query(DocumentoConhecimento).filter(
        DocumentoConhecimento.id_externo.like(f"{_PREFIXO_TESTE}%")
    ).delete(synchronize_session=False)
    db_session.commit()


def test_retorna_ordenado_por_score_e_filtra_score_minimo(db_session, engine):
    """Doc alinhado com a query (score=1.0) deve vir primeiro e passar; doc ortogonal
    (score=0.0) deve ser filtrado pelo score_minimo padrão (0.70)."""
    try:
        _criar_doc(db_session, sufixo="alinhado", tipo="produto", embedding=_vetor_base(0))
        _criar_doc(db_session, sufixo="ortogonal", tipo="produto", embedding=_vetor_base(1))

        servico = RetrievalService(
            embedding_provider=_EmbeddingProviderFake(_vetor_base(0)),
            engine=engine,
            top_k_padrao=10,
            score_minimo_padrao=0.70,
        )
        resultados = asyncio.run(servico.buscar(query="qualquer coisa", tipo="produto"))

        ids_externos = [r.id_externo for r in resultados]
        assert f"{_PREFIXO_TESTE}alinhado" in ids_externos
        assert f"{_PREFIXO_TESTE}ortogonal" not in ids_externos
        assert resultados[0].score == pytest.approx(1.0, abs=1e-6)
    finally:
        _limpar(db_session)


def test_score_minimo_explicito_sobrepoe_o_padrao(db_session, engine):
    """Passar `score_minimo=0.0` na chamada deve devolver também o doc ortogonal.

    `top_k` bem acima do total de linhas da tabela (há dados reais de produção
    convivendo com os docs de teste) garante que o LIMIT do SQL não corte o doc
    ortogonal antes do filtro de score rodar."""
    try:
        _criar_doc(db_session, sufixo="alinhado2", tipo="produto", embedding=_vetor_base(0))
        _criar_doc(db_session, sufixo="ortogonal2", tipo="produto", embedding=_vetor_base(1))

        servico = RetrievalService(
            embedding_provider=_EmbeddingProviderFake(_vetor_base(0)),
            engine=engine,
            top_k_padrao=100_000,
            score_minimo_padrao=0.70,
        )
        resultados = asyncio.run(servico.buscar(query="x", tipo="produto", score_minimo=0.0))

        ids_externos = {r.id_externo for r in resultados}
        assert {f"{_PREFIXO_TESTE}alinhado2", f"{_PREFIXO_TESTE}ortogonal2"} <= ids_externos
    finally:
        _limpar(db_session)


def test_top_k_limita_quantidade_de_resultados(db_session, engine):
    try:
        for i in range(5):
            _criar_doc(db_session, sufixo=f"topk{i}", tipo="produto", embedding=_vetor_base(0))

        servico = RetrievalService(
            embedding_provider=_EmbeddingProviderFake(_vetor_base(0)),
            engine=engine,
            top_k_padrao=4,
            score_minimo_padrao=0.0,
        )
        resultados = asyncio.run(servico.buscar(query="x", tipo="produto", top_k=2))
        assert len(resultados) == 2
    finally:
        _limpar(db_session)


def test_filtra_por_tipo(db_session, engine):
    """A tabela real já tem muitos documentos `tipo=produto` de produção — por isso a
    checagem é por pertencimento (`in`/`not in`), não por igualdade de conjunto."""
    try:
        _criar_doc(db_session, sufixo="produto1", tipo="produto", embedding=_vetor_base(0))
        _criar_doc(db_session, sufixo="faq1", tipo="faq", embedding=_vetor_base(0))

        servico = RetrievalService(
            embedding_provider=_EmbeddingProviderFake(_vetor_base(0)),
            engine=engine,
            top_k_padrao=100_000,
            score_minimo_padrao=0.0,
        )
        so_produto = {r.id_externo for r in asyncio.run(servico.buscar(query="x", tipo="produto"))}
        so_faq = {r.id_externo for r in asyncio.run(servico.buscar(query="x", tipo="faq"))}
        sem_filtro = {r.id_externo for r in asyncio.run(servico.buscar(query="x", tipo=None))}

        assert f"{_PREFIXO_TESTE}produto1" in so_produto
        assert f"{_PREFIXO_TESTE}faq1" not in so_produto
        assert f"{_PREFIXO_TESTE}faq1" in so_faq
        assert f"{_PREFIXO_TESTE}produto1" not in so_faq
        assert {f"{_PREFIXO_TESTE}produto1", f"{_PREFIXO_TESTE}faq1"} <= sem_filtro
    finally:
        _limpar(db_session)


def test_ignora_documento_inativo(db_session, engine):
    try:
        _criar_doc(db_session, sufixo="ativo1", tipo="produto", embedding=_vetor_base(0), ativo=True)
        _criar_doc(db_session, sufixo="inativo1", tipo="produto", embedding=_vetor_base(0), ativo=False)

        servico = RetrievalService(
            embedding_provider=_EmbeddingProviderFake(_vetor_base(0)),
            engine=engine,
            top_k_padrao=10,
            score_minimo_padrao=0.0,
        )
        resultados = asyncio.run(servico.buscar(query="x", tipo="produto"))
        ids_externos = {r.id_externo for r in resultados}
        assert f"{_PREFIXO_TESTE}ativo1" in ids_externos
        assert f"{_PREFIXO_TESTE}inativo1" not in ids_externos
    finally:
        _limpar(db_session)


def test_query_vazia_retorna_lista_vazia(db_session, engine):
    servico = RetrievalService(
        embedding_provider=_EmbeddingProviderFake(_vetor_base(0)),
        engine=engine,
    )
    assert asyncio.run(servico.buscar(query="   ")) == []
