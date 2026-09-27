# Chat (simulador de atendimento)

Ambiente de testes: aqui **você escreve como se fosse o cliente** e vê o que o
assistente responderia. Serve para experimentar perguntas e conferir o comportamento
do sistema antes de o cliente real passar pela mesma situação.

## Escolher com quem conversar

No painel **Telefones**, à esquerda:

- Digite um número no formato `+5511999999999` e clique em **Iniciar Conversa** para
  começar um atendimento novo.
- Ou selecione uma das **Conversas anteriores**, ordenadas da mais recente para a mais
  antiga, com a data da última mensagem.

O número usado determina quem o sistema acha que está falando. Um telefone já
cadastrado carrega a empresa e o histórico correspondentes; um número novo entra como
desconhecido, e o assistente vai pedir os dados de identificação.

A lista inclui também os telefones que falaram pelo WhatsApp de verdade. Ao abrir um
deles você vê a conversa real, e o que digitar aqui entra nela como se o cliente tivesse
escrito. Para testar, prefira números de teste.

## Faixa de informações da conversa

Logo abaixo do cabeçalho aparecem os dados que o sistema reconheceu:

- **Empresa** (CNPJ e nome fantasia) ou **Pessoa** (nome e CPF mascarado). Clique na
  empresa para ver o cadastro completo.
- **Contato**: nome de quem está falando.
- **Atendimento**: número e situação; clique para abrir o detalhe (veja abaixo).
- **Fase**: *Esclarecendo*, *Finalizando* ou *Em orçamentação*.
- Selo âmbar **N pendentes**: dados que ainda faltam ser coletados. Passe o mouse sobre
  ele para ver as perguntas. Quando não falta nada, aparece o selo verde **Pronto para
  orçamento**.
- **Já coletado**: o que o cliente já informou (modelo, quantidade, faixa de pessoas
  etc.), para ninguém repetir a pergunta. Passe o mouse para ver a pergunta de cada item.

Quando aparece "não identificada" ou "não identificado", o sistema ainda não associou
aquele telefone a um cadastro.

## Detalhe do atendimento

Ao clicar no atendimento abre uma janela com os dados dele, a **Timeline do atendimento**
(criação, escalonamento, troca de modo e de fase, encerramento, reabertura), as
**Informações coletadas** e, quando houver, itens e orçamentos.

Se o atendimento foi escalado, o bloco laranja mostra o motivo e a seção **Por que
escalou**, a mesma da tela de Acompanhamento: gatilhos, evidências e a avaliação
**Procedente** / **Indevido**, com comentário, **Salvar comentário** e **Desfazer
avaliação**. Marcar Indevido abre um report e mostra o link **Report #N aberto**, que
abre o report ali mesmo. Aqui a mensagem de origem e o raciocínio aparecem só pelo
número; para navegar até eles use o Acompanhamento. Os detalhes da avaliação estão na
ajuda daquela tela.

## As mensagens

- Seus balões aparecem como **Você** (o cliente) e os do sistema como **Assistente**.
- Ícone de **cérebro**: abre o raciocínio completo que gerou a resposta.
- **Responder citando** (seta, aparece ao passar o mouse numa mensagem do Assistente):
  marca a qual pergunta sua próxima mensagem responde, como o "Responder" do WhatsApp.
  A citação aparece acima do campo de digitação; o **X** cancela.
- **Não entregue** (em vermelho): o sistema tentou enviar a mensagem, mas o WhatsApp
  recusou. O motivo aparece ao lado; o caso comum é a janela de 24 horas do WhatsApp.
  A aprovação continua valendo, só a entrega falhou.

Mensagens do cliente entre colchetes são anotações do sistema, não texto digitado:
`[documento recebido: …]` (com o nome do arquivo), `[localização: …]` (com as
coordenadas) e `[mídia recebida sem texto: …]` (foto, áudio etc.). O assistente não lê
esses anexos e **não responde a eles**; quem responde é o vendedor, pelo Acompanhamento
(em modo Humano).

Em conversas vindas do WhatsApp, o assistente pode perguntar logo no início **"Posso te
chamar assim ou seu nome é outro?"**, usando o nome do perfil do cliente. O nome só é
gravado depois da resposta: "sim" confirma, outro nome substitui, e um "não" sem nome
faz o assistente perguntar o nome uma vez. Conversas iniciadas aqui no Chat não têm
nome de perfil, então essa pergunta não aparece nelas.

## Campo Score RAG

No cabeçalho azul há um campo numérico de 0 a 1 que define o quanto um trecho da base
de conhecimento precisa ser relevante para o assistente utilizá-lo. É um atalho para o
mesmo ajuste disponível na aba Parâmetros, útil para calibrar durante um teste. O valor
é salvo ao sair do campo ou apertar Enter.

Atenção: a alteração vale para o **sistema inteiro**, não só para esta conversa.

## Apagar conversa

O botão **Apagar conversa**, também no cabeçalho, remove o contato, os atendimentos e
as mensagens daquele telefone. Serve para recomeçar um teste do zero, como se o número
nunca tivesse falado com a empresa.

A ação pede confirmação, mas **não pode ser desfeita**: use apenas com telefones de
teste. O recurso é restrito a ambiente de desenvolvimento (exige `DEBUG=True` no backend).

## Observações

- As mensagens enviadas aqui passam pelo mesmo processamento das mensagens reais e
  ficam gravadas no histórico do atendimento.
- Para aprovar ou reprovar as respostas geradas, use a aba **Acompanhamento**. Se o
  canal de saída estiver ligado ao WhatsApp, a resposta aprovada é entregue ao número
  usado aqui.
