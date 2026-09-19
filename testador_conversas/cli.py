"""CLI do testador de conversas. Ver README.md."""

from __future__ import annotations

import argparse
import sys

from cliente_backend import ClienteBackend
from db import SessionLocal
from exportar_yaml import exportar_cenario
from models import Cenario, NumeroTeste, ResultadoTurno, StatusNumero
from runner import DecisaoRevisor, TelefoneIndisponivelError, rodar_cenario


def _revisor_cli(mensagem_enviada: str, resposta_observada: str, aceitas: list[str]) -> DecisaoRevisor:
    print("\n" + "=" * 70)
    print(f"Mensagem enviada:  {mensagem_enviada!r}")
    print(f"Resposta observada (NÃO reconhecida):\n  {resposta_observada!r}")
    if aceitas:
        print("Respostas já aceitas para este turno:")
        for a in aceitas:
            print(f"  - {a!r}")
    else:
        print("(nenhuma resposta aceita registrada ainda para este turno)")
    resposta = input("Aceitar esta resposta como válida? [s/N]: ").strip().lower()
    return DecisaoRevisor(aceitar=resposta == "s", motivo="revisao_manual_cli")


def cmd_rodar(args: argparse.Namespace) -> None:
    db = SessionLocal()
    cliente = ClienteBackend()
    try:
        cenario = db.query(Cenario).filter_by(nome=args.nome, ativo=True).first()
        if not cenario:
            print(f"Cenário '{args.nome}' não encontrado (ou inativo).")
            sys.exit(1)
        try:
            execucao = rodar_cenario(db, cenario, cliente, _revisor_cli)
        except TelefoneIndisponivelError as e:
            print(f"Erro: {e}")
            sys.exit(1)
        _imprimir_resumo(db, execucao.id)
    finally:
        cliente.fechar()
        db.close()


def _imprimir_resumo(db, execucao_id: int) -> None:
    resultados = db.query(ResultadoTurno).filter_by(execucao_id=execucao_id).all()
    contagem: dict[str, int] = {}
    for r in resultados:
        contagem[r.veredito.value] = contagem.get(r.veredito.value, 0) + 1
    print("\n" + "=" * 70)
    print(f"Execução {execucao_id} — {len(resultados)} turno(s)")
    for veredito, n in contagem.items():
        print(f"  {veredito}: {n}")


def cmd_cenarios_listar(args: argparse.Namespace) -> None:
    db = SessionLocal()
    try:
        cenarios = db.query(Cenario).order_by(Cenario.nome).all()
        if not cenarios:
            print("Nenhum cenário cadastrado.")
            return
        for c in cenarios:
            marca = "" if c.ativo else " (inativo)"
            print(f"{c.nome}{marca} — {len(c.turnos)} turno(s)")
    finally:
        db.close()


def cmd_numeros_listar(args: argparse.Namespace) -> None:
    db = SessionLocal()
    try:
        numeros = db.query(NumeroTeste).order_by(NumeroTeste.numero).all()
        if not numeros:
            print("Nenhum número cadastrado no pool.")
            return
        for n in numeros:
            print(f"{n.numero} — {n.status.value}")
    finally:
        db.close()


def cmd_numeros_adicionar(args: argparse.Namespace) -> None:
    db = SessionLocal()
    try:
        if db.query(NumeroTeste).filter_by(numero=args.numero).first():
            print("Já cadastrado.")
            return
        db.add(NumeroTeste(numero=args.numero, status=StatusNumero.LIVRE))
        db.commit()
        print(f"Número {args.numero} adicionado ao pool.")
    finally:
        db.close()


def cmd_exportar(args: argparse.Namespace) -> None:
    db = SessionLocal()
    try:
        if args.nome:
            cenario = db.query(Cenario).filter_by(nome=args.nome).first()
            if cenario is None:
                print(f"Cenário '{args.nome}' não encontrado.")
                sys.exit(1)
            cenarios = [cenario]
        else:
            cenarios = db.query(Cenario).order_by(Cenario.nome).all()
        for c in cenarios:
            caminho = exportar_cenario(c)
            print(f"Exportado: {caminho}")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Testador de conversas — CLI")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_rodar = sub.add_parser("rodar", help="Roda um cenário")
    p_rodar.add_argument("nome")
    p_rodar.set_defaults(func=cmd_rodar)

    p_cen = sub.add_parser("cenarios-listar", help="Lista cenários cadastrados")
    p_cen.set_defaults(func=cmd_cenarios_listar)

    p_num_l = sub.add_parser("numeros-listar", help="Lista o pool de números de teste")
    p_num_l.set_defaults(func=cmd_numeros_listar)

    p_num_a = sub.add_parser("numeros-adicionar", help="Adiciona um número ao pool")
    p_num_a.add_argument("numero")
    p_num_a.set_defaults(func=cmd_numeros_adicionar)

    p_exp = sub.add_parser("exportar", help="Exporta cenário(s) para YAML (histórico/backup)")
    p_exp.add_argument("nome", nargs="?", default=None)
    p_exp.set_defaults(func=cmd_exportar)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
