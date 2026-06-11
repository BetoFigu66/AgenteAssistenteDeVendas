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

logger = logging.getLogger(__name__)

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
