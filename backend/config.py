"""
Configurações do sistema.
"""

from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Twilio
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_WHATSAPP_NUMBER: Optional[str] = None

    # Database
    DATABASE_URL: str = "postgresql+psycopg://inforrel:inforrel_dev@192.168.0.34:5433/assistente_vendas"

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True
    LOG_LEVEL: str = "WARNING"
    SQL_ECHO: bool = False

    # Autenticação (REQ-010, Fase 4) — assina o cookie de sessão. Default só serve
    # para dev local; sobrescrever via .env em qualquer ambiente compartilhado/produção.
    SESSION_SECRET_KEY: str = "dev-secret-key-troque-em-producao"
    SESSION_MAX_AGE_SEGUNDOS: int = 8 * 60 * 60

    # LLM
    LLM_PROVIDER: str = "groq"
    LLM_MODEL: str = "llama-3.1-8b-instant"
    LLM_API_KEY: Optional[str] = None
    LLM_TEMPERATURE: float = 0.3

    # Embeddings (RAG)
    EMBEDDING_PROVIDER: str = "openai"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_API_KEY: Optional[str] = None

    # RAG / Retrieval
    RAG_ENABLED: bool = True
    RAG_TOP_K: int = 4
    RAG_SCORE_MINIMO: float = 0.70
    RAG_SUGERIR_PRODUTOS: bool = False
    RAG_EXIBIR_FONTES_PAINEL: bool = True

    # Q&A Pairs
    QA_ENABLED: bool = True
    QA_SCORE_MINIMO: float = 0.80
    QA_SCORE_MINIMO_FULLTEXT: float = 0.25
    QA_TOP_K: int = 3
    QA_APENAS_APROVADOS: bool = True

    # Consulta CNPJ
    RECEITAWS_BASE_URL: str = "https://www.receitaws.com.br/v1/cnpj"

    # Consulta CPF / crédito (REQ-015) — provedor a definir (serasa, spc, boavista, quod)
    CPF_CONSULTA_CREDITO_ENABLED: bool = False
    CPF_CONSULTA_CREDITO_PROVIDER: Optional[str] = None
    CPF_CONSULTA_CREDITO_API_KEY: Optional[str] = None
    CPF_CONSULTA_CREDITO_BASE_URL: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
