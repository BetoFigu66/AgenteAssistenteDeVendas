"""
Modulo de ajuda contextual do painel (FAQ por tela).

Isolado do dominio de vendas de proposito: nao importa `Atendimento`, `Empresa`
nem qualquer entidade do negocio, e nao e consultado pelo `ProcessadorMensagem`.
Reaproveita apenas a infraestrutura generica (embeddings, pgvector, full-text).

Essa fronteira e o que permitiria extrair o modulo para outro sistema mudando so
configuracao — ver `ideia_modulo_ajuda_contextual.md` na raiz do repo.
"""

from .busca import (
    ORIGEM_EMBEDDING,
    ORIGEM_FULLTEXT,
    AjudaService,
    ResultadoAjuda,
    contextos_candidatos,
)

__all__ = [
    "AjudaService",
    "ResultadoAjuda",
    "contextos_candidatos",
    "ORIGEM_EMBEDDING",
    "ORIGEM_FULLTEXT",
]
