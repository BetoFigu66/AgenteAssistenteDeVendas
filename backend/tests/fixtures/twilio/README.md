# Fixtures de payloads reais da Twilio (anonimizadas)

Origem: colheita de 25/09/2026 no WhatsApp Sandbox da Twilio, gravada por
`TWILIO_CAPTURAR_PAYLOADS` em `backend/logs/payloads_twilio.jsonl` (fora do git).
Cada arquivo é uma chamada real, com o formulário exatamente como a Twilio mandou,
exceto pela anonimização abaixo. Servem para os testes de webhook conferirem o código
contra o que a Twilio de fato envia, e não contra o que supomos que ela envia.

Anonimizado:

- telefone do remetente (`From`, `WaId`, `To` do status, `ChannelToAddress` mascarado)
  trocado por `+5511900000001`; `ProfileName` por "Cliente Teste"; `ExternalUserId`
  por um id fictício do mesmo formato;
- `AccountSid` e todos os SIDs (`SM`, `MM`, `ME`, `XE`) trocados por fictícios do mesmo
  formato (prefixo + 32 hex), de forma consistente: o mesmo SID real virou o mesmo SID
  fictício em todos os arquivos, inclusive dentro das `MediaUrl` e do
  `OriginalRepliedMessageSid` (que cita a mensagem dos `status_*.json`);
- coordenadas da localização, nome do PDF e o texto longo (trocado por texto neutro de
  tamanho e caracteres especiais equivalentes); `ChannelMetadata` segue os mesmos valores;
- `x-twilio-signature` removido: foi calculado sobre o formulário real e não vale para
  este.

O número `whatsapp:+14155238886` é o número público do Sandbox da Twilio, não é dado
pessoal.
