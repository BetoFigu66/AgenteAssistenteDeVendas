# Testador de Conversas

Sistema separado do backend (`../backend/`) que simula um usuário real mandando
mensagens WhatsApp para o assistente e verifica as respostas. Dá segurança em
refactorings e novas implementações sem depender só de teste unitário.

## Como funciona

- Fala com o backend **só por HTTP**, como um cliente de fora falaria:
  `POST /webhook` (mesmo formato que o Twilio usa de verdade, form-encoded,
  `From`/`Body`) para mandar mensagem, `GET /api/mensagens/pendentes` para ver o
  que foi gerado quando a resposta não volta na hora (`SIMULACAO`/
  `CONVERSA_CONTROLADA`), `DELETE /api/dev/telefones/{telefone}` para limpar ao
  final.
- **O testador é reconhecido como chamada local** porque não manda `AccountSid`
  (a Twilio sempre manda). É isso que faz o backend devolver o texto da resposta
  dentro do TwiML qualquer que seja o `CANAL_SAIDA`, e é assim que o testador lê
  a resposta. Entrega real hoje existe: `CANAL_SAIDA=twilio` mais
  `backend/services/envio.py` e `backend/services/canal/` (ver a seção "Canal de
  saída" do `CLAUDE.md`). Uma chamada nossa nunca vira entrega real: sem
  `AccountSid`, o backend trata como local.
- **Banco é a fonte da verdade**, schema `teste_conversas`, no mesmo Postgres do
  backend (`assistente_vendas`), mas em tabelas próprias. `cenarios`/`turnos`
  (o que enviar) e `respostas_aceitas` (o que é considerado válido, evolui por
  revisão humana) moram lá. O YAML em `cenarios_exportados/` é a fotografia
  versionada no git: `cli.py exportar` grava, `cli.py importar` restaura.
- **v1 sem LLM**: o backend de teste precisa rodar **sem `GROQ_API_KEY`**
  (`ProcessadorMensagem(llm=None)`, que já é o padrão quando a chave não está
  configurada) para as respostas serem 100% determinísticas. Com LLM ligado, a
  personalização muda o texto a cada rodada e toda resposta vira divergência.
  Personalização por LLM fica pra v2 (banco de variações aceitas, ou juiz por
  LLM pra equivalência semântica).
- **Não é 100% automático de propósito**: quando a resposta observada não bate
  com nenhuma já aceita para aquele turno, o CLI para e pergunta pra você
  aceitar ou rejeitar ali mesmo. Aceitar grava uma nova `RespostaAceita`.
  Para a primeira passada de uma bateria nova, em que *toda* resposta é
  desconhecida, existe `--nao-interativo`: rejeita e registra tudo sem
  perguntar, e serve de varredura ("quais cenários divergem"). A revisão humana
  fica para a segunda passada, cenário a cenário.

## Pré-requisitos no backend

1. **Schema do backend criado**: rodar `alembic upgrade head` (de `../backend/`,
   ou subir o backend uma vez, que ele aplica as migrações no lifespan) **antes**
   de `bootstrap_usuario.py`, que faz `SELECT ... FROM public.users`. Sem isso o
   bootstrap quebra com "relation users does not exist".
2. **`DEBUG=true` no `.env` do backend**: `DELETE /api/dev/telefones/{telefone}`,
   usado para limpar a conversa ao fim de cada cenário, responde 403 sem isso.
3. **Sem `GROQ_API_KEY`** (ver acima).
4. **`ModoExecucao.EXECUCAO_NORMAL`** é o caminho testado: a resposta volta
   dentro do TwiML, síncrona, e o testador a lê direto. Em `SIMULACAO`/
   `CONVERSA_CONTROLADA` o TwiML volta vazio e o testador cai no plano B,
   `GET /api/mensagens/pendentes`, que **não aprova nada**: as pendentes se
   acumulam no painel e você precisa limpá-las na mão depois. Funciona (o
   cliente pega sempre a pendente mais recente do telefone), mas suja o painel.
5. **Porta**: `TESTADOR_BACKEND_BASE_URL` tem default `http://localhost:8001`
   (backend em dev, `uvicorn --port 8001`). O ambiente docker/QA sobe na **8000**,
   então lá é `TESTADOR_BACKEND_BASE_URL=http://localhost:8000`.

## Setup (uma vez)

```bash
cd testador_conversas
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Cria o schema teste_conversas e as tabelas
python criar_schema.py

# Cria o usuário dedicado do testador no backend (única operação que toca o
# schema do backend direto, não existe endpoint HTTP pra criar o 1º usuário).
# Exige o `alembic upgrade head` do backend já aplicado.
python bootstrap_usuario.py

# Cadastra alguns números de teste no pool
python cli.py numeros-adicionar 5511999900001

# Carrega no banco todos os cenários versionados em cenarios_exportados/
python cli.py importar
```

`seed_exemplo.py` continua existindo, mas hoje é redundante: o cenário
`saudacao_simples` também está em `cenarios_exportados/`, então `cli.py importar`
já o traz.

Variáveis de ambiente (todas com default de dev, ver `config.py`):
`TESTADOR_DATABASE_URL`, `TESTADOR_BACKEND_BASE_URL`, `TESTADOR_LOGIN`,
`TESTADOR_SENHA`.

## Uso

```bash
python cli.py cenarios-listar
python cli.py numeros-listar

# Bateria inteira, sem perguntar nada: mostra o que divergiu e dá o placar
python cli.py rodar-todos --nao-interativo

# Revisão humana, cenário a cenário (aceita/rejeita cada resposta nova)
python cli.py rodar prazo_entrega_pergunta_direta

# Fotografa no YAML o que passou a ser aceito (é o que entra no commit)
python cli.py exportar
python cli.py exportar prazo_entrega_pergunta_direta
```

`rodar-todos` pega só os cenários **ativos**, em ordem alfabética. Cenário que
depende de rede externa, ou de uma correção que ainda não existe no backend,
nasce com `ativo: false` no YAML, de propósito. Hoje só
`cnpj_valido_mas_inexistente_na_receita` está nessa situação, porque consulta a
ReceitaWS de verdade e estouraria o limite do plano gratuito numa rodada em lote.

Quando a correção que travava um cenário entrar, **reative o cenário no mesmo
commit**: `mensagem_vazia_ou_so_midia` ficou quatro dias desligado depois de o
bug dele ter sido corrigido, e nesse intervalo a única cobertura ponta a ponta do
fix estava desativada, sem ninguém perceber.

### Importar / exportar

```bash
python cli.py importar                       # todo o cenarios_exportados/
python cli.py importar prazo_entrega_pergunta_direta
python cli.py importar caminho/para/arquivo.yaml
python cli.py importar --atualizar           # sobrescreve pelo YAML o que já existe
```

Sem `--atualizar`, cenário que já existe é **pulado** (a importação é idempotente,
pode rodar quantas vezes quiser). Com `--atualizar`, o cenário é sincronizado com
o YAML: os turnos são casados por `ordem` e alterados no lugar, em vez de apagados
e recriados, porque `resultados_turno` aponta para `turnos` e apagar um turno já
executado esbarraria na FK. Turno que sumiu do YAML é removido (e aí a FK pode
reclamar mesmo, o que é o aviso correto).

Atenção: `--atualizar` sincroniza também as `respostas_aceitas` do turno com o
que está no YAML. Exporte antes de importar por cima, ou perde o que foi aceito
desde a última exportação.

### Número travado

Se uma execução morrer no meio (backend fora do ar, Ctrl+C), o telefone fica em
`EM_USO` e nenhum cenário roda mais ("nenhum número livre no pool"). Para
devolver ao pool:

```bash
python cli.py numeros-liberar 5511999900001
python cli.py numeros-liberar 5511999900001 --sem-limpar   # backend fora do ar
```

## Os cenários da bateria

Os arquivos em `cenarios_exportados/` são derivados de uma conversa real, com
**todos os dados trocados por fictícios** (nome, telefone, CNPJ, CPF, endereço).
Nenhum dado real de cliente entra aqui.

Eles nascem com `respostas_aceitas: []`: ninguém sabe ainda qual resposta é
aceitável, quem decide é o humano na revisão interativa. O critério de
julgamento de cada turno está no campo `observacoes`, no formato:

```
PRECISA: ... | NÃO PODE: ... | exercita: <regra ou REQ>
```

É isso que você lê na hora de aceitar ou rejeitar uma resposta.
