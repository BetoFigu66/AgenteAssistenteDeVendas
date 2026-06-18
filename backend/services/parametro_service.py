"""
Service para leitura de parâmetros dinâmicos da tabela `parametros`.

Permite calibrar limiares de RAG, confiança do classificador e outras
constantes sem necessidade de deploy.
"""

import logging
from decimal import Decimal
from typing import Optional, TypeVar, Union

from models import Parametro
from sqlalchemy.orm import Session
from utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)

JANELA_CONTINUACAO_ATENDIMENTO_HORAS = "janela_continuacao_atendimento_horas"
DEFAULT_JANELA_CONTINUACAO_ATENDIMENTO_HORAS = 24

# Validação na escrita (REQ-014 §5.1)
_PARAM_FLOAT_0_1 = frozenset({
    "qa_fulltext_responde_min",
    "qa_fulltext_desambigua_min",
    "qa_embedding_responde_min",
    "qa_embedding_desambigua_min",
    "classificador_conf_alta_min",
    "classificador_conf_baixa_max",
})
_PARAM_INT_MIN_1 = frozenset({
    JANELA_CONTINUACAO_ATENDIMENTO_HORAS,
    "desambiguador_max_opcoes",
    "desambiguador_timeout_min",
})

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

    def set(self, nome: str, valor: str, *, descricao: Optional[str] = None) -> Parametro:
        """Persiste parâmetro na tabela `parametros` e invalida cache da chave."""
        row = self._db.query(Parametro).filter(Parametro.nome == nome).first()
        if row:
            row.valor = valor
            if descricao is not None:
                row.descricao = descricao
            row.updated_at = utc_now()
        else:
            row = Parametro(nome=nome, valor=valor, descricao=descricao)
            self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        self.invalidar_cache(nome)
        logger.info("[Parametro] '%s' atualizado para %r", nome, valor)
        return row

    def set_int(self, nome: str, valor: int, *, minimo: int = 1, descricao: Optional[str] = None) -> int:
        if valor < minimo:
            raise ValueError(f"'{nome}' deve ser inteiro >= {minimo}")
        self.set(nome, str(valor), descricao=descricao)
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
