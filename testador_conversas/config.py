"""Configuração do testador de conversas.

Sistema separado do backend — fala com ele só por HTTP (webhook + API
autenticada) e tem seu próprio schema (`teste_conversas`) no mesmo Postgres.
Todos os valores têm default de dev; sobrescreva via variável de ambiente.
"""

import os

DATABASE_URL = os.environ.get(
    "TESTADOR_DATABASE_URL",
    "postgresql://inforrel:inforrel_dev@localhost:5433/assistente_vendas",
)
SCHEMA = "teste_conversas"

BACKEND_BASE_URL = os.environ.get("TESTADOR_BACKEND_BASE_URL", "http://localhost:8001")

# Usuário dedicado do testador no backend (ver bootstrap_usuario.py) — usado
# pra autenticar nas rotas /api/* que exigem sessão (REQ-010).
TESTADOR_LOGIN = os.environ.get("TESTADOR_LOGIN", "testador_conversas")
TESTADOR_SENHA = os.environ.get("TESTADOR_SENHA", "testador_conversas_dev_only")
