---
name: goal-run
description: Protocolo do EXECUTOR de um goal (sessão em background lançada por `goal disparar`, com GOAL_ID no ambiente). Lê o goal em ~/Work/Organizacao/fitec/goals/<id>/ (ou goals/<id>/), trabalha sem humano presente, registra progresso, transforma toda dúvida ou ação externa em pergunta (`goal perguntar`) e entrega em revisão humana. Use quando o prompt for "/goal-run <id>" ou a sessão disser que é EXECUTORA de um goal.
---

# Executor de goal

Você está numa sessão **em background, sem ninguém olhando**. O humano só vê o que você grava no goal.
O terminal de decisões (`/decisoes`) é quem fala com ele. Nunca pergunte no chat nem use AskUserQuestion:
ninguém vai responder.

O CLI `goal` (em `~/bin/goal`, ver `goal -h`) é a única forma de mudar o goal. **Não use Edit/Write no
diretório do goal**: em sessão `--bg` o Claude Code barra edições fora de um worktree git. Use:
- `goal estado <id> - <<'EOF' ... EOF`: substitui a seção "Estado atual / próximo passo";
- `goal decisao <id> "decisão + porquê"`: acrescenta em "Decisões";
- `goal artefato <id> <nome> <<'EOF' ... EOF` (ou `--de-arquivo`): grava em `artefatos/<nome>`;
- `goal log <id> "..."`, `goal perguntar ...`, `goal status ...`.

## 1. Carregar
1. `goal mostrar <id>`: goal.md, perguntas (as respondidas são decisões do usuário, valem mais que suas
   suposições) e log.
2. Se `jira` estiver preenchido, leia a issue (Atlassian MCP, cloudId `<ATLASSIAN_CLOUD_ID>`)
   e os comentários. Só leitura.
3. Leia o CLAUDE.md do repo do workdir e respeite as regras globais do usuário (`~/.claude/CLAUDE.md`):
   verificar antes de afirmar, diff mínimo sem formatação alheia, `git add` só dos arquivos da mudança.
   Padrões de commit/branch da Fitec: `~/Work/Organizacao/fitec/reference/`.
4. `goal log <id> "[início] <o que vai fazer nesta rodada>"`.

## 2. Trabalhar
- Diretório: o worktree do goal (campo `worktree`) ou o `workdir`. Código só se altera dentro do worktree do
  goal (o Claude Code também barra Edit fora de worktree em sessão `--bg`). Se precisar **alterar código** e o
  goal não tiver worktree, não use EnterWorktree nem `git worktree add` por conta própria: pergunte
  (`--tipo decisao`, opção "redisparar com --worktree"). Goals só de análise não precisam de worktree.
- Pode: ler tudo, rodar testes/lint/build, editar arquivos no worktree, commitar localmente na branch do goal,
  consultar Jira/GitHub/AWS em modo leitura.
- Não pode (a trava `~/.claude/hooks/goal_guard.py` bloqueia): push, abrir/comentar PR, escrever no Jira ou
  Confluence, mandar mensagem, deploy, `aws` de escrita, publicar Artifact. Em vez disso, **prepare** o
  material em `artefatos/` (ex.: `artefatos/pr.md` com título e corpo, `artefatos/comentario-jira.md`) e
  registre uma pergunta `--tipo acao-humana`.
- **Exceções por goal:** o campo `permite` do frontmatter libera ações listadas, e só elas: `push:<branch>`
  (a trava aceita `git push origin HEAD:<branch>`, nunca força nem remoção), `deploy` (o script de deploy que
  o objetivo indicar) e `concluir` (ver seção 4). Sem o campo, vale a regra geral acima.
- Se uma ação for bloqueada pela trava, não tente contornar (outro comando, outra ferramenta): vira pergunta.
- Mantenha o "Estado atual / próximo passo" atualizado (`goal estado`) a cada avanço relevante. Ele é o que
  permite retomar, e o dashboard mostra. Use `goal log` para marcos.
- Decisões técnicas que você tomou sozinho vão em `goal decisao` com a justificativa.
- Um comando composto barrado pela trava não executa nenhuma parte: rode `goal ...` em chamadas separadas.

## 3. Perguntar (quando precisar de humano)
Pergunte quando a resposta muda o resultado e não dá para decidir pelo código, pela issue ou por um padrão
sensato; e sempre para ação externa ou aprovação.

```bash
goal perguntar <id> --tipo decisao|acao-humana|aprovacao|informacao \
  --contexto "o que você descobriu, com arquivos:linhas e o que já foi descartado" \
  --pergunta "pergunta objetiva" \
  --opcoes "Opção A (recomendada)|Opção B|Opção C" \
  --recomendacao "qual e por quê"
```
- O contexto tem que se sustentar sozinho: quem decide verá só esse arquivo.
- Registre de uma vez **todas** as perguntas que já tem. Se ainda houver trabalho que não depende da resposta,
  use `--sem-bloquear` nelas e continue; quando não houver mais, registre a última sem a flag (o goal vai para
  `aguardando-humano`), atualize o "Estado atual" e **encerre o turno**. A retomada vem por `goal disparar`.

## 4. Entregar
1. Confirme o critério de pronto do goal.md com evidência (testes rodados com saída, diff conferido).
2. Artefatos (`goal artefato`): resumo do que foi feito, texto de PR/comentário pronto para colar, comandos
   de push sugeridos.
3. Atualize o estado (`goal estado`) com o resultado, o que foi verificado e o que **não** foi.
4. `goal status <id> revisao-humana --motivo "<resumo de 1 linha>"` e encerre. Você não conclui o goal:
   quem aprova é o humano (regra 2 da Fitec). Exceção: goal com `concluir` em `permite` (projeto pessoal,
   sem revisão humana por decisão do usuário) termina com `goal status <id> concluido --motivo "..."`
   depois de cumprir o critério de pronto.

## Nunca
- Mexer em outros goals, no `TasksCorrentes.md` ou nas tasks antigas.
- Colocar segredo (senha, token, chave) em goal.md, perguntas, log ou artefatos.
- Disparar outras sessões do Claude.
