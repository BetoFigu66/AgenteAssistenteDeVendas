# Painel do Assistente de Vendas

Este painel é a central de operação do assistente que atende clientes pelo WhatsApp.
É aqui que a equipe acompanha as conversas, revisa o que o assistente pretende
responder e ajusta o comportamento dele.

## As abas do sistema

- **Chat**: simulador de atendimento. Você escreve como se fosse o cliente e vê o que o
  assistente responderia. Também mostra o histórico das conversas reais de cada telefone.
- **Acompanhamento**: tela principal do dia a dia. Lista os atendimentos e é onde se
  aprova ou reprova cada resposta, assume a conversa como humano e avalia os
  escalonamentos.
- **Triagem de Reports**: fila de problemas registrados sobre respostas e escalonamentos
  do assistente.
- **Base Q&A**: perguntas e respostas prontas que o assistente usa para responder.
- **Parâmetros**: ajustes finos de funcionamento, alteráveis sem reiniciar o sistema.
- **Base de Ajuda**: onde se escreve a ajuda deste painel — o conteúdo que aparece no
  botão **?** de cada tela. É ajuda interna, não vai para clientes.

## O que aparece no topo da tela

- Na barra escura superior: telefone e e-mail da Inforrel, seu nome de usuário e o
  botão de sair.
- No canto direito do cabeçalho: o **modo de execução** vigente e o seletor para trocá-lo.
  Ele vale para o sistema inteiro e define se as respostas passam por uma pessoa:
  - **Simulação**: toda resposta do assistente fica pendente até alguém aprovar. Modo de
    testes.
  - **Conversa Controlada**: também exige aprovação de cada resposta, para conversas com
    clientes reais sob supervisão.
  - **Execução Normal**: o assistente responde sozinho, sem aprovação.

Passar para **Execução Normal** pede confirmação. A janela mostra as decisões humanas dos
últimos 7 dias (aprovadas, reprovadas, taxa de aprovação e quantas aguardam decisão)
para ajudar a avaliar se o assistente já está maduro para responder sozinho. Voltar para
um modo com aprovação não pede confirmação.

Se a mensagem chega de fato ao WhatsApp do cliente depende de outra trava, o **canal de
saída**, configurado pela equipe técnica fora do painel. Com o canal simulado nada é
entregue, em nenhum modo; a janela de confirmação avisa quando é esse o caso.

## Como funciona o atendimento, em resumo

1. O cliente manda uma mensagem no WhatsApp.
2. O sistema identifica quem é (pelo telefone), entende a intenção da mensagem e monta
   uma resposta, usando a Base Q&A, a base de conhecimento dos produtos ou textos padrão.
3. Conforme o modo de execução, a resposta vai direto ou aguarda aprovação na tela de
   Acompanhamento.
4. Se o cliente pede uma pessoa, reclama ou o caso é complexo, o atendimento é escalado
   para humano e o assistente para de responder nele.
5. Reprovar uma resposta, ou avaliar um escalonamento como indevido, abre um report na
   fila de Triagem.

## Ajuda em cada tela

Cada tela tem seu próprio botão de ajuda, com o ícone **?** ao lado do título. Ao abrir,
você pode **digitar uma pergunta** ("como aprovo uma mensagem?") ou clicar numa das
perguntas frequentes sugeridas. Abaixo fica sempre a explicação completa da tela.

Se a sua pergunta não tiver resposta, ela é registrada para virar conteúdo de ajuda —
quem cuida disso vê a lista na aba **Base de Ajuda**.
