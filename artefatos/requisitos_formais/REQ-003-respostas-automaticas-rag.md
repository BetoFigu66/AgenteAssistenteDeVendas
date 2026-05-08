# REQ-003: Respostas Automáticas com Base de Conhecimento (RAG)

**Versão**: 1.2  
**Data**: 2026-05-06  
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

- [ ] **REQ-003.1 — Classificação de mensagens para FAQ**: Sistema deve classificar mensagens recebidas e identificar quando são perguntas respondíveis automaticamente (FAQ)

- [ ] **REQ-003.2 — Recuperação de conteúdo da base de conhecimento (RAG)**: Sistema deve consultar a base de conhecimento (RAG) e recuperar informações relevantes para a pergunta do cliente

- [ ] **REQ-003.3 — Geração de resposta baseada em referências**: Sistema deve gerar resposta usando IA com base no conteúdo recuperado (não inventar)

- [ ] **REQ-003.4 — Tópicos mínimos suportados**: Sistema deve suportar no mínimo os tópicos:
  - Valor / preço
  - Modelos disponíveis
  - Prazos (com as restrições de regra de negócio)
  - Instalação (condições gerais)
  - Envio de catálogo quando solicitado

- [ ] **REQ-003.5 — Registro da pergunta, referências e resposta**: Sistema deve registrar a pergunta, as referências do RAG utilizadas (fonte + id do item) e a resposta enviada no histórico de conversa

### 4.2 Regras de Negócio

- [ ] **REQ-003.6 — Proibição de prometer prazo de entrega**: O sistema **NUNCA** deve prometer prazo de entrega; quando questionado, deve responder de forma segura e condicional (ex: “depende do modelo e disponibilidade; posso confirmar com o time e retorno”)

- [ ] **REQ-003.7 — Tratamento de perguntas sobre compatibilidade**: Caso a pergunta envolva compatibilidade com sistema do cliente, o sistema deve orientar validação com o fornecedor do software e/ou escalar para humano quando necessário

- [ ] **REQ-003.8 — Fallback para informação insuficiente**: Caso a IA não encontre informação suficiente na base, deve:
  - Informar que precisa confirmar
  - Fazer no máximo 1 pergunta de clarificação
  - Se ainda assim não houver base, escalar para humano

- [ ] **REQ-003.9 — Não negociar desconto em perguntas de preço**: Para perguntas de preço, o sistema não deve negociar desconto; pode mencionar que valores podem variar por quantidade e condições, e que o vendedor pode avaliar

- [ ] **REQ-003.13 — Devolver controle ao REQ-002 após responder**: Quando o cliente estiver em meio a um fluxo de qualificação (REQ-002) e fizer uma **pergunta sobre produto/serviço**, o REQ-003 deve:
  - Responder a dúvida com base no conteúdo recuperado
  - Ao final da resposta, **devolver o controle ao REQ-002**, sinalizando para retomar a qualificação na última pergunta pendente
  - Não solicitar dados de qualificação (CNPJ, endereço, contato etc.) — isso é responsabilidade do REQ-002

- [ ] **REQ-003.14 — Não acionar para respostas de qualificação**: O REQ-003 não deve ser acionado para mensagens que sejam **resposta direta a uma pergunta de qualificação** feita pelo sistema (ex: cliente enviando CNPJ, quantidade de funcionários, endereço). Essas mensagens pertencem ao REQ-002.

### 4.3 Requisitos Não-Funcionais

- [ ] **REQ-003.10 — Tempo alvo de resposta**: Tempo alvo de resposta: < 5 segundos em condições normais
- [ ] **REQ-003.11 — Respostas curtas e objetivas para WhatsApp**: Respostas devem ser curtas e objetivas para WhatsApp
- [ ] **REQ-003.12 — Auditabilidade das respostas automáticas**: Todas as respostas automáticas devem ser auditáveis (conteúdo-base + resposta)

### 4.4 Terminologia

Para alinhamento com o REQ-002, este requisito adota:

- **Pergunta sobre produto/serviço**: mensagem do **cliente** com dúvida que exige consulta à base de conhecimento (catálogo, FAQ, manuais, preços, prazos, compatibilidade, serviços prestados, características técnicas). Escopo do REQ-003.
- **Pergunta de qualificação**: pergunta feita pelo **sistema** para coletar dado necessário ao orçamento. Escopo do REQ-002 (fora do REQ-003).
- **Pergunta ambigua**: mensagem que poderia ser de qualificação ou de conhecimento; nesse caso, aplicar REQ-003.1 (classificação) e, se necessário, REQ-003.8 (uma pergunta de clarificação).

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

### 7.4 Pergunta sobre produto no meio da qualificação (interação com REQ-002)

Cenário em que o cliente está respondendo a uma qualificação (REQ-002) e interrompe com uma dúvida sobre o produto:

```
[Contexto: REQ-002 acabou de perguntar "Sua empresa já tem software de controle de ponto?"]

Cliente: "Ainda não. Aliás, qual a diferença entre biométrico e facial?"

→ Classificação (REQ-003.1): pergunta sobre produto/serviço
→ Recuperar conteúdo do catálogo (REQ-003.2)
→ Gerar resposta baseada em referências (REQ-003.3)

Sistema: "O biométrico identifica pela digital do dedo, enquanto o facial
reconhece pelo rosto — mais rápido e sem contato.
(Fonte: catálogo Control iD / Topdata)

Voltando ao seu orçamento: você prefere biométrico ou facial?"

→ REQ-003.13: devolve controle ao REQ-002 reapresentando a última pergunta pendente
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
| Resposta “inventada” pela IA | Média | Alto | Forçar uso de referências recuperadas (fonte + id do item) e auditoria |
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
| 05/05/2026 | 1.1 | Adicionada terminologia (seção 4.4), regras de interação com REQ-002 (REQ-003.13 e REQ-003.14) e exemplo 7.4 de pergunta sobre produto no meio da qualificação | Kika |
| 06/05/2026 | 1.2 | Adição de títulos descritivos a todos os requisitos do documento | Kika |

---

## 12. Aprovações

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| Analista de Requisitos | Kika | 15/04/2026 | [ ] |
| Cliente (Inforrel) | Rita | ____/____/____ | [ ] |
| Líder Técnico | Beto | ____/____/____ | [ ] |
