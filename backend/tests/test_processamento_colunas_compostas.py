"""Colunas de auditoria que recebem valor COMPOSTO em runtime precisam caber sempre.

Contexto: a divergência B de 2026-09-19 (commit `a94e996`) foi um rótulo de 34 caracteres
numa coluna `String(30)`. O INSERT de auditoria estourava e derrubava `processar()` inteiro,
e o cliente via "Desculpe, tive um problema ao processar sua mensagem". Quem quebrava o turno
era a gravação da auditoria, não a decisão da resposta.

Aquela correção tratou a ocorrência. A revisão de 2026-09-22 apontou que a **classe** do
problema continuava aberta em `template_usado`, e ali é pior: o valor não vem de um conjunto
fechado de rótulos, é montado por concatenação em três pontos que se encadeiam:

- `services/conversacao/motor.py` junta os fragmentos de todas as ações com "+"
- `services/respostas/gerador.py` monta `codigo_composto` com "+"
- `services/conversacao/estados/finalizando.py` compõe dúvida + retomada, e cada lado
  desses já pode ser composto

Três templates reais de `MensagemId` já somam 88 caracteres com os separadores. O quarto
estoura. E o gatilho é justamente a mensagem com várias intenções, que os cenários novos do
testador passaram a exercitar.
"""

import pytest
from database import Database
from models import ProcessamentoMensagem

# Nomes reais de `MensagemId`, os mesmos que a composição usa em produção.
_TEMPLATES_REAIS = [
    "PERGUNTA_CONTINUACAO_ATENDIMENTO",
    "PEDIR_INTERESSE_SISTEMA_NUVEM",
    "RETOMAR_PERGUNTA_PENDENTE",
    "PEDIR_HOMOLOGADO_SOFTWARE",
]


@pytest.fixture
def db_session():
    database = Database()
    with database.get_session() as session:
        yield session


def test_template_usado_suporta_composicao_de_varios_fragmentos(db_session):
    """Uma mensagem com várias intenções compõe vários templates num valor só.

    Sem esta garantia, o turno inteiro do cliente é perdido: o INSERT falha, `processar()`
    levanta e a transação volta atrás, exatamente como na divergência B.
    """
    composto = "+".join(_TEMPLATES_REAIS)
    assert len(composto) > 100, "o teste precisa exceder o limite antigo para ter valor"

    processamento = ProcessamentoMensagem(template_usado=composto)
    db_session.add(processamento)
    criado_id = None
    try:
        db_session.commit()
        db_session.refresh(processamento)
        criado_id = processamento.id
        # Sem truncamento: um campo de auditoria truncado passa a mentir sobre o que o
        # sistema fez, que é o oposto do propósito dele.
        assert processamento.template_usado == composto
    finally:
        db_session.rollback()
        if criado_id is not None:
            db_session.query(ProcessamentoMensagem).filter_by(id=criado_id).delete()
            db_session.commit()
