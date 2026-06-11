"""
Web scraper recursivo para https://inforrel.com.br/

Percorre recursivamente as páginas do domínio alvo, extrai o texto visível
de cada uma e salva em arquivos .txt dentro de `WebScrapping/result/`.

- O nome do arquivo .txt é derivado do caminho (slug) da URL da página.
- Um conjunto de URLs já visitadas evita visitar a mesma página mais de uma vez.
- Apenas links internos ao domínio base são seguidos.

Uso:
    python scraper.py
"""

from __future__ import annotations

import os
import re
import sys
import time
from collections import deque
from typing import Set
from urllib.parse import urljoin, urldefrag, urlparse

import requests
from bs4 import BeautifulSoup

# -----------------------------------------------------------------------------
# Configurações
# -----------------------------------------------------------------------------
BASE_URL: str = "https://inforrel.com.br/"
BASE_DOMAIN: str = urlparse(BASE_URL).netloc

# Diretório de saída (relativo a este arquivo)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "result")

REQUEST_TIMEOUT = 20  # segundos
REQUEST_DELAY = 0.5   # delay educado entre requisições (segundos)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0 Safari/537.36 InforrelScraper/1.0"
)

# Extensões a ignorar (arquivos binários / mídia)
BINARY_EXTENSIONS = {
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico",
    ".zip", ".rar", ".7z", ".tar", ".gz",
    ".mp3", ".mp4", ".wav", ".avi", ".mov",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
}


# -----------------------------------------------------------------------------
# Funções utilitárias
# -----------------------------------------------------------------------------
def normalize_url(url: str) -> str:
    """Remove fragmento (#...) e normaliza barra final."""
    url, _ = urldefrag(url)
    # Normaliza raiz (ex.: https://site.com == https://site.com/)
    parsed = urlparse(url)
    path = parsed.path or "/"
    normalized = f"{parsed.scheme}://{parsed.netloc}{path}"
    if parsed.query:
        normalized += f"?{parsed.query}"
    return normalized


def is_internal_link(url: str) -> bool:
    """Verifica se a URL pertence ao mesmo domínio base."""
    try:
        return urlparse(url).netloc == BASE_DOMAIN
    except Exception:
        return False


def has_binary_extension(url: str) -> bool:
    """Detecta se a URL aponta para um arquivo binário pelo sufixo."""
    path = urlparse(url).path.lower()
    _, ext = os.path.splitext(path)
    return ext in BINARY_EXTENSIONS


def sanitize_filename(name: str) -> str:
    """Remove caracteres inválidos para nomes de arquivo no Windows."""
    # Substitui caracteres inválidos por "_"
    name = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", name)
    # Remove múltiplos underscores
    name = re.sub(r"_+", "_", name).strip("_")
    # Limita tamanho (Windows tem limite de ~255, mas caminho completo ~260)
    return name[:150] or "index"


def url_to_filename(url: str) -> str:
    """Gera um nome de arquivo .txt a partir da URL.

    O nome é derivado do caminho (slug) da URL:
      - "/"               -> "index.txt"
      - "/produtos"       -> "produtos.txt"
      - "/cat/relogios/"  -> "cat_relogios.txt"
      - "?q=..."          -> incorporado ao nome
    """
    parsed = urlparse(url)
    path = parsed.path.strip("/")

    if not path:
        base = "index"
    else:
        base = path.replace("/", "_")

    if parsed.query:
        base = f"{base}_{parsed.query}"

    return f"{sanitize_filename(base)}.txt"


def extract_visible_text(html: str) -> str:
    """Extrai o texto visível de uma página HTML."""
    soup = BeautifulSoup(html, "lxml")

    # Remove tags que não contribuem para o conteúdo visível
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()

    # get_text com separador + strip preserva parágrafos
    text = soup.get_text(separator="\n", strip=True)

    # Remove linhas em branco consecutivas
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return "\n".join(lines)


def extract_links(html: str, current_url: str) -> Set[str]:
    """Extrai todos os links internos absolutos de uma página."""
    soup = BeautifulSoup(html, "lxml")
    links: Set[str] = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:")):
            continue

        absolute = urljoin(current_url, href)
        absolute = normalize_url(absolute)

        if not absolute.startswith(("http://", "https://")):
            continue
        if not is_internal_link(absolute):
            continue
        if has_binary_extension(absolute):
            continue

        links.add(absolute)

    return links


# -----------------------------------------------------------------------------
# Scraper
# -----------------------------------------------------------------------------
def scrape_site(start_url: str, output_dir: str) -> None:
    """Percorre o site a partir de `start_url` (BFS) e salva cada página em .txt."""
    os.makedirs(output_dir, exist_ok=True)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    visited: Set[str] = set()
    used_filenames: Set[str] = set()
    queue: deque[str] = deque()

    start_normalized = normalize_url(start_url)
    queue.append(start_normalized)

    total_saved = 0

    while queue:
        url = queue.popleft()
        if url in visited:
            continue
        visited.add(url)

        print(f"[{len(visited)}] Acessando: {url}")

        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as exc:
            print(f"  ! Erro ao acessar: {exc}")
            continue

        if response.status_code != 200:
            print(f"  ! Status {response.status_code} - pulando.")
            continue

        content_type = response.headers.get("Content-Type", "").lower()
        if "text/html" not in content_type:
            print(f"  ! Content-Type não-HTML ({content_type}) - pulando.")
            continue

        html = response.text

        # Extrai texto e salva em arquivo
        text = extract_visible_text(html)
        filename = url_to_filename(url)

        # Garante unicidade do nome do arquivo
        final_name = filename
        counter = 2
        while final_name in used_filenames:
            root, ext = os.path.splitext(filename)
            final_name = f"{root}_{counter}{ext}"
            counter += 1
        used_filenames.add(final_name)

        file_path = os.path.join(output_dir, final_name)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"URL: {url}\n")
                f.write("=" * 80 + "\n\n")
                f.write(text)
            total_saved += 1
            print(f"  -> Salvo: {final_name}")
        except OSError as exc:
            print(f"  ! Erro ao salvar arquivo '{final_name}': {exc}")

        # Descobre novos links internos
        for link in extract_links(html, url):
            if link not in visited:
                queue.append(link)

        time.sleep(REQUEST_DELAY)

    print("\n" + "=" * 60)
    print(f"Concluído. Páginas visitadas: {len(visited)} | Arquivos salvos: {total_saved}")
    print(f"Saída: {output_dir}")


def main() -> int:
    try:
        scrape_site(BASE_URL, OUTPUT_DIR)
    except KeyboardInterrupt:
        print("\nInterrompido pelo usuário.")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
