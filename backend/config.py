"""
Configurações do sistema.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Twilio
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_WHATSAPP_NUMBER: Optional[str] = None
    
    # Database
    DATABASE_URL: str = "postgresql://inforrel:inforrel_dev@localhost:5433/assistente_vendas"
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
