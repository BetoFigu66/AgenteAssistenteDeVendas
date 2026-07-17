# REQ-009: Tratamento de Reclamações Pós-venda (Atraso/Suporte) com Identificação de Orçamento/Pedido

<!-- CLASSIFICACAO: SISTEMA-CAIXAPRETA -->
<!-- CLASSIFICACAO: IA -->

**Versão**: 1.3  
**Data**: 2026-04-17  
**Autor**: Kika (Analista de Requisitos)  
**Status**: Em Elaboração  
**Prioridade**: Alta  

---

## 1. Identificação do Requisito

**ID**: REQ-009  
**Tipo**: Funcional  
**Categoria**: Pós-venda / Reclamações / Suporte  
**Solicitante**: Operação (vendedor)  

---

## 2. Descrição

O sistema deve identificar e tratar mensagens de pós-venda relacionadas a reclamações, especialmente sobre **atraso de entrega**, **falta de prazo**, **produto com problema** ou **pedido de suporte**. Ao detectar esse tipo de mensagem, o sistema deve:

1. Identificar o número/contato do WhatsApp do cliente
2. Buscar orçamentos e/ou registros relacionados ao cliente (via telefone e/ou CNPJ) para tentar identificar qual orçamento/pedido está relacionado ao assunto
3. Apresentar ao cliente um resumo para confirmação (ex: empresa, produto, data do orçamento) antes de prosseguir
4. Após confirmação, escalar para o vendedor com a reclamação e dados do orçamento/pedido

---

## 3. Justificativa de Negócio

**Problema Atual**:
- Reclamações de pós-venda (prazo, entrega, suporte) exigem resposta rápida e humana
- Sem identificação do orçamento/pedido, o vendedor perde tempo pedindo dados e buscando histórico

**Benefício Esperado**:
- Reduzir tempo de triagem e entendimento do problema
- Encaminhar para o vendedor com contexto completo
- Evitar resposta automática inadequada em situações críticas

---

## 4. Critérios de Aceite

### 4.1 Detecção de Reclamação/Pós-venda

- [ ] **REQ-009.1 — Detecção de mensagens de pós-venda**: O sistema deve detectar mensagens de pós-venda, com foco inicial em:
  - atraso/prazo de entrega
  - falta de prazo
  - produto não funciona / defeito
  - suporte/instalação/ajuda

- [ ] **REQ-009.2 — Marcação como conversa crítica ao detectar pós-venda**: Ao detectar pós-venda, o sistema deve classificar a conversa como crítica (integração com REQ-007) e iniciar tratamento de reclamação

### 4.2 Identificação de Orçamento/Pedido Relacionado

- [ ] **REQ-009.3 — Identificação do cliente e busca de orçamentos pelo telefone**: O sistema deve identificar o cliente a partir do número WhatsApp (`cliente_id`/telefone) e buscar orçamentos associados (REQ-006)

- [ ] **REQ-009.4 — Seleção do orçamento mais provável quando houver múltiplos**: Quando houver mais de um orçamento associado ao mesmo número, o sistema deve selecionar o mais provável (por recência) e pedir confirmação do cliente

- [ ] **REQ-009.5 — Solicitação de dados alternativos quando não achar orçamento pelo telefone**: Quando não houver orçamento associado ao número, o sistema deve solicitar dados mínimos para localizar:
  - CNPJ (preferencial) ou
  - e-mail usado no orçamento (se aplicável)

### 4.3 Confirmação com o Cliente

- [ ] **REQ-009.6 — Resumo do orçamento para confirmação do cliente**: Antes de escalonar, o sistema deve apresentar um resumo do orçamento/pedido identificado para o cliente confirmar, contendo quando possível:
  - empresa (razão social)
  - produto(s)
  - **data de referência**, escolhida conforme a regra abaixo:
    - Se o orçamento estiver com status `convertido` (REQ-006.5) — ou seja, foi marcado como pedido efetivado pelo vendedor no painel administrativo (REQ-006.8 / REQ-010) — usar a **data da transição para `convertido`** (REQ-006.6) e referenciá-la ao cliente como **"data do pedido"**
    - Caso contrário, usar a **data do último orçamento enviado** ao cliente (timestamp de envio registrado pelo REQ-006.4) e referenciá-la como **"data do orçamento"**

- [ ] **REQ-009.7 — Tratamento de orçamento incorreto identificado pelo cliente**: Quando o cliente indicar que o orçamento apresentado no REQ-009.6 **não é** o que ele quer tratar, o sistema deve seguir esta política:
  - **1ª tentativa adicional**: se houver outro orçamento associado ao mesmo telefone (lista do REQ-009.3 ordenada por recência), propor o **próximo da lista** e voltar ao REQ-009.6 para confirmação
  - **2ª tentativa adicional**: caso o cliente recuse novamente e ainda existam orçamentos não oferecidos, propor mais um. O limite total é de **até 2 propostas alternativas** após a primeira (3 tentativas no total) para evitar loops longos
  - **Sem mais opções por telefone**: se a lista terminar ou o limite for atingido sem confirmação, cair no fluxo do REQ-009.5 (pedir CNPJ ou e-mail usado no orçamento) e, ao localizar, reiniciar a confirmação pelo REQ-009.6
  - **Desistência/escalonamento sem identificação**: se mesmo após o REQ-009.5 nada for localizado, o sistema deve **escalar mesmo assim** (REQ-009.8) marcando o evento com a flag `orcamento_nao_identificado` e enviando ao vendedor o texto da reclamação e os dados coletados (telefone, CNPJ/e-mail informados, se houver), para que ele conduza a triagem manualmente
  - Cada proposta apresentada e cada "não" do cliente deve ser registrada como evento (REQ-005 / REQ-009.10)

### 4.4 Escalonamento para o vendedor

- [ ] **REQ-009.8 — Escalonamento com contexto completo da reclamação**: Após confirmação do cliente, o sistema deve escalar imediatamente para o vendedor (REQ-004), enviando:
  - identificação do cliente (telefone)
  - `orcamento_id` (se existir)
  - dados do orçamento (produto, empresa, data)
  - texto da reclamação do cliente
  - categoria da reclamação (prazo/atraso, suporte, não funciona, etc.)

- [ ] **REQ-009.9 — Suspensão de respostas automáticas após escalonamento**: Após o escalonamento, o sistema deve entrar em estado “em atendimento humano” (REQ-004) para não continuar respondendo automaticamente

### 4.5 Registro e Auditoria

- [ ] **REQ-009.10 — Registro auditavel das etapas do tratamento de reclamação**: O sistema deve registrar como eventos (REQ-005):
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

(Sistema notifica vendedor com os dados + reclamação)
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
| 12/05/2026 | 1.1 | Adição de títulos descritivos a todos os requisitos do documento | Kika |
| 12/05/2026 | 1.2 | REQ-009.6: refinamento da "data de referência" exibida ao cliente — usar a data da transição para `convertido` ("data do pedido") quando o orçamento foi efetivado via REQ-006.8/REQ-010, ou a data do último orçamento enviado (REQ-006.4) caso contrário | Kika |
| 12/05/2026 | 1.3 | REQ-009.7 detalhado com política de tentativas (máximo 2 propostas alternativas), integração explícita com REQ-009.5 (fallback para CNPJ/e-mail), critério de desistência (escalar com flag `orcamento_nao_identificado` via REQ-009.8) e exigência de registro de cada proposta/recusa (REQ-005 / REQ-009.10) | Kika |

---

## 11. Aprovações

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| Analista de Requisitos | Kika | 17/04/2026 | [ ] |
| Cliente (Inforrel) | Rita | ____/____/____ | [ ] |
| Líder Técnico | Beto | ____/____/____ | [ ] |
