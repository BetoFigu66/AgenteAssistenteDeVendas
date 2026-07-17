"""Testes de autenticação mínima (REQ-010, Fase 4) — login/logout/sessão, gate
de `/api/*`, e definição de senha. Zero cobertura antes desta fase.
"""

import pytest
from database import Database
from fastapi.testclient import TestClient
from models import User
from services import auth as auth_svc


@pytest.fixture
def db_session():
    database = Database()
    with database.get_session() as session:
        yield session


def _limpar_usuario(db_session, login: str):
    db_session.commit()
    db_session.query(User).filter_by(login=login).delete()
    db_session.commit()


def test_endpoint_protegido_sem_sessao_retorna_401():
    import main

    with TestClient(main.app) as c:
        r = c.get("/api/atendimentos/ativas")
        assert r.status_code == 401


def test_health_e_webhook_nao_exigem_sessao():
    import main

    with TestClient(main.app) as c:
        assert c.get("/health").status_code == 200
        # Sem assinatura Twilio válida o webhook pode falhar por outro motivo,
        # mas não deve ser bloqueado pelo gate de autenticação (401).
        r = c.post("/webhook", data={"From": "whatsapp:+5511999999999", "Body": "oi"})
        assert r.status_code != 401


def test_login_com_credenciais_invalidas_401(db_session):
    import main

    login = "teste_auth_invalido"
    try:
        senha_hash = auth_svc.hash_senha("senhacerta")
        user = User(nome="Teste Auth Inválido", login=login, senha_hash=senha_hash)
        db_session.add(user)
        db_session.commit()

        with TestClient(main.app) as c:
            r = c.post("/api/auth/login", json={"login": login, "senha": "senhaerrada"})
            assert r.status_code == 401

            r2 = c.post("/api/auth/login", json={"login": "nao_existe", "senha": "qualquer"})
            assert r2.status_code == 401
    finally:
        _limpar_usuario(db_session, login)


def test_login_sem_senha_configurada_401(db_session):
    """Usuário criado antes da Fase 4 (sem senha_hash) nunca autentica."""
    import main

    login = "teste_auth_sem_senha"
    try:
        user = User(nome="Sem Senha", login=login, senha_hash=None)
        db_session.add(user)
        db_session.commit()

        with TestClient(main.app) as c:
            r = c.post("/api/auth/login", json={"login": login, "senha": "qualquer"})
            assert r.status_code == 401
    finally:
        _limpar_usuario(db_session, login)


def test_login_logout_ciclo_completo(db_session):
    import main

    login = "teste_auth_ciclo"
    try:
        user = User(nome="Ciclo Completo", login=login, senha_hash=auth_svc.hash_senha("senha123"))
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        with TestClient(main.app) as c:
            r = c.post("/api/auth/login", json={"login": login, "senha": "senha123"})
            assert r.status_code == 200
            body = r.json()
            assert body["id"] == user.id
            assert body["login"] == login
            assert "senha_hash" not in body

            r_me = c.get("/api/auth/me")
            assert r_me.status_code == 200
            assert r_me.json()["id"] == user.id

            r_logout = c.post("/api/auth/logout")
            assert r_logout.status_code == 200

            r_me_depois = c.get("/api/auth/me")
            assert r_me_depois.status_code == 401
    finally:
        _limpar_usuario(db_session, login)


def test_definir_senha_permite_login_de_usuario_legado(db_session):
    """Usuário sem login/senha (ex.: seed antigo) ganha capacidade de logar via
    PATCH /api/users/{id}/senha, autenticado por outra sessão já aberta."""
    import main

    login_admin = "teste_auth_admin"
    login_legado = "teste_auth_legado"
    try:
        admin = User(nome="Admin Teste", login=login_admin, senha_hash=auth_svc.hash_senha("admin123"))
        legado = User(nome="Usuário Legado", login=None, senha_hash=None)
        db_session.add_all([admin, legado])
        db_session.commit()
        db_session.refresh(admin)
        db_session.refresh(legado)

        with TestClient(main.app) as c:
            r_login = c.post("/api/auth/login", json={"login": login_admin, "senha": "admin123"})
            assert r_login.status_code == 200

            r_senha = c.patch(
                f"/api/users/{legado.id}/senha",
                json={"senha": "novaSenha1", "login": login_legado},
            )
            assert r_senha.status_code == 200
            assert r_senha.json()["login"] == login_legado
            assert r_senha.json()["tem_senha"] is True

        with TestClient(main.app) as c2:
            r_login2 = c2.post("/api/auth/login", json={"login": login_legado, "senha": "novaSenha1"})
            assert r_login2.status_code == 200
    finally:
        _limpar_usuario(db_session, login_admin)
        _limpar_usuario(db_session, login_legado)


def test_definir_senha_sem_login_existente_exige_login_no_payload(db_session):
    import main

    login_admin = "teste_auth_admin2"
    try:
        admin = User(nome="Admin Teste 2", login=login_admin, senha_hash=auth_svc.hash_senha("admin123"))
        legado = User(nome="Legado Sem Login", login=None, senha_hash=None)
        db_session.add_all([admin, legado])
        db_session.commit()
        db_session.refresh(admin)
        db_session.refresh(legado)

        with TestClient(main.app) as c:
            c.post("/api/auth/login", json={"login": login_admin, "senha": "admin123"})
            r = c.patch(f"/api/users/{legado.id}/senha", json={"senha": "novaSenha1"})
            assert r.status_code == 400
    finally:
        _limpar_usuario(db_session, login_admin)
        db_session.query(User).filter_by(nome="Legado Sem Login").delete()
        db_session.commit()


def test_criar_user_com_login_duplicado_conflito(db_session):
    import main

    login = "teste_auth_dup"
    login_admin = "teste_auth_admin3"
    try:
        admin = User(nome="Admin Teste 3", login=login_admin, senha_hash=auth_svc.hash_senha("admin123"))
        existente = User(nome="Já existe", login=login, senha_hash=auth_svc.hash_senha("x"))
        db_session.add_all([admin, existente])
        db_session.commit()

        with TestClient(main.app) as c:
            c.post("/api/auth/login", json={"login": login_admin, "senha": "admin123"})
            r = c.post("/api/users", json={"nome": "Outro", "login": login, "senha": "y"})
            assert r.status_code == 409
    finally:
        _limpar_usuario(db_session, login)
        _limpar_usuario(db_session, login_admin)
