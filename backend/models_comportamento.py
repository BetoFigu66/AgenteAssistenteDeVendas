"""
Comportamento derivado do estado próprio de entidades do domínio.

Separado de `models.py` de propósito: um diff em `models.py` continua
significando "mudou estrutura de tabela"; um diff aqui significa "mudou uma
regra". Os métodos deste módulo só podem ler atributos/relationships já
carregados do próprio objeto — nada de sessão de banco, nada de colaboradores
externos (catálogo, outros serviços). Isso resolve Feature Envy sem reabrir a
porta para a entidade virar um novo "faz-tudo" (ver
docs/arquitetura_motor_conversacao_2026-07.md §7, sobre por que
`catalogo_campos.py::Pergunta` continua sem conhecer ORM).
"""

from __future__ import annotations

from datetime import datetime
from typing import Mapping, Optional

from utils.datetime_utils import utc_now

# Chave de AtendimentoInfo onde o tipo de produto de interesse é registrado hoje
# (backend/services/processador.py::_atualizar_infos_atendimento). Ainda não
# migrado para ItemAtendimento.produto_id (ver risco/decisão #1 em §8 do plano
# de MVP Continuidade).
_CHAVE_TIPOS_PRODUTO = "tipos_produto"


class ComportamentoAtendimento:
    """Mixin com derivações puras do que já foi capturado num Atendimento.

    Depende só de `.informacoes` (chave/valor) e `.itens` (modelo_id) por duck
    typing — funciona tanto na `Atendimento` real (models.py) quanto em stubs
    de teste que tenham essa mesma forma.
    """

    def tipo_produto_atual(self) -> Optional[str]:
        """Tipo de produto de interesse do atendimento, se já identificado."""
        for info in self.informacoes:
            if info.chave == _CHAVE_TIPOS_PRODUTO and info.valor:
                primeiro = info.valor.split(",")[0].strip()
                return primeiro or None
        return None

    def valores_capturados(self) -> Mapping[str, str]:
        """Snapshot chave -> valor de tudo já capturado em `AtendimentoInfo`."""
        return {info.chave: info.valor for info in self.informacoes if info.valor is not None}

    def modelo_ja_resolvido(self) -> bool:
        """True se algum `ItemAtendimento` do atendimento já tem `modelo_id` resolvido.

        `modelo_produto` não passa por `AtendimentoInfo` — resolve direto para uma
        linha real do catálogo (ver `Pergunta.destino` em `catalogo_campos.py`).
        """
        return any(item.modelo_id is not None for item in self.itens)

    def registrar_ultima_mensagem_em(self, quando: Optional[datetime] = None) -> None:
        """Atualiza o timestamp da última mensagem do cliente (REQ-016 T-A3)."""
        self.ultima_mensagem_at = quando or utc_now()
