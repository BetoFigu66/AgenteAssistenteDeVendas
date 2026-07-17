# RT-012 — Jornada: MVP Continuidade (relógio de ponto — Esclarecendo → Finalizando → Em orçamentação)

<!-- CLASSIFICACAO: SISTEMA-DEV -->

**Data de criação:** 2026-07-13
**Autor:** `[qa]` (Claude Code)
**Tempo estimado:** ~25 min
**REQs cobertos:** REQ-002.1 (categorias/intenção), REQ-002.1B/C (transição de fase), REQ-002.17 (dúvida durante coleta), REQ-002.21 (validação de modelo), REQ-004 (handoff Criando Orçamento), REQ-010 (painel — exibir fase e campos)
**Status geral:** ✅ Implementado (Fases A-H do `docs/plano_implementacao_mvp_continuidade_2026-07.md`) — aguardando execução manual no painel

---

## Pré-requisitos

- Backend e painel em execução (`docker-compose up` ou `uvicorn` + `npm run dev`).
- Escopo do MVP: **um único produto** (Relógio de Ponto) — mensagens sobre catracas ou outros produtos não seguem este roteiro.
- **Catálogo `produtos`/`tipos_produto` está vazio neste ambiente por padrão.** Isso muda o resultado esperado do Passo 4:
  - **Sem seed**: o sistema nunca resolve `modelo_produto` para uma linha real do catálogo → após 2 tentativas, escala para atendimento humano (`modo_operacao = humano`). Esse é o comportamento hoje em produção/dev sem dados semeados — **também é um cenário válido a testar** (ver Passo 4b).
  - **Com seed**: para testar o caminho feliz completo (Passo 4a), inserir manualmente uma linha em `tipos_produto` (descrição contendo "ponto") e uma em `produtos` (descrição contendo o termo do leitor, ex.: "biométrico"), vinculada ao `tipo_produto_id` acima. Ver exemplo de SQL no Passo 4a.
- Usar um telefone de teste que nunca tenha conversado antes (evita colidir com atendimentos reais).
- Ter acesso a `psql`/DBeaver para inspecionar `atendimentos.fase`, `atendimentos.modo_operacao` e `atendimento_infos`.

---

## Convenções

| Símbolo | Significado |
|---------|-------------|
| ✅ | REQ validado por este passo |
| 🚧 | REQ ainda não implementado |
| **Status:** `[ ]` | Não executado |
| **Status:** `[OK]` | Passou |
| **Status:** `[FAIL]` | Falhou — registrar evidência em `artefatos/qa/evidencias/RT-012/` |
| **Status:** `[N/A]` | Impossível executar — anotar motivo |

---

## Passo 1 — Dúvida sobre produto antes de qualquer intenção comercial (Esclarecendo)

**Ação:** Com um telefone novo, enviar "Vocês têm relógio de ponto biométrico?".

**Valida:**
✅ REQ-002.1 categoria 3 (dúvida produto/preço/fora-contexto) respondida via Q&A/RAG, sem exigir CNPJ/CPF antes.

**Verificação:**
- Sistema responde sobre o produto (via par Q&A ou RAG) e **não** pede CNPJ.
- Banco: `atendimentos.fase = esclarecendo` para o atendimento anônimo criado.
- Painel (Acompanhamento ou chat): badge de fase mostra **"Esclarecendo"** (cinza).

**Status:** `[ ]`

---

## Passo 2 — Segunda dúvida, ainda em Esclarecendo

**Ação:** Enviar "Qual a diferença pro facial?".

**Valida:**
✅ REQ-002.1 (permanece em Esclarecendo enquanto só houver dúvida, sem intenção de orçamento).

**Verificação:**
- Resposta via base de conhecimento.
- `atendimentos.fase` continua `esclarecendo`.

**Status:** `[ ]`

---

## Passo 3 — Intenção de orçamento transita a fase imediatamente

**Ação:** Enviar "Quero orçamento".

**Valida:**
✅ REQ-002.1B/C (categoria 1 → transição imediata para Finalizando, **sem** esperar modelo/software confirmados antes).

**Verificação:**
- Sistema envia mensagem de transição ("Ótimo! Vou precisar de algumas informações...") seguida da primeira pergunta pendente (modelo, se o tipo de produto já foi mencionado no Passo 1; ou "que tipo de equipamento você precisa?" caso contrário).
- Banco: `atendimentos.fase` virou `finalizando`.
- Painel: badge de fase muda para **"Finalizando"** (azul/secundária) imediatamente, sem recarregar a página manualmente (conferir se o painel atualiza ao reabrir o detalhe do atendimento).

**Status:** `[ ]`

---

## Passo 4a — Responder ao modelo (caminho feliz — requer catálogo semeado)

**Pré-requisito:** Seed manual do catálogo (rodar antes deste passo):

```sql
INSERT INTO tipos_produto (descricao, ativo, created_at)
VALUES ('Relógio de Ponto (QA)', true, now());

INSERT INTO produtos (tipo_produto_id, codigo, descricao, preco_tabela, unidade, ativo, created_at, updated_at)
SELECT id, 'QA-REP-001', 'REP Biométrico QA', 0, 'UN', true, now(), now()
FROM tipos_produto WHERE descricao = 'Relógio de Ponto (QA)';
```

**Ação:** Responder "Biométrico" à pergunta de modelo.

**Valida:**
✅ REQ-002.21 (modelo resolve para uma linha real do catálogo via `tipo_leitor_mencionado`).

**Verificação:**
- Sistema resolve o modelo (sem pedir de novo) e pergunta o **software de ponto**.
- Banco: `itens_atendimento.produto_id` preenchido com o id do produto semeado.
- `atendimentos.modo_operacao` continua `agente` (não escalou).

**Status:** `[ ]`

**Limpeza:** ao final do roteiro, remover as linhas de seed (`DELETE FROM produtos WHERE codigo='QA-REP-001'; DELETE FROM tipos_produto WHERE descricao='Relógio de Ponto (QA)';`).

---

## Passo 4b — Responder ao modelo sem catálogo semeado (comportamento padrão hoje)

**Pré-requisito:** Catálogo **sem** seed (comportamento padrão do ambiente).

**Ação:** Responder "Biométrico" duas vezes seguidas (simulando duas tentativas de esclarecimento).

**Valida:**
✅ REQ-002.21 (sem correspondência após 2 tentativas → escalar para atendente, nunca aceitar texto livre como modelo).

**Verificação:**
- 1ª resposta: sistema não resolve, mas também não escala ainda (reapresenta pergunta relacionada, ou responde dúvida caso a frase tenha sido classificada como categoria 3 — ex.: "biométrico" bate na regra de `perguntar_produto`).
- 2ª resposta: `atendimentos.modo_operacao` vira `humano`; sistema envia a mensagem de escalonamento ("Vou passar sua solicitação para um de nossos atendentes...").
- Painel: badge de modo muda de "AGENTE" para "HUMANO"; nenhuma nova resposta automática é gerada a partir daqui (conferir enviando mais uma mensagem de teste e confirmando que não há resposta automática).

**Status:** `[ ]`

---

## Passo 5 — Software já informado na mesma mensagem que pede orçamento (mensagem composta)

**Pré-requisito:** Repetir a partir do Passo 3 com um telefone novo (não reaproveitar o do Passo 4).

**Ação:** Enviar diretamente "Quero orçamento de relógio de ponto, já uso o Domínio".

**Valida:**
✅ REQ-002.1C (a `Pergunta` de um campo reconhece a resposta na mesma mensagem que dispara a transição — não é preciso esperar o próximo turno).

**Verificação:**
- `atendimento_infos` já tem `software_controle_ponto = Domínio` registrado no mesmo turno da transição.
- Sistema pula direto para perguntar o modelo (não pergunta software de novo).
- Painel (H2): tabela "Informações coletadas" mostra a linha "Software de ponto" com pill **verde "Capturado"** (não "Pendente").

**Status:** `[ ]`

---

## Passo 6 — Dúvida no meio da coleta (retomada)

**Pré-requisito:** Atendimento em Finalizando, aguardando alguma pergunta pendente (ex.: acabou de perguntar sobre software, ainda não respondida).

**Ação:** Enviar uma dúvida fora do fluxo, ex.: "Vocês têm catraca também?" ou "Quanto custa?".

**Valida:**
✅ REQ-002.17 (dúvida durante Finalizando não perde o contexto da pergunta pendente).

**Verificação:**
- Sistema responde a dúvida (via Q&A/RAG) **e** reapresenta a última pergunta pendente, prefixada por "Voltando ao orçamento: ...".
- Banco: `atendimento_infos.tipos_produto` continua `relogio_ponto` (a dúvida sobre catraca não deve ter sobrescrito o tipo de produto do atendimento).
- `atendimentos.fase` continua `finalizando`.

**Status:** `[ ]`

---

## Passo 7 — Resumo e confirmação (handoff para Criando Orçamento)

**Pré-requisito:** Modelo resolvido (Passo 4a) ou escalado (Passo 4b — nesse caso este passo não se aplica, pois o atendimento já está em modo humano; usar um atendimento à parte com modelo resolvido via seed).

**Ação:**
1. Responder as perguntas pendentes restantes (software e, se aplicável, faixa de funcionários) até tudo estar capturado.
2. Observar a mensagem de **resumo** enviada pelo sistema (deve listar modelo, software e faixa quando aplicável, e perguntar se pode encaminhar).
3. Responder "Sim" à pergunta de confirmação.

**Valida:**
✅ REQ-004 (handoff mínimo para o time humano preparar o orçamento de verdade).

**Verificação:**
- O resumo só é apresentado quando não há mais nada pendente — conferir que a mensagem imediatamente anterior ao "Sim" foi de fato o resumo (não uma pergunta).
- Após o "Sim": `atendimentos.fase` vira `em_orcamentacao`; `atendimentos.modo_operacao` vira `humano`.
- Sistema envia "Recebi suas informações. Nossa equipe vai preparar o orçamento e retorna em breve."
- Painel: badge de fase muda para **"Em orçamentação"** (cor de destaque/laranja).
- Enviar mais uma mensagem de teste após a confirmação e conferir que **não** há resposta automática (modo humano já suprime o agente).

**Status:** `[ ]`

---

## Passo 8 — Conferência visual no painel (H1/H2)

**Ação:** Com o atendimento do Passo 5 ou 7 aberto no painel (aba Chat → clicar no atendimento na faixa `ConversaInfo`, e também na aba Acompanhamento), conferir:

**Valida:**
✅ REQ-010 (fase e campos coletados visíveis no painel administrativo).

**Verificação:**
- Badge de fase aparece em **3 lugares**: faixa compacta acima do chat (`ConversaInfo`), lista de atendimentos da aba Acompanhamento, e cabeçalho do detalhe do atendimento (aba Acompanhamento e modal de detalhes do chat).
- Cores diferentes por fase: Esclarecendo (cinza), Finalizando (azul), Em orçamentação (laranja/destaque) — conferir que não ficam todas iguais.
- Tabela "Informações coletadas" (modal de detalhes) mostra os rótulos amigáveis (ex.: "Software de ponto", não `software_controle_ponto`) e a pill de status (verde "Capturado" / amarelo "Pendente") para cada linha.

**Status:** `[ ]`

---

## Resultado esperado ao final

| Cenário | Comportamento esperado |
|---------|------------------------|
| Dúvida antes de orçamento | Responde via Q&A/RAG, sem pedir CNPJ, permanece Esclarecendo |
| Intenção de orçamento | Transita para Finalizando imediatamente, pergunta o primeiro campo pendente |
| Modelo com catálogo semeado | Resolve para linha real, segue para próximo campo |
| Modelo sem catálogo (2 tentativas) | Escala para atendimento humano, nunca aceita texto livre |
| Mensagem composta (orçamento + resposta) | Captura o campo no mesmo turno, não repete a pergunta |
| Dúvida durante a coleta | Responde a dúvida e retoma a pergunta pendente, sem perder progresso nem trocar o tipo de produto |
| Resumo + confirmação | Só conclui após um resumo de fato apresentado; transita para Em orçamentação e escala para humano |
| Painel (fase + campos) | Badge de fase visível e colorida em 3 pontos da UI; tabela de campos com rótulos amigáveis e pills de status |

---

## Evidências

Salvar em `artefatos/qa/evidencias/RT-012/`:
- Screenshots dos badges de fase nos 3 pontos da UI (Passo 8), um por cor/fase.
- Screenshot da tabela "Informações coletadas" com pills verde/amarelo.
- Output do `SELECT fase, modo_operacao FROM atendimentos WHERE id = ...` em cada transição (Passos 3, 4b, 7).
- Conteúdo completo da conversa (Passos 1-7) via export do painel ou histórico da API (`GET /api/historico/{telefone}`).
