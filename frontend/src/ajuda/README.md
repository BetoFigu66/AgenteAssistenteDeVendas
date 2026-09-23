# Textos de ajuda por tela

Conteúdo exibido pelo botão **?** (`src/components/BotaoAjuda.jsx`) ao lado do título
de cada tela do painel. Substitui a necessidade de um manual do usuário separado.

## Como adicionar ajuda a uma tela

1. Crie `<contexto>.md` neste diretório (ex.: `orcamentos.md`).
2. Monte o botão na tela, ao lado do título:

```jsx
import BotaoAjuda from './BotaoAjuda'

<h2 className="...">Orçamentos</h2>
<BotaoAjuda contexto="orcamentos" />
```

Não é preciso registrar o arquivo em lugar nenhum: o `index.js` carrega todos os `.md`
deste diretório automaticamente (`import.meta.glob` do Vite).

Em fundo escuro, sobrescreva as cores do ícone:

```jsx
<BotaoAjuda contexto="chat" className="text-white/70 hover:text-white transition" />
```

## Fallback hierárquico

O contexto usa pontos para indicar especificidade crescente. `reports.detalhe` procura,
nesta ordem: `reports.detalhe.md` → `reports.md` → `geral.md`.

Isso permite criar ajuda específica de uma subárea sem duplicar o texto da tela inteira.
Se nenhum arquivo existir, o botão simplesmente não é renderizado.

## Arquivos atuais

| Arquivo | Tela |
|---|---|
| `geral.md` | Fallback — visão geral do painel |
| `chat.md` | Chat (simulador de atendimento) |
| `acompanhamento.md` | Acompanhamento de Atendimentos |
| `reports.md` | Triagem de Reports |
| `qa-base.md` | Base Q&A |
| `parametros.md` | Parâmetros |

## Como escrever

- Português, tom direto, foco em **o que o usuário faz** — não em como o código funciona.
- Use os mesmos nomes de botões e rótulos que aparecem na interface.
- Estrutura sugerida: o que é a tela → principais elementos → como fazer as ações
  comuns → observações e pegadinhas.
- Markdown suportado: títulos, listas, negrito, tabelas e links. HTML bruto é ignorado
  por segurança.

## Manutenção

Estes textos envelhecem junto com a interface. **Ao alterar uma tela de forma visível
para o usuário, revise o `.md` correspondente no mesmo PR.**

Existe um mecanismo de detecção para isso. O arquivo `_fontes.json` mapeia cada tela aos
componentes que ela descreve e guarda uma impressão digital das strings que o usuário vê
(texto JSX, `title`, `placeholder`, `aria-label`). Quando essa assinatura muda, o aviso
aparece:

```bash
python scripts/ajuda_fingerprint.py              # verifica
python scripts/ajuda_fingerprint.py --atualizar  # registra que revisou
```

Roda também como check `ajuda-telas-desatualizada` do QA Engineer (severidade
`warning` — não bloqueia commit).

Ao ver o aviso, decida:

- **o texto ficou errado** → corrija o `.md` e rode `--atualizar`;
- **o texto continua correto** → rode só `--atualizar` (reconhecimento explícito).

Renomear uma variável ou reorganizar a lógica não dispara nada — só mudança no texto
que o usuário lê. Ao criar um `.md` novo, adicione a tela em `_fontes.json` com
`"hash": ""` e rode `--atualizar`.
