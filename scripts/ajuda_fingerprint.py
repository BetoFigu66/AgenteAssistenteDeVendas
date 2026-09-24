"""
Impressao digital do texto visivel das telas, para detectar ajuda desatualizada.

Problema que resolve: os textos de ajuda em `frontend/src/ajuda/*.md` descrevem o que
o usuario ve em cada tela. Quando a tela muda, o texto envelhece silenciosamente.

Estrategia: em vez de vigiar o arquivo do componente inteiro (o que dispararia em
qualquer refatoracao), extraimos apenas as **strings que o usuario ve** — texto entre
tags JSX e atributos textuais (`title`, `placeholder`, `aria-label`, `alt`, `label`) —
e guardamos um hash por tela em `frontend/src/ajuda/_fontes.json`.

Renomear um botao muda o hash. Renomear uma variavel, nao.

Quando o hash divergir, quem alterou a tela decide:
  - o texto de ajuda precisa mudar -> edita o `.md` e roda `--atualizar`;
  - o texto continua correto        -> roda so `--atualizar` (reconhecimento explicito).

Uso:
    python scripts/ajuda_fingerprint.py              # verifica (exit 1 se divergir)
    python scripts/ajuda_fingerprint.py --atualizar  # regrava os hashes (re-baseline)

Rodado tambem pelo check `ajuda-telas-desatualizada` do QA Engineer
(`agentes/qa_engineer.py`), com severidade `warning` — nao bloqueia commit.

Limitacoes conhecidas (aceitas de proposito, para manter o sinal limpo):
  - Texto vindo de mapas em JS (ex.: `const FASE_LABELS = {...}` em
    `utils/atendimento.js`) nao e capturado: caberia junto de centenas de strings
    tecnicas (paths de import, nomes de classe) e afogaria o sinal.
  - As strings sao ordenadas antes do hash, entao reordenar elementos na tela sem
    alterar o texto nao dispara aviso.
  - Texto montado dinamicamente dentro de `{...}` e ignorado.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, NamedTuple

RAIZ = Path(__file__).resolve().parent.parent
FRONTEND = RAIZ / "frontend"
MANIFESTO = FRONTEND / "src" / "ajuda" / "_fontes.json"

# Texto entre tags JSX. Deliberadamente NAO removemos os `{...}` do arquivo inteiro
# antes de casar: em React quase todo texto fica dentro de um `map()`/condicional, e
# colapsar as chaves globalmente apagaria justamente o texto que queremos.
_RE_TEXTO_TAG = re.compile(r">([^<>]+)<")
# `{expressao}` balanceada dentro de um fragmento de texto ja isolado.
_RE_EXPRESSAO_LOCAL = re.compile(r"\{[^{}]*\}")
# Atributos que chegam aos olhos do usuario (tooltip, placeholder, leitor de tela).
_RE_ATTR_TEXTO = re.compile(r'\b(?:title|placeholder|aria-label|alt|label)\s*=\s*"([^"]*)"')
# Descarta separadores e simbolos soltos ("—", "•", ":").
_RE_TEM_LETRA = re.compile(r"[A-Za-zÀ-ÿ]")
# Um no de texto entre duas tags pode conter codigo de ternario JSX — ex.: o
# `) : parametros.length === 0 ? (` que fica entre `</p>` e `<p`. E codigo, muda em
# refatoracao e nao e visto pelo usuario: exatamente o falso positivo a evitar.
_MARCADORES_CODIGO = ("===", "!==", "=>", "&&", "||", ") :", "? (", ";")


class Divergencia(NamedTuple):
    """Tela cujo texto visivel mudou desde o ultimo re-baseline."""

    tela: str
    hash_registrado: str
    hash_atual: str
    arquivo_ajuda: str


def _normalizar(texto: str) -> str:
    return " ".join(texto.split())


def extrair_texto_visivel(conteudo: str) -> List[str]:
    """Extrai as strings que o usuario ve num arquivo JSX."""
    # Atributos com valor literal; os `{dinamicos}` nao casam e ficam de fora.
    fragmentos = _RE_ATTR_TEXTO.findall(conteudo)
    # Nos de texto: o proprio `[^<>]+` para na tag seguinte, entao cada fragmento
    # e local — texto dentro de `map()`/condicional continua sendo capturado.
    fragmentos += _RE_TEXTO_TAG.findall(conteudo)

    limpos = set()
    for bruto in fragmentos:
        # `>{total} par(es) total<` -> "par(es) total"
        t = _normalizar(_RE_EXPRESSAO_LOCAL.sub(" ", bruto))
        # Chave solta indica fragmento partido no meio de uma expressao
        # (ex.: `{p.descricao || ` de `{p.descricao || <span>—</span>}`): e ruido.
        if "{" in t or "}" in t:
            continue
        if any(marcador in t for marcador in _MARCADORES_CODIGO):
            continue
        if len(t) >= 2 and _RE_TEM_LETRA.search(t):
            limpos.add(t)
    return sorted(limpos)


def calcular_hash(componentes: List[str]) -> str:
    """Hash das strings visiveis de todos os componentes de uma tela."""
    todos: List[str] = []
    for rel in componentes:
        caminho = FRONTEND / rel
        if not caminho.exists():
            raise FileNotFoundError(rel)
        todos.extend(extrair_texto_visivel(caminho.read_text(encoding="utf-8")))
    assinatura = "\n".join(sorted(set(todos)))
    return hashlib.sha256(assinatura.encode("utf-8")).hexdigest()[:16]


def carregar_manifesto() -> Dict:
    if not MANIFESTO.exists():
        raise FileNotFoundError(f"Manifesto nao encontrado: {MANIFESTO}")
    return json.loads(MANIFESTO.read_text(encoding="utf-8"))


def _salvar_manifesto(manifesto: Dict) -> None:
    MANIFESTO.write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def verificar() -> tuple[List[Divergencia], List[str]]:
    """
    Compara os hashes registrados com o estado atual dos componentes.

    Returns:
        (divergencias, erros) — `erros` lista componentes mapeados que nao existem
        mais (mapeamento do manifesto apodreceu).
    """
    manifesto = carregar_manifesto()
    divergencias: List[Divergencia] = []
    erros: List[str] = []

    for tela, dados in sorted(manifesto.get("telas", {}).items()):
        componentes = dados.get("componentes", [])
        try:
            atual = calcular_hash(componentes)
        except FileNotFoundError as exc:
            erros.append(f"tela '{tela}': componente inexistente: {exc}")
            continue
        registrado = dados.get("hash", "")
        if atual != registrado:
            divergencias.append(
                Divergencia(
                    tela=tela,
                    hash_registrado=registrado or "(vazio)",
                    hash_atual=atual,
                    arquivo_ajuda=f"frontend/src/ajuda/{tela}.md",
                )
            )
    return divergencias, erros


def atualizar() -> List[str]:
    """Regrava os hashes a partir do estado atual. Retorna as telas alteradas."""
    manifesto = carregar_manifesto()
    alteradas: List[str] = []

    for tela, dados in manifesto.get("telas", {}).items():
        try:
            atual = calcular_hash(dados.get("componentes", []))
        except FileNotFoundError as exc:
            print(f"AVISO tela '{tela}': componente inexistente ({exc}); hash mantido.")
            continue
        if dados.get("hash") != atual:
            dados["hash"] = atual
            alteradas.append(tela)

    if alteradas:
        _salvar_manifesto(manifesto)
    return alteradas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument(
        "--atualizar",
        action="store_true",
        help="Regrava os hashes com o estado atual das telas (re-baseline).",
    )
    args = parser.parse_args()

    if args.atualizar:
        alteradas = atualizar()
        if alteradas:
            print(f"Hashes atualizados: {', '.join(sorted(alteradas))}")
            print(f"Nao esqueca de 'git add {MANIFESTO.relative_to(RAIZ).as_posix()}'")
        else:
            print("Nenhum hash precisava ser atualizado.")
        return 0

    divergencias, erros = verificar()

    for erro in erros:
        print(f"ERRO {erro}")

    if not divergencias:
        print("Texto visivel das telas bate com os hashes registrados.")
        return 1 if erros else 0

    print(f"{len(divergencias)} tela(s) com texto visivel alterado desde o ultimo re-baseline:\n")
    for d in divergencias:
        print(f"  - {d.tela}: revise {d.arquivo_ajuda}")
        print(f"      hash registrado={d.hash_registrado} atual={d.hash_atual}")
    print(
        "\nSe o texto de ajuda continua correto, rode:\n"
        "  python scripts/ajuda_fingerprint.py --atualizar"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
