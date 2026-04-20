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

## Histórico de Dúvidas

| Data | Quem | Dúvida | Comando/Solução |
|------|------|--------|-----------------|
| 2026-04-20 | Beto | Como ativar venv no Windows? | `venv\Scripts\Activate.ps1` |
| 2026-04-20 | Beto | Precisa de venv para frontend? | Não, Node.js usa `node_modules` |

---

*Atualize este arquivo sempre que surgir uma dúvida nova!*
