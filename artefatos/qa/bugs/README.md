# Bugs encontrados durante os testes manuais

Cada arquivo neste diretório representa **um bug** encontrado durante a execução de um cenário de teste.

## Convenção de nome

`<CENARIO_ID>-<seq>.md`

- `<CENARIO_ID>` — ID do cenário que falhou (ex.: `CTF-011-04`).
- `<seq>` — número sequencial de dois dígitos, único por cenário. O primeiro bug do cenário é `01`, o segundo `02`, e assim por diante.

Exemplos:

```
CTF-011-04-01.md   # primeiro bug encontrado em CTF-011-04
CTF-011-04-02.md   # segundo bug encontrado no mesmo cenário
CTF-003-02-01.md   # primeiro bug em outro cenário
```

## Como criar

Os arquivos são criados automaticamente pelo **QA Runner** (`artefatos/qa/runner/index.html`) sempre que você marca um cenário como `FAIL` e preenche o modal de bug. As imagens coladas (Ctrl+V) ficam embedadas em base64 no próprio `.md`.

Não há nada para criar manualmente aqui.

## Estrutura de cada arquivo

- Cabeçalho com `Cenário`, `Cobre`, `Severidade`, data, navegador
- Descrição
- Passos para reproduzir
- Resultado esperado vs. resultado obtido
- Evidências (imagens inline em base64)

## Workflow sugerido

1. Executar cenário no QA Runner.
2. Cenário falha → clicar no botão `FAIL` → modal abre.
3. **Opcional — capturar contexto da conversa:** no painel de Acompanhamento, abrir a conversa relacionada, clicar no ícone 📋 ao lado da mensagem com problema. Voltar ao modal do QA Runner e clicar em **"📋 Colar do clipboard"** na seção "Contexto da conversa". Telefone, ID da negociação, timestamps e textos da pergunta/resposta entram automaticamente no `.md` final.
4. Preencher descrição, passos, resultado esperado/obtido.
5. Colar prints (Ctrl+V) na área de evidências.
6. Salvar → arquivo aparece aqui.
7. Para correção, abrir branch `bugfix/BUG-<sigla>-descricao` (convenção do projeto — ver `AGENTS.md`).

## Formato do contexto

Quando capturado pelo botão 📋 do painel, o `.md` ganha uma seção `## Contexto da conversa` com:

- Telefone, ID da negociação, modo de operação, timestamp da captura.
- Pergunta do cliente: ID da mensagem, timestamp, conteúdo.
- Resposta do sistema: ID da mensagem, timestamp, status (pendente?), ID do processamento, conteúdo.

A captura é **somente do par mais próximo** (a mensagem que você clicou e a vizinha mais relevante). Se precisar de mais contexto, complemente com prints ou texto livre na descrição.
