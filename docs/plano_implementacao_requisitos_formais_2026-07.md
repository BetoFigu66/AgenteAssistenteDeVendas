# Plano de Implementação — Requisitos Formais (ordem definida por Beto, jul/2026)

**Versão:** 1.0
**Data:** 2026-07-16
**Autor:** Beto + Claude
**Status:** Planejado — nenhuma fase iniciada
**Origem:** `AnotacoesPessoais/Beto/relatorio_completude_requisitos_2026-07-16.md` (análise de completude código x `artefatos/requisitos_formais/`)
**Escopo deste plano:** sequenciar a implementação dos 16 REQs formais na ordem de prioridade definida pelo Beto, com tarefas concretas por fase.

---

## 1. Como usar este plano

Cada fase corresponde a um REQ, na ordem definida pelo Beto. Para cada fase:
- **Estado atual** — completude estimada no relatório de 2026-07-16 (reconfirmar no código antes de começar; o relatório é um snapshot).
- **Objetivo da fase** — o que "pronto" significa aqui, não necessariamente 100% do REQ original (algumas partes dependem de fases futuras — ver notas de dependência).
- **Tarefas** — lista acionável, derivada do gap analysis.
- **Arquivos-chave** — onde mexer.
- **Dependências/riscos** — o que essa fase precisa de fases anteriores, e o que ela deixa pendente para fases futuras.
- **Critério de pronto** — definição de "concluído" testável.

A ordem foi definida pelo Beto e não foi alterada por este plano. Onde uma fase depende de trabalho de uma fase **posterior** na ordem (ex.: REQ-016 depende parcialmente de REQ-006, que só vem na fase 14), o plano sinaliza isso explicitamente e propõe uma solução de contorno temporária (mock/campo simplificado) em vez de propor reordenar.

### Visão geral

| Fase | REQ | Título | Completude atual | Depende de (fases anteriores) | Deixa pendente para |
|---|---|---|---|---|---|
| 1 | REQ-016 | Identificação/Numeração de Atendimentos | ~42% | — | Efeito de conversão/perda de orçamento (fase 14) |
| 2 | REQ-011 | Modos de Execução/Aprovação | ~30% | — | — |
| 3 | REQ-003 | Respostas Automáticas RAG | ~79% | — | — |
| 4 | REQ-004 | Human Takeover/Escalonamento | ~25% | Fase 2 (aprovação) | Regra de prioridade sobre REQ-009 (fase 15) |
| 5 | REQ-005 | Registro de Interações/Histórico | ~35% | Fases 1, 4 (eventos que auditar) | Eventos de orçamento (fase 14) |
| 6 | REQ-014 | Configuração em Runtime | ~39% | Fase 1 (janela de continuação já deve existir) | — |
| 7 | REQ-012 | Reports de Problema | ~57% | — | Ponte com REQ-013 (fase 8) |
| 8 | REQ-013 | Pares Q&A Curados | ~59% | Fase 3 (RAG), Fase 7 (reports) | — |
| 9 | REQ-008 | Integração WhatsApp/Twilio | ~40% | Fase 2 (gate de aprovação) | — |
| 10 | REQ-002 | Fluxo Conversacional Guiado | ~38% | Fases 1, 6, 9 | — |
| 11 | REQ-010 | Painel Administrativo | ~37% | Todas anteriores (expõe dados delas) | Tela de orçamentos completa (fase 14) |
| 12 | REQ-007 | Análise de Sentimento/Conversa Crítica | ~10% | Fase 4 (escalonamento) | — |
| 13 | REQ-001 | Integração Receita Federal (CNPJ) | ~55% | — | — |
| 14 | REQ-006 | Rastreamento de Orçamentos/Conversão | ~10% | Fase 1 (atendimento), Fase 5 (eventos) | — |
| 15 | REQ-009 | Reclamações Pós-venda | ~5% | Fases 4, 14 | — |
| 16 | REQ-015 | Validação CPF/Consulta de Débitos | ~35% | Fase 4 (escalonamento por restrição) | — |

---

## Fase 1 — REQ-016: Identificação e Numeração de Atendimentos

**Estado atual**: ~42%. Fundação de dados sólida (modelo, numeração sequencial com lock, `ultima_mensagem_at`, exibição "Atendimento #N" no frontend). Ciclo de vida dinâmico ausente.

**Objetivo da fase**: fechar o ciclo de vida do Atendimento — transições reais, janela de continuação funcionando, perguntas de continuação/fechamento.

**Tarefas**:
1. Adicionar motivos de encerramento faltantes (`concluido_conversao`, `desistencia`) ao check constraint do banco e ao vocabulário Python (hoje só existem `concluido_pelo_cliente`, `abandono`, `manual_vendedor`).
2. Implementar a matriz REQ-016.7 em `backend/services/atendimentos.py`: ao buscar o atendimento do contato, comparar `ultima_mensagem_at` com o parâmetro `janela_continuacao_atendimento_horas` (já existe e é configurável — só falta ser lido) e decidir entre continuar automaticamente / perguntar / criar novo.
3. Implementar pergunta de continuação (REQ-016.9, templates `PERG-016-009`/`009B`) e pergunta de fechamento (REQ-016.10, `PERG-016-010`) — hoje só existem como documentação em `artefatos/`, sem template no catálogo (`services/respostas/catalogo.py`) nem regra de fase no motor de conversação.
4. Implementar transições reais `ativo → encerrado`: por resposta negativa à pergunta de fechamento, por abandono (a lógica de abandono em si é da fase 10 / REQ-002.22 — aqui só a transição de status precisa existir e ficar pronta para ser acionada), e por encerramento manual.
5. Endpoint de reabertura/encerramento manual pelo vendedor, com bloqueio explícito quando `motivo_encerramento = concluido_conversao` (não pode reabrir).
6. Auditoria mínima das transições (mesmo que simplificada agora — pode ser enriquecida na Fase 5/REQ-005): pelo menos autor, timestamp, motivo.

**Arquivos-chave**: `backend/services/atendimentos.py`, `backend/models.py` (`Atendimento`, check constraint de `motivo_encerramento`), `backend/services/conversacao/regras_finalizando.py` (padrão de referência para novas regras de fase), `backend/services/respostas/catalogo.py`, `backend/main.py` (novo endpoint de reabertura/encerramento manual).

**Dependências/riscos**: REQ-016.12 (efeito de orçamento `convertido`/`perdido` no atendimento) depende de `StatusOrcamento` ganhar esses valores — isso só acontece na Fase 14 (REQ-006). **Solução de contorno**: implementar a transição do atendimento de forma que possa ser chamada por qualquer código futuro (uma função `encerrar_por_conversao(atendimento_id)`), mas não conectá-la a `Orcamento` ainda — deixar essa conexão como tarefa explícita da Fase 14.

**Critério de pronto**: cliente com atendimento `encerrado` recebe pergunta de continuação dentro/fora da janela conforme a matriz; responder "continuar" reabre e confirma interesses anteriores; pergunta de fechamento encerra corretamente; vendedor consegue encerrar/reabrir manualmente pelo painel (endpoint, mesmo que sem UI dedicada ainda — UI vem na Fase 11).

---

## Fase 2 — REQ-011: Modos de Execução e Aprovação de Mensagens

**Estado atual**: ~30%. **Bug crítico**: aprovação é só pós-fato — o webhook Twilio já envia a resposta da IA ao cliente via TwiML antes de qualquer aprovação humana.

**Objetivo da fase**: implementar o gate real de envio e o modo de execução configurável.

**Tarefas**:
1. **Prioridade máxima**: alterar o webhook (`backend/main.py`) para que, quando o modo de execução exigir aprovação, a resposta gerada pela IA seja persistida como `Mensagem` **pendente** (sem enviar no TwiML) em vez de devolvida diretamente ao cliente.
2. Modelar o enum de modo de execução (`simulacao` / `conversa_controlada` / `execucao_normal`) — reaproveitar a infraestrutura de `Parametro` já existente (`services/parametro_service.py`) em vez de criar tabela nova.
3. Implementar envio efetivo apenas quando a mensagem for aprovada — depende do cliente Twilio REST real, que será construído na Fase 9 (REQ-008); até lá, usar o mecanismo síncrono existente apenas no modo `execucao_normal` como comportamento transitório, e documentar a limitação.
4. Endpoint de leitura/troca do modo de execução, com registro de auditoria (modo anterior, novo, usuário, timestamp).
5. Indicador visual do modo vigente no painel (mesmo que básico — a tela completa vem na Fase 11).
6. SLA visual de pendências (tempo desde que a mensagem ficou pendente).
7. Feedback textual opcional na aprovação (hoje só existe na reprovação).

**Arquivos-chave**: `backend/main.py` (webhook `/webhook`, endpoints `/api/mensagens/{id}/aprovar|reprovar`), `backend/services/parametro_service.py`, `backend/services/processador.py`.

**Dependências/riscos**: o envio real "pós-aprovação" fica **incompleto** até a Fase 9 entregar o cliente Twilio REST — nesta fase, o foco é garantir que a mensagem **não seja enviada automaticamente antes da aprovação** quando o modo exigir; o "como enviar de fato depois de aprovada" pode ficar como TODO explícito até a Fase 9. Alternativa: antecipar minimamente o cliente Twilio REST aqui, se o esforço combinado valer a pena — decisão de escopo a tomar no início da fase.

**Critério de pronto**: em `conversa_controlada`/`simulacao`, nenhuma resposta automática chega ao cliente sem passar por `/aprovar`; troca de modo é auditável; painel mostra o modo vigente.

---

## Fase 3 — REQ-003: Respostas Automáticas RAG

**Estado atual**: ~79%. Requisito mais maduro do sistema.

**Objetivo da fase**: fechar os gaps restantes e eliminar o risco de performance já identificado.

**Tarefas**:
1. Recriar o índice `ivfflat`/`hnsw` em `documentos_conhecimento.embedding`, removido pela migração `3699280dbfe7_adiciona_pares_qa.py` e nunca recriado no `upgrade()` — nova migração Alembic.
2. Implementar REQ-003.11 (envio de catálogo): novo intent, templates, configuração de link por tipo de produto.
3. Adicionar uma etapa real de 1 pergunta de clarificação antes do fallback genérico (REQ-003.7), com escalonamento para humano se a base realmente não tiver conteúdo.
4. Expor `rag_trechos`/`rag_score_maximo`/`rag_utilizada` na UI (`ProcessamentoDetalhes.jsx`) — hoje só consultável direto no banco.
5. Testes automatizados para `RetrievalService` e para `_responder_com_rag` (zero cobertura hoje).

**Arquivos-chave**: nova migração Alembic, `backend/services/rag/retrieval.py`, `backend/services/classificador.py` (novo intent de catálogo), `frontend/src/components/ProcessamentoDetalhes.jsx`.

**Dependências/riscos**: nenhuma dependência de fases anteriores. Baixo risco.

**Critério de pronto**: consulta RAG usa índice vetorial (plano de execução confirma via `EXPLAIN`); pedido de catálogo responde com link/anexo; UI mostra os trechos usados; testes cobrindo os cenários principais passam.

---

## Fase 4 — REQ-004: Human Takeover / Escalonamento

**Estado atual**: ~25%. **Bug crítico**: gatilhos de escalonamento (`ESCALAR_HUMANO`/`RECLAMAR`) respondem um template mas nunca setam `modo_operacao = HUMANO` — o bot continua respondendo normalmente depois.

**Objetivo da fase**: fazer o escalonamento ter efeito real, com resumo de contexto e notificação.

**Tarefas**:
1. **Prioridade máxima**: corrigir `_executar_escalar_humano`/`_executar_reclamar` (`services/conversacao/regras_globais.py`) para de fato setar `atendimento.modo_operacao = ModoOperacao.HUMANO` e persistir.
2. Implementar geração de resumo de contexto para o vendedor (dados coletados, pendências, motivo) — reaproveitar o padrão de `_gerar_resumo_finalizando`.
3. Persistir motivo/timestamp do escalonamento (aproveitar a estrutura de auditoria criada na Fase 1 para atendimento; se a Fase 5 ainda não rodou, usar uma solução simples aqui e generalizar depois).
4. Notificação real ao vendedor — depende do cliente Twilio REST (Fase 9); até lá, pelo menos garantir que o escalonamento fique visível no painel (lista de pendências) mesmo sem notificação push/WhatsApp.
5. Gatilhos implícitos: análise técnica/projeto complexo (quantidade de equipamentos, faixa de funcionários), e escalonamento por baixa confiança (`confianca_nivel`, hoje calculado mas nunca usado como gatilho).

**Arquivos-chave**: `backend/services/conversacao/regras_globais.py`, `backend/services/processador.py`, `backend/models.py` (campos de motivo/resumo em `Atendimento`, se ainda não existirem da Fase 1).

**Dependências/riscos**: notificação com SLA de 10s (REQ-004.13) fica bloqueada até a Fase 9 (Twilio REST) — registrar como pendência explícita, não tentar resolver aqui. Regra de prioridade sobre REQ-009 só se aplica de fato na Fase 15.

**Critério de pronto**: pedir "falar com humano" ou reclamar de fato bloqueia respostas automáticas na mensagem seguinte; vendedor vê o motivo/resumo no painel (mesmo que a UI completa venha na Fase 11).

---

## Fase 5 — REQ-005: Registro de Interações e Histórico

**Estado atual**: ~35%. Mensagens e `ProcessamentoMensagem` bem auditados; falta log de eventos de transição de estado.

**Objetivo da fase**: implementar a estrutura de eventos auditáveis que várias outras fases (1, 4, 6, 14) precisam, e generalizá-la retroativamente.

**Tarefas**:
1. Modelar tabela/entidade de eventos auditáveis (`tipo`, `atendimento_id`, `estado_anterior`, `estado_novo`, `timestamp`, `ator`, `motivo`) — desenhar de forma genérica o suficiente para cobrir `atendimento_criado/encerrado/reaberto` (Fase 1), `escalonamento` (Fase 4) e, futuramente, `orcamento_*` (Fase 14).
2. Migrar a auditoria simplificada criada nas Fases 1 e 4 para essa tabela nova (refactor, não feature nova).
3. Persistir (não apenas `logger.info`) mudanças de `modo_operacao`/`fase`/`status` do `Atendimento` com autor e motivo.
4. Completar campos de fallback em `ProcessamentoMensagem` (`fallback_req003`, `resultado_fallback`, `justificativa_curta`) e a lógica no classificador/processador que os preenche.
5. Exibir `confianca_nivel`, `rag_trechos` e indicadores de fallback no `ProcessamentoDetalhes.jsx` (a exibição de `rag_trechos` já deve ter sido feita na Fase 3 — aqui é sobre `confianca_nivel`/fallback).
6. Adicionar filtro por período/status aos endpoints de histórico (`GET /api/historico/{telefone}`).

**Arquivos-chave**: `backend/models.py` (nova entidade de evento), `backend/services/processador.py`, `backend/main.py` (endpoints de histórico), `frontend/src/components/ProcessamentoDetalhes.jsx`.

**Dependências/riscos**: eventos de orçamento (`orcamento_criado/enviado/convertido/perdido`) só existirão de fato na Fase 14 — a tabela deve ser desenhada agora de forma genérica para não precisar de migração de schema depois, só de novos `tipo`s de evento.

**Critério de pronto**: toda transição de estado relevante (atendimento, escalonamento) gera um evento consultável; UI de processamento mostra confiança e fallback; histórico filtrável por período.

---

## Fase 6 — REQ-014: Configuração em Runtime

**Estado atual**: ~39%. Parâmetros existem no banco mas boa parte é ignorada pela lógica real.

**Objetivo da fase**: fazer os parâmetros já persistidos terem efeito real, e corrigir o bug de atomicidade.

**Tarefas**:
1. Corrigir o bug de atomicidade no `PATCH /api/config/rag` (`rag_score_minimo` é aplicado antes de validar `rag_top_k`) — validar tudo antes de aplicar qualquer campo.
2. Conectar `ParametroService` de fato ao `classificador.py` (hoje os limiares 0.70/0.40 são hardcoded) e ao `QAService` (zona cinza não usada no fluxo real).
3. Confirmar que `janela_continuacao_atendimento_horas` (usado desde a Fase 1) está sendo lido do parâmetro, não hardcoded — se a Fase 1 já implementou isso corretamente, só validar aqui.
4. Persistir `rag_score_minimo`/`rag_top_k` em banco em vez de manter voláteis no singleton `RetrievalService` (hoje se perdem a cada restart).
5. Unificar/expandir `GET/PATCH /api/config/rag` para incluir toggles `rag_enabled`/`qa_enabled` e os demais parâmetros numa única superfície.
6. Criar tabela `historico_configuracao` (autor, diff, timestamp) — pode reaproveitar a tabela de eventos da Fase 5.
7. Endpoint de reset a defaults.
8. Autenticação mínima nos endpoints de configuração (depende da Fase 11 para autenticação completa do painel; aqui pelo menos não deixar o endpoint mais aberto que o resto do sistema).

**Arquivos-chave**: `backend/main.py` (`/api/config/rag`, `/api/config/atendimento`), `backend/services/parametro_service.py`, `backend/services/classificador.py`, `backend/services/rag/qa_service.py`.

**Dependências/riscos**: item 6 (histórico) depende da tabela de eventos da Fase 5 já existir.

**Critério de pronto**: alterar um parâmetro pelo painel/API muda o comportamento observável do sistema (classificador, QA, RAG) sem restart; PATCH parcial nunca deixa estado inconsistente; histórico de alterações consultável.

---

## Fase 7 — REQ-012: Reports de Problema

**Estado atual**: ~57%. Boa cobertura de captura/triagem; faltam regras de negócio e complementos de UI.

**Objetivo da fase**: corrigir divergências de regra de negócio e completar a UI existente.

**Tarefas**:
1. Corrigir severidade default da reprovação automática (hoje grava `ALTA`, deveria ser `media`).
2. Validar transições de status no `PATCH /api/reports/{id}` (hoje aceita qualquer→qualquer) e registrar histórico de transição (reaproveitar tabela de eventos da Fase 5).
3. Tornar `autor` obrigatório também no formulário manual do frontend (hoje só o fluxo automático preenche).
4. Validar mínimo de 10 caracteres na descrição do report.
5. Adicionar filtros de período/autor/busca textual na listagem.
6. Renderizar `por_categoria`/`por_severidade` na `ReportsPage.jsx` (a API já retorna, só falta consumir).
7. Exibir `rag_trechos` no detalhe do report (dado já existe desde a Fase 3) e adicionar navegação real report→atendimento/processamento.
8. Revisar a exclusão em cascata de reports feita por `dev_limpeza_telefone.py` (garantir que só roda em ambiente de dev/teste).

**Arquivos-chave**: `backend/main.py` (`PATCH /api/reports/{id}`, `POST /api/processamentos/{id}/reports`), `frontend/src/components/ReportsPage.jsx`, `frontend/src/components/ReportDetalhe.jsx`, `frontend/src/components/ProcessamentoDetalhes.jsx`.

**Dependências/riscos**: item 2 (histórico de transição) depende da tabela de eventos da Fase 5.

**Critério de pronto**: severidade e transições de status corretas; UI mostra estatísticas completas e permite navegação report↔atendimento; autor sempre preenchido.

---

## Fase 8 — REQ-013: Pares Q&A Curados

**Estado atual**: ~59%. Workflow de curadoria bem implementado; faltam integração com o resto do sistema e infraestrutura de busca em escala.

**Objetivo da fase**: fechar a ponte com Reports/Config e resolver o gap de performance.

**Tarefas**:
1. Criar índice `ivfflat`/`hnsw` em `pares_qa.embedding` (nunca existiu — mesma classe de problema já resolvida em `documentos_conhecimento` na Fase 3).
2. Expor `qa_enabled`/`qa_score_minimo` no endpoint unificado de configuração criado na Fase 6.
3. Corrigir `id_externo` no fluxo de criação a partir de reprovação (hoje cai no hash genérico em vez de `reprovacao:<mensagem_id>`, perdendo rastreabilidade).
4. Implementar ação "criar par Q&A a partir de report" (REQ-013.7) na `ReportDetalhe.jsx` — hoje só existe exportação YAML manual.
5. Implementar detecção de duplicatas (busca por similaridade) na criação manual (`QABasePage.jsx`).
6. Ajustar `ingerir_pares_qa.py` para respeitar o princípio "lazy embedding" também na ingestão em lote (hoje gera embedding para todo par novo/atualizado, independente de aprovação).
7. Completar `QABasePage.jsx`: filtro por tag, exibição de `id_externo` (origem), estatística de "pares mais usados".
8. Testes automatizados cobrindo workflow lazy embedding, precedência sobre RAG e soft delete (zero cobertura hoje).

**Arquivos-chave**: nova migração Alembic, `backend/main.py` (config unificada), `backend/routers/pares_qa.py`, `frontend/src/components/QABasePage.jsx`, `frontend/src/components/ReportDetalhe.jsx`, `frontend/src/components/AcompanhamentoPage.jsx`, `backend/scripts/base_conhecimento/ingerir_pares_qa.py`.

**Dependências/riscos**: itens 2 e 4 dependem das Fases 6 e 7, respectivamente, estarem concluídas.

**Critério de pronto**: busca por embedding em `pares_qa` usa índice; config de Q&A ajustável em runtime; report vira par Q&A com 1 ação; sem duplicatas óbvias criadas via painel.

---

## Fase 9 — REQ-008: Integração WhatsApp/Twilio

**Estado atual**: ~40%. Webhook de entrada funciona bem; falta segurança e envio ativo real.

**Objetivo da fase**: fechar os pilares de segurança e viabilizar o envio ativo que as Fases 2 e 4 deixaram pendente.

**Tarefas**:
1. Adicionar SDK `twilio` e um client de envio ativo (`twilio.rest.Client`) usando as credenciais já configuradas em `config.py` (hoje nunca usadas).
2. Conectar esse client ao gate de aprovação da Fase 2: mensagem aprovada dispara envio real via Twilio REST.
3. Conectar esse client à notificação de escalonamento da Fase 4.
4. Fazer `enviar_mensagem_manual` (`backend/main.py`) de fato chamar a API do Twilio (hoje só persiste no banco).
5. Implementar validação de assinatura Twilio (`X-Twilio-Signature` + `RequestValidator`) no endpoint `/webhook` — hoje qualquer POST bem formado aciona o sistema.
6. Ativar a checagem de duplicata: chamar `Database.mensagem_existe(message_sid)` antes de inserir (hoje a função existe mas está morta; reentrega do Twilio hoje gera erro de constraint em vez de ser ignorada).
7. Suporte a mídia: ler `NumMedia`/`MediaUrl0..N` no webhook e suportar envio de mídia nas respostas (necessário para REQ-003.11, catálogo, da Fase 3).
8. Registrar erros de webhook/envio como evento auditável (reaproveitar tabela da Fase 5).
9. Política de retry/fallback para falha de envio via Twilio.
10. Testes automatizados de webhook, dedup e assinatura (zero cobertura hoje).

**Arquivos-chave**: `backend/requirements.txt`, novo módulo `backend/services/twilio_client.py` (ou similar), `backend/main.py` (`/webhook`, `enviar_mensagem_manual`), `backend/database.py`.

**Dependências/riscos**: itens 2 e 3 fecham pendências deixadas explicitamente pelas Fases 2 e 4 — revisar aquelas fases ao concluir esta.

**Critério de pronto**: webhook rejeita requisições sem assinatura válida; reentrega do Twilio não gera erro; mensagens aprovadas/manuais chegam de fato ao WhatsApp do cliente; catálogo com mídia funciona.

---

## Fase 10 — REQ-002: Fluxo Conversacional Guiado

**Estado atual**: ~38%. Arquitetura central boa, mas só "encanada" para relógio de ponto.

**Objetivo da fase**: expandir a cobertura para catraca, endereço, contato, e implementar abandono/reengajamento.

**Tarefas**:
1. Catálogo de campos para **catraca** (modelo, quantidade de equipamentos) — reusa a infraestrutura de `catalogo_campos.py`/`campos_pendentes.py` já validada para relógio de ponto.
2. `CAMPO-endereco` (logradouro, número, bairro, cidade, UF, CEP, indicador entrega/instalação/retirada).
3. `CAMPO-contato` (e-mail/telefone para envio do orçamento) como campo obrigatório do catálogo, não só regex oportunista.
4. **REQ-002.22 (abandono/reengajamento)**: parâmetros `abandono_inatividade_horas`/`abandono_total_horas`/`abandono_reengajamento_max_mensagens` (expor via Fase 6), job/scheduler de verificação de inatividade, mensagem de reengajamento, transição para `encerrado` com motivo `abandono` (a transição em si já existe desde a Fase 1 — aqui só falta o gatilho). **Nota de design**: reaproveitar o mesmo mecanismo de "job/verificação por tempo" desenhado para a janela de continuação da Fase 1, se possível, em vez de criar dois schedulers distintos.
5. Confirmação/eco consolidado dos dados extraídos da mensagem inicial (REQ-002.16).
6. Pergunta explícita de ambiguidade PF/PJ (REQ-002.2A) e tratamento de troca de tipo PF↔PJ no meio da conversa.
7. Generalizar a política de retry (REQ-002.21) — hoje só existe para `modelo` — para os demais campos (endereço, contato, faixa/quantidade).
8. Uso efetivo de `confianca_nivel` para diferenciar os 3 casos do REQ-002.1A (hoje só auditado, nunca usado na decisão de rota).

**Arquivos-chave**: `backend/services/conversacao/catalogo_campos.py`, `backend/services/conversacao/campos_pendentes.py`, `backend/services/processador.py`, `backend/services/classificador.py`, novo módulo de scheduler (verificar se já existe algum mecanismo de job no repo antes de criar um novo).

**Dependências/riscos**: item 4 depende de a Fase 1 já ter as transições de estado do atendimento funcionando e de a Fase 6 já expor os parâmetros de abandono.

**Critério de pronto**: fluxo completo de qualificação funciona para catraca e relógio de ponto, incluindo endereço/contato; cliente inativo recebe reengajamento e o atendimento encerra corretamente por abandono.

---

## Fase 11 — REQ-010: Painel Administrativo

**Estado atual**: ~37%. Sem autenticação; faltam telas inteiras.

**Objetivo da fase**: autenticação mínima + telas que dependem de dados já produzidos pelas fases anteriores.

**Tarefas**:
1. **Prioridade**: autenticação mínima (login + sessão + expiração) — hoje qualquer ação é auto-declarada (`aprovador_id` vem do corpo da requisição).
2. Identidade real do usuário em toda ação administrativa (aprovar/reprovar, mudar modo, resolver report) — substituir campos auto-declarados por dados da sessão.
3. Tela de histórico de conversas com filtros reais (cliente/período/estado) — usa os filtros de histórico da Fase 5.
4. Cabeçalho de conversa com identificação PJ/PF, CPF mascarado, badge de restrição financeira (dado existirá completo só após a Fase 16, mas o campo/estrutura pode ser exibido desde já se já houver algo persistido).
5. Conectar `campos_pendentes()`/`campos_do_produto()` (já existem no backend) a um endpoint exposto no topo da conversa, em vez de só dentro de modal.
6. Tela de escalonamentos (lista filtrada pelos eventos de escalonamento da Fase 4/5).
7. Tela de orçamentos (lista + filtro + atualizar status) — **esta tarefa fica bloqueada até a Fase 14** entregar o CRUD de orçamento; registrar como pendência explícita e não tentar implementar aqui.
8. Paginação nas listagens de maior volume.

**Arquivos-chave**: novo módulo de autenticação no backend, `frontend/src/App.jsx` (rotas protegidas), `frontend/src/components/AcompanhamentoPage.jsx`, `frontend/src/components/ChatArea.jsx`, `frontend/src/components/ConversaInfo.jsx`.

**Dependências/riscos**: item 7 só pode ser concluído após a Fase 14 — esta fase entrega as demais telas e deixa a de orçamentos como follow-up.

**Critério de pronto**: painel exige login; ações administrativas têm autoria real de sessão; histórico filtrável; escalonamentos visíveis em tela própria.

---

## Fase 12 — REQ-007: Análise de Sentimento e Conversa Crítica

**Estado atual**: ~10%. Praticamente inexistente.

**Objetivo da fase**: MVP de classificação de sentimento e marcação de conversa crítica.

**Tarefas**:
1. Serviço de classificação de sentimento por heurística de palavras-chave (reaproveitar o padrão de `_REGRAS_INTENCAO` do classificador) como MVP, antes de partir para LLM.
2. Campo(s) persistente(s) de estado (`sentimento`, `critica`, `motivos`) — usar a tabela de eventos da Fase 5 em vez de criar estrutura nova.
3. Lógica de agregação por janela de últimas N mensagens.
4. Tratamento básico de negação (ex.: "não estou irritado" não deve marcar como negativo).
5. Conectar o estado "crítico" ao escalonamento real da Fase 4 (hoje o vínculo é só via intents `RECLAMAR`/`ESCALAR_HUMANO`, não via sentimento acumulado).
6. Testes de classificação de sentimento (zero cobertura hoje).

**Arquivos-chave**: novo `backend/services/sentimento.py` (ou dentro de `classificador.py`), `backend/services/conversacao/regras_globais.py` (conectar com escalonamento).

**Dependências/riscos**: depende da Fase 4 (escalonamento) e da Fase 5 (tabela de eventos) já estarem prontas.

**Critério de pronto**: mensagens com sinais claros de insatisfação acumulada marcam o atendimento como crítico e disparam escalonamento real.

---

## Fase 13 — REQ-001: Integração Receita Federal (CNPJ)

**Estado atual**: ~55%. Núcleo técnico sólido; faltam confirmação, retry e contador de tentativas.

**Objetivo da fase**: fechar as lacunas de regra de negócio em torno da consulta já funcional.

**Tarefas**:
1. Confirmação interativa "Está correto? (S/N)" antes de aceitar os dados da empresa — reativar o template `CONFIRMAR_EMPRESA` (hoje código morto).
2. Contador de tentativas de CNPJ (máx. 3) com escalonamento para humano ao esgotar — mesmo padrão já usado para `modelo` em REQ-002.
3. Diferenciar motivo do erro (formato inválido / não encontrado / falha de infraestrutura) e aplicar retry com backoff apenas para falha de infra (timeout/429).
4. Regex de CNPJ com espaços (`XX XXX XXX XXX XX`).

**Arquivos-chave**: `backend/services/cnpj/receitaws.py`, `backend/services/processador.py`, `backend/services/respostas/catalogo.py`.

**Dependências/riscos**: nenhuma dependência forte de fases anteriores.

**Critério de pronto**: cliente confirma os dados da empresa antes de prosseguir; 3 tentativas inválidas escalam para humano; falha de infraestrutura não conta como tentativa do cliente.

---

## Fase 14 — REQ-006: Rastreamento de Orçamentos e Conversão

**Estado atual**: ~10%. Só o esqueleto de schema existe.

**Objetivo da fase**: CRUD completo de orçamento com vocabulário de negócio correto — a fase mais estrutural pendente do sistema.

**Tarefas**:
1. Redefinir/mapear `StatusOrcamento` para `rascunho/enviado/convertido/perdido` (hoje é `em_elaboracao/pendente_aprovacao/enviado_cliente/aprovado/reprovado/expirado`, nunca usado em lógica alguma).
2. Endpoints CRUD: criar orçamento, atualizar status (com motivo obrigatório em "perdido"), listar com filtros por período/cliente/status.
3. Campo de conteúdo/referência do orçamento (texto/markdown ou referência externa) + canal de envio, com trava de imutabilidade pós-`enviado`.
4. Auditoria de quem alterou e quando — usar a tabela de eventos da Fase 5.
5. Conectar a mudança de status a efeitos no Atendimento (Fase 1, REQ-016.12): `convertido` → encerra o atendimento automaticamente com `motivo_encerramento=concluido_conversao` (a função de encerramento já deve existir desde a Fase 1 — aqui só falta chamá-la); `perdido` → não altera o atendimento.
6. Tela dedicada no frontend (lista + filtros + ação de atualizar status com confirmação) — completa a pendência deixada pela Fase 11.

**Arquivos-chave**: `backend/models.py` (`StatusOrcamento`, `Orcamento`), `backend/main.py` (novos endpoints `/api/orcamentos*`), `frontend/src/components/` (nova tela de orçamentos), `frontend/src/components/AtendimentoDetalhes.jsx`.

**Dependências/riscos**: item 5 é a peça que faltava para REQ-016.12 ficar 100% completo — ao concluir esta fase, revisar e fechar essa pendência da Fase 1. Item 6 fecha a pendência da Fase 11.

**Critério de pronto**: vendedor cria e atualiza status de orçamento pelo painel; orçamento convertido encerra o atendimento automaticamente; orçamento perdido exige motivo e não fecha o atendimento.

---

## Fase 15 — REQ-009: Reclamações Pós-venda

**Estado atual**: ~5%. Praticamente inexistente.

**Objetivo da fase**: implementar o fluxo completo, agora que escalonamento (Fase 4) e orçamento (Fase 14) estão prontos.

**Tarefas**:
1. Ampliar keywords/classificação para cobrir "atraso", "prazo de entrega", "suporte", "instalação" como pós-venda.
2. Flag de "conversa crítica" específica para pós-venda (reaproveitar a estrutura da Fase 12, priorizando sobre REQ-004.7 conforme o requisito exige).
3. Service de busca de orçamentos por telefone/CNPJ, usando o CRUD da Fase 14.
4. Seleção do orçamento mais provável por recência + resumo de confirmação ao cliente (empresa/produto/data), usando `StatusOrcamento.convertido` já existente desde a Fase 14.
5. Tratamento de orçamento incorreto: até 2 propostas alternativas, depois solicitar CNPJ/e-mail, depois escalar com flag `orcamento_nao_identificado`.
6. Escalonamento com contexto completo (`orcamento_id`, dados, categoria) — usar o escalonamento real da Fase 4.
7. Registro auditável de cada etapa (detecção, sugestão, confirmação, escalonamento) via tabela de eventos da Fase 5.

**Arquivos-chave**: `backend/services/classificador.py`, novo `backend/services/pos_venda.py` (ou dentro de `conversacao/`), `backend/services/conversacao/regras_globais.py`.

**Dependências/riscos**: esta fase só faz sentido completa após as Fases 4 e 14 — se por algum motivo precisar adiantar, o mínimo viável é a detecção de intenção (item 1), sem o restante.

**Critério de pronto**: cliente reclamando de pedido antigo tem o orçamento certo identificado (ou escalado corretamente se não encontrado) e a conversa é escalada com contexto completo.

---

## Fase 16 — REQ-015: Validação de CPF e Consulta de Débitos

**Estado atual**: ~35%. Validação local ótima; consulta de débito é um stub.

**Objetivo da fase**: fechar o valor de negócio central do requisito (saber se a pessoa tem dívida).

**Tarefas**:
1. Integrar um provedor real de consulta de débito (Serasa/SPC/Boa Vista/Quod) — hoje `consultar_credito` é 100% stub.
2. Eco/confirmação do CPF capturado ao cliente ("Anotei o CPF X. Está correto?").
3. Escalonamento automático para humano quando há restrição financeira — conectar ao escalonamento real da Fase 4 (hoje só registra o dado, sem acionar handoff).
4. Badge de restrição financeira no painel (zero referência hoje — depende da Fase 11 já ter cabeçalho de conversa pronto para receber esse badge).
5. Contador de tentativas de CPF inválido (máx. 3) + tratamento de recusa do cliente em informar CPF (não insistir mais de 2x, escalar antes do orçamento).
6. Reuso de CPF entre atendimentos diferentes do mesmo telefone — estender `identificador.py` para considerar `Pessoa`, análogo ao que já existe para `Empresa`.
7. Aviso LGPD na primeira solicitação de CPF.

**Arquivos-chave**: `backend/services/cpf/consulta_credito.py`, `backend/services/cpf/persistencia.py`, `backend/services/identificador.py`, `backend/services/processador.py`, `frontend/src/components/ConversaInfo.jsx` (badge).

**Dependências/riscos**: item 3 depende da Fase 4; item 4 depende da Fase 11.

**Critério de pronto**: consulta de débito retorna dado real; restrição financeira escala para humano e aparece como badge no painel; cliente que recusa CPF não trava o fluxo.

---

## 2. Notas gerais de execução

- **Sequência sugerida, não estritamente bloqueante**: dentro de cada fase, tarefas de correção de bug (ex.: Fases 2 e 4) devem ser priorizadas sobre as de feature nova — são risco de confiabilidade em produção, não apenas gaps de escopo.
- **Tabela de eventos (Fase 5) é infraestrutura compartilhada**: várias fases posteriores (6, 7, 12, 14, 15) dependem dela para auditoria — vale desenhá-la de forma genérica desde a Fase 5, mesmo sabendo que só será totalmente populada mais tarde.
- **Scheduler/job de tempo (Fases 1 e 10)**: tanto a janela de continuação de atendimento (REQ-016) quanto o abandono/reengajamento (REQ-002.22) precisam de verificação por tempo. Avaliar na Fase 1 se vale construir um mecanismo único reaproveitável na Fase 10, em vez de dois schedulers separados.
- **Twilio REST (Fase 9) desbloqueia pendências das Fases 2 e 4**: ao concluir a Fase 9, revisar explicitamente essas duas fases para fechar os itens que ficaram marcados como "depende do cliente Twilio real".
- **Reavaliar percentuais antes de cada fase**: os números de completude são de 2026-07-16; se houver mudanças no código entre o planejamento e a execução de uma fase específica, reconfirmar o estado atual antes de iniciar as tarefas.
