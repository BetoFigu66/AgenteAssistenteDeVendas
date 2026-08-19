"""Base declarativa e tipos SQLAlchemy compartilhados entre os modelos."""

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import UserDefinedType

UTCDateTime = DateTime(timezone=True)


class Base(DeclarativeBase):
    """Classe base para todos os modelos."""

    pass


class Vector(UserDefinedType):
    """Tipo pgvector para embeddings.

    Serializa list[float] no formato textual aceito pelo pgvector ("[v1,v2,...]")
    e converte a leitura de volta para list[float]. Permite usar o atributo
    `embedding` como uma lista Python em codigo cliente.
    """

    cache_ok = True

    def __init__(self, dimensions: int):
        self.dimensions = dimensions

    def get_col_spec(self, **kw) -> str:
        return f"vector({self.dimensions})"

    def bind_processor(self, dialect):
        def process(value):
            if value is None:
                return None
            if isinstance(value, str):
                return value
            return "[" + ",".join(repr(float(x)) for x in value) + "]"

        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            if value is None:
                return None
            if isinstance(value, (list, tuple)):
                return list(value)
            texto = value.strip()
            if texto.startswith("[") and texto.endswith("]"):
                texto = texto[1:-1]
            if not texto:
                return []
            return [float(x) for x in texto.split(",")]

        return process
