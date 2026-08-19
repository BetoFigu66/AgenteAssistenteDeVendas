"""
Modelos SQLAlchemy para o Assistente de Vendas via WhatsApp com IA.

Este pacote agrupa os modelos por área de domínio (um módulo por entidade
principal e o que só existe em função dela), no lugar de um único arquivo
`models.py` monolítico. Este `__init__.py` reexporta tudo para preservar o
import plano usado no resto do código (`from models import Atendimento`, etc.)
— dividir os arquivos não deveria exigir tocar em nenhum outro módulo.
"""

from .atendimento import (
    Atendimento,
    AtendimentoInfo,
    EventoAtendimento,
    FaseAtendimento,
    ItemAtendimento,
    ModoOperacao,
    MotivoEncerramento,
    MotivoEscalonamento,
    OrigemInfo,
    StatusAtendimento,
    TipoDocumento,
    TipoEventoAtendimento,
)
from .base import Base, UTCDateTime, Vector
from .catalogo import AtributoAdicionalModelo, Categoria, Modelo, Produto, modelos_categorias
from .contato import Contato
from .empresa import AtividadeEmpresa, Empresa, SocioEmpresa, TipoEmpresa
from .mensagem import Mensagem, OrigemMensagem
from .orcamento import ItemOrcamento, Orcamento, StatusOrcamento
from .parametro import HistoricoConfiguracao, HistoricoModoExecucao, ModoExecucao, Parametro
from .pessoa import Pessoa
from .processamento import OrigemClassificacao, ProcessamentoMensagem
from .rag import DocumentoConhecimento, ParQA
from .report import (
    CategoriaReport,
    HistoricoStatusReport,
    ReportProblema,
    SeveridadeReport,
    StatusReport,
)
from .user import User

__all__ = [
    "Atendimento",
    "AtendimentoInfo",
    "AtividadeEmpresa",
    "AtributoAdicionalModelo",
    "Base",
    "Categoria",
    "CategoriaReport",
    "Contato",
    "DocumentoConhecimento",
    "Empresa",
    "EventoAtendimento",
    "FaseAtendimento",
    "HistoricoConfiguracao",
    "HistoricoModoExecucao",
    "HistoricoStatusReport",
    "ItemAtendimento",
    "ItemOrcamento",
    "Mensagem",
    "Modelo",
    "ModoExecucao",
    "ModoOperacao",
    "MotivoEncerramento",
    "MotivoEscalonamento",
    "Orcamento",
    "OrigemClassificacao",
    "OrigemInfo",
    "OrigemMensagem",
    "ParQA",
    "Parametro",
    "Pessoa",
    "ProcessamentoMensagem",
    "Produto",
    "ReportProblema",
    "SeveridadeReport",
    "SocioEmpresa",
    "StatusAtendimento",
    "StatusOrcamento",
    "StatusReport",
    "TipoDocumento",
    "TipoEmpresa",
    "TipoEventoAtendimento",
    "User",
    "UTCDateTime",
    "Vector",
    "modelos_categorias",
]
