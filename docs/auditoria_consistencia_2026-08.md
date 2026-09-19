# Auditoria de consistência — agosto/2026

**Data:** 2026-08-29
**Escopo:** três eixos — (C) documentado mas falso, (B) inconsistência interna, (A) decidido mas não implementado.
**Método:** seis frentes de análise em paralelo (docs×código, convenções do backend, REQs marcados como implementados, testes, frontend×API, memórias×código), com síntese e verificação final.
**Padrão de evidência:** todo achado tem "X afirma A" (arquivo:linha) + "o código faz B" (arquivo:linha). O que não atendeu foi descartado.

> **Nota de método:** dois achados P0 abaixo são **regressões introduzidas na própria sessão de trabalho de 2026-08-28/29**, ainda não commitadas. Foram descobertos por esta auditoria e estão no topo do roadmap por serem bloqueantes.

---

## 0. Andamento

Este documento é o registro da auditoria de 2026-08-29 e **não é reescrito**: os achados
permanecem como foram redigidos. O que muda é o status, anotado abaixo e em cada achado resolvido.

| Data | Item | Commit | Situação |
|------|------|--------|----------|
| 2026-09-15 | P0-1 | `02d66ef` | Resolvido |
| 2026-09-16 | P0-2 | `6455022` | Resolvido |
| 2026-09-16 | P1 #5 (B2) | `544ac96` | Resolvido |
| 2026-09-16 | P1 #7 (A3) | `544ac96` | Resolvido |
| 2026-09-16 | P1 #4 (B1) | `544ac96` | Resolvido |
| 2026-09-16 | P1 #8 (A2) | `544ac96` | Resolvido (back-fill) |
| 2026-09-19 | P2 #9 (C1) | `90b5986` | Resolvido |
| 2026-09-19 | P2 #10 (C2) | `90b5986` | Resolvido |
| 2026-09-19 | P2 #11 (M1) | fora do repo | Resolvido (memória) |
| 2026-09-19 | P2 #12 (M2) | fora do repo | Resolvido (memória) |
| 2026-09-19 | P2 #13 (C3/C4/C5) | `90b5986` | Resolvido |
| 2026-09-19 | C6 (achado novo) | `90b5986` | Resolvido nos documentos; código não tocado |
| 2026-09-19 | C7 (achado novo) | `866be8d` | Resolvido: config de ESLint criada, `npm run lint` passa limpo |
| 2026-09-19 | P3 #15 (A4) | `6ea5d09` | Resolvido (REQ-012.8, com migração) |
| 2026-09-19 | P3 #18 (T1) | `6ea5d09` | Resolvido (8 testes do envio manual) |
| 2026-09-19 | P4 F1/F2/F3/F4 | `866be8d` | Resolvidos |
| 2026-09-19 | C8 (achado novo) | — | Aberto: `/webhook` recusa mensagem sem texto |
| 2026-09-19 | B4 (achado novo) | — | Aberto: limpeza por telefone deixa `empresas` órfã |
| 2026-09-19 | D1 (achado novo) | `175ab15` | Resolvido: "sim"/"não" descartados como resposta |
| 2026-09-19 | T3 | `55f4e4a` | **Obsoleto**: o gap que o `xfail` iria nomear foi fechado pelo canal de saída (REQ-008, Fase 10) |

**Suíte:** 329 passando em 2026-09-19 (eram 261 passando / 7 falhando quando a auditoria foi
escrita, e 282 depois do bloco P0). O crescimento veio dos testes escritos junto de cada correção:
canal de saída e reply-to, envio manual, histórico de report e a resposta "sim"/"não".

---

## 1. Sumário executivo — os 5 achados mais graves

| # | Achado | Severidade | Esforço | Situação |
|---|---|---|---|---|
| **P0-1** | **A aplicação não sobe com o `.env` atual** — `config.py` rejeita as chaves Twilio de API Key | Bloqueante | Trivial | ✅ resolvido (`02d66ef`) |
| **P0-2** | **Fluxo de qualificação quebrado** — troca `commit()`→`flush()` deixa cache do ORM obsoleto; bot repete perguntas já respondidas (7 testes falhando) | Alta | Baixo | ✅ resolvido (`6455022`) |
| **B1** | Transição de fase/modo e evento de auditoria em **dois commits separados** — atendimento pode travar em `HUMANO` sem rastro | Alta | Médio | ✅ resolvido (`544ac96`) |
| **M1** | Memória do MVP descreve um **Template Method que não existe** no código | Alta | Trivial (corrigir memória) | ✅ resolvido 2026-09-19 (memória) |
| **T2** | Regra de negócio "desviar compatibilidade para validação técnica" **sem guarda determinística** — só instrução de prompt | Média-alta | Médio | aberto (P1 #6) |

**Resultado negativo relevante (e tranquilizador):** `CLAUDE.md` e `docs/arquitetura_motor_conversacao_2026-07.md` foram verificados ponto a ponto e **estão fiéis ao código**. Zero achados nos dois. As quatro convenções centrais do backend (nada de psycopg cru, ordem de rotas, import via pacote `models`, timestamps UTC) também estão íntegras de ponta a ponta. O contrato frontend↔backend não tem nenhuma rota quebrada nem cor fora dos tokens da marca.

---

## 2. Achados por eixo

### P0 — Regressões não commitadas (introduzidas em 2026-08-28/29)

#### P0-1 · A aplicação não sobe com o `.env` atual — **BLOQUEANTE**

- **`.env` contém:** `TWILIO_API_KEY_SID` e `TWILIO_API_KEY_SECRET` (adicionadas para o spike Twilio).
- **`backend/config.py:9-70`** define `Settings` (pydantic-settings) **sem esses dois campos**, e o comportamento padrão é `extra_forbidden`.
- **Efeito:** `pydantic_core.ValidationError: Extra inputs are not permitted` na importação de `config.py`. Isso derruba **qualquer** execução local — servidor, scripts e até a coleta do pytest (`tests/conftest.py:9`).
- **Impacto:** total. Nenhum comando do projeto roda hoje sem contornar isso manualmente.
- **Correção:** declarar `TWILIO_API_KEY_SID: Optional[str] = None` e `TWILIO_API_KEY_SECRET: Optional[str] = None` em `Settings`, junto das três chaves Twilio já existentes (`config.py:12-14`).
- **Esforço:** trivial.

> **✅ Resolvido em 2026-09-15 — commit `02d66ef`.** As duas chaves declaradas em `Settings`.
> Verificação além do óbvio: comparadas **todas** as 23 chaves do `.env` com os campos de
> `Settings` — nenhuma sobra (o risco real não eram essas duas, era qualquer chave nova). Também
> documentadas em `backend/.env.example`, que não as mencionava. `import main` e
> `pytest --collect-only` (268 testes) voltaram a funcionar.

#### P0-2 · `commit()`→`flush()` deixou o cache do relationship obsoleto — **ALTA**

- **Mudança:** `backend/services/processador.py:1243-1264` — `_salvar_info_atendimento`/`_remover_info_atendimento` passaram de `db.commit()` para `db.flush()`, para remover commits parciais no meio do processamento (objetivo legítimo).
- **Consequência não prevista:** `commit()` expirava os objetos da sessão (`expire_on_commit=True`, padrão do SQLAlchemy), forçando a releitura de `Atendimento.informacoes` (relationship `lazy="select"`, `models/atendimento.py:202-204`). `flush()` grava o SQL mas **não invalida a coleção já carregada**.
- **Onde quebra:** `services/conversacao/estados/finalizando.py:203` carrega `campos_pendentes(atendimento)` (primeiro acesso à coleção); a linha 237 persiste a resposta do cliente via `_salvar_info_atendimento`; a linha 239 recalcula `campos_pendentes` **lendo a coleção obsoleta** (`models_comportamento.py:44-46`) e não enxerga o valor recém-gravado.
- **Sintoma para o cliente:** o bot **repete uma pergunta que o cliente acabou de responder** e a coleta trava. Atinge todas as respostas "soltas" (fora dos extratores por palavra-gatilho), que são justamente o caso comum.
- **Verificação:** `tests/test_processador_finalizando_coleta_ativa.py` — com a mudança: `7 failed, 5 passed`; revertendo só o `processador.py`: `12 passed`. Os testes estão corretos; o código é que regrediu.
- **Correção:** manter o `flush()` (a atomicidade é desejável) e resolver a obsolescência — expirar a coleção após gravar (`db.expire(atendimento, ["informacoes"])`), ou ler os valores por query direta em vez do relationship cacheado. **A escolha entre as duas tem implicação de design** — ver roadmap.
- **Esforço:** baixo para o fix; a decisão de qual caminho seguir é que pede cuidado.

> **✅ Resolvido em 2026-09-16 — commit `6455022`.** Escolhido o **expire seletivo no escritor**.
> O que decidiu foi o contrato no topo de `models_comportamento.py` ("só podem ler
> atributos/relationships já carregados — nada de sessão de banco"): a alternativa de ler por query
> direta passaria por `valores_capturados()`, que vive nesse mixin, e exigiria injetar sessão ali,
> contrariando decisão arquitetural documentada e quebrando os stubs por duck typing de
> `test_campos_pendentes.py`.
>
> A correção fica no escritor, não nos leitores: é o `AtendimentoInfo` novo que torna a coleção
> obsoleta. Nos leitores seria preciso lembrar dela em cada leitor futuro.
>
> **Além do escopo descrito no achado:** `_remover_info_atendimento` tem o mesmo defeito e não
> estava citado — `query.delete()` é bulk e passa por fora da sessão, então a linha apagada
> continuava aparecendo na coleção carregada. Coberto também.
>
> Novo `backend/tests/test_processador_cache_infos.py` testa a causa direta (os 7 testes de coleta
> ativa só pegavam o sintoma conversacional). Verificado que **2 dos 4 falham sem a correção**;
> os outros dois são caracterização e guarda contra reverter para `commit()`.
>
> `test_processador_finalizando_coleta_ativa`: 7 failed/5 passed → **12 passed**. Suíte: **272 passed**.

---

### Eixo C — Documentado mas falso

#### C1 · Comandos dos scripts de RAG apontam para diretório errado — **ALTA / trivial**
- **DOC:** `docs/comandos_uteis.md:481,484` (e o mesmo padrão em `:493,496`, `:508,511`, `:523,526`) — `python backend\scripts\inventariar_fontes_rag.py`.
- **CÓDIGO:** os scripts vivem em `backend/scripts/base_conhecimento/`; `backend/scripts/` contém apenas `criar_usuario_admin.py` e `importar_catalogo_csv.py`.
- **Impacto:** os quatro comandos, como documentados, **falham**. Argumentos e caminhos de saída estão corretos — falta só o segmento `base_conhecimento\`.

> **✅ Resolvido em 2026-09-19.** O segmento foi inserido nas **8** linhas de comando (as
> quatro seções têm duas cada: a forma básica e a com argumentos explícitos), hoje
> `docs/comandos_uteis.md:626,629,638,641,653,656,668,671`. Verificado que os quatro
> scripts existem em `backend/scripts/base_conhecimento/`.

#### C2 · Lista de tabelas da limpeza de telefone desatualizada — **MÉDIA / trivial**
- **DOC:** `docs/comandos_uteis.md:580` cita `itens_negociacao`.
- **CÓDIGO:** `backend/services/dev_limpeza_telefone.py:141-169` usa `itens_atendimento` (`ItemAtendimento`, `models/atendimento.py:287`). `ItemNegociacao` não existe mais — foi renomeado. O doc também omite `eventos_atendimento`, que o código remove.

> **✅ Resolvido em 2026-09-19.** A lista foi reescrita a partir do código, na ordem real de
> remoção (`reports`, `eventos_atendimento`, `mensagens`, `processamentos`,
> `itens_orcamento`, `orcamentos`, `itens_atendimento`, `atendimento_infos`,
> `atendimentos`, `contatos`), com a explicação de por que `eventos_atendimento` precisa
> vir antes de `mensagens` (achado A2-bis). A menção genérica mais abaixo no mesmo doc
> também foi corrigida: omitia eventos e itens.

#### C3 · Hook de sync atribuído ao `.py`, pulando o wrapper — **BAIXA / trivial**
- **DOC:** `docs/comandos_uteis.md:736` — "script `scripts/sync_skill_windsurf.py`".
- **CÓDIGO:** `.pre-commit-config.yaml` chama `bash scripts/sync_skill_windsurf.sh`, que invoca o `.py`.

> **✅ Resolvido em 2026-09-19.** O doc passou a descrever a cadeia inteira: o hook roda o
> `.sh`, um launcher que escolhe `python3` ou `python` e executa o `.py`.

#### C4 · `artefatos/planejador_negocios/` não existe — **BAIXA / trivial**
- **DOC:** `AGENTS.md:55` roteia o `[planejador]` para esse diretório.
- **REALIDADE:** `agentes/planejador_negocios.md` existe; o diretório de artefatos, não.

> **✅ Resolvido em 2026-09-19.** O nome do diretório foi **mantido** e marcado com nota de
> rodapé como "a ser criado no primeiro uso". Manter é a opção honesta: o `[planejador]`
> (precificação, marketing, concorrência) é um agente distinto do `[auxiliar]` (MVP,
> roadmap, mercado), então apontar um para o diretório do outro misturaria artefatos de
> dois papéis. E o próprio `AGENTS.md` já diz que não se cria diretório vazio só para
> satisfazer a tabela. **De passagem:** `artefatos/auxiliar_negocios/` está no mesmo caso
> (existe só como diretório vazio local, não rastreado pelo git) e recebeu a mesma nota.

#### C5 · Exemplo de arquivo inexistente — **BAIXA / trivial**
- **DOC:** `AGENTS.md:140` cita `questionario_pos_venda.md`.
- **REALIDADE:** o arquivo é `questionario_rita_v1.md`.

> **✅ Resolvido em 2026-09-19.** Exemplo trocado em `AGENTS.md`. Os outros três nomes de
> arquivo citados na mesma tabela foram conferidos e existem.

#### Verificados e fiéis (sem achado)
- **`CLAUDE.md`** — todas as afirmações checáveis conferem: pipeline do `processar()`, rotas, ordem QA→RAG→templates, `ModoExecucao`/`ModoOperacao`, factories, modelo de domínio, componentes do frontend, cores do Tailwind, `testador_conversas/`.
- **`docs/arquitetura_motor_conversacao_2026-07.md`** — conferido ponto a ponto, inclusive detalhes finos: prioridade absoluta do `exclusivo` (`motor.py:76`), junção de fragmentos com `"\n\n"`, `REGISTRO_POR_FASE` só com Esclarecendo/Finalizando (`processador.py:90-93`), `_processar_finalizando` de fato removido.

---

### Eixo B — Inconsistência interna

#### B1 · Estado e evento de auditoria em transações separadas — **ALTA / médio**
- **Padrão de referência:** o pipeline deve persistir de uma vez no commit final de `processar()` (`services/processador.py:370`).
- **Violação:** `services/conversacao/estados/base.py:35-49` (`transicionar_para`) altera `atendimento.fase`, faz `ctx.db.commit()` (linha 40) e **só depois** chama `registrar_evento_atendimento`, que faz o **próprio** `db.add`+`db.commit()` (`services/atendimentos.py:59-60`). Duas transações para uma transição lógica. Repete-se em `estados/finalizando.py:267-280` (`concluir`, com mais commits para `modo_operacao`) e em `estados/finalizando.py:400-405`, que ainda mistura as duas estratégias na mesma função (`db.commit()` na linha 404, `_remover_info_atendimento` com `flush()` na linha seguinte).
- **Impacto:** se o segundo commit falhar, o atendimento muda de estado **sem o evento de auditoria** — quebrando a trilha que o `CLAUDE.md` define como fonte de verdade para "por que o bot respondeu X". No pior caso (`concluir`), `modo_operacao=HUMANO` fica commitado — **suprimindo toda resposta automática futura** — sem a mensagem de handoff que explicaria isso. Atendimento travado, silenciosamente.

#### B2 · `_atualizar_infos_atendimento` duplica o helper e manteve o commit — **MÉDIA / pequeno**
- **Helper correto:** `services/processador.py:1243-1264` (`_salvar_info_atendimento`), já com `flush()`.
- **Duplicação:** `services/processador.py:1351-1375` reimplementa o mesmo get-or-create inline e termina com `db.commit()` (linha 1375) — o padrão que acabou de ser corrigido no vizinho, numa cópia que passou despercebida. Chamado de dentro de `_decidir_resposta`, antes do commit final.
- **Impacto:** commit parcial no meio da decisão + lógica duplicada que tende a divergir (um lado ganha bugfix, o outro não).

#### B3 · Três variantes de tratamento de erro em `main.py` — **MÉDIA / pequeno**
- **Variante 1 (maioria):** `backend/main.py:589-802` — sem tratamento; exceção inesperada vira 500 sem nenhum log da aplicação.
- **Variante 2:** `backend/main.py:1100-1108` — `print(f"[ERRO REPROVAR]...", flush=True)` (linha 1106) **e** `logger.error`. O `print` ignora o `LOG_LEVEL` documentado no `CLAUDE.md` e sempre escreve em stdout.
- **Variante 3:** `backend/main.py:1536-1540` — `logger.exception` + `HTTPException`, sem `print`.
- **Impacto:** erros em produção na maioria dos endpoints não deixam rastro; observabilidade inconsistente.

#### Convenções verificadas e íntegras (sem achado)
Nenhum `psycopg` cru fora de `services/` · ordem estático-antes-de-dinâmico correta em **todas** as rotas de `main.py` e `routers/pares_qa.py` · **zero** imports de submódulo de `models` · nenhum `datetime.utcnow()`/`datetime.now()` naive em código persistido.

---

### Eixo A — Decidido mas não implementado

*(restrito a fases marcadas como implementadas; fase não iniciada não é achado)*

| # | Achado | Evidência | Sev. | Esforço |
|---|---|---|---|---|
| **A1** | REQ-011.18: promover para `execucao_normal` deveria exigir confirmação explícita e mostrar aprovadas vs. reprovadas no período | REQ-011:149-154,291 × `frontend/src/components/Header.jsx:37-50` (troca direto no `onChange`), `main.py:1753-1777` | Média | Pequeno |
| **A2** | `EventoAtendimento.mensagem_id`/`processamento_id` existem e são migrados, mas **nenhum dos 7 call sites preenche** | `models/atendimento.py:263-266` × `processador.py:793-801,917-925`, `estados/finalizando.py:272-280`, `atendimentos.py:112-120,157-165,305-311,348-355` | Média | Pequeno/médio |
| **A3** | REQ-012.6: matriz de transição de status de report diverge (ex.: `resolvido` reaberto deveria ir para `em_analise`, vai para `aberto`) | REQ-012:132-137 × `main.py:1133-1144`; sem cobertura de teste | Média | Trivial |
| **A4** | REQ-012.8: edição de categoria/severidade deveria gerar histórico | REQ-012:148 × `main.py:1202-1257` (só status gera `HistoricoStatusReport`) | Média | Pequeno |
| **A5** | REQ-004.5A: pré-qualificação mínima (CNPJ + produto) antes de escalar por projeto complexo/baixa confiança | REQ-004 §4.1 × `regras_globais.py:67-84` (só checa entidades da mensagem atual) | Média | Médio |
| **A6** | REQ-010.7B: campos já capturados deveriam aparecer no topo da conversa, não só em modal | plano:145 × `main.py:616-636` (só pendências), `ConversaInfo.jsx` | Média | Pequeno |
| **A7** | REQ-016.17: perguntas de continuação/fechamento deveriam virar eventos auditáveis | REQ-016:191 × `TipoEventoAtendimento` (`models/atendimento.py:48-59`) sem valor correspondente; só vai para log de arquivo | Baixa/média | Pequeno |
| **A8** | REQ-016.9: resposta ambígua resolve direto pelo default, sem os "até 2 esclarecimentos" | REQ-016:144 × `processador.py:756-772` (o próprio docstring, :702-704, admite a simplificação) | Baixa | Médio |

**Fases 3, 7 e 9 (REQ-003 RAG, REQ-014 config runtime, REQ-013 Q&A) reconfirmadas íntegras**, sem regressão desde a reauditoria de julho. Também confirmados: gate de aprovação por `ModoExecucao`, escalonamento setando `modo_operacao=HUMANO` de fato, autenticação real cobrindo rotas administrativas, matriz REQ-016.7 completa, bug de vazamento de resposta antes da aprovação corrigido.

---

### Memórias × código

#### M1 · Memória descreve um Template Method que não existe — **ALTA / trivial**
- **MEMÓRIA** `project_mvp_continuidade_state_pattern.md`: *"State pattern combinado com **Template Method**: `EstadoAtendimento` é uma classe-mãe abstrata com um método concreto (ex. `processar_mensagem`) que faz o tratamento inicial genérico, chama um método abstrato (`tratamento_principal`)... e depois faz o tratamento final genérico."*
- **CÓDIGO:** `services/conversacao/estados/base.py:1-11,24-33` — o State pattern existe (ABC + `tratamento_principal` + subclasses), mas **não há `processar_mensagem`** envolvendo pré/pós. A reversão foi **consciente e documentada**: `docs/arquitetura_motor_conversacao_2026-07.md:199-200` diz que "não é um Template Method no sentido GoF... adicionar hooks vazios só para completar o padrão seria abstração especulativa".
- **Classificação:** código divergiu da decisão original, de forma deliberada e justificada — mas **nenhuma memória registrou a reversão**.
- **Impacto:** quem ler só a memória procura um método que não existe. **A correção é na memória, não no código.**

> **✅ Resolvido em 2026-09-19.** O item 5 da memória foi reescrito em três parágrafos: o
> que foi decidido em 2026-07-09, o que o código faz hoje (State puro, `tratamento_principal`
> abstrato, `transicionar_para` como único concreto, pré/pós a cargo do motor de Ações) e
> por que reverteu, citando `docs/arquitetura_motor_conversacao_2026-07.md:195-203`. A
> decisão original ficou preservada: quem ler entende que houve escolha, não esquecimento.

#### M2 · Nome de símbolo desatualizado — **BAIXA / trivial**
- **MEMÓRIA** `project_motor_intencao_fase_acoes.md` cita `_builder_categoria3`; o código renomeou para `_builder_categoria_pergunta` (`regras_esclarecendo.py:244`, commit `5f2e68f`). Comportamento intacto (`ctx.fragmentos_ate_agora` continua na linha 262). Correção na memória.

> **✅ Resolvido em 2026-09-19.** Rename aplicado na memória.

#### Confirmado fiel
A regra "nunca voltar a um if/elif central de intenção em `processador.py`" está sendo respeitada — **zero ocorrências de `Intencao.` no arquivo inteiro**. `_gerar_resposta_por_intencao` continua removido. Renomeação Produto/Modelo, `create_all()` removido, `AtendimentoInfo` ainda EAV sem `item_atendimento_id` (limitação registrada, ainda real).

---

### Testes

- **Placar atual:** `7 failed, 259 passed` — as 7 falhas são inteiramente o P0-2 (revertendo, `12 passed` no arquivo afetado).
- **T1 · `POST /api/atendimentos/{id}/mensagens-manuais` (`main.py:778`) sem nenhum teste** — é o caminho de resposta manual em `ModoOperacao.HUMANO`, citado no `CLAUDE.md` como parte do pipeline. Nem o comportamento atual ("só grava, não envia") está coberto. **Média / pequeno.**
- **T2 · `MensagemId.COMPATIBILIDADE_SISTEMA` definido e nunca roteado** — `services/respostas/catalogo.py:176-181` define o template; **nenhum outro ponto do código o referencia**. A regra de negócio do `CLAUDE.md` ("sempre deferir compatibilidade para validação técnica") depende hoje só de instrução solta no prompt (`services/respostas/gerador.py:50,66-67`), sem rota determinística nem teste. **Média-alta / médio.**
- **T3 · O gap de "aprovar não entrega" não tem sinal executável** — existe só como texto no `CLAUDE.md`; um teste `xfail` nomeando a lacuna evitaria que ela seja esquecida. **Baixa / trivial.**
  - **⊘ Obsoleto em 2026-09-19.** Não foi resolvido como estava escrito, deixou de fazer
    sentido: o gap que o `xfail` iria nomear foi **fechado** pelo commit `55f4e4a`
    (canal de saída + `services/envio.py`, REQ-008 Fase 10). Aprovar agora entrega de
    verdade quando `CANAL_SAIDA=twilio`. Um teste marcando a lacuna como esperada passaria
    a documentar algo falso. O que faz sentido no lugar é teste **normal** do caminho de
    entrega, e isso é escopo do REQ-008, não desta auditoria.
- Sem testes tautológicos, sem mocks substituindo a unidade sob teste.

---

### Frontend × API — contrato coerente

Os 44 métodos de `services/api.js` batem com as rotas do backend; nenhuma cor fora dos tokens; tratamento de erro consistente. Quatro achados **BAIXA**: `created_at` exibido em UTC cru no modal de raciocínio (`ProcessamentoDetalhes.jsx:458`, sem `formatDatetimeBRT`); motivo `modelo_nao_reconhecido` sem rótulo amigável (`utils/atendimento.js:36-43`); campos de encerramento/reabertura enviados e nunca exibidos (`models/atendimento.py:222-227`); `historico_status` do report consultado no backend (`main.py:1486-1499`) e nunca renderizado (`ReportDetalhe.jsx:62`).

---

## 3. Roadmap priorizado

**Rubrica de modelo:** `opus` para design, ambiguidade ou mudança transversal · `sonnet` para edição localizada com especificação clara · `haiku` para mecânico e verificável.

### P0 — Desbloquear (fazer antes de qualquer outra coisa)

**✅ Bloco concluído em 2026-09-16.**

| # | Tarefa | Arquivos | Modelo | Situação |
|---|---|---|---|---|
| 1 | Declarar `TWILIO_API_KEY_SID`/`TWILIO_API_KEY_SECRET` em `Settings` | `backend/config.py` | **haiku** | ✅ `02d66ef` |
| 2 | Corrigir a obsolescência do cache mantendo o `flush()` | `backend/services/processador.py:1243-1264`, `services/conversacao/estados/finalizando.py:203,239` | **opus** | ✅ `6455022` — expire seletivo no escritor |
| 3 | Rodar a suíte e confirmar `266 passed` | — | **haiku** | ✅ **272 passed** (266 previstos + 6 testes novos) |

### P1 — Integridade e correção

| # | Tarefa | Arquivos | Modelo | Situação |
|---|---|---|---|---|
| 4 | Unificar transição de estado + evento de auditoria em uma transação | `estados/base.py:35-49`, `services/atendimentos.py:59-60`, `estados/finalizando.py:267-280,400-405` | **opus** | ✅ resolvido — commit único; `registrar_evento_atendimento` passou a `flush()` |
| 5 | Fazer `_atualizar_infos_atendimento` delegar ao helper | `services/processador.py:1351-1375` | **sonnet** | ✅ resolvido — delega e não commita mais; união D6 preservada e agora testada |
| 6 | Rotear `COMPATIBILIDADE_SISTEMA` de forma determinística + teste | `services/respostas/catalogo.py`, `services/classificador.py`, `services/conversacao/regras_*.py` | **opus** | **aberto — investigado em 2026-09-16, ver nota** |
| 7 | Corrigir matriz de transição de report (REQ-012.6) + testes | `backend/main.py:1133-1144` | **sonnet** | ✅ resolvido — 5 divergências (não 1); frontend tinha cópia da matriz errada |
| 8 | Preencher `mensagem_id`/`processamento_id` nos eventos | 7 call sites de `registrar_evento_atendimento` | **sonnet** | ✅ resolvido — back-fill no fim de `processar()`, não nos call sites |

> **Nota sobre o #8 (achado A2), descoberta em 2026-09-16.** O item é menos mecânico do que
> parecia. `mensagem_id` está disponível (o `msg_in` é criado e flushado em
> `processador.py:226` antes de `_decidir_resposta`), mas **`processamento_id` não existe
> ainda** quando os eventos são gravados: `_criar_processamento` roda *depois* de
> `_decidir_resposta` e recebe a `resposta` como entrada — ele registra o resultado da
> decisão, então não dá para antecipá-lo.
>
> **Resolvido por back-fill**, aprovado em 2026-09-16: uma marca d'água antes da decisão
> (`max(EventoAtendimento.id)`) e um `UPDATE` dos eventos deste atendimento criados depois
> dela, logo após `_criar_processamento`. Um lugar só, em vez de acrescentar o parâmetro a
> seis assinaturas (`_escalar_atendimento`, `_reiniciar_qualificacao` e afins), onde um
> chamador esquecido falharia em silêncio com `None`. Só é viável **por causa do #4**: sem
> os commits intermediários, os eventos ainda estão na transação nesse ponto.

> **Nota sobre o #6, investigação de 2026-09-16 (medições no banco real).**
>
> A pergunta que motivou: como garantir que "funciona com ABC **V1.0.1**?" não receba a
> resposta cadastrada para **V1.0.2**, se as duas frases são quase idênticas?
>
> **O mecanismo de discriminação exata já existe** e é a camada full-text do
> `QAService.buscar()`, que roda **antes** do embedding e curto-circuita quando acerta:
> - O parser do Postgres trata `V1.0.1` como **um token único, não stemizado**, distinto
>   de `v1.0.2`.
> - `plainto_tsquery` liga os termos com **AND**, então o par da V1.0.2 não é sequer
>   candidato para uma pergunta sobre V1.0.1.
> - Medido com dois pares reais: a consulta por V1.0.1 devolve só o par da V1.0.1,
>   `ts_rank` 0.4571 (limiar de full-text **0.30**, chave `qa_fulltext_responde_min` da
>   tabela `parametros`). *Correção de 2026-09-19: o texto original desta auditoria dizia
>   `QA_SCORE_MINIMO_FULLTEXT` = 0.25; esse campo está morto, ver achado C6 abaixo. A
>   conclusão não muda, porque 0.4571 passa nos dois valores.*
>
> **Por que a ordem das camadas é a proteção inteira:** a similaridade de cosseno entre as
> duas perguntas é **0.9957**, muito acima do `QA_SCORE_MINIMO` de 0.80. Pelo embedding elas
> são indistinguíveis.
>
> **Onde quebra (o risco real, e o que o #6 precisa resolver):** o token tem que bater
> exatamente. Variações que o cliente escreve geram lexemas diferentes —
> `V1.0.1` → `'v1.0.1'`, `1.0.1` → `'1.0.1'`, `V 1.0.1` → `'v' & '1.0.1'`,
> `V1.01` → `'v1.01'`. Qualquer uma que não case erra o full-text e **cai no embedding**,
> que devolve com confiança a resposta da versão errada. O mesmo vale quando não há par
> cadastrado para aquela versão. **A falha não é segura: degrada em silêncio para a camada
> que não sabe distinguir.**
>
> **Desenho proposto (aguardando decisão):** a guarda não deve ser "tornar o match exato" —
> já é, quando acerta. Deve ser: quando a pergunta contém um identificador de versão/modelo
> (padrão tipo `\bv?\s?\d+(\.\d+)+\b`), o sistema **não pode responder pela camada
> semântica**; se o full-text não casou com aquele token exato, roteia para validação
> técnica. É determinístico, testável, e é a regra de negócio que o `CLAUDE.md` já declara.

---

## Achados descobertos durante a correção (não estavam na auditoria original)

| # | Achado | Onde | Situação |
|---|--------|------|----------|
| **B1-bis** | Mais duas ocorrências do B1 que a auditoria não listou: `db.commit()` entre a mudança de estado e o evento em `_reiniciar_qualificacao` e em **`_escalar_atendimento`** | `services/processador.py:793,917` | ✅ corrigido junto com o #4 |
| **A3-bis** | O frontend mantém uma **cópia própria** da matriz de transição de reports, que espelhava a versão errada | `frontend/src/constants/reports.js:30-36` | ✅ corrigido junto com o #7 |
| **A2-bis** | Com `mensagem_id` finalmente preenchido, a FK `eventos_atendimento_mensagem_id_fkey` passou a ter efeito e a limpeza por telefone quebrou: apagava `mensagens` antes dos eventos que as referenciam | `services/dev_limpeza_telefone.py` | ✅ corrigido; ordem passou a eventos → mensagens |
| **C6** (eixo C) | `settings.QA_SCORE_MINIMO_FULLTEXT = 0.25` está **morto** (zero consumidores); o limiar que governa o filtro vem da tabela `parametros`, chave `qa_fulltext_responde_min`, valor real **0.30**. Dois documentos citavam 0,25 como se valesse | `backend/config.py:94` (definição), `backend/services/rag/qa_service.py:336` (uso real), `backend/services/parametro_service.py:213`; docs afetados: `docs/auditoria_consistencia_2026-08.md:249`, `docs/arquitetura_avaliacao_rag_2026-07.md:30,71` | ✅ documentos corrigidos em 2026-09-19; **o código não foi tocado** |
| **C7** (eixo C) | `npm run lint` **nunca funcionou** neste projeto: até 2026-09-19 não havia nenhuma config de ESLint em `frontend/` (nem `.eslintrc*`, nem `eslint.config.js`) e, sem `.eslintignore`, o ESLint 8 ainda varreria `frontend/dist/`. O comando está documentado no `CLAUDE.md` como comando do projeto | `frontend/package.json:10` (script), `CLAUDE.md` (seção Frontend), ausência de config em `frontend/` | registrado em 2026-09-19; correção em andamento por outra frente (setup do ESLint) |
| **C8** (eixo C) | `POST /webhook` recusa mensagem **sem texto**: `Body: str = Form(...)` faz o FastAPI tratar string vazia como campo ausente e devolver **HTTP 422**. É o caso da mensagem só com mídia (`NumMedia>0`), que a conversa real de cliente em `docs/` mostra ser comum (foto e áudio). A mensagem do cliente se perde sem registro nenhum. Confirmado empiricamente em 2026-09-19 | `backend/main.py` (assinatura de `webhook_twilio`) | aberto em 2026-09-19 |
| **B4** (eixo B) | `apagar_dados_telefone` limpa contato, atendimento e mensagens, mas **não** as `empresas` criadas pela consulta de CNPJ, nem `atividades_empresa`/`socios_empresa`. A empresa sobrevive à limpeza e à rodada seguinte, então um cenário de "CNPJ novo" passa a exercitar, sem avisar, o caminho de "empresa já conhecida" | `backend/services/dev_limpeza_telefone.py` | aberto em 2026-09-19 |
| **T4** (testes) | Os cenários do testador e a suíte de pytest compartilham o mesmo banco e usavam o **mesmo CNPJ** (`11222333000181`). A bateria de 2026-09-19 gravou a empresa e quebrou `test_regras_globais::test_fornecer_cnpj_cria_atendimento_vinculado_a_empresa_existente` com violação de unicidade. Agravante: o CNPJ "fictício" é de uma entidade **real**, e a consulta à Receita trouxe os dados dela para o banco | `testador_conversas/cenarios_exportados/cnpj_sem_pontuacao_com_nome_junto.yaml` × `backend/tests/test_regras_globais.py` | ✅ corrigido em 2026-09-19: CNPJ do cenário trocado, registro removido do banco |
| **D1** (defeito de comportamento) | A captura de resposta em Finalizando exigia intenção `DESCONHECIDO`, mas o classificador reconhece `"sim"` isolado como `CONFIRMAR` e `"não"` como `NEGAR`. Responder "sim" para a pergunta de nuvem, ou "não" para a de software, **não gravava nada e o bot repetia a pergunta**. Os 12 testes de coleta ativa não pegavam porque todos injetam `DESCONHECIDO` fabricada, inclusive para o conteúdo `"sim"` | `services/conversacao/estados/finalizando.py:466` × `services/classificador.py:205-217` | ✅ corrigido em 2026-09-19 (`175ab15`) |

O `_escalar_atendimento` merece nota: era exatamente o "pior caso" descrito no B1
(`modo_operacao=HUMANO` commitado sem o evento que o explica), só que noutra função —
a auditoria o descreveu a partir de `concluir` e não varreu os demais escalonamentos.

O A2-bis é o tipo de defeito que só aparece quando a coluna deixa de ser sempre nula: a
FK existia desde a migration, mas nunca tinha sido exercitada.

O **C6** é do mesmo tipo dos achados originais do eixo C, só que encontrado agora: um valor
documentado em dois lugares que nunca governou nada. Vale registrar a consequência operacional,
porque ela sobrevive à correção dos documentos: `POST /api/config/rag/reset`
(`backend/main.py:1942`) restaura `qa_embedding_responde_min` a partir de
`settings.QA_SCORE_MINIMO`, mas **não restaura nenhum limiar de full-text**. Quem apertar
"resetar" achando que volta tudo ao default continua com o `qa_fulltext_responde_min` que
estiver no banco. Ajustá-lo hoje só é possível pelo `PATCH /api/parametros/{nome}` genérico.
Decidir se o campo morto sai do `Settings` ou se vira a fonte do reset é mudança de código,
fora do escopo desta passada de documentação.

O **C7** é um caso de comando documentado que nunca rodou. Foi registrado aqui e deixado para
a frente que montou o setup do ESLint na mesma data (`frontend/.eslintrc.cjs` e
`frontend/.eslintignore` apareceram no working tree durante esta passada); esta frente não
tocou `frontend/`. Confirmar que `npm run lint` passa faz parte daquele trabalho, não deste.

### P2 — Documentação e memórias (barato, alto retorno)

| # | Tarefa | Arquivos | Modelo | Por quê |
|---|---|---|---|---|
| 9 | Corrigir caminho dos 4 scripts RAG | `docs/comandos_uteis.md:481-526` | **haiku** | Inserir `base_conhecimento\`; verificável rodando |
| 10 | Atualizar lista da limpeza de telefone | `docs/comandos_uteis.md:580,594` | **haiku** | Trocar nome + acrescentar tabela |
| 11 | Atualizar memória do MVP sobre o Template Method | memória `project_mvp_continuidade_state_pattern.md` | **sonnet** | Precisa redigir a correção referenciando a justificativa da reversão, não só apagar |
| 12 | Corrigir `_builder_categoria3` → `_builder_categoria_pergunta` | memória `project_motor_intencao_fase_acoes.md` | **haiku** | Rename puro |
| 13 | Corrigir C3/C4/C5 | `docs/comandos_uteis.md:736`, `AGENTS.md:55,140` | **haiku** | Três edições pontuais |

### P3 — Requisitos com última milha faltando

| # | Tarefa | Modelo | Por quê |
|---|---|---|---|
| 14 | REQ-011.18: confirmação + indicadores ao promover para `execucao_normal` | **sonnet** | UI + endpoint com spec no próprio REQ |
| 15 | REQ-012.8: histórico de edição de categoria/severidade | **sonnet** | Padrão já existe para status |
| 16 | REQ-010.7B: campos capturados no topo da conversa | **sonnet** | Endpoint e componente já existem |
| 17 | REQ-004.5A: pré-qualificação antes de escalar | **opus** | Muda quando o sistema escala — regra de negócio com efeito no cliente |
| 18 | T1: teste do endpoint de mensagem manual | **sonnet** | Escrever teste com fixtures existentes |
| 19 | REQ-016.17 / REQ-016.9 | **opus** (016.9) / **sonnet** (016.17) | 016.9 depende da política de retry cross-cutting; 016.17 é acrescentar valor ao enum |

### P4 — Cosmético

Os quatro achados de frontend (F1-F4) e o T3 (`xfail` documentando o gap de entrega): **haiku**, todos verificáveis na tela ou na suíte.

> **Observação sobre o P1-4 e o desenho da pilha de perguntas pendentes:** a tarefa 4 mexe exatamente na fronteira transacional que a futura pilha vai usar para empilhar/desempilhar perguntas. Vale fazê-la **antes** de começar o passo 1 da migração da pilha, para não construir sobre uma base que vai mudar.

---

## 4. Deliberadamente fora do escopo

- **Fases não iniciadas** (Fase 10/Twilio, Fase 11+): ausência já é conhecida e rastreada; não é inconsistência.
- **Gaps declarados no `CLAUDE.md`** (sem cliente REST Twilio; aprovar/responder manualmente só altera o banco): documentados como limitação conhecida, portanto não são "documentado mas falso".
- **Cobertura percentual de testes:** pedido explicitamente lacunas nomeadas, não métrica.
- **Estilo, formatação, refatoração sem defeito associado**, acessibilidade e UX.
- **Varredura exaustiva dos ~30 arquivos de teste** em busca de tautologias: foi feita amostragem dirigida (escalonamento, modo de execução, endpoints administrativos), não cobertura total.
- **Verificação linha a linha de todas as chaves ad hoc de `AtendimentoInfo`:** confirmada a existência e amostra, não a cobertura completa.
- **Decisões de negócio sem afirmação técnica verificável** (escolha do chip pré-pago, preferências de ferramenta).
- **Colisão janela de 24h × gate de aprovação (REQ-011):** identificada nesta sessão e registrada no handoff do spike Twilio; é decisão de produto pendente, não inconsistência de implementação.
