#!/usr/bin/env bash
# Roda o Gradle do App Android (android/) pelo Windows, a partir do WSL.
#
# O SDK Android e o JDK do WSL são velhos (API 29, Java 8) e não devem ser usados: o build usa o
# JDK 17 que vem com o Android Studio e o SDK do Windows. Gera android/local.properties (gitignored)
# se faltar.
#
#   bash scripts/app_gradle.sh test                 # testes unitários
#   bash scripts/app_gradle.sh assembleRelease      # APK em android/app/build/outputs/apk/release/
#
# Variáveis opcionais: JAVA_HOME_WIN (padrão: jbr do Android Studio), ANDROID_SDK_WIN (padrão:
# %LOCALAPPDATA%\Android\Sdk).
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
ANDROID_DIR="$RAIZ/android"
JAVA_HOME_WIN="${JAVA_HOME_WIN:-C:\\Program Files\\Android\\Android Studio\\jbr}"
if [[ -z "${ANDROID_SDK_WIN:-}" ]]; then
  ANDROID_SDK_WIN="$(cmd.exe /c 'echo %LOCALAPPDATA%' 2>/dev/null | tr -d '\r')\\Android\\Sdk"
fi

if [[ ! -f "$ANDROID_DIR/local.properties" ]]; then
  # local.properties escapa ':' e '\'.
  sdk_escapado="$(printf '%s' "$ANDROID_SDK_WIN" | sed -e 's/\\/\\\\/g' -e 's/:/\\:/g')"
  printf 'sdk.dir=%s\n' "$sdk_escapado" > "$ANDROID_DIR/local.properties"
fi

cd "$ANDROID_DIR"
# cmd.exe herda o diretório atual (convertido para C:\...). JAVA_HOME e ANDROID_HOME vão pelo
# WSLENV (/p converte o caminho): aspas dentro do comando do cmd.exe chegam escapadas e quebram.
export JAVA_HOME ANDROID_HOME
JAVA_HOME="$(wslpath -u "$JAVA_HOME_WIN")"
ANDROID_HOME="$(wslpath -u "$ANDROID_SDK_WIN")"
export WSLENV="JAVA_HOME/p:ANDROID_HOME/p${WSLENV:+:$WSLENV}"
cmd.exe /c gradlew.bat --console=plain "$@" 2>&1 | tr -d '\r'
exit "${PIPESTATUS[0]}"
