# Comandos Úteis

Referência rápida de comandos para o projeto. Atualizado conforme dúvidas da equipe.

---

## Git

```bash
# Ver status dos arquivos
git status

# Baixar atualizações do repositório
git pull

# Adicionar arquivos e commitar
git add .
git commit -m "descrição do que foi feito"

# Enviar para o repositório
git push

# Criar nova branch de feature
git checkout -b feature/nome-da-feature

# Voltar para develop
git checkout develop

# Ver branches locais
git branch

# Ver histórico de commits (últimos 10)
git log -n 10 --oneline
```

---

## Docker

```bash
# Subir todos os containers
docker-compose up

# Subir em background (sem travar o terminal)
docker-compose up -d

# Parar containers
docker-compose down

# Ver containers rodando
docker ps

# Ver logs de um container
docker logs <nome-do-container>

# Rebuild após mudanças no Dockerfile
docker-compose up --build

# Limpar containers parados e imagens não usadas
docker system prune
```

---

## Backend (Python)

```bash
# Criar ambiente virtual (apenas primeira vez)
cd backend
python -m venv venv

# Ativar ambiente virtual (Windows PowerShell)
venv\Scripts\Activate.ps1

# Ativar ambiente virtual (Windows CMD)
venv\Scripts\activate.bat

# Ativar ambiente virtual (WSL/Linux/Mac)
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Rodar o backend (opção 1 - simples)
python main.py

# Rodar o backend (opção 2 - mais controle, reload automático)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Rodar migrations do banco
alembic upgrade head

# Criar nova migration
alembic revision --autogenerate -m "descricao"
```

---

## PostgreSQL

```bash
# Subir apenas o postgres (sem backend/frontend)
docker-compose up -d postgres

# Ver logs do postgres
docker-compose logs -f postgres

# Acessar shell do postgres (dentro do container)
docker exec -it inforrel_postgres psql -U inforrel -d assistente_vendas

# Parar e remover volume (APAGA TODOS OS DADOS)
docker-compose down -v
```

### LLM Provider (Groq)

1. Crie uma conta em https://console.groq.com
2. Gere uma API Key em https://console.groq.com/keys
3. Adicione no seu `backend/.env`:
```env
LLM_PROVIDER=groq
LLM_MODEL=llama-3.1-8b-instant
LLM_API_KEY=sua_chave_aqui
```

**Importante:** Nunca commitar `.env`. Está no `.gitignore`.

Para trocar de provider (ex: OpenAI, Gemini, Ollama), basta alterar `LLM_PROVIDER` e implementar a classe em `backend/services/llm/`.

---

### Conexão DBeaver / cliente externo

| Campo | Valor |
|-------|-------|
| Host | `localhost` |
| Porta | `5433` *(5432 interno do container, 5433 exposto para não conflitar com postgres local)* |
| Database | `assistente_vendas` |
| User | `inforrel` |
| Password | `inforrel_dev` |

---

## Frontend (Node.js)

```bash
# Instalar dependências (apenas primeira vez ou após pull)
cd frontend
npm install

# Rodar em desenvolvimento (hot reload automático)
npm run dev

# Build de produção
npm run build

# Preview do build
npm run preview

# Se o hot reload não funcionar, limpar cache:
# 1. Parar o servidor (Ctrl+C)
# 2. Deletar cache do Vite
Remove-Item -Recurse -Force node_modules/.vite
# 3. Rodar novamente
npm run dev
# 4. No navegador: Ctrl+Shift+R (force refresh)
```

---

## WSL (Windows Subsystem for Linux)

```bash
# Abrir WSL
wsl

# Ver distribuições instaladas
wsl --list --verbose

# Reiniciar WSL (PowerShell como Admin)
wsl --shutdown

# Acessar pasta do Windows no WSL
cd /mnt/c/Users/SeuUsuario/...
```

---

## PowerShell

```powershell
# Ver processos usando uma porta
netstat -ano | findstr :8000

# Matar processo por PID
taskkill /PID <numero> /F

# Limpar tela
cls

# Ver variáveis de ambiente
$env:PATH
```

---

## VSCode / WindSurf

```json
// Ativar quebra visual de linhas longas no editor
{
  "editor.wordWrap": "on"
}
```

Atalho rapido para alternar a quebra visual de linha: `Alt + Z`.

Tambem pode ser ativado pelo menu: `View` -> `Word Wrap`.

Observacao: isso altera apenas a visualizacao no editor, sem modificar o arquivo.

---

## Histórico de Dúvidas

| Data | Quem | Dúvida | Comando/Solução |
|------|------|--------|-----------------|
| 2026-04-20 | Beto | Como ativar venv no Windows? | `venv\Scripts\Activate.ps1` |
| 2026-04-20 | Beto | Precisa de venv para frontend? | Não, Node.js usa `node_modules` |
| 2026-04-25 | Beto | Como quebrar a visualizacao de linhas longas no VSCode? | Ativar `editor.wordWrap: on` ou usar `Alt + Z` |

---

*Atualize este arquivo sempre que surgir uma dúvida nova!*
