# RT-001 — Jornada: Novo cliente envia CNPJ e faz pergunta técnica

<!-- CLASSIFICACAO: SISTEMA-DEV -->

**Data de criação:** 2026-06-15
**Autor:** `[qa]` (Cascade)
**Tempo estimado:** ~15 min
**REQs cobertos:** REQ-001, REQ-002, REQ-003, REQ-005, REQ-008

---

## Pré-requisitos

- Backend e painel em execução.
- Contato sem histórico prévio no sistema.
- Base de conhecimento com ao menos um produto cadastrado.

---

## Convenções

| Símbolo | Significado |
|---------|-------------|
| ✅ | REQ validado por este passo |
| 🚧 | REQ ainda não implementado — passo confirma gap, não valida comportamento completo |
| **Status:** `[ ]` | Não executado |
| **Status:** `[OK]` | Passou |
| **Status:** `[FAIL]` | Falhou — registrar evidência em `artefatos/qa/evidencias/RT-001/` |
| **Status:** `[N/A]` | Impossível executar — anotar motivo |

---

## Passo 1 — Enviar saudação

**Resultado esperado:** a mensagem aparece no painel; o sistema responde de forma coerente com uma saudação, sem pedir CNPJ nem iniciar qualificação técnica imediatamente.

**Valida:** ✅ REQ-002.1 (classificação de saudação) · ✅ REQ-008.1 (webhook aceita mensagem) · ✅ REQ-005.1 (mensagem registrada)

**Status:** `[ ]`

---

## Passo 2 — Enviar CNPJ da empresa

**Resultado esperado:** o painel exibe, na negociação correspondente, a empresa identificada com razão social, situação cadastral e ao menos um endereço. O CNPJ é reconhecido no formato enviado.

**Valida:** ✅ REQ-001.1 (reconhecimento do formato CNPJ) · ✅ REQ-001.2 (validação do formato) · ✅ REQ-001.3 (consulta à Receita Federal e retorno de dados) · ✅ REQ-001.7 (persistência no perfil da empresa) · ✅ REQ-002.2 (extração de dados da mensagem) · ✅ REQ-005.1 (mensagem registrada)

**Status:** `[ ]`

---

## Passo 3 — Verificar vínculo da empresa com a negociação

**Resultado esperado:** ao abrir a negociação no painel, os dados da empresa aparecem como contexto associado.

**Valida:** ✅ REQ-001.5 (empresa disponibilizada para orçamento/negociação)

**Status:** `[ ]`

---

## Passo 4 — Enviar tipo de produto (ex.: relógio de ponto ou catraca)

**Resultado esperado:** a negociação no painel reflete o campo "tipo de produto" capturado. O sistema pergunta o **modelo** primeiro; em seguida, conforme o tipo de produto, pergunta dinamicamente os campos aplicáveis na ordem do catálogo:
- **Relógio de ponto**: modelo → software de ponto (se o cliente não tem nenhum software instalado, pergunta faixa de funcionários).
- **Catraca**: modelo → software de acesso →
  - Se o cliente **não tem nenhum software instalado**: pergunta interesse em sistema de controle de acesso na nuvem; se houver interesse, pergunta a **faixa de pessoas** e a **quantidade de equipamentos** (ambas obrigatórias); se não houver interesse, pergunta **apenas a quantidade** (obrigatória).
  - Se o cliente **já tem um software conhecido** (ex.: EVO, Pacto, SCA, ou citar franquias como Panobianco/Sky que tipicamente usam EVO): o sistema pergunta, **como alerta/orientação** (resposta opcional, não bloqueia o fluxo), se o cliente já verificou a homologação entre o modelo desejado e aquele software — reforçando a importância de checar isso antes da compra. **Além disso**, pergunta a **quantidade de equipamentos** (obrigatória).
  - Se o cliente já tem **outro software não reconhecido** (ou "não sei"): o sistema **também** exibe o alerta/orientação de homologação (opcional, não bloqueia) — reforço ainda mais relevante por não haver garantia prévia de compatibilidade. Pergunta a **quantidade de equipamentos** (obrigatória); a faixa de pessoas é opcional.

O sistema não repete perguntas já respondidas nem reinicia o fluxo.

**Valida:** ✅ REQ-002.2 (extração de entidades) · ✅ REQ-002.3 (estado dos campos capturado/pendente)

**Status:** `[ ]`

---

## Passo 5 — Verificar campos pendentes na negociação

**Resultado esperado:** o painel indica quais campos já foram coletados (CNPJ, modelo, software, quantidade/faixa, homologação) e quais ainda estão pendentes, refletindo a aplicabilidade dinâmica por tipo de produto (ex.: "quantidade" só aparece para catraca; "faixa de funcionários" só aparece quando não há software real informado).

**Valida:** ✅ REQ-002.3 (visibilidade do estado de qualificação)

**Status:** `[ ]`

---

## Passo 6 — Enviar pergunta técnica sobre produto

**Resultado esperado:** o sistema responde com conteúdo baseado na base de conhecimento. O modal de raciocínio (acessível pelo painel) exibe os trechos consultados e a resposta gerada.

**Valida:** ✅ REQ-003.2 (recuperação RAG) · ✅ REQ-003.3 (geração baseada em referências) · ✅ REQ-003.5 (auditoria da resposta) · ✅ REQ-005.6 (auditoria IA/RAG no painel)

**Status:** `[ ]`

---

## Passo 7 — Verificar histórico completo da conversa

**Resultado esperado:** o endpoint de histórico retorna todas as mensagens da sessão em ordem cronológica, com origem correta (cliente / sistema).

**Valida:** ✅ REQ-005.2 (mensagem do sistema registrada) · ✅ REQ-005.5 (consulta ao histórico por cliente)

**Status:** `[ ]`

---

## Passo 8 — Enviar o mesmo CNPJ por um segundo contato

**Resultado esperado:** os dados da empresa são os mesmos da consulta anterior, sem nova chamada à Receita Federal (uso de cache). Ambas as negociações exibem a mesma razão social e endereço.

**Valida:** ✅ REQ-001.7 (reuso da empresa já consultada) · ✅ REQ-002.10 (reaproveitamento de CNPJ validado)

**Status:** `[ ]`

---

## Passo 9 — Confirmar que agente não enviou mensagens reais ao WhatsApp

**Resultado esperado:** todas as respostas aparecem apenas no painel interno; nenhum envio outbound real foi realizado pelo sistema.

**Valida:** 🚧 REQ-008.5 (envio efetivo via Twilio — gap conhecido, não implementado)

**Status:** `[ ]`

---

## Passo 10 — Enviar mensagens sem sentido/ambíguas sem informar CNPJ (pergunta única, sem insistência)

**Contexto:** cliente novo/sem empresa vinculada envia mensagens **sem sentido/ambíguas** (texto que não é saudação, não pede orçamento, não é dúvida sobre produto — só "ruído"), forçando o classificador a devolver confiança baixa. O cliente nunca informa CNPJ/CPF.

**Exemplos de mensagens para o teste:**
- 1ª mensagem: `"aihwiuh o que eh isso pqoiwjeqwoi"`
- 2ª mensagem: `"nao intendo nada disso blablabla"`

**Resultado esperado:**
1. Na 1ª mensagem sem sentido, o sistema pergunta o CNPJ (`PERGUNTAR_CNPJ`) — a identificação fiscal tem prioridade sobre o fallback de baixa confiança.
2. Na 2ª mensagem sem sentido (CNPJ ainda não informado), o sistema **não insiste** no CNPJ — marca a pergunta como "recusada" internamente e responde com o fallback padrão (`NAO_ENTENDI`).
3. Somente na **Fase Finalizando** (quando o cliente já demonstrou intenção clara de orçamento) o CNPJ/CPF volta a ser cobrado como campo obrigatório para concluir a qualificação.

**Valida:** ✅ REQ-002.1B (identificação fiscal não bloqueia demais fluxos) · ✅ REQ-002.3 (estado do campo `documento_fiscal_pendente`) · ✅ REQ-002.10 (não repetir pedido de documento sem necessidade)

**Status:** `[ ]`

---

## Resumo do roteiro

| Passo | REQs | Status |
|-------|------|--------|
| 1 — Saudação | REQ-002.1, REQ-008.1, REQ-005.1 | `[ ]` |
| 2 — CNPJ | REQ-001.1, REQ-001.2, REQ-001.3, REQ-001.7, REQ-002.2, REQ-005.1 | `[ ]` |
| 3 — Vínculo empresa/negociação | REQ-001.5 | `[ ]` |
| 4 — Tipo de produto e perguntas dinâmicas | REQ-002.2, REQ-002.3 | `[ ]` |
| 5 — Campos pendentes | REQ-002.3 | `[ ]` |
| 6 — Pergunta técnica (RAG) | REQ-003.2, REQ-003.3, REQ-003.5, REQ-005.6 | `[ ]` |
| 7 — Histórico | REQ-005.2, REQ-005.5 | `[ ]` |
| 8 — Reuso de CNPJ | REQ-001.7, REQ-002.10 | `[ ]` |
| 9 — Gap Twilio 🚧 | REQ-008.5 | `[ ]` |
| 10 — Mensagens sem sentido + CNPJ único, sem insistência | REQ-002.1B, REQ-002.3, REQ-002.10 | `[ ]` |

---

## Histórico

| Data | Versão | Mudança |
|------|--------|---------|
| 2026-06-15 | 1.0 | Criação inicial. |
| 2026-07-28 | 1.1 | Passo 4/5 atualizados para refletir perguntas dinâmicas por tipo de produto (modelo, software de ponto/acesso, interesse em nuvem, homologação, quantidade). Adicionado Passo 10 (CNPJ perguntado uma única vez, sem insistência, obrigatório só na Finalizando). |
| 2026-07-28 | 1.2 | Passo 4 (catraca) corrigido conforme REQ-002.14C/15 v1.36: pergunta de homologação é alerta/orientação opcional (não bloqueia o fluxo), feita apenas quando o software é reconhecido (EVO/Pacto/SCA/franquias como Panobianco/Sky); quantidade é sempre obrigatória quando há software instalado; faixa de pessoas só entra no cenário sem software + interesse em nuvem. |
| 2026-07-28 | 1.3 | Passo 4 (catraca) ajustado conforme REQ-002.15 v1.37: o alerta/orientação de homologação passa a ser exibido também quando o software existente não é reconhecido no catálogo (opcional, não bloqueante). |
| 2026-07-28 | 1.4 | Passo 10 esclarecido: "pergunta confusa" renomeado para "mensagens sem sentido/ambíguas", com exemplos concretos de texto usados para forçar confiança baixa no classificador (sem relação com dúvidas reais do cliente). |
