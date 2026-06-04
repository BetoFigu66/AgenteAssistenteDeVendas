# REQ-015: Validação de CPF e Consulta de Débitos (Pessoa Física)

**Versão**: 1.0  
**Data**: 2026-06-01  
**Autor**: Kika (Analista de Requisitos)  
**Status**: Em Elaboração  
**Prioridade**: Média  

---

## 1. Identificação do Requisito

**ID**: REQ-015  
**Tipo**: Funcional  
**Categoria**: Integração Externa / Validação  
**Solicitante**: vendedor (Inforrel)  

---

## 2. Descrição

O sistema deve identificar quando o cliente solicitante de orçamento é **Pessoa Física**, coletar seu **CPF**, validar formato e dígitos verificadores, e consultar serviço externo de **débitos / restrições financeiras** (consulta de "dívidas na praça"). A consulta tem caráter **informativo** para o vendedor — o sistema **não** nega orçamento automaticamente em razão de restrições; o resultado é registrado e a conversa é encaminhada para revisão humana antes do fechamento.

Este requisito é o **par de REQ-001** (que trata de CNPJ / Pessoa Jurídica). Os dois nunca se aplicam à mesma conversa: o tipo de cliente é definido em REQ-002.

---

## 3. Justificativa de Negócio

**Problema Atual**:
- A Inforrel também atende Pessoa Física (não apenas empresas).
- Hoje a coleta de CPF e a verificação de restrições é feita manualmente pelo vendedor, fora da conversa do WhatsApp.
- Já houve casos de orçamento elaborado para CPF com restrição grave que inviabiliza pagamento — retrabalho e perda de tempo da equipe.

**Benefício Esperado**:
- Padronizar a coleta de CPF na qualificação inicial.
- Sinalizar precocemente ao vendedor casos com restrição financeira, sem bloquear automaticamente o cliente.
- Reduzir retrabalho na elaboração de orçamento para clientes inviáveis.
- **Critério de sucesso definido pelo vendedor (Rita)**: "saber se a pessoa tem dívida na praça antes de fechar".

---

## 4. Critérios de Aceite

### 4.1 Funcionalidades Obrigatórias

- [ ] **REQ-015.1 — Reconhecimento de CPF em diferentes formatos**: Sistema deve reconhecer CPF em diferentes formatos:
  - XXX.XXX.XXX-XX
  - XXXXXXXXXXX
  - XXX XXX XXX XX

- [ ] **REQ-015.2 — Validação de formato e dígitos verificadores do CPF**: Sistema deve validar:
  - Quantidade de dígitos (11)
  - Dígitos verificadores (algoritmo padrão de validação de CPF)
  - Rejeitar sequências triviais conhecidamente inválidas (`00000000000`, `11111111111`, ..., `99999999999`)

  **Importante**: a validação é **algorítmica** e **local** (não depende de chamada externa). Não há API pública gratuita da Receita Federal para consulta de CPF (diferente de CNPJ — REQ-001.3); por isso, o sistema **não** consulta dados cadastrais (nome, situação) do CPF na Receita.

- [ ] **REQ-015.3 — Consulta a serviço externo de débitos / restrições financeiras**: Após o CPF ser validado em REQ-015.2, o sistema deve consultar um serviço externo de débitos para o CPF e capturar:
  - Indicador agregado de existência de restrição (sim/não)
  - Quantidade de ocorrências, quando disponibilizada
  - Score / nota de crédito, quando disponibilizado
  - Data da consulta

  **Provedor**: `[PENDENTE: definir provedor — Serasa Experian, SPC Brasil, Boa Vista (Equifax) ou Quod]`. A escolha depende de:
  - Custo por consulta
  - Cobertura (alguns provedores cobrem mais varejistas que outros)
  - Necessidade de credenciamento / contrato (todos exigem cadastro PJ; nenhum oferece consulta totalmente gratuita)
  - Forma de integração (API REST direta vs. agregadores)

- [ ] **REQ-015.4 — Confirmação dos dados pelo cliente**: O sistema deve **ecoar ao cliente** o CPF capturado para confirmação antes de prosseguir, no mesmo padrão de REQ-001.4 e REQ-002.16. **Não** é exibido ao cliente o resultado da consulta de débitos (informação interna do vendedor).

- [ ] **REQ-015.5 — Disponibilização dos dados para orçamento**: CPF validado e resultado da consulta de débitos devem ficar disponíveis para o vendedor / orçamento (REQ-006), com destaque visual no painel quando houver restrição.

### 4.2 Regras de Negócio

- [ ] **REQ-015.6 — Tratamento de CPF inválido**: Se o CPF informado falhar na validação algorítmica (REQ-015.2), o sistema deve:
  - Informar erro de forma amigável, indicando o motivo (ex: "o CPF informado não é válido — confira os dígitos")
  - Solicitar nova tentativa
  - Permitir até **3 tentativas** na mesma conversa (a inicial + 2 retentativas), seguindo a mesma política de REQ-001.6 para CNPJ
  - Esgotadas as 3 tentativas sem sucesso, **escalar para humano** (REQ-004.9 — baixa confiança / contradição de dados) com o resumo dos valores tentados, evitando manter o cliente em loop
  - Cada tentativa e seu desfecho devem ser registrados como evento (REQ-005.4)

- [ ] **REQ-015.7 — Tratamento de CPF com restrição (dívida)**: Se a consulta de débitos (REQ-015.3) retornar **indicador de restrição**, o sistema deve:
  - **NÃO** negar, bloquear ou interromper o atendimento automaticamente
  - **NÃO** revelar ao cliente o resultado da consulta nem mencionar a existência de restrição
  - Registrar o resultado no contexto da conversa (REQ-005.1 / REQ-005.4)
  - Sinalizar visualmente ao vendedor no painel administrativo (REQ-010) com destaque (ex: badge `⚠️ restrição financeira`)
  - **Escalar para revisão humana** (REQ-004) **antes** de o orçamento ser finalizado, para que o vendedor decida (proceder, pedir pagamento antecipado, recusar, etc.)
  - Manter o fluxo de qualificação prosseguindo normalmente até o ponto da revisão humana

  **Justificativa**: o art. 20 da LGPD garante ao titular o direito de revisão humana de decisões automatizadas que o afetem. Negar orçamento automaticamente com base em consulta de crédito é decisão automatizada de impacto direto e exigiria mecanismos formais de revisão. Em vez disso, o sistema apenas **informa** o vendedor, e a decisão fica humana desde o início.

- [ ] **REQ-015.8 — Tratamento de PF que não fornece CPF**: Se o cliente Pessoa Física não quiser ou não souber informar o CPF na qualificação:
  - O sistema deve aceitar e prosseguir com a qualificação coletando apenas os campos não dependentes de CPF (nome, telefone, endereço de instalação — ver REQ-002.5 para a lista de campos PF)
  - Antes de finalizar o orçamento, o sistema deve **escalar para humano** (REQ-004.9) registrando que a conversa não tem CPF, para que o vendedor decida se pede o CPF na hora da nota fiscal ou se prossegue sem
  - O sistema não deve insistir mais de **2 vezes** na coleta do CPF; respeitada a recusa, segue o fluxo

- [ ] **REQ-015.9 — Persistência do CPF**: O CPF validado deve ser persistido associado ao cliente / conversa para reuso em conversas futuras do mesmo telefone, mas com cuidados específicos (ver REQ-015.13).

- [ ] **REQ-015.10 — Reuso de CPF já validado**: Se cliente já tiver CPF validado em conversa anterior (mesmo telefone), sistema **não** deve pedir CPF novamente, a menos que haja conflito de dados:
  - Cliente informar um CPF diferente em mensagem posterior
  - Cliente solicitar explicitamente troca

  Análogo ao REQ-002.10 para CNPJ.

### 4.3 Requisitos Não-Funcionais e LGPD

- [ ] **REQ-015.11 — Tempo de resposta da consulta de débitos**: Tempo de resposta da consulta externa: < 5 segundos (mais alto que o de CNPJ por característica dos provedores de crédito).

- [ ] **REQ-015.12 — Tratamento de falhas da consulta externa**: Falhas da consulta de débitos (timeout, indisponibilidade) **não** bloqueiam o fluxo:
  - O sistema aplica retry interno
  - Persistindo a falha, prossegue a qualificação **sem** o resultado de débitos e **escala para humano** (REQ-004) sinalizando "consulta indisponível — revisar manualmente"
  - Falhas de infra **não** consomem tentativa do cliente (igual REQ-001.10)

- [ ] **REQ-015.13 — Tratamento LGPD do CPF**: O CPF é **dado pessoal** sob a Lei Geral de Proteção de Dados. O sistema deve:
  - **Finalidade explícita**: solicitar o CPF apenas para fins de elaboração de orçamento e verificação de aptidão financeira
  - **Base legal**: execução de procedimentos preliminares relacionados a contrato a pedido do titular (LGPD art. 7º, V) — em conjunto com legítimo interesse para a consulta de débitos
  - **Informação ao titular**: na primeira solicitação de CPF da conversa, o sistema deve informar ao cliente, em linguagem simples, que o CPF será usado para "elaborar o orçamento e verificar pendências financeiras com nossos parceiros de crédito"
  - **Retenção**: o CPF é mantido enquanto houver relação comercial ativa ou obrigação legal/fiscal (NF emitida, contrato vigente). Após esse período, deve ser **anonimizado** ou removido em rotina de limpeza
  - **Anonimização em logs e auditoria**: registros operacionais (REQ-005), modal de raciocínio (REQ-005.6), reports (REQ-012) e exportações **não** devem conter o CPF em texto pleno — usar mascaramento (ex: `***.456.789-**`) sempre que o dado for exibido em interfaces de operação não destinadas ao orçamento. O CPF completo só aparece nas telas onde é estritamente necessário (cadastro do cliente / detalhe do orçamento)
  - **Não usar em respostas automáticas**: o CPF nunca deve ser ecoado pela IA em respostas livres ao cliente, e nunca deve ser indexado pelo RAG (REQ-003)
  - **Direitos do titular**: cliente pode pedir, em qualquer momento, exclusão dos seus dados — o sistema deve ter um caminho operacional para esse atendimento (mesmo que não automatizado nesta versão)

- [ ] **REQ-015.14 — Auditoria das consultas de débito**: Cada consulta de débitos deve ser registrada como evento (REQ-005.4) com:
  - CPF mascarado
  - Provedor consultado
  - Resultado agregado (com restrição? quantidade de ocorrências? score?)
  - Data/hora
  - Resultado completo da consulta **NÃO** deve ser persistido em texto pleno; manter apenas o agregado e, se necessário, um identificador de transação no provedor para reconsulta

---

## 5. Fluxo de Conversa Esperado

```
Cliente: "Olá, gostaria de orçamento para uma catraca residencial. Sou pessoa física."

Sistema: "Claro! Para preparar seu orçamento, vou precisar do seu CPF.
ℹ️ Usamos seu CPF apenas para elaborar o orçamento e verificar pendências
financeiras com nossos parceiros de crédito. Pode informar?"

Cliente: "123.456.789-09"

Sistema: (valida formato + dígitos)
        (consulta serviço de débitos — resultado: SEM restrição)
        "Anotei o CPF 123.456.789-09. Está correto?"

Cliente: "Sim"

Sistema: "Ótimo! Continuando: qual modelo de catraca? Pedestal, giratória ou cancela?"
... (segue qualificação normal — REQ-002)
```

**Cenário com restrição:**

```
Sistema: (consulta retorna: COM restrição, 3 ocorrências)
        "Anotei o CPF 123.456.789-09. Está correto?"

Cliente: "Sim"

Sistema: (no painel — sem revelar ao cliente)
        ⚠️ Cliente João da Silva — CPF ***.456.789-** — RESTRIÇÃO FINANCEIRA detectada
        (segue qualificação; antes de finalizar orçamento, escala para vendedor revisar)
```

---

## 6. Dependências

### 6.1 Dependências Técnicas
- API externa para consulta de débitos / score de crédito — `[PENDENTE: provedor]`
- Conexão internet estável
- Sistema de tratamento de erros (REQ-015.12)
- Mecanismo de mascaramento de CPF em logs e auditoria (REQ-015.13)

### 6.2 Dependências de Negócio
- Definição do provedor de consulta (custo, cobertura, contrato)
- Texto da informação LGPD apresentada ao cliente (REQ-015.13) — validar com jurídico se houver
- Definição operacional de como o vendedor é alertado em casos de restrição (REQ-010)

### 6.3 Dependências entre Requisitos
- **REQ-001** — Espelho deste requisito para Pessoa Jurídica (CNPJ). Os dois são **mutuamente exclusivos** por conversa, decisão tomada em REQ-002.
- **REQ-002** — Identifica o tipo de cliente (PF/PJ) e roteia para REQ-001 ou REQ-015. Ver REQ-002.X (criado nesta atualização).
- **REQ-004** — Recebe o escalonamento previsto em REQ-015.7 (restrição) e REQ-015.8 (PF sem CPF).
- **REQ-005** — Auditoria das tentativas e da consulta de débitos. CPF removido da lista de "dados sensíveis proibidos" em REQ-005.8.
- **REQ-006** — Recebe o CPF e o indicador de restrição para o orçamento.
- **REQ-010** — Painel exibe o badge de restrição.

---

## 7. Restrições e Limitações

### 7.1 Restrições
- API de consulta de débitos é **paga** em todos os provedores brasileiros relevantes; não há equivalente "BrasilAPI gratuita" como existe para CNPJ.
- Cobertura da consulta varia por provedor (alguns têm mais varejistas, outros mais bancos).
- O sistema **não** acessa dados cadastrais do CPF na Receita Federal (diferente de CNPJ via REQ-001).

### 7.2 Limitações Aceitas no POC
- [ ] Sem cache de consultas de débito (cada conversa nova consulta o provedor — pode ser otimizado em fase posterior, mas o resultado tem caráter temporal e cache prolongado é arriscado)
- [ ] Sem mecanismo automatizado de exclusão de CPF a pedido do titular (REQ-015.13) — atendido por processo manual / abertura de chamado
- [ ] Sem segunda opinião (consultar dois provedores e comparar)

---

## 8. Critérios de Sucesso

### 8.1 Métricas
- Taxa de captura correta de CPF na primeira tentativa: > 90%
- Latência média da consulta de débitos: < 3s (limite duro: 5s — REQ-015.11)
- Falsos positivos no escalonamento por restrição: medir nos primeiros 30 dias após go-live e ajustar threshold se necessário

### 8.2 Condições de Aceite Final
- Vendedor recebe alerta visual quando CPF tem restrição, antes de fechar orçamento
- CPF nunca aparece em texto pleno em logs, modais de raciocínio ou reports
- Cliente é informado da finalidade da coleta na primeira menção a CPF
- 3 tentativas de CPF inválido escalam para humano sem loop

---

## 9. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Provedor de débitos indisponível | Média | Médio | Retry + escalar para humano sem bloquear (REQ-015.12) |
| Custo da consulta inviabilizar o uso | Média | Alto | Avaliar volume estimado antes de fechar contrato; restringir consulta a CPF aprovado por REQ-015.2 |
| Vazamento de CPF em logs | Baixa | Alto | Mascaramento obrigatório (REQ-015.13); revisão de código focada em logs |
| Cliente recusar fornecer CPF (perda de lead) | Média | Médio | REQ-015.8 permite seguir sem CPF; vendedor decide |
| Falso positivo de restrição (homonímia, dado desatualizado) | Média | Médio | Não negar automaticamente — sempre revisão humana (REQ-015.7) |
| Decisão automatizada violar LGPD art. 20 | Baixa | Alto | REQ-015.7 explicitamente proíbe negação automática |

---

## 10. Estimativas

| Atividade | Horas |
|-----------|-------|
| Pesquisa e seleção do provedor de débitos | 4h |
| Implementação de validação algorítmica de CPF | 2h |
| Implementação da consulta externa | 4h |
| Mascaramento de CPF em logs e UI | 3h |
| Texto LGPD de informação ao cliente + revisão | 2h |
| Integração com REQ-002 (PF/PJ) e REQ-004 (escalonamento) | 4h |
| Testes e ajustes | 4h |
| **Total** | **23h** |

---

## 11. Histórico de Alterações

| Data | Versão | Alteração | Autor |
|------|--------|-----------|-------|
| 01/06/2026 | 1.0 | Criação inicial do requisito (par PF de REQ-001). Inclui validação algorítmica de CPF, consulta de débitos via provedor externo (a definir), tratamento explícito de restrição sem decisão automatizada (LGPD art. 20), tratamento LGPD detalhado e integração com REQ-002 (PF/PJ). | Kika |

---

## 12. Aprovações

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| Analista de Requisitos | Kika | 01/06/2026 | [ ] |
| Cliente (Inforrel) | Rita | ____/____/____ | [ ] |
| Líder Técnico | Beto | ____/____/____ | [ ] |
