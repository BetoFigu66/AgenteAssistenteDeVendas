# Janela de 25/09 (tarde/noite): progresso passo a passo

<!-- CLASSIFICACAO: PROCESSO -->

Arquivo de retomada. Atualizado **ao fim de cada passo**, para que, se a quota acabar no
meio, a sessão agendada para 22:10 (ou uma nova) saiba exatamente de onde continuar e refaça
só o passo interrompido.

**Branch:** `janela/2026-09-25` (local, sem push). O Beto revisa e faz o merge em `develop`.
**Plano de origem:** `2026-09-23_plano_twilio_4_dias.md`.

## Decisões do Beto (25/09 ~18:10)

1. Commitar na branch local, sem push.
2. Bugs de documento e localização: opção (a), sem migração. Documento vira
   `[documento recebido: <nome>]`, localização vira `[localização: <lat>, <lon>]` no `conteudo`.
3. Idempotência do webhook: sim. `MessageSid` repetido devolve 200 com TwiML vazio.
4. Escalonamento pelo texto longo: não investigar, pode estar correto.
5. Modo de teste fica ligado até amanhã.
6. INFOR-REL: deixar como está.
7. `ProfileName`: usar o nome que o WhatsApp manda, passando por um método de validação
   (por ora só tamanho mínimo: 3 caracteres alfabéticos), para não gerar "Olá ~~~, tudo bem?".
8. Retomada agendada para 22:10.

## Passos (marcar `[x]` ao concluir, com o commit)

### Leva 1 (em paralelo)
- [x] **W. Webhook:** (commit `b23c4cb`) `MessageType` para documento e localização, idempotência por
  `MessageSid`, fixtures anonimizadas dos payloads reais, testes de webhook com os
  formulários reais, isolar testes do `.env`.
- [x] **P. ProfileName:** (commit `8a7939a`) método de validação do nome + uso do `ProfileName` onde o sistema
  hoje pergunta o nome (só em `services/`; a ligação no `main.py` fica para o passo 3).

### Depois da leva 1
- [x] **3. Ligar o `ProfileName` no `/webhook`** e commitar W e P. (em `b23c4cb`; 437 passando, ruff limpo)
- [x] **4. Cenários de negócio pelo testador** (relatório `artefatos/qa/2026-09-25_cenarios_testador.md`, commit `3013a70`) (backend estável; divergências separadas para
  o Beto aceitar ou rejeitar, nada aceito automaticamente).
- [x] **5. Revisão de código** (relatório `artefatos/qa/2026-09-25_revisao_branch_janela.md`; A1-A4 corrigidos em `273b0bd`) (`/revisao-codigo`) sobre o diff da branch; corrigir achados.
- [x] **6. Documentação:** (commit `7c52b24`; o `STATUS.md` do spike é local, gitignored) `docs/comandos_uteis.md` e `STATUS.md` do spike.
- [x] **7. Atualizar o plano** e deixar a lista de decisões pendentes para o Beto.

## Respostas do Beto (26/09 09:00)

- **Nome do WhatsApp (decidido):** no início do atendimento, se o `ProfileName` passar na
  validação, perguntar "Olá, <nome>! Posso te chamar assim ou seu nome é outro?"; se não
  passar, segue o fluxo atual de perguntar o nome. **Muda o que o commit `8a7939a` faz**
  (hoje ele usa o nome direto, sem perguntar): vira item de implementação (I1 abaixo).
- **Logs de andamento:** passam a ter `dd/MM HH:MM (X%) [sigla]:`. A quota eu não consigo
  ler; uso a última informada ou `(?%)`.
- **Novas frentes pedidas:** página de manutenção durante deploy (I2) e isolamento da
  escrita do container no disco da máquina (I3).

## ⏩ Beto: decisões pendentes (revisado 26/09 09:15)

Entre parênteses, a minha recomendação.

**A. Fechar a branch `janela/2026-09-25` (9 commits, sem push)**
1. Revisar e fazer o merge em `develop`. Mais sensíveis: `273b0bd` (segurança do download)
   e `8a7939a` (nome de perfil; será ajustado pelo I1, então pode revisar depois dele).
2. Confirmar as decisões embutidas: nome digitado depois substitui o do perfil; perfil
   nunca vai para `Pessoa.nome`; emoji junto de letras é mantido; a fixture de testes zera
   as credenciais Twilio; localização com `Body` preenchido também vira marcador.

**B. Implementação já decidida ou que só precisa de "sim"**
- [x] **I1. Confirmação do nome do WhatsApp** (commit `f51ea13`, 504 passando). Decisões a revisar no corpo do commit.
- **I2. Página de manutenção no deploy.** Escolher o formato (opções em "Frentes novas").
- **I3. Isolar a escrita do container.** Escolher o formato (opções em "Frentes novas").
- **I4. Correções de produto achadas pela varredura** (sim/não para cada):
  compatibilidade não vai para validação técnica; reclamação não é detectada; "45
  funcionários" e "1) 2) 3)" viram quantidade; "sou pessoa física" vira pedido de humano.

**C. Produto (precisam de escolha, não só de "sim")**
3. Catraca recebe a pergunta de relógio: (1) template por produto, texto da Kika;
   (2) relógio mantém o texto e os demais usam o genérico; (3) limitar a repetição da
   mesma pergunta (N e ação a definir). (2 hoje, 3 com N=2 e reformular.)
4. A Inforrel vende câmera (o template diz "Sim, Intelbras")? Leitor facial é sempre
   projeto complexo? Duas cortesias seguidas devem escalar?

**D. Testador**
5. Aceitar/rejeitar as respostas: lista em `artefatos/qa/2026-09-25_cenarios_testador.md`.
6. Reimportar `mensagem_vazia_ou_so_midia`; corrigir o default `"now()"` do
   `testador_conversas/models.py` (exige `ALTER` no schema `teste_conversas`); trocar o
   CNPJ "fictício" `11222333000181`, que é real. (Sim para os três.)

**E. Revisão (detalhes em `artefatos/qa/2026-09-25_revisao_branch_janela.md`)**
7. A5: registrar a origem do nome do perfil de verdade (migração) ou manter a comparação.
   (Revisitar junto com o I1: a confirmação do cliente é o momento natural de gravar a
   origem.)
8. Estender o dublê de `ModoExecucao` ao `test_processador_modo_execucao.py`. (Sim.)
9. B1: reentrega após timeout perde a resposta e o banco diz "entregue". (Anotar para o
   piloto.)
10. B4: caracteres invisíveis passam na validação do nome. (Entra na regra definitiva.)
11. B8: `debug_log.py` tem `19991931176`, a um dígito do seu número. (Trocar.)

**F. WhatsApp (~25 min seus):** lista do topo do plano de 23/09. Ao terminar,
`./scripts/twilio_modo_teste.sh desligar`.

## Frentes novas (26/09), com opções

**I2. Página de manutenção.** Caminho atual: Cloudflare → túnel → `localhost:3000` (nginx
do container `frontend`) → `backend:8000`.
- (a) **nginx serve `manutencao.html` quando o backend não responde** (`error_page 502 503
  504`). Automático, sem script; mas não sabe desde quando, e não cobre o rebuild do
  próprio `frontend` (aí quem responde é a Cloudflare, com o erro dela).
- (b) **Script `deploy.sh` com arquivo-bandeira:** grava a página com "em manutenção desde
  dd/MM/aa hh:mm", o nginx devolve 503 com ela enquanto a bandeira existir, o script faz o
  deploy e remove a bandeira. Tem o horário que você pediu; é a (a) mais um script.
- Em ambas, o `/webhook` fica de fora da página: a Twilio não entende HTML e não reentrega,
  então mensagem que chegar no meio do deploy se perde (fica só no log da Twilio). Isso é
  limite do modo TwiML, não do deploy.
- (Recomendo b, que inclui a a.)
- **Ideia do Beto (26/09) para o `/webhook`:** com a bandeira ativa, o nginx responde ele
  mesmo na rota `/webhook`, com HTTP 200 e TwiML `<Response><Message>Sistema em manutenção,
  tente mais tarde.</Message></Response>` (`application/xml`); `/webhook/status` responde 200
  vazio. **Funciona**: a Twilio só quer TwiML válido, não importa quem o gere. O cliente é
  avisado em vez de ficar sem resposta. Limites: a mensagem dele não entra no nosso banco
  (fica só no log da Twilio), e não cobre o instante em que o próprio container `frontend`
  é recriado. Entra no formato (b).

**I3. Isolar a escrita do container.** Hoje o `docker-compose.yml` monta `./backend:/app`
(bind mount) e o container roda como **root**: tudo que o backend grava cai no seu disco,
inclusive dentro do código-fonte. O path traversal de 25/09 era grave por isso: gravar um
`.py` em `backend/` faria o `--reload` executá-lo.
- (a) **Código montado só para leitura (`./backend:/app:ro`) e `logs/` num volume nomeado
  do Docker.** O container deixa de escrever no seu disco; o `--reload` continua funcionando.
  Custo: `logs/` e anexos passam a ser lidos com `docker cp`/`docker exec`, e o
  `analisar_payloads_twilio.py` e as fixtures precisam apontar para lá.
- (b) (a) **mais usuário não-root** no `Dockerfile`. Fecha também escrita em qualquer lugar
  do container fora do volume. Exige rebuild da imagem.
- (c) Sem bind mount no ambiente público (imagem com o código copiado). Mais isolado, mas
  perde o `--reload`: todo ajuste vira rebuild.
- Não verificado: onde o Docker Desktop guarda o volume nomeado (disco virtual do WSL, não
  em `C:\Beto`) e se algum script do repositório lê `backend/logs/` pelo caminho do host.
- (Recomendo b.)

## Frente E: registro do que levou ao escalonamento (26/09)

Decisões do Beto (26/09 09:59): tabela nova `escalonamentos`; avaliação humana
(procedente/indevido) já nesta entrega, com tela; só escalonamentos futuros; estende o
REQ-004 (novos REQ-004.5B e 5C, v1.9).

- [x] **E1. Especificação** em `artefatos/requisitos_formais/REQ-004-human-takeover-escalonamento.md`.
- [x] **E2. Backend:** (commit a seguir; 522 passando, migração `2026092601` aplicada) model + migração Alembic, registro no `_escalar_atendimento`
  (`processador.py:1097`, ponto único das 7 chamadas) com gatilho e evidências vindos de
  cada chamada, endpoints de leitura e avaliação, testes. **Esperar o [N] (I1) terminar**:
  mexe nos mesmos arquivos.
- [ ] **E3. Frontend:** gatilho, evidências e avaliação no painel do atendimento escalado.
- [ ] **E4. Revisão e commit.**

## Registro

- 18:10 branch criada; commits `035d2e7` (download de mídia) e `fa0ae7b` (plano).
- 18:17 leva 1 disparada (W e P em paralelo, sem commit; eu commito ao fim de cada um). Retomada agendada para 22:10.
- 18:25 P concluído: 412 passando, ruff limpo. Arquivos: `utils/nome_perfil.py`, `tests/test_nome_perfil.py`, `tests/test_processador_nome_perfil.py`, `services/processador.py`, `services/conversacao/{acoes,regras_globais,regras_esclarecendo}.py`, `estados/esclarecendo.py`. Falta a ligação no `main.py` (passo 3): `ProfileName: Optional[str] = Form(None)` no `/webhook`, repassar `nome_perfil=ProfileName` em `_processar_via_cerebro` e daí para `processador.processar(...)`.
  Decisões do P para o Beto revisar: nome digitado depois substitui o do perfil; perfil nunca vai para `Pessoa.nome`; emoji junto de letras é mantido; origem registrada só em `ProcessamentoMensagem.entidades` (durável exigiria migração); mensagem só com mídia não preenche nome.
  Achado fora do escopo: "Quero orçamento de catraca" responde perguntando sobre **relógio** ("cartográfico ou eletrônico?"). Já acontecia antes.
- 18:25 disparado diagnóstico (só leitura) do achado catraca→relógio. Não é passo do plano; se for interrompido, não precisa refazer.
- 18:33 diagnóstico catraca→relógio concluído (nada editado). Duas causas distintas, **ambas já conhecidas** como `xfail(strict=True)` em `tests/test_processador_divergencias_bateria_cenarios.py` ("Divergência A" e `test_pergunta_de_modelo_nao_se_repete_indefinidamente`):
  1. Texto do template `PEDIR_MODELO` (`services/respostas/catalogo.py:241-247`) é fixo de relógio, mas o campo modelo (`catalogo_campos.py:93-114`) vale para 10 produtos. O classificador acerta "catraca".
  2. Na conversa real (produto era mesmo relógio), a repetição: turno sem sinal de modelo não conta tentativa (`finalizando.py:338`, `_MODELO_MAX_TENTATIVAS` em `:56`/`:455`), então a mesma pergunta volta sem limite.
  Opções para o Beto: (1) template por produto, texto a ser escrito pela Kika; (2) relógio mantém o texto e os demais usam o genérico `PerguntaModelo.pergunta`, dá para fazer hoje; (3) contar reapresentações também sem sinal e, após N, mudar de ação (N e ação são decisão de produto). A 3 combina com a 1 ou a 2.
  Observação: os testes usam o mesmo banco `assistente_vendas` (não há banco de teste separado).
- 18:50 W concluído e commitado (`b23c4cb`), junto com a ligação do `ProfileName`. P commitado (`8a7939a`). Telefone real trocado por fictício em docstring, script, teste e docs (`59b21a4`); o histórico do git continua com ele. Suíte: 437 passando, 2 xfail.
  Decisões do W para o Beto revisar: a fixture de testes zera também as credenciais Twilio (teste que esqueça o mock cai no simulado); idempotência sem filtro de origem (SID é único); localização com `Body` preenchido também vira marcador (sem payload real desse caso); foto com legenda segue ao cérebro sem registrar a mídia; log de mensagem sem texto registra só o id; marcadores entre colchetes não foram conferidos no frontend.
  Não commitado de propósito: `artefatos/gerente_de_projetos/janelas/TextoLongo.md` (do Beto) e `.gitignore_beto`.
- 18:39 passos 4 (cenários, backend separado na 8001 sem LLM e canal simulado) e 5 (revisão, só leitura) disparados em paralelo. Relatórios em `artefatos/qa/2026-09-25_cenarios_testador.md` e `artefatos/qa/2026-09-25_revisao_branch_janela.md`. Se interrompidos: conferir se há backend órfão na 8001/8002 e worktree em /tmp/claude-1000/wt-develop antes de refazer.
- 18:45 revisão concluída. **A1-A3 (altas) eram brechas no download de mídia, ativas com a captura ligada e o webhook público**: path traversal pelo `MessageSid`, API Key enviada a qualquer host de `MediaUrl` (e SSRF), download disparado antes da assinatura. Corrigidas às 18:50 em `273b0bd`, junto com A4 (teste gravava `MODO_EXECUCAO` no banco compartilhado). 444 passando.
  Para o Beto decidir: A5 (origem do nome do perfil só por comparação; registrar de verdade exige migração), estender A4 ao `test_processador_modo_execucao.py` (preexistente, mesmo padrão), B1 (reentrega após timeout perde a resposta e o banco diz entregue), B3 (localização perde `Address`/`Label`), B4 (caracteres invisíveis passam na validação do nome), B5, B8 (`debug_log.py` tem `19991931176`, a um dígito do número real: é real?).
- 18:48 testador concluído: 16 cenários, 1 passou, 15 divergiram, **nenhuma regressão da branch** (bateria idêntica contra `develop`). Fora `saudacao_simples`, nenhum cenário tinha resposta aceita. Idempotência sem risco: o testador não manda `MessageSid`.
  Para o Beto: lista de aceitar/rejeitar no relatório; decisões de negócio (a Inforrel vende câmera? "facial" é sempre projeto complexo? duas cortesias seguidas escalarem é aceitável?). Bugs de produto achados: "45 funcionários" e enumeração "1) 2) 3)" viram quantidade (dispara projeto complexo); compatibilidade não vai para validação técnica ("funciona ou não?" vira reclamação e encerra); reclamação não detectada; "sou pessoa física" tratado como pedido de humano.
  Testador: `mensagem_vazia_ou_so_midia` inativo no banco (falta `importar --atualizar`); data de início das execuções congelada em 21/08 (default `"now()"` como texto em `models.py`); CNPJ "fictício" `11222333000181` é real (uma escola) e consulta a ReceitaWS a cada rodada; README diz `GROQ_API_KEY` mas a variável é `LLM_API_KEY`.
- 18:56 documentação commitada (`7c52b24`).
- 18:58 auditoria da exposição A1-A3: os 27 payloads capturados são legítimos (SID no formato, `MediaUrl` da Twilio, user-agent da Twilio, `AccountSid` válido) e nenhum arquivo foi gravado fora de `logs/midias_twilio/`. Não houve exploração.
- 19:00 lista consolidada de decisões escrita acima. **Leva desta janela concluída.**
- 22:10 retomada agendada disparou: todos os passos marcados, árvore limpa (só `TextoLongo.md` e `.gitignore_beto`, do Beto), nenhum trabalho parcial. Nenhuma decisão nova do Beto desde 19:00; nada a executar sem elas.
- 26/09 09:15 respostas do Beto registradas; decisões revisadas; frentes I1 a I4 abertas.
- 26/09 09:52 ideia da resposta de manutenção no `/webhook` registrada no I2; `scripts/claude_quota.py --csv` implementado e commitado; I1 disparado.
- 26/09 10:02 frente E aberta; E1 (especificação REQ-004.5B/5C) escrita.
- 26/09 10:12 [N] concluído e commitado (`f51ea13`). Bugs preexistentes achados pelo [N]: (1) **dígitos de CNPJ/CPF viram `quantidades`** ("11.222.333/0001-81" → [11, 222, 333, 1, 81]) e disparam projeto complexo antes da confirmação do CNPJ; (2) `_resolver_modelo` trata qualquer chave de `AtendimentoInfo` como atributo de modelo (`documento_fiscal_pendente` quebra "biometria" → "Não encontrei esse modelo").
- 26/09 10:13 [E] disparado para E2 (model, migração, registro, leitura e avaliação sem abertura de report). Pendentes do Beto: indevido abre `ReportProblema`? quem pode avaliar?
- 26/09 10:28 [E] concluído. Decisões a revisar: base insuficiente sem o melhor score abaixo do limiar (exigiria 2ª busca de embedding); sinais do modelo não reconhecido só da mensagem atual; handoff para orçamento (`FinalizandoState.concluir`) põe em HUMANO sem gerar `Escalonamento` (não é escalonamento pela especificação); desfazer avaliação limpa comentário/autor/data (sem histórico); projeto complexo grava as 3 condições sempre. Possível bug preexistente: `cpf_pendente` e outras chaves de `AtendimentoInfo` entram como filtro de catálogo.
