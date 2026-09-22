# Acompanhamento de Atendimentos

Tela principal do dia a dia. Do lado esquerdo ficam os atendimentos; ao clicar em um
deles, o lado direito mostra a conversa completa e as ações disponíveis.

A lista vem **ordenada por mensagens pendentes de aprovação**, ou seja, o que precisa
da sua atenção aparece primeiro.

## Lista de atendimentos

Cada linha traz o número do atendimento, a empresa (quando identificada), o nome do
contato e o telefone. Ao lado aparecem os selos:

- **AGENTE** (verde) — o assistente está respondendo automaticamente.
- **HUMANO** (laranja) — o assistente parou de responder e alguém da equipe assumiu.
  Passe o mouse sobre o selo para ver o motivo do escalonamento.
- **Fase** — em que ponto da negociação o atendimento está: *Esclarecendo* (entendendo
  a necessidade), *Finalizando* (juntando dados para fechar) ou *Em orçamentação*.
- **N pendentes** (vermelho) — quantas respostas aguardam aprovação.

Para localizar um atendimento, use o campo de busca (aceita telefone, nome do contato
ou empresa) e o seletor de status: *Ativos*, *Encerrados* ou *Todos*.

## Modo de Operação

No painel da direita você alterna entre:

- **Agente (automático)** — o assistente continua gerando respostas.
- **Humano (manual)** — o assistente para de responder e libera o campo de digitação
  no rodapé, para você escrever diretamente ao cliente.

A troca vale só para aquele atendimento e tem efeito imediato na próxima mensagem
que o cliente enviar.

## Aprovar ou reprovar uma resposta

Mensagens do assistente com fundo amarelo e o selo **Pendente** ainda não foram
enviadas ao cliente. Em cada uma:

- **Aprovar** — libera a mensagem.
- **Reprovar** — pede uma justificativa e **abre automaticamente um report** na aba
  Triagem de Reports, para que o problema seja analisado depois.

O selo cinza *há N min* mostra há quanto tempo a mensagem espera. Ele fica vermelho
quando ultrapassa o tempo limite definido no parâmetro `sla_aprovacao_minutos`.

## Entender por que o assistente respondeu aquilo

- Ícone de **cérebro** — abre o raciocínio completo: intenção detectada, confiança,
  dados extraídos da mensagem, trechos de conhecimento consultados e tempo de resposta.
  É o melhor lugar para investigar uma resposta estranha.
- Ícone de **prancheta** — copia o contexto da mensagem, para relatar um problema.
- Botão **Reportar** — registra um problema mesmo sem reprovar a mensagem.

## Enviar mensagem manual

Disponível apenas quando o modo está em **Humano**. Digite no rodapé e pressione Enter
para enviar (Shift+Enter quebra a linha).
