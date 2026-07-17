"""
Autenticação mínima do painel administrativo (REQ-010, Fase 4).

Hash de senha via `bcrypt` puro (não `passlib` — incompatível com `bcrypt>=4.1`,
ver nota em `requirements.txt`). Sessão é um cookie assinado (Starlette
`SessionMiddleware`, ver `main.py`), não há tabela de sessão nem token.
"""

from __future__ import annotations

from typing import Optional

import bcrypt
from models import User
from sqlalchemy.orm import Session

_BCRYPT_MAX_BYTES = 72


def _truncar_bytes(senha: str) -> bytes:
    """bcrypt rejeita senhas com mais de 72 bytes — trunca em vez de falhar
    (mesmo comportamento que o passlib tinha por padrão)."""
    return senha.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(_truncar_bytes(senha), bcrypt.gensalt()).decode("ascii")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_truncar_bytes(senha), senha_hash.encode("ascii"))
    except ValueError:
        # hash malformado/vazio — nunca autentica, não propaga exceção pro chamador.
        return False


def autenticar(db: Session, login: str, senha: str) -> Optional[User]:
    """Retorna o `User` se `login`+`senha` forem válidos, senão `None`.

    Usuários sem `senha_hash` (ainda não configurada) nunca autenticam — não há
    "senha em branco" válida.
    """
    login_normalizado = (login or "").strip().lower()
    if not login_normalizado or not senha:
        return None

    user = db.query(User).filter(User.login == login_normalizado).first()
    if not user or not user.senha_hash:
        return None
    if not verificar_senha(senha, user.senha_hash):
        return None
    return user
