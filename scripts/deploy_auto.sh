#!/usr/bin/env bash
# Deploy da stack de QA (app.auxvendas.com) a partir de origin/develop.
#
# Roda num checkout dedicado (.worktrees/_deploy, HEAD destacado em origin/develop) e não no
# checkout principal: o compose monta ./backend no container, e o checkout principal tem o WIP
# de quem está desenvolvendo. Assim a QA mostra só o que foi publicado em develop.
#
# Usado pelos goals de correção automática de reports (backend/scripts/ponte_reports_goals.py),
# mas serve para deploy manual também. Roda do WSL; o Docker é o do Windows (docker.exe).
#
#   bash scripts/deploy_auto.sh            # deploy de origin/develop
#   bash scripts/deploy_auto.sh --sem-build # só atualiza o código e reinicia o backend
set -euo pipefail

PROJETO=agenteassistentedevendas   # mesmo nome do projeto de hoje: substitui os mesmos containers
ESPERA_S=240

comum="$(git -C "$(dirname "$0")" rev-parse --git-common-dir)"
[[ "$comum" = /* ]] || comum="$(cd "$(dirname "$0")" && cd "$comum" && pwd)"
REPO="$(dirname "$comum")"
DEPLOY="$REPO/.worktrees/_deploy"
LOG="$REPO/logs/deploy_auto.log"
mkdir -p "$REPO/logs"

log() { echo "$(date '+%d/%m %H:%M:%S') [deploy] $*" | tee -a "$LOG"; }

# Um deploy por vez (dois goals terminando juntos).
exec 9>"$REPO/logs/.deploy_auto.lock"
flock -w 900 9 || { log "outro deploy segurando a trava há 15 min, desisto"; exit 1; }

git -C "$REPO" fetch -q origin develop
if [[ ! -d "$DEPLOY" ]]; then
  grep -qx '/.worktrees/' "$REPO/.git/info/exclude" 2>/dev/null || echo '/.worktrees/' >> "$REPO/.git/info/exclude"
  git -C "$REPO" worktree add -q --detach "$DEPLOY" origin/develop
fi
git -C "$DEPLOY" checkout -q --detach --force origin/develop
git -C "$DEPLOY" clean -fdq          # sem -x: preserva backend/.env e afins (ignorados)
sha="$(git -C "$DEPLOY" rev-parse --short HEAD)"
versao="$(tr -d '\r\n' < "$DEPLOY/backend/VERSAO")"

# O backend lê backend/.env (pydantic-settings, caminho relativo); o .env não está no git.
cp "$REPO/backend/.env" "$DEPLOY/backend/.env"

log "deploy de origin/develop $sha (backend $versao)"
cd "$DEPLOY"
if [[ "${1:-}" != "--sem-build" ]]; then
  docker.exe compose -p "$PROJETO" up -d --build backend frontend 2>&1 | tr -d '\r' | tail -5 | tee -a "$LOG"
fi
# O --reload do uvicorn não enxerga mudança vinda do bind mount do Windows (o processo da QA
# ficava dias sem recarregar): reinício explícito, que também roda as migrations no lifespan.
docker.exe compose -p "$PROJETO" restart backend 2>&1 | tr -d '\r' | tee -a "$LOG"

for ((i = 0; i < ESPERA_S; i += 5)); do
  atual="$(curl -fsS --max-time 4 http://localhost:8000/health 2>/dev/null | tr -d '\r' | grep -o "$versao" || true)"
  if [[ -n "$atual" ]]; then
    front="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://localhost:3000/ || true)"
    log "ok: /health na versão $versao, frontend HTTP $front"
    [[ "$front" == "200" ]] || { log "frontend não respondeu 200"; exit 1; }
    exit 0
  fi
  sleep 5
done
log "FALHA: /health não chegou à versão $versao em ${ESPERA_S}s"
docker.exe logs --tail 40 "${PROJETO}-backend-1" 2>&1 | tr -d '\r' | tee -a "$LOG"
exit 1
