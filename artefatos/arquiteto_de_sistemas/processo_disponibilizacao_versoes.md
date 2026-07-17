# Processo de Disponibilização de Versões

<!-- CLASSIFICACAO: SISTEMA-DEV -->

**Versão**: 1.0  
**Data**: 2026-04-19  
**Autor**: Arquiteto de Sistemas  
**Status**: Aprovado  

---

## 1. Objetivo

Definir como as versões do sistema serão disponibilizadas para validação, evitando que os validadores precisem executar código fonte diretamente.

---

## 2. Opções Avaliadas

| Opção | Como funciona | Prós | Contras |
|-------|---------------|------|---------|
| **Deploy em servidor** | Hospeda em VPS/cloud, acesso via URL | Ambiente real, fácil acesso | Custo, setup inicial |
| **Ngrok + máquina dev** | Dev roda local, expõe via ngrok | Zero custo, rápido | Depende do dev estar online |
| **Docker + instruções simples** | Validador roda `docker-compose up` | Isolado, reproduzível | Validador precisa ter Docker |
| **GitHub Codespaces** | Ambiente cloud no GitHub | Zero setup local | Custo após limite gratuito |
| **Render/Railway/Fly.io** | Deploy automático do repo | Free tier, CI/CD simples | Limitações do free tier |

---

## 3. Detalhamento das Opções Consideradas

### 3.1 GitHub Codespaces

**Limite gratuito (contas pessoais):**
- **60 horas/mês** em máquinas 2-core
- **15 GB/mês** de storage
- Se usar máquina 4-core, são 30 horas/mês (consome 2x)

**Na prática:**
- 60h ÷ 20 dias úteis = ~3h/dia de uso
- Suficiente para validações pontuais
- Codespace "dorme" após 30min de inatividade
- **Atenção**: Webhook do Twilio precisa de endpoint sempre disponível durante testes

**Veredicto**: Bom para validação com cliente (Rita), requer agendamento de sessões de teste

---

### 3.2 Render / Railway / Fly.io

| Plataforma | Free Tier | Limitações |
|------------|-----------|------------|
| **Render** | 750h/mês (web services) | Dorme após 15min sem requests; cold start ~30s; 512MB RAM |
| **Railway** | $5 crédito/mês | ~500h de uso; dorme se inativo; 512MB RAM |
| **Fly.io** | 3 VMs shared-cpu | 256MB RAM cada; requer cartão de crédito para ativar |

**Problemas comuns no free tier:**
1. **Sleep/Cold start** - App dorme após inatividade, primeira mensagem demora ~30s
2. **RAM limitada** - 512MB pode ser apertado com FastAPI + modelo de IA carregado
3. **Sem domínio fixo garantido** (Render muda se recriar o serviço)
4. **Logs limitados** - Dificulta debug

**Para uso com Twilio:**
- Cold start de 30s pode causar **timeout no webhook** (Twilio espera resposta em 15s)
- Solução: usar fila assíncrona ou responder 200 imediatamente e processar depois

---

### 3.3 Docker

**Requisitos para o validador:**
- Docker Desktop instalado
- Clonar repositório ou receber arquivo docker-compose

**Vantagens:**
- Ambiente idêntico ao de desenvolvimento
- Isolado do sistema do validador
- Reproduzível e versionado

**Comando para validador:**
```bash
docker-compose up
```

---

## 4. Decisões

### ADR-004: Disponibilização para Validação Interna (Kika)

**Decisão**: Docker  
**Motivo**: Ambiente isolado, reproduzível, Kika tem capacidade técnica para rodar Docker  
**Data da decisão**: 2026-04-19  

**Fluxo**:
1. Dev conclui implementação
2. Dev faz push para branch `release`
3. Kika faz pull e executa `docker-compose up`
4. Kika valida contra critérios de aceite
5. Se aprovado → versão liberada para Rita
6. Se reprovado → retorna para correção com feedback

---

### ADR-005: Disponibilização para Validação com Cliente (Rita)

**Decisão**: GitHub Codespaces  
**Motivo**: Zero setup para Rita, ambiente cloud acessível via browser  
**Data da decisão**: 2026-04-19  

**Fluxo**:
1. Versão aprovada pela Kika
2. Dev prepara Codespace com a versão
3. Agenda sessão de teste com Rita
4. Durante a sessão, Codespace fica ativo
5. Rita testa via WhatsApp (Twilio Sandbox)
6. Após sessão, Codespace é pausado

**Observações**:
- Limite de 60h/mês no free tier
- Sessões de teste devem ser agendadas para otimizar uso
- Codespace dorme após 30min de inatividade

---

### ADR-006: Disponibilização em Nuvem sem Custo via Túnel Local

**Decisão**: Cloudflare Tunnel apontando para o `docker-compose` rodando na máquina do Beto.
**Motivo**: Permite que Kika e Rita acessem a aplicação via URL HTTPS pública sem custo de hospedagem e sem depender do Codespaces (ADR-005), enquanto não há orçamento para cloud (Railway/Render/VPS).
**Data da decisão**: 2026-04-28

**Limitação**: Aplicação só fica no ar enquanto a máquina do Beto estiver ligada com os containers e o `cloudflared` rodando.

**Passo-a-passo completo**: ver `deploy_tunel_local.md` (mesmo diretório).

**Quando substituir**: ao migrar para hospedagem paga (Railway/VPS), criar ADR-007 depreciando esta.

---

## 5. Artefatos Necessários

| Artefato | Responsável | Status |
|----------|-------------|--------|
| `Dockerfile` | Dev | Pendente |
| `docker-compose.yml` | Dev | Pendente |
| `.devcontainer/devcontainer.json` (Codespaces) | Dev | Pendente |
| Instruções de uso para Kika | Dev | Pendente |
| Instruções de uso para Rita | Dev | Pendente |

---

## 6. Histórico de Alterações

| Data | Versão | Alteração | Autor |
|------|--------|-----------|-------|
| 2026-04-19 | 1.0 | Criação do documento | Arquiteto de Sistemas |
