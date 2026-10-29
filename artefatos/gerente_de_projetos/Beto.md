# Beto: ponto de reentrada

<!-- CLASSIFICACAO: PROCESSO -->

Arquivo enxuto, **sem histórico**: só o estado atual, o que depende de mim e as ideias soltas. Item resolvido sai daqui (o histórico fica no git e nos arquivos de janela).
Detalhe de cada item: `janelas/2026-09-25_progresso.md`.

**Atualizado:** 12/10/2026

## Onde estamos

- Tudo em `develop` (sem branches, decisão de 27/09). Local à frente do `origin/develop`
- Twilio trial: colheita e reply-to feitos. **Modo de teste deslligado** (`CANAL_SAIDA=simulado`).
- **Sem commit, aguardando sua revisão (10-11/10, caso +5519987654321):** (1) nome do perfil do WhatsApp sem caracteres não alfabéticos ("~~Joaquim Barbosa~~" vira "Joaquim Barbosa"); (2) data de nascimento não é mais pedida nem gravada (coluna mantida, sem uso); (3) captura de CPF/CNPJ deixou de ser exclusiva: "Anotei seu CPF." e o resto da mensagem (dúvida, resposta) segue na mesma resposta; (4) no Finalizando, antes do resumo, uma pergunta sobre o documento da nota fiscal (confirma o dado no início ou pede); (5) dúvida que cai numa ação exclusiva (pedido de atendente etc.) vai para a tabela nova `duvidas_pendentes` e aparece na tela de acompanhamento com "Marcar como respondida"; (6) "pode me fornecer mais detalhes?" vira dúvida de produto e consulta a RAG pelo produto do atendimento; (7) dígitos de CPF/CNPJ formatados não viram mais quantidade nem resposta numérica. Migração `2026101101` aplicada no banco de dev; o backend do Docker precisa de rebuild. A `Pessoa` id 1 (nome lixo de junho) foi corrigida no banco de dev.
- **LLM fora do ar e aba Sistema (12/10, sem commit):** a Groq bloqueou a organização (`organization_restricted`); desde então tudo sai de regras e templates. Nova tabela `comparacoes_llm` (o que o sistema faria sem o LLM e o que ele devolveu, por mensagem, ligada à pergunta e à resposta) e nova aba **Sistema** (configurações do `.env` mascaradas, teste ao vivo do LLM, comparações). Correção junto: LLM com erro na classificação descartava o que as regras tinham achado (virava "desconhecido"); agora volta para as regras. Migração `2026101201` aplicada no banco de dev; o backend do Docker precisa de rebuild.
- **Container do backend isolado (I3, 02/10):** código só leitura, usuário `app`, e `logs/` no volume `backend_logs`. Logs, payloads e mídias do Docker não aparecem mais em `backend/logs/`: ler com `docker exec agenteassistentedevendas-backend-1 ...` (`docs/comandos_uteis.md`, "Logs do backend no Docker"). Commit a revisar: o do I3 (abaixo do `081d6c2`).
- **Chat simula o nome do perfil do WhatsApp (02/10):** campo "Nome do perfil (WhatsApp)" acima da digitação, só em memória, por telefone. Commit a revisar: `41864fe`. Para ver na porta 3000, rebuild do container `frontend`.
- **Nome inventado junto do documento (02/10):** "Sim, pode me chamar assim, meu cnpj é X" virava o nome "Sim Pode Me Chamar Assim Meu É" (e "Oi, quero um orçamento, cnpj X" virava "Oi Quero Um Orçamento"). Corrigido no classificador. Commit a revisar: `de546e4`.
- **Uma pergunta por mensagem (02/10):** resposta com várias perguntas sai em várias mensagens de WhatsApp, cada uma terminando numa pergunta e com aprovação própria. Commit a revisar: `587b426`. Falta testar no celular a ordem de chegada das mensagens (religar o modo de teste).
- **Pilha de perguntas pendentes (05/10):** os 3 passos do desenho de agosto implementados. Commits a revisar: `9b12060`, `3484cee`, `f79f0bf` (decisões embutidas no corpo de cada um). Migração nova (`perguntas_pendentes`), aplicada no banco de dev; o backend do Docker precisa de rebuild. Divergência do desenho para você avaliar: a clarificação da RAG ficou fora da pilha (motivo no commit `f79f0bf`). No celular: um "sim" solto após as 3 perguntas da saudação deve dar "Fiquei confuso...", e o "Responder" numa delas deve evitar isso.
- **Projeto complexo espera a coleta; CNPJ/CPF no início (05/10, caso +5519991931173):** commit a revisar `a592115`. Inclui correção de bug antigo: o modelo não resolvia quando a faixa era coletada antes (fluxo "vocês vendem X?"). As respostas aceitas do testador de conversas que começam por orçamento mudam (ganham o pedido de documento).
- **Skill `testar-backend` (08/10):** testador roda contra backend próprio na 8002 (sem LLM), o Claude julga e só **propõe** respostas aceitas. 7 cenários novos dos folders. Relatório: `artefatos/qa/2026-10-08_testar_backend.md`. Commits a revisar: `9b91116`, `cc1aaf9`, `86aba21`, `928dd20` (correções de conversa) e `5e54588` (skill, testador, cenários).
- **Versão:** cada lado tem `VERSAO` (data e hora da última mudança), exibida no rodapé como "Front X · Back Y". Antes de commitar: `python scripts/versao.py atualizar`; o
  pre-commit bloqueia se esquecer.
- Frontend do Docker (porta 3000) serve build antigo: para ver as telas novas, `npm run dev` ou rebuild do container `frontend`.

## Decidir ou fazer (em ordem)

OK - **Revisar os commits da janela de 25-27/09** (já no remoto). `git log --oneline 612fe4d..047696b`. Comece por `273b0bd` (segurança do download de mídia), `f51ea13` (confirmação do nome) e `2f76496` (tabela de escalonamentos).
OK - **Push dos 3 commits locais de 01/10:** `b503f63` (versão por lado), `b7ea758` (lint do seu `ae47499`) e `081d6c2` (este arquivo). Revisar antes; `develop` está 3 à frente do `origin/develop`.
OK - **Ver a versão no rodapé:** às 10:43 o backend do Docker ainda respondia `0.1.0` (o `docker.exe` falhou por falta de memória no Windows e não deu para conferir o container). Reiniciar o container `backend` e reconstruir o `frontend`; o esperado é "Front 2026.10.01-1043 · Back 2026.10.01-1046".
OK - **Celular, ~25 min:** latência, rajada, reply-to fora de ordem, citar a própria mensagem, figurinha, pedido de humano. Lista no topo de `janelas/2026-09-23_plano_twilio_4_dias.md`. O modo de teste agora está desligado: religar com `./scripts/twilio_modo_teste.sh ligar` e desligar ao terminar. **Antes, conferir se a conta trial ainda existe** (o plano previa que ela expirasse por volta de 26/09); se expirou, este item sai e o que sobrou fica para o número próprio (chip pré-pago).

- **Correções de produto (I4): feitas em 08/10** (tomei o pedido de hoje, "corrigir o que não precisar de decisão", como o sim). Revisar `9b91116`, `cc1aaf9`, `86aba21`, `928dd20`; se discordar de alguma, reverto. Dígitos de CNPJ virando quantidade: corrigido em 11/10 (ainda sem commit).
- **Aprovar as 27 respostas propostas** pelo Claude: `cd testador_conversas && python cli.py propostas-listar`, depois `propostas-aprovar <ids> --por beto` (ou `--por kika`).
- **Cortesia depois do pedido de documento:** hoje retoma a pergunta ("Voltando à minha pergunta: ...CNPJ..."); o cenário de 25/09 diz para não repedir. Manter, ou só responder à cortesia (texto novo)?
- **Testar a base de conhecimento exige LLM:** sem ele, os cenários dos folders param no classificador. Backend de teste com LLM e o Claude como juiz semântico, ampliar palavras-chave, ou deixar para depois? (opções no relatório de 08/10)
- **Revisar e commitar a entrega de 10-11/10** (item "Sem commit" acima). Depois, no testador, o cenário `cpf_pessoa_fisica_e_data_nascimento` precisa de respostas novas (não há mais pergunta de data) e os de orçamento ganham a pergunta da nota fiscal antes do resumo.
- **Escolher o LLM (12/10):** provedor genérico compatível com a OpenAI pronto (sem commit): Cloudflare, Ollama, OpenRouter, Gemini e OpenAI só pelo `.env` (tabela em `docs/comandos_uteis.md`). Falta: (1) contestar o bloqueio da Groq pelo "Questions?" do console, depois de trocar a chave; (2) criar a conta grátis da Cloudflare (Workers AI) e preencher `LLM_PROVIDER=cloudflare`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`; conferir na aba Sistema. Gemini grátis usa os dados para treino: só com conversa fictícia.
- **Catraca (e bastão de ronda) recebe pergunta de relógio:** o `PEDIR_MODELO` é fixo "O relógio seria cartográfico ou eletrônico?" para qualquer produto; apareceu no orçamento de bastão de ronda de 10/10. Opção 1 (texto por produto, Kika), 2 (genérico para os outros) ou 3 (limitar repetição). Sugestão: 2 agora, 3 com N=2.
- **Negócio:** a Inforrel vende câmera? Leitor facial é sempre projeto complexo? (se for "só controle de acesso", patch pronto em `artefatos/qa/2026-10-08_patches_propostos/`) Duas cortesias seguidas devem escalar?
- **Testador:** aceitar/rejeitar as respostas (`artefatos/qa/2026-09-25_cenarios_testador.md`) e autorizar os três ajustes (reimportar cenário, default `now()`, CNPJ fictício real).
- **Escalonamento indevido no takeover manual não abre report** (não há mensagem para ligar; a regra do banco exige uma). Concorda, ou afrouxar a regra?
- **Testar no navegador:** bloco "Por que escalou", avaliação, "Salvar comentário", link para o report (no Chat abre janela sobre janela).
- **Dois comportamentos da tela achados na revisão das ajudas:** o modal da Base Q&A diz que o embedding é refeito "na próxima aprovação", mas é refeito ao salvar; editar `modo_execucao` em Parâmetros pula a confirmação do REQ-011.18. Corrigir?
- **Revisar decisões embutidas nos commits** (listadas no corpo de cada commit e no progresso): nome do perfil, escalonamentos, fixtures.

## Baixa prioridade:
- **Página de manutenção no deploy (I2):** aprovar o formato (script com bandeira + aviso TwiML no `/webhook`).

## Depois que contratar o Twilio pago:
- **Recuperar mensagens perdidas no startup:** ao subir, listar na Twilio as mensagens recebidas depois da última que tratamos e processar as que faltam (a idempotência por `MessageSid` já impede duplicar). Limites na trial: dá para listar, mas não para responder fora do webhook (REST bloqueado no Sandbox) nem listar mídia.
- Registrar a origem do nome do perfil de forma durável (hoje em `AtendimentoInfo`).
- Estender o dublê de `ModoExecucao` ao `test_processador_modo_execucao.py`.
- O check de ajuda (`scripts/ajuda_fingerprint.py`) deixa de fora texto seguido de `{...}` com `>`, entidades `&quot;`, rótulos passados como prop e mapas JS. Melhorar o script?
