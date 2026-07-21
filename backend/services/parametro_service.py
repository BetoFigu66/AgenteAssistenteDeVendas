"""
Service para leitura de parâmetros dinâmicos da tabela `parametros`.

Permite calibrar limiares de RAG, confiança do classificador e outras
constantes sem necessidade de deploy.
"""

import logging
from decimal import Decimal
from typing import Optional, TypeVar, Union

from models import HistoricoConfiguracao, ModoExecucao, Parametro
from sqlalchemy.orm import Session
from utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)

JANELA_CONTINUACAO_ATENDIMENTO_HORAS = "janela_continuacao_atendimento_horas"
DEFAULT_JANELA_CONTINUACAO_ATENDIMENTO_HORAS = 24

# REQ-011: modo de execução vigente (simulacao/conversa_controlada/execucao_normal).
# Default = execucao_normal — decisão explícita: preserva o comportamento atual de fato
# (envio automático) até alguém trocar conscientemente pelo painel/API, em vez de mudar
# o comportamento observável do sistema silenciosamente neste deploy.
MODO_EXECUCAO = "modo_execucao"
DEFAULT_MODO_EXECUCAO = ModoExecucao.EXECUCAO_NORMAL.value

# REQ-011.13: limiar de alerta visual de SLA para mensagens pendentes de aprovação.
SLA_APROVACAO_MINUTOS = "sla_aprovacao_minutos"
DEFAULT_SLA_APROVACAO_MINUTOS = 10

# Validação na escrita (REQ-014 §5.1)
_PARAM_FLOAT_0_1 = frozenset({
    "qa_fulltext_responde_min",
    "qa_fulltext_desambigua_min",
    "qa_embedding_responde_min",
    "qa_embedding_desambigua_min",
    "classificador_conf_alta_min",
    "classificador_conf_baixa_max",
    "rag_score_minimo",
})
_PARAM_INT_MIN_1 = frozenset({
    JANELA_CONTINUACAO_ATENDIMENTO_HORAS,
    "desambiguador_max_opcoes",
    "desambiguador_timeout_min",
    SLA_APROVACAO_MINUTOS,
    "rag_top_k",
})
_PARAM_BOOL = frozenset({
    "rag_enabled",
    "qa_enabled",
})
_PARAM_ENUM: dict[str, frozenset[str]] = {
    MODO_EXECUCAO: frozenset(m.value for m in ModoExecucao),
}

T = TypeVar("T", int, float, bool, str)


class ParametroService:
    """Leitor de parâmetros de configuração com cache leve por sessão."""

    def __init__(self, db: Session):
        self._db = db
        self._cache: dict[str, str] = {}

    def get(self, nome: str, padrao: Optional[T] = None, tipo: type[T] = str) -> Union[T, None]:
        """
        Retorna o valor de um parâmetro, convertido para o tipo desejado.

        Args:
            nome: chave do parâmetro (ex: 'qa_fulltext_responde_min')
            padrao: valor padrão se o parâmetro não existir no banco
            tipo: tipo de conversão (int, float, bool, str)

        Returns:
            Valor convertido ou `padrao` se não encontrado.
        """
        # cache leve (por sessão)
        if nome in self._cache:
            raw = self._cache[nome]
        else:
            row = (
                self._db.query(Parametro)
                .filter(Parametro.nome == nome)
                .first()
            )
            if row is None:
                if padrao is not None:
                    logger.warning("[Parametro] '%s' não encontrado; usando padrão=%r", nome, padrao)
                return padrao
            raw = row.valor
            self._cache[nome] = raw

        try:
            return _cast(raw, tipo)
        except (ValueError, TypeError) as exc:
            logger.warning(
                "[Parametro] '%s' valor='%s' não converte para %s: %s; usando padrão=%r",
                nome, raw, tipo.__name__, exc, padrao,
            )
            return padrao

    def get_float(self, nome: str, padrao: Optional[float] = None) -> Optional[float]:
        return self.get(nome, padrao, float)

    def get_int(self, nome: str, padrao: Optional[int] = None) -> Optional[int]:
        return self.get(nome, padrao, int)

    def get_bool(self, nome: str, padrao: Optional[bool] = None) -> Optional[bool]:
        return self.get(nome, padrao, bool)

    def get_str(self, nome: str, padrao: Optional[str] = None) -> Optional[str]:
        return self.get(nome, padrao, str)

    def invalidar_cache(self, nome: Optional[str] = None) -> None:
        """Remove entrada(s) do cache de sessão (após PATCH)."""
        if nome is None:
            self._cache.clear()
        else:
            self._cache.pop(nome, None)

    def set(
        self,
        nome: str,
        valor: str,
        *,
        descricao: Optional[str] = None,
        ator: Optional[str] = None,
    ) -> Parametro:
        """Persiste parâmetro na tabela `parametros` e invalida cache da chave.

        Quando `ator` é informado, grava também uma linha em `HistoricoConfiguracao`
        (REQ-014, Fase 7) com o valor anterior/novo — endpoints que já têm sua própria
        auditoria dedicada (ex.: `PATCH /api/config/execucao` → `HistoricoModoExecucao`)
        podem seguir sem passar `ator` aqui para não duplicar o registro.
        """
        row = self._db.query(Parametro).filter(Parametro.nome == nome).first()
        valor_anterior = row.valor if row else None
        if row:
            row.valor = valor
            if descricao is not None:
                row.descricao = descricao
            row.updated_at = utc_now()
        else:
            row = Parametro(nome=nome, valor=valor, descricao=descricao)
            self._db.add(row)
        if ator is not None:
            self._db.add(
                HistoricoConfiguracao(
                    nome=nome,
                    valor_anterior=valor_anterior,
                    valor_novo=valor,
                    ator=ator,
                )
            )
        self._db.commit()
        self._db.refresh(row)
        self.invalidar_cache(nome)
        logger.info("[Parametro] '%s' atualizado para %r (ator=%s)", nome, valor, ator)
        return row

    def set_int(
        self,
        nome: str,
        valor: int,
        *,
        minimo: int = 1,
        descricao: Optional[str] = None,
        ator: Optional[str] = None,
    ) -> int:
        if valor < minimo:
            raise ValueError(f"'{nome}' deve ser inteiro >= {minimo}")
        self.set(nome, str(valor), descricao=descricao, ator=ator)
        return valor

    def janela_continuacao_atendimento_horas(self) -> int:
        """Janela REQ-016.7 / REQ-014.2C (default 24h)."""
        return (
            self.get_int(
                JANELA_CONTINUACAO_ATENDIMENTO_HORAS,
                DEFAULT_JANELA_CONTINUACAO_ATENDIMENTO_HORAS,
            )
            or DEFAULT_JANELA_CONTINUACAO_ATENDIMENTO_HORAS
        )

    def modo_execucao(self) -> ModoExecucao:
        """Modo de execução vigente (REQ-011.1). Valor inválido no banco (ex.: alterado
        manualmente fora da validação) cai para o default em vez de levantar exceção —
        este é lido a cada mensagem processada, não pode quebrar o atendimento."""
        valor = self.get_str(MODO_EXECUCAO, DEFAULT_MODO_EXECUCAO) or DEFAULT_MODO_EXECUCAO
        try:
            return ModoExecucao(valor)
        except ValueError:
            logger.warning(
                "[Parametro] '%s' valor='%s' não é um ModoExecucao válido; usando default=%s",
                MODO_EXECUCAO, valor, DEFAULT_MODO_EXECUCAO,
            )
            return ModoExecucao(DEFAULT_MODO_EXECUCAO)

    def sla_aprovacao_minutos(self) -> int:
        """Limiar de alerta visual de SLA de aprovação (REQ-011.13, default 10min)."""
        return (
            self.get_int(SLA_APROVACAO_MINUTOS, DEFAULT_SLA_APROVACAO_MINUTOS)
            or DEFAULT_SLA_APROVACAO_MINUTOS
        )

    def limiares_zona_cinza(self) -> dict[str, float]:
        """
        Retorna os 4 limiares de zona cinza usados pelo QAService.
        """
        return {
            "qa_fulltext_responde_min": self.get_float("qa_fulltext_responde_min", 0.30),
            "qa_fulltext_desambigua_min": self.get_float("qa_fulltext_desambigua_min", 0.12),
            "qa_embedding_responde_min": self.get_float("qa_embedding_responde_min", 0.80),
            "qa_embedding_desambigua_min": self.get_float("qa_embedding_desambigua_min", 0.65),
        }

    def limiares_classificador(self) -> dict[str, float]:
        """
        Retorna os limiares de confiança do classificador.
        """
        return {
            "alta_min": self.get_float("classificador_conf_alta_min", 0.70),
            "baixa_max": self.get_float("classificador_conf_baixa_max", 0.40),
        }


def validar_valor_parametro(nome: str, valor: str) -> str:
    """Valida valor textual antes de persistir (REQ-014 §5.1)."""
    v = valor.strip()
    if not v:
        raise ValueError("valor não pode ser vazio")
    if nome in _PARAM_FLOAT_0_1:
        n = float(v)
        if not 0.0 <= n <= 1.0:
            raise ValueError(f"'{nome}' deve ser um número entre 0.0 e 1.0")
    elif nome in _PARAM_INT_MIN_1:
        n = int(v)
        if n < 1:
            raise ValueError(f"'{nome}' deve ser inteiro >= 1")
    elif nome in _PARAM_ENUM:
        if v not in _PARAM_ENUM[nome]:
            raise ValueError(f"'{nome}' deve ser um de {sorted(_PARAM_ENUM[nome])}")
    elif nome in _PARAM_BOOL:
        _cast(v, bool)  # levanta ValueError se não for um booleano reconhecido
    return v


def _cast(valor: str, tipo: type[T]) -> T:
    if tipo is bool:
        v = valor.strip().lower()
        if v in ("true", "1", "yes", "sim"):
            return True  # type: ignore[return-value]
        if v in ("false", "0", "no", "nao", "não"):
            return False  # type: ignore[return-value]
        raise ValueError(f"booleano inválido: {valor}")
    if tipo is Decimal:
        return Decimal(valor)  # type: ignore[return-value]
    return tipo(valor)  # type: ignore[return-value]
