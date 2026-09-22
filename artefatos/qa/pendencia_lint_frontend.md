# Pendência — `npm run lint` não funciona (falta config do ESLint)

<!-- CLASSIFICACAO: ANDAMENTO -->

> **Agente:** [qa]
> **Data:** 2026-09-22
> **Contexto:** Descoberto ao verificar a entrega da ajuda contextual das telas
> (`frontend/src/ajuda/`). A condição é **pré-existente** e não foi causada por aquela
> mudança; optou-se por registrar aqui em vez de corrigir no mesmo PR, para não misturar
> escopos.

---

## Situação

O script existe em `frontend/package.json`:

```json
"lint": "eslint . --ext js,jsx --report-unused-disable-directives --max-warnings 0"
```

Mas não há arquivo de configuração do ESLint no projeto. O comando aborta:

```
Oops! Something went wrong! :(
ESLint: 8.57.1
ESLint couldn't find a configuration file.
```

**O arquivo nunca existiu no histórico do repositório** — confirmado com
`git log --all -- "frontend/.eslintrc*" "frontend/eslint.config*"` (nenhum resultado).
Ou seja, não é regressão: o lint do frontend nunca rodou.

## O que já está pronto

As dependências estão todas instaladas em `frontend/package.json` (devDependencies):

| Pacote | Versão | Para que serve |
|--------|--------|----------------|
| `eslint` | ^8.56.0 | o linter |
| `eslint-plugin-react` | ^7.33.2 | regras de JSX/React |
| `eslint-plugin-react-hooks` | ^4.6.0 | regras de hooks (o mais valioso aqui) |
| `eslint-plugin-react-refresh` | ^0.4.5 | HMR do Vite |

Falta apenas o arquivo de configuração amarrando tudo.

## Por que vale corrigir

O ganho concreto está no `eslint-plugin-react-hooks`, que detecta a classe de bug mais
comum neste frontend: `useEffect` com array de dependências incompleto (tela que não
atualiza quando deveria) e hooks chamados condicionalmente. Também pegaria imports e
variáveis não usados, que hoje passam batido.

Como o backend já tem `ruff` no pre-commit e QA checks automatizados, o frontend é o
único lado sem verificação estática — assimetria de qualidade entre as duas metades do
projeto.

## Cuidado ao executar

O script usa `--max-warnings 0`, ou seja **qualquer aviso derruba o comando**. Ao criar
a configuração, o ESLint vai varrer de uma vez todo o código acumulado; é esperado um
volume alto de apontamentos. Por isso a tarefa não é "criar um arquivo", é
"criar o arquivo + decidir o que fazer com o passivo".

## Caminho sugerido

1. **Diagnóstico primeiro (sem corrigir nada)** — criar `frontend/.eslintrc.cjs` com o
   preset padrão de React + Vite e rodar `npx eslint . --ext js,jsx` (sem
   `--max-warnings 0`) só para **medir** o tamanho do passivo.
2. **Decidir a estratégia** conforme o número encontrado:
   - poucos apontamentos → corrigir tudo e manter `--max-warnings 0`;
   - muitos → começar com as regras de `react-hooks` como `error` e o resto como `warn`,
     afrouxando o `--max-warnings` temporariamente, e apertar aos poucos.
3. **Corrigir** o que for real (atenção especial às dependências de `useEffect` — algumas
   podem estar "erradas de propósito"; nesses casos, documentar com
   `// eslint-disable-next-line` e um comentário explicando o porquê).
4. **Integrar** ao fluxo, alinhado ao que já existe no backend: incluir o lint do frontend
   no `scripts/qa_check.py` ou como hook no `.pre-commit-config.yaml` (hoje o pre-commit
   só roda checks Python — ver `qa-check` e `sync-skill-windsurf`).

## Observação adicional encontrada no caminho

Possível bug pré-existente, não relacionado ao lint, anotado aqui para não se perder:
em `frontend/src/App.jsx`, `carregarTelefones` preenche `telefones` com **objetos**
(`{telefone, ultima_mensagem_em}`, como `PhonePanel` espera ao desestruturar), mas
`selecionarTelefone` faz `telefones.includes(telefone)` e insere uma **string** na lista.
A comparação nunca casa e o item inserido não tem o formato esperado pelo `PhonePanel`.
Vale confirmar em tela antes de abrir como bug.
