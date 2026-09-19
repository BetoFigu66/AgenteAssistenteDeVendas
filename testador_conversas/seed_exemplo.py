"""Cadastra um cenário de exemplo — só pra ter algo pra rodar de ponta a ponta
na primeira vez. Não é o fluxo normal de cadastro (isso ainda não tem CLI de
criação; cenários novos hoje entram direto via banco/script, igual este)."""

from db import SessionLocal
from models import Cenario, Turno


def main() -> None:
    db = SessionLocal()
    try:
        if db.query(Cenario).filter_by(nome="saudacao_simples").first():
            print("Cenário 'saudacao_simples' já existe.")
            return
        cenario = Cenario(nome="saudacao_simples", descricao="Cliente novo diz oi.")
        db.add(cenario)
        db.flush()
        db.add(Turno(cenario_id=cenario.id, ordem=1, mensagem_enviada="oi"))
        db.commit()
        print(f"Cenário 'saudacao_simples' criado (id={cenario.id}).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
