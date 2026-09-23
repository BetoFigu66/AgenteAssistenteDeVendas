# Pendência — sync de skills ficou órfão após a migração para `.devin/`

<!-- CLASSIFICACAO: ANDAMENTO -->

> **Agente:** [ia_expert]
> **Data:** 2026-09-22
> **Contexto:** Descoberto ao adicionar uma linha ao skill `revisao-codigo` (mecanismo de
> ajuda contextual das telas). A edição foi feita no local real (`.devin/skills/`), mas o
> resto do mecanismo de espelhamento ficou apontando para um caminho que não existe mais.
> Não foi corrigido na hora porque a correção depende de uma decisão (ver abaixo).

---

## Situação

O skill `revisao-codigo` vive hoje em `.devin/skills/revisao-codigo/` — é o que o
`git ls-files` confirma como rastreado:

```
.devin/skills/revisao-codigo/SKILL.md
.devin/skills/revisao-codigo/diretrizes.md
```

E `.claude/` não está mais no índice do git. Mas três peças continuam referenciando o
caminho antigo:

| Peça | Estado |
|------|--------|
| `scripts/sync_skill_windsurf.py` | `FONTE = ROOT / ".claude" / "skills"` — diretório inexistente; o script não tem o que copiar |
| `.pre-commit-config.yaml`, hook `sync-skill-windsurf` | `files: ^\.claude/skills/` — o filtro nunca casa, o hook nunca dispara |
| `.devin/skills/revisao-codigo/SKILL.md` (corpo do texto) | Afirma "**Edite só aqui** (`.claude/skills/revisao-codigo/`)" e descreve o espelhamento para `.windsurf/skills/` |
| `.windsurf/skills/` | Não existe mais |

Ou seja: o espelhamento está **silenciosamente inativo**. Nada falha, nada avisa — só
não acontece.

## Por que não foi corrigido direto

Há duas saídas possíveis, e a escolha não é técnica:

1. **O espelhamento ainda é necessário** → reapontar `FONTE` para `.devin/skills`, ajustar
   o `files:` do hook para `^\.devin/skills/` e corrigir o texto do `SKILL.md`.
2. **O espelhamento não é mais necessário** → o Devin Desktop/Windsurf descobre skills em
   `.devin/skills/` direto, o que tornaria `.windsurf/skills/` redundante. Nesse caso o
   certo é **remover** `scripts/sync_skill_windsurf.py`, `scripts/sync_skill_windsurf.sh`
   e o hook, em vez de reapontá-los.

A opção 2 parece a mais provável (foi justamente por isso que a migração para `.devin/`
aconteceu), mas confirmar isso é decisão do Beto — envolve saber se alguma ferramenta no
fluxo da Kika ainda lê `.windsurf/skills/`.

## O risco concreto de deixar como está

O `SKILL.md` instrui a editar num diretório que não existe. A próxima pessoa que for
alterar o skill — ou o próprio agente, seguindo a instrução — vai procurar
`.claude/skills/`, não achar, e potencialmente **recriar o diretório**, restaurando a
duplicação que a migração eliminou.

## Sugestão de ordem

1. Confirmar se algo ainda consome `.windsurf/skills/`.
2. Aplicar a opção 1 ou 2.
3. Em qualquer dos casos, corrigir o parágrafo do `SKILL.md` que fala do espelhamento —
   é o que induz ao erro.
4. Conferir se `docs/comandos_uteis.md` (seção "Skill de code review — sincronização com
   Windsurf") também precisa de ajuste; ela descreve o fluxo antigo.

## Referências

- `scripts/sync_skill_windsurf.py` → `FONTE` / `DESTINO`
- `.pre-commit-config.yaml` → hook `sync-skill-windsurf`
- `.devin/skills/revisao-codigo/SKILL.md` → parágrafo "Este é o arquivo-fonte."
- `docs/comandos_uteis.md` → "Skill de code review — sincronização com Windsurf"
