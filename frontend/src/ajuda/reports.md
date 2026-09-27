# Triagem de Reports

Fila dos problemas registrados sobre respostas do assistente. Um report nasce de três
formas:

- automaticamente, quando alguém **reprova** uma mensagem no Acompanhamento;
- automaticamente, quando alguém avalia um escalonamento como **indevido** (categoria
  *Escalonamento indevido*);
- manualmente, pelo botão **Reportar** (formulário *Reportar problema* no raciocínio da
  mensagem).

O objetivo desta tela é transformar esses relatos em melhorias concretas na base de
conhecimento e no comportamento do assistente.

## Painel de números

Os cartões do topo mostram o total de reports e a divisão por situação:

- **Abertos**: ainda não analisados.
- **Em análise**: alguém já está investigando.
- **Aguardando fix**: a causa foi identificada e a correção está pendente.
- **Resolvidos**: corrigidos.
- **Descartados**: avaliados e considerados improcedentes.

Logo abaixo aparece a distribuição por categoria e por severidade. Quando há filtro
ativo, os cartões mostram o recorte filtrado sobre o total (por exemplo *3/12*).

## Categorias

*Classificação* (intenção ou dados lidos errado), *Fluxo* (caminho da conversa errado),
*Template* (texto ou tom da resposta), *Resposta Inadequada* (resposta reprovada),
*Dados* (CNPJ, contato etc. incorretos), *LLM*, *Escalonamento indevido* (aberto sozinho
quando um escalonamento é avaliado como indevido) e *Outro*.

## Filtrar a fila

Você pode combinar:

- **Status**, **Categoria** e **Severidade**.
- **Apenas não-finalizados**: deixa de fora resolvidos e descartados. É o padrão, e fica
  desligado quando um Status específico está escolhido.
- **Autor** (quem registrou) e **Busca** (texto da descrição ou da resolução): valem ao
  apertar Enter ou clicar em **Buscar**.
- Período **De** / **Até**.

## Analisar um report

Clique em um item da lista para abrir o detalhe. Ali você encontra:

- a **Descrição** de quem reportou, com data e autor;
- o **Contexto da conversa** em volta, com a mensagem reportada destacada;
- **Ver processamento completo** (o raciocínio do assistente) e **Ver atendimento #N**,
  que leva direto ao atendimento na tela de Acompanhamento;
- o resumo do processamento e, quando usados, os trechos da base de conhecimento.

No report de escalonamento indevido, a descrição traz o motivo, os gatilhos, as
evidências e o comentário de quem avaliou.

## Triagem e histórico

No bloco **Triagem**, ajuste **Status**, **Categoria** e **Severidade**, descreva em
**Resolução** o que foi feito e clique em **Salvar alterações**. O seletor de status só
oferece os próximos passos possíveis (por exemplo, um report *Aberto* vai para *Em
análise* ou *Descartado*; um resolvido ou descartado pode voltar para *Em análise*).

O **Histórico de alterações** registra cada mudança de status, categoria e severidade,
com data e autor. No report de escalonamento indevido, se a avaliação do escalonamento
mudar depois, a mudança também aparece ali como *Avaliação do escalonamento*.

## Criar par Q&A a partir do report

Quando o problema é uma resposta que faltava ou estava errada, use **Criar par Q&A**: a
pergunta do cliente vem preenchida, você escreve a resposta ideal, escolhe o contexto e
clica em **Salvar rascunho**. O par vai para a **Base Q&A** como pendente, ligado a este
report, e só passa a valer depois de aprovado lá.

## Pacote para curador

O botão **Download YAML** gera um arquivo com o report, a conversa, uma nova busca na
Base Q&A e na base de conhecimento e sugestões de documentos. Serve para análise fora
do painel pelo curador de conhecimento, quando é preciso estudar o caso com calma.
