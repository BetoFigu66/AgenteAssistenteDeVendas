"""CLI do testador de conversas. Ver README.md."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cliente_backend import ClienteBackend
from db import SessionLocal
from exportar_yaml import DIR_EXPORTACAO, exportar_cenario
from importar_yaml import YamlInvalidoError, importar_cenario_detalhado, listar_yamls
from models import Cenario, NumeroTeste, ResultadoTurno, StatusNumero, Veredito
from runner import (
    DecisaoRevisor,
    TelefoneIndisponivelError,
    revisor_nao_interativo,
    rodar_cenario,
)


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


def _revisor_varredura(mensagem_enviada: str, resposta_observada: str, aceitas: list[str]) -> DecisaoRevisor:
    """`--nao-interativo`: não pergunta nada, só mostra e rejeita (fica gravado
    em `resultados_turno` para a segunda passada, essa sim interativa)."""
    print(f"  [divergiu] enviado:   {mensagem_enviada!r}")
    print(f"             observado: {resposta_observada!r}")
    return revisor_nao_interativo(mensagem_enviada, resposta_observada, aceitas)


def _escolher_revisor(args: argparse.Namespace):
    return _revisor_varredura if getattr(args, "nao_interativo", False) else _revisor_cli


def cmd_rodar(args: argparse.Namespace) -> None:
    db = SessionLocal()
    cliente = ClienteBackend()
    try:
        cenario = db.query(Cenario).filter_by(nome=args.nome, ativo=True).first()
        if not cenario:
            print(f"Cenário '{args.nome}' não encontrado (ou inativo).")
            sys.exit(1)
        try:
            execucao = rodar_cenario(db, cenario, cliente, _escolher_revisor(args))
        except TelefoneIndisponivelError as e:
            print(f"Erro: {e}")
            sys.exit(1)
        _imprimir_resumo(db, execucao.id)
    finally:
        cliente.fechar()
        db.close()


def cmd_rodar_todos(args: argparse.Namespace) -> None:
    db = SessionLocal()
    cliente = ClienteBackend()
    revisor = _escolher_revisor(args)
    try:
        cenarios = db.query(Cenario).filter_by(ativo=True).order_by(Cenario.nome).all()
        if not cenarios:
            print("Nenhum cenário ativo cadastrado (rode `cli.py importar` antes).")
            return

        placar: list[tuple[str, str]] = []
        for cenario in cenarios:
            print("\n" + "#" * 70)
            print(f"# {cenario.nome} ({len(cenario.turnos)} turno(s))")
            try:
                execucao = rodar_cenario(db, cenario, cliente, revisor)
            except TelefoneIndisponivelError as e:
                print(f"Erro: {e}")
                sys.exit(1)
            except Exception as e:  # um cenário quebrado não derruba a bateria
                db.rollback()
                print(f"  ABORTADO: {type(e).__name__}: {e}")
                placar.append((cenario.nome, "abortado"))
                continue
            _imprimir_resumo(db, execucao.id)
            placar.append((cenario.nome, _situacao_execucao(db, execucao.id)))

        print("\n" + "=" * 70)
        print("PLACAR DA BATERIA")
        for nome, situacao in placar:
            print(f"  {situacao:<10} {nome}")
        divergentes = [n for n, s in placar if s != "ok"]
        print(f"\n{len(placar) - len(divergentes)}/{len(placar)} cenário(s) sem divergência.")
        if divergentes:
            print("Revisar (rodar de novo sem --nao-interativo):")
            for nome in divergentes:
                print(f"  python cli.py rodar {nome}")
    finally:
        cliente.fechar()
        db.close()


def _situacao_execucao(db, execucao_id: int) -> str:
    """'ok' quando nenhum turno foi rejeitado; senão, quantos divergiram."""
    resultados = db.query(ResultadoTurno).filter_by(execucao_id=execucao_id).all()
    rejeitados = [r for r in resultados if r.veredito == Veredito.REJEITADO]
    return "ok" if not rejeitados else f"{len(rejeitados)} div."


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


def cmd_numeros_liberar(args: argparse.Namespace) -> None:
    """Devolve ao pool um número preso em EM_USO, que é o que sobra quando uma
    execução morre no meio (o `finally` do runner não chega a rodar)."""
    db = SessionLocal()
    try:
        numero = db.query(NumeroTeste).filter_by(numero=args.numero).first()
        if numero is None:
            print(f"Número {args.numero} não está no pool.")
            sys.exit(1)

        if not args.sem_limpar:
            cliente = ClienteBackend()
            try:
                cliente.limpar_telefone(args.numero)
                print("Limpeza dos dados do telefone pedida ao backend.")
            except Exception as e:
                print(
                    f"Aviso: não consegui limpar os dados no backend ({type(e).__name__}: {e}). "
                    "O número é liberado mesmo assim; repita com o backend no ar se quiser "
                    "a conversa zerada, ou use --sem-limpar."
                )
            finally:
                cliente.fechar()

        numero.status = StatusNumero.LIVRE
        numero.cenario_atual_id = None
        db.commit()
        print(f"Número {args.numero} liberado.")
    finally:
        db.close()


def cmd_importar(args: argparse.Namespace) -> None:
    caminhos = _resolver_caminhos_importacao(args.alvo)
    if not caminhos:
        print("Nenhum arquivo .yaml encontrado para importar.")
        sys.exit(1)

    db = SessionLocal()
    try:
        contagem: dict[str, int] = {}
        for caminho in caminhos:
            try:
                resultado = importar_cenario_detalhado(db, caminho, atualizar=args.atualizar)
            except YamlInvalidoError as e:
                print(f"ERRO: {e}")
                sys.exit(1)
            contagem[resultado.acao] = contagem.get(resultado.acao, 0) + 1
            print(f"{resultado.acao:<11} {resultado.cenario.nome} ({len(resultado.cenario.turnos)} turno(s))")
        print("\n" + ", ".join(f"{n} {acao}" for acao, n in sorted(contagem.items())))
        if contagem.get("pulado"):
            print("(cenário já existente é preservado; use --atualizar para sobrescrever pelo YAML)")
    finally:
        db.close()


def _resolver_caminhos_importacao(alvo: str | None) -> list[Path]:
    """Aceita: nada (o diretório padrão), um diretório, um arquivo, ou só o nome
    do cenário (resolvido como `cenarios_exportados/<nome>.yaml`)."""
    if not alvo:
        return listar_yamls(DIR_EXPORTACAO)
    caminho = Path(alvo)
    if caminho.is_dir():
        return listar_yamls(caminho)
    if caminho.is_file():
        return [caminho]
    candidato = DIR_EXPORTACAO / f"{alvo}.yaml"
    if candidato.is_file():
        return [candidato]
    print(f"Não encontrei '{alvo}' (nem como arquivo, nem como {candidato}).")
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Testador de conversas — CLI")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_rodar = sub.add_parser("rodar", help="Roda um cenário")
    p_rodar.add_argument("nome")
    p_rodar.add_argument(
        "--nao-interativo",
        action="store_true",
        help="Não pergunta nada: rejeita e registra o que divergir.",
    )
    p_rodar.set_defaults(func=cmd_rodar)

    p_todos = sub.add_parser("rodar-todos", help="Roda todos os cenários ativos, em ordem alfabética")
    p_todos.add_argument(
        "--nao-interativo",
        action="store_true",
        help="Varredura: rejeita e registra tudo que divergir, sem parar para perguntar.",
    )
    p_todos.set_defaults(func=cmd_rodar_todos)

    p_cen = sub.add_parser("cenarios-listar", help="Lista cenários cadastrados")
    p_cen.set_defaults(func=cmd_cenarios_listar)

    p_num_l = sub.add_parser("numeros-listar", help="Lista o pool de números de teste")
    p_num_l.set_defaults(func=cmd_numeros_listar)

    p_num_a = sub.add_parser("numeros-adicionar", help="Adiciona um número ao pool")
    p_num_a.add_argument("numero")
    p_num_a.set_defaults(func=cmd_numeros_adicionar)

    p_num_lib = sub.add_parser(
        "numeros-liberar", help="Devolve ao pool um número travado em EM_USO (execução abortada)"
    )
    p_num_lib.add_argument("numero")
    p_num_lib.add_argument(
        "--sem-limpar",
        action="store_true",
        help="Não tenta apagar os dados do telefone no backend (use com o backend fora do ar).",
    )
    p_num_lib.set_defaults(func=cmd_numeros_liberar)

    p_exp = sub.add_parser("exportar", help="Exporta cenário(s) para YAML (histórico/backup)")
    p_exp.add_argument("nome", nargs="?", default=None)
    p_exp.set_defaults(func=cmd_exportar)

    p_imp = sub.add_parser("importar", help="Importa cenário(s) de YAML para o banco")
    p_imp.add_argument(
        "alvo",
        nargs="?",
        default=None,
        help="Arquivo, diretório ou nome do cenário. Sem argumento: todo o cenarios_exportados/.",
    )
    p_imp.add_argument(
        "--atualizar",
        action="store_true",
        help="Sobrescreve pelo YAML um cenário que já exista (o padrão é pular).",
    )
    p_imp.set_defaults(func=cmd_importar)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
