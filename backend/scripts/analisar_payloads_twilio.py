#!/usr/bin/env python3
"""Compara os payloads reais capturados da Twilio com o que o nosso código declara esperar.

Motivo de existir: todo teste de webhook deste projeto monta o formulário à mão, com os
campos que *supomos* que a Twilio manda. Este script fecha a volta, confrontando a suposição
com o que chegou de verdade enquanto a conta trial existiu.

Ele responde três perguntas, e a segunda é a que costuma surpreender:

1. Que campos o nosso endpoint declara e **não** vieram? (suposição a mais)
2. Que campos vieram e nós **ignoramos**? (informação que está sendo jogada fora)
3. Que valores cada campo assume na prática? (o formato real, não o documentado)

A lista de campos esperados é lida por **introspecção da assinatura** dos endpoints, não
copiada para cá: uma lista copiada envelheceria no primeiro parâmetro novo, e o script
passaria a mentir exatamente sobre o que deveria vigiar.

Uso:
    python scripts/analisar_payloads_twilio.py [caminho.jsonl]

Sem argumento, usa `TWILIO_CAPTURA_ARQUIVO` do .env (default `logs/payloads_twilio.jsonl`).
"""

from __future__ import annotations

import inspect
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings  # noqa: E402

# Campos que a Twilio manda em toda requisição e que não dizem respeito à mensagem em si.
# Ficam fora de "ignorados" para o relatório não virar ruído.
_RUIDO = {"AccountSid", "ApiVersion", "SmsMessageSid", "SmsSid", "SmsStatus", "MessageSid"}


def _campos_declarados(funcao) -> set[str]:
    """Nomes dos parâmetros do endpoint, que é o que ele sabe receber.

    Ignora `request` e afins: só interessam os que viram campo de formulário.
    """
    return {
        nome
        for nome in inspect.signature(funcao).parameters
        if nome not in ("request", "mensagem_id")
    }


def _carregar(caminho: Path) -> list[dict]:
    if not caminho.exists():
        print(f"Arquivo não encontrado: {caminho}")
        print("A captura está ligada? Precisa de TWILIO_CAPTURAR_PAYLOADS=true no .env.")
        sys.exit(1)
    registros = []
    for numero, linha in enumerate(caminho.read_text(encoding="utf-8").splitlines(), 1):
        linha = linha.strip()
        if not linha:
            continue
        try:
            registros.append(json.loads(linha))
        except json.JSONDecodeError:
            print(f"  (linha {numero} ilegível, ignorada)")
    return registros


def main() -> None:
    caminho = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(settings.TWILIO_CAPTURA_ARQUIVO)
    registros = _carregar(caminho)
    if not registros:
        print(f"Nenhum payload em {caminho}.")
        return

    import main as app_main

    esperados_por_endpoint = {
        "/webhook": _campos_declarados(app_main.webhook_twilio),
        "/webhook/status": _campos_declarados(app_main.webhook_status_twilio),
    }

    por_endpoint: dict[str, list[dict]] = defaultdict(list)
    for registro in registros:
        por_endpoint[registro.get("endpoint", "?")].append(registro)

    print(f"\n{len(registros)} payload(s) em {caminho}\n")

    for endpoint, itens in sorted(por_endpoint.items()):
        esperados = esperados_por_endpoint.get(endpoint, set())
        vistos: Counter = Counter()
        valores: dict[str, set[str]] = defaultdict(set)
        for item in itens:
            for chave, valor in item.get("form", {}).items():
                vistos[chave] += 1
                if len(valores[chave]) < 6:
                    valores[chave].add(str(valor)[:60])

        print("=" * 78)
        print(f"{endpoint} — {len(itens)} chamada(s)")
        print("=" * 78)

        nunca_vieram = sorted(esperados - set(vistos))
        if nunca_vieram:
            print("\n  Declarados pelo endpoint e NUNCA recebidos:")
            for campo in nunca_vieram:
                print(f"    - {campo}")
            print("    (pode ser campo opcional que não ocorreu nestes testes, ou suposição errada)")

        ignorados = sorted(set(vistos) - esperados - _RUIDO)
        if ignorados:
            print("\n  Recebidos e IGNORADOS pelo nosso código:")
            for campo in ignorados:
                exemplos = " | ".join(sorted(valores[campo])[:3])
                print(f"    - {campo}  ({vistos[campo]}x)  ex.: {exemplos}")
            print("    (informação que a Twilio manda e estamos jogando fora)")

        print("\n  Todos os campos recebidos, por frequência:")
        for campo, n in vistos.most_common():
            marca = "ok " if campo in esperados else ("   " if campo in _RUIDO else "NOVO")
            exemplos = " | ".join(sorted(valores[campo])[:2])
            print(f"    {marca} {campo:32} {n:3}x  {exemplos}")
        print()


if __name__ == "__main__":
    main()
