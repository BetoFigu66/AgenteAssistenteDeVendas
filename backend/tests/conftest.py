"""Fixtures compartilhadas entre os testes que sobem o FastAPI real via `TestClient`.

Desde a Fase 4 (REQ-010), praticamente todo `/api/*` exige sessão válida — o
fixture `client` já loga com um usuário de teste dedicado antes de entregar o
`TestClient`, para não duplicar esse boilerplate em cada arquivo de teste.
"""

import pytest
from config import settings
from database import Database
from fastapi.testclient import TestClient
from models import User
from services import auth as auth_svc

_LOGIN_TESTE = "pytest_runner"
_SENHA_TESTE = "pytest_senha_123"


@pytest.fixture(autouse=True)
def gate_autenticacao_ligado(monkeypatch):
    """Roda toda a suíte com o gate de sessão LIGADO, ignorando o `.env` da
    máquina.

    `AUTH_ENABLED=false` (escape hatch de dev/QA) substitui a identidade da
    sessão por um usuário fixo — e vários testes dependem de agir como o
    `pytest_runner` do fixture `client` (ex.: filtro de reports por autor).
    Sem isto a suíte falharia num ambiente com o gate desligado, sem nada estar
    quebrado. O teste do próprio bypass desliga o flag explicitamente.
    """
    monkeypatch.setattr(settings, "AUTH_ENABLED", True)


# Configurações de canal/Twilio que o `.env` da máquina pode ter ligado e que mudam o
# comportamento de teste sem nada estar quebrado. As credenciais entram na lista de
# propósito: sem elas, mesmo um teste que ligue `CANAL_SAIDA=twilio` e esqueça de mockar
# o envio cai no `CanalSimulado` (falha segura da factory) em vez de falar com a Twilio.
_SETTINGS_ISOLADOS_DO_ENV = (
    "CANAL_SAIDA",
    "TWILIO_MODO_ENVIO",
    "APP_URL_PUBLICA",
    "TWILIO_VALIDAR_ASSINATURA",
    "TWILIO_CAPTURAR_PAYLOADS",
    "TWILIO_CAPTURA_ARQUIVO",
    "TWILIO_CAPTURA_MIDIAS_PASTA",
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_WHATSAPP_NUMBER",
    "TWILIO_API_KEY_SID",
    "TWILIO_API_KEY_SECRET",
)


@pytest.fixture(autouse=True)
def canal_e_twilio_nos_defaults(monkeypatch):
    """Roda toda a suíte com canal e Twilio nos defaults do `Settings`, ignorando o
    `.env` da máquina.

    Na janela da colheita de payloads o `.env` ficou com `CANAL_SAIDA=twilio` e
    `TWILIO_CAPTURAR_PAYLOADS=true`, e testes que assumem o default passaram a falhar (e,
    pior, os de webhook passaram a tentar gravar no arquivo de captura real). O default
    vem da própria declaração do campo, para não haver uma segunda cópia dele aqui. Quem
    precisa de outro valor continua fazendo `monkeypatch.setattr` no próprio teste, que
    roda depois deste fixture e prevalece.

    O `cache_clear` é necessário porque `obter_canal` guarda a instância: um canal
    montado com o `.env` antes deste fixture sobreviveria a ele.
    """
    from services.canal.factory import obter_canal

    campos = type(settings).model_fields
    for nome in _SETTINGS_ISOLADOS_DO_ENV:
        monkeypatch.setattr(settings, nome, campos[nome].default)
    obter_canal.cache_clear()
    yield
    obter_canal.cache_clear()


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
