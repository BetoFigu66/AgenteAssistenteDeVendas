# Assistente de Vendas - Guia de Execução

Este guia explica como executar o projeto usando Docker.

---

## 1. Pré-requisitos: Instalar Docker

### Opção A: Windows (Docker Desktop)

1. **Baixe o Docker Desktop**  
   Acesse: https://www.docker.com/products/docker-desktop/  
   Clique em "Download Docker Desktop" e depois "Download for Windows"

2. **Execute o instalador**  
   - Siga as instruções na tela
   - Marque a opção "Use WSL 2 instead of Hyper-V" (recomendado)

3. **Reinicie o computador** quando solicitado

4. **Abra o Docker Desktop**  
   - Aguarde até aparecer "Docker Desktop is running" na barra de tarefas
   - Pode levar alguns minutos na primeira vez
   - Preencha os dados se solicitado, crie conta se necessário

5. **Verifique a instalação**  
   Abra o PowerShell ou Terminal e digite:
   ```powershell
   docker --version
   ```
   Deve aparecer algo como: `Docker version xx.x.x`

### Opção B: WSL (Windows Subsystem for Linux)

Se você já usa WSL com Ubuntu/Debian:

1. **Instale o Docker Desktop** (mesmos passos acima)  
   O Docker Desktop integra automaticamente com WSL 2

2. **Ou instale Docker direto no WSL** (sem Docker Desktop):
   ```bash
   # Atualize os pacotes
   sudo apt update && sudo apt upgrade -y

   # Instale dependências
   sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

   # Adicione a chave GPG do Docker
   curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

   # Adicione o repositório
   echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

   # Instale o Docker
   sudo apt update
   sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

   # Adicione seu usuário ao grupo docker (evita usar sudo)
   sudo usermod -aG docker $USER

   # Reinicie o WSL (feche e abra novamente)
   ```

3. **Verifique a instalação**:
   ```bash
   docker --version
   docker compose version
   ```

---

## 2. Executar o Projeto

### Passo 1: Abra o terminal na pasta do projeto

**Windows (PowerShell):**
```powershell
cd C:\<seu caminho>\AgenteAssistenteDeVendas
```

**WSL:**
```bash
cd <seu caminho>/AgenteAssistenteDeVendas
```

### Passo 2: Inicie os containers

```bash
docker-compose up --build
```

**O que vai acontecer:**
- Docker vai baixar as imagens necessárias (primeira vez demora mais)
- Vai subir o PostgreSQL
- Vai construir o backend Python
- Vai iniciar o frontend, backend e banco de dados

**Quando estiver pronto, você verá:**
```
backend_1   | INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Passo 3: Acesse no navegador

| Serviço | URL |
|---------|-----|
| **Frontend** | http://localhost:3000 |
| **Backend API** | http://localhost:8000 |
| **Documentação API** | http://localhost:8000/docs |
| **PostgreSQL** | localhost:5432 (user: `inforrel`, pass: `inforrel_dev`, db: `assistente_vendas`) |

### Passo 4: Parar o projeto

Pressione `Ctrl + C` no terminal onde o docker está rodando.

Ou em outro terminal:
```bash
docker-compose down
```

---

## 3. Comandos Úteis

| Comando | Descrição |
|---------|-----------|
| `docker-compose up` | Inicia os containers |
| `docker-compose up --build` | Reconstrói e inicia (use após mudanças no código) |
| `docker-compose down` | Para os containers |
| `docker-compose logs -f` | Mostra logs em tempo real |
| `docker ps` | Lista containers rodando |

---

## 4. Solução de Problemas

### "Docker daemon is not running"
- Abra o Docker Desktop e aguarde ele iniciar completamente

### "Port 8000 already in use"
- Outro programa está usando a porta. Feche-o ou altere a porta no `docker-compose.yml`

### "Permission denied" no WSL
- Execute: `sudo usermod -aG docker $USER`
- Feche e abra o WSL novamente

### Containers não iniciam
- Verifique se o Docker Desktop está rodando
- Tente: `docker-compose down` e depois `docker-compose up --build`

---

## 5. Executar sem Docker (alternativa)

Se preferir rodar o backend/frontend sem Docker, você ainda precisa do **PostgreSQL**:

```bash
# 1. Subir apenas o postgres via docker
docker-compose up -d postgres

# 2. Rodar o backend localmente
cd backend
python -m venv venv
source venv/bin/activate   # ou venv\Scripts\Activate.ps1 no Windows
pip install -r requirements.txt
alembic upgrade head
python main.py
```

O frontend precisa ser servido separadamente:
```bash
cd frontend
npm install
npm run dev
```
Acesse: http://localhost:5173

---

## 6. Migrations (Alembic)

O projeto usa **Alembic** para controle de versão do banco de dados.

### Comandos principais

```bash
cd backend

# Ver status das migrations
alembic current

# Aplicar todas as migrations pendentes
alembic upgrade head

# Reverter última migration
alembic downgrade -1

# Criar nova migration (após alterar models.py)
alembic revision --autogenerate -m "descricao da mudanca"
```

### Configuração do banco

O projeto usa **PostgreSQL 16** (rodando em container Docker).

Edite o arquivo `.env` conforme necessário:

```bash
# Via docker-compose (backend dentro do container)
DATABASE_URL=postgresql://inforrel:inforrel_dev@postgres:5432/assistente_vendas

# Backend rodando local, postgres no docker
DATABASE_URL=postgresql://inforrel:inforrel_dev@localhost:5432/assistente_vendas
```

---

## 7. Endpoints da API

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/webhook` | Recebe mensagens do Twilio WhatsApp |
| POST | `/api/mensagem` | Envia mensagem via interface web |
| GET | `/api/historico/{telefone}` | Retorna histórico de um telefone |
| GET | `/api/telefones` | Lista telefones com conversas |
| GET | `/health` | Health check |

### Exemplo: Enviar mensagem
```json
POST /api/mensagem
{
  "telefone": "+5511999999999",
  "mensagem": "Olá!"
}
```
