# REQ-001: Integração com Receita Federal (CNPJ)

**Versão**: 1.2  
**Data**: 2026-05-06  
**Autor**: Kika (Analista de Requisitos)  
**Status**: Em Elaboração  
**Prioridade**: Alta  

---

## 1. Identificação do Requisito

**ID**: REQ-001  
**Tipo**: Funcional  
**Categoria**: Integração Externa  
**Solicitante**: vendedor (Inforrel)  

---

## 2. Descrição

O sistema deve consultar automaticamente dados da Receita Federal quando um cliente informa o CNPJ durante a conversa no WhatsApp, retornando informações cadastrais da empresa para agilizar o processo de elaboração de orçamentos.

---

## 3. Justificativa de Negócio

**Problema Atual**:
- vendedor precisa buscar manualmente dados do cliente por CNPJ
- Processo demorado e suscetível a erros de digitação
- Atrasa a elaboração de orçamentos

**Benefício Esperado**:
- Redução de tempo na qualificação de leads
- Melhoria na experiência do cliente
- Dados padronizados e confiáveis
- **Critério de sucesso definido pelo vendedor**: "Facilitar elaboração de orçamento"

---

## 4. Critérios de Aceite

### 4.1 Funcionalidades Obrigatórias

- [ ] **REQ-001.1 — Reconhecimento de CNPJ em diferentes formatos**: Sistema deve reconhecer CNPJ em diferentes formatos:
  - XX.XXX.XXX/XXXX-XX
  - XXXXXXXXXXXXXX
  - XX XXX XXX XXX XX

- [ ] **REQ-001.2 — Validação de formato do CNPJ**: Sistema deve validar formato do CNPJ antes da consulta

- [ ] **REQ-001.3 — Consulta à API da Receita Federal**: Sistema deve consultar API externa e retornar:
  - Razão Social
  - Nome Fantasia (se houver)
  - Endereço completo (logradouro, número, complemento, bairro, cidade, UF, CEP)
  - Situação cadastral (ativa, inativa, etc.)
  - Data de abertura
  - CNAE principal

- [ ] **REQ-001.4 — Confirmação dos dados pelo cliente**: Sistema deve exibir dados para confirmação do usuário

- [ ] **REQ-001.5 — Disponibilização dos dados para orçamento**: Dados confirmados devem ficar disponíveis para orçamento

### 4.2 Regras de Negócio

- [ ] **REQ-001.6 — Tratamento de CNPJ inválido ou não encontrado**: Se CNPJ for inválido ou não encontrado, sistema deve:
  - Informar erro de forma amigável
  - Solicitar verificação dos dados
  - Permitir nova tentativa

  **Política de tentativas**:
  - O sistema permite até **3 tentativas** de informar o CNPJ na mesma conversa (a inicial + 2 retentativas)
  - A cada falha, a mensagem de erro deve indicar **o motivo** quando possível (formato inválido, CNPJ não encontrado na Receita, situação cadastral inativa) e orientar a correção
  - Esgotadas as 3 tentativas sem sucesso, o sistema deve **escalar para humano** (REQ-004.9 — baixa confiança/contradição de dados) com o resumo dos valores tentados, evitando manter o cliente em loop
  - Falhas de **infraestrutura** da API externa (timeout, indisponibilidade) **não** consomem tentativa do cliente; nesses casos, o sistema aplica retry interno conforme REQ-001.10 e, persistindo a falha, escala para humano informando indisponibilidade temporária
  - Cada tentativa e seu desfecho devem ser registrados como evento (REQ-005.4)

- [ ] **REQ-001.7 — Persistência dos dados no perfil do cliente**: Dados devem ser armazenados no perfil do cliente para consultas futuras

### 4.3 Requisitos Não-Funcionais

- [ ] **REQ-001.8 — Tempo de resposta da consulta**: Tempo de resposta da consulta: < 3 segundos
- [ ] **REQ-001.9 — Disponibilidade da API externa**: Disponibilidade da API: > 99%
- [ ] **REQ-001.10 — Tratamento de falhas da API externa**: Tratamento de falhas da API externa

---

## 5. Fluxo de Conversa Esperado

```
Cliente: "Olá, gostaria de orçamento para catracas. CNPJ: 12.345.678/0001-90"

Sistema: "✅ Empresa identificada: RAZÃO SOCIAL LTDA
📍 Endereço: Rua Exemplo, 123 - Centro - São Paulo/SP
📅 Abertura: 15/01/2020
📋 Situação: ATIVA

Os dados estão corretos? (S/N)"
```

---

## 6. Dependências

### 6.1 Dependências Técnicas
- API externa para consulta CNPJ (BrasilAPI ou receitaws)
- Conexão internet estável
- Sistema de tratamento de erros

### 6.2 Dependências de Negócio
- Definição da API a ser utilizada
- Verificação de limites de uso da API escolhida

---

## 7. Restrições e Limitações

### 7.1 Restrições
- API gratuita pode ter limites de requisições
- Dados dependem da atualização da Receita Federal
- Apenas CNPjs brasileiros

### 7.2 Limitações Aceitas no POC
- [ ] Sem cache de consultas (consultar sempre API)
- [ ] Sem histórico de alterações cadastrais
- [ ] Sem validação de sócios/quadro societário

---

## 8. Critérios de Sucesso

### 8.1 Métricas
- Redução de tempo na qualificação: > 50%
- Taxa de acurácia dos dados: > 95%
- Satisfação do vendedor: qualitativa

### 8.2 Condições de Aceite Final
- vendedor consegue elaborar orçamento 50% mais rápido
- Sistema funciona sem falhas por 1 semana
- Dados retornados são confiáveis

---

## 9. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| API indisponível | Média | Alto | Ter API alternativa configurada |
| Limite de requisições excedido | Baixa | Médio | Implementar cache local |
| Dados desatualizados | Baixa | Baixo | Informar fonte e data dos dados |

---

## 10. Estimativas

| Atividade | Horas |
|-----------|-------|
| Pesquisa e seleção da API | 2h |
| Implementação da consulta | 3h |
| Validação e tratamento de erros | 2h |
| Interface de confirmação | 1h |
| Testes e ajustes | 2h |
| **Total** | **10h** |

---

## 11. Histórico de Alterações

| Data | Versão | Alteração | Autor |
|------|--------|-----------|-------|
| 14/04/2026 | 1.0 | Criação inicial do requisito | Kika |
| 06/05/2026 | 1.1 | Adição de títulos descritivos a todos os requisitos do documento | Kika |
| 13/05/2026 | 1.2 | REQ-001.6 enriquecido com política de tentativas (máximo 3), distinção entre falha do cliente e falha de infraestrutura, escalonamento via REQ-004.9 após esgotar tentativas e exigência de registro auditavel (REQ-005.4) | Kika |

---

## 12. Aprovações

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| Analista de Requisitos | Kika | 14/04/2026 | [ ] |
| Cliente (Inforrel) | Rita | ____/____/____ | [ ] |
| Líder Técnico | Beto | ____/____/____ | [ ] |
