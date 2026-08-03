"""`EstadoAtendimento` — base das classes de Fase (State, GoF).

Cada Fase do atendimento (`FaseAtendimento`) com comportamento próprio ganha uma subclasse
concreta (`EsclarecendoState`, `FinalizandoState`, ...). O único método concreto
compartilhado (`transicionar_para`) existe porque duas transições reais já duplicavam o
mesmo boilerplate (mutar `atendimento.fase`, commitar, registrar evento de auditoria) — não
é um "Template Method" no sentido GoF (não há passo genérico com hook sobrescrito por
subclasse hoje). É rotulado como o que é — um helper de infraestrutura de fase — para não
sugerir um ponto de variação que não existe (adicionar hooks vazios só para completar o
padrão seria a mesma abstração especulativa que este redesenho corrige).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from models import FaseAtendimento, TipoEventoAtendimento

from services import atendimentos as atendimentos_svc
from services.conversacao.acoes import ContextoAcao, RespostaFragmento


class EstadoAtendimento(ABC):
    """Fase do atendimento com comportamento próprio."""

    fase: ClassVar[FaseAtendimento]

    @abstractmethod
    async def tratamento_principal(self, ctx: ContextoAcao) -> RespostaFragmento:
        """O que esta Fase faz com a mensagem atual, quando chamada como "ação padrão"
        (wildcard) do registro de Regras da Fase — ver `services/conversacao/motor.py`."""
        ...

    def transicionar_para(self, ctx: ContextoAcao, nova_fase: FaseAtendimento, motivo: str) -> None:
        """Muda `atendimento.fase`, commita e registra o evento de auditoria."""
        atendimento = ctx.atendimento
        fase_anterior = atendimento.fase.value
        atendimento.fase = nova_fase
        ctx.db.commit()
        atendimentos_svc.registrar_evento_atendimento(
            ctx.db,
            atendimento,
            tipo=TipoEventoAtendimento.FASE_ALTERADA,
            ator="sistema:motor_conversacao",
            estado_anterior=fase_anterior,
            estado_novo=nova_fase.value,
            motivo=motivo,
        )
        if ctx.dlog:
            ctx.dlog.log("fase", f"{fase_anterior} → {nova_fase.value} (atendimento id={atendimento.id})")
