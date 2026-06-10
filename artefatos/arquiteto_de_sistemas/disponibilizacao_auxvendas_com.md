# Disponibilização em `auxvendas.com` (Cloudflare)

**Versão**: 1.0  
**Data**: 2026-06-06  
**Autor**: Beto (Arquiteto) — rascunho para revisão da Kika  
**Status**: Proposta  
**Domínio**: `auxvendas.com` (registrado e gerenciado no Cloudflare)

---

## 1. Objetivo

Colocar o Assistente de Vendas (frontend + backend + Postgres) acessível via HTTPS no domínio `auxvendas.com`, em fase de **desenvolvimento**, com **custo zero ou mínimo** e pouco tráfego.

Este documento consolida **decisões**, **recomendação para o momento atual** e **passo a passo** operacional. Complementa:

- `deploy_tunel_local.md` — detalhes do Cloudflare Tunnel (genérico)
- `processo_disponibilizacao_versoes.md` — ADR-004 a ADR-006

---

## 2. Contexto técnico do projeto

| Componente | Stack | Porta local (docker-compose) |
|------------|-------|------------------------------|
| Frontend | React + Nginx | `3000` → container `:80` |
| Backend | FastAPI (uvicorn) | `8000` |
| Banco | PostgreSQL 16 + **pgvector** | `5433` → container `:5432` |

O Nginx do frontend **já faz proxy** de `/api`, `/webhook` e `/health` para o backend (`frontend/nginx.conf`). Isso permite expor **um único hostname público** sem CORS extra.

Webhook Twilio (REQ-008): `POST https://<host>/webhook`

---

## 3. Decisões — opções e recomendação

### 3.1 Onde hospedar a aplicação?

| Opção | Custo | 24/7 sem PC ligado | pgvector | Twilio webhook | Complexidade |
|-------|-------|--------------------|----------|----------------|--------------|
| **A — Cloudflare Tunnel + PC dev** | Grátis | Não | Sim (Postgres local) | OK enquanto PC+túnel ativos | Baixa |
| **B — Oracle Cloud Free (VM ARM)** | Grátis* | Sim | Sim (docker-compose) | OK | Alta |
| **C — Railway / Render + DB gerenciado** | ~$0–5/mês | Sim (com limites) | Depende do DB | Cold start pode falhar Twilio | Média |
| **D — Fly.io (3 VMs free)** | Grátis* | Sim | Postgres Fly ou Neon | OK se sempre acordado | Média-alta |

\* Pode exigir cartão de crédito para verificação; sem cobrança no tier free.

**Recomendação para agora (dev, pouco uso, custo zero):** **Opção A** — Named Tunnel Cloudflare apontando para o `docker-compose` na sua máquina.

**Motivos:**

- Você **já tem** o domínio no Cloudflare e documentação ADR-006 alinhada a isso.
- O projeto **já roda** com `docker-compose up`.
- Free tiers de PaaS (Render/Railway) **dormem** → cold start ~30s → risco de **timeout no webhook Twilio** (15s).
- Postgres com **pgvector** complica DB gratuito (Neon/Supabase funcionam, mas é mais uma peça para configurar).

**Quando migrar da Opção A:** quando precisar de URL **24/7** sem depender do seu PC (demo para Rita, Twilio produção, Kika testando fora do horário). Aí escolher **B** (VM gratuita) ou **C/D** com banco Neon (pgvector).

---

### 3.2 Estrutura de URLs (subdomínios)

| Opção | URLs | Prós | Contras |
|-------|------|------|---------|
| **Subdomínio único (recomendado)** | `https://app.auxvendas.com` | Nginx já unifica API + webhook; um certificado; Twilio simples | Raiz `auxvendas.com` fica vazia até landing page |
| **Dois subdomínios** | `app.` + `api.` | Separação clara | Dois registros DNS; CORS se frontend chamar API absoluta |
| **Raiz apenas** | `https://auxvendas.com` | URL curta | Mistura app com futuro site institucional |

**Decisão proposta:** **`app.auxvendas.com`** para o painel + API + webhook.

Opcional depois:

- `auxvendas.com` → redirect 301 para `app.` (ou landing futura)
- `www.auxvendas.com` → redirect para `app.`

**Twilio (sandbox/produção):** configurar webhook como `https://app.auxvendas.com/webhook`

---

### 3.3 Proteger o ambiente de dev?

O painel administrativo ficará **público na internet** se só usar o túnel.

| Opção | Custo | Esforço |
|-------|-------|---------|
| Nada (aceitar risco POC) | Grátis | Zero |
| **Cloudflare Zero Trust Access** (e-mail allowlist Kika/Rita/Beto) | Grátis até 50 usuários | Baixo |
| Basic Auth no Nginx | Grátis | Baixo |

**Decisão proposta:** adicionar **Zero Trust Access** em `app.auxvendas.com` assim que o Named Tunnel estiver estável (Passo 8 abaixo). Não expor dados reais de clientes neste ambiente (já previsto em ADR-006).

---

### 3.4 Banco de dados

| Fase | Onde fica o Postgres |
|------|----------------------|
| **Dev via túnel (A)** | Container local (`docker-compose`) — dados de teste |
| **Cloud 24/7 (futuro)** | Mesmo container na VM **ou** Neon/Supabase com pgvector + `DATABASE_URL` no backend |

Não migrar o banco para cloud até decidir a Opção B/C/D definitiva.

---

## 4. Passo a passo — Fase 1 (recomendada): `app.auxvendas.com` via Cloudflare Tunnel

### Pré-requisitos

- [X] Domínio `auxvendas.com` com **nameservers do Cloudflare** (painel Cloudflare → Overview → “Active”)
- [X] Docker Desktop no Windows funcionando
- [X] Repositório clonado; `docker-compose up` OK localmente
- [X] `cloudflared` instalado:

```powershell
winget install --id Cloudflare.cloudflared
cloudflared --version
```

---
### Passo 1 — Validar stack local

```powershell
cd C:\Beto\Pessoal\Python\git\AgenteAssistenteDeVendas
docker-compose up -d --build
```

Conferir:

- [X] http://localhost:3000 — painel abre
- [X] http://localhost:3000/api/... ou http://localhost:8000/docs — API responde
- [X] Migrations aplicadas (ver `docs/comandos_uteis.md`)

---

### Passo 2 — Autenticar cloudflared na conta Cloudflare

O `cloudflared` precisa de permissão na sua conta Cloudflare para criar o túnel e registros DNS. Isso é feito **uma vez** por máquina.

```powershell
cloudflared tunnel login
```

O comando abre o **navegador padrão** em uma página de login/autorização da Cloudflare (URL do tipo `https://dash.cloudflare.com/...`). Siga na **página web**, não no PowerShell:

1. **Entrar** na conta Cloudflare (se ainda não estiver logado).
2. **Clicar em `auxvendas.com`** nessa lista — a “zona” é o domínio que você gerencia em [dash.cloudflare.com](https://dash.cloudflare.com) → **Websites** → `auxvendas.com`.
3. A Cloudflare mostra a pergunta **“Authorize Cloudflare Tunnel”** (ou similar) e uma **lista dos domínios (zonas DNS)** da sua conta.
4. Confirmar / **Authorize** (Autorizar).

Se `auxvendas.com` **não aparecer** na lista, o domínio ainda não está nesta conta ou os nameservers não apontam para a Cloudflare. Confira em **Websites** se o site está **Active** antes de repetir o login.

Sucesso: o terminal exibe algo como *“You have successfully logged in”* e grava o certificado em `%USERPROFILE%\.cloudflared\cert.pem`.

---

### Passo 3 — Criar Named Tunnel

```powershell
cloudflared tunnel create auxvendas-dev
```

Anotar o **Tunnel ID** (UUID) exibido no terminal.
(9d67c75f-331b-4aba-a795-7ec97bbb7974 17/06/2026 8:56)

Arquivo de credenciais gerado:  
`%USERPROFILE%\.cloudflared\<TUNNEL-ID>.json`

---

### Passo 4 — Configurar ingress (um hostname → frontend)

Criar/editar `%USERPROFILE%\.cloudflared\config.yml`:

```yaml
tunnel: auxvendas-dev
credentials-file: C:\Users\betof\.cloudflared\<TUNNEL-ID>.json

ingress:
  - hostname: app.auxvendas.com
    service: http://localhost:3000
  - service: http_status:404
```

> **Por que só a porta 3000?** O container `frontend` (Nginx) já encaminha `/api`, `/webhook` e `/health` para o backend. Twilio e o painel usam o **mesmo host**.

Substituir `<TUNNEL-ID>` e o caminho do usuário se diferente.

---
### Passo 5 — Criar registro DNS no Cloudflare

```powershell
cloudflared tunnel route dns auxvendas-dev app.auxvendas.com
```

No painel Cloudflare → DNS, deve aparecer um CNAME `app` → `<tunnel-id>.cfargotunnel.com` (proxied).

Opcional (redirect raiz — fazer depois no dashboard):

- Page Rule ou Redirect Rule: `auxvendas.com/*` → `https://app.auxvendas.com/$1`

---

### Passo 6 — Subir o túnel

Teste em foreground:

```powershell
cloudflared tunnel run auxvendas-dev
```

Validar:

- [ ] https://app.auxvendas.com — painel carrega (HTTPS automático)
- [ ] https://app.auxvendas.com/docs ou `/api/...` — API via proxy Nginx
- [ ] https://app.auxvendas.com/webhook — endpoint existe (POST retorna resposta Twilio ou 422)

Encerrar teste: `Ctrl+C`.

---

### Passo 7 — Instalar túnel como serviço Windows (opcional, recomendado)

Para o túnel iniciar com o Windows (ainda depende do Docker estar up):

**Requer PowerShell como Administrador** (instalar serviço Windows usa o Service Control Manager). Se aparecer `Access is denied`, abra de novo o terminal elevado:

1. Menu Iniciar → digite **PowerShell**
2. **Executar como administrador**
3. Na pasta do projeto (ou de qualquer lugar, se `cloudflared` está no PATH):

```powershell
cloudflared service install
```

> **Armadilha no Windows:** o serviço roda como **LocalSystem**, não como seu usuário. Ele **não** lê `C:\Users\betof\.cloudflared\` — procura em `C:\Windows\System32\config\systemprofile\.cloudflared\`. Sem isso, o serviço fica *Running* mas o túnel **não conecta** (erro **1033** no browser; `cloudflared tunnel info` mostra *no active connection*).

**Passo 7b — Copiar config para o perfil do serviço** (PowerShell **como Administrador**):

```powershell
$dest = "C:\Windows\System32\config\systemprofile\.cloudflared"
$src  = "$env:USERPROFILE\.cloudflared"
New-Item -ItemType Directory -Force -Path $dest
Copy-Item "$src\cert.pem" "$dest\cert.pem" -Force
Copy-Item "$src\9d67c75f-331b-4aba-a795-7ec97bbb7974.json" "$dest\" -Force

@'
tunnel: auxvendas-dev
credentials-file: C:\Windows\System32\config\systemprofile\.cloudflared\9d67c75f-331b-4aba-a795-7ec97bbb7974.json

ingress:
  - hostname: app.auxvendas.com
    service: http://localhost:3000
  - service: http_status:404
'@ | Set-Content -Path "$dest\config.yml" -Encoding UTF8

$newPath = '"C:\Program Files (x86)\cloudflared\cloudflared.exe" --config C:\Windows\System32\config\systemprofile\.cloudflared\config.yml tunnel run auxvendas-dev'
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\Cloudflared" -Name ImagePath -Value $newPath
Restart-Service Cloudflared
```

Validar:

```powershell
cloudflared tunnel info auxvendas-dev   # deve listar CONNECTOR(S)
Invoke-WebRequest https://app.auxvendas.com -UseBasicParsing   # StatusCode 200
```

Reiniciar o serviço ou reboot. Confirmar em **Services** (`services.msc`) → **Cloudflared agent** → Status *Running* **e** conexão ativa no comando acima.

**Alternativa sem serviço:** deixar um terminal aberto com `cloudflared tunnel run auxvendas-dev` sempre que precisar do site no ar (Passo 6).

**Ordem de boot sugerida:** Docker Desktop (automático) → cloudflared service.

---

### Passo 8 — Restringir acesso (Zero Trust, opcional)
Beto: Pendente

1. Cloudflare Dashboard → **Zero Trust** → Access → Applications  
2. Add application → Self-hosted  
3. Domain: `app.auxvendas.com`  
4. Policy: Allow → e-mails `@...` (Beto, Kika, Rita)  
5. Salvar

Quem acessar o painel precisará login Cloudflare (OTP por e-mail).

---

### Passo 9 — Twilio (quando for testar WhatsApp real)

1. Twilio Console → WhatsApp Sandbox (ou número produção)  
2. **When a message comes in:** `https://app.auxvendas.com/webhook`  
3. Método: POST  
4. `.env` do backend com `TWILIO_*` (nunca commitar)

**Requisito:** PC ligado + `docker-compose` + túnel ativos durante o teste.

---

### Passo 10 — Checklist ao liberar versão para Kika

1. [ ] `git pull` na branch acordada (`dev` / `qa`)
2. [ ] `docker-compose up -d --build`
3. [ ] Migrations se houver
4. [ ] Testar local + https://app.auxvendas.com
5. [ ] Enviar URL + o que mudou + janela em que o ambiente fica no ar
6. [ ] Kika valida CTFs / critérios de aceite

---

## 5. Passo a passo — Fase 2 (futuro): hospedagem cloud 24/7
Beto: Pendente daqui prá frente.

Executar **somente** quando decidir sair do túnel local. Escolher **uma** linha abaixo.

### 5.1 Linha Oracle Cloud Free (VM)

1. Criar conta Oracle Cloud (Always Free ARM — 4 OCPU / 24 GB RAM elegível)
2. VM Ubuntu + Docker + Docker Compose
3. Clonar repo; copiar `.env` de produção/dev
4. `docker-compose up -d` (considerar compose de produção sem bind-mount de código)
5. Named Tunnel **na VM** (mesmo `config.yml`, `localhost:3000`) **ou** abrir porta 443 com Caddy/Nginx + certbot (menos recomendado que Tunnel)
6. Manter `app.auxvendas.com` apontando para o túnel da VM

**Prós:** stack idêntica ao dev, pgvector local, 24/7 real.  
**Contras:** setup inicial maior; conta Oracle às vezes difícil de criar.

### 5.2 Linha PaaS (Railway / Render / Fly.io)

1. Postgres gerenciado com **pgvector** (ex.: [Neon](https://neon.tech) free tier)
2. Deploy backend e frontend como serviços separados **ou** monolith frontend+nginx
3. Variável `DATABASE_URL` apontando para Neon
4. Migrations Alembic no deploy
5. DNS: CNAME `app` → URL do PaaS **ou** Tunnel se o PaaS não der HTTPS customizado fácil

**Atenção Twilio:** desabilitar sleep (plano pago) ou usar worker always-on; free tier com cold start **não** é confiável para webhook.

---

## 6. Variáveis de ambiente (produção/dev exposto)

Arquivo `backend/.env` (não versionado). Mínimo para ambiente público:

```env
DEBUG=false
DATABASE_URL=postgresql://inforrel:<senha>@postgres:5432/assistente_vendas
# Twilio (quando ativo)
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_NUMBER=whatsapp:+...
# LLM / Embeddings (conforme config.py)
```

Trocar senhas default do `docker-compose.yml` antes de expor publicamente (mesmo com Zero Trust).

---

## 7. Troubleshooting

| Sintoma | Causa provável | Ação |
|---------|----------------|------|
| **Error 1033** — Tunnel error / unable to resolve | Serviço Windows *Running* mas sem config no perfil **LocalSystem** | Passo 7b (copiar para `systemprofile\.cloudflared` + ajustar `ImagePath` no registro); validar com `cloudflared tunnel info` |
| DNS não resolve `app.` | CNAME não criado ou propagação | `cloudflared tunnel route dns` + aguardar 5 min |
| 502 Bad Gateway | Docker parado ou porta errada | `docker ps`; subir compose; conferir `localhost:3000` |
| API 404 no browser | Acesso direto `:8000` em vez de via Nginx | Usar `app.auxvendas.com/api/...` |
| Twilio timeout | PC dormiu ou cold start | Manter máquina acordada; evitar sleep |
| Loop de redirect | SSL mode incorreto | Cloudflare SSL/TLS → **Full** (não Strict se origem for HTTP local) |
| Webhook 403 | Zero Trust bloqueando Twilio | Criar policy Bypass para path `/webhook` ou IP Twilio |
| Build Docker no PowerShell: `venv\lib64` inaccessible | `backend/venv` (WSL) no build context | Usar `.dockerignore`; `docker-compose build --no-cache` (ver `docs/comandos_uteis.md`) |

**SSL/TLS (Cloudflare → origem local):** modo **Full** é suficiente (origem `http://localhost:3000` sem certificado local).

---

## 8. Decisões registradas / pendentes

| # | Decisão | Status |
|---|---------|--------|
| D1 | Fase 1 = Cloudflare Tunnel + docker local | **Proposta (Beto)** |
| D2 | Hostname = `app.auxvendas.com` (único) | **Proposta** |
| D3 | Zero Trust após estabilizar | **Proposta** |
| D4 | Fase 2 (cloud 24/7) — Oracle vs PaaS | **Pendente** — decidir quando sair do túnel |
| D5 | CTF-002-08 / validação Kika no domínio público | Independente — ver QA |

---

## 9. Histórico de Alterações

| Data | Versão | Alteração | Autor |
|------|--------|-----------|-------|
| 2026-06-06 | 1.0 | Criação: plano `auxvendas.com`, decisões A–D, passo a passo Fase 1 (Named Tunnel) e esboço Fase 2 (cloud 24/7) | Beto |

---

## 10. Referências

- [Cloudflare Tunnel — documentação](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
- [Twilio Webhooks](https://www.twilio.com/docs/usage/webhooks)
- `artefatos/arquiteto_de_sistemas/deploy_tunel_local.md`
- `artefatos/arquiteto_de_sistemas/processo_disponibilizacao_versoes.md` (ADR-006)
