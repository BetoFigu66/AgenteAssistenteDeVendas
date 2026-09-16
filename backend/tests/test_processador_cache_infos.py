"""Invariante dos escritores de `AtendimentoInfo` (achado P0-2 da auditoria 2026-08).

Dois requisitos que puxam em direções opostas e que precisam valer ao mesmo tempo:

1. **Não commitar no meio do processamento.** Por isso `_salvar_info_atendimento` e
   `_remover_info_atendimento` usam `flush()`, e não `commit()` — uma mensagem que falhe
   na metade não pode deixar meia verdade gravada.
2. **Não deixar cache obsoleto.** `commit()` expirava os objetos da sessão e, de graça,
   forçava a releitura de `Atendimento.informacoes`. Trocar por `flush()` tirou esse
   efeito colateral: a coleção já carregada continuava com o valor antigo, e o bot
   repetia a pergunta que o cliente acabara de responder.

Os testes da coleta ativa (`test_processador_finalizando_coleta_ativa.py`) pegam a
regressão, mas só pelo sintoma conversacional — quem apagasse o `expire` veria sete
falhas obscuras sem ligar uma coisa à outra. Aqui a causa é testada direto.
"""

import pytest
from database import Database
from models import Atendimento
from services import atendimentos as svc
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.identificador import criar_contato_sem_empresa
from services.processador import ProcessadorMensagem


@pytest.fixture
def db_session():
    database = Database()
    with database.get_session() as session:
        yield session


@pytest.fixture
def processador():
    return ProcessadorMensagem()


def _novo_atendimento(db_session, telefone) -> Atendimento:
    contato = criar_contato_sem_empresa(db_session, telefone, nome=None)
    return svc.obter_ou_criar_atendimento(db_session, contato)


def _limpar(db_session, telefone):
    db_session.commit()
    apagar_dados_telefone(db_session, telefone)
    db_session.commit()


def test_salvar_info_torna_valor_visivel_na_colecao_ja_carregada(db_session, processador):
    """O caso exato do P0-2: ler a coleção ANTES de gravar é o que criava o cache."""
    telefone = "5511999977001"
    try:
        atendimento = _novo_atendimento(db_session, telefone)

        # Primeiro acesso: carrega e cacheia a coleção (é o que `campos_pendentes()`
        # fazia na linha 203 de `estados/finalizando.py`).
        assert atendimento.valores_capturados().get("faixa_funcionarios") is None

        processador._salvar_info_atendimento(db_session, atendimento.id, "faixa_funcionarios", "50-100")

        # Sem invalidar o cache, isto continuaria None e a pergunta seria repetida.
        assert atendimento.valores_capturados().get("faixa_funcionarios") == "50-100"
    finally:
        _limpar(db_session, telefone)


def test_sobrescrever_valor_existente_reflete_na_colecao(db_session, processador):
    """O ramo de UPDATE do helper, não só o de INSERT.

    Este passa mesmo sem o `expire`: o UPDATE muta o próprio objeto ORM que já está
    dentro da coleção carregada, então a mudança aparece por identidade. Fica aqui como
    caracterização — pega uma troca futura para `query.update()` em massa, que passaria
    por fora da sessão e recriaria a obsolescência, como acontece no `delete()`."""
    telefone = "5511999977002"
    try:
        atendimento = _novo_atendimento(db_session, telefone)
        processador._salvar_info_atendimento(db_session, atendimento.id, "software_ponto", "nenhum")
        assert atendimento.valores_capturados().get("software_ponto") == "nenhum"

        processador._salvar_info_atendimento(db_session, atendimento.id, "software_ponto", "ahgora")
        assert atendimento.valores_capturados().get("software_ponto") == "ahgora"
    finally:
        _limpar(db_session, telefone)


def test_remover_info_some_da_colecao_ja_carregada(db_session, processador):
    """`query.delete()` é bulk e passa por fora da sessão: sem expire, a linha apagada
    continuaria aparecendo na coleção carregada."""
    telefone = "5511999977003"
    try:
        atendimento = _novo_atendimento(db_session, telefone)
        processador._salvar_info_atendimento(db_session, atendimento.id, "cpf_pendente", "12345678909")
        assert "cpf_pendente" in atendimento.valores_capturados()

        processador._remover_info_atendimento(db_session, atendimento.id, "cpf_pendente")

        assert "cpf_pendente" not in atendimento.valores_capturados()
    finally:
        _limpar(db_session, telefone)


def test_salvar_info_nao_commita(db_session, processador):
    """Guarda o outro lado do invariante: consertar a obsolescência voltando para
    `commit()` reintroduziria o commit parcial que o `flush()` veio remover."""
    telefone = "5511999977004"
    try:
        atendimento = _novo_atendimento(db_session, telefone)
        db_session.commit()  # o atendimento existe; a info abaixo é que não pode persistir

        processador._salvar_info_atendimento(db_session, atendimento.id, "efemero", "x")
        db_session.rollback()

        assert "efemero" not in atendimento.valores_capturados()
    finally:
        _limpar(db_session, telefone)
