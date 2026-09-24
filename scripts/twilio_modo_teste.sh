#!/usr/bin/env bash
#
# twilio_modo_teste.sh - Liga e desliga o modo de teste real com a Twilio.
#
# Existe por dois motivos. O primeiro e evitar erro de digitacao em quatro variaveis
# que, erradas, produzem falhas silenciosas (a pior delas: APP_URL_PUBLICA errada faz
# tudo parecer funcionar, mas o message_sid nunca chega). O segundo, e mais importante,
# e tornar o DESLIGAR trivial: CANAL_SAIDA=twilio faz o sistema responder de verdade no
# WhatsApp, e esquecer isso ligado e o tipo de coisa que so se descobre pelo cliente.
#
# Uso:
#   ./scripts/twilio_modo_teste.sh ligar      # entra em modo de teste real
#   ./scripts/twilio_modo_teste.sh desligar   # volta para simulado (default do projeto)
#   ./scripts/twilio_modo_teste.sh status     # mostra o que esta valendo agora
#
# Depois de ligar ou desligar, REINICIE o backend: as variaveis sao lidas no boot.

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$RAIZ/backend/.env"
BACKUP="$RAIZ/backend/.env.antes_modo_teste"

URL_PUBLICA_PADRAO="https://app.auxvendas.com"

vermelho() { printf '\033[31m%s\033[0m\n' "$1"; }
verde()    { printf '\033[32m%s\033[0m\n' "$1"; }
amarelo()  { printf '\033[33m%s\033[0m\n' "$1"; }

[[ -f "$ENV_FILE" ]] || { vermelho "Nao achei $ENV_FILE"; exit 1; }

# Remove a chave do .env (se existir) e acrescenta com o valor novo.
# Mexe so nas quatro chaves deste script; o resto do arquivo fica intacto.
definir() {
    local chave="$1" valor="$2"
    grep -v -E "^${chave}=" "$ENV_FILE" > "$ENV_FILE.tmp" || true
    mv "$ENV_FILE.tmp" "$ENV_FILE"
    printf '%s=%s\n' "$chave" "$valor" >> "$ENV_FILE"
}

valor_de() {
    grep -E "^$1=" "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- || true
}

mostrar_status() {
    echo "Configuracao atual em backend/.env:"
    for chave in CANAL_SAIDA TWILIO_MODO_ENVIO APP_URL_PUBLICA TWILIO_CAPTURAR_PAYLOADS TWILIO_VALIDAR_ASSINATURA; do
        local v; v="$(valor_de "$chave")"
        printf '  %-28s %s\n' "$chave" "${v:-(nao definida, usa o default do config.py)}"
    done
    echo
    local canal; canal="$(valor_de CANAL_SAIDA)"
    if [[ "$canal" == "twilio" ]]; then
        vermelho "  >> ENTREGA REAL LIGADA: o sistema responde no WhatsApp de verdade."
    else
        verde "  >> Modo simulado: nada e entregue ao cliente."
    fi
    echo
    echo "O backend so enxerga mudanca depois de reiniciar. Conferir o que ele carregou:"
    echo "  curl -s localhost:8000/api/config/execucao | python3 -m json.tool"
}

case "${1:-status}" in
    ligar)
        cp "$ENV_FILE" "$BACKUP"
        definir CANAL_SAIDA twilio
        definir TWILIO_MODO_ENVIO twiml
        definir APP_URL_PUBLICA "${2:-$URL_PUBLICA_PADRAO}"
        definir TWILIO_CAPTURAR_PAYLOADS true
        # TWILIO_VALIDAR_ASSINATURA fica de fora de proposito: exige o Auth Token da conta,
        # que nao temos. Ligar sem ele faz os dois webhooks devolverem HTTP 503.
        verde "Modo de teste real LIGADO."
        echo "Backup do .env anterior: $BACKUP"
        echo
        mostrar_status
        echo
        amarelo "Lembre de rodar '$0 desligar' ao terminar os testes."
        ;;
    desligar)
        definir CANAL_SAIDA simulado
        definir TWILIO_CAPTURAR_PAYLOADS false
        verde "Modo de teste real DESLIGADO (canal simulado, captura off)."
        echo
        mostrar_status
        ;;
    status)
        mostrar_status
        ;;
    *)
        echo "Uso: $0 {ligar [url_publica]|desligar|status}"
        exit 1
        ;;
esac
