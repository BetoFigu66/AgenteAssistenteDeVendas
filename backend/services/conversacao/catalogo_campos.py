"""
Catálogo de campos de qualificação (MVP Continuidade, jul/2026 — passos B1-B4).

Espelha as fichas `CAMPO-xxx` de
`artefatos/analista_de_requisitos/catalogo_conversacao/campos/` em definições
declarativas que o motor de fases (Fase C do plano de MVP — `campos_pendentes()`) vai consumir.

Este módulo não conhece banco de dados nem SQLAlchemy: a regra de
aplicabilidade recebe um snapshot dos valores já capturados (chave -> valor,
ex.: vindo de `AtendimentoInfo`) em vez de objetos ORM, para manter o
catálogo desacoplado da camada de persistência.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

Valores = Mapping[str, str]

# Destinos possíveis de `CampoDef.destino` — onde a Fase C deve gravar o valor capturado.
DESTINO_ATENDIMENTO_INFO = "atendimento_info"
DESTINO_ITEM_ATENDIMENTO_MODELO_ID = "item_atendimento.modelo_id"


def _sempre_aplicavel(tipo_produto: str, valores: Valores) -> bool:
    return True


@dataclass(frozen=True)
class CampoDef:
    """Definição declarativa de um campo de qualificação — espelha uma ficha `CAMPO-xxx`."""

    id_catalogo: str
    chave: str
    produtos_aplicaveis: frozenset[str]
    pergunta: str
    ordem: int
    aplicavel: Callable[[str, Valores], bool] = _sempre_aplicavel
    destino: str = DESTINO_ATENDIMENTO_INFO
    """Onde o valor capturado deve ser persistido (Fase C):

    - `DESTINO_ATENDIMENTO_INFO` (padrão) — grava em `AtendimentoInfo` (chave-valor).
    - `DESTINO_ITEM_ATENDIMENTO_MODELO_ID` — o valor precisa resolver para uma linha
      real do catálogo (`Modelo`) e gravar em `ItemAtendimento.modelo_id`, nunca texto
      livre. Ver risco/decisão #1 em §8 do plano de MVP: `produto` (categoria) já vai
      para `ItemAtendimento`; o modelo específico segue a mesma lógica.
    """

    def se_aplica(self, tipo_produto: str, valores: Valores) -> bool:
        """True se o campo é relevante para `tipo_produto`, dado o que já foi capturado em `valores`."""
        if tipo_produto not in self.produtos_aplicaveis:
            return False
        return self.aplicavel(tipo_produto, valores)


# ---------------------------------------------------------------------------
# CAMPO-modelo
# artefatos/analista_de_requisitos/catalogo_conversacao/campos/CAMPO-modelo.md
# ---------------------------------------------------------------------------
#
# A resposta do cliente deve sempre resolver para uma linha real do catálogo
# (`Modelo`) — nunca texto livre. Sem
# correspondência reconhecível após 1-2 tentativas de esclarecimento
# (REQ-002.21), o sistema escala para modo atendente (`escalar_humano`) em vez
# de gravar o texto do cliente. Essa resolução/validação é implementada na
# Fase F (F2 — Validação mínima), não aqui: este módulo só declara o campo.

CAMPO_MODELO = CampoDef(
    id_catalogo="CAMPO-modelo",
    chave="modelo_produto",
    produtos_aplicaveis=frozenset({"relogio_ponto"}),
    pergunta=(
        "O relógio seria cartográfico ou eletrônico? Se eletrônico: cartão de "
        "proximidade, cartão de barras, biometria ou reconhecimento facial?"
    ),
    ordem=10,
    destino=DESTINO_ITEM_ATENDIMENTO_MODELO_ID,
)


# ---------------------------------------------------------------------------
# CAMPO-software-ponto
# artefatos/analista_de_requisitos/catalogo_conversacao/campos/CAMPO-software-ponto.md
# ---------------------------------------------------------------------------

CAMPO_SOFTWARE_PONTO = CampoDef(
    id_catalogo="CAMPO-software-ponto",
    chave="software_controle_ponto",
    produtos_aplicaveis=frozenset({"relogio_ponto"}),
    pergunta="Qual software de ponto vocês usam hoje? (ex.: Domínio, Alterdata, TOTVS, ou nenhum)",
    ordem=20,
)


# ---------------------------------------------------------------------------
# CAMPO-faixa-funcionarios
# artefatos/analista_de_requisitos/catalogo_conversacao/campos/CAMPO-faixa-funcionarios.md
# ---------------------------------------------------------------------------
#
# Só é aplicável depois que `software_controle_ponto` for respondido = "nenhum"
# (dependência de aplicabilidade, não de ordem — ver §2 do plano: se ainda não
# sabemos a resposta de software, o campo simplesmente não é uma pendência
# ainda; se há software, o software já dimensiona e o campo nunca é perguntado).


def _aplicavel_faixa_funcionarios(tipo_produto: str, valores: Valores) -> bool:
    software = valores.get(CAMPO_SOFTWARE_PONTO.chave)
    if software is None:
        return False
    return software.strip().lower() == "nenhum"


CAMPO_FAIXA_FUNCIONARIOS = CampoDef(
    id_catalogo="CAMPO-faixa-funcionarios",
    chave="faixa_funcionarios",
    produtos_aplicaveis=frozenset({"relogio_ponto"}),
    pergunta="Quantos funcionários vão usar o relógio de ponto?",
    ordem=30,
    aplicavel=_aplicavel_faixa_funcionarios,
)


CAMPOS: dict[str, CampoDef] = {
    campo.chave: campo
    for campo in (CAMPO_MODELO, CAMPO_SOFTWARE_PONTO, CAMPO_FAIXA_FUNCIONARIOS)
}


def campos_do_produto(tipo_produto: str) -> list[CampoDef]:
    """Retorna os `CampoDef` cadastrados para um tipo de produto, na ordem de exibição sugerida.

    Não filtra por já-capturado/aplicável — isso é responsabilidade de
    `campos_pendentes()` (Fase C), que cruza este catálogo com o que já foi
    coletado no atendimento.
    """
    return sorted(
        (campo for campo in CAMPOS.values() if tipo_produto in campo.produtos_aplicaveis),
        key=lambda campo: campo.ordem,
    )
