#!/usr/bin/env python3
"""Coloca todos os telefones do banco num formato único: `+55DDD9NNNNNNNN`.

Por que existe: o mesmo cliente aparecia no banco em até três formatos, conforme a porta
de entrada. O WhatsApp entrega `whatsapp:+5519990001234`, a interface web recebia
`19990001234` digitado à mão, e o testador usava outra forma ainda. Como `Mensagem.telefone`
é a chave que o histórico usa, a conversa de uma pessoa ficava partida: em 24/09/2026 o
painel não mostrava nenhuma mensagem vinda do WhatsApp, porque procurava pelo telefone do
contato, gravado noutro formato.

A regra interpreta o número pelo **tamanho**, em vez de completar um prefixo à esquerda.
A diferença não é cosmética: completar à esquerda empurra os dígitos originais para a
direita, e em `1999854265` o `19` que era DDD vira parte do número, com o DDD virando `11`.
Medido antes de escolher: a regra por tamanho acerta 28 de 31 contatos; a de prefixo, 16.

| dígitos | interpretação | resultado |
|---------|---------------|-----------|
| 13 com 55 | já tem DDI | `+` + dígitos |
| 12 com 55 | DDI + DDD + 8 | insere o 9 do celular |
| 11 | DDD + celular | `+55` + dígitos |
| 10 | DDD + 8 dígitos | insere o 9 do celular |
| 9 | celular sem DDD | assume DDD 19 (região da Inforrel) |
| outro | não reconhecido | **não mexe** e reporta |

Uso:
    python scripts/canonizar_telefones.py            # dry-run: mostra e não grava
    python scripts/canonizar_telefones.py --aplicar  # grava
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import Database  # noqa: E402
from sqlalchemy import text  # noqa: E402

DDD_PADRAO = "19"
TABELAS = ("contatos", "mensagens")


def canonizar(telefone: str | None) -> tuple[str | None, str]:
    """Devolve (telefone_canonico, motivo). Mantém o original quando não reconhece."""
    if not telefone:
        return telefone, "vazio"
    digitos = re.sub(r"\D", "", telefone)

    if len(digitos) == 13 and digitos.startswith("55"):
        return "+" + digitos, "ja tinha DDI"
    if len(digitos) == 12 and digitos.startswith("55"):
        return "+55" + digitos[2:4] + "9" + digitos[4:], "DDI+DDD+8, inserido o 9"
    if len(digitos) == 11:
        return "+55" + digitos, "DDD+celular"
    if len(digitos) == 10:
        return "+55" + digitos[:2] + "9" + digitos[2:], "DDD+8, inserido o 9"
    if len(digitos) == 9:
        return "+55" + DDD_PADRAO + digitos, f"sem DDD, assumido {DDD_PADRAO}"
    return telefone, "NAO RECONHECIDO"


def main() -> None:
    aplicar = "--aplicar" in sys.argv
    db = Database()

    with db.get_session() as sessao:
        print("=" * 76)
        print("CANONIZACAO DE TELEFONES" + ("  [APLICANDO]" if aplicar else "  [DRY-RUN]"))
        print("=" * 76)

        total_alteracoes = 0
        nao_reconhecidos: list[tuple[str, int, str]] = []

        for tabela in TABELAS:
            linhas = sessao.execute(text(f"select id, telefone from {tabela} where telefone is not null")).fetchall()
            por_motivo: defaultdict[str, int] = defaultdict(int)
            alteracoes: list[tuple[int, str, str]] = []

            for registro_id, telefone in linhas:
                novo, motivo = canonizar(telefone)
                por_motivo[motivo] += 1
                if motivo == "NAO RECONHECIDO":
                    nao_reconhecidos.append((tabela, registro_id, telefone))
                elif novo != telefone:
                    alteracoes.append((registro_id, telefone, novo))

            print(f"\n{tabela}: {len(linhas)} linhas, {len(alteracoes)} a alterar")
            for motivo, quantidade in sorted(por_motivo.items(), key=lambda item: -item[1]):
                print(f"   {quantidade:4}x {motivo}")

            if aplicar and alteracoes:
                # UPDATE por id, e não em massa por padrão: o mapeamento é calculado em
                # Python (a regra não é expressável em SQL simples sem ficar ilegível) e
                # assim cada linha muda para exatamente o valor que o dry-run mostrou.
                for registro_id, _antigo, novo in alteracoes:
                    sessao.execute(
                        text(f"update {tabela} set telefone = :novo where id = :id"),
                        {"novo": novo, "id": registro_id},
                    )
                print(f"   -> {len(alteracoes)} linhas atualizadas")
            total_alteracoes += len(alteracoes)

        if nao_reconhecidos:
            print(f"\nNAO RECONHECIDOS ({len(nao_reconhecidos)}), mantidos como estão:")
            for tabela, registro_id, telefone in nao_reconhecidos:
                print(f"   {tabela} id={registro_id}: {telefone} ({len(re.sub(r'D', '', telefone))} caracteres)")

        # Colisão de contato é o que exige decisão humana: dois cadastros que viram a
        # mesma pessoa. Detectada sempre, mesmo em dry-run.
        print("\nCOLISOES em contatos (mesmo telefone depois da canonização):")
        destino: defaultdict[str, list] = defaultdict(list)
        for contato_id, telefone, nome in sessao.execute(
            text("select id, telefone, nome from contatos where telefone is not null")
        ).fetchall():
            novo, _ = canonizar(telefone)
            destino[novo].append((contato_id, telefone, nome))
        colisoes = {k: v for k, v in destino.items() if len(v) > 1}
        if not colisoes:
            print("   nenhuma")
        for numero, grupo in colisoes.items():
            print(f"   {numero}:")
            for contato_id, telefone, nome in grupo:
                print(f"      id={contato_id} (era {telefone}) {nome}")

        if aplicar:
            sessao.commit()
            print(f"\nCOMMIT feito. {total_alteracoes} linhas alteradas.")
        else:
            print(f"\nDry-run: nada foi gravado. {total_alteracoes} linhas seriam alteradas.")
            print("Para aplicar: python scripts/canonizar_telefones.py --aplicar")


if __name__ == "__main__":
    main()
