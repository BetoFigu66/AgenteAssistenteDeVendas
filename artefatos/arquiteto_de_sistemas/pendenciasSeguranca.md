# Pendências de Segurança — Análise de Exposição de Código

<!-- CLASSIFICACAO: ANDAMENTO -->

> **Agente:** [arquiteto]
> **Data:** 2026-05-22
> **Contexto:** Verificação de se o código-fonte fica exposto ao disponibilizar o sistema via `docker-compose up`.

---

## Resumo Executivo

O código-fonte **não é baixável diretamente da internet** ao rodar `docker-compose up`. Porém, existem múltiplos vetores de exposição indireta que devem ser mitigados antes de qualquer deploy em ambiente público.

---

## 1. Backend

### Dockerfile (`Dockerfile`)

```dockerfile
COPY backend/ .
```

- **Risco:** ALTO
- **Problema:** Todo o código-fonte `.py` do backend é copiado para **dentro da imagem Docker final**.
- **Impacto:** Se a imagem for empurrada para um registry (público ou privado comprometido), qualquer um com acesso pode extrair o código completo.

### docker-compose.yml (`backend` service)

```yaml
volumes:
  - ./backend:/app
```

- **Risco:** ALTO
- **Problema:** Bind mount dá ao container **acesso de leitura e escrita** nos arquivos do host.
- **Impacto:** Se o container for comprometido (via vulnerabilidade na aplicação ou em dependências), o atacante pode ler e modificar todo o código do host.

### Variável de ambiente

```yaml
environment:
  - DEBUG=true
```

- **Risco:** MÉDIO
- **Problema:** Em caso de erro 500, o FastAPI expõe **stack traces completos** com paths e trechos de código.
- **Impacto:** Revela estrutura de diretórios e lógica interna da aplicação.

---

## 2. Frontend

### Dockerfile (`frontend/Dockerfile`)

Multi-stage build usado corretamente:

```dockerfile
COPY --from=build /app/dist /usr/share/nginx/html
```

- **Risco da imagem final:** BAIXO — apenas arquivos buildados (`dist/`) ficam na imagem final.
- **Risco das camadas intermediárias:** MÉDIO — O stage `build` contém o código fonte React/TypeScript. Se a imagem for empurrada para um registry, as camadas intermediárias são empurradas junto e podem ser inspecionadas.

### docker-compose.yml (`frontend-dev` service)

```yaml
volumes:
  - ./frontend:/app
```

- **Risco:** ALTO (apenas no profile `dev`)
- **Problema:** Mesmo problema de bind mount do backend. O profile `dev` não deve ser usado em produção.

---

## 3. Banco de Dados

```yaml
ports:
  - "5433:5432"
```

- **Risco:** ALTO
- **Problema:** PostgreSQL exposto na porta 5433 do host.
- **Impacto:** Se a máquina tiver IP público e firewall aberto, qualquer um pode tentar conectar ao banco. Credenciais (`inforrel / inforrel_dev`) são fracas e conhecidas.

---

## 4. Tabela de Riscos

| Vetor | Código exposto? | Onde / Como | Severidade |
|-------|----------------|-------------|------------|
| API acessível de fora | ❌ Não | FastAPI não serve `.py` | — |
| Frontend acessível de fora | ❌ Não | Apenas bundle buildado | — |
| Acesso ao container backend | ✅ Sim | Todo `/app` (`.py`, configs, etc.) | 🔴 Alta |
| Acesso à imagem backend | ✅ Sim | `COPY backend/ .` está na imagem final | 🔴 Alta |
| Acesso à imagem frontend | ⚠️ Parcial | Camadas intermediárias têm código fonte | 🟡 Média |
| Container comprometido | ✅ Sim | Bind mount = acesso total ao host | 🔴 Alta |
| Stack trace em erro (DEBUG=true) | ⚠️ Parcial | Paths e trechos de código | 🟡 Média |
| Banco de dados exposto | ✅ Sim | Porta 5433 aberta | 🔴 Alta |

---

## 5. Recomendações

### Para desenvolvimento local
- Bind mounts são úteis para hot reload, mas o container pode modificar seus arquivos. **Mantenha backups e versionamento Git.**

### Para produção / ambiente público

1. **Remover bind mounts** do `docker-compose.yml` (backend e frontend-dev).
2. **Criar `.dockerignore`** na raiz e em `frontend/` para evitar copiar arquivos sensíveis (`.env`, `.git`, `__pycache__`, `node_modules`, `.venv`).
3. **Nunca usar `DEBUG=true`** em produção. Usar `DEBUG=false` ou omitir a variável.
4. **Não fazer `docker push`** das imagens sem verificar o conteúdo. Preferir builds locais ou CI/CD com registry privado.
5. **Não expor a porta do PostgreSQL** para o host. Remover `ports:` do serviço `postgres` — apenas os containers internos precisam acessá-lo.
6. **Usar secrets** (Docker Swarm / Kubernetes / Docker Secrets) para credenciais, nunca hardcoded no `docker-compose.yml`.
7. **Multi-stage build do frontend:** considerar adicionar `--target production` ou usar `docker buildx` com `--squash` para eliminar camadas intermediárias.

---

## 6. Checklist de Verificação Pré-Deploy

- [ ] Bind mounts removidos do `docker-compose.yml`
- [ ] `.dockerignore` criado e testado (`docker build` não copia arquivos desnecessários)
- [ ] `DEBUG=false` no backend
- [ ] Porta do PostgreSQL não exposta ao host
- [ ] Credenciais movidas para secrets
- [ ] Imagens não empurradas para registry público sem revisão
- [ ] Firewall / security group restrito (aplicar regra de least privilege)

---

## Referências

- `docker-compose.yml` → serviços `postgres`, `backend`, `frontend`, `frontend-dev`
- `Dockerfile` → backend
- `frontend/Dockerfile` → frontend (multi-stage)
