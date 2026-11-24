#!/usr/bin/env bash
# Compila o APK release do App Android e publica para download em https://app.auxvendas.com/android/.
#
# O nginx do container frontend serve a pasta publicado/android/ (gitignored) do checkout de onde
# o compose subiu, montada em /usr/share/nginx/html/android (docker-compose.yml). A QA sobe do
# checkout dedicado .worktrees/_deploy (scripts/deploy_auto.sh), então o destino padrão é a
# publicado/android/ de lá; sem esse checkout, a do repositório principal. O `git clean` do
# deploy_auto.sh não tem -x, por isso a pasta publicada sobrevive aos deploys.
#
#   bash scripts/app_publicar.sh               # compila e publica
#   bash scripts/app_publicar.sh --sem-build   # publica o último APK compilado
#   DESTINO=/caminho bash scripts/app_publicar.sh
#
# Publica três arquivos: inforrel-atendente.apk, versao.json ({versao, versionCode, data,
# commit}) e index.html (página de download, cópia de scripts/app_android_pagina.html).
# Assinatura: chave de debug do Windows (ver android/app/build.gradle.kts).
set -euo pipefail

CHECKOUT="$(cd "$(dirname "$0")/.." && pwd)"
comum="$(git -C "$CHECKOUT" rev-parse --git-common-dir)"
[[ "$comum" = /* ]] || comum="$(cd "$CHECKOUT" && cd "$comum" && pwd)"
REPO="$(dirname "$comum")"
if [[ -z "${DESTINO:-}" ]]; then
  if [[ -d "$REPO/.worktrees/_deploy" ]]; then
    DESTINO="$REPO/.worktrees/_deploy/publicado/android"
  else
    DESTINO="$REPO/publicado/android"
  fi
fi

APK="$CHECKOUT/android/app/build/outputs/apk/release/app-release.apk"
METADADOS="$CHECKOUT/android/app/build/outputs/apk/release/output-metadata.json"

if [[ "${1:-}" != "--sem-build" ]]; then
  bash "$CHECKOUT/scripts/app_gradle.sh" assembleRelease
fi
[[ -f "$APK" ]] || { echo "APK não encontrado em $APK" >&2; exit 1; }

versao="$(tr -d '\r\n' < "$CHECKOUT/android/VERSAO")"
version_name="$(grep -o '"versionName": *"[^"]*"' "$METADADOS" | grep -o '[0-9.]*-[0-9]*')"
version_code="$(grep -o '"versionCode": *[0-9]*' "$METADADOS" | grep -o '[0-9]*$')"
if [[ "$version_name" != "$versao" ]]; then
  echo "O APK compilado é da versão $version_name e o android/VERSAO diz $versao; compile de novo." >&2
  exit 1
fi

mkdir -p "$DESTINO"
# Cópia para temporário e mv: quem estiver baixando não pega um APK pela metade.
cp "$APK" "$DESTINO/.inforrel-atendente.apk.tmp"
mv -f "$DESTINO/.inforrel-atendente.apk.tmp" "$DESTINO/inforrel-atendente.apk"
cp "$CHECKOUT/scripts/app_android_pagina.html" "$DESTINO/index.html"
cat > "$DESTINO/versao.json" <<JSON
{"versao": "$versao", "versionCode": $version_code, "data": "$(TZ=America/Sao_Paulo date '+%Y-%m-%dT%H:%M:%S%:z')", "commit": "$(git -C "$CHECKOUT" rev-parse --short HEAD)"}
JSON

echo "Publicado em $DESTINO: App $versao (versionCode $version_code)"
if curl -fsS --max-time 5 http://localhost:3000/android/versao.json 2>/dev/null | grep -q "$versao"; then
  echo "ok: http://localhost:3000/android/ já serve a versão $versao"
else
  echo "aviso: http://localhost:3000/android/versao.json não mostra $versao (o frontend sobe de outro checkout ou ainda não tem o volume publicado/android; ver docs/comandos_uteis.md)" >&2
fi
