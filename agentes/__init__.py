# Agentes para desenvolvimento do Assistente de Vendas via WhatsApp com IA
# Este módulo contém os agentes especializados que auxiliam no desenvolvimento do projeto
#
# Agentes com lógica Python executável (mantêm .py):
#   AnalistaRequisitos  — criar_req_formal(), revisar_consistencia()
#   GerenteDeProjetos   — gerar_relatorio_sprint(), gerar_apresentacao_pptx()
#   QAEngineer          — registry @registrar_check, infraestrutura de checks
#   Implementador       — registrar_diretriz(), listar_diretrizes()
#
# Agentes definidos apenas como .md (sem classe Python — segue IA01):
#   [auxiliar]   → agentes/auxiliar_negocios.md
#   [arquiteto]  → agentes/arquiteto_sistemas.md
#   [planejador] → agentes/planejador_negocios.md

from .analista_requisitos import AnalistaRequisitos
from .gerente_de_projetos import GerenteDeProjetos
from .qa_engineer import QAEngineer
from .implementador import Implementador

__all__ = [
    'AnalistaRequisitos',
    'GerenteDeProjetos',
    'QAEngineer',
    'Implementador',
]
