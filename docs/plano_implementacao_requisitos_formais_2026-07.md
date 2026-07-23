# Plano de Implementação — Requisitos Formais (ordem definida por Beto, jul/2026)

<!-- CLASSIFICACAO: ANDAMENTO -->

**Versão:** 1.2
**Data de criação:** 2026-07-16
**Última revisão:** 2026-07-22 (levantamento motivado por avaliação do RAG — ver [Histórico de Revisões](#4-histórico-de-revisões))
**Autor:** Beto + Claude
**Status:** Em execução — Fases 1 a 8 (REQ-016, REQ-011, REQ-003, REQ-010, REQ-004, REQ-005, REQ-014, REQ-012) implementadas e commitadas; Fase 9 (REQ-013) substancialmente implementada no mesmo commit das Fases 7/8. Fases 3, 7 e 9 foram reauditadas tarefa a tarefa em 2026-07-22 (ver `docs/arquitetura_avaliacao_rag_2026-07.md`); Fases 4, 5, 6 e 8 têm commit de implementação mas **não** foram reauditadas tarefa a tarefa nesta revisão. Próxima fase não iniciada: Fase 10 (REQ-008, Twilio).
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

A ordem foi definida pelo Beto e não foi alterada por este plano, exceto pela reordenação explícita registrada no [Histórico de Revisões](#4-histórico-de-revisões) (REQ-010 antecipado para Fase 4). Onde uma fase depende de trabalho de uma fase **posterior** na ordem (ex.: REQ-016 depende parcialmente de REQ-006, que só vem na fase 14), o plano sinaliza isso explicitamente e propõe uma solução de contorno temporária (mock/campo simplificado) em vez de propor reordenar.

### Visão geral

| Fase | REQ | Título | Completude atual | Depende de (fases anteriores) | Deixa pendente para |
|---|---|---|---|---|---|
| 1 | REQ-016 | Identificação/Numeração de Atendimentos | ~42% — **implementada** (commit `4c4666b`) | — | Efeito de conversão/perda de orçamento (fase 14) |
| 2 | REQ-011 | Modos de Execução/Aprovação | ~30% — **implementada** (commit `3316200`) | — | — |
| 3 | REQ-003 | Respostas Automáticas RAG | **~100% — implementada** (commit `58c2d54`; reauditada tarefa a tarefa em 2026-07-22) | — | — |
| 4 | REQ-010 | Painel Administrativo | ~37% — **implementada** (commit `998ce5b`; não reauditada tarefa a tarefa) | Fases 1-3 (parcial — ver notas da fase) | Tela de escalonamentos (fase 5), filtro de período no histórico (fase 6), badge de restrição financeira (fase 16), tela de orçamentos (fase 14) — confirmar se ainda pendentes |
| 5 | REQ-004 | Human Takeover/Escalonamento | ~25% — **implementada** (commit `38fb1ee`; bug crítico de `modo_operacao` confirmado corrigido, demais tarefas não reauditadas) | Fase 2 | Regra de prioridade sobre REQ-009 (fase 15); tela de escalonamentos da fase 4 fica pendente até aqui |
| 6 | REQ-005 | Registro de Interações/Histórico | ~35% — **implementada** (commit `eca2aca`; não reauditada tarefa a tarefa) | Fases 1, 5 | Eventos de orçamento (fase 14) |
| 7 | REQ-014 | Configuração em Runtime | **~100% — implementada** (commit `3652491`, junto com a fase 8; reauditada tarefa a tarefa em 2026-07-22) | Fase 1 | — |
| 8 | REQ-012 | Reports de Problema | ~57% — **implementada** (commit `3652491`, junto com a fase 7; correção de severidade default confirmada, demais tarefas não reauditadas) | — | Ponte com REQ-013 (fase 9) |
| 9 | REQ-013 | Pares Q&A Curados | **~100% — implementada** (mesmo commit `3652491` das fases 7/8; reauditada tarefa a tarefa em 2026-07-22) | Fases 3, 8 | — |
| 10 | REQ-008 | Integração WhatsApp/Twilio | ~40% | Fase 2 | — |
| 11 | REQ-002 | Fluxo Conversacional Guiado | ~38% | Fases 1, 7, 10 | — |
| 12 | REQ-007 | Análise de Sentimento/Conversa Crítica | ~10% | Fase 5 | — |
| 13 | REQ-001 | Integração Receita Federal (CNPJ) | ~55% | — | — |
| 14 | REQ-006 | Rastreamento de Orçamentos/Conversão | ~10% | Fase 1, 6 | — |
| 15 | REQ-009 | Reclamações Pós-venda | ~5% | Fases 5, 14 | — |
| 16 | REQ-015 | Validação CPF/Consulta de Débitos | ~35% | Fase 5 | — |

---

## Fase 1 — REQ-016: Identificação e Numeração de Atendimentos

**Status: ✅ Implementada** (commit `4c4666b`).

**Estado atual**: ~42%. Fundação de dados sólida (modelo, numeração sequencial com lock, `ultima_mensagem_at`, exibição "Atendimento #N" no frontend). Ciclo de vida dinâmico ausente.

**Objetivo da fase**: fechar o ciclo de vida do Atendimento — transições reais, janela de continuação funcionando, perguntas de continuação/fechamento.

**Tarefas**:
1. Adicionar motivos de encerramento faltantes (`concluido_conversao`, `desistencia`) ao check constraint do banco e ao vocabulário Python (hoje só existem `concluido_pelo_cliente`, `abandono`, `manual_vendedor`).
2. Implementar a matriz REQ-016.7 em `backend/services/atendimentos.py`: ao buscar o atendimento do contato, comparar `ultima_mensagem_at` com o parâmetro `janela_continuacao_atendimento_horas` (já existe e é configurável — só falta ser lido) e decidir entre continuar automaticamente / perguntar / criar novo.
3. Implementar pergunta de continuação (REQ-016.9, templates `PERG-016-009`/`009B`) e pergunta de fechamento (REQ-016.10, `PERG-016-010`) — hoje só existem como documentação em `artefatos/`, sem template no catálogo (`services/respostas/catalogo.py`) nem regra de fase no motor de conversação.
4. Implementar transições reais `ativo → encerrado`: por resposta negativa à pergunta de fechamento, por abandono (a lógica de abandono em si é da fase 11 / REQ-002.22 — aqui só a transição de status precisa existir e ficar pronta para ser acionada), e por encerramento manual.
5. Endpoint de reabertura/encerramento manual pelo vendedor, com bloqueio explícito quando `motivo_encerramento = concluido_conversao` (não pode reabrir).
6. Auditoria mínima das transições (mesmo que simplificada agora — pode ser enriquecida na Fase 6/REQ-005): pelo menos autor, timestamp, motivo.

**Arquivos-chave**: `backend/services/atendimentos.py`, `backend/models.py` (`Atendimento`, check constraint de `motivo_encerramento`), `backend/services/conversacao/regras_finalizando.py` (padrão de referência para novas regras de fase), `backend/services/respostas/catalogo.py`, `backend/main.py` (novo endpoint de reabertura/encerramento manual).

**Dependências/riscos**: REQ-016.12 (efeito de orçamento `convertido`/`perdido` no atendimento) depende de `StatusOrcamento` ganhar esses valores — isso só acontece na Fase 14 (REQ-006). **Solução de contorno**: implementar a transição do atendimento de forma que possa ser chamada por qualquer código futuro (uma função `encerrar_por_conversao(atendimento_id)`), mas não conectá-la a `Orcamento` ainda — deixar essa conexão como tarefa explícita da Fase 14.

**Critério de pronto**: cliente com atendimento `encerrado` recebe pergunta de continuação dentro/fora da janela conforme a matriz; responder "continuar" reabre e confirma interesses anteriores; pergunta de fechamento encerra corretamente; vendedor consegue encerrar/reabrir manualmente pelo painel (endpoint, mesmo que sem UI dedicada ainda — UI vem na Fase 4).

---

## Fase 2 — REQ-011: Modos de Execução e Aprovação de Mensagens

**Status: ✅ Implementada** (commit `3316200`).

**Estado atual**: ~30%. **Bug crítico**: aprovação é só pós-fato — o webhook Twilio já envia a resposta da IA ao cliente via TwiML antes de qualquer aprovação humana.

**Objetivo da fase**: implementar o gate real de envio e o modo de execução configurável.

**Tarefas**:
1. **Prioridade máxima**: alterar o webhook (`backend/main.py`) para que, quando o modo de execução exigir aprovação, a resposta gerada pela IA seja persistida como `Mensagem` **pendente** (sem enviar no TwiML) em vez de devolvida diretamente ao cliente.
2. Modelar o enum de modo de execução (`simulacao` / `conversa_controlada` / `execucao_normal`) — reaproveitar a infraestrutura de `Parametro` já existente (`services/parametro_service.py`) em vez de criar tabela nova.
3. Implementar envio efetivo apenas quando a mensagem for aprovada — depende do cliente Twilio REST real, que será construído na Fase 10 (REQ-008); até lá, usar o mecanismo síncrono existente apenas no modo `execucao_normal` como comportamento transitório, e documentar a limitação.
4. Endpoint de leitura/troca do modo de execução, com registro de auditoria (modo anterior, novo, usuário, timestamp).
5. Indicador visual do modo vigente no painel (mesmo que básico — a tela completa vem na Fase 4).
6. SLA visual de pendências (tempo desde que a mensagem ficou pendente).
7. Feedback textual opcional na aprovação (hoje só existe na reprovação).

**Arquivos-chave**: `backend/main.py` (webhook `/webhook`, endpoints `/api/mensagens/{id}/aprovar|reprovar`), `backend/services/parametro_service.py`, `backend/services/processador.py`.

**Dependências/riscos**: o envio real "pós-aprovação" fica **incompleto** até a Fase 10 entregar o cliente Twilio REST — nesta fase, o foco é garantir que a mensagem **não seja enviada automaticamente antes da aprovação** quando o modo exigir; o "como enviar de fato depois de aprovada" pode ficar como TODO explícito até a Fase 10. Alternativa: antecipar minimamente o cliente Twilio REST aqui, se o esforço combinado valer a pena — decisão de escopo a tomar no início da fase.

**Critério de pronto**: em `conversa_controlada`/`simulacao`, nenhuma resposta automática chega ao cliente sem passar por `/aprovar`; troca de modo é auditável; painel mostra o modo vigente.

---

## Fase 3 — REQ-003: Respostas Automáticas RAG

**Status: ✅ Implementada** (commit `58c2d54`).

**Nota de verificação (2026-07-22)**, feita durante o levantamento para `docs/arquitetura_avaliacao_rag_2026-07.md`: as 5 tarefas abaixo foram confirmadas concluídas no código atual — (1) índice HNSW recriado em `documentos_conhecimento.embedding` (migração `2026071605_recria_indice_vetorial_documentos_conhecimento.py`); (2) catálogo de produto (REQ-003.11) implementado e testado (`test_processador_responder_com_rag.py::test_pedir_catalogo_*`); (3) pergunta de clarificação antes do fallback implementada (parâmetros `RAG_PEDIR_CLARIFICACAO`/`RAG_ESCALADO_SEM_BASE`); (4) `rag_trechos`/`rag_score_maximo`/`rag_utilizada` expostos em `ProcessamentoDetalhes.jsx`; (5) testes automatizados existem para `RetrievalService` (`test_retrieval_service.py`) e para `_responder_com_rag`/`_decidir_resposta` (`test_processador_responder_com_rag.py`). Sem gaps residuais conhecidos nesta camada — ver avaliação completa e recomendações de evolução (reranking, filtro por produto, ingestão incremental) no documento de arquitetura citado acima.

**Estado atual (na criação deste plano, 2026-07-16)**: ~79%. Requisito mais maduro do sistema.

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

## Fase 4 — REQ-010: Painel Administrativo

> **Nota de reordenação (2026-07-16)**: esta fase estava originalmente na posição 11 ("depende de todas as anteriores"). Foi antecipada para a posição 4 por prioridade de negócio definida em reunião — ver [Histórico de Revisões](#4-histórico-de-revisões). Como consequência, ela roda logo depois de REQ-016/REQ-011/REQ-003 (fases 1-3) e **antes** de REQ-004/escalonamento (fase 5) e REQ-005/eventos (fase 6). Isso muda o perfil de dependências desta fase: em vez de "todas as anteriores" prontas, várias tarefas ficam com pendência explícita até essas fases futuras rodarem — marcado tarefa a tarefa abaixo.

**Status: ✅ Implementada** (commit `998ce5b`) — inclui autenticação real (`backend/services/auth.py`, `frontend/src/components/LoginPage.jsx`, gate global `gate_autenticacao` em `backend/main.py` protegendo todas as rotas exceto `/health`, `/webhook`, `/api/auth/login`). **Não foi reauditada tarefa a tarefa nesta revisão** (focada em RAG, ver `docs/arquitetura_avaliacao_rag_2026-07.md`) — antes de assumir 100%, confirmar as demais tarefas (telas de histórico/escalonamento/orçamento, badge de restrição, paginação).

**Estado atual (na criação deste plano, 2026-07-16)**: ~37%. Sem autenticação; faltam telas inteiras.

**Objetivo da fase**: autenticação mínima + telas que já têm dados disponíveis nas Fases 1-3, deixando pendência explícita (não meia-implementação silenciosa) onde depender de fases futuras.

**Tarefas**:
1. **Prioridade**: autenticação mínima (login + sessão + expiração) — hoje qualquer ação é auto-declarada (`aprovador_id` vem do corpo da requisição). *Sem dependências — pode ser feita integralmente agora.*
2. Identidade real do usuário em toda ação administrativa (aprovar/reprovar, mudar modo, resolver report) — substituir campos auto-declarados por dados da sessão. *Depende só da tarefa 1; as ações a substituir (aprovar/reprovar mensagem, trocar modo de execução) já existem desde a Fase 2.*
3. Tela de histórico de conversas com filtros reais (cliente/período/estado). **Parcial**: o endpoint de histórico já existe hoje e dá para filtrar por cliente/status simples; o filtro robusto por período só fica completo quando a Fase 6 (REQ-005, tarefa 6) rodar — registrar como pendência explícita, não tentar implementar o filtro de período aqui.
4. Cabeçalho de conversa com identificação PJ/PF, CPF mascarado, badge de restrição financeira. Fazer o cabeçalho PJ/PF/CPF mascarado agora; o badge de restrição financeira depende de dado que só existirá de fato após a Fase 16 (REQ-015) — deixar escondido/pendente até lá.
5. Conectar `campos_pendentes()`/`campos_do_produto()` (já existem no backend) a um endpoint exposto no topo da conversa, em vez de só dentro de modal. *Sem dependências — pode ser feita agora.*
6. Tela de escalonamentos (lista filtrada pelos eventos de escalonamento). **Bloqueada**: hoje o escalonamento (`ESCALAR_HUMANO`/`RECLAMAR`) nem seta `modo_operacao=HUMANO` de verdade — sem efeito real no sistema, não há o que listar de forma confiável. Depende da Fase 5 (REQ-004) corrigir esse bug crítico e, idealmente, da Fase 6 (REQ-005) fornecer os eventos formais para alimentar a lista. Registrar como pendência explícita.
7. Tela de orçamentos (lista + filtro + atualizar status) — **esta tarefa fica bloqueada até a Fase 14** entregar o CRUD de orçamento (já era pendência na posição original desta fase; continua igual).
8. Paginação nas listagens de maior volume. *Sem dependências — pode ser feita agora.*

**Arquivos-chave**: novo módulo de autenticação no backend, `frontend/src/App.jsx` (rotas protegidas), `frontend/src/components/AcompanhamentoPage.jsx`, `frontend/src/components/ChatArea.jsx`, `frontend/src/components/ConversaInfo.jsx`.

**Dependências/riscos**: em vez de "todas as anteriores" (posição original), esta fase agora depende só das Fases 1-3. Ficam pendências explícitas para: tela de escalonamentos (aguarda Fase 5 e, idealmente, Fase 6), filtro de período no histórico (aguarda Fase 6), badge de restrição financeira (aguarda Fase 16) e tela de orçamentos (aguarda Fase 14, como já era). Ao concluir cada uma dessas fases futuras, **revisar esta fase explicitamente** e fechar a pendência correspondente — mesmo padrão de "fechar pendência retroativa" já usado em outras fases deste plano (ex.: Fase 14 → Fase 1).

**Critério de pronto**: painel exige login; ações administrativas têm autoria real de sessão; histórico filtrável pelo que já existe hoje (cliente/status); cabeçalho PJ/PF com CPF mascarado; paginação nas listagens grandes. Tela de escalonamentos, filtro de período e badge de restrição ficam fora do critério de pronto desta fase (pendências explícitas, ver acima).

---

## Fase 5 — REQ-004: Human Takeover / Escalonamento

**Status: ✅ Implementada** (commit `38fb1ee`). **Verificado nesta revisão (2026-07-22)**: o bug crítico abaixo foi corrigido — `backend/services/processador.py` hoje seta `atendimento.modo_operacao = ModoOperacao.HUMANO` nos fluxos de escalonamento/reclamação (linhas ~1092, ~1170, ~1318) e persiste. Demais tarefas da fase (resumo de contexto, notificação, gatilhos implícitos) **não foram reauditadas tarefa a tarefa** nesta revisão.

**Estado atual (na criação deste plano, 2026-07-16)**: ~25%. **Bug crítico**: gatilhos de escalonamento (`ESCALAR_HUMANO`/`RECLAMAR`) respondem um template mas nunca setam `modo_operacao = HUMANO` — o bot continua respondendo normalmente depois.

**Objetivo da fase**: fazer o escalonamento ter efeito real, com resumo de contexto e notificação.

**Tarefas**:
1. **Prioridade máxima**: corrigir `_executar_escalar_humano`/`_executar_reclamar` (`services/conversacao/regras_globais.py`) para de fato setar `atendimento.modo_operacao = ModoOperacao.HUMANO` e persistir.
2. Implementar geração de resumo de contexto para o vendedor (dados coletados, pendências, motivo) — reaproveitar o padrão de `_gerar_resumo_finalizando`.
3. Persistir motivo/timestamp do escalonamento (aproveitar a estrutura de auditoria criada na Fase 1 para atendimento; se a Fase 6 ainda não rodou, usar uma solução simples aqui e generalizar depois).
4. Notificação real ao vendedor — depende do cliente Twilio REST (Fase 10); até lá, pelo menos garantir que o escalonamento fique visível no painel (lista de pendências) mesmo sem notificação push/WhatsApp.
5. Gatilhos implícitos: análise técnica/projeto complexo (quantidade de equipamentos, faixa de funcionários), e escalonamento por baixa confiança (`confianca_nivel`, hoje calculado mas nunca usado como gatilho).

**Arquivos-chave**: `backend/services/conversacao/regras_globais.py`, `backend/services/processador.py`, `backend/models.py` (campos de motivo/resumo em `Atendimento`, se ainda não existirem da Fase 1).

**Dependências/riscos**: notificação com SLA de 10s (REQ-004.13) fica bloqueada até a Fase 10 (Twilio REST) — registrar como pendência explícita, não tentar resolver aqui. Regra de prioridade sobre REQ-009 só se aplica de fato na Fase 15. **A tela de escalonamentos da Fase 4 (Painel Administrativo) ficou pendente aguardando esta fase — ao concluir, revisar a Fase 4 e habilitar essa tela.**

**Critério de pronto**: pedir "falar com humano" ou reclamar de fato bloqueia respostas automáticas na mensagem seguinte; vendedor vê o motivo/resumo no painel (mesmo que a UI completa venha na Fase 4, revisada após esta fase).

---

## Fase 6 — REQ-005: Registro de Interações e Histórico

**Status: ✅ Implementada** (commit `eca2aca`) — **não foi reauditada tarefa a tarefa nesta revisão** (focada em RAG, ver `docs/arquitetura_avaliacao_rag_2026-07.md`).

**Estado atual (na criação deste plano, 2026-07-16)**: ~35%. Mensagens e `ProcessamentoMensagem` bem auditados; falta log de eventos de transição de estado.

**Objetivo da fase**: implementar a estrutura de eventos auditáveis que várias outras fases (1, 5, 7, 14) precisam, e generalizá-la retroativamente. **Inclui, por prioridade definida em reunião de 2026-07-16, a timeline de mudanças de estado do atendimento no painel — ver tarefas 1 e 7 abaixo.**

**Tarefas**:
1. Modelar tabela/entidade de eventos auditáveis (`tipo`, `atendimento_id`, `estado_anterior`, `estado_novo`, `timestamp`, `ator`, `motivo`, **`mensagem_id`/`processamento_id` de origem — qual mensagem/evento motivou a mudança, prioridade de reunião de 2026-07-16**) — desenhar de forma genérica o suficiente para cobrir `atendimento_criado/encerrado/reaberto` (Fase 1), `escalonamento` (Fase 5) e, futuramente, `orcamento_*` (Fase 14).
2. Migrar a auditoria simplificada criada nas Fases 1 e 5 para essa tabela nova (refactor, não feature nova).
3. Persistir (não apenas `logger.info`) mudanças de `modo_operacao`/`fase`/`status` do `Atendimento` com autor e motivo.
4. Completar campos de fallback em `ProcessamentoMensagem` (`fallback_req003`, `resultado_fallback`, `justificativa_curta`) e a lógica no classificador/processador que os preenche.
5. Exibir `confianca_nivel`, `rag_trechos` e indicadores de fallback no `ProcessamentoDetalhes.jsx` (a exibição de `rag_trechos` e de `confianca_nivel` já deve ter sido antecipada na Fase 4 — ver nota de reunião de 2026-07-16 — aqui é sobre completar os indicadores de fallback restantes).
6. Adicionar filtro por período/status aos endpoints de histórico (`GET /api/historico/{telefone}`) — **destrava o filtro de período pendente na Fase 4 (Painel Administrativo)**.
7. **Timeline de atendimento no painel**: expor a tabela de eventos da tarefa 1 numa tela/seção de `AtendimentoDetalhes.jsx`, mostrando cada mudança de estado (fase/modo_operacao/status), o autor/motivo e a mensagem que a provocou (quando houver) — prioridade de reunião de 2026-07-16 (item 2).

**Arquivos-chave**: `backend/models.py` (nova entidade de evento), `backend/services/processador.py`, `backend/main.py` (endpoints de histórico), `frontend/src/components/ProcessamentoDetalhes.jsx`, `frontend/src/components/AtendimentoDetalhes.jsx` (timeline).

**Dependências/riscos**: eventos de orçamento (`orcamento_criado/enviado/convertido/perdido`) só existirão de fato na Fase 14 — a tabela deve ser desenhada agora de forma genérica para não precisar de migração de schema depois, só de novos `tipo`s de evento. **Ao concluir esta fase, revisar a Fase 4 (Painel) para habilitar o filtro de período no histórico.**

**Critério de pronto**: toda transição de estado relevante (atendimento, escalonamento) gera um evento consultável, com a mensagem/processamento que a provocou quando aplicável; UI de processamento mostra confiança e fallback; histórico filtrável por período; painel mostra a timeline do atendimento.

---

## Fase 7 — REQ-014: Configuração em Runtime

**Status: ✅ Implementada** (commit `3652491`, junto com a Fase 8).

**Nota de verificação (2026-07-22)**, feita durante o levantamento para `docs/arquitetura_avaliacao_rag_2026-07.md`: as 8 tarefas foram confirmadas concluídas — (1) bug de atomicidade corrigido, `PATCH /api/config/rag` valida todos os campos antes de aplicar qualquer um; (2) `ParametroService` conectado ao classificador (`_calcular_nivel_confianca`/`classificar()` aceitam `limiares_confianca` opcional, comentário no código referencia explicitamente "REQ-014, Fase 7") e à zona cinza do `QAService` (limiares carregados via `ParametroService.limiares_zona_cinza()`, embora a lógica de "pergunta de desambiguação" em si ainda não use os limiares "desambigua" — ver observação equivalente na avaliação de RAG); (3) `janela_continuacao_atendimento_horas` já lida do parâmetro desde a Fase 1; (4) `rag_score_minimo`/`rag_top_k` persistidos em `parametros`, não mais voláteis no singleton; (5) `GET`/`PATCH /api/config/rag` unificado, incluindo `rag_enabled`/`qa_enabled`/`qa_score_minimo`; (6) tabela `historico_configuracao` criada (migração `2026072002_cria_historico_configuracao.py`) com endpoint `GET /api/config/historico`; (7) `POST /api/config/rag/reset` implementado; (8) endpoints de configuração já protegidos pelo gate de autenticação global (`gate_autenticacao`, entregue na Fase 4). Completude reestimada: **~100%**.

**Estado atual (na criação deste plano, 2026-07-16)**: ~39%. Parâmetros existem no banco mas boa parte é ignorada pela lógica real.

**Objetivo da fase**: fazer os parâmetros já persistidos terem efeito real, e corrigir o bug de atomicidade.

**Tarefas**:
1. Corrigir o bug de atomicidade no `PATCH /api/config/rag` (`rag_score_minimo` é aplicado antes de validar `rag_top_k`) — validar tudo antes de aplicar qualquer campo.
2. Conectar `ParametroService` de fato ao `classificador.py` (hoje os limiares 0.70/0.40 são hardcoded) e ao `QAService` (zona cinza não usada no fluxo real).
3. Confirmar que `janela_continuacao_atendimento_horas` (usado desde a Fase 1) está sendo lido do parâmetro, não hardcoded — se a Fase 1 já implementou isso corretamente, só validar aqui.
4. Persistir `rag_score_minimo`/`rag_top_k` em banco em vez de manter voláteis no singleton `RetrievalService` (hoje se perdem a cada restart).
5. Unificar/expandir `GET/PATCH /api/config/rag` para incluir toggles `rag_enabled`/`qa_enabled` e os demais parâmetros numa única superfície.
6. Criar tabela `historico_configuracao` (autor, diff, timestamp) — pode reaproveitar a tabela de eventos da Fase 6.
7. Endpoint de reset a defaults.
8. Autenticação mínima nos endpoints de configuração (a Fase 4/REQ-010 já entrega autenticação básica do painel — só confirmar que estes endpoints também passam a exigi-la).

**Arquivos-chave**: `backend/main.py` (`/api/config/rag`, `/api/config/atendimento`), `backend/services/parametro_service.py`, `backend/services/classificador.py`, `backend/services/rag/qa_service.py`.

**Dependências/riscos**: item 6 (histórico) depende da tabela de eventos da Fase 6 já existir.

**Critério de pronto**: alterar um parâmetro pelo painel/API muda o comportamento observável do sistema (classificador, QA, RAG) sem restart; PATCH parcial nunca deixa estado inconsistente; histórico de alterações consultável.

---

## Fase 8 — REQ-012: Reports de Problema

**Status: ✅ Implementada** (commit `3652491`, junto com a Fase 7). **Verificado nesta revisão (2026-07-22)**: a tarefa 1 (severidade default da reprovação automática) está corrigida para `SeveridadeReport.MEDIA` (`backend/main.py:1088`). Demais tarefas (transições de status, filtros, estatísticas na UI, navegação report↔atendimento) **não foram reauditadas tarefa a tarefa** nesta revisão.

**Estado atual (na criação deste plano, 2026-07-16)**: ~57%. Boa cobertura de captura/triagem; faltam regras de negócio e complementos de UI.

**Objetivo da fase**: corrigir divergências de regra de negócio e completar a UI existente.

**Tarefas**:
1. Corrigir severidade default da reprovação automática (hoje grava `ALTA`, deveria ser `media`).
2. Validar transições de status no `PATCH /api/reports/{id}` (hoje aceita qualquer→qualquer) e registrar histórico de transição (reaproveitar tabela de eventos da Fase 6).
3. Tornar `autor` obrigatório também no formulário manual do frontend (hoje só o fluxo automático preenche).
4. Validar mínimo de 10 caracteres na descrição do report.
5. Adicionar filtros de período/autor/busca textual na listagem.
6. Renderizar `por_categoria`/`por_severidade` na `ReportsPage.jsx` (a API já retorna, só falta consumir).
7. Exibir `rag_trechos` no detalhe do report (dado já existe desde a Fase 3) e adicionar navegação real report→atendimento/processamento.
8. Revisar a exclusão em cascata de reports feita por `dev_limpeza_telefone.py` (garantir que só roda em ambiente de dev/teste).

**Arquivos-chave**: `backend/main.py` (`PATCH /api/reports/{id}`, `POST /api/processamentos/{id}/reports`), `frontend/src/components/ReportsPage.jsx`, `frontend/src/components/ReportDetalhe.jsx`, `frontend/src/components/ProcessamentoDetalhes.jsx`.

**Dependências/riscos**: item 2 (histórico de transição) depende da tabela de eventos da Fase 6.

**Critério de pronto**: severidade e transições de status corretas; UI mostra estatísticas completas e permite navegação report↔atendimento; autor sempre preenchido.

---

## Fase 9 — REQ-013: Pares Q&A Curados

**Status: ✅ Implementada** (mesmo commit `3652491` das Fases 7/8 — não há commit dedicado "Fase 9", mas todo o escopo foi entregue junto).

**Nota de verificação (2026-07-22)**, feita durante o levantamento para `docs/arquitetura_avaliacao_rag_2026-07.md`: as 8 tarefas foram confirmadas concluídas — (1) índice HNSW cosine criado em `pares_qa.embedding` (migração `2026072004_indice_vetorial_pares_qa.py`); (2) `qa_enabled`/`qa_score_minimo` expostos no `PATCH /api/config/rag` unificado da Fase 7; (3) `id_externo` corrigido no fluxo de criação a partir de reprovação — `frontend/src/components/AcompanhamentoPage.jsx` gera `` `reprovacao:${mensagemReprovando.id}` ``; (4) ação "criar par Q&A a partir de report" implementada em `ReportDetalhe.jsx` (`abrirCriarQA`/`criarParQADoReport`); (5) detecção de duplicatas na criação manual implementada em `QABasePage.jsx` via `GET /api/pares-qa/similares`; (6) `ingerir_pares_qa.py` já respeita lazy embedding também na ingestão em lote — só gera embedding se `--aprovar-automaticamente` for passado; (7) `QABasePage.jsx` completo: filtro por tag, contexto, aprovado/ativo, e painel de "pares mais usados" (`GET /api/pares-qa/estatisticas-uso`); (8) testes automatizados cobrindo lazy embedding, soft delete e ordenação de rotas (`test_pares_qa_router.py`) e precedência QA sobre RAG (`test_processador_responder_com_rag.py`). Completude reestimada: **~100%** — sem gaps residuais conhecidos.

**Estado atual (na criação deste plano, 2026-07-16)**: ~59%. Workflow de curadoria bem implementado; faltam integração com o resto do sistema e infraestrutura de busca em escala.

**Objetivo da fase**: fechar a ponte com Reports/Config e resolver o gap de performance.

**Tarefas**:
1. Criar índice `ivfflat`/`hnsw` em `pares_qa.embedding` (nunca existiu — mesma classe de problema já resolvida em `documentos_conhecimento` na Fase 3).
2. Expor `qa_enabled`/`qa_score_minimo` no endpoint unificado de configuração criado na Fase 7.
3. Corrigir `id_externo` no fluxo de criação a partir de reprovação (hoje cai no hash genérico em vez de `reprovacao:<mensagem_id>`, perdendo rastreabilidade).
4. Implementar ação "criar par Q&A a partir de report" (REQ-013.7) na `ReportDetalhe.jsx` — hoje só existe exportação YAML manual.
5. Implementar detecção de duplicatas (busca por similaridade) na criação manual (`QABasePage.jsx`).
6. Ajustar `ingerir_pares_qa.py` para respeitar o princípio "lazy embedding" também na ingestão em lote (hoje gera embedding para todo par novo/atualizado, independente de aprovação).
7. Completar `QABasePage.jsx`: filtro por tag, exibição de `id_externo` (origem), estatística de "pares mais usados".
8. Testes automatizados cobrindo workflow lazy embedding, precedência sobre RAG e soft delete (zero cobertura hoje).

**Arquivos-chave**: nova migração Alembic, `backend/main.py` (config unificada), `backend/routers/pares_qa.py`, `frontend/src/components/QABasePage.jsx`, `frontend/src/components/ReportDetalhe.jsx`, `frontend/src/components/AcompanhamentoPage.jsx`, `backend/scripts/base_conhecimento/ingerir_pares_qa.py`.

**Dependências/riscos**: itens 2 e 4 dependem das Fases 7 e 8, respectivamente, estarem concluídas.

**Critério de pronto**: busca por embedding em `pares_qa` usa índice; config de Q&A ajustável em runtime; report vira par Q&A com 1 ação; sem duplicatas óbvias criadas via painel.

---

## Fase 10 — REQ-008: Integração WhatsApp/Twilio
Beto: Obs: Não implementar a partir daqui antes de testar.

**Estado atual**: ~40%. Webhook de entrada funciona bem; falta segurança e envio ativo real.

**Objetivo da fase**: fechar os pilares de segurança e viabilizar o envio ativo que as Fases 2 e 5 deixaram pendente.

**Tarefas**:
1. Adicionar SDK `twilio` e um client de envio ativo (`twilio.rest.Client`) usando as credenciais já configuradas em `config.py` (hoje nunca usadas).
2. Conectar esse client ao gate de aprovação da Fase 2: mensagem aprovada dispara envio real via Twilio REST.
3. Conectar esse client à notificação de escalonamento da Fase 5.
4. Fazer `enviar_mensagem_manual` (`backend/main.py`) de fato chamar a API do Twilio (hoje só persiste no banco).
5. Implementar validação de assinatura Twilio (`X-Twilio-Signature` + `RequestValidator`) no endpoint `/webhook` — hoje qualquer POST bem formado aciona o sistema.
6. Ativar a checagem de duplicata: chamar `Database.mensagem_existe(message_sid)` antes de inserir (hoje a função existe mas está morta; reentrega do Twilio hoje gera erro de constraint em vez de ser ignorada).
7. Suporte a mídia: ler `NumMedia`/`MediaUrl0..N` no webhook e suportar envio de mídia nas respostas (necessário para REQ-003.11, catálogo, da Fase 3).
8. Registrar erros de webhook/envio como evento auditável (reaproveitar tabela da Fase 6).
9. Política de retry/fallback para falha de envio via Twilio.
10. Testes automatizados de webhook, dedup e assinatura (zero cobertura hoje).

**Arquivos-chave**: `backend/requirements.txt`, novo módulo `backend/services/twilio_client.py` (ou similar), `backend/main.py` (`/webhook`, `enviar_mensagem_manual`), `backend/database.py`.

**Dependências/riscos**: itens 2 e 3 fecham pendências deixadas explicitamente pelas Fases 2 e 5 — revisar aquelas fases ao concluir esta.

**Critério de pronto**: webhook rejeita requisições sem assinatura válida; reentrega do Twilio não gera erro; mensagens aprovadas/manuais chegam de fato ao WhatsApp do cliente; catálogo com mídia funciona.

---

## Fase 11 — REQ-002: Fluxo Conversacional Guiado

**Estado atual**: ~38%. Arquitetura central boa, mas só "encanada" para relógio de ponto.

**Objetivo da fase**: expandir a cobertura para catraca, endereço, contato, e implementar abandono/reengajamento.

**Tarefas**:
1. Catálogo de campos para **catraca** (modelo, quantidade de equipamentos) — reusa a infraestrutura de `catalogo_campos.py`/`campos_pendentes.py` já validada para relógio de ponto.
2. `CAMPO-endereco` (logradouro, número, bairro, cidade, UF, CEP, indicador entrega/instalação/retirada).
3. `CAMPO-contato` (e-mail/telefone para envio do orçamento) como campo obrigatório do catálogo, não só regex oportunista.
4. **REQ-002.22 (abandono/reengajamento)**: parâmetros `abandono_inatividade_horas`/`abandono_total_horas`/`abandono_reengajamento_max_mensagens` (expor via Fase 7), job/scheduler de verificação de inatividade, mensagem de reengajamento, transição para `encerrado` com motivo `abandono` (a transição em si já existe desde a Fase 1 — aqui só falta o gatilho). **Nota de design**: reaproveitar o mesmo mecanismo de "job/verificação por tempo" desenhado para a janela de continuação da Fase 1, se possível, em vez de criar dois schedulers distintos.
5. Confirmação/eco consolidado dos dados extraídos da mensagem inicial (REQ-002.16).
6. Pergunta explícita de ambiguidade PF/PJ (REQ-002.2A) e tratamento de troca de tipo PF↔PJ no meio da conversa.
7. Generalizar a política de retry (REQ-002.21) — hoje só existe para `modelo` — para os demais campos (endereço, contato, faixa/quantidade).
8. Uso efetivo de `confianca_nivel` para diferenciar os 3 casos do REQ-002.1A (hoje só auditado, nunca usado na decisão de rota).

**Arquivos-chave**: `backend/services/conversacao/catalogo_campos.py`, `backend/services/conversacao/campos_pendentes.py`, `backend/services/processador.py`, `backend/services/classificador.py`, novo módulo de scheduler (verificar se já existe algum mecanismo de job no repo antes de criar um novo).

**Dependências/riscos**: item 4 depende de a Fase 1 já ter as transições de estado do atendimento funcionando e de a Fase 7 já expor os parâmetros de abandono.

**Critério de pronto**: fluxo completo de qualificação funciona para catraca e relógio de ponto, incluindo endereço/contato; cliente inativo recebe reengajamento e o atendimento encerra corretamente por abandono.

---

## Fase 12 — REQ-007: Análise de Sentimento e Conversa Crítica

**Estado atual**: ~10%. Praticamente inexistente.

**Objetivo da fase**: MVP de classificação de sentimento e marcação de conversa crítica.

**Tarefas**:
1. Serviço de classificação de sentimento por heurística de palavras-chave (reaproveitar o padrão de `_REGRAS_INTENCAO` do classificador) como MVP, antes de partir para LLM.
2. Campo(s) persistente(s) de estado (`sentimento`, `critica`, `motivos`) — usar a tabela de eventos da Fase 6 em vez de criar estrutura nova.
3. Lógica de agregação por janela de últimas N mensagens.
4. Tratamento básico de negação (ex.: "não estou irritado" não deve marcar como negativo).
5. Conectar o estado "crítico" ao escalonamento real da Fase 5 (hoje o vínculo é só via intents `RECLAMAR`/`ESCALAR_HUMANO`, não via sentimento acumulado).
6. Testes de classificação de sentimento (zero cobertura hoje).

**Arquivos-chave**: novo `backend/services/sentimento.py` (ou dentro de `classificador.py`), `backend/services/conversacao/regras_globais.py` (conectar com escalonamento).

**Dependências/riscos**: depende da Fase 5 (escalonamento) e da Fase 6 (tabela de eventos) já estarem prontas.

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
4. Auditoria de quem alterou e quando — usar a tabela de eventos da Fase 6.
5. Conectar a mudança de status a efeitos no Atendimento (Fase 1, REQ-016.12): `convertido` → encerra o atendimento automaticamente com `motivo_encerramento=concluido_conversao` (a função de encerramento já deve existir desde a Fase 1 — aqui só falta chamá-la); `perdido` → não altera o atendimento.
6. Tela dedicada no frontend (lista + filtros + ação de atualizar status com confirmação) — completa a pendência deixada pela Fase 4.

**Arquivos-chave**: `backend/models.py` (`StatusOrcamento`, `Orcamento`), `backend/main.py` (novos endpoints `/api/orcamentos*`), `frontend/src/components/` (nova tela de orçamentos), `frontend/src/components/AtendimentoDetalhes.jsx`.

**Dependências/riscos**: item 5 é a peça que faltava para REQ-016.12 ficar 100% completo — ao concluir esta fase, revisar e fechar essa pendência da Fase 1. Item 6 fecha a pendência da Fase 4.

**Critério de pronto**: vendedor cria e atualiza status de orçamento pelo painel; orçamento convertido encerra o atendimento automaticamente; orçamento perdido exige motivo e não fecha o atendimento.

---

## Fase 15 — REQ-009: Reclamações Pós-venda

**Estado atual**: ~5%. Praticamente inexistente.

**Objetivo da fase**: implementar o fluxo completo, agora que escalonamento (Fase 5) e orçamento (Fase 14) estão prontos.

**Tarefas**:
1. Ampliar keywords/classificação para cobrir "atraso", "prazo de entrega", "suporte", "instalação" como pós-venda.
2. Flag de "conversa crítica" específica para pós-venda (reaproveitar a estrutura da Fase 12, priorizando sobre REQ-004.7 conforme o requisito exige).
3. Service de busca de orçamentos por telefone/CNPJ, usando o CRUD da Fase 14.
4. Seleção do orçamento mais provável por recência + resumo de confirmação ao cliente (empresa/produto/data), usando `StatusOrcamento.convertido` já existente desde a Fase 14.
5. Tratamento de orçamento incorreto: até 2 propostas alternativas, depois solicitar CNPJ/e-mail, depois escalar com flag `orcamento_nao_identificado`.
6. Escalonamento com contexto completo (`orcamento_id`, dados, categoria) — usar o escalonamento real da Fase 5.
7. Registro auditável de cada etapa (detecção, sugestão, confirmação, escalonamento) via tabela de eventos da Fase 6.

**Arquivos-chave**: `backend/services/classificador.py`, novo `backend/services/pos_venda.py` (ou dentro de `conversacao/`), `backend/services/conversacao/regras_globais.py`.

**Dependências/riscos**: esta fase só faz sentido completa após as Fases 5 e 14 — se por algum motivo precisar adiantar, o mínimo viável é a detecção de intenção (item 1), sem o restante.

**Critério de pronto**: cliente reclamando de pedido antigo tem o orçamento certo identificado (ou escalado corretamente se não encontrado) e a conversa é escalada com contexto completo.

---

## Fase 16 — REQ-015: Validação de CPF e Consulta de Débitos

**Estado atual**: ~35%. Validação local ótima; consulta de débito é um stub.

**Objetivo da fase**: fechar o valor de negócio central do requisito (saber se a pessoa tem dívida).

**Tarefas**:
1. Integrar um provedor real de consulta de débito (Serasa/SPC/Boa Vista/Quod) — hoje `consultar_credito` é 100% stub.
2. Eco/confirmação do CPF capturado ao cliente ("Anotei o CPF X. Está correto?").
3. Escalonamento automático para humano quando há restrição financeira — conectar ao escalonamento real da Fase 5 (hoje só registra o dado, sem acionar handoff).
4. Badge de restrição financeira no painel (zero referência hoje — depende da Fase 4 já ter cabeçalho de conversa pronto para receber esse badge; **destrava o badge deixado pendente na Fase 4**).
5. Contador de tentativas de CPF inválido (máx. 3) + tratamento de recusa do cliente em informar CPF (não insistir mais de 2x, escalar antes do orçamento).
6. Reuso de CPF entre atendimentos diferentes do mesmo telefone — estender `identificador.py` para considerar `Pessoa`, análogo ao que já existe para `Empresa`.
7. Aviso LGPD na primeira solicitação de CPF.

**Arquivos-chave**: `backend/services/cpf/consulta_credito.py`, `backend/services/cpf/persistencia.py`, `backend/services/identificador.py`, `backend/services/processador.py`, `frontend/src/components/ConversaInfo.jsx` (badge).

**Dependências/riscos**: item 3 depende da Fase 5; item 4 depende da Fase 4 (revisar essa fase ao concluir, para habilitar o badge).

**Critério de pronto**: consulta de débito retorna dado real; restrição financeira escala para humano e aparece como badge no painel; cliente que recusa CPF não trava o fluxo.

---

## 2. Melhorias imediatas — janela "Raciocínio do Cérebro" (prioridade de reunião, 2026-07-16)

Prioridades definidas em reunião com o Beto, transversais a REQ-003/REQ-005/REQ-011 — sem dependência de nenhuma fase futura, podem ser feitas a qualquer momento (inclusive antes da Fase 4). Não alteram a numeração das 16 fases de REQ acima.

O componente é `frontend/src/components/ProcessamentoDetalhes.jsx` (a mesma tela abre tanto pelo ícone de cérebro no chat quanto no painel de acompanhamento — não são janelas diferentes).

**Tarefas**:
1. Mostrar explicitamente "RAG utilizada: sim/não" mesmo quando `rag_utilizada=false` (hoje a seção inteira some nesse caso, dando a impressão de que a informação simplesmente não existe).
2. Renomear os dois badges de score existentes, hoje visualmente idênticos e fáceis de confundir: **"Confiança da classificação"** (`proc.confianca` — confiança do classificador de intenção) vs. **"Confiabilidade da resposta (RAG)"** (`proc.rag_score_maximo` — similaridade do melhor trecho/par Q&A recuperado). Expor também `confianca_nivel` (Alta/Média/Baixa) como badge textual complementar — hoje persistido em `ProcessamentoMensagem` mas ausente do `to_dict()`/API e da tela (antecipa parte da tarefa 5 da Fase 6).
3. Adicionar um controle (radio/checkbox) para alternar a ordem de exibição das seções entre **"cronológica"** (ordem atual: Classificação → Entidades → Identificação → Decisão de resposta → RAG/Q&A → LLM → Controle) e **"por importância"** (Decisão de resposta + RAG/Q&A primeiro, por ser o que mais interessa: "por que o bot respondeu isso"). Implementar via um array de configuração de seções (não ordem fixa inline no JSX), para ficar fácil reconfigurar a ordem no futuro.
4. Rotular explicitamente a pergunta curada que deu "match" no Q&A (`t.pergunta`, quando `t.tipo === 'qa_pair'`) como "Pergunta da base que casou" em vez de texto genérico — a informação já existe em `rag_trechos`, só falta o rótulo.
5. Mostrar o modo de execução (`simulacao`/`conversa_controlada`/`execucao_normal`) vigente no momento em que aquela mensagem específica foi processada — reconstruído por consulta cruzada entre `ProcessamentoMensagem.created_at` e o histórico de trocas já existente (`historico_modo_execucao`, desde a Fase 2), em vez de adicionar coluna nova.
6. Nenhuma outra informação útil adicional foi identificada nesta revisão — reavaliar se surgir necessidade concreta.

A timeline de mudanças de estado do atendimento (segundo item priorizado na reunião) **não foi antecipada** — continua fazendo parte da Fase 6 (REQ-005), cujo desenho foi atualizado para incluir a referência à mensagem/evento causador de cada mudança (ver tarefas 1 e 7 da Fase 6).

**Arquivos-chave**: `frontend/src/components/ProcessamentoDetalhes.jsx`, `backend/models.py` (expor `confianca_nivel` em `ProcessamentoMensagem.to_dict()`), `backend/main.py` (`GET /api/processamentos/{id}`), `backend/services/parametro_service.py`/`historico_modo_execucao` (consulta retroativa de modo de execução).

**Critério de pronto**: janela sempre indica se a RAG foi usada (sim/não); os dois scores aparecem rotulados sem ambiguidade, com `confianca_nivel` visível; toggle de ordenação cronológica/importância funcional; pergunta Q&A rotulada; modo de execução vigente no momento do processamento exibido.

---

## 3. Notas gerais de execução

- **Sequência sugerida, não estritamente bloqueante**: dentro de cada fase, tarefas de correção de bug (ex.: Fases 2 e 5) devem ser priorizadas sobre as de feature nova — são risco de confiabilidade em produção, não apenas gaps de escopo.
- **Tabela de eventos (Fase 6) é infraestrutura compartilhada**: várias fases posteriores (7, 8, 12, 14, 15) dependem dela para auditoria — vale desenhá-la de forma genérica desde a Fase 6, mesmo sabendo que só será totalmente populada mais tarde.
- **Scheduler/job de tempo (Fases 1 e 11)**: tanto a janela de continuação de atendimento (REQ-016) quanto o abandono/reengajamento (REQ-002.22) precisam de verificação por tempo. Avaliar na Fase 1 se vale construir um mecanismo único reaproveitável na Fase 11, em vez de dois schedulers separados.
- **Twilio REST (Fase 10) desbloqueia pendências das Fases 2 e 5**: ao concluir a Fase 10, revisar explicitamente essas duas fases para fechar os itens que ficaram marcados como "depende do cliente Twilio real".
- **REQ-010 (Fase 4) foi antecipado e roda fora de ordem em relação às suas dependências originais**: ao concluir as Fases 5, 6, 14 e 16, revisar a Fase 4 explicitamente para destravar, respectivamente, a tela de escalonamentos, o filtro de período no histórico, a tela de orçamentos e o badge de restrição financeira — ver detalhamento tarefa a tarefa na própria Fase 4.
- **Reavaliar percentuais antes de cada fase**: os números de completude são de 2026-07-16; se houver mudanças no código entre o planejamento e a execução de uma fase específica, reconfirmar o estado atual antes de iniciar as tarefas.

---

## 4. Histórico de Revisões

| Data | Versão | Alteração |
|------|--------|-----------|
| 2026-07-16 | 1.0 | Criação do plano — 16 fases na ordem original de prioridade definida pelo Beto. |
| 2026-07-16 | 1.1 | Reunião de priorização: (1) REQ-010 (Painel Administrativo) antecipado da posição 11 para posição 4 — fases antigas 4-10 (REQ-004, REQ-005, REQ-014, REQ-012, REQ-013, REQ-008, REQ-002) renumeradas para 5-11, mantendo a ordem relativa entre si; fases 12-16 inalteradas. Tarefas da Fase 4 (REQ-010) que dependiam de fases hoje posteriores foram marcadas com pendência explícita (tela de escalonamentos, filtro de período, badge de restrição). (2) Adicionada nova seção "2. Melhorias imediatas — janela Raciocínio do Cérebro", com tarefas concretas de UI/backend sem dependência de fase, decididas em reunião (RAG sim/não sempre visível; badges de score renomeados + `confianca_nivel` exposto; toggle de ordenação cronológica/importância; rótulo explícito da pergunta Q&A que casou; modo de execução vigente por mensagem via consulta retroativa ao histórico). (3) Fase 6 (REQ-005) teve o desenho da tabela de eventos (tarefa 1) e um novo item de timeline (tarefa 7) atualizados para incluir qual mensagem/evento motivou cada mudança de estado do atendimento — sem antecipar a posição desta fase no cronograma. |
| 2026-07-22 | 1.2 | Atualização motivada por um levantamento de arquitetura do RAG (ver `docs/arquitetura_avaliacao_rag_2026-07.md`), que revelou o plano desatualizado em relação ao código: (1) confirmado via `git log` que as Fases 1 a 8 têm commit de implementação (`4c4666b`, `3316200`, `58c2d54`, `998ce5b`, `38fb1ee`, `eca2aca`, `3652491` — as Fases 7 e 8 foram entregues no mesmo commit) e que a Fase 9 (REQ-013) foi substancialmente entregue nesse mesmo commit `3652491`, apesar de não ter commit dedicado. (2) Fases 3 (REQ-003), 7 (REQ-014) e 9 (REQ-013) foram reauditadas tarefa a tarefa neste levantamento — todas as tarefas confirmadas concluídas, completude reestimada em ~100% para as três, sem gaps residuais conhecidos (recomendações de evolução, não gaps do escopo original, estão em `docs/arquitetura_avaliacao_rag_2026-07.md`). (3) Fases 4, 5, 6 e 8 tiveram apenas o status atualizado para "implementada" com base no commit encontrado; para 5 e 8 os respectivos bugs críticos/de prioridade máxima foram verificados e confirmados corrigidos, mas as demais tarefas dessas 4 fases **não foram reauditadas tarefa a tarefa** — recomenda-se uma revisão dedicada antes de assumir 100% de completude nelas. (4) Nenhuma alteração na ordem das fases ou nos textos de "Estado atual" originais (mantidos como registro histórico do estado em 2026-07-16, com nota indicando isso). |
