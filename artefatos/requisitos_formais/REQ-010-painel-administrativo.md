# REQ-010: Painel Administrativo (POC)

<!-- CLASSIFICACAO: SISTEMA-CAIXAPRETA -->
<!-- CLASSIFICACAO: IA -->

**Versão**: 1.4  
**Data**: 2026-07-14  
**Autor**: Kika (Analista de Requisitos)  
**Status**: Em Elaboração  
**Prioridade**: Média  

---

## 1. Identificação do Requisito

**ID**: REQ-010  
**Tipo**: Funcional  
**Categoria**: Operação / Interface Administrativa  
**Solicitante**: Necessidade do produto (operação do vendedor)  

---

## 2. Descrição

O sistema deve oferecer uma **interface administrativa web** (painel) que permita ao vendedor operar o sistema de atendimento sem depender exclusivamente do WhatsApp. O painel é o ponto único de:

- Consulta de orçamentos (REQ-006)
- Atualização manual do status de orçamentos (REQ-006.8)
- Consulta de histórico de conversas (REQ-005)
- Visualização de escalonamentos pendentes (REQ-004)

Este requisito **formaliza** a interface administrativa que hoje é assumida implicitamente em outros requisitos (especialmente REQ-006), eliminando a inconsistência entre os REQs que dizem "sem dashboard no POC" (REQ-004, REQ-005, REQ-007) e os que pressupõem um painel (REQ-006).

**Importante**: o painel **não substitui o WhatsApp** como canal principal de resposta ao cliente no POC. Ele é uma camada de **gestão e auditoria**, não de atendimento em tempo real.

---

## 3. Justificativa de Negócio

**Problema Atual**:
- REQ-006 exige operação manual (atualizar status, consultar orçamentos) sem interface definida
- Sem um lugar único para gestão, o vendedor acaba dependendo de planilhas paralelas, perdendo rastreabilidade
- Outros REQs apontam "sem dashboard" como limitação, mas isso conflita com a operação real

**Benefício Esperado**:
- Operação centralizada (orçamentos, conversas, escalonamentos em um só lugar)
- Auditabilidade efetiva dos dados registrados pelo sistema (REQ-005, REQ-006)
- Base para evolução pós-POC (relatórios, métricas, multi-usuário)

---

## 4. Critérios de Aceite

### 4.1 Autenticação e Acesso

- [ ] **REQ-010.1 — Acesso restrito por autenticação**: O painel deve exigir autenticação para qualquer acesso (login com usuário e senha no POC)

- [ ] **REQ-010.2 — Identidade do usuário registrada**: Toda ação realizada no painel deve ser associada ao usuário autenticado, para fins de auditoria (REQ-006.10, REQ-005)

- [ ] **REQ-010.3 — Usuário único no POC**: No POC, há apenas um usuário operacional (o vendedor). A estrutura deve, no entanto, permitir adicionar novos usuários no futuro sem refatoração estrutural

- [ ] **REQ-010.4 — Sessão com expiração**: Sessão autenticada deve expirar após período de inatividade (sugestão: 8 horas), exigindo novo login

### 4.2 Telas Mínimas (POC)

- [ ] **REQ-010.5 — Tela de orçamentos**: Lista de orçamentos com filtros por período, cliente e status (atende REQ-006.11), e ação "Atualizar status" por orçamento (atende REQ-006.8)

- [ ] **REQ-010.6 — Tela de detalhe do orçamento**: Visualização consolidada de um orçamento (atende REQ-006.12), incluindo:
  - Conteúdo/referência do orçamento (REQ-006.4)
  - Histórico de status (REQ-006.6)
  - Conversa relacionada (link para tela de conversa)
  - Dados coletados na qualificação (REQ-002)

- [ ] **REQ-010.7 — Tela de histórico de conversas**: Visualização das conversas registradas, com filtros básicos (cliente, período, estado), atendendo às consultas previstas no REQ-005

- [ ] **REQ-010.7A — Identificação do cliente no cabeçalho da tela de conversa**: Quando uma conversa for selecionada e exibida em detalhe, o cabeçalho da tela de chat deve identificar o cliente de forma adequada ao **tipo de cliente** (REQ-002.2A):

  - **Pessoa Jurídica (PJ)**: exibir o **nome fantasia** retornado pela consulta do CNPJ (REQ-001.3); na ausência de nome fantasia, exibir a **razão social**. O CNPJ pode aparecer como subtítulo ou tooltip.
  - **Pessoa Física (PF)**: exibir o **nome do solicitante** capturado em REQ-002.3C. O CPF **nunca** deve aparecer no cabeçalho em texto pleno; quando exibido, usar mascaramento (ex.: `***.456.789-**`), conforme REQ-015.13 e REQ-005.8.
  - **Tipo não identificado** (cliente ainda não classificado em PF/PJ): exibir o telefone como identificador primário com indicador visual de "em qualificação".

  **Subtítulo / metadados secundários** (sempre visíveis sob o nome principal): telefone do cliente, badge `PF` ou `PJ`, **indicador do atendimento atual** no formato `Atendimento #N` (REQ-016.14 — onde `N` é o `numero_atendimento_cliente`), e quando aplicável o badge `⚠️ restrição financeira` (REQ-015.7) para conversas de PF com restrição detectada.

  **Exemplo de cabeçalho consolidado**:
  - PJ: `ACME Comercial Ltda` / `(11) 99999-0000 · PJ · Atendimento #3`
  - PF: `João da Silva` / `(11) 98888-0000 · PF · Atendimento #1 · ⚠️ restrição financeira`

  **Comportamento ao trocar de tipo durante a conversa** (REQ-002.10): quando a mudança de tipo for confirmada e um novo documento fiscal coletado, o cabeçalho deve refletir o novo identificador. Conversas históricas mantêm o identificador vigente à época.

- [ ] **REQ-010.7B — Exibição da fase e campos pendentes no topo da conversa**: Quando uma conversa for exibida em detalhe, o topo da tela (junto ao cabeçalho REQ-010.7A) deve mostrar:

  1. **Fase atual do atendimento** — badge visual indicando em qual fase o atendimento se encontra (`Esclarecendo`, `Finalizando`, `Em orçamentação`, etc.), conforme REQ-002.1C.
  2. **Campos pendentes para orçamento** — lista dos campos ainda não capturados (`campos_pendentes()`), exibidos como indicadores visuais (ex.: pills com status pendente/capturado). Inclui campos como `CAMPO-modelo`, `CAMPO-software-ponto`, `CAMPO-faixa-funcionarios`, `CAMPO-quantidade`, `CAMPO-endereco`, `CAMPO-contato`, tipo de cliente PF/PJ, etc.
  3. **Campos já capturados** — exibidos com status "capturado" e o valor resumido, para que o vendedor tenha visão rápida do progresso da coleta sem precisar ler toda a conversa.

  **Regras**:
  - A informação é **somente leitura** (o vendedor não edita campos por aqui no POC).
  - Os campos exibidos variam conforme o tipo de produto identificado (REQ-002.3A) — só aparecem campos aplicáveis ao produto do atendimento.
  - Quando todos os campos estiverem capturados, exibir indicador de "coleta completa" (ex.: ✓ Pronto para orçamento).
  - Quando o atendimento estiver em `em_orcamentacao` ou encerrado, os campos aparecem todos como capturados (histórico).

- [ ] **REQ-010.8 — Tela de escalonamentos**: Lista de conversas escaladas para humano (REQ-004), com indicação de pendência e link para a conversa

### 4.3 Ações Administrativas

- [ ] **REQ-010.9 — Atualização manual de status do orçamento**: Implementação concreta do REQ-006.8, com validações, confirmação antes de aplicar e registro de autoria (REQ-006.10)

- [ ] **REQ-010.10 — Consulta sem alteração de dados**: Telas de histórico (REQ-005) e de conversa devem ser **somente leitura** no POC (sem edição de mensagens registradas, conforme imutabilidade do REQ-005)

### 4.4 Requisitos Não-Funcionais

- [ ] **REQ-010.11 — Tempo de resposta razoável**: Telas de listagem devem carregar em menos de 3 segundos para volumes típicos do POC (até alguns milhares de orçamentos/conversas)

- [ ] **REQ-010.12 — Compatibilidade com navegadores modernos**: Painel deve funcionar em Chrome, Firefox e Edge atualizados; não há exigência de suporte a navegadores legados

- [ ] **REQ-010.13 — Layout responsivo mínimo**: Painel deve ser usável em desktop; uso em mobile não é prioridade no POC mas deve degradar de forma aceitável

---

## 5. Integração com Requisitos Existentes

| REQ | Como o painel atende |
|-----|----------------------|
| **REQ-002** | Exibe dados coletados na qualificação dentro do detalhe do orçamento e da conversa; o tipo de cliente (REQ-002.2A) e o nome do solicitante (REQ-002.3C) alimentam o cabeçalho do chat (REQ-010.7A); fase atual e campos pendentes/capturados exibidos no topo da conversa (REQ-010.7B, conforme REQ-002.1C e REQ-002.3) |
| **REQ-001 / REQ-015** | Nome fantasia / razão social (REQ-001.3) e nome do solicitante PF (REQ-015 + REQ-002.3C) são os identificadores exibidos no cabeçalho da tela de conversa (REQ-010.7A); CPF sempre mascarado conforme REQ-015.13 |
| **REQ-016** | Número sequencial do atendimento (`numero_atendimento_cliente`) é exibido no cabeçalho do chat (REQ-010.7A), na lista de orçamentos (REQ-010.5) e no detalhe do orçamento (REQ-010.6) — conforme REQ-016.14. Painel permite navegação a partir do atendimento para suas conversas e orçamentos (REQ-016.15), e ações de encerrar/reabrir atendimento manualmente (REQ-016.8) |
| **REQ-004** | Tela de escalonamentos (REQ-010.8) dá visibilidade de conversas que precisam de atenção humana |
| **REQ-005** | Telas de consulta (REQ-010.7) materializam o "endpoint/admin simples" mencionado como limitação POC |
| **REQ-006** | Painel é a interface concreta para REQ-006.8, REQ-006.11 e REQ-006.12 |
| **REQ-007** | Indicadores de sentimento podem ser exibidos na tela de conversa (não obrigatório no POC) |

---

## 6. Limitações Aceitas no POC

- [ ] Apenas o vendedor como usuário operacional
- [ ] Sem perfis de permissão (todo usuário autenticado tem acesso pleno no POC)
- [ ] Sem responder ao cliente diretamente pelo painel — resposta continua pelo WhatsApp (alinhado com REQ-004)
- [ ] Sem relatórios analíticos avançados (gráficos, exportações, métricas de funil)
- [ ] Sem notificações em tempo real (push, e-mail) a partir do painel
- [ ] Sem auditoria de acesso (quem viu o quê) — apenas auditoria de alterações

---

## 7. Dependências

### 7.1 Dependências Técnicas
- Frontend (React + Vite + TailwindCSS, conforme stack do projeto)
- Backend (FastAPI) com endpoints para listar/atualizar orçamentos, listar conversas, listar escalonamentos
- Mecanismo de autenticação (sugestão: JWT simples no POC)
- Persistência já estabelecida pelos REQ-005 e REQ-006

### 7.2 Dependências de Negócio
- Definir credencial inicial do vendedor
- Validar com o vendedor as telas mínimas antes da implementação

---

## 8. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Painel virar "tudo ou nada" e atrasar o POC | Média | Alto | Manter escopo nas telas mínimas (4.2) e adiar relatórios |
| Vendedor preferir continuar usando WhatsApp e ignorar o painel | Média | Médio | Validar UX com ele antes de implementar; tornar atualização de status simples |
| Falta de autenticação robusta | Baixa | Alto | Usar biblioteca consolidada de auth no POC; revisar antes de produção |
| Inconsistência entre dados do painel e do banco | Baixa | Alto | Painel sempre lê do banco oficial (sem cache local) |

---

## 9. Estimativas

| Atividade | Horas |
|-----------|-------|
| Estrutura base do painel (layout, navegação, autenticação) | 8h |
| Tela de orçamentos (lista + filtros + ação de atualizar status) | 6h |
| Tela de detalhe do orçamento | 4h |
| Tela de histórico de conversas (somente leitura) | 5h |
| Tela de escalonamentos | 3h |
| Endpoints backend para suportar as telas | 6h |
| Testes e ajustes de UX com o vendedor | 4h |
| **Total** | **36h** |

---

## 10. Histórico de Alterações

| Data | Versão | Alteração | Autor |
|------|--------|-----------|-------|
| 12/05/2026 | 1.0 | Criação inicial do requisito para formalizar o painel administrativo do POC, eliminando inconsistência entre REQs que assumem dashboard (REQ-006) e os que dizem "sem dashboard" (REQ-004, REQ-005, REQ-007) | Kika |
| 01/06/2026 | 1.1 | Criação do REQ-010.7A (identificação do cliente no cabeçalho da tela de conversa): PJ exibe nome fantasia / razão social (REQ-001.3); PF exibe nome do solicitante (REQ-002.3C), com CPF sempre mascarado (REQ-015.13); subtítulo com telefone, badge PF/PJ e badge de restrição financeira (REQ-015.7); tratamento de mudança de tipo durante a conversa (REQ-002.10). Tabela de integração com requisitos atualizada para incluir REQ-001 e REQ-015. | Kika |
| 01/06/2026 | 1.2 | REQ-010.7A: inclusão do indicador `Negociação #N` no subtítulo do cabeçalho (REQ-016.12); exemplos consolidados PF/PJ com badges. Tabela de integração ampliada para incluir REQ-016 (numeração e navegação por negociação). | Kika |
| 09/06/2026 | 1.3 | Renomeação Negociação → Atendimento em todas as referências de UI: cabeçalho (`Atendimento #N`), exemplos PF/PJ, tabela de integração com REQ-016 v2.0. Painel passa a expor ações de encerrar/reabrir atendimento (REQ-016.8) decorrentes do novo ciclo de vida `ativo`/`encerrado`. | Beto |
| 14/07/2026 | 1.4 | Criação do REQ-010.7B (exibição da fase atual e campos pendentes/capturados no topo da tela de conversa). Tabela de integração com REQ-002 atualizada. | Cascade |

---

## 11. Aprovações

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| Analista de Requisitos | Kika | 12/05/2026 | [ ] |
| Cliente (Inforrel) | Rita | ____/____/____ | [ ] |
| Líder Técnico | Beto | ____/____/____ | [ ] |
