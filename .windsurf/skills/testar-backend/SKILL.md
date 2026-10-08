---
name: testar-backend
description: Testa o backend ponta a ponta como um cliente de WhatsApp faria, usando o testador de conversas. Cria cenários novos a partir da base de conhecimento crua (docs/FoldersProdutos) e dos requisitos formais, roda a bateria contra um backend dedicado sem LLM, julga cada resposta pelo critério do turno, propõe as aceitáveis como respostas aceitas (pendentes de aprovação do Beto ou da Kika) e, nas inaceitáveis, faz análise de causa raiz e corrige ou registra pendência. Use quando o Beto pedir "testar o backend", "rodar a bateria", "criar cenários de teste", "achar bugs de conversa" ou der uma janela de quota para teste exploratório.
---

# Testar o backend (testador de conversas + julgamento)

Este skill orquestra o `testador_conversas/` (leia o `README.md` dele uma vez por sessão). O testador fala com o backend só por HTTP (`POST /webhook`), grava o que observou em `resultados_turno` e compara com `respostas_aceitas`. Quem julga aqui é o Claude, mas **o Claude não aprova**: o que ele acha aceitável vira **proposta** (resposta aceita inativa, `criado_por = proposta_claude`), que só passa a valer quando o Beto ou a Kika aprovam (regra 2 da FITec: humano no comando).

## 0. Ritmo e quota

O Beto costuma dar um teto de quota por hora da janela (ex.: 20% por hora, cumulativo). Antes de cada cenário novo, consultar `python3 scripts/claude_quota.py --csv` (coluna `five_hour_pct`). Ao atingir o teto da hora, parar num ponto limpo (cenário terminado, nada sem commit pela metade), registrar o progresso no arquivo da janela e agendar a retomada (`ScheduleWakeup`) para o início da próxima hora. Mensagens de andamento com o prefixo `dd/MM HH:MM (X%):`.

## 1. Backend dedicado à bateria

Nunca usar o backend da 8001 (é o de dev do Beto, com `--reload` e LLM ligado) nem o da 8000 (Docker, pode estar em teste real). Subir um próprio, em background, na **8002**:

```bash
cd backend && source venv/bin/activate && \
LLM_API_KEY= CANAL_SAIDA=simulado TWILIO_CAPTURAR_PAYLOADS=false DEBUG=true \
DATABASE_URL=postgresql://inforrel:inforrel_dev@localhost:5433/assistente_vendas \
exec uvicorn main:app --host 0.0.0.0 --port 8002 > <scratchpad>/backend8002.log 2>&1
```

- Sem LLM, de propósito: a resposta fica determinística e pode virar resposta aceita.
- Sem `--reload`: depois de corrigir código, **reiniciar** o processo da 8002 antes de rodar de novo.
- O `ModoExecucao` é global (tabela `parametros`): só ler (`GET /api/config/execucao`), nunca alterar. O caminho testado é `execucao_normal`.
- Testador apontado para ela: `export TESTADOR_BACKEND_BASE_URL=http://localhost:8002`, venv em `testador_conversas/venv`.
- Ao terminar a sessão, derrubar a 8002.

## 2. Criar cenários

Fontes, nesta ordem:

1. **Base crua de produtos**: `docs/FoldersProdutos/*.txt` (texto extraído dos folders). Daqui saem perguntas realistas de cliente sobre produto (capacidade, tecnologia de leitura, modelos, Portaria 671, integração), sem copiar a resposta do folder para o critério: o critério diz o que a resposta **precisa conter** e o que **não pode** afirmar.
2. **Requisitos formais**: `artefatos/requisitos_formais/REQ-*.md`. Cada cenário exercita um ou mais itens (ex.: REQ-002.1 roteamento, REQ-004 escalonamento, REQ-015 CPF).
3. **Regras de negócio do `CLAUDE.md`**: nunca prometer prazo, compatibilidade sempre para validação técnica, escalar humano em pedido explícito/reclamação, CNPJ/CPF pedido no início junto com o nome.
4. Conversa real de referência (`docs/ConversaDoWhatsApp_1/`) só como inspiração de estilo; **nunca** copiar dado real. Todo nome, telefone, CNPJ e CPF é fictício (CNPJ/CPF com dígito válido quando o cenário precisar de validação, gerado na hora).

Antes de criar, listar os existentes (`cli.py cenarios-listar`) e não duplicar o que já é coberto. Cada cenário é um YAML em `testador_conversas/cenarios_exportados/<nome>.yaml`, no formato dos existentes, com `respostas_aceitas: []` e `observacoes` no padrão:

```
PRECISA: ... | NÃO PODE: ... | exercita: <regra ou REQ>
```

Cenário que depende de rede externa (ReceitaWS de CNPJ real) nasce com `ativo: false`. Importar com `python cli.py importar <nome>`.

Priorizar cenários curtos (2 a 4 turnos) e de alto valor: o que, se errado, faria o bot prometer algo, dar informação falsa de produto, travar o fluxo ou ignorar um pedido de humano.

## 3. Rodar e julgar

```bash
python cli.py rodar <cenario> --nao-interativo   # grava tudo em resultados_turno
python cli.py execucao-mostrar <cenario>         # critério + enviado + observado, por resultado
```

Para cada turno, julgar a resposta observada contra o critério do turno **e** contra o contexto (folder do produto, REQ citado). Três desfechos:

- **Aceitável** → `python cli.py propor <resultado_id>`. Aceitável é "um vendedor da Inforrel mandaria isso", não "perfeito". Redação diferente do ideal mas correta é aceitável.
- **Inaceitável** → seção 4.
- **Duvidoso** (o critério não decide, ou depende de preferência do negócio) → não propor; anotar como pendência de decisão com a pergunta objetiva.

Turnos posteriores a um turno errado costumam herdar o erro: julgar cada um pelo que ele mesmo devia fazer, sem propor uma resposta que só "parece certa" por acaso.

## 4. Resposta inaceitável: causa raiz

1. Achar o `ProcessamentoMensagem` da mensagem (intenção, confiança, entidades, trilha QA/RAG, template) pelo telefone de teste e horário; é a fonte da verdade do "por que o bot respondeu X".
2. Reproduzir o mínimo (teste unitário em `backend/tests/` quando der) e localizar a causa no código: classificador, motor (`services/conversacao/`), pilha de perguntas, templates, QA/RAG.
3. Decidir se a correção **precisa de decisão do Beto**. Precisa quando: muda regra de negócio ou texto comercial sensível (preço, prazo, garantia, promessa), contradiz requisito escrito, tem mais de um caminho com consequência relevante, ou mexe em contrato entre módulos. Não precisa quando é bug claro com uma correção óbvia e local.
4. Sem decisão necessária: corrigir, rodar `pytest` (do `backend/`) e `ruff check .`, reiniciar a 8002, rodar o cenário de novo, propor as respostas que ficaram aceitáveis. Commit direto em `develop` (sem branch), com `python scripts/versao.py atualizar` antes, mensagem em português, um commit por correção.
5. Com decisão necessária: não corrigir; registrar a pendência (seção 5).

## 5. Registro

Um arquivo por sessão em `artefatos/qa/AAAA-MM-DD_testar_backend.md`, um parágrafo por linha (sem quebra manual), com:

- cenários criados (nome, o que exercita, fonte);
- placar por cenário (turnos propostos / inaceitáveis / duvidosos);
- cada falha: sintoma, causa raiz (arquivo:linha), e "corrigido em <commit>" ou "pendência";
- **pendências de decisão**, cada uma com a pergunta objetiva e as opções com consequência;
- comandos para o humano aprovar: `python cli.py propostas-listar`, `propostas-aprovar <ids> --por beto|kika`, `propostas-descartar <ids>`.

Ao fim: `python cli.py exportar` (os YAML com as propostas entram no commit, o que dá diff legível do que foi proposto), atualizar o `artefatos/gerente_de_projetos/Beto.md` com os commits não revistos e as pendências, e derrubar a 8002.
