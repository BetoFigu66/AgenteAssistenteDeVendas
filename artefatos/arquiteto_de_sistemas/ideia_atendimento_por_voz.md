# Ideia: atendente conversando por voz com o cliente

<!-- CLASSIFICACAO: SISTEMA-DEV -->

**Data**: 2026-11-24
**Autor**: Arquiteto de Sistemas (conversa com o Beto)
**Status**: Ideia registrada, com pouca chance de ser usada. Fica pronta para o caso de algum cliente pedir a funcionalidade.

## O que é

Permitir que o atendente humano fale por voz com o cliente, pelo número da empresa, a partir do atendimento no painel. Hoje a conversa humana já existe por texto: no modo `HUMANO` o assistente para de gerar resposta e o atendente escreve pela tela (`POST /api/atendimentos/{id}/mensagens-manuais`, entregue por `services/envio.py::entregar_mensagem`). Voz é o que falta.

Não é um agente de IA falando: é o atendente humano. O assistente continua só no texto.

## Pré-requisitos

- Conta Twilio paga (a trial expirou em 29/09/2026) e o número próprio da empresa (chip pré-pago, decisão de agosto).
- Aviso ao cliente se a chamada for gravada (LGPD).

## Caminhos possíveis

**1. Ligação telefônica comum disparada pelo painel (Twilio Voice).** O número do WhatsApp do cliente é um telefone de verdade. Botão **Ligar** no atendimento, em uma de duas formas:

- Ponte com o celular do atendente: a Twilio liga para o atendente e, quando ele atende, liga para o cliente e conecta os dois. É a mais simples de usar, sem fone nem navegador.
- No navegador: o atendente fala pelo computador (Twilio Voice JS SDK, WebRTC). Precisa de microfone e fone.

Nas duas, a ligação sai pelo número da empresa, pode ser gravada e fica registrada no atendimento (horário, duração, gravação). O cliente também pode ligar para o número e cair no atendente.

**2. Chamada de voz pelo próprio WhatsApp.** A Meta tem uma API de chamadas para o WhatsApp Business e a Twilio passou a oferecê-la (não confirmado em 24/11/2026: disponibilidade geral, Brasil e preço). É a experiência mais natural para o cliente, porque a ligação chega pelo mesmo contato da conversa.

**3. Twilio Flex.** Central de atendimento pronta, com telefone do atendente, fila, distribuição entre atendentes e métricas. A mais completa e a mais cara (licença por usuário) e trabalhosa: as mensagens do atendimento humano passam pela Twilio Conversations, e o nosso `/webhook` deixa de recebê-las, o que exige sincronizar pelos webhooks da Conversations (`onMessageAdded`) para o histórico continuar completo no nosso banco. Só compensa com vários atendentes e volume.

## Ponto comum a todos: a voz fica fora do histórico

Quando o atendimento volta para o modo `AGENTE`, o assistente não sabe o que foi combinado na ligação. Solução: transcrever a chamada (Twilio ou outro modelo de transcrição) e gravar um resumo no atendimento, como evento ou mensagem anotada, para o cérebro continuar coerente.

## Recomendação, se um cliente pedir

Começar pelo caminho 1 com ponte para o celular do atendente: é o mais curto até "o atendente fala com o cliente pelo número da empresa e o sistema registra". O 2 entra quando a chamada pelo WhatsApp estiver confirmada na Twilio. O Flex só se o volume justificar.

O ponto de entrada no código já existe: a passagem para `ModoOperacao.HUMANO` (escalonamento ou ação do atendente) é onde o botão **Ligar** e o registro da chamada se encaixam.

## A verificar antes de implementar

- Chamada de voz pelo WhatsApp na Twilio: disponibilidade, suporte no Brasil e custo.
- Coexistência do número: um número registrado na API do WhatsApp em geral não pode ser usado ao mesmo tempo no aplicativo do celular. Existe a coexistência com o WhatsApp Business app, mas não se sabe se a Twilio suporta. Isso importa se alguém contar em atender ligações pelo celular com o chip da empresa.
- Preços atuais de Twilio Voice (minuto de ligação no Brasil, gravação, transcrição) e do Flex.
- No caso do Flex: se o mesmo número WhatsApp pode atender ao nosso webhook e à Conversations com autocriação ligada sem conflito de roteamento.
