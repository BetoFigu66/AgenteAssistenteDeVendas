"""
Módulo de persistência de dados.
Usa SQLAlchemy para ORM e suporta SQLite, MySQL e PostgreSQL.
"""

from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config import settings
from models import Atendimento, Mensagem, OrigemMensagem, StatusAtendimento
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from utils.datetime_utils import serialize_utc_datetime


class Database:
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or settings.DATABASE_URL
        self._garantir_diretorio()

        self.engine = create_engine(
            self.database_url,
            echo=settings.SQL_ECHO,
            connect_args={"check_same_thread": False} if "sqlite" in self.database_url else {},
        )

        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def _garantir_diretorio(self):
        """Garante que o diretório do banco existe (apenas para SQLite)."""
        if "sqlite" in self.database_url:
            db_path = self.database_url.replace("sqlite:///", "")
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

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
            mensagem = Mensagem(
                telefone=telefone, conteudo=conteudo, origem=OrigemMensagem(origem), message_sid=message_sid
            )
            session.add(mensagem)
            session.flush()
            return mensagem.id

    def obter_historico(
        self,
        telefone: str,
        limit: Optional[int] = None,
        offset: int = 0,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
        status_atendimento: Optional[str] = None,
    ) -> List[Dict]:
        """
        Retorna o histórico de mensagens de um telefone.

        Args:
            telefone: Número do telefone
            limit: se informado, retorna só as `limit` mensagens mais recentes
                (a partir de `offset` mensagens atrás) — REQ-010, Fase 4.
            offset: quantas mensagens recentes pular (paginação de "mais antigas").
            data_inicio/data_fim: filtra por período de `Mensagem.timestamp` (REQ-005,
                Fase 6) — destrava o filtro de período pendente na Fase 4.
            status_atendimento: filtra só mensagens de atendimentos com este status
                (`ativo`/`encerrado`) — mensagens sem atendimento vinculado são excluídas
                quando este filtro é usado.

        Returns:
            Lista de mensagens ordenadas por timestamp (crescente).
        """
        with self.get_session() as session:
            stmt = select(Mensagem).where(Mensagem.telefone == telefone)
            if data_inicio is not None:
                stmt = stmt.where(Mensagem.timestamp >= data_inicio)
            if data_fim is not None:
                stmt = stmt.where(Mensagem.timestamp <= data_fim)
            if status_atendimento is not None:
                stmt = stmt.join(Atendimento, Mensagem.atendimento_id == Atendimento.id).where(
                    Atendimento.status == StatusAtendimento(status_atendimento)
                )
            if limit is not None:
                stmt = stmt.order_by(Mensagem.timestamp.desc()).offset(offset).limit(limit)
                mensagens = list(reversed(session.scalars(stmt).all()))
            else:
                stmt = stmt.order_by(Mensagem.timestamp.asc())
                mensagens = session.scalars(stmt).all()
            return [msg.to_dict() for msg in mensagens]

    def listar_telefones(self) -> List[Dict]:
        """
        Lista telefones com histórico, cada um com o timestamp da última
        mensagem — ordenado do mais recente para o mais antigo (a conversa
        ativa fica sempre no topo da lista, sem precisar de scroll pra achar).

        Returns:
            Lista de {"telefone": str, "ultima_mensagem_em": str ISO} por telefone.
        """
        with self.get_session() as session:
            ultima_mensagem = func.max(Mensagem.timestamp)
            stmt = (
                select(Mensagem.telefone, ultima_mensagem.label("ultima_mensagem_em"))
                .group_by(Mensagem.telefone)
                .order_by(ultima_mensagem.desc())
            )
            return [
                {"telefone": telefone, "ultima_mensagem_em": serialize_utc_datetime(ultima)}
                for telefone, ultima in session.execute(stmt).all()
            ]

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
