"""
Sugestão de documentos fonte em docs/FoldersProdutos/ para o [curador_conhecimento].

Estratégia em camadas (REQ-003 / curadoria):
1. Trechos RAG do diagnóstico — metadata.arquivo quando origem folder_produto.
2. Entidades extraídas pelo classificador (tipos_produto).
3. Overlap de tokens da pergunta com nomes de arquivo do inventário RAG.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Optional

_STOPWORDS = frozenset({
    "a", "o", "e", "de", "da", "do", "das", "dos", "em", "no", "na", "nos", "nas",
    "um", "uma", "os", "as", "que", "para", "com", "por", "se", "eu", "me", "te",
    "voce", "voces", "qual", "quais", "como", "onde", "tem", "ter", "ser", "esta",
    "este", "isso", "essa", "esse", "ao", "aos", "ou", "mais", "menos", "sobre",
})

_TIPO_PRODUTO_ARQUIVOS: dict[str, list[str]] = {
    "relogio_ponto": [
        "docs/FoldersProdutos/Relógio de ponto.txt",
        "docs/FoldersProdutos/folder-controle-de-ponto.txt",
        "docs/FoldersProdutos/folder-relogio-ponto-eletronico.txt",
        "docs/FoldersProdutos/folder-relogio-ponto-cartografico.txt",
    ],
    "catraca": [
        "docs/FoldersProdutos/Catracas.txt",
        "docs/FoldersProdutos/folder-catraca-de-acesso-fit.txt",
    ],
    "controle_acesso": [
        "docs/FoldersProdutos/Controle de Acesso.txt",
        "docs/FoldersProdutos/folder-controle-de-acesso.txt",
    ],
}


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return texto.lower()


def _tokens(texto: str) -> set[str]:
    partes = re.findall(r"[a-z0-9]+", _normalizar(texto))
    return {p for p in partes if len(p) > 2 and p not in _STOPWORDS}


def _carregar_inventario_folder(projeto_root: Path) -> list[dict[str, Any]]:
    inventario_path = projeto_root / "backend" / "data" / "rag" / "inventario_fontes.json"
    if inventario_path.is_file():
        try:
            dados = json.loads(inventario_path.read_text(encoding="utf-8"))
            return [
                f for f in dados.get("fontes", [])
                if f.get("tipo_fonte") == "folder_produto"
            ]
        except (json.JSONDecodeError, OSError):
            pass

    pasta = projeto_root / "docs" / "FoldersProdutos"
    if not pasta.is_dir():
        return []
    return [
        {
            "caminho": str(arquivo.relative_to(projeto_root)).replace("\\", "/"),
            "nome_arquivo": arquivo.name,
            "tipo_fonte": "folder_produto",
        }
        for arquivo in sorted(pasta.glob("*.txt"))
    ]


def _preview_arquivo(projeto_root: Path, caminho_relativo: str, max_chars: int = 600) -> Optional[str]:
    path = projeto_root / caminho_relativo.replace("/", "\\") \
        if "\\" in str(projeto_root) \
        else projeto_root / caminho_relativo
    if not path.is_file():
        return None
    try:
        texto = path.read_text(encoding="utf-8", errors="replace")
        return texto[:max_chars].strip()
    except OSError:
        return None


def sugerir_documentos_fonte(
    pergunta: str,
    rag_candidatos: list[dict[str, Any]],
    tipos_produto: Optional[list[str]] = None,
    projeto_root: Optional[Path] = None,
    max_arquivos: int = 5,
) -> list[dict[str, Any]]:
    """
    Retorna lista ordenada de arquivos em docs/FoldersProdutos/ relevantes para a pergunta.

    Cada item: caminho, motivo, score, existe_no_disco, preview (opcional).
    """
    root = projeto_root or Path(__file__).resolve().parents[3]
    candidatos: dict[str, dict[str, Any]] = {}
    prioridade_rag: list[str] = []
    tokens_pergunta = _tokens(pergunta)

    def _adicionar(caminho: str, motivo: str, score: float, prioridade: bool = False) -> None:
        caminho_norm = caminho.replace("\\", "/")
        if not caminho_norm.lower().startswith("docs/foldersprodutos/"):
            return
        if prioridade and caminho_norm not in prioridade_rag:
            prioridade_rag.append(caminho_norm)
        atual = candidatos.get(caminho_norm)
        if atual is None or score > atual["score"]:
            candidatos[caminho_norm] = {
                "caminho": caminho_norm,
                "motivo": motivo,
                "score": round(score, 4),
            }

    for trecho in rag_candidatos or []:
        meta = trecho.get("metadata") or trecho.get("metadados") or {}
        arquivo = meta.get("arquivo")
        if arquivo:
            _adicionar(arquivo, "trecho_rag_diagnostico", 1.0, prioridade=True)

    for tipo in tipos_produto or []:
        for arquivo in _TIPO_PRODUTO_ARQUIVOS.get(tipo, []):
            _adicionar(arquivo, f"entidade_tipo_produto:{tipo}", 0.9)

    inventario = _carregar_inventario_folder(root)
    for fonte in inventario:
        caminho = fonte.get("caminho", "").replace("\\", "/")
        nome = fonte.get("nome_arquivo") or Path(caminho).name
        tokens_nome = _tokens(nome)
        if not tokens_nome:
            continue
        overlap = tokens_pergunta & tokens_nome
        if not overlap:
            continue
        score_overlap = len(overlap) / max(len(tokens_pergunta), 1)
        _adicionar(caminho, f"overlap_tokens:{','.join(sorted(overlap))}", 0.4 + score_overlap)

    vistos: set[str] = set()
    ordenados: list[dict[str, Any]] = []
    for caminho_prio in prioridade_rag:
        if caminho_prio in candidatos and caminho_prio not in vistos:
            ordenados.append(candidatos[caminho_prio])
            vistos.add(caminho_prio)
    demais = sorted(
        (v for k, v in candidatos.items() if k not in vistos),
        key=lambda x: x["score"],
        reverse=True,
    )
    ordenados.extend(demais[: max(0, max_arquivos - len(ordenados))])
    resultado: list[dict[str, Any]] = []
    for item in ordenados:
        caminho = item["caminho"]
        path_abs = root / caminho
        preview = _preview_arquivo(root, caminho)
        resultado.append({
            **item,
            "existe_no_disco": path_abs.is_file(),
            "preview": preview,
        })
    return resultado
