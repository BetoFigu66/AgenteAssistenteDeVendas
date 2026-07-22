"""
Pre-processa fontes raw da RAG para documentos normalizados em JSONL.

Entrada padrao:
    backend/data/rag/inventario_fontes.json

Saidas padrao:
    backend/data/rag/documentos_normalizados.jsonl
    backend/data/rag/preprocessamento_resumo.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RAIZ_PROJETO = Path(__file__).resolve().parents[3]
INVENTARIO_PADRAO = RAIZ_PROJETO / "backend" / "data" / "rag" / "inventario_fontes.json"
SAIDA_PADRAO = RAIZ_PROJETO / "backend" / "data" / "rag" / "documentos_normalizados.jsonl"
RESUMO_PADRAO = RAIZ_PROJETO / "backend" / "data" / "rag" / "preprocessamento_resumo.json"

URL_RE = re.compile(r"https?://[^\s)>\]]+")
WHATSAPP_MSG_RE = re.compile(r"^(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})\s+-\s+([^:]+):\s?(.*)$")
PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")
EMAIL_RE = re.compile(r"[\w.\-+]+@[\w.\-]+\.\w+")
ENDERECO_RE = re.compile(
    r"\b(rua|r\.|avenida|av\.|alameda|travessa|rodovia|estrada|praça|praca)\b",
    re.IGNORECASE,
)

LINHAS_WEB_DESCARTAR = {
    "ir para o conteúdo",
    "popular keywords",
    "categories",
    "no record found",
    "ver mais",
    "início",
    "quem somos",
    "nossos serviços",
    "controle de acessos",
    "controle de ponto",
    "assistênciatécnica",
    "assistência técnica",
    "produtos",
    "câmeras",
    "roteadores",
    "softwares",
    "cancelas",
    "soluções especiais",
    "para comércios em geral",
    "para clubes",
    "para academias",
    "blog",
    "contato",
    "menu",
    "×",
    "compartilhe",
    "newsletter",
    "enviar",
    "solicite uma proposta",
    "baixe o folder",
    "facebook",
    "instagram",
    "linkedin",
    "políticas de privacidade",
    "desenvolvido por:",
    "© todos os direitos reservados",
}

MARCADORES_RODAPE_WEB = {
    "newsletter",
    "quem somos",
    "central de",
    "mapa do site",
    "redes sociais",
    "gerenciar o consentimento",
}

LINHAS_CONVERSA_SISTEMA = (
    "As mensagens e ligações são protegidas com a criptografia",
    "As mensagens e ligacoes sao protegidas com a criptografia",
)

TRECHOS_PROMOCIONAIS_WEB = (
    "preço que você procura",
    "preco que voce procura",
)


def ler_json(caminho: Path) -> dict[str, Any]:
    return json.loads(caminho.read_text(encoding="utf-8"))


def ler_texto(caminho: Path) -> str:
    bruto = caminho.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return bruto.decode(encoding)
        except UnicodeDecodeError:
            continue
    return bruto.decode("utf-8", errors="ignore")


def normalizar_espacos(texto: str) -> str:
    texto = texto.replace("\ufeff", "")
    texto = texto.replace("\u200e", "")
    texto = texto.replace("\xa0", " ")
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def hash_texto(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def slug_do_arquivo(caminho_relativo: str) -> str:
    return Path(caminho_relativo).stem.lower().replace(" ", "-")


def slug_seguro(fonte: dict[str, Any]) -> str:
    if fonte["tipo_fonte"] == "conversa_whatsapp":
        return f"conversa-whatsapp-{fonte['sha256_bruto'][:12]}"
    return slug_do_arquivo(fonte["caminho"])


def caminho_metadata(fonte: dict[str, Any]) -> str:
    if fonte["tipo_fonte"] == "conversa_whatsapp":
        return "docs/ConversasDoWhatsApp/[CONVERSA_WHATSAPP].txt"
    return fonte["caminho"]


def inferir_tipo(fonte: dict[str, Any]) -> str:
    caminho = fonte["caminho"]
    nome = fonte["nome_arquivo"].lower()
    tipo_fonte = fonte["tipo_fonte"]

    if tipo_fonte == "conversa_whatsapp":
        return "conversa"
    if tipo_fonte == "folder_produto":
        return "produto" if nome.startswith("folder-") else "indice_produto"
    if nome.startswith("produtos_"):
        return "produto"
    if nome.startswith("categoria-de-produto_"):
        return "categoria_produto"
    if nome.startswith("blog"):
        return "blog"
    if "solucoes-especiais" in caminho:
        return "solucao"
    return "institucional"


def titulo_por_arquivo(fonte: dict[str, Any], linhas_limpas: list[str]) -> str:
    for linha in linhas_limpas[:8]:
        if linha.startswith("URL:"):
            continue
        if set(linha) == {"="}:
            continue
        titulo = linha.removesuffix(" - Inforrel").strip()
        if titulo:
            return titulo
    return Path(fonte["nome_arquivo"]).stem.replace("_", " ").replace("-", " ").strip().title()


def limpar_linhas_basico(texto: str) -> list[str]:
    linhas = []
    for linha in normalizar_espacos(texto).split("\n"):
        linha = linha.strip()
        if not linha:
            if linhas and linhas[-1] != "":
                linhas.append("")
            continue
        linhas.append(linha)
    while linhas and linhas[-1] == "":
        linhas.pop()
    return linhas


def limpar_webscraping(texto: str) -> tuple[str, dict[str, Any]]:
    linhas = limpar_linhas_basico(texto)
    removidas = 0
    inicio = 0

    for indice, linha in enumerate(linhas):
        if linha.lower() == "compartilhe":
            inicio = indice + 1
            break

    linhas_saida = []
    for linha in linhas[inicio:]:
        lower = linha.lower()
        if lower.startswith("url:") or set(linha) == {"="}:
            removidas += 1
            continue
        if lower in MARCADORES_RODAPE_WEB and linhas_saida:
            break
        if lower in LINHAS_WEB_DESCARTAR:
            removidas += 1
            continue
        if any(trecho in lower for trecho in TRECHOS_PROMOCIONAIS_WEB):
            removidas += 1
            continue
        if PHONE_RE.fullmatch(linha) or EMAIL_RE.fullmatch(linha):
            removidas += 1
            continue
        linhas_saida.append(linha)

    return normalizar_espacos("\n".join(linhas_saida)), {"linhas_removidas": removidas}


def limpar_folder(texto: str) -> tuple[str, dict[str, Any]]:
    linhas = limpar_linhas_basico(texto)
    linhas_saida = []
    removidas = 0

    for linha in linhas:
        lower = linha.lower()
        if lower.startswith("--- página"):
            removidas += 1
            continue
        if lower.startswith("central de atendimento:") or lower == "www.topdata.com.br":
            removidas += 1
            continue
        if lower in {"revendedor autorizado:", "topdata"}:
            removidas += 1
            continue
        linhas_saida.append(linha)

    return normalizar_espacos("\n".join(linhas_saida)), {"linhas_removidas": removidas}


def anonimizar_texto_conversa(texto: str) -> str:
    if ENDERECO_RE.search(texto):
        return "[ENDERECO]"
    texto = PHONE_RE.sub("[TELEFONE]", texto)
    texto = EMAIL_RE.sub("[EMAIL]", texto)
    texto = re.sub(r"\b\d{2,5}[-\s]\d{2,5}\b", "[NUMERO]", texto)
    texto = re.sub(r"\b\d{2,}\b", "[NUMERO]", texto)
    return texto


def limpar_conversa_whatsapp(texto: str) -> tuple[str, dict[str, Any]]:
    mensagens = []
    anexos = []
    sistema = 0
    mensagem_atual: dict[str, Any] | None = None

    for linha in normalizar_espacos(texto).split("\n"):
        linha = linha.strip()
        if not linha:
            continue

        if any(linha.startswith(prefixo) for prefixo in LINHAS_CONVERSA_SISTEMA):
            sistema += 1
            continue

        match = WHATSAPP_MSG_RE.match(linha)
        if match:
            if mensagem_atual:
                mensagens.append(mensagem_atual)

            data, hora, autor, conteudo = match.groups()
            papel = "vendedor" if "Inforrel" in autor else "cliente"
            if "(arquivo anexado)" in conteudo:
                anexos.append("[ANEXO_REMOVIDO]")
                conteudo = "[ANEXO_REMOVIDO]"

            mensagem_atual = {
                "data": data,
                "hora": hora,
                "papel": papel,
                "conteudo": anonimizar_texto_conversa(conteudo),
            }
            continue

        if mensagem_atual:
            if "(arquivo anexado)" in linha or re.search(r"\.(pdf|jpg|jpeg|png)\b", linha, re.I):
                anexos.append("[ANEXO_REMOVIDO]")
                continue
            mensagem_atual["conteudo"] += "\n" + anonimizar_texto_conversa(linha)

    if mensagem_atual:
        mensagens.append(mensagem_atual)

    linhas_saida = [
        f"{msg['papel'].upper()}: {msg['conteudo'].strip()}"
        for msg in mensagens
        if msg["conteudo"].strip()]
    return normalizar_espacos("\n".join(linhas_saida)), {
        "mensagens": len(mensagens),
        "anexos_removidos": len(anexos),
        "mensagens_sistema_removidas": sistema,
        "anexos": anexos,
        "anonimizado": True,
    }


def processar_fonte(fonte: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    caminho = RAIZ_PROJETO / fonte["caminho"]
    if fonte["extensao"] != ".txt":
        return None, {"motivo": "extensao_ignorada"}

    texto = ler_texto(caminho)
    tipo = inferir_tipo(fonte)

    if fonte["tipo_fonte"] == "webscraping":
        conteudo, stats = limpar_webscraping(texto)
    elif fonte["tipo_fonte"] == "conversa_whatsapp":
        conteudo, stats = limpar_conversa_whatsapp(texto)
    else:
        conteudo, stats = limpar_folder(texto)

    linhas_limpas = [linha for linha in conteudo.split("\n") if linha.strip()]
    if not conteudo or len(conteudo) < 20:
        return None, {"motivo": "conteudo_vazio_ou_curto", **stats}

    titulo = titulo_por_arquivo(fonte, linhas_limpas)
    slug = slug_seguro(fonte)
    conteudo_hash = hash_texto(conteudo)

    documento = {
        "id_fonte": fonte["sha256_bruto"],
        "id_documento": f"{fonte['tipo_fonte']}:{slug}:{conteudo_hash[:12]}",
        "tipo": tipo,
        "titulo": titulo,
        "conteudo": conteudo,
        "conteudo_hash": conteudo_hash,
        "metadata": {
            "origem": fonte["tipo_fonte"],
            "arquivo": caminho_metadata(fonte),
            "url": fonte.get("url_principal"),
            "urls": fonte.get("urls", []),
            "extensao_original": fonte["extensao"],
            "tamanho_bytes_original": fonte["tamanho_bytes"],
            "preprocessamento": stats,
        },
    }
    return documento, {"motivo": "processado", **stats}


def carregar_fontes(inventario: Path) -> list[dict[str, Any]]:
    dados = ler_json(inventario)
    return list(dados.get("fontes", []))


def gerar_documentos(inventario: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    documentos = []
    status = []

    for fonte in carregar_fontes(inventario):
        documento, resultado = processar_fonte(fonte)
        status.append(
            {
                "arquivo": caminho_metadata(fonte),
                "tipo_fonte": fonte["tipo_fonte"],
                "extensao": fonte["extensao"],
                **resultado,
            }
        )
        if documento:
            documentos.append(documento)

    por_tipo = Counter(doc["tipo"] for doc in documentos)
    por_origem = Counter(doc["metadata"]["origem"] for doc in documentos)
    por_status = Counter(item["motivo"] for item in status)

    resumo = {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "inventario": inventario.relative_to(RAIZ_PROJETO).as_posix(),
        "total_fontes": len(status),
        "total_documentos": len(documentos),
        "por_tipo_documento": dict(sorted(por_tipo.items())),
        "por_origem": dict(sorted(por_origem.items())),
        "por_status": dict(sorted(por_status.items())),
        "status_fontes": status,
    }
    return documentos, resumo


def salvar_jsonl(documentos: list[dict[str, Any]], saida: Path) -> None:
    saida.parent.mkdir(parents=True, exist_ok=True)
    with saida.open("w", encoding="utf-8", newline="\n") as arquivo:
        for documento in documentos:
            arquivo.write(json.dumps(documento, ensure_ascii=False) + "\n")


def salvar_json(dados: dict[str, Any], saida: Path) -> None:
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def caminho_absoluto_ou_raiz(caminho: Path) -> Path:
    return caminho if caminho.is_absolute() else RAIZ_PROJETO / caminho


def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-processa fontes raw da RAG.")
    parser.add_argument("--inventario", type=Path, default=INVENTARIO_PADRAO)
    parser.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    parser.add_argument("--resumo", type=Path, default=RESUMO_PADRAO)
    args = parser.parse_args()

    inventario = caminho_absoluto_ou_raiz(args.inventario)
    saida = caminho_absoluto_ou_raiz(args.saida)
    resumo_saida = caminho_absoluto_ou_raiz(args.resumo)

    documentos, resumo = gerar_documentos(inventario)
    salvar_jsonl(documentos, saida)
    salvar_json(resumo, resumo_saida)

    print(f"Documentos normalizados: {saida}")
    print(f"Resumo: {resumo_saida}")
    print(f"Total de fontes: {resumo['total_fontes']}")
    print(f"Total de documentos: {resumo['total_documentos']}")
    print(f"Por tipo: {resumo['por_tipo_documento']}")
    print(f"Por origem: {resumo['por_origem']}")
    print(f"Por status: {resumo['por_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
