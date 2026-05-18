# REQ-011: Modos de Execução e Workflow de Aprovação Humana de Mensagens

**Versão**: 1.2
**Data**: 2026-05-18
**Autor**: Kika (Analista de Requisitos)
**Status**: Em Elaboração
**Prioridade**: Alta

---

## 1. Identificação do Requisito

**ID**: REQ-011
**Tipo**: Funcional
**Categoria**: Operação / Governança da IA / Configuração do Sistema
**Solicitante**: Necessidade do produto (Beto + operação do vendedor)

---

## 2. Descrição

O sistema deve oferecer **três modos de execução** configuráveis que controlam como as mensagens geradas pela IA chegam (ou não chegam) ao cliente, e qual o papel do vendedor no fluxo:

- **Modo 1 — Simulação**: usado em fase de teste/desenvolvimento. Não há integração com WhatsApp; mensagens "do cliente" e "do sistema" são trocadas exclusivamente pelo painel administrativo (REQ-010). Toda mensagem gerada pela IA passa por aprovação/reprovação do usuário, com possibilidade de **feedback textual** tanto na aprovação quanto na reprovação.
- **Modo 2 — Conversa controlada**: mensagens do cliente chegam pelo WhatsApp (REQ-008) normalmente, mas as mensagens geradas pela IA **não são enviadas automaticamente** — ficam pendentes no painel até o vendedor aprovar (envia para o cliente) ou reprovar (não envia; opcionalmente gera correção). Modo recomendado para operação supervisionada, validação em produção e construção da base Q&A com feedback real.
- **Modo 3 — Execução normal**: operação plena. Mensagens fluem direto pelo WhatsApp em ambos os sentidos, sem aprovação manual. Só deve ser ativado depois de o sistema atingir nível de confiança suficiente.

Este requisito **formaliza** o workflow de aprovação que hoje já existe parcialmente implementado no código (endpoints `/api/mensagens/pendentes`, `/api/mensagens/{id}/aprovar`, `/api/mensagens/{id}/reprovar` e UI `AcompanhamentoPage`), encaixando-o num modelo de três modos de execução com configuração explícita.

---

## 3. Justificativa de Negócio

**Problema Atual**:
- O sistema só pode ser avaliado de forma segura se houver um caminho controlado para revisar respostas antes de enviá-las ao cliente.
- Sem um modo de simulação claro, qualquer teste consome mensagens reais e expõe o cliente a respostas potencialmente incorretas.
- Sem um modo controlado, é arriscado migrar do POC para produção sem validação humana prévia.
- O fluxo de aprovação/reprovação já existe no código, mas não está formalizado como requisito — gera dívida de rastreabilidade entre o que está implementado e o que está documentado.

**Benefício Esperado**:
- **Segurança progressiva**: três níveis bem definidos permitem evoluir do teste para a operação plena com baixo risco.
- **Curadoria contínua**: aprovações/reprovações com feedback alimentam a base Q&A (REQ-003) e os reports de problema, melhorando a IA ao longo do tempo.
- **Auditabilidade**: cada decisão humana sobre uma mensagem fica registrada, junto ao motivo/feedback.
- **Desacoplamento entre canal e cérebro**: o mesmo cérebro funciona em simulação ou em WhatsApp real, mudando apenas o modo.

---

## 4. Critérios de Aceite

### 4.1 Configuração do Modo de Execução

- [ ] **REQ-011.1 — Configuração global do modo de execução**: O sistema deve suportar a configuração de **um modo de execução vigente** entre três valores:
  - `simulacao`
  - `conversa_controlada`
  - `execucao_normal`

  No POC, a configuração pode ser **global** (um único modo para todo o sistema). A configuração deve ser **persistente** (não pode ser perdida ao reiniciar o backend) e **alterável em tempo de execução** por usuário autorizado pelo painel (REQ-010), sem necessidade de redeploy.

- [ ] **REQ-011.2 — Granularidade por negociação (futura, opcional no POC)**: A estrutura do modo de execução deve permitir, em versões futuras, definir modo distinto **por negociação** (ex: uma conversa específica em `conversa_controlada` mesmo com o sistema globalmente em `execucao_normal`). No POC, o sistema pode operar apenas com modo global, mas o modelo de dados não deve impedir essa evolução.

- [ ] **REQ-011.3 — Registro de troca de modo**: Toda mudança do modo de execução vigente deve gerar um evento auditavel no histórico (REQ-005), contendo:
  - Modo anterior e modo novo
  - Timestamp da mudança
  - Usuário que aplicou a mudança (REQ-010.2)

### 4.2 Modo 1 — Simulação

- [ ] **REQ-011.4 — Canal de mensagens em simulação**: Em modo `simulacao`, o sistema **não deve** integrar com WhatsApp (REQ-008). Toda troca de mensagens ocorre pelo **painel administrativo** (REQ-010):
  - O usuário (vendedor / tester) digita uma mensagem "como se fosse o cliente" diretamente no painel
  - O sistema processa a mensagem (REQ-002 / REQ-003) e gera a resposta automática como em qualquer outro modo
  - A resposta gerada **não sai do painel** até ser aprovada ou reprovada

- [ ] **REQ-011.5 — Aprovação obrigatória de toda mensagem gerada**: Em `simulacao`, toda mensagem gerada pelo sistema (origem `SYSTEM`) deve entrar em estado **pendente de aprovação**. O sistema não deve "enviar" a mensagem (entregar ao destinatário simulado nem persistir como entregue) enquanto não houver decisão humana.

- [ ] **REQ-011.6 — Feedback opcional na aprovação**: Ao aprovar uma mensagem, o usuário pode opcionalmente registrar **feedback textual**, com a semântica de:
  - "A mensagem está correta, mas poderia ser melhorada em algum detalhe (ex: tom, clareza, sugestão de complementar com tal informação)"

  O feedback fica vinculado à mensagem e ao processamento que a gerou (REQ-005.6), permitindo análise posterior.

- [ ] **REQ-011.7 — Feedback obrigatório/recomendado na reprovação**: Ao reprovar uma mensagem, o usuário deve registrar feedback textual com a semântica de:
  - "A mensagem está errada — descrever por quê (intenção mal classificada, fato incorreto, tom inapropriado, fluxo errado, etc.)"

  O feedback é **fortemente recomendado** na reprovação (idealmente obrigatório no POC) e fica vinculado à mensagem, ao processamento que a gerou e, quando aplicável, ao report de problema correspondente.

- [ ] **REQ-011.8 — Sem efeito no canal real**: Em `simulacao`, nem aprovações nem reprovações disparam envio para o WhatsApp. As decisões servem apenas para construir histórico, curar base Q&A (REQ-003) e gerar reports de problema (workflow já existente).

### 4.3 Modo 2 — Conversa Controlada

- [ ] **REQ-011.9 — Mensagens do cliente via WhatsApp**: Em `conversa_controlada`, as mensagens recebidas do cliente fluem pelo canal WhatsApp normalmente (REQ-008), incluindo deduplicação, registro no histórico (REQ-005) e processamento pelo cérebro.

- [ ] **REQ-011.10 — Mensagens da IA ficam pendentes no painel**: Em `conversa_controlada`, toda mensagem gerada pelo sistema (origem `SYSTEM`) deve ficar em estado **pendente de aprovação** no painel administrativo, **antes de ser enviada** ao WhatsApp do cliente. O sistema **não pode** disparar envio Twilio até existir decisão humana.

- [ ] **REQ-011.11 — Envio efetivo após aprovação**: Quando o vendedor aprovar uma mensagem pendente no `conversa_controlada`, o sistema deve:
  - Disparar o envio efetivo via WhatsApp (REQ-008.5)
  - Registrar timestamp do envio (REQ-005.2)
  - Registrar quem aprovou e quando (REQ-010.2, REQ-011.16)
  - Permitir feedback opcional na aprovação (mesma semântica do REQ-011.6)

- [ ] **REQ-011.12 — Reprovação no `conversa_controlada`**: Quando o vendedor reprovar uma mensagem pendente no `conversa_controlada`, o sistema deve:
  - **Não enviar** a mensagem ao WhatsApp
  - Registrar a reprovação com feedback (mesma semântica do REQ-011.7)
  - Gerar/atualizar report de problema associado ao processamento (workflow já existente)
  - Manter o cliente **sem resposta automática naquela rodada**; o vendedor pode optar por:
    - Responder manualmente pelo WhatsApp (caminho atual do POC)
    - Editar a mensagem reprovada e aprovar a versão corrigida (opcional, ver REQ-011.15)
    - Solicitar ao sistema que reprocesse a mensagem do cliente para gerar nova proposta (opcional pós-POC)

- [ ] **REQ-011.13 — SLA de aprovação no `conversa_controlada`**: O painel deve sinalizar visualmente mensagens pendentes há muito tempo. Sugestão de limiar inicial: **alerta visual após 10 minutos** sem decisão. O limiar deve ser configurável.

- [ ] **REQ-011.14 — Respeito ao estado "em atendimento humano"**: Quando a negociação estiver em estado `Em atendimento humano` (REQ-004.4) **independentemente do modo de execução**, o sistema não deve gerar respostas automáticas para aprovação (alinhado a REQ-004.10). Isso vale para `simulacao`, `conversa_controlada` e `execucao_normal`.

- [ ] **REQ-011.15 — Edição da mensagem antes de aprovar (opcional)**: O painel pode permitir que o vendedor **edite o texto** de uma mensagem pendente antes de aprovar. Quando isso ocorrer:
  - O texto final enviado deve ser persistido (REQ-005.2)
  - A versão original (gerada pela IA) deve ser preservada como referência, junto ao motivo da edição (mesma semântica de feedback do REQ-011.6)
  - **Deve disparar a criação automática de um report** em REQ-012 (ver REQ-012.2A) com categoria default `template` e severidade default `baixa`. A edição sinaliza que o texto original era subótimo e deve alimentar a melhoria contínua, mesmo quando a mensagem final é aprovada e enviada.
  - Considerado **opcional no POC**, mas estrutura deve permitir.

### 4.4 Modo 3 — Execução Normal

- [ ] **REQ-011.16 — Envio direto pelo WhatsApp sem aprovação**: Em `execucao_normal`, mensagens geradas pela IA são enviadas automaticamente ao cliente via WhatsApp (REQ-008.5), sem etapa de aprovação humana. Aplicam-se normalmente:
  - Regras de bloqueio quando em atendimento humano (REQ-004.10, REQ-011.14)
  - Regras de fallback e escalonamento (REQ-003.7, REQ-004.9)
  - Registro de histórico (REQ-005)

- [ ] **REQ-011.17 — Feedback retroativo de mensagens da IA**: Mesmo em `execucao_normal`, o painel deve permitir que o vendedor registre **feedback retroativo** sobre mensagens **geradas automaticamente pelo sistema** já enviadas (ex: "essa resposta estava errada", "essa resposta podia ser melhor"). Esse feedback gera report de problema (workflow já existente), permitindo melhoria contínua sem bloquear o canal.

- [ ] **REQ-011.17A — Feedback retroativo de mensagens manuais (pós-POC)**: O painel deve permitir que um usuário com perfil de **coordenador** ou **vendedor sênior** revise **mensagens enviadas manualmente por outros vendedores** (em qualquer modo de execução, mas especialmente em `execucao_normal` e durante o uso humano do canal), com o objetivo de avaliar se o atendimento humano está adequado e propor correções.

  **Funcionalidades esperadas**:
  - Listagem de mensagens manuais enviadas pelos vendedores, com filtros por vendedor, período e negociação
  - Visualização da conversa completa em torno da mensagem para entender o contexto
  - Registro de feedback estruturado pelo coordenador, no mínimo:
    - Classificação: `correta`, `correta com sugestão de melhoria`, `incorreta`
    - Texto livre com a observação
    - Sugestão de **texto corrigido**, quando aplicável
  - Quando houver sugestão de correção, o sistema deve **enviar a sugestão para o WhatsApp do vendedor que escreveu a mensagem original**, em formato claro (ex: "Mensagem original: ... / Sugestão de correção: ... / Observação: ..."), para que o vendedor aprenda e, se quiser, reenvie uma mensagem corrigida ao cliente
  - Toda revisão deve ser registrada como evento auditável (REQ-005), vinculada à mensagem original, ao coordenador que revisou e ao vendedor revisado

  **Pré-requisitos**:
  - Suporte a perfis/papéis de usuário (`vendedor`, `vendedor_senior`/`coordenador`) — extensão de REQ-010.1 / REQ-010.2 / REQ-010.3, que no POC só prevêem usuário único sem perfis
  - Cadastro do WhatsApp do vendedor para que o sistema saiba para qual número enviar a sugestão de correção
  - Política sobre privacidade/visibilidade: deixar claro entre os vendedores que mensagens manuais podem ser revisadas

  **Fora do escopo do POC**. Este subitem é registrado como **funcionalidade interessante para evolução pós-POC**; a estrutura de dados e modelos não precisa contemplá-lo agora, mas o sistema **não deve adotar decisões de design** (ex: anonimizar autor da mensagem, descartar histórico de quem enviou) que **impeçam** sua implementação futura.

- [ ] **REQ-011.18 — Promoção controlada para `execucao_normal`**: A transição de `conversa_controlada` para `execucao_normal` deve ser uma **decisão consciente** do vendedor/administrador, feita no painel. O sistema deve apresentar:
  - Indicador de quantas mensagens foram aprovadas vs. reprovadas no período recente (ex: últimos 100 ou últimos 7 dias)
  - Confirmação explícita antes de aplicar a mudança
  - Registro do evento (REQ-011.3)

  Esta é uma diretriz de uso responsável; o sistema **não deve impedir** a transição, apenas dar visibilidade.

### 4.5 Registro e Auditoria (todos os modos)

- [ ] **REQ-011.19 — Registro completo da decisão humana**: Para cada mensagem que passa por aprovação/reprovação (modos `simulacao` ou `conversa_controlada`), o sistema deve registrar:
  - Mensagem original gerada pela IA
  - Mensagem efetivamente enviada (idêntica à original, ou editada — ver REQ-011.15)
  - Decisão: `aprovada` ou `reprovada`
  - Usuário que decidiu (REQ-010.2)
  - Timestamp da decisão
  - Feedback textual (quando fornecido)
  - Vínculo ao `processamento_id` que gerou a mensagem (REQ-005.6)
  - Vínculo ao `report_problema_id` quando a reprovação gerar report

- [ ] **REQ-011.20 — Não retroatividade do modo**: A troca do modo de execução **não altera retroativamente** mensagens já decididas. Mensagens pendentes no momento da troca seguem regras do modo anterior até serem resolvidas, ou o sistema deve oferecer ação explícita para reaplicar regras do novo modo (a definir; tratamento mínimo no POC: pendências permanecem como estão).

### 4.6 Requisitos Não-Funcionais

- [ ] **REQ-011.21 — Tempo de resposta da listagem de pendentes**: A tela de mensagens pendentes deve carregar em menos de 2 segundos para volumes típicos do POC (até centenas de pendências).

- [ ] **REQ-011.22 — Indicação visual do modo vigente**: O painel deve exibir, de forma visível em todas as telas, qual o modo de execução vigente, com cores ou rótulos distintos por modo (ex: `simulacao` em tom de teste, `conversa_controlada` em tom de atenção, `execucao_normal` em tom neutro/operacional).

- [ ] **REQ-011.23 — Idempotência das ações de aprovação/reprovação**: Aprovar ou reprovar uma mensagem já decidida deve ser **bloqueado** (não permitido sobrescrever), retornando erro claro. Correções devem ser registradas como **novos eventos** (alinhado a REQ-005.7).

---

## 5. Integração com Requisitos Existentes

| REQ | Como o REQ-011 se relaciona |
|-----|-----------------------------|
| **REQ-002** | Em todos os modos, o REQ-002 continua gerando perguntas/respostas. A diferença é o que acontece com a mensagem **após** ser gerada. |
| **REQ-003** | Idem REQ-002. Reprovações no `simulacao` e `conversa_controlada` alimentam a curadoria da base Q&A. |
| **REQ-004** | O estado "em atendimento humano" suspende geração automática em **qualquer** modo (REQ-011.14), mantendo a regra do REQ-004.10. |
| **REQ-005** | Todas as decisões geram eventos auditáveis (REQ-005.4). Feedback fica vinculado ao processamento (REQ-005.6). |
| **REQ-008** | Apenas `conversa_controlada` e `execucao_normal` usam Twilio. `simulacao` é completamente desacoplada do canal real. |
| **REQ-010** | O painel é onde toda decisão acontece (aprovar/reprovar/editar/trocar modo). Telas afetadas: nova tela "Pendentes" + ação de aprovação na tela de conversas + ajuste de cabeçalho com modo vigente. |
| **REQ-012** | REQ-011 é a principal **fonte** de reports de problema (mas não a única). Reprovações (REQ-011.7 / REQ-011.12) disparam criação automática via REQ-012.2; edições antes de aprovar (REQ-011.15) disparam via REQ-012.2A; feedback retroativo (REQ-011.17 / REQ-011.17A) usa o caminho manual avulso (REQ-012.3). Após a criação, o report **vive sob REQ-012** (triagem, status, resolução). Ver §2.1 e §2.2 do REQ-012 para a fronteira detalhada. |

---

## 6. Fluxos (alto nível)

### 6.1 Modo Simulação

```
1) Usuário digita mensagem "do cliente" no painel
2) Sistema processa via cérebro (REQ-002 / REQ-003)
3) Sistema gera resposta SYSTEM como "pendente"
4) Usuário aprova (com feedback opcional) OU reprova (com feedback)
5) Sistema registra decisão + feedback no histórico
6) Nada é enviado para WhatsApp
```

### 6.2 Modo Conversa Controlada

```
1) Cliente envia mensagem pelo WhatsApp
2) Sistema recebe via webhook (REQ-008), registra (REQ-005)
3) Sistema processa via cérebro
4) Sistema gera resposta SYSTEM como "pendente"
5) Painel mostra mensagem pendente para o vendedor
6a) Vendedor aprova → sistema envia via Twilio + registra envio
6b) Vendedor reprova → sistema NÃO envia, gera report, vendedor decide próximo passo
```

### 6.3 Modo Execução Normal

```
1) Cliente envia mensagem pelo WhatsApp
2) Sistema recebe via webhook, registra
3) Sistema processa via cérebro
4) Sistema envia resposta direto via Twilio
5) Painel mostra histórico e permite feedback retroativo (opcional)
```

---

## 7. Limitações Aceitas no POC

- [ ] Modo global (sem granularidade por negociação — REQ-011.2 fica para versão futura).
- [ ] Edição de mensagem antes de aprovar (REQ-011.15) é opcional no POC.
- [ ] Reprocessamento automático após reprovação não é coberto pelo POC.
- [ ] Alertas de SLA (REQ-011.13) podem ser apenas visuais; notificação push/e-mail fora do escopo.
- [ ] Sem fluxo de aprovação em múltiplos níveis (apenas uma decisão humana basta).
- [ ] **Revisão de mensagens manuais por coordenador / vendedor sênior (REQ-011.17A) fica fora do POC**, mas o sistema não deve adotar decisões de design que impeçam sua implementação futura.

---

## 8. Dependências

### 8.1 Dependências Técnicas
- REQ-010 (painel administrativo) — telas e autenticação
- REQ-008 (Twilio) — apenas para `conversa_controlada` e `execucao_normal`
- REQ-005 (histórico) — para registrar decisões e feedback
- Mecanismo já existente no código:
  - Endpoints `/api/mensagens/pendentes`, `/api/mensagens/{id}/aprovar`, `/api/mensagens/{id}/reprovar`
  - Campos `aprovador_id`, `timestamp_aprovacao`, propriedade `pendente_aprovacao` em `Mensagem`
  - UI base em `AcompanhamentoPage.jsx` (com modal de reprovação que já cria rascunho Q&A)

### 8.2 Dependências de Negócio
- Definir limiar de SLA de aprovação no `conversa_controlada` (REQ-011.13)
- Definir critérios mínimos antes de o vendedor promover para `execucao_normal` (REQ-011.18)

---

## 9. Restrições e Limitações

### 9.1 Restrições
- O sistema **nunca** deve enviar mensagem ao cliente sem decisão humana enquanto estiver em `simulacao` ou `conversa_controlada`.
- A configuração de modo deve ser **persistente** (não pode ser perdida ao reiniciar) — não pode ser apenas variável em memória.

### 9.2 Inconsistências resolvidas por este REQ
- O REQ-008 atualmente assume que mensagens fluem livremente pelo WhatsApp; este REQ deixa explícito que o **envio efetivo** depende do modo de execução vigente.
- O fluxo de aprovação/reprovação já implementado deixa de ser "funcionalidade órfã" e passa a ter requisito formal de referência.

---

## 10. Critérios de Sucesso

### 10.1 Métricas
- Em `conversa_controlada`: taxa de aprovação de mensagens > 80% indica que o sistema pode ser candidato à promoção para `execucao_normal`.
- Em `simulacao`: cada reprovação deve gerar feedback (≥ 95% das reprovações com feedback preenchido).
- Tempo médio de decisão (aprovar/reprovar) no `conversa_controlada`: alvo < 5 minutos por mensagem.

### 10.2 Condições de Aceite Final
- Os três modos coexistem no sistema e podem ser alternados pelo painel.
- Mensagens pendentes nunca vazam para o cliente sem decisão humana em `simulacao` e `conversa_controlada`.
- Feedback (aprovação e reprovação) é registrado, vinculado ao processamento e consultável.
- Vendedor consegue operar o sistema em `conversa_controlada` antes de migrar para `execucao_normal`.

---

## 11. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Vendedor não aprova mensagens em tempo hábil no `conversa_controlada` | Média | Alto | SLA visual (REQ-011.13) e relatório de pendências |
| Migração prematura para `execucao_normal` | Média | Alto | REQ-011.18 com indicadores e confirmação explícita |
| Mensagem enviada sem aprovação por bug | Baixa | Crítico | Camada de envio (REQ-008) deve consultar o modo antes de despachar; testes regressivos obrigatórios |
| Feedback acumulado sem revisão (vira "caixa preta") | Média | Médio | Painel deve listar feedbacks recentes; integração com workflow de reports já existente |
| Confusão sobre qual modo está ativo | Média | Médio | Indicação visual permanente (REQ-011.22) |
| Revisão de mensagens manuais (REQ-011.17A) sem suporte a perfis no POC | Alta (fora do POC) | Médio | Não bloqueia o POC; ao implementar, exige RBAC mínimo e cadastro de WhatsApp do vendedor |

---

## 12. Estimativas

| Atividade | Horas |
|-----------|-------|
| Modelagem do enum de modo + persistência + endpoint de configuração | 4h |
| Indicação visual do modo vigente no painel | 2h |
| Modo Simulação: tela de input de mensagem "do cliente" no painel | 4h |
| Workflow de aprovação/reprovação com feedback (aprimoramento do já existente) | 6h |
| Modo Conversa Controlada: gate de envio Twilio baseado no modo + decisão humana | 5h |
| Modo Execução Normal: garantir bypass correto + feedback retroativo | 3h |
| Tela de pendentes com filtros e SLA visual | 5h |
| Edição de mensagem antes de aprovar (opcional / pós-POC) | 4h |
| Testes (regressão + cobertura dos três modos) | 6h |
| **Total** | **39h** |

---

## 13. Histórico de Alterações

| Data | Versão | Alteração | Autor |
|------|--------|-----------|-------|
| 18/05/2026 | 1.0 | Criação inicial do requisito formalizando o workflow de aprovação humana de mensagens (já parcialmente implementado nos endpoints `/api/mensagens/*` e em `AcompanhamentoPage`) num modelo de três modos de execução: `simulacao`, `conversa_controlada` e `execucao_normal`. | Kika |
| 18/05/2026 | 1.1 | REQ-011.17 reescopado explicitamente para mensagens **geradas pela IA**; adicionado REQ-011.17A cobrindo **revisão de mensagens manuais por coordenador / vendedor sênior** (pós-POC), com envio de sugestão de correção para o WhatsApp do vendedor original. Atualizadas §7 (limitações) e §11 (riscos). | Kika |
| 18/05/2026 | 1.2 | Adicionada linha REQ-012 na §5 (Integração com Requisitos Existentes) tornando explícita a fronteira entre os dois requisitos. REQ-011.15 agora dispara criação automática de report (via REQ-012.2A). | Kika |

---

## 14. Aprovações

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| Analista de Requisitos | Kika | 18/05/2026 | [ ] |
| Cliente (Inforrel) | Rita | ____/____/____ | [ ] |
| Líder Técnico | Beto | ____/____/____ | [ ] |
