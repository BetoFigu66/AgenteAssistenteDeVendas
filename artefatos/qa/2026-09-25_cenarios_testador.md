# Bateria do testador de conversas na branch `janela/2026-09-25`

<!-- CLASSIFICACAO: ANDAMENTO -->

> **Agente:** [qa]
> **Data:** 2026-09-25
> **Branch:** `janela/2026-09-25` (HEAD `59b21a4`), comparada com `develop` (`612fe4d`)
> **Escopo:** rodar os 16 cenários ativos em `--nao-interativo` contra um backend
> separado, checar as regras de negócio do `CLAUDE.md` e ver se algo mudou por causa
> desta branch. Nenhuma resposta foi aceita: aceitar é decisão do Beto.

---

## Resumo

- **16 cenários ativos rodados, 1 passou (`saudacao_simples`), 15 divergiram.** A
  divergência é quase toda "esperada" no sentido do testador: só `saudacao_simples`
  tem resposta aceita no banco (`respostas_aceitas` vazias em todos os outros). Então
  "divergiu" aqui quer dizer "ninguém aceitou ainda", e o julgamento real é contra o
  campo `observacoes` de cada turno (feito abaixo).
- **Nenhuma regressão desta branch.** A mesma bateria rodada contra `develop` (backend
  na 8002, worktree temporário) deu respostas **idênticas turno a turno** (diff vazio
  nos 16 cenários).
- **Idempotência por `MessageSid`: sem risco para o testador.** `cliente_backend.py`
  manda só `From` e `Body` (nem `MessageSid`, nem `AccountSid`, nem `ProfileName`), e
  `_mensagem_ja_recebida` retorna `False` quando o SID vem vazio. Nenhum turno é
  descartado. Pelo mesmo motivo o nome de perfil e os marcadores de
  documento/localização não entram em nenhum cenário atual.
- **Regra de negócio violada de forma direta: nenhuma** (nenhum prazo prometido, nenhuma
  compatibilidade afirmada, nenhum preço citado). Mas **duas das três regras não chegam
  a ser exercitadas** pelos cenários que existem para elas, e a de reclamação falha em
  detectar a reclamação (detalhes na seção "Regras de negócio").

## Como foi rodado

| Item | Valor |
|---|---|
| Backend da branch | nativo WSL, `backend/`, `uvicorn main:app --port 8001`, sem `--reload` |
| Backend de `develop` | worktree em `/tmp/claude-1000/wt-develop`, porta 8002, mesmo venv e mesmas variáveis (removido ao fim) |
| Variáveis sobrescritas | `LLM_API_KEY=` (vazio), `CANAL_SAIDA=simulado`, `TWILIO_CAPTURAR_PAYLOADS=false`, `DEBUG=true`, `DATABASE_URL=postgresql://...@localhost:5433/assistente_vendas` |
| `ModoExecucao` | `execucao_normal` (lido, não alterado) |
| Backend Docker 8000 | não usado; continua `healthy`, `canal_saida=twilio` |

Código testado: o `59b21a4` limpo. Durante a sessão apareceram alterações não
commitadas em `backend/main.py`, `services/canal/captura_midia.py` e testes (feitas por
outra frente de trabalho, não por esta), mas com horário posterior à subida do backend
da 8001 (18:40), que roda sem `--reload`. Elas **não** entraram nesta bateria.

Dois ajustes em relação ao roteiro original, para registro:

1. **A variável que desliga o LLM é `LLM_API_KEY`, não `GROQ_API_KEY`.** `config.py` só
   conhece `LLM_API_KEY`; `GroqProvider` levanta `ValueError` com chave vazia e o
   lifespan cai para `ProcessadorMensagem(llm=None)`. Confirmado por `get_llm_provider()`
   com o mesmo ambiente ("Groq API key não configurada") e pela auditoria: nenhum
   `processamentos_mensagem` desta rodada tem `personalizado_via_llm`. O README do
   testador fala em `GROQ_API_KEY` e está desatualizado nesse ponto.
2. **Driver do banco: `postgresql://` (psycopg2), não `postgresql+psycopg://`.** O
   default de `config.py` usa `psycopg` (v3), que não está instalado no
   `backend/venv` (só `psycopg2-binary`, como no `requirements.txt`); a primeira
   tentativa de subida quebrou com `No module named 'psycopg'`. O `.env` já usa
   `postgresql://`. O default de `config.py` só funciona no container.

Observação de ambiente: depois do `alembic upgrade head` no lifespan, os logs do backend
somem (o `fileConfig` do Alembic desliga os loggers existentes), inclusive a linha "LLM
Provider inicializado"/"LLM não disponível". Por isso a confirmação do LLM desligado foi
feita por fora, como descrito acima.

## Resultado por cenário

Critério: `PRECISA` / `NÃO PODE` do campo `observacoes`. "Atende" = a resposta observada
cumpre o critério e poderia ser aceita; "Não atende" = viola o critério.

| Cenário | Placar do testador | Contra `observacoes` |
|---|---|---|
| `saudacao_simples` | ok | atende |
| `cnpj_sem_pontuacao_com_nome_junto` | 3 div. | T1, T2 atendem; T3 não |
| `compatibilidade_software_terceiro` | 3 div. | T1 parcial; T2, T3 não |
| `cortesia_isolada_sem_conteudo` | 4 div. | T1 parcial; T2, T3, T4 não |
| `cpf_pessoa_fisica_e_data_nascimento` | 3 div. | nenhum turno atende |
| `faixa_funcionarios_vira_quantidade` | 2 div. | não atende |
| `fora_de_contexto_e_retomada` | 3 div. | nenhum turno atende |
| `instalacao_e_endereco_sem_campo` | 3 div. | não atende (escala no T1) |
| `leva_para_diretoria_nao_e_aprovacao` | 3 div. | não atende (escala no T1) |
| `mensagens_quebradas_em_rajada` | 5 div. | T1 atende; resto não |
| `mudanca_de_produto_no_meio` | 4 div. | nenhum turno atende |
| `pedido_humano_no_meio_do_fluxo` | 3 div. | T1 parcial; T2, T3 atendem |
| `prazo_entrega_pergunta_direta` | 4 div. | T1 atende; T2 sem violação mas pelo motivo errado; T3, T4 vazios |
| `preco_direto_sem_identificacao` | 3 div. | sem violação de preço, mas pergunta do produto errado |
| `reclamacao_atraso_pos_venda` | 3 div. | não atende (reclamação não detectada) |
| `respostas_numeradas_multiplas_em_uma_mensagem` | 3 div. | T1 atende; T2, T3 não |

Inativos e não rodados: `cnpj_valido_mas_inexistente_na_receita` (de propósito, rede
externa) e `mensagem_vazia_ou_so_midia` (ver "Achados de processo").

### Divergências, turno a turno

A intenção, o template e o motivo vêm de `processamentos_mensagem`, obtidos numa
sondagem à parte (telefone fictício `5511999900097`, limpo ao fim) com as mesmas
mensagens. A "aceita mais próxima" não existe em nenhum turno abaixo, porque não há
resposta aceita fora de `saudacao_simples`.

**`cnpj_sem_pontuacao_com_nome_junto`**
- T2 `sou a Ana, meu cnpj é 11222333000181` → "Confirmei os dados da empresa *CAIXA
  ESCOLAR DA ESCOLA ESTADUAL ... JOSEFINA JACQUES NORONHA*". Nome e CNPJ extraídos
  (atende). Porém o CNPJ **não é fictício na prática**: 11.222.333/0001-81 existe na
  Receita e a consulta à ReceitaWS acontece a cada rodada em lote (o próprio cenário
  diz que "provavelmente não será encontrado").
- T3 `isso mesmo` → NAO_ENTENDI. Intenção `confirmar` detectada, mas nenhuma ação trata
  confirmação nesse ponto ("Nenhuma ação do motor, QA ou escalonamento respondeu").

**`compatibilidade_software_terceiro`**
- T1 `vocês têm relógio de ponto que funciona com o Domínio?` → `RAG_PEDIR_CLARIFICACAO`
  ("Não tenho certeza se consigo te responder... Pode me explicar com outras palavras").
  Não afirma nem nega (sem violação), mas **não defere para validação técnica**:
  `software_ponto='Domínio'` é extraído e não há ação de compatibilidade.
- T2 `então funciona ou não funciona?` → classificado como `reclamar` (falso positivo),
  resposta "Lamento pelo inconveniente! Vou escalar... Tudo bem! Qualquer coisa é só
  chamar por aqui. Até mais! 👋" (`RECLAMACAO_ESCALADA+DESPEDIDA_ATENDIMENTO_ENCERRADO`).
  O atendimento fica **ENCERRADO e em HUMANO** na mesma mensagem: escala e se despede
  ao mesmo tempo.
- T3 `o fornecedor disse que qualquer REP serve, confirma?` → "Vi que você já conversou
  conosco antes... 1) Continuar 2) Novo pedido". Consequência do encerramento no T2.

**`cortesia_isolada_sem_conteudo`**
- T1 `Bom dia! Tudo bem e você?` → saudação de contato novo, sem responder à cortesia
  (parcial).
- T2 `Sim, é verdade` → NAO_ENTENDI (1ª ocorrência).
- T3 `Eu quem agradeço` → `ESCALADO_BAIXA_CONFIANCA` (2ª baixa confiança, REQ-004.9),
  modo HUMANO.
- T4 `Obrigada! Bom dia` → vazio (HUMANO suprime a geração).
  Cortesia pura escala para humano em duas mensagens.

**`cpf_pessoa_fisica_e_data_nascimento`**
- T1 `oi, não tenho empresa, sou pessoa física` → "Claro! Vou passar sua solicitação para
  um de nossos atendentes" (`ESCALADO_HUMANO`, intenções `saudacao`+`escalar_humano`).
  **Falso positivo de pedido de humano**; o fluxo PF nem começa.
- T2 (CPF válido) e T3 (data) → vazios, por causa do modo HUMANO.

**`faixa_funcionarios_vira_quantidade`**
- T1 `quero 2 relógios de ponto para 45 funcionários` → `PROJETO_COMPLEXO_ESCALADO`.
  Entidades: `quantidades=[2, 45]`, `faixa_funcionarios=45`. O 45 entra **nas duas**
  listas e o gatilho de REQ-004.8 dispara por `quantidade >= 4`, que é justamente o
  "NÃO PODE: tratar 45 como unidades" do cenário.
- T2 → vazio (HUMANO).

**`fora_de_contexto_e_retomada`**
- T1 `vocês vendem câmera de segurança?` → "Sim, vendemos. Trabalhamos com a marca
  Intelbras de câmera... Qual a faixa de pessoas que vão usar a câmera?"
  (`DISPONIBILIDADE_PRODUTO`, `tipos_produto=['camera']`). Viola "NÃO PODE: inventar
  catálogo", **se** a Inforrel de fato não vende câmera. Vem de template, não de LLM:
  vale o Beto confirmar se câmera está no catálogo.
- T2 `e qual o horário de vocês?` → repete "Qual a faixa de pessoas...". Não inventa
  horário (sem violação), mas ignora a pergunta.
- T3 `ok, então me manda orçamento de catraca` → repete a mesma pergunta da câmera.
  Não retoma.

**`instalacao_e_endereco_sem_campo`** e **`leva_para_diretoria_nao_e_aprovacao`**
- T1 com "relógio de ponto facial" → `PROJETO_COMPLEXO_ESCALADO` pelo gatilho
  `tipo_leitor_mencionado == 'facial'` (REQ-004.8). T2 e T3 vazios.
  O comportamento segue a regra como está escrita no código, mas os dois cenários
  deixam de testar o que dizem testar (campo de instalação, orçamento em aberto).

**`mensagens_quebradas_em_rajada`**
- T2 `tudo bem?` → NAO_ENTENDI; T3 `é o seguinte` → `ESCALADO_BAIXA_CONFIANCA`; T4 e T5
  vazios. Mesmo padrão da cortesia: duas mensagens sem conteúdo escalam.

**`mudanca_de_produto_no_meio`**
- T1 `preciso de relógio de ponto` → `RAG_PEDIR_CLARIFICACAO` ("Pode me explicar com
  outras palavras..."). Produto reconhecido (`relogio_ponto`), mas cai no RAG em vez de
  iniciar a coleta.
- T2 `biometria` → pede nome e CNPJ/CPF.
- T3 `...o que eu preciso é catraca` → "Ainda não encontrei uma resposta segura...
  Vou te transferir" (escala). T4 vazio.

**`pedido_humano_no_meio_do_fluxo`**
- T1 `quero orçamento de catraca` → "O **relógio** seria cartográfico ou eletrônico?"
  (`PEDIR_MODELO`) com `tipos_produto=['catraca']`. Pergunta de relógio para quem pediu
  catraca.
- T2 `prefiro falar com um vendedor` → `ESCALADO_HUMANO`, modo HUMANO (atende).
- T3 → vazio (atende: é o esperado com modo HUMANO).

**`prazo_entrega_pergunta_direta`**
- T2 `qual o prazo de entrega do relógio de ponto facial?` → `PROJETO_COMPLEXO_ESCALADO`.
  A intenção `perguntar_prazo` é detectada, mas o gatilho "facial" é `exclusivo` e vence.
  Não promete prazo, mas o template de prazo nunca é exercitado.
- T3, T4 → vazios (HUMANO).

**`preco_direto_sem_identificacao`**
- T1 `quanto custa a catraca de balcão?` → saudação + "Vou precisar de algumas
  informações para montar o orçamento. O relógio seria cartográfico ou eletrônico?".
  Não cita preço e puxa para orçamento (o que o cenário pede), mas com a pergunta de
  relógio para catraca.
- T2, T3 → repetem a mesma pergunta; não reconhecem a insistência por preço.

**`reclamacao_atraso_pos_venda`**
- T1 `comprei um relógio semana passada e não chegou` → intenção `desconhecido`, resposta
  de saudação pedindo CNPJ/CPF (viola "NÃO PODE: pedir CNPJ").
- T2 `isso é um absurdo, ninguém me responde` → `desconhecido`, NAO_ENTENDI.
- T3 `quero cancelar` → `ESCALADO_BAIXA_CONFIANCA` (escala por baixa confiança, e
  `tipos_produto=['cancela']`: "cancelar" virou o produto cancela).
  Termina em humano, mas por acidente, não por `RECLAMAR`.

**`respostas_numeradas_multiplas_em_uma_mensagem`**
- T2 `Bom dia! Tudo bem e você?` → NAO_ENTENDI.
- T3 (lista numerada) → `PROJETO_COMPLEXO_ESCALADO`. `quantidades=[1, 2, 3, 20, 25]`:
  os números da enumeração "1) 2) 3)" viram quantidades e o 25 também; o gatilho
  `quantidade >= 4` dispara.

## Regras de negócio do `CLAUDE.md`

| Regra | Resultado |
|---|---|
| Nunca prometer prazo | **Sem violação**, mas **não exercitada**: o único cenário de prazo menciona "facial" e escala antes de chegar ao template `PERGUNTAR_PRAZO`. Sugestão: tirar "facial" da mensagem do T2, ou criar uma variante sem gatilho de projeto complexo. |
| Compatibilidade vai para validação técnica | **Sem violação** (não afirma nem nega), mas **não atende**: T1 pede reformulação em vez de deferir para a equipe técnica, T2 vira falsa reclamação e encerra o atendimento. |
| Escalar quando pede humano | **Atende** (`pedido_humano_no_meio_do_fluxo` T2, modo HUMANO confirmado e geração suprimida no T3). Falso positivo em "não tenho empresa, sou pessoa física". |
| Escalar em reclamação | **Não atende**: as duas reclamações do cenário próprio saem `desconhecido`. A escalada acontece por baixa confiança no 3º turno. E "então funciona ou não funciona?" é tomado como reclamação. |

## Correlação com as mudanças desta branch

`git diff develop..HEAD` toca `main.py` (idempotência por `MessageSid`, `MessageType`
para documento/localização), `processador.py`, `identificador.py`,
`conversacao/acoes.py`, `regras_globais.py`, `regras_esclarecendo.py`,
`estados/esclarecendo.py` e `utils/nome_perfil.py`.

- **Nome de perfil:** o testador não manda `ProfileName`; nos caminhos alterados de
  `regras_globais.py` o `nome_perfil` fica `None` e o comportamento cai no anterior.
  Confirmado empiricamente: T2 de `cnpj_sem_pontuacao_com_nome_junto` (que passa por
  `nome_para_contato()`) sai igual em `develop`.
- **Documento/localização:** dependem de `MessageType`/`NumMedia`, que o testador não
  manda. Sem efeito.
- **Idempotência:** sem `MessageSid`, nunca barra. Sem efeito.
- **Comparação direta com `develop`:** as 50 respostas (16 cenários) são idênticas.

Contra a rodada anterior gravada no banco (19/09, execuções 5 a 20), mudaram só três
cenários (`cortesia_isolada_sem_conteudo`, `mensagens_quebradas_em_rajada`,
`reclamacao_atraso_pos_venda`): em 19/09 eles respondiam "Desculpe, tive um problema ao
processar sua mensagem", o erro corrigido depois em `a94e996` (rótulo de auditoria
estourando a coluna). Hoje respondem NAO_ENTENDI e escalam. É mudança de `develop`
anterior a esta branch, não regressão.

**Conclusão: todas as divergências são pré-existentes.**

## Achados de processo (testador)

1. **`mensagem_vazia_ou_so_midia` está inativo no banco e ativo no YAML.** O commit
   `59d37e5` (23/09) reativou o cenário no YAML, mas o banco não foi reimportado com
   `--atualizar`, então `rodar-todos` continua pulando o cenário. Justamente o caso que
   o README cita como exemplo de cobertura desligada sem ninguém perceber.
2. **`execucoes.iniciado_em` tem default congelado.** Todas as 52 execuções marcam
   `2026-08-21 13:51:20`. Em `testador_conversas/models.py` os
   `server_default="now()"` são string: o SQLAlchemy emite `DEFAULT 'now()'`, que o
   Postgres avalia uma vez na criação da tabela. O mesmo vale para os outros `criado_em`
   e `atualizado_em` do schema. Correção seria `server_default=text("now()")` ou
   `func.now()` e um `ALTER ... SET DEFAULT now()` no banco existente.
3. **README do testador:** trocar `GROQ_API_KEY` por `LLM_API_KEY`, e mencionar que o
   backend nativo precisa de `DATABASE_URL=postgresql://...` (psycopg2).
4. **CNPJ "fictício" é real:** `11222333000181` retorna uma escola da Receita e bate na
   ReceitaWS em toda rodada em lote, o que o README tenta evitar ao desligar
   `cnpj_valido_mas_inexistente_na_receita`.

## Para o Beto decidir

**Aceitar (critério atendido, ficam como referência para detectar regressão):**
- `cnpj_sem_pontuacao_com_nome_junto` T1 e T2 (T2 condicionado a manter esse CNPJ, ver
  achado 4).
- `mensagens_quebradas_em_rajada` T1, `prazo_entrega_pergunta_direta` T1,
  `respostas_numeradas_multiplas_em_uma_mensagem` T1 (saudação de contato novo, igual à
  já aceita em `saudacao_simples`).
- `pedido_humano_no_meio_do_fluxo` T2 e T3 (T3 vazio é o esperado).

**Rejeitar (violam o critério do cenário):** todos os demais turnos, em especial os de
`reclamacao_atraso_pos_venda`, `cpf_pessoa_fisica_e_data_nascimento`,
`compatibilidade_software_terceiro` T2/T3 e `faixa_funcionarios_vira_quantidade`.

**Precisa de decisão de negócio antes de aceitar ou rejeitar:**
- `fora_de_contexto_e_retomada` T1: a Inforrel vende câmera Intelbras? Se não, é
  alucinação de catálogo vinda de template.
- `prazo_entrega_pergunta_direta` T2 e os cenários com "facial": o gatilho REQ-004.8
  "leitor facial é sempre projeto complexo" está certo como regra? Se estiver, os
  cenários precisam de outra redação para testar o que dizem testar; se não, é o código.
- Duas mensagens de cortesia seguidas escalarem para humano (REQ-004.9) é aceitável?

**Bugs de produto sugeridos para registro** (não corrigidos aqui):
- Número de funcionários entra também em `quantidades` e dispara projeto complexo; a
  enumeração "1) 2) 3)" também vira quantidade.
- `PEDIR_MODELO` pergunta sobre relógio quando o produto é catraca.
- Reclamação de pós-venda não é classificada como `RECLAMAR`; "funciona ou não
  funciona?" é, e ainda encerra o atendimento junto com a escalada.
- "não tenho empresa, sou pessoa física" classificado como pedido de humano.
- Pergunta de compatibilidade com `software_ponto` extraído não vai para validação
  técnica.
