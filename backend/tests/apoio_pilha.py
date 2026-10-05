"""Apoio para testes que montam um atendimento "no meio da coleta" por fora do fluxo.

Com a pilha de perguntas pendentes, a resposta solta do cliente só é lida contra uma
pergunta que o sistema de fato fez (`services/conversacao/pilha.py`). Um teste que
resolve o modelo direto no banco pula o turno em que o sistema faria a pergunta
seguinte; este helper faz essa pergunta, do mesmo jeito que a Finalizando faria.
"""

from services.conversacao.acoes import ContextoAcao
from services.conversacao.campos_pendentes import proxima_pergunta
from services.conversacao.estados.finalizando import perguntar_campo


def registrar_proxima_pergunta(db_session, atendimento):
    """Registra na pilha a pergunta que a Finalizando faria agora. Devolve o campo."""
    db_session.refresh(atendimento)
    campo = proxima_pergunta(atendimento)
    if campo is None:
        return None
    ctx = ContextoAcao(
        db=db_session,
        telefone="",
        conteudo="",
        identificacao=None,
        resultado_class=None,
        processador=None,
        atendimento=atendimento,
    )
    perguntar_campo(ctx, campo)
    db_session.commit()
    return campo
