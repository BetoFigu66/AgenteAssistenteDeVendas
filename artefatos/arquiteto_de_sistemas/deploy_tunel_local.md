# Deploy via Túnel Local (Cloudflare Tunnel)

**Versão**: 1.0
**Data**: 2026-04-28
**Autor**: Arquiteto de Sistemas
**Status**: Aprovado (POC)

---

## 1. Objetivo

Disponibilizar a aplicação (frontend + backend) rodando na máquina do Beto para acesso público pela **Kika** e pela **Rita**, via URL HTTPS, sem custo financeiro e sem depender de deploy em provedor cloud.

**Limitações aceitas**:
- Aplicação só fica no ar enquanto a máquina do Beto estiver ligada e com os containers rodando.
- Banco de dados é o Postgres local (dados de teste, não são produção).
- Sem alta disponibilidade, sem SLA.

**Quando usar**: validação funcional pela Kika e demonstrações/testes assistidos com a Rita enquanto não há orçamento para cloud.

---

## 2. Visão Geral da Solução

```
[Kika/Rita browser]
        │  HTTPS
        ▼
[https://<subdominio>.trycloudflare.com]       (ou subdomínio fixo em domínio próprio)
        │
        ▼
[Cloudflare Edge] ──── túnel outbound ────►  [cloudflared na máquina do Beto]
                                                     │
                                                     ▼
                                              [docker-compose]
                                              ├─ frontend  :3000
                                              ├─ backend   :8000
                                              └─ postgres  :5433
```

Por que Cloudflare Tunnel:
- Gratuito, sem limite prático para POC.
- Não exige abrir portas no roteador (túnel outbound).
- HTTPS/TLS gerenciado automaticamente.
- Suporta múltiplos hostnames (frontend e backend podem ter URLs separadas se necessário).

Alternativas descartadas para este cenário:
- **ngrok free**: URL muda a cada restart; URL fixa exige plano pago.
- **LocalTunnel**: menos estável.
- **Codespaces**: ADR-005, dorme, limite de 60h/mês.

---

## 3. Pré-Requisitos

Na máquina que vai hospedar (Beto):

- Windows 10/11 com Docker Desktop instalado e funcionando.
- Projeto clonado e `docker-compose up` funcionando localmente.
- Conta gratuita no Cloudflare (apenas para o modo **Named Tunnel**, seção 5). Não precisa ter domínio próprio no modo **Quick Tunnel** (seção 4).

---

## 4. Modo Rápido - Quick Tunnel (URL temporária)

Use quando precisar de acesso **pontual** (uma sessão de teste), sem cadastrar nada no Cloudflare. A URL muda a cada execução.

### 4.1 Instalar cloudflared

PowerShell como Administrador:

```powershell
winget install --id Cloudflare.cloudflared
```

Confirmar:

```powershell
cloudflared --version
```

### 4.2 Subir a aplicação

```powershell
docker-compose up -d
```

Validar localmente:
- Frontend: http://localhost:3000
- Backend:  http://localhost:8000/docs

### 4.3 Abrir o túnel para o frontend

Em um terminal dedicado (deixar aberto):

```powershell
cloudflared tunnel --url http://localhost:3000
```

O cloudflared imprime uma URL do tipo:

```
https://<palavras-aleatorias>.trycloudflare.com
```

**Essa é a URL que você envia para Kika e Rita.**

### 4.4 Expor também o backend (se necessário)

O frontend faz chamadas à API. No POC atual o frontend em produção é servido pelo Nginx dentro do container `frontend` e normalmente a chamada à API é relativa. Se a Kika/Rita precisarem acessar o Swagger (`/docs`) ou se o frontend apontar para `http://localhost:8000` em tempo de execução, abra um segundo túnel em outro terminal:

```powershell
cloudflared tunnel --url http://localhost:8000
```

E ajuste a variável `VITE_API_URL` (ou equivalente) do frontend para a URL pública do backend, **rebuildando** o frontend:

```powershell
docker-compose up -d --build frontend
```

### 4.5 Encerrar

`Ctrl + C` nos terminais do cloudflared. `docker-compose down` para parar os containers.

---

## 5. Modo Estável - Named Tunnel (URL fixa)

Use quando a Kika/Rita precisarem de uma URL que **não muda** entre sessões. Requer ter um domínio (próprio ou gratuito) conectado ao Cloudflare.

### 5.1 Associar um domínio ao Cloudflare

Opções:
- Usar domínio próprio já existente → alterar nameservers para o Cloudflare (grátis).
- Registrar domínio barato (ex: `.click`, `.xyz` em torno de US$ 1-3/ano) e apontar para Cloudflare.

Após o domínio estar gerenciado pelo Cloudflare, prosseguir.

### 5.2 Autenticar cloudflared

```powershell
cloudflared tunnel login
```

Abre o browser para autorizar o cloudflared a acessar sua conta/domínio Cloudflare.

### 5.3 Criar o túnel

```powershell
cloudflared tunnel create inforrel-poc
```

Isso gera um arquivo de credenciais em `%USERPROFILE%\.cloudflared\<tunnel-id>.json`.

### 5.4 Criar arquivo de configuração

Criar `%USERPROFILE%\.cloudflared\config.yml`:

```yaml
tunnel: inforrel-poc
credentials-file: C:\Users\<SEU_USUARIO>\.cloudflared\<tunnel-id>.json

ingress:
  - hostname: app.seudominio.com
    service: http://localhost:3000
  - hostname: api.seudominio.com
    service: http://localhost:8000
  - service: http_status:404
```

### 5.5 Registrar os subdomínios (DNS)

```powershell
cloudflared tunnel route dns inforrel-poc app.seudominio.com
cloudflared tunnel route dns inforrel-poc api.seudominio.com
```

### 5.6 Rodar o túnel

```powershell
cloudflared tunnel run inforrel-poc
```

Compartilhar com Kika/Rita:
- Frontend: `https://app.seudominio.com`
- Backend/Swagger: `https://api.seudominio.com/docs`

### 5.7 Rodar como serviço Windows (opcional)

Para o túnel subir junto com a máquina:

```powershell
cloudflared service install
```

---

## 6. Checklist Operacional para Liberar uma Versão

Toda vez que for liberar uma versão para Kika/Rita:

1. [ ] `git pull` na branch alvo (ex: `develop` ou `qa`).
2. [ ] `docker-compose up -d --build` (rebuild se houve mudança).
3. [ ] Rodar migrations se necessário: ver `docs/comandos_uteis.md`.
4. [ ] Validar local: `http://localhost:3000` e `http://localhost:8000/docs`.
5. [ ] Iniciar o túnel (Quick ou Named).
6. [ ] Enviar a URL pública para Kika/Rita junto com:
   - O que mudou nesta versão.
   - Critérios de aceite / pontos de atenção.
   - Horário em que a máquina estará ligada (se Quick Tunnel).
7. [ ] Ao encerrar os testes: `Ctrl+C` no túnel, `docker-compose down` se desejar.

---

## 7. Segurança e Privacidade

- Dados acessados durante o túnel passam pelo Cloudflare (TLS end-to-end).
- Não colocar dados reais de clientes neste ambiente.
- Se precisar restringir acesso a Kika/Rita apenas, o Cloudflare oferece **Zero Trust Access** (grátis até 50 usuários) - pode ser adicionado depois no Named Tunnel exigindo login por e-mail.
- Nunca compartilhar arquivos de `.env` nem credenciais pelo túnel.

---

## 8. Troubleshooting

| Sintoma | Causa provável | Ação |
|---------|----------------|------|
| `cloudflared: command not found` | PATH não atualizado | Reabrir PowerShell ou reinstalar via winget |
| URL `trycloudflare.com` retorna 502 | Serviço local não está em `http://localhost:<porta>` | Verificar `docker ps` e portas expostas |
| Frontend abre mas API falha | Frontend aponta para `localhost:8000` no browser do cliente | Expor o backend também (seção 4.4) e ajustar `VITE_API_URL` |
| Túnel cai sozinho | Máquina entrou em modo de suspensão | Desativar suspensão durante a sessão de teste |
| Kika/Rita veem a versão antiga | Cache do browser | Pedir `Ctrl+Shift+R` |

---

## 9. Relação com a Política de Branches

- Kika valida a partir da branch `qa` (quando existir) ou `develop` (no POC) - ver `politica_branches.md`.
- Rita valida a partir da branch `homolog` (quando existir) ou versão aprovada pela Kika.
- O Beto mantém o túnel no ar durante as janelas de validação combinadas.

---

## 10. Histórico de Alterações

| Data | Versão | Alteração | Autor |
|------|--------|-----------|-------|
| 2026-04-28 | 1.0 | Criação do documento | Arquiteto de Sistemas |
