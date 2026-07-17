# Cenários de Teste Manual — Sprint 2

<!-- CLASSIFICACAO: SISTEMA-DEV -->
<!-- CLASSIFICACAO: HISTORICO -->

**Data:** 2026-05-27
**Autor:** `[qa]` (Cascade)
**Escopo:** validar funcionalmente os subitens com status ✅ ou 🟡 conforme `artefatos/gerente_de_projetos/cobertura_reqs_sprint02.md`.
**Modo de execução:** manual, executado pela usuária.
**REQs 🔴 (REQ-007, REQ-009) e subitens 🔴 isolados:** fora deste plano — não há código a testar.

---

## 0. Convenções

### Identificação dos cenários

`CT-<REQ>-<NN>` — ex.: `CT-001-03` é o terceiro cenário do REQ-001.

### Rastreabilidade

Cada cenário cita o(s) subitem(ns) do REQ que valida, no formato `REQ-XXX.Y` (mesma numeração da `§2` de `cobertura_reqs_sprint02.md`).

### Status do teste

Marque ao final de cada cenário:

- `[ ]` não executado
- `[OK]` passou
- `[FAIL]` falhou — registrar evidência (print, log, mensagem) em `artefatos/qa/evidencias/CT-XXX-NN/`
- `[N/A]` impossível executar no momento (anotar motivo)

### Severidade quando falha

| Severidade | Critério |
|------------|----------|
| 🔴 Crítica | Bloqueia o fluxo principal do REQ; sistema fica inutilizável |
| 🟡 Alta | Funcionalidade essencial degradada, mas há workaround |
| 🟢 Média | Comportamento incorreto sem impacto funcional grave |
| ⚪ Baixa | Cosmético / mensagem / UX |

---

### Meios de verificação permitidos

Todo cenário verifica resultados **somente** através de:

- **Interface web** (`AcompanhamentoPage`, `ReportsPage`, `QABasePage`, modal de raciocínio)
- **Swagger UI** ou cliente HTTP (`http://localhost:8000/docs`) para chamadas de API
- **Consulta SQL ao PostgreSQL** (ver §1.1 para queries prontas)

Inspeção de código-fonte, logs do servidor ou variáveis em runtime **não** são meios válidos para concluir um cenário.

---

## 1. Pré-requisitos do ambiente

Antes de iniciar:

1. **Backend** rodando (`docker-compose up` ou `python backend/main.py`) em `http://localhost:8000`.
2. **Frontend** acessível em `http://localhost:3000` (ou `5173` se via `npm run dev`).
3. **Banco** com seeds básicos:
   - ao menos 1 `TipoProduto` (catraca, relógio)
   - ao menos 1 `Produto` com chunks ingeridos no RAG
   - ao menos 1 par Q&A aprovado (`ParQA.aprovado=true, ativo=true`)
4. **Swagger** acessível em `http://localhost:8000/docs` (usado em vários cenários de API).
5. **Telefone de teste:** `5511999990000` (sufixo livre por cenário para evitar colisão).
6. **CNPJ de teste válido:** consultar um real, ex.: `00.000.000/0001-91` (Banco do Brasil).
7. **Ferramenta para POST:** Swagger UI ou Postman.

---

### 1.1 Queries SQL úteis

Conexão sugerida (psql ou DBeaver):

```
host=localhost port=5432 dbname=assistente_vendas user=inforrel password=inforrel_dev
```

#### Verificar última mensagem e seu raciocínio

```sql
SELECT m.id, m.origem, m.conteudo, m.criado_em,
       p.intencao_classificada, p.confianca, p.contexto_recuperado, p.resposta_gerada
FROM mensagens m
LEFT JOIN processamento_mensagem p ON p.mensagem_id = m.id
WHERE m.contato_id = (SELECT id FROM contatos WHERE telefone = '5511999990001')
ORDER BY m.criado_em DESC
LIMIT 5;
```

#### Verificar empresa cacheada por CNPJ

```sql
SELECT id, cnpj, razao_social, situacao FROM empresas WHERE cnpj = '00000000000191';
SELECT * FROM atividades_empresa WHERE empresa_id = <id>;
SELECT * FROM socios_empresa     WHERE empresa_id = <id>;
```

#### Listar mensagens pendentes de aprovação

```sql
SELECT id, conteudo, pendente_aprovacao, aprovado, reprovado, aprovador_id, reprovador_id
FROM mensagens
WHERE pendente_aprovacao = true
ORDER BY criado_em DESC;
```

#### Listar pares Q&A (aprovados x rascunhos)

```sql
SELECT id, pergunta, aprovado, ativo, (embedding IS NOT NULL) AS tem_embedding, criado_em
FROM pares_qa
ORDER BY criado_em DESC;
```

#### Conferir modos de operação distintos em uso

```sql
SELECT modo_operacao, COUNT(*) FROM negociacoes GROUP BY modo_operacao;
```

#### Estado dos campos de uma negociação

```sql
SELECT campo, valor, origem, status FROM negociacao_infos WHERE negociacao_id = <id>;
```

#### Reports de problema por status

```sql
SELECT status, COUNT(*) FROM reports_problema GROUP BY status;
```

> **Nota:** os nomes exatos de coluna podem variar conforme migration. Se uma query falhar, ajuste pelo schema atual em `backend/models.py` ou `\d <tabela>` no psql.

---

## 2. Cenários por REQ

### REQ-001 — Integração Receita Federal

#### CT-001-01 — Reconhecer CNPJ em mensagem livre
**Cobre:** REQ-001.1, REQ-001.2
**Pré-condição:** backend rodando, nenhuma empresa pré-cadastrada para o CNPJ.
**Passos:**
1. Via Swagger `POST /webhook` envie `From=whatsapp:+5511999990001`, `Body="Bom dia, meu CNPJ é 00.000.000/0001-91"`.
2. Consultar `GET /api/historico/5511999990001`.
**Resultado esperado:** mensagem registrada; classificador identifica entidade `cnpj` com valor `00000000000191` no `ProcessamentoMensagem` daquela mensagem.
**Status:** [ ]

#### CT-001-02 — Consulta ReceitaWS e persiste empresa
**Cobre:** REQ-001.3, REQ-001.7
**Pré-condição:** internet liberada para `receitaws.com.br`.
**Passos:**
1. Repetir CT-001-01 com CNPJ ainda não cadastrado.
2. `GET /api/empresas?cnpj=00000000000191`.
**Resultado esperado:** retorna razão social, situação, endereço, ao menos 1 CNAE e ao menos 1 sócio populados nas tabelas `empresas`, `atividades_empresa`, `socios_empresa`.
**Status:** [ ]

#### CT-001-03 — CNPJ inválido (formato errado)
**Cobre:** REQ-001.2
**Passos:**
1. Enviar `Body="meu CNPJ é 123"` via webhook.
**Resultado esperado:** entidade `cnpj` **não** extraída; não há consulta à ReceitaWS; sem registro em `empresas`.
**Status:** [ ]

#### CT-001-04 — Empresa já cacheada (reuso)
**Cobre:** REQ-001.7, REQ-002.10
**Pré-condição:** CT-001-02 executado com sucesso.
**Passos:**
1. Repetir o mesmo CNPJ via webhook em outro telefone (`5511999990002`).
**Resultado esperado:** empresa **não** é recriada (mesmo `empresa_id`); contato novo é associado.
**Status:** [ ]

#### CT-001-05 — Disponibilização para orçamento
**Cobre:** REQ-001.5
**Pré-condição:** CT-001-02 OK.
**Passos:**
1. Criar negociação manualmente associada ao contato/empresa (via Swagger).
2. `GET /api/negociacoes/{id}` e checar campo empresa.
**Resultado esperado:** `Negociacao` tem `contato_id` ligado à empresa correta; `Orcamento` pode ser criado e expõe `empresa` via `contato`.
**Status:** [ ]

---

### REQ-002 — Fluxo conversacional guiado

#### CT-002-01 — Classificador identifica intenção `saudacao`
**Cobre:** REQ-002.1
**Passos:**
1. Enviar `Body="Oi, bom dia!"`.
**Resultado esperado:** `ProcessamentoMensagem.intencao_classificada=saudacao` (verificar em `AcompanhamentoPage` > modal de raciocínio, ou via `GET /api/mensagens/{id}/raciocinio`).
**Status:** [ ]

#### CT-002-02 — Classificador identifica `perguntar_preco`
**Cobre:** REQ-002.1
**Passos:**
1. `Body="quanto custa a catraca?"`.
**Resultado esperado:** intenção `perguntar_preco`; RAG é acionado (ver REQ-003).
**Status:** [ ]

#### CT-002-03 — Extração de quantidade e tipo de produto
**Cobre:** REQ-002.2, REQ-002.3A
**Passos:**
1. `Body="Preciso de 5 catracas para minha empresa"`.
**Resultado esperado:** entidades extraídas: `quantidade=5`, `tipo_produto=catraca`; `NegociacaoInfo` correspondente criado com `OrigemInfo.USER`.
**Status:** [ ]

#### CT-002-04 — Extração de email
**Cobre:** REQ-002.2
**Passos:**
1. `Body="meu email é teste@empresa.com"`.
**Resultado esperado:** entidade `email` populada no `ProcessamentoMensagem`.
**Status:** [ ]

#### CT-002-05 — Tipo de produto não suportado
**Cobre:** REQ-002.3A (limitação conhecida)
**Passos:**
1. `Body="Quero uma câmera de segurança"`.
**Resultado esperado:** `tipo_produto` **não** é classificado como `catraca` nem `relogio_ponto` (esperado: nenhum ou `outro`). Documentar a saída atual — pode virar bug se classificador "chutar".
**Status:** [ ]

#### CT-002-06 — Estado de campos pendentes
**Cobre:** REQ-002.3
**Pré-condição:** negociação iniciada com CNPJ mas sem quantidade.
**Passos:**
1. `GET /api/negociacoes/{id}/infos`.
**Resultado esperado:** lista mostra campos com status `capturado` (CNPJ) e `pendente` (quantidade, etc.).
**Status:** [ ]

#### CT-002-07 — Roteamento para RAG durante qualificação
**Cobre:** REQ-002.17, REQ-003.2
**Passos:**
1. Em conversa com qualificação parcial, enviar `Body="qual o prazo de entrega?"`.
**Resultado esperado:** RAG é consultado; resposta gerada com trechos retornados de `DocumentoConhecimento`; auditoria registrada em `ProcessamentoMensagem.contexto_recuperado`.
**Status:** [ ]

---

### REQ-003 — RAG / respostas automáticas

#### CT-003-01 — Recuperação retorna chunks relevantes
**Cobre:** REQ-003.2
**Passos:**
1. Via Swagger, `POST /api/rag/buscar` com `pergunta="catraca biométrica"`, `top_k=3`.
**Resultado esperado:** retorna até 3 chunks com `score` ≥ `rag_score_minimo`; cada chunk com `produto_id`, `texto`, `score`.
**Status:** [ ]

#### CT-003-02 — Geração com referências
**Cobre:** REQ-003.3, REQ-003.5
**Passos:**
1. `POST /webhook` com `Body="me fala sobre a catraca X"` (ajustar X conforme seed).
2. `GET /api/mensagens/{id}/raciocinio` da resposta gerada.
**Resultado esperado:** resposta tem trechos referenciados; `ProcessamentoMensagem` registra pergunta, trechos, resposta e classificação.
**Status:** [ ]

#### CT-003-03 — Score mínimo filtra ruído
**Cobre:** REQ-003.2, REQ-014
**Passos:**
1. `PATCH /api/config/rag` com `rag_score_minimo=0.95`.
2. Buscar pergunta genérica (`"oi"`).
**Resultado esperado:** retorna lista vazia (ou só itens com score muito alto). Restaurar score original ao fim.
**Status:** [ ]

#### CT-003-04 — Top_k limita resultados
**Cobre:** REQ-003.2
**Passos:**
1. `PATCH /api/config/rag` com `rag_top_k=1`.
2. Repetir CT-003-01.
**Resultado esperado:** exatamente 1 chunk retornado.
**Status:** [ ]

#### CT-003-05 — Par Q&A aprovado precede RAG documental
**Cobre:** REQ-003 ↔ REQ-013
**Pré-condição:** ao menos 1 `ParQA` aprovado cuja pergunta é parecida com `"qual o horário de atendimento?"`.
**Passos:**
1. Enviar `Body="qual o horário de atendimento?"` via webhook.
**Resultado esperado:** resposta vem do par Q&A (não do RAG documental); auditoria registra a fonte.
**Status:** [ ]

---

### REQ-004 — Escalonamento para humano

#### CT-004-01 — Detecção de intenção `escalar_humano`
**Cobre:** REQ-004.1, REQ-004.6
**Passos:**
1. `Body="quero falar com um vendedor humano"`.
**Resultado esperado:** classificador retorna `escalar_humano` em `ProcessamentoMensagem.intencao_classificada`.
**Status:** [ ]

#### CT-004-02 — Takeover manual via API
**Cobre:** REQ-004.3, REQ-004.4
**Pré-condição:** negociação ativa em modo `AGENTE`.
**Passos:**
1. `PATCH /api/negociacoes/{id}/modo-operacao` com `modo_operacao="HUMANO"`.
2. `GET /api/negociacoes/{id}`.
**Resultado esperado:** `modo_operacao=HUMANO` persistido.
**Status:** [ ]

#### CT-004-03 — Takeover via UI
**Cobre:** REQ-004.3, REQ-010.7
**Passos:**
1. Em `AcompanhamentoPage`, abrir negociação em modo AGENTE.
2. Clicar no botão de assumir/takeover.
**Resultado esperado:** modo muda para HUMANO no banco e UI reflete em tempo real (ou após refresh).
**Status:** [ ]

#### CT-004-04 — Modo HUMANO suspende respostas automáticas
**Cobre:** REQ-004.10
**Pré-condição:** negociação em modo HUMANO (CT-004-02).
**Passos:**
1. Enviar nova mensagem no webhook para o telefone dessa negociação.
**Resultado esperado:** nenhuma mensagem é gerada automaticamente; mensagem do cliente é registrada normalmente.
**Status:** [ ]

#### CT-004-05 — Intenção `reclamar`
**Cobre:** REQ-004.7
**Passos:**
1. `Body="estou muito insatisfeito com o atendimento"`.
**Resultado esperado:** intenção classificada como `reclamar`. Ação automática **não** é esperada nesta sprint (subitem 🟡); apenas validar detecção.
**Status:** [ ]

---

### REQ-005 — Registro de interações

#### CT-005-01 — Mensagem recebida persiste
**Cobre:** REQ-005.1
**Passos:**
1. Enviar mensagem qualquer via webhook.
2. `GET /api/historico/{telefone}`.
**Resultado esperado:** mensagem aparece com `OrigemMensagem.USER` e timestamp.
**Status:** [ ]

#### CT-005-02 — Mensagem enviada automaticamente persiste
**Cobre:** REQ-005.2
**Pré-condição:** negociação em modo AGENTE.
**Passos:**
1. Enviar pergunta que dispare resposta automática (ex.: `"qual o preço?"`).
**Resultado esperado:** resposta gerada aparece no histórico com `OrigemMensagem.SYSTEM`.
**Status:** [ ]

#### CT-005-03 — Auditoria IA/RAG completa
**Cobre:** REQ-005.6
**Passos:**
1. Em `AcompanhamentoPage`, clicar em modal de raciocínio de uma mensagem `SYSTEM`.
**Resultado esperado:** modal mostra pergunta original, classificação, intent, confiança, trechos RAG, resposta. Equivalente disponível via `GET /api/mensagens/{id}/raciocinio`.
**Status:** [ ]

#### CT-005-04 — Histórico por telefone
**Cobre:** REQ-005.5
**Passos:**
1. `GET /api/historico/5511999990001`.
**Resultado esperado:** retorna lista cronológica completa do telefone.
**Status:** [ ]

#### CT-005-05 — Listagem de negociações ativas
**Cobre:** REQ-005.5
**Passos:**
1. `GET /api/negociacoes/ativas`.
**Resultado esperado:** retorna negociações com `status` != `arquivado` (ou conforme regra). Verificar filtros disponíveis.
**Status:** [ ]

---

### REQ-006 — Rastreamento de orçamentos

#### CT-006-01 — Criar orçamento e associar à negociação
**Cobre:** REQ-006.1, REQ-006.2, REQ-006.3
**Passos:**
1. Via Swagger, criar `Orcamento` vinculado a `negociacao_id` e `contato_id` existentes.
2. Criar segundo orçamento na mesma negociação.
**Resultado esperado:** ambos persistidos com IDs únicos; relação 1:N com negociação respeitada.
**Status:** [ ]

#### CT-006-02 — Item de orçamento
**Cobre:** REQ-006.4
**Passos:**
1. Adicionar `ItemOrcamento` ao orçamento criado em CT-006-01.
**Resultado esperado:** item persiste com `produto_id`, quantidade e valor; relação `orcamento_id` correta.
**Status:** [ ]

#### CT-006-03 — Estado de orçamento
**Cobre:** REQ-006.5
**Passos:**
1. Atualizar `status` de um orçamento via PATCH (se endpoint exposto).
**Resultado esperado:** transição persiste; `atualizado_em` atualiza. Nota: REQ-006.5 está 🟡 — checklist de estados pode não estar 1:1 com o REQ; documentar gaps observados.
**Status:** [ ]

---

### REQ-008 — Twilio / WhatsApp (parcial mínimo)

#### CT-008-01 — Webhook aceita POST de form
**Cobre:** REQ-008.1, REQ-008.2
**Passos:**
1. `POST /webhook` com form-data `From=whatsapp:+5511999990001`, `Body="teste"`.
**Resultado esperado:** HTTP 200, mensagem registrada.
**Status:** [ ]

#### CT-008-02 — Associação por telefone
**Cobre:** REQ-008.4
**Passos:**
1. Repetir webhook com mesmo telefone duas vezes consecutivas.
**Resultado esperado:** segunda mensagem associa ao mesmo `Contato`/`Negociacao` (não recria).
**Status:** [ ]

#### CT-008-03 — Validar que envio outbound NÃO ocorre
**Cobre:** REQ-008.5 (🔴 — confirmação de gap)
**Passos:**
1. Em modo AGENTE, deixar agente responder a uma mensagem.
2. No banco, conferir a mensagem `SYSTEM` recém-criada na tabela `mensagens`.
**Resultado esperado:** mensagem persiste em `mensagens` mas nenhum campo de identificador externo Twilio (ex.: `sid_externo`/`twilio_sid`) é populado; nenhuma evidência de envio. Confirma o gap conhecido.
**Status:** [ ]

---

### REQ-010 — Painel administrativo

#### CT-010-01 — Cockpit carrega lista de negociações
**Cobre:** REQ-010.7
**Passos:**
1. Abrir `AcompanhamentoPage` no frontend.
**Resultado esperado:** lista de negociações ativas renderiza com telefone, status, modo, contagem de mensagens.
**Status:** [ ]

#### CT-010-02 — Abrir mensagens de uma negociação
**Cobre:** REQ-010.7
**Passos:**
1. Clicar em uma negociação na lista.
**Resultado esperado:** painel lateral/modal mostra mensagens ordenadas; mensagens USER e SYSTEM diferenciadas visualmente.
**Status:** [ ]

#### CT-010-03 — Modal de raciocínio acessível
**Cobre:** REQ-010.7, REQ-005.6
**Passos:**
1. Clicar no ícone de raciocínio de uma mensagem SYSTEM.
**Resultado esperado:** modal exibe classificação, intent, trechos RAG, resposta.
**Status:** [ ]

#### CT-010-04 — Filtro por modo HUMANO
**Cobre:** REQ-010.8
**Passos:**
1. Aplicar filtro de modo HUMANO no cockpit.
**Resultado esperado:** lista filtra apenas negociações em modo HUMANO.
**Status:** [ ]

#### CT-010-05 — Ausência de autenticação (confirmação de gap)
**Cobre:** REQ-010.1 (🔴 — confirmação de gap)
**Passos:**
1. Abrir `http://localhost:3000` em janela anônima.
2. Acessar `http://localhost:8000/api/negociacoes/ativas` direto pelo browser.
**Resultado esperado:** acesso aberto, sem login. Confirma o gap conhecido.
**Status:** [ ]

---

### REQ-011 — Modos de execução e aprovação de mensagens

#### CT-011-01 — Listagem de pendentes
**Cobre:** REQ-011 (workflow de aprovação)
**Pré-condição:** ao menos 1 mensagem com `pendente_aprovacao=true`.
**Passos:**
1. `GET /api/mensagens/pendentes`.
**Resultado esperado:** retorna lista das pendentes com conteúdo, negociação, raciocínio.
**Status:** [ ]

#### CT-011-02 — Aprovar mensagem
**Cobre:** REQ-011 (aprovação)
**Passos:**
1. `POST /api/mensagens/{id}/aprovar` com `aprovador_id` válido.
2. `GET /api/mensagens/{id}`.
**Resultado esperado:** `aprovado=true`, `aprovador_id` registrado, `pendente_aprovacao=false`.
**Status:** [ ]

#### CT-011-03 — Aprovar via UI
**Cobre:** REQ-011, REQ-010.7
**Passos:**
1. Em `AcompanhamentoPage`, encontrar mensagem pendente.
2. Clicar em "Aprovar".
**Resultado esperado:** mensagem desaparece da fila de pendentes; reflete no banco.
**Status:** [ ]

#### CT-011-04 — Reprovar mensagem com feedback
**Cobre:** REQ-011, REQ-013 (criação a partir de reprovação)
**Passos:**
1. Em uma mensagem pendente, clicar em "Reprovar".
2. No modal, fornecer "resposta correta" e confirmar.
**Resultado esperado:**
   - Mensagem fica `reprovada=true`, `reprovador_id` registrado.
   - Novo `ParQA` criado como rascunho (`aprovado=false, ativo=true`) com a pergunta original e a resposta correta.
   - Mensagem some da fila de pendentes (verificar bug fix da sprint).
**Status:** [ ]

#### CT-011-05 — Confirmação de gap: 3 modos formais
**Cobre:** REQ-011 (🔴 — confirmação de gap)
**Passos:**
1. No banco: `SELECT DISTINCT modo_operacao FROM negociacoes;`.
2. Tentar via API `PATCH /api/negociacoes/{id}/modo-operacao` com `modo_operacao="simulacao"`.
**Resultado esperado:** passo 1 retorna apenas `AGENTE` e `HUMANO`; passo 2 retorna erro de validação. Confirma que os 3 modos formais (`simulacao`/`conversa_controlada`/`execucao_normal`) ainda não existem.
**Status:** [ ]

---

### REQ-012 — Reports de problema

#### CT-012-01 — Criar report manualmente
**Cobre:** REQ-012 (criação)
**Passos:**
1. `POST /api/reports` com `categoria`, `severidade`, `descricao`, `mensagem_id` (opcional).
**Resultado esperado:** `ReportProblema` persiste; retorna ID; status inicial conforme regra (`aberto`).
**Status:** [ ]

#### CT-012-02 — Listagem de reports
**Cobre:** REQ-012
**Passos:**
1. `GET /api/reports?status=aberto`.
**Resultado esperado:** retorna lista filtrada por status.
**Status:** [ ]

#### CT-012-03 — UI ReportsPage
**Cobre:** REQ-012
**Passos:**
1. Acessar `ReportsPage` no frontend.
**Resultado esperado:** lista de reports com categoria, severidade, status; filtros básicos disponíveis.
**Status:** [ ]

#### CT-012-04 — Detalhe do report
**Cobre:** REQ-012
**Passos:**
1. Clicar em um report da lista.
**Resultado esperado:** `ReportDetalhe` exibe descrição completa, mensagem associada (se houver), histórico.
**Status:** [ ]

#### CT-012-05 — Transição de status
**Cobre:** REQ-012
**Passos:**
1. Mover report de `aberto` → `em_analise` → `resolvido` via UI ou API.
**Resultado esperado:** transições persistem; campo `atualizado_em` muda.
**Status:** [ ]

---

### REQ-013 — Pares Q&A curados

#### CT-013-01 — Listar pares Q&A
**Cobre:** REQ-013
**Passos:**
1. `GET /api/pares-qa`.
**Resultado esperado:** retorna lista com pergunta, resposta, status (aprovado/rascunho), `ativo`, `categoria_id`.
**Status:** [ ]

#### CT-013-02 — Criar par Q&A manualmente
**Cobre:** REQ-013
**Passos:**
1. `POST /api/pares-qa` com `pergunta`, `resposta`, `categoria_id`.
**Resultado esperado:** par criado como rascunho (`aprovado=false`, `embedding=null`).
**Status:** [ ]

#### CT-013-03 — Aprovação gera embedding (lazy embedding)
**Cobre:** REQ-013 (lazy embedding)
**Passos:**
1. `POST /api/pares-qa/{id}/aprovar` com `aprovador_id`.
2. Consultar registro no banco.
**Resultado esperado:** `aprovado=true`, `embedding` populado (não-nulo, dimensão correta).
**Status:** [ ]

#### CT-013-04 — Busca por similaridade só retorna aprovados
**Cobre:** REQ-013
**Pré-condição:** ao menos 1 par aprovado e 1 rascunho.
**Passos:**
1. `POST /api/pares-qa/buscar` com query similar ao par rascunho.
**Resultado esperado:** rascunho **não** é retornado; só aprovados aparecem.
**Status:** [ ]

#### CT-013-05 — UI QABasePage CRUD
**Cobre:** REQ-013
**Passos:**
1. Acessar `QABasePage`.
2. Criar, editar, aprovar e desativar pares via UI.
**Resultado esperado:** todas operações refletem no banco; lista atualiza.
**Status:** [ ]

#### CT-013-06 — Par Q&A criado por reprovação aparece como rascunho
**Cobre:** REQ-013 ↔ REQ-011
**Pré-condição:** CT-011-04 executado.
**Passos:**
1. Após reprovar com feedback, conferir na `QABasePage`.
**Resultado esperado:** par aparece com `aprovado=false`, sem embedding.
**Status:** [ ]

---

### REQ-014 — Configuração runtime das camadas de conhecimento

#### CT-014-01 — GET config RAG
**Cobre:** REQ-014
**Passos:**
1. `GET /api/config/rag`.
**Resultado esperado:** retorna `rag_score_minimo`, `rag_top_k` (e demais campos expostos).
**Status:** [ ]

#### CT-014-02 — PATCH config RAG
**Cobre:** REQ-014
**Passos:**
1. `PATCH /api/config/rag` com `rag_top_k=5`.
2. `GET /api/config/rag`.
**Resultado esperado:** valor atualizado; afeta próximas buscas RAG imediatamente (validar com CT-003-04).
**Status:** [ ]

#### CT-014-03 — Confirmação de gap: persistência entre reinícios
**Cobre:** REQ-014 (🔴 — confirmação de gap)
**Passos:**
1. Alterar `rag_top_k` para valor não-default via PATCH.
2. Reiniciar backend.
3. `GET /api/config/rag`.
**Resultado esperado:** valor volta ao default (configuração não persiste — gap conhecido).
**Status:** [ ]

#### CT-014-04 — Confirmação de gap: PATCH só cobre RAG
**Cobre:** REQ-014 (🔴 — confirmação de gap)
**Passos:**
1. Tentar `PATCH /api/config/rag` com campo `qa_score_minimo` (ou similar para Q&A).
**Resultado esperado:** campo ignorado ou erro — confirma que config Q&A ainda não está exposta.
**Status:** [ ]

---

## 3. Cenários transversais (fim-a-fim)

#### CT-E2E-01 — Conversa completa com qualificação parcial
**Cobre:** REQ-001, REQ-002, REQ-003, REQ-005, REQ-008, REQ-011
**Passos:**
1. Limpar telefone `5511999990010`.
2. Webhook: `"Oi, bom dia"` → esperar resposta saudação.
3. Webhook: `"Meu CNPJ é 00.000.000/0001-91"` → empresa consultada e cacheada.
4. Webhook: `"Preciso de 5 catracas"` → quantidade e tipo extraídos.
5. Webhook: `"qual o prazo de entrega?"` → RAG aciona; resposta vai para pendentes (se modo conversa_controlada/aprovação) OU sai (se AGENTE puro).
6. Aprovar a resposta via UI.
**Resultado esperado:** todo o fluxo registrado no histórico; `NegociacaoInfo` reflete os campos capturados; modal de raciocínio acessível para cada mensagem SYSTEM.
**Status:** [ ]

#### CT-E2E-02 — Reprovação que vira par Q&A
**Cobre:** REQ-011, REQ-013, REQ-005
**Passos:**
1. Identificar mensagem pendente com resposta IA incorreta.
2. Reprovar com resposta correta no modal.
3. Aprovar o par Q&A criado em `QABasePage`.
4. Enviar nova mensagem com pergunta similar à do par.
**Resultado esperado:** novo cliente recebe a resposta curada do par Q&A (não a do RAG documental). Verificar fonte na auditoria.
**Status:** [ ]

#### CT-E2E-03 — Takeover humano interrompe agente
**Cobre:** REQ-004, REQ-010, REQ-005
**Passos:**
1. Negociação em modo AGENTE com histórico de mensagens.
2. Em `AcompanhamentoPage`, executar takeover.
3. Enviar nova mensagem do cliente via webhook.
**Resultado esperado:** mensagem persiste mas **nenhuma** resposta automática é gerada. Vendedor pode enviar mensagem manual (se UI suportar) que ficará marcada como SYSTEM/manual.
**Status:** [ ]

---

## 4. Resumo de execução

> Preencher após rodar todos os cenários.

| REQ | Cenários | OK | FAIL | N/A |
|-----|---------:|---:|----:|----:|
| REQ-001 | 5 | | | |
| REQ-002 | 7 | | | |
| REQ-003 | 5 | | | |
| REQ-004 | 5 | | | |
| REQ-005 | 5 | | | |
| REQ-006 | 3 | | | |
| REQ-008 | 3 | | | |
| REQ-010 | 5 | | | |
| REQ-011 | 5 | | | |
| REQ-012 | 5 | | | |
| REQ-013 | 6 | | | |
| REQ-014 | 4 | | | |
| E2E | 3 | | | |
| **Total** | **61** | | | |

---

## 5. Histórico

| Data | Versão | Mudança |
|------|--------|---------|
| 2026-05-27 | 1.0 | Criação inicial. 61 cenários cobrindo REQs com status ✅/🟡 da Sprint 2 + 3 fluxos E2E. Rastreabilidade ao nível de subitem. |
| 2026-05-27 | 1.1 | Restringidos meios de verificação a UI/API/SQL apenas. CT-008-03 e CT-011-05 reescritos para usar SQL em vez de logs/código. Adicionada §1.1 com queries SQL prontas. |
