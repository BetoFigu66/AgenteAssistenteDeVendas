# Acompanhamento de Atendimentos

Tela principal do dia a dia. Do lado esquerdo ficam os atendimentos; ao clicar em um
deles, o lado direito mostra a conversa completa e as ações disponíveis.

A lista vem **ordenada por mensagens pendentes de aprovação**, ou seja, o que precisa
da sua atenção aparece primeiro. O botão **Atualizar** recarrega a lista, e **Anterior**
/ **Próxima** navegam entre as páginas (20 atendimentos por página).

## Lista de atendimentos

Cada linha traz o número do atendimento, a empresa (quando identificada), o nome do
contato, o telefone, o status e a hora da última mensagem. Ao lado aparecem os selos:

- **AGENTE** (verde): o assistente está respondendo automaticamente.
- **HUMANO** (laranja): o assistente parou de responder e alguém da equipe assumiu.
  Passe o mouse sobre o selo para ver o motivo do escalonamento.
- **Fase**: em que ponto da negociação o atendimento está: *Esclarecendo* (entendendo
  a necessidade), *Finalizando* (juntando dados para fechar) ou *Em orçamentação*.
- **N pendentes** (vermelho): quantas respostas aguardam aprovação.

Para localizar um atendimento, use o campo de busca (telefone, nome do contato ou
empresa; aplica ao apertar Enter ou sair do campo) e o seletor de status: *Ativos*,
*Encerrados* ou *Todos*.

## Modo de Operação

No painel da direita você alterna entre:

- **Agente (automático)**: o assistente continua gerando respostas.
- **Humano (manual)**: o assistente para de responder e libera o campo de digitação
  no rodapé, para você escrever diretamente ao cliente.

A troca vale só para aquele atendimento e tem efeito imediato na próxima mensagem
que o cliente enviar. Assumir como Humano também fica registrado como um escalonamento
(*Vendedor assumiu a conversa*).

## Por que escalou

Quando o atendimento foi escalado, ou está em modo Humano, aparece abaixo do Modo de
Operação a faixa laranja **Por que escalou**. Ela já abre sozinha quando há escalonamento
ainda não avaliado; com todos avaliados, fica fechada (clique nela para abrir). O resumo
ao lado diz quantos escalonamentos o atendimento teve e quantos ainda não foram avaliados.

Cada escalonamento (o mais recente primeiro) mostra:

- **Motivo**, a data e hora e quem escalou (o próprio sistema, o cliente ou o vendedor).
- **Gatilhos**: o que concretamente disparou, por exemplo *Cliente pediu muitos
  equipamentos de uma vez* ou *Cliente falou em leitor facial*. Pode haver mais de um.
- **Evidências**: os valores que o sistema leu e o limite vigente na hora, por exemplo
  "Quantidades lidas: 1, 2, 3, 20, 25 (mínimo 4)" ou "Faixa de funcionários: 45
  (limiar 60)", além da intenção detectada (por exemplo *Pedir orçamento*), da confiança
  (Alta, Média ou Baixa) e se foi identificada por regra ou pela IA.
- **Ver mensagem de origem**: rola a conversa até a mensagem que causou o escalonamento
  e a destaca por alguns segundos. **Ver raciocínio** abre o cérebro daquela mensagem.
  Se a mensagem não está na conversa carregada, aparece só o número dela.

Escalonamentos anteriores a 26/09/2026 não têm esse registro detalhado, só o motivo.

### Avaliar o escalonamento

Olhando as evidências, marque se o escalonamento fez sentido:

- **Procedente**: o atendimento precisava mesmo de uma pessoa.
- **Indevido**: o sistema escalou sem necessidade (por exemplo, leu "1) 2) 3)" de uma
  lista como quantidade de equipamentos).

O comentário é opcional, mas ajuda a corrigir a regra depois. A avaliação mostra quem
avaliou e quando, e pode ser trocada a qualquer momento (vale a última). Para mudar só o
comentário, edite o texto e clique em **Salvar comentário** (o botão só habilita depois de
avaliar e quando o texto mudou). **Desfazer avaliação** volta para *Não avaliado* e apaga o
comentário.

Marcar **Indevido** abre automaticamente um report na tela **Reports**, na categoria
*Escalonamento indevido*, com o motivo, os gatilhos, as evidências e o seu comentário. O
link **Report #N aberto** aparece no escalonamento e abre o report ali mesmo; quando o
report avança na triagem, o link passa a mostrar a situação dele (por exemplo *Report #N
(Em análise)*). Marcar indevido de novo ou trocar o comentário atualiza o mesmo report,
sem abrir outro. Se a avaliação mudar depois (procedente ou desfeita), o report continua
na fila e a mudança fica anotada no histórico dele. Quando foi o vendedor quem assumiu
pelo painel, não há mensagem do cliente para analisar e nenhum report é aberto.

## Aprovar ou reprovar uma resposta

Mensagens do assistente com fundo amarelo e o selo **Pendente** ainda não foram
enviadas ao cliente; as já liberadas têm o selo verde **Aprovada**. Em cada pendente:

- **Aprovar**: libera a mensagem. Antes, o sistema pergunta um feedback opcional
  ("correto, mas..."); deixe em branco para pular.
- **Reprovar**: abre uma janela que pede a **justificativa** (obrigatória) e **abre
  automaticamente um report** na aba Triagem de Reports.

Na janela de reprovação dá para, opcionalmente, **registrar a resposta correta**: a
pergunta do cliente já vem preenchida, você escolhe o contexto e escreve como o
assistente deveria ter respondido. Isso vira um rascunho na **Base Q&A**, para revisão.
Se já houver rascunhos aguardando aprovação, o sistema lista esses rascunhos e pede para
clicar de novo para confirmar.

O selo cinza *há N min* mostra há quanto tempo a mensagem espera. Ele fica vermelho
quando ultrapassa o tempo limite definido no parâmetro `sla_aprovacao_minutos`.

## Entender por que o assistente respondeu aquilo

- Ícone de **cérebro**: abre o raciocínio completo (intenção detectada, confiança,
  dados extraídos da mensagem, trechos de conhecimento consultados e tempo de resposta).
  É o melhor lugar para investigar uma resposta estranha.
- Ícone de **prancheta**: copia o contexto da mensagem (pergunta do cliente e resposta do
  assistente), para colar no QA Runner ao relatar um problema.
- Botão **Reportar**: abre o mesmo raciocínio, com o formulário **Reportar problema** no
  final (descrição, categoria e severidade). Registra um problema mesmo sem reprovar a
  mensagem.

## Mensagens que o assistente não responde

Mensagens do cliente entre colchetes são anotações do sistema: `[documento recebido: …]`,
`[localização: …]` e `[mídia recebida sem texto: …]` (foto, áudio etc.). O assistente
não lê anexos e não gera resposta para elas. Se precisar responder, assuma o atendimento
em modo **Humano** e escreva você.

No início de conversas pelo WhatsApp, o assistente pode perguntar **"Posso te chamar
assim ou seu nome é outro?"**, oferecendo o nome do perfil do cliente. O nome só é
gravado depois que o cliente responde.

## Enviar mensagem manual

Disponível apenas quando o modo está em **Humano**. Digite no rodapé e pressione Enter
para enviar (Shift+Enter quebra a linha).
