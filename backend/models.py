"""
Modelos SQLAlchemy para o Assistente de Vendas.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, Enum, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import enum


class Base(DeclarativeBase):
    """Classe base para todos os modelos."""
    pass


class OrigemMensagem(str, enum.Enum):
    """Enum para origem da mensagem."""
    USER = "user"
    SYSTEM = "system"


class Mensagem(Base):
    """Modelo para armazenar mensagens do chat."""
    
    __tablename__ = "mensagens"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telefone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    conteudo: Mapped[str] = mapped_column(Text, nullable=False)
    origem: Mapped[OrigemMensagem] = mapped_column(
        Enum(OrigemMensagem, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    message_sid: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, unique=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow,
        nullable=False
    )
    
    __table_args__ = (
        Index('idx_mensagens_telefone_timestamp', 'telefone', 'timestamp'),
    )
    
    def to_dict(self) -> dict:
        """Converte o modelo para dicionário."""
        return {
            "id": self.id,
            "telefone": self.telefone,
            "conteudo": self.conteudo,
            "origem": self.origem.value if isinstance(self.origem, OrigemMensagem) else self.origem,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
