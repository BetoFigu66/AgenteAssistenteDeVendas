#!/usr/bin/env bash
# Cópia, no repo, dos arquivos do sistema de goals que ficam fora dele e que a correção
# automática de reports usa (ver docs/comandos_uteis.md, "Correção automática de reports").
#
#   bash ferramentas/goals/sincronizar.sh conferir    # diferença entre o instalado e a cópia do repo
#   bash ferramentas/goals/sincronizar.sh atualizar   # instalado -> repo (depois de mexer no instalado)
#   bash ferramentas/goals/sincronizar.sh instalar    # repo -> instalado (máquina nova ou restauração)
#
# O cloudId do Atlassian da Fitec não vai para o repo: na cópia o SKILL.md tem o marcador
# <ATLASSIAN_CLOUD_ID>. O `instalar` repõe o valor do SKILL.md já instalado ou, numa máquina
# nova, o da variável ATLASSIAN_CLOUD_ID; sem nenhum dos dois, fica o marcador.
set -euo pipefail

AQUI="$(cd "$(dirname "$0")" && pwd)"
MARCADOR='<ATLASSIAN_CLOUD_ID>'
UUID_RE='[0-9a-f]\{8\}-[0-9a-f]\{4\}-[0-9a-f]\{4\}-[0-9a-f]\{4\}-[0-9a-f]\{12\}'

# caminho no repo | caminho instalado
PARES=(
  "bin/goal|$HOME/bin/goal"
  "hooks/goal_guard.py|$HOME/.claude/hooks/goal_guard.py"
  "skills/goal-run/SKILL.md|$HOME/.claude/skills/goal-run/SKILL.md"
)

mascarar() { sed "s/cloudId \`$UUID_RE\`/cloudId \`$MARCADOR\`/" "$1"; }

cloud_id_instalado() {
  grep -o "cloudId \`$UUID_RE\`" "$HOME/.claude/skills/goal-run/SKILL.md" 2>/dev/null | grep -o "$UUID_RE" || true
}

conferir() {
  local difere=0 par repo inst
  for par in "${PARES[@]}"; do
    repo="$AQUI/${par%%|*}"; inst="${par#*|}"
    if [[ ! -f "$inst" ]]; then
      echo "FALTA instalar: $inst"; difere=1
    elif diff -q <(mascarar "$inst") "$repo" >/dev/null; then
      echo "igual: ${par%%|*}"
    else
      echo "DIFERENTE: ${par%%|*} (instalado em $inst)"; diff -u "$repo" <(mascarar "$inst") | head -40 || true
      difere=1
    fi
  done
  if ! grep -q "goal_guard.py" "$HOME/.claude/settings.json" 2>/dev/null; then
    echo "AVISO: ~/.claude/settings.json não registra o hook goal_guard.py (PreToolUse); a trava não age."
    difere=1
  fi
  return $difere
}

atualizar() {
  local par repo inst
  for par in "${PARES[@]}"; do
    repo="$AQUI/${par%%|*}"; inst="${par#*|}"
    mkdir -p "$(dirname "$repo")"
    mascarar "$inst" > "$repo"
    [[ -x "$inst" ]] && chmod +x "$repo"
    echo "copiado: $inst -> ${par%%|*}"
  done
  grep -rq "$UUID_RE" "$AQUI/skills" && { echo "ERRO: sobrou um UUID na cópia do SKILL.md"; exit 1; }
  echo "Confira com 'git diff ferramentas/goals' antes de commitar."
}

instalar() {
  local cid par repo inst
  cid="$(cloud_id_instalado)"; cid="${cid:-${ATLASSIAN_CLOUD_ID:-}}"
  for par in "${PARES[@]}"; do
    repo="$AQUI/${par%%|*}"; inst="${par#*|}"
    mkdir -p "$(dirname "$inst")"
    [[ -f "$inst" ]] && cp -p "$inst" "$inst.bak"
    if [[ -n "$cid" ]]; then sed "s/$MARCADOR/$cid/" "$repo" > "$inst"; else cp "$repo" "$inst"; fi
    [[ -x "$repo" ]] && chmod +x "$inst"
    echo "instalado: ${par%%|*} -> $inst"
  done
  [[ -n "$cid" ]] || echo "AVISO: sem cloudId do Atlassian; o SKILL.md ficou com $MARCADOR (só importa para goals com Jira)."
  python3 -c 'import yaml' 2>/dev/null || echo "AVISO: o CLI goal precisa do pyyaml no python3 do sistema."
  if ! grep -q "goal_guard.py" "$HOME/.claude/settings.json" 2>/dev/null; then
    cat <<'JSON'
AVISO: registre a trava em ~/.claude/settings.json (dentro de "hooks"):
    "PreToolUse": [ { "hooks": [ { "type": "command", "command": "python3 ~/.claude/hooks/goal_guard.py" } ] } ]
JSON
  fi
}

case "${1:-conferir}" in
  conferir) conferir ;;
  atualizar) atualizar ;;
  instalar) instalar ;;
  *) echo "uso: $0 conferir|atualizar|instalar"; exit 2 ;;
esac
