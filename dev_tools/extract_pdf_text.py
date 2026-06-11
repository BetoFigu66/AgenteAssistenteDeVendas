"""
Script para extrair texto de arquivos PDF em um diretório.
Uso: python extract_pdf_text.py <diretorio>
"""

import sys
from pathlib import Path

import fitz  # PyMuPDF


def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Extrai texto de um arquivo PDF.

    Args:
        pdf_path: Caminho para o arquivo PDF

    Returns:
        Texto extraído do PDF
    """
    text_parts = []

    with fitz.open(pdf_path) as doc:
        for page_num, page in enumerate(doc, 1):
            text = page.get_text()
            text_parts.append(f"--- Página {page_num} ---\n{text}")

    return "\n\n".join(text_parts)


def process_directory(directory: str) -> None:
    """
    Processa todos os PDFs de um diretório, convertendo para TXT.
    Pula arquivos que já possuem o TXT correspondente.

    Args:
        directory: Caminho para o diretório com os PDFs
    """
    dir_path = Path(directory)

    if not dir_path.exists():
        raise FileNotFoundError(f"Diretório não encontrado: {dir_path}")

    if not dir_path.is_dir():
        raise ValueError(f"O caminho deve ser um diretório: {dir_path}")

    pdf_files = list(dir_path.glob("*.pdf"))

    if not pdf_files:
        print(f"Nenhum arquivo PDF encontrado em: {dir_path}")
        return

    print(f"Encontrados {len(pdf_files)} arquivo(s) PDF em: {dir_path}\n")

    processed = 0
    skipped = 0

    for pdf_path in pdf_files:
        txt_path = pdf_path.with_suffix(".txt")

        if txt_path.exists():
            print(f"[PULADO] {pdf_path.name} -> {txt_path.name} já existe")
            skipped += 1
            continue

        print(f"[PROCESSANDO] {pdf_path.name}...")

        try:
            text = extract_text_from_pdf(pdf_path)
            txt_path.write_text(text, encoding="utf-8")
            print(f"  -> Salvo: {txt_path.name}")
            processed += 1
        except Exception as e:
            print(f"  -> Erro: {e}")

    print(f"\nResumo: {processed} processado(s), {skipped} pulado(s)")


def main():
    if len(sys.argv) < 2:
        print("Uso: python extract_pdf_text.py <diretorio>")
        print("\nExemplo:")
        print("  python extract_pdf_text.py C:\\Documentos\\PDFs")
        sys.exit(1)

    directory = sys.argv[1]

    try:
        process_directory(directory)
        print("\nExtração concluída!")
    except Exception as e:
        print(f"\nErro: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
