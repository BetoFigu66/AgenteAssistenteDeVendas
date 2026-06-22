# Proposta de curadoria — Report #11

**Pacote:** `AnotacoesPessoais/Beto/Curadoria/report_011_pacote_analise.yaml`  
**Gerado em:** 2026-06-19  
**Agente:** `[curador_conhecimento]`

---

## Diagnóstico

- **Causa provável:** `fluxo_errado` (roteamento REQ-002), **não** lacuna de conteúdo RAG/Q&A
- **Confiança:** alta
- **Justificativa:**

  O classificador acertou: intenção `pedir_orcamento` (confiança 0,75, origem regra) e extraiu o nome **Kika** em `entidades.nomes`. Mesmo assim o processador usou o template `SAUDACAO_NOVO_CONTATO`, pedindo nome, CNPJ/CPF e data de nascimento de novo.

  No código (`backend/services/processador.py`, ~L419–423), **qualquer** mensagem de contato com `status_identificacao = novo` retorna `SAUDACAO_NOVO_CONTATO` **antes** de avaliar a intenção. O bloco `PEDIR_ORCAMENTO` (que levaria a `PEDIR_TIPO_PRODUTO`) nunca é alcançado para telefone novo.

  O RAG não foi acionado (`rag_utilizada: false`) — comportamento esperado para essa rota. Os scores baixos de Q&A/RAG no pacote são **ruído** neste caso; mesmo o par `qa:geral:004` (“Como faço para solicitar um orçamento?”, score 0,65) não seria usado porque o fluxo morre no gate de identificação.

  O feedback do report confirma dois defeitos de produto/fluxo:
  1. Ignorar nome já informado na mesma mensagem.
  2. Pedir data de nascimento na saudação inicial (antes da hora no fluxo PF).

- **Agente dono da correção:** `[implementador]` (fluxo + template). `[curador_conhecimento]` não resolve sozinho.

---

## Ações sugeridas

### 1. Corrigir roteamento para contato novo com intenção clara — `[implementador]`

- **Tipo:** `corrigir_fluxo`
- **Prioridade:** alta
- **Detalhes:**

  Quando `status_identificacao == NOVO` **e** a intenção for `pedir_orcamento` (ou outra intenção de compra/qualificação), **não** devolver `SAUDACAO_NOVO_CONTATO` genérico. Sugestão de comportamento:

  1. Se `entidades.nomes` não vazio → persistir nome no contato (criar contato anônimo se necessário, alinhado a REQ-002.1B).
  2. Responder com saudação **personalizada** (`SAUDACAO_COM_NOME` ou variante) + próximo passo do fluxo de orçamento (`PEDIR_TIPO_PRODUTO` ou qualificação mínima).
  3. Só usar `SAUDACAO_NOVO_CONTATO` quando a mensagem for realmente ambígua (ex.: só “oi”) **sem** intenção de compra nem nome.

  **Arquivo principal:** `backend/services/processador.py` (`_decidir_resposta`).

### 2. Ajustar template de saudação inicial — `[implementador]`

- **Tipo:** `ajustar_template`
- **Prioridade:** media
- **Detalhes:**

  O template `SAUDACAO_NOVO_CONTATO` pede nome **e** data de nascimento na primeira interação. Para PF, a data de nascimento só deve ser solicitada **depois** do CPF (já existe `PERGUNTAR_DATA_NASCIMENTO` para isso — ver mensagens 115–116 da conversa).

  Proposta de texto revisado (quando ainda for necessário pedir identificação):

  ```
  Olá! 👋 Sou o assistente da Inforrel.
  Para te atender melhor, poderia me informar seu nome e o CNPJ da sua empresa, ou seu CPF?
  ```

  Remover “data de nascimento” desta etapa. Corrigir também o espaço faltando após a vírgula (“nome,CNPJ” → “nome e CNPJ” ou “nome, CNPJ”).

  **Arquivo:** `backend/services/respostas/templates.py`

### 3. Não criar par Q&A para este caso — `[curador_conhecimento]`

- **Tipo:** `nao_aplicavel`
- **Prioridade:** baixa
- **Detalhes:**

  Um par Q&A do tipo “Eu sou a Kika e gostaria de fazer um orçamento” **não** corrige o bug, porque a mensagem nunca chega à camada Q&A. Reavaliar Q&A só **depois** do fix de fluxo, se ainda houver resposta inadequada na etapa de qualificação.

### 4. Não enriquecer `docs/FoldersProdutos/` — `[curador_conhecimento]`

- **Tipo:** `nao_aplicavel`
- **Prioridade:** baixa
- **Detalhes:**

  Os documentos sugeridos no pacote (catracas, etc.) são irrelevantes para este report — artefato do diagnóstico RAG em mensagem de orçamento. Nenhuma edição em `docs/FoldersProdutos/*.txt` necessária.

### 5. Não ajustar limiares Q&A/RAG — `[curador_conhecimento]`

- **Tipo:** `nao_aplicavel`
- **Prioridade:** baixa
- **Detalhes:**

  Baixar `qa_score_minimo` de 0,80 para capturar o par 0,65 **não** resolveria este report e poderia degradar precisão em outros casos.

---

## Arquivos a editar

| Arquivo | Responsável |
|---------|-------------|
| `backend/services/processador.py` | `[implementador]` |
| `backend/services/respostas/templates.py` | `[implementador]` |
| `docs/FoldersProdutos/*` | — (não aplicável) |

---

## Validação sugerida

Após o fix de fluxo, repetir a conversa com telefone novo:

1. **Entrada:** `Eu sou a Kika e gostaria de fazer um orçamento`
2. **Esperado:**
   - Template diferente de `SAUDACAO_NOVO_CONTATO`
   - Resposta usa o nome “Kika” (ex.: “Olá, Kika! …”)
   - Não pede data de nascimento nesta etapa
   - Avança para qualificação de orçamento (tipo de produto, CNPJ/CPF conforme regra PF/PJ)
3. **Auditoria:** `ProcessamentoMensagem.template_usado` ≠ `SAUDACAO_NOVO_CONTATO`; `entidades.nomes` contém “Kika”.

Cenário de regressão adicional:

- **Entrada:** `oi` (telefone novo)
- **Esperado:** ainda pode usar saudação genérica pedindo identificação (sem data de nascimento).

---

## Encaminhamento

| Item | Destino |
|------|---------|
| Fix de roteamento NOVO + pedir_orcamento | `[implementador]` |
| Revisão de template inicial | `[implementador]` |
| Report #11 após fix | Mover para `resolvido` com link ao commit/PR |

---

## Nota para o pacote de análise

O campo `meta.agente_sugerido: curador_conhecimento` está correto para triagem inicial, mas este report exemplifica um caso em que a **hipótese automática** (score Q&A/RAG abaixo do limiar) induz ao caminho errado. Vale evoluir o pacote para detectar: `template_usado == SAUDACAO_NOVO_CONTATO` + `intencao == pedir_orcamento` + `entidades.nomes` preenchido → sugerir `implementador` em `hipoteses_automaticas`.
