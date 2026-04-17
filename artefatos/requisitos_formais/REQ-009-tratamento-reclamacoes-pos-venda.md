# REQ-009: Tratamento de Reclamações Pós-venda (Atraso/Suporte) com Identificação de Orçamento/Pedido

**Versão**: 1.0  
**Data**: 2026-04-17  
**Autor**: Kika (Analista de Requisitos)  
**Status**: Em Elaboração  
**Prioridade**: Alta  

---

## 1. Identificação do Requisito

**ID**: REQ-009  
**Tipo**: Funcional  
**Categoria**: Pós-venda / Reclamações / Suporte  
**Solicitante**: Operação (Rita)  

---

## 2. Descrição

O sistema deve identificar e tratar mensagens de pós-venda relacionadas a reclamações, especialmente sobre **atraso de entrega**, **falta de prazo**, **produto com problema** ou **pedido de suporte**. Ao detectar esse tipo de mensagem, o sistema deve:

1. Identificar o número/contato do WhatsApp do cliente
2. Buscar orçamentos e/ou registros relacionados ao cliente (via telefone e/ou CNPJ) para tentar identificar qual orçamento/pedido está relacionado ao assunto
3. Apresentar ao cliente um resumo para confirmação (ex: empresa, produto, data do orçamento) antes de prosseguir
4. Após confirmação, escalar para a Rita com a reclamação e dados do orçamento/pedido

---

## 3. Justificativa de Negócio

**Problema Atual**:
- Reclamações de pós-venda (prazo, entrega, suporte) exigem resposta rápida e humana
- Sem identificação do orçamento/pedido, a Rita perde tempo pedindo dados e buscando histórico

**Benefício Esperado**:
- Reduzir tempo de triagem e entendimento do problema
- Encaminhar para a Rita com contexto completo
- Evitar resposta automática inadequada em situações críticas

---

## 4. Critérios de Aceite

### 4.1 Detecção de Reclamação/Pós-venda

- [ ] **REQ-009.1**: O sistema deve detectar mensagens de pós-venda, com foco inicial em:
  - atraso/prazo de entrega
  - falta de prazo
  - produto não funciona / defeito
  - suporte/instalação/ajuda

- [ ] **REQ-009.2**: Ao detectar pós-venda, o sistema deve classificar a conversa como crítica (integração com REQ-007) e iniciar tratamento de reclamação

### 4.2 Identificação de Orçamento/Pedido Relacionado

- [ ] **REQ-009.3**: O sistema deve identificar o cliente a partir do número WhatsApp (`cliente_id`/telefone) e buscar orçamentos associados (REQ-006)

- [ ] **REQ-009.4**: Quando houver mais de um orçamento associado ao mesmo número, o sistema deve selecionar o mais provável (por recência) e pedir confirmação do cliente

- [ ] **REQ-009.5**: Quando não houver orçamento associado ao número, o sistema deve solicitar dados mínimos para localizar:
  - CNPJ (preferencial) ou
  - e-mail usado no orçamento (se aplicável)

### 4.3 Confirmação com o Cliente

- [ ] **REQ-009.6**: Antes de escalonar, o sistema deve apresentar um resumo do orçamento/pedido identificado para o cliente confirmar, contendo quando possível:
  - empresa (razão social)
  - produto(s)
  - data aproximada do orçamento

- [ ] **REQ-009.7**: O sistema deve permitir que o cliente diga que não é aquele orçamento e, nesse caso, tentar outra opção (se existir) ou pedir mais dados

### 4.4 Escalonamento para a Rita

- [ ] **REQ-009.8**: Após confirmação do cliente, o sistema deve escalar imediatamente para a Rita (REQ-004), enviando:
  - identificação do cliente (telefone)
  - `orcamento_id` (se existir)
  - dados do orçamento (produto, empresa, data)
  - texto da reclamação do cliente
  - categoria da reclamação (prazo/atraso, suporte, não funciona, etc.)

- [ ] **REQ-009.9**: Após o escalonamento, o sistema deve entrar em estado “em atendimento humano” (REQ-004) para não continuar respondendo automaticamente

### 4.5 Registro e Auditoria

- [ ] **REQ-009.10**: O sistema deve registrar como eventos (REQ-005):
  - detecção de pós-venda
  - orçamento/pedido sugerido
  - confirmação (sim/não)
  - escalonamento e resumo enviado ao humano

---

## 5. Fluxo de Conversa (exemplo)

```
Cliente: "Comprei com vocês e até agora não chegou. Qual o prazo?"

Sistema: "Entendi. Vou te ajudar com isso.
Encontrei um orçamento recente para confirmar se é sobre ele:
- Empresa: ACME LTDA
- Produto: Catraca pedestal
- Data do orçamento: 05/04

É sobre esse pedido/orçamento que você está falando? (S/N)"

Cliente: "Sim"

Sistema: "Certo. Vou acionar um atendente para te ajudar e já te retorno."

(Sistema notifica Rita com os dados + reclamação)
```

---

## 6. Integração com Requisitos Existentes

- **REQ-004**: escalonamento para humano e estado “em atendimento humano”
- **REQ-005**: registro de eventos e histórico
- **REQ-006**: vínculo conversa/cliente ↔ orçamentos (`orcamento_id`)
- **REQ-007**: classificação de conversa crítica por insatisfação

---

## 7. Limitações Aceitas no POC

- [ ] Identificação do “pedido” pode se basear apenas em `orcamento_id` (a compra real pode não estar integrada ao ERP)
- [ ] Se o cliente usar número diferente do que foi usado no orçamento, pode ser necessário pedir CNPJ para localizar

---

## 8. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|------|---------------|---------|----------|
| Vários orçamentos para o mesmo número | Média | Médio | Confirmar com o cliente (REQ-009.6/REQ-009.7) |
| Cliente não tem o mesmo número do orçamento | Média | Médio | Pedir CNPJ e localizar por CNPJ |
| Resposta automática inadequada em reclamação | Baixa | Alto | Escalonar rápido + mensagem empática curta |

---

## 9. Estimativas

| Atividade | Horas |
|-----------|-------|
| Definir sinais/categorias de reclamação | 2h |
| Implementar busca de orçamentos por telefone/CNPJ | 4h |
| Implementar confirmação com o cliente | 3h |
| Integrar escalonamento (REQ-004) | 2h |
| Registro de eventos (REQ-005) | 2h |
| Testes com cenários reais | 4h |
| **Total** | **17h** |

---

## 10. Histórico de Alterações

| Data | Versão | Alteração | Autor |
|------|--------|-----------|-------|
| 17/04/2026 | 1.0 | Criação inicial do requisito | Kika |

---

## 11. Aprovações

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| Analista de Requisitos | Kika | 17/04/2026 | [ ] |
| Cliente (Inforrel) | Rita | ____/____/____ | [ ] |
| Líder Técnico | Beto | ____/____/____ | [ ] |
