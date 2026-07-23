"""
Gera inventario das fontes iniciais da RAG.

O inventario registra os arquivos raw usados como entrada para as proximas etapas:
- docs/FoldersProdutos
- WebScrapping/result
- docs/ConversasDoWhatsApp

Saida padrao:
    backend/data/rag/inventario_fontes.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

RAIZ_PROJETO = Path(__file__).resolve().parents[3]
SAIDA_PADRAO = RAIZ_PROJETO / "backend" / "data" / "rag" / "inventario_fontes.json"

FONTES_PADRAO = {
    "folder_produto": RAIZ_PROJETO / "docs" / "FoldersProdutos",
    "webscraping": RAIZ_PROJETO / "WebScrapping" / "result",
    "conversa_whatsapp": RAIZ_PROJETO / "docs" / "ConversasDoWhatsApp",
}

URL_RE = re.compile(r"https?://[^\s)>\]]+")


@dataclass(frozen=True)
class FonteInventario:
    caminho: str
    nome_arquivo: str
    tipo_fonte: str
    extensao: str
    tamanho_bytes: int
    sha256_bruto: str
    urls: list[str]
    url_principal: str | None


def calcular_sha256(caminho: Path) -> str:
    hash_obj = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            hash_obj.update(bloco)
    return hash_obj.hexdigest()


def ler_texto_para_urls(caminho: Path) -> str:
    if caminho.suffix.lower() not in {".txt", ".md", ".json", ".csv"}:
        return ""

    bruto = caminho.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return bruto.decode(encoding)
        except UnicodeDecodeError:
            continue
    return bruto.decode("utf-8", errors="ignore")


def extrair_urls(caminho: Path) -> list[str]:
    texto = ler_texto_para_urls(caminho)
    urls = URL_RE.findall(texto)
    return list(dict.fromkeys(urls))


def iterar_arquivos(tipo_fonte: str, diretorio: Path) -> Iterable[FonteInventario]:
    if not diretorio.exists():
        return

    for caminho in sorted(diretorio.rglob("*")):
        if not caminho.is_file():
            continue

        urls = extrair_urls(caminho)
        yield FonteInventario(
            caminho=caminho.relative_to(RAIZ_PROJETO).as_posix(),
            nome_arquivo=caminho.name,
            tipo_fonte=tipo_fonte,
            extensao=caminho.suffix.lower(),
            tamanho_bytes=caminho.stat().st_size,
            sha256_bruto=calcular_sha256(caminho),
            urls=urls,
            url_principal=urls[0] if urls else None,
        )


def gerar_inventario() -> dict:
    fontes = []
    diretorios_ausentes = []

    for tipo_fonte, diretorio in FONTES_PADRAO.items():
        if not diretorio.exists():
            diretorios_ausentes.append(diretorio.relative_to(RAIZ_PROJETO).as_posix())
            continue
        fontes.extend(asdict(item) for item in iterar_arquivos(tipo_fonte, diretorio))

    por_tipo = Counter(item["tipo_fonte"] for item in fontes)
    por_extensao = Counter(item["extensao"] or "(sem extensao)" for item in fontes)

    return {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "raiz_projeto": str(RAIZ_PROJETO),
        "diretorios": {tipo: caminho.relative_to(RAIZ_PROJETO).as_posix() for tipo, caminho in FONTES_PADRAO.items()},
        "diretorios_ausentes": diretorios_ausentes,
        "resumo": {
            "total_arquivos": len(fontes),
            "por_tipo_fonte": dict(sorted(por_tipo.items())),
            "por_extensao": dict(sorted(por_extensao.items())),
            "arquivos_com_url": sum(1 for item in fontes if item["urls"]),
        },
        "fontes": fontes,
    }


def salvar_inventario(inventario: dict, saida: Path) -> None:
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(
        json.dumps(inventario, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera inventario das fontes da RAG.")
    parser.add_argument(
        "--saida",
        type=Path,
        default=SAIDA_PADRAO,
        help=f"Caminho do JSON de saida. Padrao: {SAIDA_PADRAO}",
    )
    args = parser.parse_args()

    saida = args.saida
    if not saida.is_absolute():
        saida = RAIZ_PROJETO / saida

    inventario = gerar_inventario()
    salvar_inventario(inventario, saida)

    resumo = inventario["resumo"]
    print(f"Inventario gerado em: {saida}")
    print(f"Total de arquivos: {resumo['total_arquivos']}")
    print(f"Por tipo de fonte: {resumo['por_tipo_fonte']}")
    print(f"Por extensao: {resumo['por_extensao']}")
    print(f"Arquivos com URL: {resumo['arquivos_com_url']}")
    if inventario["diretorios_ausentes"]:
        print(f"Diretorios ausentes: {inventario['diretorios_ausentes']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
