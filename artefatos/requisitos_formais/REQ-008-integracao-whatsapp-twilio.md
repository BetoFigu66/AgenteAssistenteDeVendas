# REQ-008: Integração WhatsApp via Twilio (Webhook + Envio)

**Versão**: 1.0  
**Data**: 2026-04-16  
**Autor**: Kika (Analista de Requisitos)  
**Status**: Em Elaboração  
**Prioridade**: Alta  

---

## 1. Identificação do Requisito

**ID**: REQ-008  
**Tipo**: Funcional  
**Categoria**: Integração / Canal de Atendimento  
**Solicitante**: Necessidade do POC (Rita)  

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
- Canal de entrada/saída confiável para testes com a Rita
- Setup rápido para validação

---

## 4. Critérios de Aceite

### 4.1 Recebimento de Mensagens (Webhook)

- [ ] **REQ-008.1**: O sistema deve expor um endpoint HTTP (webhook) para receber eventos de mensagem do WhatsApp via Twilio

- [ ] **REQ-008.2**: Ao receber uma mensagem, o sistema deve extrair no mínimo:
  - Identificador do remetente (ex: número do WhatsApp)
  - Conteúdo da mensagem
  - Timestamp (quando fornecido)
  - Identificador da mensagem (quando fornecido)

- [ ] **REQ-008.3**: O webhook deve responder com status HTTP adequado em até 5 segundos

- [ ] **REQ-008.4**: O sistema deve ser capaz de associar mensagens a uma conversa (`conversa_id`) por cliente

### 4.2 Envio de Mensagens

- [ ] **REQ-008.5**: O sistema deve enviar mensagens de texto ao cliente via Twilio

- [ ] **REQ-008.6**: O sistema deve suportar envio de mensagens de transição para handoff (REQ-004)

- [ ] **REQ-008.7**: O sistema deve suportar envio de catálogos/arquivos quando solicitado (REQ-003), respeitando as limitações do canal

### 4.3 Idempotência e Duplicidade

- [ ] **REQ-008.8**: O sistema deve lidar com reentrega de eventos (mensagens duplicadas) sem processar duas vezes a mesma mensagem

- [ ] **REQ-008.9**: O sistema deve registrar o identificador da mensagem recebida para evitar reprocessamento

### 4.4 Segurança e Validação

- [ ] **REQ-008.10**: O webhook deve validar que a requisição veio da Twilio (validação de assinatura) ou usar medida equivalente de segurança

- [ ] **REQ-008.11**: Segredos de integração (ex: credenciais) não devem ser armazenados em código-fonte

### 4.5 Observabilidade e Registro

- [ ] **REQ-008.12**: Toda mensagem recebida e enviada deve ser registrada no histórico (REQ-005)

- [ ] **REQ-008.13**: Erros de envio/recebimento devem ser registrados como eventos

---

## 5. Regras de Negócio

- [ ] **REQ-008.14**: Se a conversa estiver em estado “em atendimento humano” (REQ-004), o sistema não deve enviar respostas automáticas

- [ ] **REQ-008.15**: Se ocorrer falha de envio via Twilio, o sistema deve:
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
| Mensagens duplicadas/reentrega | Média | Médio | Idempotência (REQ-008.8/REQ-008.9) |
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
| Idempotência (deduplicação) | 3h |
| Testes end-to-end com mensagens reais | 3h |
| **Total** | **16h** |

---

## 10. Histórico de Alterações

| Data | Versão | Alteração | Autor |
|------|--------|-----------|-------|
| 16/04/2026 | 1.0 | Criação inicial do requisito | Kika |

---

## 11. Aprovações

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| Analista de Requisitos | Kika | 16/04/2026 | [ ] |
| Cliente (Inforrel) | Rita | ____/____/____ | [ ] |
| Líder Técnico | Beto | ____/____/____ | [ ] |
