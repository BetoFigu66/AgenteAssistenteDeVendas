# Bugs encontrados durante os testes manuais

<!-- CLASSIFICACAO: SISTEMA-DEV -->

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

## Arquivos `_status_execucao.*` (compartilhamento entre máquinas)

Toda vez que você muda algum status no QA Runner (PENDENTE / OK / FAIL / N/A) ou edita uma observação, o runner regrava **automaticamente** dois arquivos nesta pasta:

- `_status_execucao.json` — dump estruturado (versao, plano, timestamp e lista de cenários com status, observação e bugs vinculados). É **fonte da verdade** para sincronizar entre máquinas.
- `_status_execucao.md` — tabela legível com resumo (totais por status) e uma linha por cenário. É o que o time olha no GitHub/IDE quando quer saber o estado da execução **sem abrir o QA Runner**.

### Para o desenvolvedor (Beto) ver o estado dos testes

1. Pull no repositório (a Kika commitou os arquivos junto com os bugs).
2. Abrir `artefatos/qa/bugs/_status_execucao.md` no IDE ou no GitHub.
3. Filtrar por `FAIL` para ver os bugs ativos; cada linha referencia os arquivos `*-01.md`, `*-02.md` etc. desta mesma pasta.

### Para abrir o estado dentro do próprio QA Runner em outra máquina

1. Carregar o plano (`1. Carregar plano (.md)`).
2. Selecionar a pasta de bugs (`2. Pasta de bugs`).
3. Se houver `_status_execucao.json` na pasta, o QA Runner pergunta se você quer **sobrescrever o status local** com o estado salvo. Confirmando, a tabela aparece com tudo que a outra pessoa marcou.

### Política de commit

- ✅ Comitar `_status_execucao.md` e `_status_execucao.json` junto com os bugs.
- ⚠️ Não editar esses arquivos à mão — eles são regrávados pelo runner.
- O `.json` muda a cada interação (timestamp); commits devem ser feitos no fim de uma sessão de teste, não a cada clique.
