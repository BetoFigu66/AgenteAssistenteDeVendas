# Beto: ponto de reentrada

<!-- CLASSIFICACAO: PROCESSO -->

Arquivo enxuto, **sem histórico**: só o estado atual, o que depende de mim e as ideias
soltas. Item resolvido sai daqui (o histórico fica no git e nos arquivos de janela).
Detalhe de cada item: `janelas/2026-09-25_progresso.md`.

**Atualizado:** 27/09/2026 08:00

## Onde estamos

- Branch `janela/2026-09-25`: 16 commits, **sem push, sem merge**. Tudo verde (suíte
  backend, ruff, lint e build do frontend).
- Twilio trial: colheita e reply-to feitos. **Modo de teste ainda ligado**
  (`CANAL_SAIDA=twilio`).
- Em andamento com o Claude: revisão de todos os textos de ajuda das telas.
- Frontend do Docker (porta 3000) serve build antigo: para ver as telas novas, `npm run dev`
  ou rebuild do container `frontend`. Nada foi testado no navegador ainda.

## Decidir ou fazer (em ordem)

1. **Revisar e fazer o merge da branch.** Comece por `273b0bd` (segurança do download de
   mídia), `f51ea13` (confirmação do nome) e `2f76496` (tabela de escalonamentos).
2. **Celular, ~25 min:** latência, rajada, reply-to fora de ordem, citar a própria
   mensagem, figurinha, pedido de humano. Lista no topo de
   `janelas/2026-09-23_plano_twilio_4_dias.md`. **Ao terminar:**
   `./scripts/twilio_modo_teste.sh desligar`.
3. **Página de manutenção no deploy (I2):** aprovar o formato (script com bandeira + aviso
   TwiML no `/webhook`).
4. **Isolar o container (I3):** aprovar código `:ro` + `logs/` em volume + usuário
   não-root.
5. **Correções de produto (I4), sim/não:** compatibilidade não vai para validação técnica;
   reclamação não detectada; "45 funcionários", "1) 2) 3)" e dígitos de CNPJ viram
   quantidade; "sou pessoa física" vira pedido de humano.
6. **Catraca recebe pergunta de relógio:** opção 1 (texto por produto, Kika), 2 (genérico
   para os outros) ou 3 (limitar repetição). Sugestão: 2 agora, 3 com N=2.
7. **Negócio:** a Inforrel vende câmera? Leitor facial é sempre projeto complexo? Duas
   cortesias seguidas devem escalar?
8. **Testador:** aceitar/rejeitar as respostas (`artefatos/qa/2026-09-25_cenarios_testador.md`)
   e autorizar os três ajustes (reimportar cenário, default `now()`, CNPJ fictício real).
9. **Escalonamento indevido no takeover manual não abre report** (não há mensagem para
   ligar; a regra do banco exige uma). Concorda, ou afrouxar a regra?
10. **Testar no navegador:** bloco "Por que escalou", avaliação, "Salvar comentário",
    link para o report (no Chat abre janela sobre janela).
11. **Revisar decisões embutidas nos commits** (listadas no corpo de cada commit e no
   progresso): nome do perfil, escalonamentos, fixtures.

## Ideias (ainda não viraram tarefa)

- **Recuperar mensagens perdidas no startup:** ao subir, listar na Twilio as mensagens
  recebidas depois da última que tratamos e processar as que faltam (a idempotência por
  `MessageSid` já impede duplicar). Limites na trial: dá para listar, mas não para
  responder fora do webhook (REST bloqueado no Sandbox) nem listar mídia.
- Registrar a origem do nome do perfil de forma durável (hoje em `AtendimentoInfo`).
- Estender o dublê de `ModoExecucao` ao `test_processador_modo_execucao.py`.
- `debug_log.py` tem `19991931176`, a um dígito do meu número: trocar.
