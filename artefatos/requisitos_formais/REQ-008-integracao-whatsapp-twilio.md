# REQ-008: Integração WhatsApp via Twilio (Webhook + Envio)

<!-- CLASSIFICACAO: SISTEMA-CAIXAPRETA -->
<!-- CLASSIFICACAO: IA -->

**Versão**: 1.4  
**Data**: 2026-04-16  
**Autor**: Kika (Analista de Requisitos)  
**Status**: Em Elaboração  
**Prioridade**: Alta  

---

## 1. Identificação do Requisito

**ID**: REQ-008  
**Tipo**: Funcional  
**Categoria**: Integração / Canal de Atendimento  
**Solicitante**: Necessidade do POC (vendedor)  

---

## 2. Descrição

O sistema deve integrar com WhatsApp utilizando a infraestrutura da **Twilio**, permitindo:

- Receber mensagens do cliente via webhook
- Processar a mensagem e decidir a ação (REQ-002, REQ-003, REQ-004, REQ-007)
- Enviar respostas para o cliente via Twilio
- Registrar mensagens e eventos (REQ-005)

---

## 3. Justificativa de Negócio

**Problema/necessidade**:
- Sem integração com WhatsApp, o POC não pode operar com clientes reais

**Benefício Esperado**:
- Canal de entrada/saída confiável para testes com o vendedor
- Setup rápido para validação

---

## 4. Critérios de Aceite

### 4.1 Recebimento de Mensagens (Webhook)

- [ ] **REQ-008.1 — Webhook de recebimento de mensagens**: O sistema deve expor um endpoint HTTP (webhook) para receber eventos de mensagem do WhatsApp via Twilio

- [ ] **REQ-008.2 — Extração de campos mínimos da mensagem recebida**: Ao receber uma mensagem, o sistema deve extrair no mínimo:
  - Identificador do remetente (ex: número do WhatsApp)
  - Conteúdo da mensagem
  - Timestamp (quando fornecido)
  - Identificador da mensagem (quando fornecido)

- [ ] **REQ-008.3 — Tempo de resposta do webhook**: O webhook deve responder com status HTTP adequado em até 5 segundos

- [ ] **REQ-008.4 — Associação da mensagem à conversa do cliente**: O sistema deve ser capaz de associar mensagens a uma conversa (`conversa_id`) por cliente

### 4.2 Envio de Mensagens

- [ ] **REQ-008.5 — Envio de mensagens de texto ao cliente**: O sistema deve enviar mensagens de texto ao cliente via Twilio

- [ ] **REQ-008.6 — Envio de mensagens de transição para handoff**: O sistema deve suportar envio de mensagens de transição para handoff (REQ-004)

- [ ] **REQ-008.7 — Suporte do canal Twilio para envio de links e arquivos**: O canal Twilio deve suportar o envio de mensagens contendo links públicos e, quando aplicável, anexos (arquivos), respeitando as limitações do WhatsApp. Esta capacidade é consumida pelo REQ-003.11 (envio de catálogo) e por outros fluxos que precisem entregar mídia/links ao cliente. Este requisito cobre apenas a **capacidade técnica** do canal; a regra de negócio (qual catálogo, quando, como registrar) é do REQ-003.11.

### 4.3 Deduplicação de Mensagens

- [ ] **REQ-008.8 — Identificar e descartar duplicatas de mensagens antes de processar**: O sistema deve lidar com reentrega de eventos (mensagens duplicadas) sem processar duas vezes a mesma mensagem

- [ ] **REQ-008.9 — Registro do identificador para deduplicação**: O sistema deve registrar o identificador da mensagem recebida para evitar reprocessamento

### 4.4 Segurança e Validação

- [ ] **REQ-008.10 — Validação da origem da requisição (assinatura Twilio)**: O webhook deve validar que a requisição veio da Twilio (validação de assinatura) ou usar medida equivalente de segurança

- [ ] **REQ-008.11 — Proteção de segredos de integração**: Segredos de integração (ex: credenciais) não devem ser armazenados em código-fonte

### 4.5 Observabilidade e Registro

- [ ] **REQ-008.12 — Registro de mensagens recebidas e enviadas no histórico**: Toda mensagem recebida e enviada deve ser registrada no histórico (REQ-005)

- [ ] **REQ-008.13 — Registro de erros de envio e recebimento**: Erros de envio/recebimento devem ser registrados como eventos

---

## 5. Regras de Negócio

- [ ] **REQ-008.14 — Respeito ao estado "em atendimento humano" no canal de envio**: O módulo de envio via Twilio deve respeitar a suspensão de respostas automáticas definida no **REQ-004.10**: enquanto a conversa estiver em estado `Em atendimento humano` (REQ-004.4), o canal não deve disparar mensagens automáticas (REQ-002 ou REQ-003). Este requisito **não cria regra nova** — apenas afirma que a camada de integração do REQ-008 é o ponto onde a regra do REQ-004.10 é efetivamente aplicada.

- [ ] **REQ-008.15 — Tratamento de falhas de envio via Twilio**: Se ocorrer falha de envio via Twilio, o sistema deve:
  - Registrar o erro
  - Tentar novamente conforme política simples (a definir) ou escalar para humano

---

## 6. Limitações Aceitas no POC

- [ ] Usar Twilio Sandbox para desenvolvimento/testes
- [ ] Sem múltiplos números/roteamento no POC

---

## 7. Dependências

### 7.1 Dependências Técnicas
- Conta Twilio configurada para WhatsApp
- Endpoint público para o webhook (ex: ngrok)
- Banco de dados para histórico e idempotência (REQ-005)

### 7.2 Dependências de Negócio
- Definir número/instância do WhatsApp no Twilio

---

## 8. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|------|---------------|---------|----------|
| Mensagens duplicadas/reentrega | Média | Médio | Deduplicação (REQ-008.8/REQ-008.9) |
| Problemas de configuração do webhook | Média | Médio | Checklist de setup + testes com sandbox |
| Custos por mensagem em produção | Média | Médio | Manter POC limitado e monitorar volume |

---

## 9. Estimativas

| Atividade | Horas |
|-----------|-------|
| Configuração Twilio (Sandbox/WhatsApp) | 3h |
| Implementação webhook + parsing | 3h |
| Implementação envio de mensagens | 2h |
| Validação de assinatura e segredos | 2h |
| Deduplicação de mensagens | 3h |
| Testes end-to-end com mensagens reais | 3h |
| **Total** | **16h** |

---

## 10. Histórico de Alterações

| Data | Versão | Alteração | Autor |
|------|--------|-----------|-------|
| 16/04/2026 | 1.0 | Criação inicial do requisito | Kika |
| 12/05/2026 | 1.1 | Adição de títulos descritivos a todos os requisitos do documento | Kika |
| 12/05/2026 | 1.2 | Substituição do termo "idempotência" por "deduplicação" no título da seção 4.3, no REQ-008.8, na tabela de riscos e na estimativa, por ser mais preciso para o comportamento descrito (descartar duplicatas via `message_id`) | Kika |
| 12/05/2026 | 1.3 | Reescrita do REQ-008.7 para deixar claro que se trata da **capacidade técnica** do canal Twilio (envio de links e arquivos), separando-a explicitamente da regra de negócio do envio de catálogo (REQ-003.11) e eliminando aparente sobreposição entre os dois requisitos | Kika |
| 12/05/2026 | 1.4 | Reescrita do REQ-008.14 como **referência cruzada** ao REQ-004.10 (fonte única da regra), eliminando duplicação entre os dois requisitos e deixando claro que o módulo de envio é apenas o ponto de aplicação da regra | Kika |

---

## 11. Aprovações

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| Analista de Requisitos | Kika | 16/04/2026 | [ ] |
| Cliente (Inforrel) | Rita | ____/____/____ | [ ] |
| Líder Técnico | Beto | ____/____/____ | [ ] |
