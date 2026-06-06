# Cenários de Teste Funcional — Sprint 2

**Data:** 2026-05-27
**Autor:** `[qa]` (Cascade)
**Escopo:** validação funcional caixa-preta dos comportamentos entregues até o fim da Sprint 2.
**Público:** equipe de testes — **não requer conhecimento de código, modelos ou banco**.
**Modo de execução:** manual.
**Versão técnica equivalente:** `cenarios_teste_sprint02.md` (mantido em paralelo para uso da equipe de desenvolvimento).
**Fonte de cobertura:** `artefatos/gerente_de_projetos/cobertura_reqs_sprint02.md`.

---

## 0. Convenções

### Identificação

`CTF-<REQ>-<NN>` — `CTF` = Cenário de Teste Funcional; sufixo numérico por REQ. Cenários fim-a-fim: `CTF-E2E-<NN>`.

### Rastreabilidade

Cada cenário cita o REQ (ou subitens) que valida, no formato `REQ-XXX` ou `REQ-XXX.Y`. A numeração de subitens segue `cobertura_reqs_sprint02.md`.

### Meios de verificação permitidos

- **Painel de administração** (frontend) — telas `Acompanhamento`, `Reports`, `Base de Q&A`, `Pendentes de aprovação`.
- **Conversa simulada** via `POST /webhook` no Swagger UI (`http://localhost:8000/docs`) — equivale a uma mensagem entrando pelo WhatsApp.
- **Endpoints listados em Swagger** que retornam dados que aparecem no painel (ex.: `GET /api/historico/{telefone}`, `GET /api/empresas`).

Não use: inspeção de código, logs do servidor, consultas SQL diretas. Se um cenário não puder ser concluído pelos meios acima, marque `[N/A]` e descreva.

### Status

- `[ ]` não executado
- `[OK]` passou
- `[FAIL]` falhou — anotar evidência (print, vídeo curto, transcrição) em `artefatos/qa/evidencias/CTF-XXX-NN/`
- `[N/A]` impossível executar agora — anotar motivo curto

### Severidade quando falha

| Severidade | Critério |
|------------|----------|
| 🔴 Crítica | Bloqueia o fluxo principal do REQ; sistema fica inutilizável |
| 🟡 Alta | Funcionalidade essencial degradada; há workaround |
| 🟢 Média | Comportamento incorreto sem impacto funcional grave |
| ⚪ Baixa | Cosmético / mensagem / UX |

---

## 1. Pré-requisitos do ambiente

1. **Backend** acessível em `http://localhost:8000` (Swagger em `/docs`).
2. **Painel** acessível em `http://localhost:3000` (ou `5173`).
3. Base mínima:
   - Pelo menos um produto ativo com conteúdo na base de conhecimento.
   - Pelo menos um par Q&A aprovado e ativo.
4. **Telefone de teste:** `5511999990000`. Use sufixos diferentes (`...001`, `...002`, ...) por cenário para evitar colisão entre execuções.
5. **CNPJ de teste válido:** ex.: `00.000.000/0001-91` (Banco do Brasil).
6. Para enviar mensagem como cliente: usar `POST /webhook` em Swagger, preenchendo `From=whatsapp:+<telefone>` e `Body=<texto>`.

---

### 1.1 Como usar o Swagger UI

O **Swagger UI** é a página de documentação interativa das APIs do backend, gerada automaticamente. Você usa ela para simular ações que ainda não têm tela no painel (ex.: enviar mensagem como se fosse o WhatsApp, consultar configuração).

**Acesso:** `http://localhost:8000/docs` (com o backend rodando).

**Passo a passo genérico:**

1. Abrir a página acima no navegador.
2. Localizar o endpoint pelo nome (ex.: `POST /webhook`) — a lista é organizada em grupos.
3. Clicar na linha do endpoint para expandir os detalhes.
4. Clicar no botão **Try it out** (canto direito).
5. Preencher os campos do formulário que aparecem.
6. Clicar em **Execute**.
7. Rolar para baixo: aparece a resposta com **Code** (200 = OK, 4xx/5xx = erro), o **Response body** (JSON) e os **Response headers**.

**Exemplo — enviar mensagem como cliente (`POST /webhook`):**

| Campo | Valor exemplo |
|-------|---------------|
| `From` | `whatsapp:+5511999990001` |
| `Body` | `Bom dia, meu CNPJ é 00.000.000/0001-91` |

Após **Execute**, o esperado é `Code: 200`. Em seguida, abrir o painel para ver o efeito da mensagem.

**Exemplo — consultar histórico (`GET /api/historico/{telefone}`):**

1. Expandir o endpoint, clicar em **Try it out**.
2. No campo `telefone`, colocar `5511999990001`.
3. **Execute** → retorna a lista de mensagens daquele telefone.

**Dicas:**

- Se um campo é obrigatório, ele aparece marcado com `*`.
- Para endpoints `PATCH`/`POST` com corpo JSON, há um exemplo pré-preenchido — basta ajustar os valores.
- Se algo der `422 Unprocessable Entity`, geralmente é campo obrigatório faltando ou tipo errado (a mensagem de erro indica qual).
- Use o botão **Cancel** para descartar uma chamada antes de executar.

---

## 2. Cenários por REQ

### REQ-001 — Integração Receita Federal

#### CTF-001-01 — Cliente envia mensagem com CNPJ válido
**Cobre:** REQ-001.1, REQ-001.2, REQ-001.3, REQ-001.7
**Passos:**
1. Enviar mensagem `"Bom dia, meu CNPJ é 00.000.000/0001-91"` pelo telefone `5511999990001`.
2. No painel de Acompanhamento, abrir a conversa do telefone `5511999990001`.
**Resultado esperado:** painel mostra a mensagem recebida; a negociação exibe a empresa identificada (razão social, situação cadastral, ao menos um endereço).
**Status:** [ ]

#### CTF-001-02 — Mensagem sem CNPJ válido
**Cobre:** REQ-001.2
**Passos:**
1. Enviar `"meu CNPJ é 123"` pelo telefone `5511999990002`.
2. Abrir a conversa no painel.
**Resultado esperado:** mensagem aparece no painel, mas **nenhuma** empresa é vinculada à negociação.
**Status:** [ ]

#### CTF-001-03 — Reuso de empresa já consultada
**Cobre:** REQ-001.7, REQ-002.10
**Pré-condição:** CTF-001-01 executado com sucesso.
**Passos:**
1. Enviar o mesmo CNPJ pelo telefone `5511999990003`.
2. Abrir as duas conversas no painel.
**Resultado esperado:** ambas mostram exatamente os mesmos dados de empresa (mesma razão social/endereço); a operação não demora notavelmente mais que a primeira (uso de cache).
**Status:** [ ]

#### CTF-001-04 — Empresa visível em consulta direta
**Cobre:** REQ-001.7
**Pré-condição:** CTF-001-01 OK.
**Passos:**
1. No Swagger, executar `GET /api/empresas?cnpj=00000000000191`.
**Resultado esperado:** retorna razão social, situação, endereço, ao menos 1 atividade/CNAE e ao menos 1 sócio.
**Status:** [ ]

#### CTF-001-05 — Empresa associada à negociação
**Cobre:** REQ-001.5
**Pré-condição:** CTF-001-01 OK.
**Passos:**
1. No painel, abrir a negociação criada e identificar o vínculo com a empresa.
**Resultado esperado:** dados da empresa aparecem como contexto da negociação.
**Status:** [ ]

---

### REQ-002 — Fluxo conversacional guiado

> Observação: a verificação aqui é pelo **comportamento da conversa** e pelo que aparece no painel. A "intenção classificada" é exibida no modal de raciocínio da mensagem (acessível pelo painel de Acompanhamento).

#### CTF-002-01 — Saudação
**Cobre:** REQ-002.1
**Passos:**
1. Enviar `"Oi, bom dia!"`.
2. Abrir a mensagem no painel e abrir o modal de raciocínio.
**Resultado esperado:** modal mostra a mensagem como saudação; sistema responde de forma compatível com saudação (não pede CNPJ, não inicia qualificação técnica).
**Status:** [ ]

#### CTF-002-02 — Pergunta sobre preço aciona base de conhecimento
**Cobre:** REQ-002.1, REQ-003 (geração)
**Passos:**
1. Enviar `"quanto custa a catraca?"`.
2. Abrir a mensagem e o modal de raciocínio.
**Resultado esperado:** resposta do agente toca no tema preço/orçamento e, no modal de raciocínio, aparecem trechos da base de conhecimento usados como referência.
**Status:** [ ]

#### CTF-002-03 — Quantidade e tipo de produto extraídos
**Cobre:** REQ-002.2, REQ-002.3, REQ-002.3A
**Passos:**
1. Enviar `"Preciso de 5 catracas para minha empresa"`.
2. No painel, abrir a negociação correspondente.
**Resultado esperado:** painel mostra na negociação "quantidade = 5" e "tipo de produto = catraca" capturados como informação do cliente.
**Status:** [ ]

#### CTF-002-04 — E-mail extraído
**Cobre:** REQ-002.2
**Passos:**
1. Enviar `"meu email é teste@empresa.com"`.
2. Abrir a mensagem no painel.
**Resultado esperado:** o e-mail é reconhecido como informação do cliente (visível no painel ou no detalhe da negociação).
**Status:** [ ]

#### CTF-002-05 — Tipo de produto fora do catálogo suportado
**Cobre:** REQ-002.3A (limitação conhecida)
**Passos:**
1. Enviar `"Quero uma câmera de segurança"`.
**Resultado esperado:** o sistema **não** classifica como catraca nem relógio de ponto. A resposta deve, no mínimo, não confirmar erroneamente o tipo. Anotar como o sistema reage (resposta genérica? pede mais detalhes? escala?).
**Status:** [ ]

#### CTF-002-06 — Painel mostra estado dos campos da negociação
**Cobre:** REQ-002.3
**Passos:**
1. Iniciar uma conversa enviando apenas `"Bom dia, meu CNPJ é 00.000.000/0001-91"` (sem informar quantidade).
2. Abrir a negociação no painel.
**Resultado esperado:** o painel mostra que CNPJ já foi capturado e que campos como "quantidade" e "tipo de produto" ainda estão pendentes.
**Status:** [ ]

#### CTF-002-07 — Pergunta livre durante qualificação consulta a base
**Cobre:** REQ-002.17
**Passos:**
1. Em uma conversa já iniciada (com CNPJ informado), enviar `"qual o prazo de entrega?"`.
2. Abrir o modal de raciocínio dessa mensagem.
**Resultado esperado:** o modal mostra trechos da base de conhecimento; a resposta gerada cita prazo (ou explicita falta de informação).
**Status:** [ ]

#### CTF-002-08 — Pergunta sobre catálogo da empresa é atendida pela base de Q&A
**Cobre:** REQ-002.1, REQ-002.1A (caso 1 — confiança alta), REQ-002.1B (cat. 3 antes do documento fiscal)
**Pré-condição:** existir par Q&A aprovado e ativo equivalente a `"Quais produtos a Inforrel vende?"` (criar via `Base de Q&A` se necessário). Usar telefone **`5511999990020` sempre como contato novo** (nunca visto antes no banco de testes) — valida que cat. 3 funciona **sem** CNPJ prévio.
**Passos:**
1. Garantir que o telefone `5511999990020` **não** exista em `contatos` (limpar dados de teste anteriores se necessário).
2. Enviar `"Quais produtos a Inforrel vende?"` por esse telefone.
3. Abrir o modal de raciocínio da resposta no painel.
**Resultado esperado:**
- O sistema **responde** ao cliente com o conteúdo da Q&A (não retorna "não entendi" nem pede CNPJ antes de responder).
- Foi criado contato/negociação anônimo (`empresa_id` nulo) para registrar a conversa (REQ-002.1B).
- O modal mostra a categoria classificada como **pergunta sobre produto/serviço/empresa** com confiança **alta** (rota direta para REQ-003).
- O modal **não** indica fallback acionado (`fallback_req003` = false ou não aplicável).
**Status:** [ ]

#### CTF-002-09 — Fallback condicional acionado em mensagem ambígua
**Cobre:** REQ-002.1A (caso 2 — fallback por baixa confiança)
**Pré-condição:** existir par Q&A aprovado equivalente ao tema da mensagem (ex.: catálogo, prazo, formas de pagamento). Mensagem propositalmente ambígua que tende a confundir o classificador.
**Passos:**
1. Enviar uma mensagem ambígua que toque em produto/serviço sem ser claramente uma pergunta direta — ex.: `"queria saber sobre as catracas de vocês"` pelo telefone `5511999990021`.
2. Abrir o modal de raciocínio.
**Resultado esperado:**
- Se a confiança do classificador for **alta** em alguma categoria → comportamento conforme essa categoria (sem fallback).
- Se a confiança for **baixa** ou retornar "não identificado" → o modal indica que houve **fallback via REQ-003**, mostra a confiança original do classificador, e a resposta entregue ao cliente vem da base.
- **Em nenhum caso** o sistema deve responder "não entendi" sem antes ter tentado o fallback (anti-padrão do REQ-002.1A).
**Status:** [ ]

#### CTF-002-10 — Anti-padrão: fallback NÃO acontece em resposta de qualificação
**Cobre:** REQ-002.1A (anti-padrão — não consultar REQ-003 em toda mensagem)
**Pré-condição:** conversa em curso com qualificação ativa (ex.: sistema acabou de perguntar "qual a quantidade de catracas?").
**Passos:**
1. Em uma conversa já em qualificação, responder `"5"` ao prompt do sistema (telefone `5511999990022`).
2. Abrir o modal de raciocínio dessa resposta.
**Resultado esperado:**
- Mensagem é classificada como **resposta a pergunta de qualificação em curso** (categoria 2 do REQ-002.1).
- O campo "quantidade" é capturado na negociação.
- O modal **não** indica consulta à base de Q&A nem trechos de RAG anexados (REQ-003 não foi acionado).
- A resposta do agente **não** mistura conteúdo da base com a confirmação da qualificação.
**Status:** [ ]

---

### REQ-003 — RAG / respostas automáticas

#### CTF-003-01 — Pergunta técnica retorna conteúdo da base
**Cobre:** REQ-003.2, REQ-003.3
**Passos:**
1. Enviar `"me fala sobre catraca biométrica"` em uma conversa.
2. Abrir o modal de raciocínio da resposta gerada.
**Resultado esperado:** modal lista trechos consultados na base; a resposta é coerente com o conteúdo desses trechos.
**Status:** [ ]

#### CTF-003-02 — Auditoria da resposta no painel
**Cobre:** REQ-003.5, REQ-005.6
**Passos:**
1. Em qualquer mensagem respondida automaticamente, abrir o modal de raciocínio.
**Resultado esperado:** modal exibe pergunta original, classificação/intenção, trechos consultados e resposta final entregue ao cliente.
**Status:** [ ]

#### CTF-003-03 — Par Q&A aprovado precede a base documental
**Cobre:** REQ-003 ↔ REQ-013
**Pré-condição:** existir par Q&A aprovado e ativo cuja pergunta seja `"qual o horário de atendimento?"` (ou equivalente próximo). Caso não exista, criá-lo via `Base de Q&A` antes do teste.
**Passos:**
1. Enviar `"qual o horário de atendimento?"`.
2. Abrir o modal de raciocínio.
**Resultado esperado:** a resposta é a do par Q&A (idêntica ou com pequena variação) e o modal indica que a fonte foi a base curada (Q&A), não a base documental.
**Status:** [ ]

#### CTF-003-04 — Mudança de configuração afeta busca
**Cobre:** REQ-014, REQ-003.2
**Passos:**
1. Em Swagger, `GET /api/config/rag` para registrar valor atual de `rag_top_k`.
2. `PATCH /api/config/rag` com `rag_top_k=1`.
3. Em uma conversa, enviar uma pergunta técnica que normalmente traz vários trechos.
4. Abrir o modal de raciocínio.
5. Restaurar valor original via PATCH.
**Resultado esperado:** após o passo 2, o modal de raciocínio mostra **no máximo 1 trecho** consultado.
**Status:** [ ]

---

### REQ-004 — Escalonamento para humano

#### CTF-004-01 — Cliente pede atendimento humano
**Cobre:** REQ-004.1, REQ-004.6
**Passos:**
1. Enviar `"quero falar com um vendedor humano"`.
2. Abrir o modal de raciocínio da mensagem no painel.
**Resultado esperado:** intenção/classificação registrada como pedido de atendimento humano. (Ação automática de escalar **não** está implementada nesta sprint — apenas detecção é validada aqui.)
**Status:** [ ]

#### CTF-004-02 — Vendedor assume conversa pelo painel
**Cobre:** REQ-004.3, REQ-004.4
**Pré-condição:** existir negociação em modo "agente".
**Passos:**
1. No painel, abrir a negociação.
2. Acionar o botão de assumir/takeover.
3. Recarregar a página.
**Resultado esperado:** após o takeover, a negociação aparece em modo "humano" e o estado persiste após o refresh.
**Status:** [ ]

#### CTF-004-03 — Modo humano suspende respostas automáticas
**Cobre:** REQ-004.10
**Pré-condição:** CTF-004-02 OK.
**Passos:**
1. Para essa mesma negociação (em modo humano), enviar nova mensagem do cliente via webhook.
2. Aguardar alguns segundos e abrir o painel.
**Resultado esperado:** a mensagem do cliente aparece no painel; **nenhuma** resposta automática do agente é gerada.
**Status:** [ ]

#### CTF-004-04 — Reclamação é detectada
**Cobre:** REQ-004.7
**Passos:**
1. Enviar `"estou muito insatisfeito com o atendimento"`.
2. Abrir modal de raciocínio.
**Resultado esperado:** intenção registrada como reclamação. Ação automática não é esperada.
**Status:** [ ]

---

### REQ-005 — Registro de interações

#### CTF-005-01 — Mensagem do cliente aparece no histórico
**Cobre:** REQ-005.1
**Passos:**
1. Enviar uma mensagem qualquer pelo telefone `5511999990010`.
2. Em Swagger, `GET /api/historico/5511999990010`.
**Resultado esperado:** retorno inclui a mensagem enviada com origem indicando que veio do cliente, e timestamp.
**Status:** [ ]

#### CTF-005-02 — Resposta automática aparece no histórico
**Cobre:** REQ-005.2
**Pré-condição:** negociação em modo agente.
**Passos:**
1. Enviar uma pergunta que dispare resposta (`"qual o preço?"`).
2. Atualizar o painel de Acompanhamento para essa conversa.
**Resultado esperado:** resposta do agente aparece na conversa, marcada como mensagem enviada pelo sistema.
**Status:** [ ]

#### CTF-005-03 — Auditoria completa por mensagem
**Cobre:** REQ-005.6
**Passos:**
1. No painel, escolher qualquer mensagem respondida pelo agente.
2. Abrir o modal de raciocínio.
**Resultado esperado:** modal mostra pergunta, classificação/intenção, confiança, trechos consultados e resposta.
**Status:** [ ]

#### CTF-005-04 — Histórico por telefone
**Cobre:** REQ-005.5
**Passos:**
1. Em Swagger, `GET /api/historico/<telefone com mensagens>`.
**Resultado esperado:** retorna a sequência cronológica completa, incluindo mensagens do cliente e do sistema.
**Status:** [ ]

#### CTF-005-05 — Listagem de negociações ativas no painel
**Cobre:** REQ-005.5, REQ-010.7
**Passos:**
1. Abrir a tela de Acompanhamento.
**Resultado esperado:** lista mostra as negociações ativas com telefone, status atual, modo (agente/humano) e indicação de mensagens recentes.
**Status:** [ ]

---

### REQ-006 — Rastreamento de orçamentos (parcial)

> Observação: a Sprint 2 não entregou tela dedicada de orçamentos. Os cenários abaixo usam Swagger para validar que o backend já mantém os dados — cobertura mais ampla virá em sprint futura.

#### CTF-006-01 — Criar orçamento associado a cliente
**Cobre:** REQ-006.1, REQ-006.2
**Pré-condição:** existir uma negociação ativa.
**Passos:**
1. Em Swagger, criar um orçamento informando a negociação e o contato existentes.
2. Consultar o orçamento criado.
**Resultado esperado:** retorna ID único; orçamento aparece vinculado ao cliente/negociação informados.
**Status:** [ ]

#### CTF-006-02 — Cliente pode ter múltiplos orçamentos
**Cobre:** REQ-006.3
**Passos:**
1. Criar um segundo orçamento na mesma negociação.
2. Listar orçamentos da negociação.
**Resultado esperado:** ambos aparecem com IDs distintos.
**Status:** [ ]

#### CTF-006-03 — Item de orçamento
**Cobre:** REQ-006.4
**Passos:**
1. Adicionar um item ao orçamento criado em CTF-006-01 (produto, quantidade, valor).
2. Consultar novamente o orçamento.
**Resultado esperado:** item retorna nas informações do orçamento com os valores informados.
**Status:** [ ]

---

### REQ-008 — WhatsApp / Twilio (parcial mínimo)

#### CTF-008-01 — Webhook aceita mensagem entrante
**Cobre:** REQ-008.1, REQ-008.2
**Passos:**
1. Em Swagger, `POST /webhook` com `From=whatsapp:+5511999990050`, `Body="teste de entrada"`.
**Resultado esperado:** resposta HTTP 200; mensagem aparece no painel para esse telefone.
**Status:** [ ]

#### CTF-008-02 — Mensagens do mesmo telefone permanecem em uma conversa
**Cobre:** REQ-008.4
**Passos:**
1. Enviar duas mensagens consecutivas pelo mesmo telefone.
2. Abrir a conversa no painel.
**Resultado esperado:** ambas aparecem na mesma conversa; o painel não cria duplicidade do mesmo cliente.
**Status:** [ ]

#### CTF-008-03 — Confirmação de gap: agente não envia mensagens reais
**Cobre:** REQ-008.5 (gap conhecido)
**Passos:**
1. Em uma conversa em modo agente, enviar uma pergunta que normalmente seria respondida.
2. Confirmar com a equipe técnica/observar no painel se a resposta saiu apenas para o painel ou também foi "enviada" para algum canal externo.
**Resultado esperado:** resposta aparece **apenas** no painel; nenhum envio outbound real ocorre. Confirma o gap.
**Status:** [ ]

---

### REQ-010 — Painel administrativo

#### CTF-010-01 — Cockpit lista negociações
**Cobre:** REQ-010.7
**Passos:**
1. Abrir a tela de Acompanhamento.
**Resultado esperado:** lista com telefone, status, modo e contagem/preview de mensagens.
**Status:** [ ]

#### CTF-010-02 — Detalhe da conversa
**Cobre:** REQ-010.7
**Passos:**
1. Clicar em uma negociação.
**Resultado esperado:** mensagens aparecem em ordem cronológica, com diferenciação visual entre cliente e sistema.
**Status:** [ ]

#### CTF-010-03 — Modal de raciocínio
**Cobre:** REQ-010.7, REQ-005.6
**Passos:**
1. Em uma mensagem respondida pelo sistema, acionar o ícone/ação de "ver raciocínio".
**Resultado esperado:** modal abre com classificação, trechos da base e resposta.
**Status:** [ ]

#### CTF-010-04 — Filtro por modo humano
**Cobre:** REQ-010.8
**Passos:**
1. Aplicar filtro "modo humano" na tela de Acompanhamento.
**Resultado esperado:** lista mostra apenas conversas em atendimento humano.
**Status:** [ ]

#### CTF-010-05 — Confirmação de gap: painel sem login
**Cobre:** REQ-010.1 (gap conhecido)
**Passos:**
1. Abrir o painel em uma janela anônima.
**Resultado esperado:** carrega sem solicitar credenciais. Confirma que autenticação ainda não está implementada.
**Status:** [ ]

---

### REQ-011 — Aprovação de mensagens (workflow)

#### CTF-011-01 — Mensagem pendente aparece na fila
**Cobre:** REQ-011 (workflow)
**Pré-condição:** sistema configurado para enfileirar mensagens (modo de aprovação ativo).
**Passos:**
1. Provocar uma resposta automática enviando uma pergunta ao webhook.
2. Abrir a tela/seção de "Pendentes de aprovação" no painel.
**Resultado esperado:** a resposta gerada aparece na fila com pergunta original, conteúdo e contexto.
**Status:** [ ]

#### CTF-011-02 — Aprovar uma mensagem
**Cobre:** REQ-011 (aprovação)
**Pré-condição:** existir mensagem pendente.
**Passos:**
1. Abrir a mensagem pendente e clicar em "Aprovar".
**Resultado esperado:** mensagem some da fila; aparece marcada como aprovada na conversa.
**Status:** [ ]

#### CTF-011-03 — Reprovar uma mensagem com resposta correta
**Cobre:** REQ-011 (reprovação) ↔ REQ-013 (criação de Q&A)
**Pré-condição:** existir mensagem pendente.
**Passos:**
1. Clicar em "Reprovar".
2. No modal, fornecer a resposta correta e confirmar.
3. Abrir a tela "Base de Q&A".
**Resultado esperado:**
   - Mensagem some da fila de pendentes.
   - Na Base de Q&A aparece um novo par como **rascunho** com a pergunta original e a resposta corrigida (não publicado para uso ainda).
**Status:** [ ]

#### CTF-011-04 — Bug fix: mensagem reprovada não fica pendente
**Cobre:** REQ-011 (estabilização da Sprint 2)
**Passos:**
1. Reprovar uma mensagem e recarregar a página.
**Resultado esperado:** após o refresh, a mensagem reprovada **não** reaparece na fila de pendentes.
**Status:** [ ]

#### CTF-011-05 — Confirmação de gap: três modos formais
**Cobre:** REQ-011 (gap conhecido)
**Passos:**
1. No painel, observar quais modos de operação a negociação pode assumir.
**Resultado esperado:** somente "agente" e "humano". Os modos `simulacao`, `conversa_controlada` e `execucao_normal` ainda não existem na interface.
**Status:** [ ]

---

### REQ-012 — Reports de problema

#### CTF-012-01 — Criar report a partir do painel
**Cobre:** REQ-012 (criação)
**Passos:**
1. Abrir a tela de Reports.
2. Criar um report novo informando categoria, severidade e descrição.
**Resultado esperado:** report aparece na lista com status inicial (ex.: "aberto") e dados informados.
**Status:** [ ]

#### CTF-012-02 — Filtrar reports por status
**Cobre:** REQ-012
**Passos:**
1. Aplicar filtro "aberto" na lista.
**Resultado esperado:** lista mostra apenas reports nesse status.
**Status:** [ ]

#### CTF-012-03 — Detalhe do report
**Cobre:** REQ-012
**Passos:**
1. Clicar em um report da lista.
**Resultado esperado:** tela de detalhe mostra descrição completa, categoria, severidade, status e mensagem associada (se houver).
**Status:** [ ]

#### CTF-012-04 — Transição de status
**Cobre:** REQ-012
**Passos:**
1. Em um report aberto, mudar status para "em análise" e depois para "resolvido".
**Resultado esperado:** transições refletem na lista e no detalhe; data/hora de atualização muda.
**Status:** [ ]

---

### REQ-013 — Pares Q&A curados

#### CTF-013-01 — Listar Q&As
**Cobre:** REQ-013
**Passos:**
1. Abrir a Base de Q&A.
**Resultado esperado:** lista mostra cada par com pergunta, resposta, status (rascunho/aprovado) e indicação de ativo.
**Status:** [ ]

#### CTF-013-02 — Criar par Q&A manualmente
**Cobre:** REQ-013
**Passos:**
1. Na Base de Q&A, criar um novo par com pergunta e resposta.
**Resultado esperado:** par aparece na lista como rascunho (não aprovado).
**Status:** [ ]

#### CTF-013-03 — Aprovar e usar par Q&A
**Cobre:** REQ-013, REQ-003
**Passos:**
1. Aprovar o par criado em CTF-013-02 (ou outro rascunho existente).
2. Em uma conversa, enviar uma pergunta semelhante à do par aprovado.
3. Abrir o modal de raciocínio da resposta.
**Resultado esperado:** após aprovação, a pergunta similar passa a ser respondida pelo conteúdo do par; o modal indica fonte como base de Q&A.
**Status:** [ ]

#### CTF-013-04 — Buscar Q&A no painel
**Cobre:** REQ-013
**Pré-condição:** ao menos 1 par aprovado e 1 rascunho.
**Passos:**
1. Buscar na Base de Q&A por uma palavra-chave presente no rascunho.
**Resultado esperado:** rascunhos podem aparecer na busca interna do painel (gestão), mas **não** são usados em respostas reais ao cliente (validar com CTF-013-03).
**Status:** [ ]

#### CTF-013-05 — Editar e desativar par
**Cobre:** REQ-013
**Passos:**
1. Editar um par existente e salvar.
2. Desativar o par.
3. Enviar pergunta correspondente em uma conversa.
**Resultado esperado:** edição persiste na lista; após desativar, o par não é mais usado em respostas.
**Status:** [ ]

#### CTF-013-06 — Par criado por reprovação aparece como rascunho
**Cobre:** REQ-013 ↔ REQ-011
**Pré-condição:** CTF-011-03 executado.
**Passos:**
1. Após a reprovação, abrir a Base de Q&A.
**Resultado esperado:** par criado a partir da reprovação aparece como rascunho até que alguém o aprove.
**Status:** [ ]

---

### REQ-014 — Configuração das camadas de conhecimento

#### CTF-014-01 — Consultar configuração atual
**Cobre:** REQ-014
**Passos:**
1. Em Swagger, `GET /api/config/rag`.
**Resultado esperado:** retorna parâmetros configuráveis (no mínimo `rag_score_minimo` e `rag_top_k`).
**Status:** [ ]

#### CTF-014-02 — Alterar configuração
**Cobre:** REQ-014
**Passos:**
1. `PATCH /api/config/rag` com `rag_top_k=5`.
2. `GET /api/config/rag`.
**Resultado esperado:** valor atualizado é refletido imediatamente.
**Status:** [ ]

#### CTF-014-03 — Configuração afeta o comportamento
**Cobre:** REQ-014, REQ-003
**Passos:** equivalente a CTF-003-04.
**Resultado esperado:** mudança em `rag_top_k` reduz o número de trechos exibidos no modal de raciocínio.
**Status:** [ ]

#### CTF-014-04 — Confirmação de gap: configuração de Q&A
**Cobre:** REQ-014 (gap conhecido)
**Passos:**
1. Tentar `PATCH /api/config/rag` informando um campo de Q&A (ex.: `qa_score_minimo`).
**Resultado esperado:** o campo é ignorado ou rejeitado; configuração da camada Q&A ainda não é exposta.
**Status:** [ ]

#### CTF-014-05 — Confirmação de gap: persistência entre reinícios
**Cobre:** REQ-014 (gap conhecido)
**Passos:**
1. Alterar `rag_top_k` via PATCH para um valor diferente do default.
2. Pedir à equipe técnica para reiniciar o backend (ou aguardar reinício natural).
3. `GET /api/config/rag`.
**Resultado esperado:** após o reinício, valor volta ao default. Confirma que configuração ainda não persiste.
**Status:** [ ]

---

## 3. Cenários fim-a-fim

#### CTF-E2E-01 — Conversa completa com qualificação
**Cobre:** REQ-001, REQ-002, REQ-003, REQ-005, REQ-008, REQ-011
**Passos:**
1. Em telefone novo `5511999990100`, enviar `"Oi, bom dia"`.
2. Enviar `"Meu CNPJ é 00.000.000/0001-91"`.
3. Enviar `"Preciso de 5 catracas"`.
4. Enviar `"qual o prazo de entrega?"`.
5. No painel, abrir a conversa, conferir mensagens e abrir o modal de raciocínio da resposta sobre prazo.
6. Se a resposta estiver na fila de pendentes, aprová-la.
**Resultado esperado:** todas as mensagens aparecem em ordem; empresa identificada e vinculada à negociação; quantidade e tipo capturados; resposta sobre prazo cita conteúdo da base; modal de raciocínio acessível.
**Status:** [ ]

#### CTF-E2E-02 — Reprovação vira par Q&A
**Cobre:** REQ-011, REQ-013, REQ-005
**Passos:**
1. Encontrar uma resposta automática que esteja com conteúdo inadequado.
2. Reprová-la com a resposta correta.
3. Aprovar o par criado na Base de Q&A.
4. Em conversa nova, enviar uma pergunta similar.
**Resultado esperado:** a nova conversa recebe a resposta curada; modal de raciocínio aponta a base de Q&A como fonte.
**Status:** [ ]

#### CTF-E2E-03 — Takeover humano interrompe agente
**Cobre:** REQ-004, REQ-010, REQ-005
**Passos:**
1. Iniciar conversa em modo agente e fazer algumas trocas com respostas automáticas.
2. No painel, executar takeover.
3. Enviar mais uma mensagem do cliente.
**Resultado esperado:** mensagem do cliente aparece na conversa, mas o agente **não** responde automaticamente; modo da negociação mostrado como humano.
**Status:** [ ]

---

## 4. Resumo de execução

> Atualizado automaticamente por `agentes/scripts/qa/gera_resumo_cenarios_teste.py` (com `--arquivo cenarios_teste_funcionais_sprint02.md`).

| REQ | Cenários | OK | FAIL | N/A |
|-----|---------:|---:|----:|----:|
| REQ-001 | 5 | | | |
| REQ-002 | 7 | | | |
| REQ-003 | 4 | | | |
| REQ-004 | 4 | | | |
| REQ-005 | 5 | | | |
| REQ-006 | 3 | | | |
| REQ-008 | 3 | | | |
| REQ-010 | 5 | | | |
| REQ-011 | 5 | | | |
| REQ-012 | 4 | | | |
| REQ-013 | 6 | | | |
| REQ-014 | 5 | | | |
| E2E | 3 | | | |
| **Total** | **59** | | | |

---

## 5. Diferenças vs. versão técnica (`cenarios_teste_sprint02.md`)

| Aspecto | Versão técnica | Esta versão (funcional) |
|---------|----------------|-------------------------|
| Público | Equipe de desenvolvimento | Equipe de testes / QA |
| Verificação | UI + API + SQL direto + nomes de modelos/tabelas | UI + API públicas, sem SQL nem internals |
| Linguagem | Termos do código (`ProcessamentoMensagem`, `OrigemMensagem.SYSTEM`, `ParQA`, etc.) | Termos do produto ("modal de raciocínio", "fila de pendentes", "base de Q&A") |
| Volume | 61 cenários | 59 cenários (3 itens de SQL/inspeção foram fundidos ou removidos por não terem verificação caixa-preta) |

---

## 6. Histórico

| Data | Versão | Mudança |
|------|--------|---------|
| 2026-05-27 | 1.0 | Criação inicial. Versão funcional caixa-preta derivada de `cenarios_teste_sprint02.md`. 59 cenários verificáveis somente via UI e endpoints públicos. |
| 2026-05-27 | 1.1 | Adicionada §1.1 com guia rápido de uso do Swagger UI (acesso, passo-a-passo, exemplos de `POST /webhook` e `GET /api/historico`, dicas comuns de erro). |
