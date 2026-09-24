# Plano: últimos dias da conta Twilio trial (23 a 26/09/2026)

<!-- CLASSIFICACAO: PROCESSO -->

A conta trial expira e leva junto o Sandbox e o pareamento do celular. Tudo que exige a
Twilio de verdade precisa caber nesta janela.

> ## Revisado em 24/09: o Dia 1 não rodou, restam 3 dias
>
> Verificado na manhã de 24/09: nenhuma mensagem nova na conta (a última continua sendo a de
> 14/09), nenhuma das quatro variáveis no `.env`, nenhum payload capturado. O plano original
> tinha quatro dias e agora tem três, então os Dias 1 e 2 foram fundidos.
>
> O que isso custa, em ordem: se **hoje** não houver uma rodada real, o Dia 3 (reply-to e
> cenários) perde a base, porque o reply-to depende do `message_sid` capturado na véspera. E
> se a conta expirar antes do previsto, o que sobra é o que já estiver capturado.
>
> Para reduzir o atrito, as quatro variáveis viraram `./scripts/twilio_modo_teste.sh`
> (`ligar` / `desligar` / `status`), testado nos dois sentidos, preservando as 23 chaves
> existentes do `.env`. O `desligar` importa mais que o `ligar`: `CANAL_SAIDA=twilio` faz o
> sistema responder de verdade no WhatsApp, e esquecer isso ligado é o tipo de coisa que só
> se descobre pelo cliente.

**Restrições, decididas em 23/09:** sem upgrade (cartão fora de cogitação), sem
`TWILIO_AUTH_TOKEN` à mão, ~1h/dia de disponibilidade do Beto para o que exige celular.

---

## 1. O fato que motiva o plano

O canal `twilio` foi construído em 19/09: `services/canal/`, `POST /webhook/status`,
reply-to, validação de assinatura, entrega na aprovação. **Nada disso trocou uma única
mensagem com a Twilio.** A última atividade na conta é de **14/09**, e foi do script de
spike, que é outro programa.

Ou seja: temos código de produção validado apenas contra dublês que nós mesmos escrevemos.

Verificado hoje pela API da conta:

| Evidência | O que diz |
|---|---|
| Última mensagem: 14/09 | nenhum tráfego depois da implementação do canal |
| `IncomingPhoneNumbers`: **0 números** | o `+17372212163` do `.env` não pertence mais à conta |
| Todas as inbound com `error_code=12300` | "Invalid Content-Type" nas respostas do spike |
| Conta não legível pela API Key | a key só tem escopo de Messaging; status e saldo exigem Auth Token |

O `12300` **não** é do nosso sistema: testei o webhook atual e ele responde
`Content-Type: application/xml`, que é válido. Era do spike. Mas serve de aviso: esse erro é
invisível para quem só olha o celular, porque a mensagem parece ter chegado.

## 2. A ideia que organiza a janela

A conta morre; o que extrairmos dela pode ser permanente.

**Todos os nossos testes de webhook montam o formulário à mão**, com os campos que *nós
supomos* que a Twilio manda. Nenhum prova que o campo existe, que se chama assim, ou que vem
nesse formato. É a mesma classe de erro que já nos custou duas sessões: o teste construído em
cima da suposição, que passa justamente por não tocar na realidade.

Então a prioridade número um não é "ver funcionar no celular". É **capturar os payloads reais
de cada situação e convertê-los em fixtures**. Isso sobrevive à conta, e a partir daí os
testes passam a ser conferidos contra o que a Twilio realmente envia.

Já implementado hoje (`TWILIO_CAPTURAR_PAYLOADS`): os dois webhooks gravam o formulário cru,
uma linha JSON por chamada, **antes** de qualquer processamento, para que um erro no cérebro
não faça perder o payload. Desligado por padrão, com teste garantindo que fica desligado.
Arquivo no `.gitignore`, porque contém o seu telefone.

## 3. O que é testável nesta conta, e o que não é

Sendo honesto sobre o escopo, porque metade da lista que parecia óbvia não cabe:

### Testável

| Item | Por quê importa |
|---|---|
| Ciclo TwiML completo no sistema real | é o único caminho de entrega que a trial permite, e nunca rodou |
| `statusCallback` gravando `message_sid` | é o que liga o reply-to; sem ele a pilha de perguntas perde o desempate (0) |
| Reply-to ponta a ponta | o spike provou o mecanismo, o **sistema** não |
| Payloads reais de cada tipo de mensagem | vira fixture permanente |
| Tipos de mídia (foto, áudio, documento, localização, contato) | cada um manda campos diferentes, e o fix de ontem só foi testado com `NumMedia` inventado |
| Casos de borda de texto (emoji, mensagem longa, acentuação) | nunca passaram por um encoding real |
| Os cenários de negócio pelo WhatsApp de verdade | o testador fala com o `/webhook` direto, sem passar pela Twilio |

### **Não** testável nesta conta (e isso é permanente, não pendência)

| Item | Bloqueio |
|---|---|
| Modo `TWILIO_MODO_ENVIO=rest` | Sandbox recusa texto livre pela API (erro **21654**); a Content API, que criaria o template, exige conta paga |
| Entrega ao **aprovar** mensagem | usa REST, mesmo bloqueio |
| Entrega na **resposta manual** do operador | usa REST, mesmo bloqueio |
| Erro **63016** (janela de 24h) | só ocorre no envio REST, que não funciona |
| Validação de `X-Twilio-Signature` | exige `TWILIO_AUTH_TOKEN`, que não temos |

Vale registrar o que isso significa: **os três caminhos de entrega do sistema, hoje, só têm um
exercitável.** `services/envio.py::entregar_mensagem` continuará sendo código nunca executado
contra a Twilio real. Não é falha do plano, é limite da conta, e precisa ficar escrito para
ninguém supor o contrário no piloto com a Rita.

---

## 4. Os dias

### Dia 1 + 2 — hoje (24/09): ligar, provar o ciclo e colher os tipos

**Fundidos, porque só restam três dias.** Se o tempo apertar, a ordem de prioridade dentro da
hora é: (a) uma mensagem ida e volta com `message_sid` preenchido, (b) foto sem legenda, que
é o caso que exercita o fix de ontem, (c) o resto dos tipos. Parar no meio da lista é
aceitável; não começar não é.

**Eu, antes de você começar:** captura de payloads implementada e testada (feito), checklist
de configuração e roteiro abaixo, e verificação de que o túnel e o backend público estão de
pé (feito: `app.auxvendas.com` responde, `/webhook` devolve 200).

**Você (~1h):**

1. **Re-parear o Sandbox.** A sessão expira por inatividade e a última mensagem é de 14/09,
   então quase certamente caiu. No console: Messaging → Try it out → Send a WhatsApp message
   → aba **Sandbox**, e mande a palavra `join <palavra>` que a tela mostrar, do seu celular.
   (Em 14/09 era `join twilio-trial`, mas a palavra muda por conta.)
2. **Apontar o webhook para o sistema**, não para o spike. Na aba **Sandbox settings**, campo
   *"When a message comes in"*: `https://app.auxvendas.com/webhook`, método **POST**.
   Atenção: em 14/09 esse campo apontava para `spike.auxvendas.com`.
3. **Ligar o modo de teste** e reiniciar o backend:
   `./scripts/twilio_modo_teste.sh ligar` (ver seção 5).
4. **Mandar `oi`** do celular e conferir que a resposta chega.

**O que eu faço na sequência, com você parado:** leio o payload capturado, confiro contra o
que os nossos testes supõem, e reporto divergência campo a campo.

**Critério de sucesso do dia:** uma mensagem ida e volta, e o `message_sid` da mensagem de
saída preenchido no banco (prova que o `statusCallback` chegou).

#### A colheita de tipos (a segunda metade da sua hora de hoje)

Cada tipo gera um payload diferente que nunca vimos.

**Você:** mandar, do celular, uma de cada e nada mais:
foto com legenda · foto **sem** legenda · áudio · documento (PDF) · localização · contato
(vCard) · figurinha · emoji puro · mensagem longa (>1000 caracteres) · texto com acentuação e
`ç` · e uma mensagem **editada** depois de enviada.

**Eu:** para cada uma, comparo o payload com o que o código espera, e reporto o que ignoramos
sem saber. O fix de ontem (mensagem sem texto) foi escrito supondo `NumMedia`; este é o dia em
que ele é confrontado com mídia de verdade.

### Dia 2 — sexta (25/09): reply-to e os cenários de negócio

**Você (~1h):**

1. **Reply-to:** responder, com o "Responder" do WhatsApp, a três mensagens nossas diferentes,
   **fora de ordem**. É o teste que o spike fez, agora contra o sistema: o que se quer provar é
   que `resposta_a_mensagem_id` fica preenchido com a mensagem certa.
2. **Cenários de negócio:** rodar pelo WhatsApp real 4 ou 5 dos 17 cenários, escolhendo os de
   prioridade alta (prazo, preço, compatibilidade, pedido de humano). O testador conversa com
   o `/webhook` direto; aqui a mensagem passa pela Twilio, e é onde aparecem diferenças de
   encoding, quebra de linha e agrupamento.

### Dia 3 — sábado (26/09): transformar em patrimônio

**Eu, o dia inteiro:** converter os payloads capturados em fixtures anonimizadas (seu telefone
vira fictício), reescrever os testes de webhook para usarem os formulários reais, e registrar
no `docs/comandos_uteis.md` e no `STATUS.md` o que aprendemos. É o trabalho que faz os 3 dias
anteriores valerem depois que a conta morrer.

**Você (~15 min):** conferir o resumo final e decidir o que vai para o backlog.

---

## 5. Configuração: um comando, não quatro variáveis

```bash
./scripts/twilio_modo_teste.sh ligar       # antes dos testes
./scripts/twilio_modo_teste.sh status      # o que está valendo agora
./scripts/twilio_modo_teste.sh desligar    # AO TERMINAR, sempre
```

Reiniciar o backend depois de cada um: as variáveis são lidas no boot.

O script mexe só nas quatro chaves dele e guarda um backup do `.env` anterior. Verificado nos
dois sentidos, com as 23 chaves existentes preservadas. `TWILIO_VALIDAR_ASSINATURA` fica
deliberadamente de fora: exige o Auth Token, e ligar sem ele faz os dois webhooks devolverem
HTTP 503.

Dois avisos que valem mais que o resto da configuração:

- **`APP_URL_PUBLICA` é o que faz o `statusCallback` existir.** Sem ela a mensagem é entregue
  normalmente, mas nunca descobrimos o SID de saída, e aí o reply-to do Dia 3 não tem como
  funcionar. Se o Dia 1 terminar com `message_sid` nulo, é aqui que se olha primeiro.
- **`CANAL_SAIDA=twilio` faz o sistema falar com cliente de verdade.** Enquanto estiver assim,
  qualquer mensagem que chegar naquele número recebe resposta automática. Voltar para
  `simulado` ao fim dos 4 dias.

Conferir o que está valendo, sem abrir o `.env`:

```bash
curl -s localhost:8000/api/config/execucao | python3 -m json.tool
# esperado durante os testes: "canal_saida": "twilio", "entrega_real": true
```

---

## 6. Riscos e como cada um se manifesta

| Risco | Como aparece | O que fazer |
|---|---|---|
| Sessão do Sandbox expirada | o celular recebe convite para mandar `join <palavra>` | re-parear (passo 1 do Dia 1) |
| Webhook não configurado | volta a *"Standard auto-reply"* da Twilio, cujo texto diz isso | conferir a aba Sandbox settings |
| Webhook configurado, backend fora | não volta nada | `./sanity_check.sh` |
| `APP_URL_PUBLICA` errada | tudo parece funcionar, mas `message_sid` fica nulo | conferir a variável e o túnel |
| Túnel com dois conectores | falha intermitente, difícil de diagnosticar | não rodar `cloudflared` no terminal com o serviço ativo |
| Conta expira antes do previsto | mensagens param de chegar | por isso a captura de payloads é o Dia 1 e 2, não o Dia 4 |

As armadilhas de console e de túnel estão em `AnotacoesPessoais/Beto/spike_twilio/STATUS.md`,
seção "Histórico". Vale reler antes do Dia 1: várias custaram horas.

## 7. O que fica decidido

- **A conta não será atualizada.** Consequência: `services/envio.py` e o modo `rest` seguem
  sem validação real, e o piloto com a Rita vai depender de um número novo (o chip pré-pago já
  decidido) com WABA próprio, onde essas restrições não valem.
- **A validação de assinatura fica sem exercício.** Os dois webhooks continuam públicos e sem
  autenticação. Enquanto `CANAL_SAIDA=simulado`, o risco é baixo; ao ligar um número real,
  isso vira item de segurança, não de conveniência.
