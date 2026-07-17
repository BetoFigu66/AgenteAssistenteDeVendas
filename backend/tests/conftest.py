"""Fixtures compartilhadas entre os testes que sobem o FastAPI real via `TestClient`.

Desde a Fase 4 (REQ-010), praticamente todo `/api/*` exige sessão válida — o
fixture `client` já loga com um usuário de teste dedicado antes de entregar o
`TestClient`, para não duplicar esse boilerplate em cada arquivo de teste.
"""

import pytest
from database import Database
from fastapi.testclient import TestClient
from models import User
from services import auth as auth_svc

_LOGIN_TESTE = "pytest_runner"
_SENHA_TESTE = "pytest_senha_123"


def _garantir_usuario_teste() -> None:
    db = Database()
    with db.get_session() as session:
        user = session.query(User).filter_by(login=_LOGIN_TESTE).first()
        if not user:
            user = User(
                nome="Pytest Runner",
                login=_LOGIN_TESTE,
                senha_hash=auth_svc.hash_senha(_SENHA_TESTE),
            )
            session.add(user)
            session.flush()


@pytest.fixture
def client():
    """`TestClient` já autenticado (cookie de sessão persiste entre chamadas)."""
    import main

    _garantir_usuario_teste()
    with TestClient(main.app) as c:
        r = c.post("/api/auth/login", json={"login": _LOGIN_TESTE, "senha": _SENHA_TESTE})
        assert r.status_code == 200, r.text
        yield c
