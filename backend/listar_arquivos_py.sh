#!/bin/bash
# Lista todos os arquivos .py do diretório atual e subdiretórios,
# com path, data da última modificação e número de linhas.

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

printf "%-70s %-20s %10s\n" "ARQUIVO" "ULTIMA_MODIFICACAO" "LINHAS"

find "$DIR" \
    \( -type d \( \
        -name ".git" -o \
        -name ".venv" -o \
        -name "venv" -o \
        -name "__pycache__" -o \
        -name ".idea" \
    \) -prune \) \
    -o \
    \( -type f -name "*.py" -print \) |
sort |
while IFS= read -r arquivo; do
    data_mod=$(date -r "$arquivo" "+%Y-%m-%d %H:%M:%S")
    linhas=$(wc -l < "$arquivo")
    rel="${arquivo#"$DIR"/}"
    printf "%-70s %-20s %10s\n" "$rel" "$data_mod" "$linhas"
done
