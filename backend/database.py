"""
Módulo de persistência de dados.
Usa SQLAlchemy para ORM e suporta SQLite, MySQL e PostgreSQL.
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Optional

from config import settings
from models import Base, Mensagem, OrigemMensagem
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker


class Database:
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or settings.DATABASE_URL
        self._garantir_diretorio()

        self.engine = create_engine(
            self.database_url, echo=settings.DEBUG, connect_args={"check_same_thread": False} if "sqlite" in self.database_url else {}
        )

        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        self._criar_tabelas()

    def _garantir_diretorio(self):
        """Garante que o diretório do banco existe (apenas para SQLite)."""
        if "sqlite" in self.database_url:
            db_path = self.database_url.replace("sqlite:///", "")
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def _criar_tabelas(self):
        """Cria as tabelas se não existirem."""
        Base.metadata.create_all(bind=self.engine)

    @contextmanager
    def get_session(self):
        """Context manager para sessões do banco."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def salvar_mensagem(self, telefone: str, conteudo: str, origem: str, message_sid: Optional[str] = None) -> int:
        """
        Salva uma mensagem no histórico.

        Args:
            telefone: Número do telefone
            conteudo: Conteúdo da mensagem
            origem: 'user' ou 'system'
            message_sid: ID da mensagem do Twilio (opcional)

        Returns:
            ID da mensagem inserida
        """
        with self.get_session() as session:
            mensagem = Mensagem(telefone=telefone, conteudo=conteudo, origem=OrigemMensagem(origem), message_sid=message_sid)
            session.add(mensagem)
            session.flush()
            return mensagem.id

    def obter_historico(self, telefone: str) -> List[Dict]:
        """
        Retorna o histórico de mensagens de um telefone.

        Args:
            telefone: Número do telefone

        Returns:
            Lista de mensagens ordenadas por timestamp
        """
        with self.get_session() as session:
            stmt = select(Mensagem).where(Mensagem.telefone == telefone).order_by(Mensagem.timestamp.asc())
            mensagens = session.scalars(stmt).all()
            return [msg.to_dict() for msg in mensagens]

    def listar_telefones(self) -> List[str]:
        """
        Lista todos os telefones únicos com histórico.

        Returns:
            Lista de números de telefone
        """
        with self.get_session() as session:
            stmt = select(Mensagem.telefone).distinct().order_by(Mensagem.telefone)
            return list(session.scalars(stmt).all())

    def mensagem_existe(self, message_sid: str) -> bool:
        """
        Verifica se uma mensagem já foi processada (idempotência).

        Args:
            message_sid: ID da mensagem do Twilio

        Returns:
            True se a mensagem já existe
        """
        if not message_sid:
            return False

        with self.get_session() as session:
            stmt = select(Mensagem).where(Mensagem.message_sid == message_sid)
            return session.scalar(stmt) is not None


# Instância global para dependency injection
def get_db() -> Database:
    """Retorna instância do banco para uso com FastAPI Depends."""
    return Database()
