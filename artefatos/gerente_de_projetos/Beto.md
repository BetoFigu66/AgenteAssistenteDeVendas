# Beto: ponto de reentrada

<!-- CLASSIFICACAO: PROCESSO -->

Arquivo enxuto, **sem histórico**: só o estado atual, o que depende de mim e as ideias soltas. Item resolvido sai daqui (o histórico fica no git e nos arquivos de janela).
Detalhe de cada item: `janelas/2026-09-25_progresso.md`.

**Atualizado:** 02/10/2026 08:50

## Onde estamos

- Tudo em `develop` (sem branches, decisão de 27/09). Local à frente do `origin/develop`
- Twilio trial: colheita e reply-to feitos. **Modo de teste deslligado** (`CANAL_SAIDA=simulado`).
- Nada em andamento com o Claude.
- **Container do backend isolado (I3, 02/10):** código só leitura, usuário `app`, e `logs/` no volume `backend_logs`. Logs, payloads e mídias do Docker não aparecem mais em `backend/logs/`: ler com `docker exec agenteassistentedevendas-backend-1 ...` (`docs/comandos_uteis.md`, "Logs do backend no Docker"). Commit a revisar: o do I3 (abaixo do `081d6c2`).
- **Versão:** cada lado tem `VERSAO` (data e hora da última mudança), exibida no rodapé como "Front X · Back Y". Antes de commitar: `python scripts/versao.py atualizar`; o
  pre-commit bloqueia se esquecer.
- Frontend do Docker (porta 3000) serve build antigo: para ver as telas novas, `npm run dev` ou rebuild do container `frontend`.

## Decidir ou fazer (em ordem)

OK - 1. **Revisar os commits da janela de 25-27/09** (já no remoto). `git log --oneline 612fe4d..047696b`. Comece por `273b0bd` (segurança do download de mídia), `f51ea13` (confirmação do nome) e `2f76496` (tabela de escalonamentos).
OK - 2. **Push dos 3 commits locais de 01/10:** `b503f63` (versão por lado), `b7ea758` (lint do seu `ae47499`) e `081d6c2` (este arquivo). Revisar antes; `develop` está 3 à frente do `origin/develop`.
OK - 3. **Ver a versão no rodapé:** às 10:43 o backend do Docker ainda respondia `0.1.0` (o `docker.exe` falhou por falta de memória no Windows e não deu para conferir o container). Reiniciar o container `backend` e reconstruir o `frontend`; o esperado é "Front 2026.10.01-1043 · Back 2026.10.01-1046".
OK - 4. **Celular, ~25 min:** latência, rajada, reply-to fora de ordem, citar a própria mensagem, figurinha, pedido de humano. Lista no topo de `janelas/2026-09-23_plano_twilio_4_dias.md`. O modo de teste agora está desligado: religar com `./scripts/twilio_modo_teste.sh ligar` e desligar ao terminar. **Antes, conferir se a conta trial ainda existe** (o plano previa que ela expirasse por volta de 26/09); se expirou, este item sai e o que sobrou fica para o número próprio (chip pré-pago).

7. **Correções de produto (I4), sim/não:** compatibilidade não vai para validação técnica; reclamação não detectada; "45 funcionários", "1) 2) 3)" e dígitos de CNPJ viram quantidade; "sou pessoa física" vira pedido de humano.
8. **Catraca recebe pergunta de relógio:** opção 1 (texto por produto, Kika), 2 (genérico para os outros) ou 3 (limitar repetição). Sugestão: 2 agora, 3 com N=2.
9. **Negócio:** a Inforrel vende câmera? Leitor facial é sempre projeto complexo? Duas cortesias seguidas devem escalar?
10. **Testador:** aceitar/rejeitar as respostas (`artefatos/qa/2026-09-25_cenarios_testador.md`) e autorizar os três ajustes (reimportar cenário, default `now()`, CNPJ fictício real).
11. **Escalonamento indevido no takeover manual não abre report** (não há mensagem para ligar; a regra do banco exige uma). Concorda, ou afrouxar a regra?
12. **Testar no navegador:** bloco "Por que escalou", avaliação, "Salvar comentário", link para o report (no Chat abre janela sobre janela).
13. **Dois comportamentos da tela achados na revisão das ajudas:** o modal da Base Q&A diz que o embedding é refeito "na próxima aprovação", mas é refeito ao salvar; editar `modo_execucao` em Parâmetros pula a confirmação do REQ-011.18. Corrigir?
14. **Revisar decisões embutidas nos commits** (listadas no corpo de cada commit e no progresso): nome do perfil, escalonamentos, fixtures.

## Baixa prioridade:
5. **Página de manutenção no deploy (I2):** aprovar o formato (script com bandeira + aviso TwiML no `/webhook`).

## Depois que contratar o Twilio pago:
- **Recuperar mensagens perdidas no startup:** ao subir, listar na Twilio as mensagens recebidas depois da última que tratamos e processar as que faltam (a idempotência por `MessageSid` já impede duplicar). Limites na trial: dá para listar, mas não para responder fora do webhook (REST bloqueado no Sandbox) nem listar mídia.
- Registrar a origem do nome do perfil de forma durável (hoje em `AtendimentoInfo`).
- Estender o dublê de `ModoExecucao` ao `test_processador_modo_execucao.py`.
- O check de ajuda (`scripts/ajuda_fingerprint.py`) deixa de fora texto seguido de `{...}` com `>`, entidades `&quot;`, rótulos passados como prop e mapas JS. Melhorar o script?
