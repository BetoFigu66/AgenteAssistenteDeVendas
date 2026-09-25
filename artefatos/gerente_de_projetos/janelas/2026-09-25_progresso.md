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

## ⏩ Beto: decisões pendentes (consolidado às 19:00)

Em ordem do que destrava mais trabalho. Entre parênteses, a minha recomendação.

**A. Para fechar a branch**
1. Revisar e fazer o merge de `janela/2026-09-25` em `develop` (9 commits). Os mais
   sensíveis para revisar: `273b0bd` (segurança do download) e `8a7939a` (nome de perfil,
   mexe no fluxo de conversa).
2. Decisões embutidas nos commits, para confirmar ou reverter:
   - nome digitado depois substitui o do perfil; perfil nunca vai para `Pessoa.nome`;
     emoji junto de letras é mantido (P);
   - a fixture de testes zera também as credenciais Twilio; localização com `Body`
     preenchido também vira marcador (W).

**B. Produto (destravam correções que posso fazer em seguida)**
3. **Catraca recebe a pergunta de relógio.** Opções: (1) template por produto, texto da
   Kika; (2) relógio mantém o texto e os demais usam o genérico `PerguntaModelo.pergunta`;
   (3) limitar a repetição da mesma pergunta (N e ação a definir). (2 hoje, 3 com N=2 e
   reformular; 1 quando a Kika puder.)
4. **Compatibilidade não vai para validação técnica** (viola regra de negócio do
   CLAUDE.md): "funciona ou não funciona?" vira reclamação e encerra o atendimento.
   (Corrigir; é regra já decidida, falta só autorizar mexer no classificador.)
5. **Reclamação não é detectada** nas duas mensagens do cenário. (Corrigir junto com o 4.)
6. **"45 funcionários" e "1) 2) 3)" viram quantidade de equipamento** e disparam projeto
   complexo. (Corrigir.)
7. **"sou pessoa física" é lido como pedido de humano.** (Corrigir.)
8. Três perguntas de negócio: a Inforrel vende câmera (o template diz "Sim, Intelbras")?
   Leitor facial é sempre projeto complexo? Duas cortesias seguidas devem escalar?

**C. Testador**
9. Aceitar/rejeitar as respostas: lista em `artefatos/qa/2026-09-25_cenarios_testador.md`.
10. Reimportar `mensagem_vazia_ou_so_midia` (`importar --atualizar`); corrigir o default
    `"now()"` em `testador_conversas/models.py` (exige `ALTER` no schema `teste_conversas`,
    que não tem Alembic); trocar o CNPJ "fictício" `11222333000181`, que é de uma escola
    real e consulta a ReceitaWS a cada rodada. (Sim para os três.)

**D. Revisão (baixa severidade)**
11. A5, origem do nome do perfil registrada de verdade (migração) ou comparação atual.
    (Comparação atual até existir a regra definitiva de nome.)
12. Estender o dublê de `ModoExecucao` ao `test_processador_modo_execucao.py`. (Sim.)
13. B1: reentrega após timeout perde a resposta e o banco diz "entregue". (Anotar para o
    piloto com número próprio; na trial não dá para provocar.)
14. B4: caracteres invisíveis passam na validação do nome. (Entra na regra definitiva.)
15. B8: `debug_log.py` tem `19991931176`, a um dígito do seu número. É real? (Trocar.)

**E. WhatsApp (amanhã, ~25 min seus):** a lista do topo do plano de 23/09 (latência,
rajada, reply-to fora de ordem, citar a própria mensagem, figurinha, pedido de humano).
Ao terminar, `./scripts/twilio_modo_teste.sh desligar`.

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
