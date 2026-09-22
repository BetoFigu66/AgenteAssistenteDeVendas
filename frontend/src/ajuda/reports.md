# Triagem de Reports

Fila dos problemas registrados sobre respostas do assistente. Um report nasce de duas
formas: automaticamente, quando alguém **reprova** uma mensagem no Acompanhamento, ou
manualmente, pelo botão **Reportar**.

O objetivo desta tela é transformar esses relatos em melhorias concretas na base de
conhecimento e no comportamento do assistente.

## Painel de números

Os cartões do topo mostram o total de reports e a divisão por situação:

- **Abertos** — ainda não analisados.
- **Em análise** — alguém já está investigando.
- **Aguardando fix** — a causa foi identificada e a correção está pendente.
- **Resolvidos** — corrigidos.
- **Descartados** — avaliados e considerados improcedentes.

Logo abaixo aparece a distribuição por categoria e por severidade. Quando há filtro
ativo, os cartões mostram também o número correspondente ao recorte filtrado.

## Filtrar a fila

Você pode combinar:

- **Status**, **Categoria** e **Severidade**.
- **Apenas não-finalizados** — deixa de fora resolvidos e descartados. É o padrão.
- **Autor** — quem registrou o report.
- **Busca por texto** e **período** de datas.

## Analisar um report

Clique em um item da lista para abrir o detalhe. Ali você encontra a mensagem que gerou
o problema, a justificativa de quem reportou e o trecho da conversa em volta, para
entender o que o cliente havia dito antes.

Conforme avança a investigação, atualize o status do report — o histórico de mudanças
fica registrado.

## Pacote de análise

O botão de download gera um arquivo YAML com o report, a conversa ao redor e o
raciocínio do assistente. Ele serve para análise fora do painel, quando é preciso
estudar o caso com calma e propor ajustes na base de conhecimento.
