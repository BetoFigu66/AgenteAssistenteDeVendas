#!/usr/bin/env bash
#
# sanity_check.sh - Verificacao de ponta a ponta da infraestrutura do
# Assistente de Vendas (ambiente QA: Docker + Cloudflare Tunnel + Twilio).
#
# Verifica, em ordem de dependencia:
#   1. Docker e containers (postgres, backend, frontend)
#   2. Postgres acessivel e com schema respondendo
#   3. Backend local (localhost:8000/health)
#   4. Frontend local (localhost:3000) e proxy nginx -> backend
#   5. Tunel Cloudflare (servico Windows + conectores)
#   6. URL publica https://app.auxvendas.com (HTML + bundle JS)
#   7. API publica atraves do tunel
#   8. Login (POST /api/auth/login)
#   9. Aba Acompanhamento com dados (GET /api/atendimentos/ativas)
#  10. Webhook /webhook vivo (e, com --profundo, uma mensagem real de ponta a ponta)
#  11. Credenciais Twilio (leitura da API)
#
# Uso:
#   ./sanity_check.sh                # saida legivel, colorida
#   ./sanity_check.sh --silencioso   # so imprime falhas e avisos (para cron/monitor)
#   ./sanity_check.sh --json         # uma linha JSON por check + resumo (para monitor)
#   ./sanity_check.sh --profundo     # inclui envio real pelo /webhook (cria e apaga dados)
#   ./sanity_check.sh --ajuda
#
# Codigo de saida: 0 = tudo ok | 1 = ao menos uma falha | 2 = so avisos
#
# Configuracao opcional em sanity_check.conf (mesmo diretorio, nao versionado):
#   SANITY_URL_PUBLICA=https://app.auxvendas.com
#   SANITY_LOGIN=testador_conversas
#   SANITY_SENHA=...
#   SANITY_TELEFONE_TESTE=+5519000000000
#
# Autoria: gerado com Claude Code, revisado por Beto.

set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---------------------------------------------------------------------------
# Configuracao
# ---------------------------------------------------------------------------

# sanity_check.conf (nao versionado) define os SANITY_*. Tem que ser lido ANTES
# dos defaults abaixo, senao o valor do arquivo chega tarde demais. Por isso ele
# tambem tem prioridade sobre variaveis de ambiente de mesmo nome.
[ -f "$RAIZ/sanity_check.conf" ] && . "$RAIZ/sanity_check.conf"

URL_PUBLICA="${SANITY_URL_PUBLICA:-https://app.auxvendas.com}"
URL_BACKEND_LOCAL="${SANITY_URL_BACKEND:-http://localhost:8000}"
URL_FRONT_LOCAL="${SANITY_URL_FRONT:-http://localhost:3000}"
TUNEL="${SANITY_TUNEL:-auxvendas-dev}"
LOGIN="${SANITY_LOGIN:-testador_conversas}"
SENHA="${SANITY_SENHA:-testador_conversas_dev_only}"
TELEFONE_TESTE="${SANITY_TELEFONE_TESTE:-+5519000000000}"
TIMEOUT="${SANITY_TIMEOUT:-15}"
ENV_FILE="${SANITY_ENV_FILE:-$RAIZ/backend/.env}"
SANITY_CLOUDFLARED_CONFIG="${SANITY_CLOUDFLARED_CONFIG:-}"
CONTAINER_PG="${SANITY_CONTAINER_PG:-inforrel_postgres}"
CONTAINER_BACK="${SANITY_CONTAINER_BACK:-agenteassistentedevendas-backend-1}"
CONTAINER_FRONT="${SANITY_CONTAINER_FRONT:-agenteassistentedevendas-frontend-1}"

MODO_SAIDA="normal"   # normal | silencioso | json
PROFUNDO=0

while [ $# -gt 0 ]; do
    case "$1" in
        --silencioso|-s) MODO_SAIDA="silencioso" ;;
        --json|-j)       MODO_SAIDA="json" ;;
        --profundo|-p)   PROFUNDO=1 ;;
        --ajuda|-h|--help)
            sed -n '3,30p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *) echo "Opcao desconhecida: $1 (use --ajuda)" >&2; exit 64 ;;
    esac
    shift
done

# ---------------------------------------------------------------------------
# Saida
# ---------------------------------------------------------------------------

if [ -t 1 ] && [ "$MODO_SAIDA" = "normal" ]; then
    C_OK=$'\033[0;32m'; C_ERRO=$'\033[0;31m'; C_AVISO=$'\033[0;33m'
    C_TITULO=$'\033[1;36m'; C_FRACO=$'\033[0;90m'; C_FIM=$'\033[0m'
else
    C_OK=""; C_ERRO=""; C_AVISO=""; C_TITULO=""; C_FRACO=""; C_FIM=""
fi

N_OK=0; N_FALHA=0; N_AVISO=0
FALHAS_RESUMO=""

_json_escape() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g' | tr -d '\n\r'; }

_registrar() {  # $1=status $2=nome $3=detalhe $4=dica
    local status="$1" nome="$2" detalhe="$3" dica="${4:-}"
    if [ "$MODO_SAIDA" = "json" ]; then
        printf '{"check":"%s","status":"%s","detalhe":"%s","dica":"%s"}\n' \
            "$(_json_escape "$nome")" "$status" "$(_json_escape "$detalhe")" "$(_json_escape "$dica")"
        return
    fi
    case "$status" in
        ok)
            [ "$MODO_SAIDA" = "silencioso" ] && return
            printf '  %s[ OK ]%s %-46s %s%s%s\n' "$C_OK" "$C_FIM" "$nome" "$C_FRACO" "$detalhe" "$C_FIM" ;;
        nota)
            [ "$MODO_SAIDA" = "silencioso" ] && return
            printf '  %s[NOTA ]%s %-46s %s%s%s\n' "$C_FRACO" "$C_FIM" "$nome" "$C_FRACO" "$detalhe" "$C_FIM"
            [ -n "$dica" ] && printf '         %s-> %s%s\n' "$C_FRACO" "$dica" "$C_FIM" ;;
        aviso)
            printf '  %s[AVISO]%s %-46s %s\n' "$C_AVISO" "$C_FIM" "$nome" "$detalhe"
            [ -n "$dica" ] && printf '         %s-> %s%s\n' "$C_FRACO" "$dica" "$C_FIM" ;;
        falha)
            printf '  %s[FALHA]%s %-46s %s\n' "$C_ERRO" "$C_FIM" "$nome" "$detalhe"
            [ -n "$dica" ] && printf '         %s-> %s%s\n' "$C_FRACO" "$dica" "$C_FIM" ;;
    esac
}

ok()    { N_OK=$((N_OK+1));       _registrar ok    "$1" "${2:-}" ""; }
# Informativo: contexto que ajuda a interpretar o resto, sem ser defeito. Nao
# entra na contagem nem muda o codigo de saida.
nota()  { _registrar nota "$1" "${2:-}" "${3:-}"; }
aviso() { N_AVISO=$((N_AVISO+1)); _registrar aviso "$1" "${2:-}" "${3:-}"; }
falha() {
    N_FALHA=$((N_FALHA+1))
    FALHAS_RESUMO="${FALHAS_RESUMO}${FALHAS_RESUMO:+; }$1"
    _registrar falha "$1" "${2:-}" "${3:-}"
}
secao() {
    [ "$MODO_SAIDA" = "json" ] && return
    [ "$MODO_SAIDA" = "silencioso" ] && return
    printf '\n%s%s%s\n' "$C_TITULO" "$1" "$C_FIM"
}

# ---------------------------------------------------------------------------
# Utilitarios
# ---------------------------------------------------------------------------

TMP="$(mktemp -d)"
COOKIES="$TMP/cookies.txt"
trap 'rm -rf "$TMP"' EXIT

# Docker: neste WSL a integracao com o daemon costuma estar desligada, entao
# cai para o binario do Docker Desktop no Windows.
DOCKER=""
_achar_docker() {
    if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
        DOCKER="docker"; return 0
    fi
    local candidatos=(
        "/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe"
        "/mnt/c/ProgramData/DockerDesktop/version-bin/docker.exe"
    )
    local c
    for c in "${candidatos[@]}"; do
        if [ -x "$c" ] && "$c" info >/dev/null 2>&1; then DOCKER="$c"; return 0; fi
    done
    if command -v docker.exe >/dev/null 2>&1 && docker.exe info >/dev/null 2>&1; then
        DOCKER="docker.exe"; return 0
    fi
    return 1
}

_dk() { "$DOCKER" "$@" 2>&1 | tr -d '\r'; }

# Le uma chave do backend/.env sem executar o arquivo e sem imprimir o valor.
_ler_env() {
    [ -f "$ENV_FILE" ] || return 1
    grep -E "^[[:space:]]*$1[[:space:]]*=" "$ENV_FILE" 2>/dev/null \
        | tail -1 | cut -d= -f2- \
        | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//" \
        | tr -d '\r'
}

# Normaliza YAML para comparacao: tira CR, espaco no fim da linha e linha vazia.
# Sem isso um CRLF ou um espaco sobrando acusaria diferenca que nao existe.
_normalizar_yaml() { tr -d '\r' | sed -e 's/[[:space:]]*$//' -e '/^$/d'; }

# HTTP: imprime "<http_code> <arquivo_corpo>"
_http() {  # $1=url, demais = args extras do curl
    local url="$1"; shift
    local corpo="$TMP/corpo.$RANDOM"
    local code
    code="$(curl -s -o "$corpo" -w '%{http_code}' --max-time "$TIMEOUT" "$@" "$url" 2>/dev/null)"
    printf '%s %s' "${code:-000}" "$corpo"
}

# ---------------------------------------------------------------------------
# 1. Docker e containers
# ---------------------------------------------------------------------------

DOCKER_OK=0
checar_docker() {
    secao "1. Docker e containers"
    if ! _achar_docker; then
        falha "Docker" "daemon inacessivel" \
            "Abrir o Docker Desktop no Windows e aguardar 'Engine running'"
        return
    fi
    DOCKER_OK=1
    ok "Docker" "cliente: ${DOCKER##*/}"

    local nome status
    for nome in "$CONTAINER_PG" "$CONTAINER_BACK" "$CONTAINER_FRONT"; do
        status="$(_dk ps -a --filter "name=^${nome}$" --format '{{.Status}}' | head -1)"
        if [ -z "$status" ]; then
            falha "Container $nome" "nao existe" \
                "docker-compose up -d --build (na raiz do projeto, no Windows)"
        elif [[ "$status" == Up* ]]; then
            if [[ "$status" == *unhealthy* ]]; then
                falha "Container $nome" "$status" "docker logs --tail 50 $nome"
            elif [[ "$status" == *Restarting* ]]; then
                falha "Container $nome" "$status" "docker logs --tail 50 $nome"
            else
                ok "Container $nome" "$status"
            fi
        else
            falha "Container $nome" "$status" "docker-compose up -d"
        fi
    done

    # Imagem do frontend antiga em relacao ao codigo: o bundle servido e estatico,
    # copiado no build. Ele responde 200 feliz da vida enquanto chama uma API que
    # ja mudou de contrato - tela branca no navegador, tudo verde aqui. Foi o que
    # aconteceu em 13/09/2026: bundle de 15/07, oito commits de frontend depois.
    local img_epoch commit_epoch
    img_epoch="$(_dk image inspect agenteassistentedevendas-frontend:latest --format '{{.Created}}' \
        | head -1 | xargs -I{} date -d {} +%s 2>/dev/null)"
    commit_epoch="$(git -C "$RAIZ" log -1 --format=%ct -- frontend/src frontend/package.json 2>/dev/null)"
    if [[ "$img_epoch" =~ ^[0-9]+$ ]] && [[ "$commit_epoch" =~ ^[0-9]+$ ]]; then
        if [ "$img_epoch" -lt "$commit_epoch" ]; then
            local dias=$(( (commit_epoch - img_epoch) / 86400 ))
            falha "Imagem do frontend" "build anterior ao codigo ($dias dia(s))" \
                "docker-compose up -d --build frontend"
        else
            ok "Imagem do frontend" "mais nova que o ultimo commit de frontend/src"
        fi
    fi

    # Container "Up" nao significa aplicacao viva: o uvicorn pode estar em loop
    # de crash (foi o que aconteceu quando bcrypt faltou na imagem). Por isso os
    # checks de HTTP adiante sao os que valem, e aqui so olhamos o log recente.
    local erro
    erro="$(_dk logs --tail 30 "$CONTAINER_BACK" 2>/dev/null | grep -E 'ModuleNotFoundError|ImportError|Traceback' | tail -1)"
    if [ -n "$erro" ]; then
        aviso "Log do backend" "erro recente: ${erro:0:70}" \
            "docker-compose up -d --build backend (imagem desatualizada em relacao ao requirements.txt)"
    fi
}

# ---------------------------------------------------------------------------
# 2. Postgres
# ---------------------------------------------------------------------------

checar_postgres() {
    secao "2. Banco de dados"
    if [ "$DOCKER_OK" -eq 0 ]; then
        aviso "Postgres" "nao verificado (Docker indisponivel)" ""
        return
    fi
    if _dk exec "$CONTAINER_PG" pg_isready -U inforrel -d assistente_vendas | grep -q "accepting connections"; then
        ok "Postgres" "aceitando conexoes"
    else
        falha "Postgres" "pg_isready nao respondeu" "docker restart $CONTAINER_PG"
        return
    fi

    # Query real: prova que o schema existe, nao so que a porta abre.
    local n
    n="$(_dk exec "$CONTAINER_PG" psql -U inforrel -d assistente_vendas -tAc \
        'select count(*) from atendimentos' | tr -d ' ')"
    if [[ "$n" =~ ^[0-9]+$ ]]; then
        ok "Schema (tabela atendimentos)" "$n atendimentos"
    else
        falha "Schema (tabela atendimentos)" "consulta falhou: ${n:0:60}" \
            "Rodar 'alembic upgrade head' no backend"
    fi
}

# ---------------------------------------------------------------------------
# 3-4. Backend e frontend locais
# ---------------------------------------------------------------------------

checar_local() {
    secao "3. Servicos locais"
    local r code corpo

    r="$(_http "$URL_BACKEND_LOCAL/health")"; code="${r%% *}"; corpo="${r#* }"
    if [ "$code" = "200" ] && grep -q '"status":"healthy"' "$corpo"; then
        ok "Backend local ($URL_BACKEND_LOCAL/health)" "HTTP 200 healthy"
    else
        falha "Backend local ($URL_BACKEND_LOCAL/health)" "HTTP $code" \
            "docker logs --tail 50 $CONTAINER_BACK (porta pode abrir mesmo com o uvicorn em crash-loop)"
    fi

    r="$(_http "$URL_FRONT_LOCAL/")"; code="${r%% *}"; corpo="${r#* }"
    if [ "$code" = "200" ] && grep -q 'id="root"' "$corpo"; then
        ok "Frontend local ($URL_FRONT_LOCAL)" "HTTP 200, SPA servida"
    else
        falha "Frontend local ($URL_FRONT_LOCAL)" "HTTP $code" \
            "docker logs --tail 50 $CONTAINER_FRONT"
    fi

    # Prova o proxy nginx -> backend dentro da rede do compose.
    r="$(_http "$URL_FRONT_LOCAL/health")"; code="${r%% *}"
    if [ "$code" = "200" ]; then
        ok "Proxy nginx -> backend" "HTTP 200"
    else
        falha "Proxy nginx -> backend" "HTTP $code" \
            "502 aqui = nginx no ar, backend fora. Ver frontend/nginx.conf e o container do backend"
    fi
}

# ---------------------------------------------------------------------------
# 5. Tunel Cloudflare
# ---------------------------------------------------------------------------

checar_tunel() {
    secao "4. Tunel Cloudflare"
    local cloudflared=""
    local candidatos=(
        "/mnt/c/Program Files (x86)/cloudflared/cloudflared.exe"
        "/mnt/c/Program Files/cloudflared/cloudflared.exe"
    )
    local c
    for c in "${candidatos[@]}"; do [ -x "$c" ] && cloudflared="$c" && break; done
    if [ -z "$cloudflared" ] && command -v cloudflared >/dev/null 2>&1; then
        cloudflared="cloudflared"
    fi

    if command -v powershell.exe >/dev/null 2>&1; then
        local svc
        svc="$(powershell.exe -NoProfile -Command \
            "(Get-Service -Name *cloudflared* -ErrorAction SilentlyContinue | Select-Object -First 1).Status" \
            2>/dev/null | tr -d '\r' | tr -d ' ')"
        if [ "$svc" = "Running" ]; then
            ok "Servico cloudflared (Windows)" "Running"
        elif [ -n "$svc" ]; then
            falha "Servico cloudflared (Windows)" "$svc" \
                "PowerShell como admin: Start-Service Cloudflared"
        else
            aviso "Servico cloudflared (Windows)" "servico nao encontrado" \
                "Pode estar rodando em terminal: cloudflared tunnel run $TUNEL"
        fi
    fi

    if [ -n "$cloudflared" ]; then
        local info
        # stderr descartado de proposito: o cloudflared manda avisos ("your version
        # is outdated") em stderr, e com os dois no mesmo pipe eles se intercalam
        # NO MEIO de uma linha de stdout, corrompendo as colunas. Se o comando
        # falhar, `info` vem vazio e o ramo "sem conectores" cobre.
        info="$("$cloudflared" tunnel info "$TUNEL" 2>/dev/null | tr -d '\r')"
        local conectores
        conectores="$(printf '%s' "$info" | grep -cE '^[0-9a-f]{8}-[0-9a-f]{4}-')"
        if [ "${conectores:-0}" -gt 0 ]; then
            ok "Tunel $TUNEL" "$conectores conector(es) ativo(s)"
            # Mais de um conector saindo do MESMO IP = quase sempre o servico do
            # Windows e um `cloudflared tunnel run` de terminal rodando juntos.
            # A Cloudflare distribui as requisicoes entre eles, entao se as duas
            # configs divergirem a falha aparece intermitente, no meio das vezes.
            local ips_distintos
            ips_distintos="$(printf '%s' "$info" | grep -E '^[0-9a-f]{8}-[0-9a-f]{4}-' \
                | awk '{print $5}' | sort -u | grep -c .)"
            if [ "$conectores" -gt 1 ] && [ "${ips_distintos:-0}" -eq 1 ]; then
                aviso "Conectores duplicados" "$conectores conectores no mesmo IP de origem" \
                    "Servico + terminal rodando juntos. Parar um: Stop-Service Cloudflared, ou Ctrl+C no terminal"
            fi
        else
            falha "Tunel $TUNEL" "sem conectores" \
                "cloudflared tunnel run $TUNEL (ou reiniciar o servico)"
        fi
    else
        aviso "Binario cloudflared" "nao encontrado" \
            "O check de URL publica abaixo ja cobre o resultado final do tunel"
    fi
}

# ---------------------------------------------------------------------------
# Ingress do tunel: o que o config.yml promete x o que existe de fato
# ---------------------------------------------------------------------------

# Tres coisas precisam estar alinhadas para um hostname do tunel funcionar:
# o ingress no config.yml, o registro DNS na Cloudflare, e o servico local que
# atende a porta. Editar so o config.yml nao basta - e da para editar o arquivo
# ERRADO, porque o servico do Windows roda com um `--config` proprio
# (systemprofile), nao com o do perfil do usuario.
# `app.auxvendas.com` ja e verificado como FALHA na secao 5; os demais hostnames
# sao auxiliares (ex.: spike.auxvendas.com) e saem como AVISO.
checar_ingress_tunel() {
    local cfg_usuario="$SANITY_CLOUDFLARED_CONFIG"
    if [ -z "$cfg_usuario" ]; then
        local perfil
        perfil="$(powershell.exe -NoProfile -Command 'Write-Output $env:USERPROFILE' 2>/dev/null | tr -d '\r')"
        [ -n "$perfil" ] && cfg_usuario="$(wslpath "$perfil" 2>/dev/null)/.cloudflared/config.yml"
    fi
    [ -f "$cfg_usuario" ] || return 0

    secao "5. Ingress do tunel"

    # Qual config o servico realmente usa? Se nao for esta, editar esta nao surte efeito.
    local cfg_servico
    cfg_servico="$(powershell.exe -NoProfile -Command \
        "(Get-CimInstance Win32_Service -Filter \"Name like '%cloudflared%'\").PathName" \
        2>/dev/null | tr -d '\r' | grep -oiE '\-\-config +[^ ]+' | awk '{print $2}')"
    if [ -n "$cfg_servico" ]; then
        local cfg_servico_wsl
        cfg_servico_wsl="$(wslpath "$cfg_servico" 2>/dev/null)"
        if [ "$cfg_servico_wsl" = "$cfg_usuario" ]; then
            ok "Config do servico" "e a mesma do seu perfil"
        else
            # Caminho diferente nao e defeito: os dois arquivos podem estar em
            # sincronia. O que importa e o CONTEUDO — so que ler o do
            # systemprofile exige admin, entao nem sempre da para comparar.
            local conteudo_servico
            conteudo_servico="$(powershell.exe -NoProfile -Command \
                "Get-Content '$cfg_servico' -Raw -ErrorAction SilentlyContinue" 2>/dev/null | tr -d '\r')"
            if [ -z "$conteudo_servico" ]; then
                nota "Config do servico" "outro arquivo, nao comparavel sem admin" \
                    "Servico usa $cfg_servico; mantenha-o em sincronia com $cfg_usuario"
            elif [ "$(printf '%s' "$conteudo_servico" | _normalizar_yaml)" \
                 = "$(_normalizar_yaml < "$cfg_usuario")" ]; then
                ok "Config do servico" "arquivo diferente, conteudo identico"
            else
                aviso "Config do servico" "conteudo DIFERENTE do seu perfil" \
                    "O servico obedece $cfg_servico. Copiar a sua versao para la (admin) e reiniciar"
            fi
        fi
    fi

    # Compara o que a ORIGEM local responde com o que o hostname publico responde,
    # no mesmo caminho. Julgar pelo codigo sozinho nao funciona: um 404 em "/"
    # pode ser o pega-tudo do cloudflared OU simplesmente a origem nao ter rota
    # em "/" (o receptor do spike so expoe /webhook e /docs). Se os dois lados
    # dizem a mesma coisa, o caminho publico->tunel->origem esta inteiro.
    local hostname servico
    while read -r hostname servico; do
        [ -n "$hostname" ] || continue
        # O hostname principal ja tem cobertura propria na secao seguinte.
        [ "https://$hostname" = "$URL_PUBLICA" ] && continue

        if ! getent hosts "$hostname" >/dev/null 2>&1; then
            aviso "Ingress $hostname" "no config.yml mas SEM registro DNS" \
                "cloudflared tunnel route dns $TUNEL $hostname (no Windows)"
            continue
        fi

        local r code_local code_publico
        r="$(_http "$servico/")";          code_local="${r%% *}"
        r="$(_http "https://$hostname/")"; code_publico="${r%% *}"

        if [ "$code_local" = "000" ]; then
            aviso "Ingress $hostname" "origem $servico nao responde" \
                "DNS e tunel ok; falta subir o processo que atende essa porta"
        elif [ "$code_publico" = "000" ]; then
            aviso "Ingress $hostname" "origem ok, mas o hostname publico nao responde" \
                "Tunel nao esta roteando esse hostname. Conferir o ingress e reiniciar o cloudflared"
        elif [ "$code_publico" = "$code_local" ]; then
            ok "Ingress $hostname" "publico e origem coerentes (HTTP $code_local)"
        else
            aviso "Ingress $hostname" "publico HTTP $code_publico, origem HTTP $code_local" \
                "Divergencia entre o que o tunel entrega e o que a origem responde"
        fi
    done <<EOF_INGRESS
$(tr -d '\r' < "$cfg_usuario" | awk '/^[[:space:]]*-[[:space:]]*hostname:/ { h=$NF; next }
       /^[[:space:]]*service:/ && h != "" { print h, $NF; h="" }')
EOF_INGRESS
}

# ---------------------------------------------------------------------------
# 6-7. URL publica
# ---------------------------------------------------------------------------

checar_publico() {
    secao "6. URL publica ($URL_PUBLICA)"
    local r code corpo

    r="$(_http "$URL_PUBLICA/")"; code="${r%% *}"; corpo="${r#* }"
    if [ "$code" != "200" ]; then
        falha "Site $URL_PUBLICA" "HTTP $code" \
            "530/1033 = tunel fora do ar; 502 = tunel ok, container frontend fora"
        return 1
    fi
    if ! grep -q 'id="root"' "$corpo"; then
        falha "Site $URL_PUBLICA" "HTTP 200 mas nao e a SPA do painel" \
            "Conferir ingress do config.yml do cloudflared (deve apontar para localhost:3000)"
        return 1
    fi
    ok "Site $URL_PUBLICA" "HTTP 200, SPA servida"

    # O HTML sozinho nao prova que a tela carrega: o bundle precisa existir.
    local bundle
    bundle="$(grep -o 'src="/assets/[^"]*\.js"' "$corpo" | head -1 | sed 's/src="//;s/"//')"
    if [ -n "$bundle" ]; then
        r="$(_http "$URL_PUBLICA$bundle")"; code="${r%% *}"
        if [ "$code" = "200" ]; then
            ok "Bundle JS do painel" "HTTP 200 ($bundle)"
        else
            falha "Bundle JS do painel" "HTTP $code em $bundle" \
                "Build do frontend desatualizado: docker-compose up -d --build frontend"
        fi
    else
        aviso "Bundle JS do painel" "nao referenciado no HTML" ""
    fi

    r="$(_http "$URL_PUBLICA/health")"; code="${r%% *}"; corpo="${r#* }"
    if [ "$code" = "200" ] && grep -q '"status":"healthy"' "$corpo"; then
        ok "API publica ($URL_PUBLICA/health)" "HTTP 200 healthy"
    else
        falha "API publica ($URL_PUBLICA/health)" "HTTP $code" \
            "Tunel chega no nginx mas nao no backend. Ver container $CONTAINER_BACK"
    fi
    return 0
}

# ---------------------------------------------------------------------------
# 8-9. Login e aba Acompanhamento
# ---------------------------------------------------------------------------

# Nao ha navegador headless disponivel neste ambiente, entao "o front mostra
# dados" e verificado pelo que a tela consome: o bundle carrega (acima) e a API
# /api/atendimentos/ativas devolve linhas. Nao substitui olhar a tela.
checar_painel() {
    secao "7. Painel: login e aba Acompanhamento"
    local r code corpo
    rm -f "$COOKIES"

    # Gate de autenticacao aberto (AUTH_ENABLED=false no backend/.env) e escape
    # hatch temporario de dev/QA. Avisa sempre, para nao ficar esquecido ligado.
    r="$(_http "$URL_PUBLICA/api/atendimentos/ativas?limit=1")"
    if [ "${r%% *}" = "200" ]; then
        aviso "Gate de autenticacao" "/api/* responde SEM login" \
            "AUTH_ENABLED=false em backend/.env. Voltar para true quando nao precisar mais"
    fi

    r="$(_http "$URL_PUBLICA/api/auth/login" -c "$COOKIES" \
        -H "Content-Type: application/json" \
        -d "{\"login\":\"$LOGIN\",\"senha\":\"$SENHA\"}")"
    code="${r%% *}"; corpo="${r#* }"
    case "$code" in
        200) ok "Login ($LOGIN)" "HTTP 200, sessao aberta" ;;
        401) falha "Login ($LOGIN)" "HTTP 401 credenciais invalidas" \
                "Ajustar SANITY_LOGIN/SANITY_SENHA em sanity_check.conf" ; return ;;
        *)   falha "Login ($LOGIN)" "HTTP $code" "$(head -c 80 "$corpo")" ; return ;;
    esac

    r="$(_http "$URL_PUBLICA/api/atendimentos/ativas?limit=5" -b "$COOKIES")"
    code="${r%% *}"; corpo="${r#* }"
    if [ "$code" != "200" ]; then
        falha "Aba Acompanhamento (API)" "HTTP $code" \
            "GET /api/atendimentos/ativas - ver docker logs $CONTAINER_BACK"
        return
    fi
    local total
    total="$(grep -o '"total"[[:space:]]*:[[:space:]]*[0-9]*' "$corpo" | head -1 | grep -o '[0-9]*$')"
    if [ -z "$total" ]; then
        falha "Aba Acompanhamento (API)" "resposta sem campo 'total'" \
            "Contrato do endpoint mudou? Ver backend/main.py::listar_atendimentos_ativos"
    elif [ "$total" -eq 0 ]; then
        aviso "Aba Acompanhamento (API)" "HTTP 200 mas 0 atendimentos ativos" \
            "Tela vai aparecer vazia. Pode ser legitimo (nenhum atendimento aberto) ou banco errado"
    else
        ok "Aba Acompanhamento (API)" "$total atendimento(s) ativo(s)"
    fi
}

# ---------------------------------------------------------------------------
# 10. Webhook
# ---------------------------------------------------------------------------

checar_webhook() {
    secao "8. Webhook (entrada de mensagens do Twilio)"
    local r code corpo

    # Check leve: POST sem campos deve dar 422 (rota viva, validacao do FastAPI),
    # sem criar nenhum dado.
    r="$(_http "$URL_PUBLICA/webhook" -X POST)"; code="${r%% *}"
    if [ "$code" = "422" ]; then
        ok "Rota POST /webhook" "HTTP 422 (rota viva, validando campos)"
    elif [ "$code" = "200" ]; then
        aviso "Rota POST /webhook" "HTTP 200 sem campos obrigatorios" \
            "Esperado 422. Contrato do endpoint mudou?"
    else
        falha "Rota POST /webhook" "HTTP $code" \
            "Twilio nao consegue entregar mensagens. Ver o backend e o ingress do tunel"
        return
    fi

    [ "$PROFUNDO" -eq 1 ] || return

    # Check profundo: exercita o cerebro de verdade. Cria contato/atendimento/
    # mensagem no banco de QA e apaga depois via /api/dev/telefones.
    r="$(_http "$URL_PUBLICA/webhook" -X POST \
        --data-urlencode "From=whatsapp:$TELEFONE_TESTE" \
        --data-urlencode "Body=sanity check automatico, favor ignorar" \
        --data-urlencode "MessageSid=SMsanitycheck$(date +%s)")"
    code="${r%% *}"; corpo="${r#* }"
    if [ "$code" = "200" ] && grep -q "<Response>" "$corpo"; then
        local tam; tam="$(wc -c < "$corpo")"
        ok "Ponta a ponta pelo /webhook" "TwiML devolvido ($tam bytes)"
    else
        falha "Ponta a ponta pelo /webhook" "HTTP $code" \
            "O cerebro nao processou a mensagem. Ver docker logs $CONTAINER_BACK"
    fi

    # Limpeza (exige DEBUG=true no backend; fora disso o dado de teste fica).
    r="$(_http "$URL_PUBLICA/api/dev/telefones/$TELEFONE_TESTE" -X DELETE -b "$COOKIES")"
    code="${r%% *}"
    case "$code" in
        200) ok "Limpeza do dado de teste" "telefone $TELEFONE_TESTE removido" ;;
        404) ok "Limpeza do dado de teste" "nada a remover" ;;
        *)   aviso "Limpeza do dado de teste" "HTTP $code" \
                "Remover a mao: DELETE /api/dev/telefones/$TELEFONE_TESTE (exige DEBUG=true)" ;;
    esac
}

# ---------------------------------------------------------------------------
# 11. Twilio
# ---------------------------------------------------------------------------

# Escopo deliberado: valida CREDENCIAL + ALCANCE da API (leitura). Nao envia
# mensagem, por dois motivos: (a) a conta e trial e o Sandbox recusa texto livre
# no Body com erro 21654 - so aceita template via ContentSid, que exige conta
# paga; (b) o backend nao tem cliente REST da Twilio (Fase 10), entao o unico
# caminho de saida hoje e o TwiML sincrono do /webhook, coberto acima.
# Ver AnotacoesPessoais/Beto/spike_twilio/STATUS.md.
checar_twilio() {
    secao "9. Twilio"
    local sid key secret token
    sid="$(_ler_env TWILIO_ACCOUNT_SID)"
    key="$(_ler_env TWILIO_API_KEY_SID)"
    secret="$(_ler_env TWILIO_API_KEY_SECRET)"
    token="$(_ler_env TWILIO_AUTH_TOKEN)"

    if [ -z "$sid" ]; then
        aviso "Credenciais Twilio" "TWILIO_ACCOUNT_SID ausente em $ENV_FILE" \
            "Sem isso nao da para verificar a Twilio"
        return
    fi

    local usuario
    if [ -n "$key" ] && [ -n "$secret" ]; then
        usuario="$key:$secret"
    elif [ -n "$token" ]; then
        usuario="$sid:$token"
    else
        aviso "Credenciais Twilio" "sem API Key nem Auth Token em $ENV_FILE" ""
        return
    fi

    local r code corpo
    r="$(_http "https://api.twilio.com/2010-04-01/Accounts/$sid/Messages.json?PageSize=1" -u "$usuario")"
    code="${r%% *}"; corpo="${r#* }"
    case "$code" in
        200)
            local n
            n="$(grep -o '"sid"[[:space:]]*:[[:space:]]*"SM[^"]*"' "$corpo" | wc -l | tr -d ' ')"
            ok "API Twilio (leitura de mensagens)" "HTTP 200, $n mensagem(ns) no historico" ;;
        401)
            local motivo; motivo="$(grep -o '"code"[[:space:]]*:[[:space:]]*[0-9]*' "$corpo" | grep -o '[0-9]*$')"
            falha "API Twilio (leitura de mensagens)" "HTTP 401 (codigo ${motivo:-?})" \
                "70051 = API Key sem permissao; 20003 = credencial invalida. Recriar a key com escopo de Messaging" ;;
        000)
            falha "API Twilio (leitura de mensagens)" "sem resposta (timeout/rede)" \
                "Conferir conexao de saida para api.twilio.com" ;;
        *)
            falha "API Twilio (leitura de mensagens)" "HTTP $code" "$(head -c 80 "$corpo")" ;;
    esac

    local numero; numero="$(_ler_env TWILIO_WHATSAPP_NUMBER)"
    if [ -n "$numero" ]; then
        ok "Numero WhatsApp configurado" "presente no .env"
    else
        aviso "Numero WhatsApp configurado" "TWILIO_WHATSAPP_NUMBER ausente" ""
    fi
}

# ---------------------------------------------------------------------------
# Execucao
# ---------------------------------------------------------------------------

if [ "$MODO_SAIDA" = "normal" ]; then
    printf '%sSanity check - Assistente de Vendas%s  %s%s%s\n' \
        "$C_TITULO" "$C_FIM" "$C_FRACO" "$(date '+%d/%m/%Y %H:%M:%S')" "$C_FIM"
    [ "$PROFUNDO" -eq 1 ] && printf '%smodo profundo: envia mensagem real pelo /webhook%s\n' "$C_AVISO" "$C_FIM"
fi

checar_docker
checar_postgres
checar_local
checar_tunel
checar_ingress_tunel
if checar_publico; then
    checar_painel
    checar_webhook
else
    aviso "Painel e webhook" "nao verificados (URL publica fora do ar)" ""
    aviso "Webhook" "nao verificado (URL publica fora do ar)" ""
fi
checar_twilio

if [ "$N_FALHA" -gt 0 ]; then
    STATUS_FINAL="FALHA"; SAIDA=1
elif [ "$N_AVISO" -gt 0 ]; then
    STATUS_FINAL="AVISO"; SAIDA=2
else
    STATUS_FINAL="OK"; SAIDA=0
fi

if [ "$MODO_SAIDA" = "json" ]; then
    printf '{"resumo":true,"status":"%s","ok":%d,"avisos":%d,"falhas":%d,"detalhe":"%s","timestamp":"%s"}\n' \
        "$STATUS_FINAL" "$N_OK" "$N_AVISO" "$N_FALHA" \
        "$(_json_escape "$FALHAS_RESUMO")" "$(date -Iseconds)"
elif [ "$MODO_SAIDA" = "silencioso" ] && [ "$STATUS_FINAL" = "OK" ]; then
    : # nada a dizer - cron/monitor so precisa do codigo de saida
else
    printf '\n'
    case "$STATUS_FINAL" in
        OK)    printf '%sTudo no ar%s - %d checks ok\n' "$C_OK" "$C_FIM" "$N_OK" ;;
        AVISO) printf '%sNo ar com ressalvas%s - %d ok, %d aviso(s)\n' "$C_AVISO" "$C_FIM" "$N_OK" "$N_AVISO" ;;
        FALHA) printf '%sPROBLEMA%s - %d ok, %d aviso(s), %d FALHA(S): %s\n' \
                   "$C_ERRO" "$C_FIM" "$N_OK" "$N_AVISO" "$N_FALHA" "$FALHAS_RESUMO" ;;
    esac
fi

exit "$SAIDA"
