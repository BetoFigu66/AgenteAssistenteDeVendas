# REQ-003: Respostas Automáticas com Base de Conhecimento (RAG)

**Versão**: 1.0  
**Data**: 2026-04-15  
**Autor**: Kika (Analista de Requisitos)  
**Status**: Em Elaboração  
**Prioridade**: Alta  

---

## 1. Identificação do Requisito

**ID**: REQ-003  
**Tipo**: Funcional  
**Categoria**: Atendimento Automático / Base de Conhecimento  
**Solicitante**: Rita (Inforrel)  

---

## 2. Descrição

O sistema deve responder automaticamente às perguntas mais frequentes recebidas no WhatsApp relacionadas à venda de **catracas** e **relógios de ponto**, utilizando uma base de conhecimento (RAG) construída a partir de:

- Respostas rápidas já existentes no WhatsApp Business
- Catálogos (catracas e relógios)
- Tabelas de preço dos fabricantes e regras internas de precificação
- Perguntas frequentes (FAQ)

A resposta automática deve ser gerada com auxílio de IA, mas sempre baseada em informação recuperada da base de conhecimento.

---

## 3. Justificativa de Negócio

**Problema Atual**:
- Rita responde repetidamente as mesmas perguntas (valor, modelos, prazo e instalação)
- Atendimento manual consome tempo e pode gerar atrasos

**Benefício Esperado**:
- Redução do esforço operacional
- Resposta mais rápida nos horários de pico
- Padronização das respostas

---

## 4. Critérios de Aceite

### 4.1 Funcionalidades Obrigatórias

- [ ] **REQ-003.1**: Sistema deve classificar mensagens recebidas e identificar quando são perguntas respondíveis automaticamente (FAQ)

- [ ] **REQ-003.2**: Sistema deve consultar a base de conhecimento (RAG) e recuperar informações relevantes para a pergunta do cliente

- [ ] **REQ-003.3**: Sistema deve gerar resposta usando IA com base no conteúdo recuperado (não inventar)

- [ ] **REQ-003.4**: Sistema deve suportar no mínimo os tópicos:
  - Valor / preço
  - Modelos disponíveis
  - Prazos (com as restrições de regra de negócio)
  - Instalação (condições gerais)
  - Envio de catálogo quando solicitado

- [ ] **REQ-003.5**: Sistema deve registrar a pergunta, trechos recuperados e resposta enviada no histórico de conversa

### 4.2 Regras de Negócio

- [ ] **REQ-003.6**: O sistema **NUNCA** deve prometer prazo de entrega; quando questionado, deve responder de forma segura e condicional (ex: “depende do modelo e disponibilidade; posso confirmar com o time e retorno”)

- [ ] **REQ-003.7**: Caso a pergunta envolva compatibilidade com sistema do cliente, o sistema deve orientar validação com o fornecedor do software e/ou escalar para humano quando necessário

- [ ] **REQ-003.8**: Caso a IA não encontre informação suficiente na base, deve:
  - Informar que precisa confirmar
  - Fazer no máximo 1 pergunta de clarificação
  - Se ainda assim não houver base, escalar para humano

- [ ] **REQ-003.9**: Para perguntas de preço, o sistema não deve negociar desconto; pode mencionar que valores podem variar por quantidade e condições, e que o vendedor pode avaliar

### 4.3 Requisitos Não-Funcionais

- [ ] **REQ-003.10**: Tempo alvo de resposta: < 5 segundos em condições normais
- [ ] **REQ-003.11**: Respostas devem ser curtas e objetivas para WhatsApp
- [ ] **REQ-003.12**: Todas as respostas automáticas devem ser auditáveis (conteúdo-base + resposta)

---

## 5. Conteúdo da Base de Conhecimento

### 5.1 Fontes
- Respostas rápidas do WhatsApp Business (ex: `DUVIDASREPTOPDATA`, `DUVIDASREPCONTROLID`, etc.)
- Catálogo de catracas
- Catálogo de relógios
- Lista de modelos/tecnologias (Topdata, Control ID)
- Regras internas de precificação (margem 40% a 65%)

### 5.2 Formato (POC)
- Arquivos estruturados (ex: `.txt`, `.md`, `.json`) com busca simples por palavras-chave

---

## 6. Fluxo de Atendimento (alto nível)

```
1) Mensagem do cliente
2) Classificação: é FAQ / pedido de catálogo / precisa de humano?
3) Se FAQ:
   3.1 Recuperar conteúdo relevante (RAG)
   3.2 Gerar resposta com IA baseada no conteúdo
   3.3 Validar regras de negócio (prazo, compatibilidade, desconto)
4) Enviar resposta
5) Registrar no histórico
```

---

## 7. Exemplos

### 7.1 Pergunta de preço

```
Cliente: "Qual o valor do relógio biométrico Control iD?"

Sistema: "O valor varia conforme o modelo e condições.
Se você me disser a quantidade e a cidade de entrega/instalação, eu já te direciono certinho."
```

### 7.2 Pergunta de prazo

```
Cliente: "Qual o prazo de entrega da catraca?"

Sistema: "O prazo pode variar conforme o modelo e disponibilidade no momento.
Se você me informar qual modelo você tem interesse e a cidade de entrega, eu verifico e te retorno com a confirmação."
```

### 7.3 Pedido de catálogo

```
Cliente: "Você tem catálogo?"

Sistema: "Tenho sim. Você quer o catálogo de catracas ou de relógios de ponto?"
```

---

## 8. Dependências

### 8.1 Dependências Técnicas
- Integração com motor de IA
- Repositório/armazenamento da base de conhecimento
- Registro de histórico de conversa

### 8.2 Dependências de Negócio
- Receber as respostas rápidas completas da Rita
- Receber catálogos e tabelas de preço atualizadas

---

## 9. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Base de conhecimento incompleta | Alta | Alto | Começar com FAQ top 20 e iterar |
| Resposta “inventada” pela IA | Média | Alto | Forçar uso de trechos recuperados e auditoria |
| Informações desatualizadas | Média | Médio | Processo simples de atualização dos arquivos |

---

## 10. Estimativas

| Atividade | Horas |
|-----------|-------|
| Organizar materiais (respostas rápidas/catálogos) | 4h |
| Estruturar base (arquivos) | 3h |
| Implementar busca simples + montagem de contexto | 4h |
| Prompt e regras de negócio (prazo/compatibilidade) | 3h |
| Testes com perguntas reais | 4h |
| **Total** | **18h** |

---

## 11. Histórico de Alterações

| Data | Versão | Alteração | Autor |
|------|--------|-----------|-------|
| 15/04/2026 | 1.0 | Criação inicial do requisito | Kika |

---

## 12. Aprovações

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| Analista de Requisitos | Kika | 15/04/2026 | [ ] |
| Cliente (Inforrel) | Rita | ____/____/____ | [ ] |
| Líder Técnico | Beto | ____/____/____ | [ ] |
