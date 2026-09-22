# Painel do Assistente de Vendas

Este painel é a central de operação do assistente que atende clientes pelo WhatsApp.
É aqui que a equipe acompanha as conversas, revisa o que o assistente pretende
responder e ajusta o comportamento dele.

## As abas do sistema

- **Chat** — simulador de atendimento. Permite conversar com o assistente fingindo ser
  um cliente, sem envolver o WhatsApp real. Use para testar respostas.
- **Acompanhamento** — tela principal do dia a dia. Lista os atendimentos em andamento
  e é onde se aprova ou reprova cada resposta antes de ela chegar ao cliente.
- **Triagem de Reports** — fila de problemas registrados sobre respostas do assistente.
- **Base Q&A** — perguntas e respostas prontas que o assistente usa para responder.
- **Parâmetros** — ajustes finos de funcionamento, alteráveis sem reiniciar o sistema.

## O que aparece no topo da tela

- Seu nome de usuário e o botão de sair, na barra escura superior.
- O **modo de execução** vigente, no canto direito do cabeçalho. Ele vale para o sistema
  inteiro e define o quanto o assistente age sozinho:
  - **Simulação** — nada é enviado ao cliente.
  - **Conversa Controlada** — envio só acontece após aprovação humana.
  - **Execução Normal** — o assistente envia automaticamente.

## Como funciona o atendimento, em resumo

1. O cliente manda uma mensagem no WhatsApp.
2. O sistema identifica quem é (pelo telefone), entende a intenção da mensagem e monta
   uma resposta — usando a Base Q&A, a base de conhecimento dos produtos ou textos padrão.
3. A resposta fica registrada e, conforme o modo de execução, aguarda aprovação de
   alguém da equipe na tela de Acompanhamento.
4. Se alguém reprova a resposta, é aberto automaticamente um report na fila de Triagem.

## Ajuda das outras telas

Cada tela tem seu próprio botão de ajuda, com o ícone **?** ao lado do título.
Ele explica o que aquela tela faz e como executar as ações mais comuns.
