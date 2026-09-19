"""Cria o usuário dedicado do testador no backend real (`public.users`), se ainda
não existir — necessário pra autenticar nas rotas `/api/*` que exigem sessão
(REQ-010): `/api/mensagens/pendentes`, `/api/dev/telefones/*`.

Única operação deste projeto que toca o schema do backend direto em vez de
passar por HTTP — não existe endpoint público pra criar o primeiro usuário
(`POST /api/users` também exige sessão já aberta). Mesmo hash usado por
`backend/services/auth.py` (bcrypt puro, sem passlib).
"""

import bcrypt
from config import DATABASE_URL, TESTADOR_LOGIN, TESTADOR_SENHA
from sqlalchemy import create_engine, text

_BCRYPT_MAX_BYTES = 72


def main() -> None:
    engine = create_engine(DATABASE_URL, future=True)
    senha_hash = bcrypt.hashpw(
        TESTADOR_SENHA.encode("utf-8")[:_BCRYPT_MAX_BYTES], bcrypt.gensalt()
    ).decode("ascii")

    with engine.begin() as conn:
        existente = conn.execute(
            text("SELECT id FROM users WHERE login = :login"), {"login": TESTADOR_LOGIN}
        ).first()
        if existente:
            print(f"Usuário '{TESTADOR_LOGIN}' já existe (id={existente[0]}).")
            return
        conn.execute(
            text(
                "INSERT INTO users (nome, login, senha_hash, created_at) "
                "VALUES (:nome, :login, :senha_hash, now())"
            ),
            {"nome": "Testador de Conversas", "login": TESTADOR_LOGIN, "senha_hash": senha_hash},
        )
    print(f"Usuário '{TESTADOR_LOGIN}' criado.")


if __name__ == "__main__":
    main()
