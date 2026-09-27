# Base Q&A

Coleção de perguntas e respostas escritas pela equipe. Quando um cliente pergunta algo
parecido com uma pergunta cadastrada aqui, o assistente responde com o texto revisado
por uma pessoa, em vez de montar a resposta sozinho.

É a forma mais direta e segura de controlar o que o assistente diz.

No cabeçalho aparecem o total de pares e, em laranja, quantos estão **aguardando
aprovação**. O botão **Atualizar** recarrega a lista.

## Rascunho e aprovado

Todo par novo nasce como **Pendente** (rascunho) e **não é usado** no atendimento.
Só depois de **Aprovado** ele passa a valer.

A aprovação é o momento em que o sistema processa a pergunta para conseguir
reconhecê-la mesmo quando o cliente escrever com outras palavras. Por isso o par só
entra em uso após esse passo.

Rascunhos também chegam de outras telas: da janela de **Reprovar** no Acompanhamento e
do botão **Criar par Q&A** de um report. Abaixo da pergunta aparecem o autor e a origem
do par (por exemplo `reprovacao:123` ou `report:45`), para saber de onde ele veio.

## Criar um par

1. Clique em **Novo par**.
2. Escreva a pergunta como um cliente faria e a resposta que o assistente deve dar.
3. Escolha o contexto (catraca, relógio de ponto, leitor facial, controle de acesso,
   bastão de ronda ou geral). Ele ajuda a organizar e a restringir quando aquela
   resposta se aplica.
4. Clique em **Salvar rascunho** e, quando estiver satisfeito, clique no ícone verde da
   linha para aprovar.

Antes de salvar, o sistema procura perguntas parecidas entre os pares já aprovados. Se
encontrar alguma muito semelhante, mostra os candidatos com o percentual de semelhança e
o botão vira **Criar mesmo assim**. Serve para evitar duplicatas que competem entre si
na hora de responder: ajuste a pergunta ou confirme.

## Editar, desativar e filtrar

- **Editar** (lápis): ajusta pergunta, resposta ou contexto. Ao mudar a pergunta de um
  par já aprovado, o reconhecimento é refeito na hora de salvar.
- **Desativar** (lixeira): pede confirmação e tira o par de uso sem apagá-lo. Pares
  inativos aparecem esmaecidos quando você troca o filtro para *Inativos* ou *Todos*.
- **Filtros**: por contexto, situação de aprovação (*Aprovados* / *Pendentes*),
  ativo/inativo e tag. A busca por texto filtra o que já está na tela, procurando tanto
  na pergunta quanto na resposta, e mostra quantos resultados achou.

## Pares mais usados

A faixa logo abaixo do cabeçalho mostra quais pares mais responderam clientes de fato
nos últimos 90 dias, com o número de usos. Passe o mouse para ler a pergunta inteira. É
um bom indicador de quais respostas merecem mais cuidado na revisão, e de quais nunca
são usadas.
