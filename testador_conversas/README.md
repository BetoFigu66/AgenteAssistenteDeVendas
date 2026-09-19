# Testador de Conversas

Sistema separado do backend (`../backend/`) que simula um usuário real mandando
mensagens WhatsApp para o assistente e verifica as respostas — dá segurança em
refactorings e novas implementações sem depender só de teste unitário.

## Como funciona

- Fala com o backend **só por HTTP**, como um cliente de fora falaria:
  `POST /webhook` (mesmo formato que o Twilio usa de verdade — form-encoded,
  `From`/`Body`) para mandar mensagem, `GET /api/mensagens/pendentes` para ver o
  que foi gerado quando a resposta não volta na hora (`SIMULACAO`/
  `CONVERSA_CONTROLADA`), `DELETE /api/dev/telefones/{telefone}` para limpar ao
  final. Não existe client REST do Twilio no backend hoje (gap conhecido, ver
  `CLAUDE.md`) — a "entrega ao cliente" em `EXECUCAO_NORMAL` é literalmente essa
  resposta HTTP síncrona, então não precisamos mockar o Twilio ainda.
- **Banco é a fonte da verdade** — schema `teste_conversas`, no mesmo Postgres
  do backend (`assistente_vendas`), mas em tabelas próprias. `cenarios`/`turnos`
  (o que enviar) e `respostas_aceitas` (o que é considerado válido — evolui por
  revisão humana) moram lá. Um script de exportação (`cli.py exportar`) tira uma
  fotografia em YAML por cenário, versionada no git como histórico/backup — não
  é a fonte de verdade, é só pra ter `git diff`/revisão de PR sobre as mudanças.
- **v1 sem LLM** — o backend real de teste deve rodar com `LLM_PROVIDER`
  desabilitado (`ProcessadorMensagem(llm=None)`, que já é o padrão sem
  configurar `GROQ_API_KEY`) para respostas serem 100% determinísticas.
  Personalização por LLM fica pra v2 (banco de variações aceitas, ou juiz por
  LLM pra equivalência semântica).
- **Não é 100% automático de propósito** — quando a resposta observada não bate
  com nenhuma já aceita para aquele turno, o CLI para e pergunta pra você
  aceitar ou rejeitar ali mesmo. Aceitar grava uma nova `RespostaAceita`.

## Setup (uma vez)

```bash
cd testador_conversas
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Cria o schema teste_conversas e as tabelas
python criar_schema.py

# Cria o usuário dedicado do testador no backend (única operação que toca o
# schema do backend direto — não existe endpoint HTTP pra criar o 1º usuário)
python bootstrap_usuario.py

# Cadastra alguns números de teste no pool
python cli.py numeros-adicionar 5511999900001

# Cenário de exemplo, só pra ter algo pra rodar de ponta a ponta
python seed_exemplo.py
```

Variáveis de ambiente (todas com default de dev, ver `config.py`):
`TESTADOR_DATABASE_URL`, `TESTADOR_BACKEND_BASE_URL`, `TESTADOR_LOGIN`, `TESTADOR_SENHA`.

## Uso

```bash
python cli.py cenarios-listar
python cli.py numeros-listar
python cli.py rodar saudacao_simples
python cli.py exportar               # todos os cenários
python cli.py exportar saudacao_simples
```
