# REQ-014: Configuração em Runtime das Camadas de Conhecimento (RAG e Q&A)

**Versão**: 1.1
**Data**: 2026-06-06
**Autor**: Kika (Analista de Requisitos)
**Status**: Em Elaboração
**Prioridade**: Média

---

## 1. Identificação do Requisito

**ID**: REQ-014
**Tipo**: Funcional
**Categoria**: Configuração / Operação / Observabilidade
**Solicitante**: Necessidade do produto (ajuste fino do agente sem redeploy)

---

## 2. Descrição

O sistema deve oferecer um mecanismo para **consultar e alterar em tempo de execução** os parâmetros que governam as camadas de conhecimento do agente — RAG documental (REQ-003) e Q&A curada (REQ-013) — sem necessidade de reiniciar o backend ou alterar variáveis de ambiente. O objetivo é permitir **calibragem operacional** (ajuste de thresholds de similaridade, top-K, ligar/desligar camadas) durante validação, testes A/B simples e respostas a incidentes.

A configuração tem dois níveis:

- **Defaults estáticos** carregados de variáveis de ambiente (`backend/config.py` + `.env`) na inicialização do servidor.
- **Overrides em runtime** aplicados via API (`/api/config/rag`) e/ou painel administrativo, com **persistência configurável** (volátil no POC, persistente em versão futura).

Este requisito **formaliza** o que está parcialmente implementado nas Sprints 1-2 (`GET /api/config/rag`, `PATCH /api/config/rag`, settings em `config.py`) e **expande** o escopo para cobrir parâmetros faltantes (Q&A, toggles `enabled`, persistência).

---

## 3. Justificativa de Negócio

**Problema Atual**:
- Calibrar thresholds de similaridade exige editar `.env` e reiniciar o servidor — fluxo lento e disruptivo.
- Não existe canal único para inspecionar a configuração efetiva do agente em produção.
- Em incidentes (ex: RAG retornando lixo, Q&A com falsos positivos), só é possível desabilitar uma camada via redeploy.
- Cobertura atual do endpoint é parcial: `PATCH /api/config/rag` só altera `rag_score_minimo` e `rag_top_k`; parâmetros de Q&A e toggles `enabled` ainda exigem reinício.

**Benefício Esperado**:
- **Ajuste fino sem downtime**: calibrar thresholds e top-K em produção observando métricas reais.
- **Resposta rápida a incidentes**: desligar uma camada com 1 clique enquanto o time corrige a causa-raiz.
- **Experimentação controlada**: comparar comportamento do agente com diferentes thresholds antes de fixar valor padrão.
- **Inspeção operacional**: ver qual a configuração efetiva do agente sem precisar SSH no servidor ou ler logs.

---

## 4. Critérios de Aceite

### 4.1 Parâmetros Configuráveis

- [ ] **REQ-014.1 — Parâmetros mínimos da camada RAG** (alinhado a REQ-003): O endpoint deve permitir consultar e atualizar:
  - `rag_enabled` (bool) — liga/desliga a camada RAG documental globalmente
  - `rag_score_minimo` (float, 0.0-1.0) — threshold mínimo de similaridade para um chunk ser usado
  - `rag_top_k` (int, ≥1) — quantos chunks são recuperados por busca

- [ ] **REQ-014.2 — Parâmetros mínimos da camada Q&A** (alinhado a REQ-013): O endpoint deve permitir consultar e atualizar:
  - `qa_enabled` (bool) — liga/desliga a camada Q&A curada globalmente (REQ-013.13)
  - `qa_score_minimo` (float, 0.0-1.0) — threshold mínimo de similaridade para um par ser usado (REQ-013.10)
  - `qa_top_k` (int, ≥1) — quantos pares são recuperados por busca
  - `qa_apenas_aprovados` (bool) — se `true`, apenas pares com `aprovado=true` participam da busca (default: `true`)

- [ ] **REQ-014.2A — Parâmetros do classificador (REQ-002.1A)**: Limiares de confiança usados para derivar `confianca_nivel` e decidir fallback condicional. Devem ser consultáveis e alteráveis em runtime, com os mesmos critérios de validação da REQ-014.3:
  - `classificador_conf_alta_min` (float, 0.0-1.0) — limiar mínimo para nível **alta** (default: `0.70`)
  - `classificador_conf_baixa_max` (float, 0.0-1.0) — limiar máximo para nível **baixa**; valores abaixo disso (e até `classificador_conf_alta_min`) formam a zona **media** (default: `0.40`)

  **Persistência no POC**: tabela `parametros` (`nome`, `valor`, `descricao`) no Postgres, lida via serviço de configuração (`ParametroService`). Seed inicial na migration Alembic. Integração com `GET/PATCH /api/config/rag` (ou endpoint dedicado) pode ser incremental — o mínimo aceito no POC é leitura/escrita via banco com efeito na próxima mensagem processada.

- [ ] **REQ-014.2B — Parâmetros de zona cinza Q&A** (busca híbrida full-text + embedding): thresholds usados pelo `QAService` para decidir responder direto, desambiguar ou descartar:
  - `qa_fulltext_responde_min`, `qa_fulltext_desambigua_min`
  - `qa_embedding_responde_min`, `qa_embedding_desambigua_min`

  Mesma persistência da REQ-014.2A (tabela `parametros`). Defaults conservadores definidos no seed da migration.

- [ ] **REQ-014.3 — Validação de valores**: Toda alteração deve validar:
  - `*_score_minimo`: valor entre `0.0` e `1.0` (inclusive)
  - `*_top_k`: valor inteiro `≥ 1`
  - Tipos coerentes (bool, float, int)
  - Resposta de erro `422` com mensagem clara em caso de violação

- [ ] **REQ-014.4 — Atualização parcial**: O endpoint deve aceitar atualização **parcial** (apenas os campos enviados são alterados; campos omitidos permanecem inalterados). Atualmente já suportado para RAG; estender para Q&A.

### 4.2 Endpoints e Acesso

- [ ] **REQ-014.5 — Consulta da configuração efetiva**: `GET /api/config/rag` (mantido por compatibilidade — em versão futura pode ser renomeado para `/api/config/conhecimento`) deve retornar **todos** os parâmetros da REQ-014.1 e REQ-014.2 em uma única chamada, com os valores **efetivos** em runtime (override aplicado quando houver, default caso contrário).

- [ ] **REQ-014.6 — Atualização**: `PATCH /api/config/rag` deve aceitar atualização parcial dos parâmetros listados em REQ-014.1 e REQ-014.2 (corrigindo gap atual em que apenas RAG é alterável).

- [ ] **REQ-014.7 — Restauração de defaults**: O sistema deve oferecer endpoint/ação para **resetar** a configuração aos defaults estáticos (variáveis de ambiente). Pode ser:
  - `POST /api/config/rag/reset` (zera todos os overrides)
  - Ou atualização explícita campo a campo com `null` indicando "voltar ao default"

  Implementação fica a critério técnico, mas a operação deve ser possível sem reiniciar o servidor.

- [ ] **REQ-014.8 — Autorização**: Em versão pós-POC, alterações na configuração devem ser restritas a usuário com perfil de **administrador** (depende de evolução do REQ-010.1/.2). No POC, com usuário único, sem restrição adicional além da autenticação básica.

### 4.3 Persistência e Auditoria

- [ ] **REQ-014.9 — Persistência da configuração runtime**: Os overrides aplicados em runtime devem ser **persistentes** entre reinícios do servidor. No POC, a persistência pode ser:
  - **Mínimo aceito**: armazenamento em arquivo JSON ou tabela dedicada no Postgres (`configuracao_runtime`)
  - **Não aceito**: persistência apenas em memória (estado atual)

  Ao iniciar, o servidor carrega defaults de env e sobrescreve com overrides persistidos, se houver.

- [ ] **REQ-014.10 — Histórico de alterações**: Toda alteração via `PATCH` deve gerar um evento auditável (alinhado a REQ-005) com:
  - Timestamp
  - Usuário que aplicou a alteração (REQ-010.2)
  - Diff entre valor anterior e valor novo, por campo

  No POC, o histórico pode ser simples (tabela `historico_configuracao` com campos: `timestamp`, `autor`, `campo`, `valor_anterior`, `valor_novo`).

- [ ] **REQ-014.11 — Imutabilidade do histórico**: Eventos de alteração não devem ser excluídos. Permitem reconstruir, em qualquer momento, **qual era a configuração efetiva do agente** em uma data X — útil para diagnóstico de incidentes e análise post-mortem.

### 4.4 Painel e Visibilidade

- [ ] **REQ-014.12 — Tela de configuração no painel**: O painel administrativo (REQ-010) deve oferecer tela dedicada para visualizar e editar todos os parâmetros da REQ-014.1 e REQ-014.2, com:
  - Indicação clara de quais valores são default vs. override em runtime
  - Botão para restaurar default por campo (REQ-014.7)
  - Listagem do histórico de alterações recentes (últimas 20, expansível)
  - Confirmação explícita antes de salvar mudanças sensíveis (toggles `*_enabled`)

- [ ] **REQ-014.13 — Indicação visual de camada desabilitada**: Quando `rag_enabled=false` ou `qa_enabled=false`, o painel deve sinalizar visivelmente em telas relacionadas (`AcompanhamentoPage`, `QABasePage`) que a camada está desligada. Evita confusão ao diagnosticar comportamento do agente.

### 4.5 Integração com Outros Módulos

- [ ] **REQ-014.14 — Aplicação imediata**: Mudanças aplicadas via `PATCH` devem ser refletidas na próxima requisição processada pelo agente, **sem necessidade de reinício**. Isso já funciona parcialmente em `RetrievalService` via override de `_score_minimo_padrao` e `_top_k_padrao`; estender para `QAService` e para os toggles `enabled`.

- [ ] **REQ-014.15 — Toggle de camada respeitado em todo o fluxo**: Quando uma camada está desabilitada via runtime, todos os caminhos do `ProcessadorMensagem` que a utilizariam devem **bypassar** a camada de forma limpa, sem erros e sem fallback silencioso para comportamento divergente. Logs devem registrar que a camada estava desabilitada (já existe parcialmente via `DebugLogger`).

### 4.6 Requisitos Não-Funcionais

- [ ] **REQ-014.16 — Tempo de resposta**: `GET /api/config/rag` e `PATCH /api/config/rag` devem responder em < 500ms.

- [ ] **REQ-014.17 — Atomicidade**: Em `PATCH` com múltiplos campos, ou todos são aplicados ou nenhum é (transação). Falha de validação em um campo não pode deixar outros aplicados.

- [ ] **REQ-014.18 — Compatibilidade retroativa do endpoint**: A migração para incluir parâmetros de Q&A não pode quebrar consumidores que já usam `GET /api/config/rag`. Manter os campos atuais (`rag_enabled`, `rag_score_minimo`, `rag_top_k`) e adicionar novos.

---

## 5. Modelo de Dados (alto nível)

> **Nota:** os defaults já existem em `backend/config.py:34-44`. O que **falta** é uma tabela/arquivo de persistência dos overrides e (opcionalmente) uma tabela de histórico.

### 5.1 Configuração efetiva (lógica)

| Campo | Tipo | Default (env) | Faixa |
|-------|------|---------------|-------|
| `rag_enabled` | bool | `true` | true/false |
| `rag_score_minimo` | float | `0.70` | 0.0 - 1.0 |
| `rag_top_k` | int | `4` | ≥ 1 |
| `qa_enabled` | bool | `true` | true/false |
| `qa_score_minimo` | float | `0.80` | 0.0 - 1.0 |
| `qa_top_k` | int | `3` | ≥ 1 |
| `qa_apenas_aprovados` | bool | `true` | true/false |
| `classificador_conf_alta_min` | float | `0.70` | 0.0 - 1.0 |
| `classificador_conf_baixa_max` | float | `0.40` | 0.0 - 1.0 |
| `qa_fulltext_responde_min` | float | `0.30` | 0.0 - 1.0 |
| `qa_fulltext_desambigua_min` | float | `0.12` | 0.0 - 1.0 |
| `qa_embedding_responde_min` | float | `0.80` | 0.0 - 1.0 |
| `qa_embedding_desambigua_min` | float | `0.65` | 0.0 - 1.0 |

### 5.2 Tabela `parametros` (implementada no POC)

| Campo | Tipo | Notas |
|-------|------|-------|
| `nome` | string | PK lógica; chave do parâmetro (ex: `classificador_conf_alta_min`) |
| `valor` | text | Valor serializado como string; cast na leitura (int/float/bool) |
| `descricao` | text | Documentação operacional |
| `updated_at` | datetime | Última alteração |

> **Nota:** REQ-014.9 previa `configuracao_runtime`; no POC Sprint 02 a persistência efetiva usa `parametros`. Unificação ou migração para um único modelo fica como evolução futura.

### 5.3 Tabela `configuracao_runtime` (sugerida — evolução)

| Campo | Tipo | Notas |
|-------|------|-------|
| `chave` | string | PK; nome do parâmetro (ex: `rag_score_minimo`) |
| `valor` | jsonb | Valor sobrescrito (qualquer tipo serializável) |
| `atualizado_em` | datetime | Última alteração |
| `atualizado_por` | string | Usuário responsável |

### 5.4 Tabela `historico_configuracao` (sugerida)

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int | PK auto |
| `chave` | string | Parâmetro alterado |
| `valor_anterior` | jsonb | Antes da alteração |
| `valor_novo` | jsonb | Depois da alteração |
| `autor` | string | Quem alterou |
| `timestamp` | datetime | Quando |

---

## 6. Fluxos (alto nível)

### 6.1 Inicialização do servidor

```
1) Carrega defaults de variáveis de ambiente (backend/config.py)
2) Lê tabela `configuracao_runtime`; aplica overrides sobre os defaults
3) Inicializa RetrievalService e QAService com os valores efetivos
4) Servidor está pronto
```

### 6.2 Alteração via PATCH

```
1) Usuário envia PATCH /api/config/rag {qa_score_minimo: 0.85}
2) Backend valida (REQ-014.3)
3) Em transação:
   a) Persiste override em `configuracao_runtime`
   b) Atualiza in-memory state do QAService
   c) Registra evento em `historico_configuracao` (REQ-014.10)
4) Retorna configuração efetiva atualizada
5) Próxima mensagem processada já usa o novo threshold
```

### 6.3 Reset ao default

```
1) Usuário envia POST /api/config/rag/reset (ou PATCH com null nos campos)
2) Backend remove o(s) override(s) de `configuracao_runtime`
3) RetrievalService e QAService voltam a usar valores de env
4) Evento registrado em `historico_configuracao`
```

---

## 7. Limitações Aceitas no POC

- [ ] Sem tela de configuração polida (REQ-014.12) — pode ser mínima (formulário simples).
- [ ] Sem confirmação multi-step para mudanças sensíveis — apenas botão de save.
- [ ] Histórico (REQ-014.10) limitado a últimas N entradas; sem busca avançada.
- [ ] Sem export/import de configuração (útil para replicar entre ambientes).
- [ ] Sem versionamento nomeado (ex: "configuração de 10/06"; útil para rollback rápido).
- [ ] Toggles `*_enabled` aplicados imediatamente; sem flag "modo de manutenção" mais elaborado.
- [ ] Sem A/B testing automatizado entre configurações.

---

## 8. Dependências

### 8.1 Dependências Técnicas
- REQ-003 — RAG documental (parâmetros consumidos)
- REQ-013 — Q&A curados (parâmetros consumidos)
- REQ-005 — auditoria (histórico de alterações)
- REQ-010 — painel administrativo (tela de configuração)
- Settings em `backend/config.py` (`RAG_ENABLED`, `QA_ENABLED`, etc.) já existentes
- Endpoints `GET/PATCH /api/config/rag` parcialmente implementados em `backend/main.py:951-994`

### 8.2 Dependências de Negócio
- Definir quem pode alterar configuração (papel admin) — formal pós-POC
- Definir cadência de revisão dos thresholds (sugestão: revisão mensal)

---

## 9. Restrições e Limitações

- Configuração runtime **não substitui** o `.env` — é um **override**. Reset sempre traz de volta o valor de env.
- Mudanças em runtime **não persistem código** — para fixar um valor permanentemente, atualizar `.env`/`config.py` e fazer deploy. Runtime é para calibragem operacional, não para "esconder" decisões arquiteturais.
- Toggles `*_enabled` em produção só devem ser usados em incidentes ou validação curta — desligar a camada por dias é antipattern (vira "deploy esquecido").

---

## 10. Critérios de Sucesso

### 10.1 Métricas
- Tempo médio de aplicação de uma mudança de threshold: < 1 minuto (do PATCH ao próximo processamento usar o novo valor).
- Cobertura de auditoria: 100% das alterações via `PATCH` registradas em `historico_configuracao`.
- Recuperação correta após reinício: 100% dos overrides aplicados antes do reinício efetivos após o reinício.

### 10.2 Condições de Aceite Final
- Todas as configurações da §5.1 são consultáveis via `GET /api/config/rag` em uma única chamada.
- Todas as configurações da §5.1 são alteráveis via `PATCH /api/config/rag` (correção do gap atual de Q&A e toggles).
- Mudanças persistem entre reinícios do servidor.
- Histórico de alterações é consultável (mínimo: API; ideal: painel).
- Reset ao default funciona sem reiniciar o servidor.

---

## 11. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Configuração mal calibrada degrada qualidade do agente | Alta | Alto | Histórico (REQ-014.10) permite rollback rápido; revisão periódica |
| Toggle `enabled=false` esquecido em produção | Média | Alto | Indicação visual no painel (REQ-014.13); alerta automático após N dias desabilitado (futuro) |
| Conflito entre múltiplos admins editando ao mesmo tempo | Baixa (POC: usuário único) | Médio | Optimistic locking ou last-write-wins com histórico |
| Persistência corrompida → servidor falha ao iniciar | Baixa | Alto | Tolerância a falha de leitura: se override não puder ser aplicado, log de warning + uso do default; healthcheck reporta inconsistência |
| Mudanças runtime mascaram bugs de configuração no `.env` | Média | Baixo | Indicação clara no painel de "default vs. override" (REQ-014.12); reset periódico recomendado em ambientes de teste |

---

## 12. Estimativas

> **Nota:** parte significativa já está implementada. As estimativas abaixo cobrem **gaps** entre o estado atual e os critérios de aceite deste REQ.

| Atividade | Horas |
|-----------|-------|
| Estender `GET /api/config/rag` para incluir parâmetros de Q&A (REQ-014.5) | 2h |
| Estender `PATCH /api/config/rag` para aceitar parâmetros de Q&A e toggles (REQ-014.6) | 4h |
| Tabela `configuracao_runtime` + carregamento na inicialização (REQ-014.9) | 5h |
| Tabela `historico_configuracao` + registro automático em PATCH (REQ-014.10) | 4h |
| Endpoint/ação de reset ao default (REQ-014.7) | 2h |
| Tela de configuração no painel (REQ-014.12) — formulário + listagem do histórico | 6h |
| Indicação visual de camada desabilitada (REQ-014.13) | 2h |
| Garantir aplicação imediata em `QAService` (REQ-014.14) — verificar o que falta | 3h |
| Testes (validação, persistência, reinício, reset) | 5h |
| **Total** | **33h** |

---

## 13. Histórico de Alterações

| Data | Versão | Alteração | Autor |
|------|--------|-----------|-------|
| 18/05/2026 | 1.0 | Criação inicial do requisito formalizando o mecanismo de configuração runtime das camadas de conhecimento (RAG e Q&A). Endpoints `GET/PATCH /api/config/rag` e settings em `backend/config.py` parcialmente implementados nas Sprints 1-2; este REQ expande para cobrir parâmetros de Q&A, toggles `enabled`, persistência entre reinícios e auditoria de alterações. | Kika |
| 06/06/2026 | 1.1 | REQ-014.2A (limiares do classificador REQ-002.1A) e REQ-014.2B (zona cinza Q&A); tabela `parametros` documentada como persistência efetiva no POC; defaults de seed alinhados à migration `2026060601`. | Beto |

---

## 14. Aprovações

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| Analista de Requisitos | Kika | 18/05/2026 | [ ] |
| Cliente (Inforrel) | Rita | ____/____/____ | [ ] |
| Líder Técnico | Beto | ____/____/____ | [ ] |
