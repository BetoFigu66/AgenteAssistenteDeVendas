# Respostas da Rita ao Questionário

<!-- CLASSIFICACAO: HISTORICO -->

**Data**: 12/04/2026 (atualizado 14/04/2026)  
**Status**: ✅ COMPLETO - Todas as seções respondidas

---

## 1. Volume e Padrões de Atendimento

| Pergunta | Resposta |
|----------|----------|
| 1.1 Mensagens/dia | **10 a 30** |
| 1.2 Horário de pico | **10h às 12h** |
| 1.3 Tempo gasto/dia | **Varia muito**: de 10 min até o dia todo. Depende do conhecimento da pessoa. **Relógio é mais demorado que catraca.** |

### Insights:
- Volume moderado (10-30/dia) - viável para automação
- Pico pela manhã - importante ter resposta rápida nesse horário
- Relógios de ponto demandam mais tempo de atendimento que catracas

---

## 2. Tipos de Perguntas Recebidas

| Pergunta | Resposta |
|----------|----------|
| 2.1 Perguntas frequentes | **Valor, modelos, prazo e instalação** |
| 2.2 Respostas prontas | **Sim** - tem respostas rápidas no WhatsApp + 2 catálogos |
| 2.3 Perguntas caso a caso | **Relógios e catracas dependem do sistema que o cliente usa** |

### Insights:
- As 4 perguntas mais frequentes são automatizáveis: valor, modelos, prazo, instalação
- Já existe material de apoio (respostas rápidas + catálogos)
- Compatibilidade com sistema do cliente é ponto que exige análise humana

---

## 3. Produtos e Preços

| Pergunta | Resposta |
|----------|----------|
| 3.1 Modelos/tipos | **Vai enviar detalhes**. Relógios: cartão de proximidade, cartão de barras, biometria, facial |
| 3.2 Preços | **Tabela dos fabricantes + margem de 40% a 65%** |
| 3.3 Material de apoio | **2 catálogos**: catracas (mais completo) e relógios |

### Insights:
- Dois tipos de produtos: **Catracas** e **Relógios de ponto**
- Relógios têm variações por tecnologia (proximidade, barras, biometria, facial)
- Precificação baseada em margem sobre tabela do fabricante
- Catálogos existentes podem ser base para RAG

---

## 4. Processo de Venda

### 4.1 Fluxo típico de uma venda

**Ao receber contato do cliente (ou indicação TOPDATA/Control ID):**

1. **Solicitar informações:**
   - Qual CNPJ e nome da empresa?
   - Qual modelo (facial, proximidade somente ou proximidade e biometria)?
   - Endereço de entrega / instalação?
   - Já possui software de controle de ponto? Caso não, qual a faixa de funcionários?
   - Dados de contato para envio do orçamento (e-mail, telefone)?

2. **Verificar histórico:**
   - Existe orçamento anterior ou nota fiscal emitida para o mesmo cliente?
   - Validar modelo do equipamento e preço de venda

3. **Validar compatibilidade:**
   - Confirmar se o sistema do cliente é homologado para o produto
   - SDKs e DLLs são públicos (TOPDATA/Control ID), mas não há controle de homologação
   - **Recomendação**: Cliente deve confirmar com a empresa do sistema

4. **Elaborar orçamento** (conforme procedimento específico)

| Pergunta | Resposta |
|----------|----------|
| 4.2 Tempo até fechar venda | **Varia muito**: de 2 dias até 6 meses |
| 4.3 Taxa de conversão | **~2 em 10** (estimativa). Varia muito. Às vezes fecham orçamentos de meses atrás |

### Insights:
- Processo estruturado com coleta de dados específicos
- Histórico de cliente é importante (orçamentos anteriores)
- **Compatibilidade de sistema é crítica** - não pode ser automatizado sem validação
- Ciclo de venda longo e imprevisível

---

## 5. Dores e Frustrações

| Pergunta | Resposta |
|----------|----------|
| 5.1 O que mais incomoda | **[x] Responder as mesmas perguntas repetidamente** |
| | **[x] Perder vendas por demora na resposta** |
| 5.2 Perdeu vendas por demora | **Não** |
| 5.3 Ignora mensagens | **Não** - responde todas |

### Insights:
- Principal dor: **repetição de perguntas** - automatizável!
- Preocupação com demora, mas não perdeu vendas por isso (ainda)
- Rita é dedicada - responde 100% das mensagens

---

## 6. Automação Atual

| Pergunta | Resposta |
|----------|----------|
| 6.1 Como funciona | **Respostas rápidas do WhatsApp Business** |
| 6.2 O que funciona bem | Respostas prontas por tipo (ex: `DUVIDASREPTOPDATA`) |
| 6.3 O que gostaria de automatizar | **Busca de CNPJ na Receita Federal** (razão social, endereço) + consulta de protestos |

### Exemplo de resposta rápida existente (`DUVIDASREPTOPDATA`):
```
Olá, tudo bem? Sou da equipe de vendas da Inforrel, e estou entrando em contato 
referente a uma solicitação realizada junto à Topdata sobre orçamento de relógio ponto. 
1) Qual modelo (proximidade somente ou proximidade e biometria, facial)? 
2) É retirada ou para instalar. Se for para instalar, preciso do endereço de instalação?
3) Você já tem o software de controle de ponto? Caso não tenha, qual a faixa de funcionários? 
4) Qual o e-mail para envio do orçamento?
```

### Insights:
- Já usa respostas rápidas do WhatsApp Business - **podemos aproveitar esse conteúdo**
- Desejo de integração com **Receita Federal (CNPJ)** - funcionalidade de alto valor
- Consulta de **protestos** - validação de crédito do cliente

---

## 7. Expectativas do Sistema

| Pergunta | Resposta |
|----------|----------|
| 7.1 UMA coisa mais valiosa | **Busca automática de CNPJ na Receita Federal** |
| 7.2 "Valeu a pena" se... | **Facilitar elaboração de orçamento** (agilidade e eficácia) |
| 7.3 NÃO DEVE fazer | **Nunca prometer prazo** (depende muito do produto) |

### Insights:
- **Prioridade #1**: Integração com Receita Federal (CNPJ → dados da empresa)
- Sucesso = agilizar orçamentos
- **Regra crítica**: Sistema NUNCA deve prometer prazo de entrega

---

## 8. Handoff para Humano

| Pergunta | Resposta Rita |
|----------|---------------|
| 8.1 Situações que precisam de humano | **Controle de acesso**: Ivan ou técnico visita. **Cliente grande**: entender projeto e dar orçamento mais preciso |
| 8.2 Como ser avisada | **[x] Notificação no WhatsApp** |

> 📝 **Nota**: Além das respostas da Rita, Beto definiu requisitos adicionais (ver abaixo).

### 8.1 Requisitos Definidos:

1. **Registro completo de interações**
   - Sistema deve registrar TODAS as interações com TODOS os clientes
   - Administrador consegue acompanhar todos os chats

2. **Análise de sentimento com IA**
   - Identificar se cliente está satisfeito ou insatisfeito
   - Classificar conversas como **críticas** quando:
     - Cliente demonstra insatisfação
     - Cliente pede para falar com humano (frases-chave)

3. **Dashboard para atendente humano**
   - Visualizar conversas classificadas como críticas
   - Para cada conversa crítica, exibir:
     - **Resumo da conversa** até o momento
     - **Metadados importantes**:
       - Quantidade de equipamentos
       - Localidade do cliente
       - Outras informações identificáveis

### Frases que indicam necessidade de humano (classificar como crítica):
- "quero falar com alguém"
- "falar com vendedor"
- "falar com humano"
- "atendente"
- "pessoa real"
- (outras a identificar)

### Resposta pelo Dashboard (Human Takeover)

O atendente humano poderá **responder diretamente pelo dashboard**, e a mensagem será enviada ao cliente via WhatsApp.

| Fase | Abordagem | Descrição |
|------|-----------|-----------|
| **POC** | Notificação | Dashboard avisa, Rita responde pelo WhatsApp Business |
| **Single-Tenant** | Híbrida | Rita responde pelo dashboard → sistema envia via API WhatsApp |

**Fluxo Single-Tenant:**
```
Cliente (WhatsApp) ←→ Sistema ←→ Dashboard (Rita)
                         ↓
                    Conversa crítica detectada
                         ↓
                    Rita responde pelo dashboard
                         ↓
                    Mensagem enviada via API WhatsApp
                         ↓
                    Cliente recebe no WhatsApp
```

---

## 9. Informações Técnicas

| Pergunta | Resposta |
|----------|----------|
| 9.1 Sistema de gestão (ERP, CRM, planilha) | **ERP SUPERSOFT** (Rita não acha bom) |
| 9.2 WhatsApp Business? Mais de um número? | **Sim, 3 números** (agora são 3 pessoas no vendas) |

### Insights:
- ERP existente (SUPERSOFT) - possível integração futura, mas Rita não gosta
- **3 números de WhatsApp** = 3 vendedores - sistema precisa suportar múltiplos atendentes
- Isso impacta arquitetura: multi-atendente desde o início

---

## 10. Pergunta Aberta

**Resposta da Rita:**
> Sobre as respostas rápidas, eu tenho algumas (para relógios Topdata, Control ID, catracas, controle de acesso)

> Quando eu estava no CPQD trabalhava no sistema no covid e especificava e testava a interação por chat. Eu não sei implementar mas seria interessante se tivesse algumas perguntas. Ex: qual o CNPJ, após ele responder o sistema faz outra pergunta e assim vai.

### Insights:
- Respostas rápidas existentes organizadas por:
  - Relógios Topdata
  - Relógios Control ID
  - Catracas
  - Controle de acesso
- **Material valioso para RAG** - solicitar essas respostas rápidas
- **Rita tem experiência** em especificação de chatbots (trabalhou no CPQD)
- **Expectativa de UX**: fluxo conversacional guiado (pergunta → resposta → próxima pergunta)
- Isso **valida** nossa abordagem de coleta estruturada de dados

---

## Status das Seções

- [x] 1. Volume e Padrões ✅
- [x] 2. Tipos de Perguntas ✅
- [x] 3. Produtos e Preços ✅
- [x] 4. Processo de Venda ✅
- [x] 5. Dores e Frustrações ✅
- [x] 6. Automação Atual ✅
- [x] 7. Expectativas do Sistema ✅
- [x] 8. Handoff para Humano ✅
- [x] 9. Informações Técnicas ✅
- [x] 10. Pergunta Aberta ✅

**🎉 QUESTIONÁRIO COMPLETO!**

---

## Conclusões (atualizadas)

### O que pode ser automatizado:
1. **Coleta inicial de dados** (CNPJ, modelo, endereço, contato)
2. Responder sobre **valores** (com base na margem sobre tabela)
3. Enviar **catálogos** de catracas e relógios
4. Responder sobre **instalação**
5. **Busca de CNPJ na Receita Federal** ⭐ (prioridade da Rita!)
6. **Análise de sentimento** das conversas (satisfeito/insatisfeito)
7. **Resumo automático** da conversa para handoff

### O que NÃO pode ser automatizado:
1. **Prometer prazo de entrega** ❌ (regra crítica)
2. Validar **compatibilidade de sistema** (exige análise humana)
3. **Negociação** de margem (40-65% é uma faixa)
4. Consulta de **histórico de orçamentos/NF** do cliente

### Material existente para RAG:
- Respostas rápidas do WhatsApp Business (ex: `DUVIDASREPTOPDATA`)
- Catálogo de catracas
- Catálogo de relógios
- Tabelas de preços dos fabricantes

### Funcionalidades de Alto Valor Identificadas:
1. **Integração Receita Federal** - buscar dados por CNPJ (razão social, endereço)
2. **Consulta de protestos** - validação de crédito
3. **Agilizar elaboração de orçamentos** - critério de sucesso da Rita
4. **Dashboard de acompanhamento** - visualizar conversas críticas
5. **Extração de metadados** - quantidade equipamentos, localidade, etc.
6. **Human Takeover** - responder pelo dashboard, enviar via WhatsApp API

### Regras de Negócio Críticas:
- ❌ **NUNCA prometer prazo** de entrega
- ⚠️ **Sempre validar compatibilidade** de sistema com o cliente
- ✅ Pode informar margem de preço (40-65% sobre fabricante)
- 🚨 **Escalar para humano** quando cliente demonstrar insatisfação ou pedir
