"""
Bootstrap de usuário para o painel administrativo (REQ-010, Fase 4).

Cria (ou atualiza login/senha de) um usuário direto no banco, sem passar pela
API — necessário porque, com o gate de autenticação ativo, `POST /api/users`
e `PATCH /api/users/{id}/senha` exigem uma sessão já aberta (não há como
logar pela primeira vez sem já existir um usuário com senha).

Uso (a partir de backend/, com venv ativo):
    python -m scripts.criar_usuario_admin --nome "Beto" --login beto --senha "escolha-uma-senha"

Se já existir um usuário com esse `login`, apenas atualiza nome/senha.
"""

import argparse
import sys

from database import Database
from models import User
from services.auth import hash_senha


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nome", required=True, help="Nome de exibição (ex.: 'Rita')")
    parser.add_argument("--login", required=True, help="Login único (ex.: 'rita')")
    parser.add_argument("--senha", required=True, help="Senha em texto plano (será hasheada)")
    args = parser.parse_args()

    login = args.login.strip().lower()
    if not login:
        print("login não pode ser vazio", file=sys.stderr)
        sys.exit(1)
    if len(args.senha) < 4:
        print("senha deve ter ao menos 4 caracteres", file=sys.stderr)
        sys.exit(1)

    db = Database()
    with db.get_session() as session:
        user = session.query(User).filter_by(login=login).first()
        if user:
            user.nome = args.nome
            user.senha_hash = hash_senha(args.senha)
            acao = "atualizado"
        else:
            user = User(nome=args.nome, login=login, senha_hash=hash_senha(args.senha))
            session.add(user)
            acao = "criado"
        session.flush()
        print(f"Usuário {acao}: id={user.id} nome={user.nome!r} login={user.login!r}")


if __name__ == "__main__":
    main()
