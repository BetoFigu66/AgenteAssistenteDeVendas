# Chat (simulador de atendimento)

Ambiente de testes: aqui **você escreve como se fosse o cliente** e vê o que o
assistente responderia. Serve para experimentar perguntas e conferir o comportamento
do sistema antes de o cliente real passar pela mesma situação.

## Escolher com quem conversar

No painel **Telefones**, à esquerda:

- Digite um número no formato `+5511999999999` e clique em **Iniciar Conversa** para
  começar um atendimento novo.
- Ou selecione uma das conversas anteriores na lista, ordenada da mais recente para a
  mais antiga.

O número usado determina quem o sistema acha que está falando. Um telefone já
cadastrado carrega a empresa e o histórico correspondentes; um número novo entra como
desconhecido, e o assistente vai pedir os dados de identificação.

## Faixa de informações da conversa

Logo abaixo do cabeçalho aparecem os dados que o sistema reconheceu:

- **Empresa** (CNPJ) ou **Pessoa** (CPF mascarado) — clique na empresa para ver o
  cadastro completo.
- **Contato** — nome de quem está falando.
- **Atendimento** — número e situação; clique para abrir o detalhe.
- **Fase** e, quando houver, um selo âmbar com os dados que ainda faltam ser coletados.
  Passe o mouse sobre ele para ver a lista.

Quando aparece "não identificada", é sinal de que o sistema ainda não associou aquele
telefone a um cadastro.

## Campo Score RAG

No cabeçalho azul há um campo numérico de 0 a 1 que define o quanto um trecho da base
de conhecimento precisa ser relevante para o assistente utilizá-lo. É um atalho para o
mesmo ajuste disponível na aba Parâmetros, útil para calibrar durante um teste.

Atenção: a alteração vale para o **sistema inteiro**, não só para esta conversa.

## Apagar conversa

O botão **Apagar conversa**, também no cabeçalho, remove o contato, os atendimentos e
as mensagens daquele telefone — serve para recomeçar um teste do zero, como se o número
nunca tivesse falado com a empresa.

É uma ação **destrutiva e sem confirmação**: use apenas com telefones de teste. O
recurso é restrito a ambiente de desenvolvimento (exige `DEBUG=True` no backend).

## Observações

- As mensagens enviadas aqui passam pelo mesmo processamento das mensagens reais e
  ficam gravadas no histórico do atendimento.
- Para aprovar ou reprovar as respostas geradas, use a aba **Acompanhamento**.
