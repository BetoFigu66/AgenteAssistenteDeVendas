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

# Comparar 2 commits (ou branches, ou tags)
git diff <sha1> <sha2>
git diff <sha1> <sha2> -- caminho/do/arquivo   # só um arquivo
git diff --name-only <sha1> <sha2>             # só nomes de arquivos que mudaram
git diff --stat <sha1> <sha2>                  # resumo com +/- por arquivo
git diff main develop                          # comparar branches
git diff HEAD~1 HEAD                           # HEAD vs commit anterior

# Listar commits que estão em B mas não em A
git log <sha1>..<sha2> --oneline

# Ver o diff de um único commit
git show <sha>

# Comparar no GitHub via URL:
# https://github.com/<user>/<repo>/compare/<sha1>...<sha2>

# Ver conteúdo completo de um arquivo em um commit específico
git show <sha>:caminho/do/arquivo

# Histórico de commits que tocaram um arquivo
git log --oneline -- caminho/do/arquivo

# Histórico com o diff de cada commit no arquivo (-p = patch)
git log -p -- caminho/do/arquivo
```

**Dica VSCode/Windsurf:** botão direito no arquivo → `Open Timeline`. Lista todos os commits que tocaram aquele arquivo; `Ctrl+Click` em duas entradas compara as versões lado a lado.

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

### Embeddings / RAG (EMBEDDING_API_KEY)

O provider padrão é **OpenAI** (`text-embedding-3-small`, 1536 dimensões).
A mesma conta OpenAI usada eventualmente para o LLM serve aqui; a chave é a mesma.

**Como obter:**

1. Acesse https://platform.openai.com e faça login (ou crie conta).
2. No menu lateral, clique em **API keys**.
3. Clique em **+ Create new secret key**, dê um nome (ex: `inforrel-dev`) e copie a chave gerada — ela só aparece uma vez.
4. Adicione no seu `backend/.env`:

```env
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_API_KEY=sk-...sua_chave_aqui...
```

**Custo estimado (referência):** `text-embedding-3-small` custa US$ 0,02 por 1 milhão de tokens.
Uma ingestão inicial do catálogo completo da Inforrel fica na casa de centavos.
Buscas em produção também são baratas (cada pergunta = 1 chamada pequena).

**Fallback sem chave (desenvolvimento sem embeddings):**
Defina `RAG_ENABLED=false` no `.env` para desabilitar a RAG completamente.
O agente continua funcionando com templates e LLM, só não usa o catálogo vetorial.

```env
RAG_ENABLED=false
```

Erro de quota na API do OpenAI (insufficient_quota).
Entrei em https://platform.openai.com/settings/billing, pediu para criar uma organização e adicionar um metodo de pagamento.
(Signed in with betofigu@gmail.com)
Organization name: "BF Desenvolvimento de sistemas"
What best describes you?: "Data Scientist"

API key name: inforrel-dev
Project name: Inforrel
API keys belong to projects to help you manage usage limits, team access, and data security.
---

### RAG - inventario das fontes

```powershell
# Gera o inventario das fontes raw usadas pela RAG
python backend\scripts\inventariar_fontes_rag.py

# Gerar em outro caminho, se necessario
python backend\scripts\inventariar_fontes_rag.py --saida backend\data\rag\inventario_fontes.json
```

Saida padrao: `backend/data/rag/inventario_fontes.json`.

### RAG - pre-processamento das fontes

```powershell
# Gera documentos normalizados em JSONL a partir do inventario
python backend\scripts\preprocessar_conhecimento_rag.py

# Informar caminhos explicitamente, se necessario
python backend\scripts\preprocessar_conhecimento_rag.py --inventario backend\data\rag\inventario_fontes.json --saida backend\data\rag\documentos_normalizados.jsonl --resumo backend\data\rag\preprocessamento_resumo.json
```

Saidas padrao:

- `backend/data/rag/documentos_normalizados.jsonl`
- `backend/data/rag/preprocessamento_resumo.json`

### RAG - consolidacao e deduplicacao

```powershell
# Deduplica documentos normalizados e gera a base consolidada
python backend\scripts\consolidar_conhecimento_rag.py

# Ajustar o limiar para marcar documentos similares, se necessario
python backend\scripts\consolidar_conhecimento_rag.py --similaridade-minima 0.82
```

Saidas padrao:

- `backend/data/rag/documentos_consolidados.jsonl`
- `backend/data/rag/consolidacao_resumo.json`

### RAG - chunking

```powershell
# Gera chunks a partir dos documentos consolidados
python backend\scripts\gerar_chunks_rag.py

# Ajustar tamanhos, se necessario
python backend\scripts\gerar_chunks_rag.py --alvo-tokens 700 --max-tokens 900 --overlap-tokens 100
```

Saidas padrao:

- `backend/data/rag/chunks_conhecimento.jsonl`
- `backend/data/rag/chunking_resumo.json`

### RAG - banco pgvector

```powershell
# Recria apenas o container Postgres usando a imagem pgvector definida no docker-compose
# Preserva o volume postgres_data existente.
docker-compose up -d postgres

# Aplica migrations pelo container backend
docker exec agenteassistentedevendas-backend-1 alembic upgrade head

# Verifica revision atual
docker exec agenteassistentedevendas-backend-1 alembic current

# Confirma extensao vector
docker exec inforrel_postgres psql -U inforrel -d assistente_vendas -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"

# Inspeciona tabela da RAG
docker exec inforrel_postgres psql -U inforrel -d assistente_vendas -c "\d+ documentos_conhecimento"
```

---

### QA Engineer — checks automatizados e pre-commit

Os checks de qualidade ficam em `agentes/qa_engineer.py` (registry via `@registrar_check`). Ver diretriz D06 em `artefatos/implementador/diretrizes.md`.

**Setup (uma vez por clone):**
```powershell
pip install -r backend/requirements.txt
pre-commit install
```

**Rodar manualmente:**
```powershell
# Todos os checks registrados
python scripts/qa_check.py

# Somente os checks do escopo pre-commit (rápidos)
python scripts/qa_check.py --escopo pre-commit

# Um check específico
python scripts/qa_check.py --check gitkeep-redundantes

# Listar checks registrados
python scripts/qa_check.py --listar
```

**Severidade:** `error` bloqueia o commit; `warning` e `info` apenas avisam.

**Adicionar um novo check:** decorar uma função em `agentes/qa_engineer.py`:
```python
@registrar_check(id="meu-check", titulo="...", severidade="warning",
                 escopos=["sempre", "pre-commit"])
def _check_meu(raiz: Path) -> CheckResult:
    ...
```

**Rodar pre-commit sobre tudo (útil após mudanças grandes):**
```powershell
pre-commit run --all-files
```

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

## Cloudflare Tunnel (deploy zero-custo para Kika/Rita)

Documento completo: `artefatos/arquiteto_de_sistemas/deploy_tunel_local.md`

```powershell
# Instalar (uma vez)
winget install --id Cloudflare.cloudflared

# Subir a app
docker-compose up -d

# Quick Tunnel (URL temporária, sem login) - frontend
cloudflared tunnel --url http://localhost:3000

# Quick Tunnel para o backend (outro terminal)
cloudflared tunnel --url http://localhost:8000

# Named Tunnel (URL fixa, requer conta Cloudflare + domínio)
cloudflared tunnel login
cloudflared tunnel create inforrel-poc
cloudflared tunnel route dns inforrel-poc app.seudominio.com
cloudflared tunnel run inforrel-poc
```

---

## Histórico de Dúvidas

| Data | Quem | Dúvida | Comando/Solução |
|------|------|--------|-----------------|
| 2026-04-20 | Beto | Como ativar venv no Windows? | `venv\Scripts\Activate.ps1` |
| 2026-04-20 | Beto | Precisa de venv para frontend? | Não, Node.js usa `node_modules` |
| 2026-04-25 | Beto | Como quebrar a visualizacao de linhas longas no VSCode? | Ativar `editor.wordWrap: on` ou usar `Alt + Z` |

---

*Atualize este arquivo sempre que surgir uma dúvida nova!*
