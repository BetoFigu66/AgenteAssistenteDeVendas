# Política de Branches e Fluxo de Trabalho

**Versão**: 1.0  
**Data**: 2026-04-20  
**Autor**: Arquiteto de Sistemas  
**Status**: Aprovado  

---

## 1. Branches de Ambiente

| Branch | Ambiente | Propósito | Deploy | Status |
|--------|----------|-----------|--------|--------|
| `main` | **Produção** | Código estável, validado | Automático | ✅ Ativo |
| `homolog` | **Homologação** | Validação com cliente (Rita) | Automático | ⏳ Pós-POC |
| `qa` | **QA** | Validação interna (Kika) | Automático | ⏳ Pós-POC |
| `develop` | **Desenvolvimento** | Integração de features | Automático | ✅ Ativo |

### Uso no POC

Durante o POC, utilizamos apenas:
- `main` → versão estável
- `develop` → trabalho em andamento
- `feature/*` → novas funcionalidades

As branches `qa` e `homolog` serão criadas quando sair do POC.

---

## 2. Fluxo de Trabalho

### POC (Atual)

```
feature/xxx ──► develop ──► main
                  │           │
                  ▼           ▼
               Dev env     Prod env
               (local)     (Rita/Kika)
```

### Pós-POC (Futuro)

```
feature/xxx ──► develop ──► qa ──► homolog ──► main
                  │          │        │          │
                  ▼          ▼        ▼          ▼
               Dev env    QA env   HML env    Prod env
               (local)    (Kika)   (Rita)    (Clientes)
```

---

## 3. Nomenclatura de Branches

### Branches de Feature

| Tipo | Padrão | Exemplo |
|------|--------|---------|
| Feature | `feature/<id>-<desc>` | `feature/REQ-008-integracao-twilio` |
| Bugfix | `bugfix/<id>-<desc>` | `bugfix/BUG-001-timeout-webhook` |
| Hotfix | `hotfix/<id>-<desc>` | `hotfix/HOT-001-corrige-crash-prod` |

### Regras

- Sempre criar a partir de `develop`
- Nome em **minúsculas**, separado por **hífen**
- Incluir **ID do requisito/bug** quando existir
- Descrição curta e objetiva (máx. 50 caracteres)

### Exemplos Válidos

```
feature/REQ-008-integracao-twilio
feature/REQ-003-envio-catalogo
bugfix/BUG-012-mensagem-duplicada
hotfix/HOT-001-corrige-timeout
```

### Exemplos Inválidos

```
Feature/REQ-008                    # Maiúscula
feature/integração_twilio          # Acento e underscore
minha-feature                      # Sem prefixo
feature/REQ-008-implementacao-da-integracao-com-twilio-para-whatsapp  # Muito longo
```

---

## 4. Política de Pull Requests

### Matriz de Aprovações

| De | Para | Aprovações | Quem aprova |
|----|------|------------|-------------|
| `feature/*` | `develop` | 0 (POC) | - |
| `bugfix/*` | `develop` | 0 (POC) | - |
| `develop` | `qa` | 1 | Dev ou Kika |
| `qa` | `homolog` | 1 | Kika |
| `homolog` | `main` | 1 | Beto |
| `hotfix/*` | `main` | 1 | Beto |

### Regras de PR

1. **Título descritivo**: `[REQ-008] Implementa webhook Twilio`
2. **Descrição** deve conter:
   - O que foi feito
   - Como testar
   - Checklist de validação (quando aplicável)
3. **Sem conflitos** com branch destino
4. **Testes passando** (quando houver CI configurado)

### Template de PR

```markdown
## Descrição
[Descreva o que foi implementado/corrigido]

## Tipo de mudança
- [ ] Feature (nova funcionalidade)
- [ ] Bugfix (correção de bug)
- [ ] Hotfix (correção urgente em produção)
- [ ] Refatoração (sem mudança de comportamento)
- [ ] Documentação

## Como testar
1. [Passo 1]
2. [Passo 2]
3. [Resultado esperado]

## Checklist
- [ ] Código segue os padrões do projeto
- [ ] Documentação atualizada (se aplicável)
- [ ] Testes adicionados/atualizados (se aplicável)

## Requisitos relacionados
- REQ-XXX
```

---

## 5. Proteção de Branches

### Configuração no GitHub

| Branch | Requer PR | Requer Aprovação | Bloqueia Push Direto |
|--------|-----------|------------------|---------------------|
| `main` | ✅ | ✅ (1) | ✅ |
| `homolog` | ✅ | ✅ (1) | ✅ |
| `qa` | ✅ | ❌ | ✅ |
| `develop` | ❌ (POC) | ❌ | ❌ (POC) |

### Como Configurar (GitHub)

1. Acesse: Settings → Branches → Add rule
2. Branch name pattern: `main`
3. Marque:
   - ✅ Require a pull request before merging
   - ✅ Require approvals (1)
   - ✅ Do not allow bypassing the above settings

---

## 6. Hotfix (Emergências)

Para correções urgentes em produção:

```
main ──► hotfix/HOT-xxx ──► main
              │
              └──► develop (merge back)
```

### Processo

1. Criar branch `hotfix/HOT-xxx` a partir de `main`
2. Implementar correção
3. Abrir PR para `main` (requer aprovação do Beto)
4. Após merge em `main`, fazer merge back em `develop`

---

## 7. Imagens Docker por Branch

| Branch | Tag da Imagem | Visibilidade |
|--------|---------------|--------------|
| `main` | `latest`, `vX.Y.Z` | Pública |
| `homolog` | `homolog` | Pública |
| `qa` | `qa` | Pública |
| `develop` | `develop` | Pública |

### Versionamento Semântico

- **Major** (X): Mudanças incompatíveis
- **Minor** (Y): Novas funcionalidades compatíveis
- **Patch** (Z): Correções de bugs

Exemplo: `v1.2.3`

---

## 8. Histórico de Alterações

| Data | Versão | Alteração | Autor |
|------|--------|-----------|-------|
| 2026-04-20 | 1.0 | Criação do documento | Arquiteto de Sistemas |
