"""Camada de Estado (GoF State) do motor de conversação — o que cada Fase FAZ.

Complementa `services/conversacao/regras_*.py` (que decide SE uma Ação dispara para um par
Intenção×Fase, via o Motor em `motor.py`) sem substituí-lo: os builders de `RegraIntencao`
continuam decidindo o roteamento; quando a lógica é específica de uma Fase, o builder
delega para o `EstadoAtendimento` correspondente em vez de para `ProcessadorMensagem`
diretamente — corrige a violação de GRASP Information Expert em que o comportamento da
fase Finalizando morava no orquestrador genérico (`ProcessadorMensagem`, ~2100 linhas,
anti-padrão "Bloated Controller").

Princípio: `regras_*.py` = roteamento, `estados/*.py` = comportamento. Infraestrutura
genuinamente cross-cutting (persistência de `AtendimentoInfo`, geração de resposta,
escalonamento, RAG/QA, CNPJ/CPF) continua em `ProcessadorMensagem` — os Estados chamam
`ctx.processador._metodo_infra(...)` para isso, como as Regras já fazem hoje.

Ver `docs/arquitetura_motor_conversacao_2026-07.md` (§7) para o racional completo.
"""

from .base import EstadoAtendimento
from .esclarecendo import ESCLARECENDO, EsclarecendoState
from .finalizando import FINALIZANDO, FinalizandoState

__all__ = [
    "EstadoAtendimento",
    "EsclarecendoState",
    "ESCLARECENDO",
    "FinalizandoState",
    "FINALIZANDO",
]
