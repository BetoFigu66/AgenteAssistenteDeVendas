"""
Dúvidas do cliente que ficaram sem resposta automática (decisão do Beto, 11/10/2026).

Uma ação `exclusivo` do motor descarta o resto da mensagem. As que sobraram depois que a
captura de CPF/CNPJ deixou de ser exclusiva (pedido de atendente, reclamação, projeto
complexo, confirmação do resumo, "não" ao fechamento, resposta só ao nome) passam o
atendimento a um humano ou o encerram, então a dúvida que vinha junto não tem um turno
seguinte do agente para ser respondida. Ela é registrada em `duvidas_pendentes` e
mostrada ao operador, que a responde e a marca como resolvida
(`POST /api/duvidas-pendentes/{id}/resolver`).
"""

from __future__ import annotations

from typing import Optional

from models import DuvidaPendente, StatusDuvida
from sqlalchemy.orm import Session
from utils.datetime_utils import utc_now

from services.classificador import Intencao

from .acoes import ContextoAcao

# Intenções de quem pergunta algo que o agente responderia se a mensagem não tivesse caído
# numa ação exclusiva.
INTENCOES_DUVIDA = frozenset(
    {
        Intencao.PERGUNTAR_PRODUTO,
        Intencao.PERGUNTAR_PRECO,
        Intencao.PERGUNTAR_PRAZO,
        Intencao.PERGUNTAR_DISPONIBILIDADE,
        Intencao.PEDIR_CATALOGO,
        Intencao.FORA_CONTEXTO,
    }
)


def registrar_descartada(ctx: ContextoAcao, acao_exclusiva: str) -> Optional[DuvidaPendente]:
    """Chamado pelo motor depois de rodar uma ação exclusiva: registra a dúvida que a
    mensagem trazia, se trazia uma e se há atendimento onde pendurá-la."""
    if ctx.atendimento is None or ctx.resultado_class is None:
        return None
    intencao = next((i for i in ctx.resultado_class.intencoes if i in INTENCOES_DUVIDA), None)
    if intencao is None:
        return None
    duvida = DuvidaPendente(
        atendimento_id=ctx.atendimento.id,
        mensagem_id=ctx.mensagem_id,
        texto=ctx.conteudo,
        intencao=intencao.value,
        acao_exclusiva=acao_exclusiva,
    )
    ctx.db.add(duvida)
    ctx.db.commit()
    if ctx.dlog:
        ctx.dlog.log("duvida_pendente", f"{intencao.value} sem resposta ({acao_exclusiva}) → operador")
    return duvida


def pendentes(db: Session, atendimento_id: int) -> list[DuvidaPendente]:
    return (
        db.query(DuvidaPendente)
        .filter_by(atendimento_id=atendimento_id, status=StatusDuvida.PENDENTE.value)
        .order_by(DuvidaPendente.criado_em)
        .all()
    )


def resolver(db: Session, duvida: DuvidaPendente, usuario_id: Optional[int]) -> DuvidaPendente:
    duvida.status = StatusDuvida.RESOLVIDA.value
    duvida.resolvido_em = utc_now()
    duvida.resolvido_por_id = usuario_id
    db.commit()
    db.refresh(duvida)
    return duvida
