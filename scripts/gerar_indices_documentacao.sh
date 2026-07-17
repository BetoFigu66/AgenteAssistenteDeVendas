#!/bin/bash
# Gera os indices de documentacao (docs/indices/INDICE_<TAG>.md) a partir das
# linhas "CLASSIFICACAO: <TAG>" espalhadas pelos docs do repo. So faz grep —
# nao interpreta nada, entao rodar de novo depois de retaguear um arquivo e
# seguro (idempotente, sobrescreve os indices).
#
# Usa `find -prune` (nao `grep --exclude-dir`) para listar os candidatos:
# `grep -r` recursivo tropeca em `dev_tools/.venv` neste repo (montagem
# WSL/DrvFs + venv com muitos arquivos pequenos = trava). `find -prune`
# evita descer nesses diretorios de verdade, sem esse problema.
cd "$(dirname "$0")/.." || exit 1

TAGS=("HISTORICO" "IA" "SISTEMA-CAIXAPRETA" "SISTEMA-DEV" "ANDAMENTO" "PROCESSO")
OUTDIR="docs/indices"
mkdir -p "$OUTDIR"

CANDIDATOS=$(find . \
  -path "./node_modules" -prune -o \
  -path "./frontend/node_modules" -prune -o \
  -path "./backend/venv" -prune -o \
  -path "./.venv" -prune -o \
  -path "./dev_tools" -prune -o \
  -path "./.git" -prune -o \
  -path "*/__pycache__" -prune -o \
  -path "./AnotacoesPessoais" -prune -o \
  -path "./frontend/dist" -prune -o \
  -path "./docs/indices" -prune -o \
  \( -name "*.md" -o -name "*.yaml" \) -type f -print)

titulo_de() {
  # 1a linha nao-vazia que nao seja o comentario de CLASSIFICACAO
  grep -m1 -v -E '^[[:space:]]*$|^<!--|^#[[:space:]]*CLASSIFICACAO' "$1" 2>/dev/null | sed -e 's/^#\+[[:space:]]*//'
}

for TAG in "${TAGS[@]}"; do
  OUT="$OUTDIR/INDICE_${TAG//-/_}.md"
  ARQUIVOS=$(echo "$CANDIDATOS" | xargs grep -l -- "CLASSIFICACAO: $TAG" 2>/dev/null | sort)

  {
    echo "# Índice — $TAG"
    echo
    echo "_Gerado automaticamente por \`scripts/gerar_indices_documentacao.sh\` — não editar à mão. Rode o script de novo após retaguear algum arquivo._"
    echo
    if [ -z "$ARQUIVOS" ]; then
      echo "_Nenhum arquivo com esta classificação ainda._"
    else
      while IFS= read -r f; do
        rel="${f#./}"
        titulo=$(titulo_de "$f")
        if [ -z "$titulo" ]; then
          titulo="(sem título)"
        fi
        echo "- [\`$rel\`](../../$rel) — $titulo"
      done <<< "$ARQUIVOS"
    fi
  } > "$OUT"

  qtd=0
  if [ -n "$ARQUIVOS" ]; then
    qtd=$(echo "$ARQUIVOS" | wc -l)
  fi
  echo "Gerado $OUT ($qtd arquivos)"
done
