---
name: planejamento-semanal
description: Conduz a rotina semanal de planejamento do Beto para este repositório — 15 min de perguntas, 30 min de revisão do projeto, e como saída um plano para a janela de IA do dia e um plano de verificação manual para a semana. Use quando o Beto pedir "planejamento da semana", "vamos planejar", "nova janela", "rotina semanal", ou disser quanto tempo e quanta quota tem disponível.
---

# Planejamento semanal — AgenteAssistenteDeVendas

Rotina fixa do Beto, executada normalmente na sexta de manhã. A premissa que organiza tudo:
**a janela de IA é cara e curta; o tempo dele durante a semana é barato e fragmentado.** Então o
que exige IA concentra-se na janela, e o que exige julgamento humano vira roteiro para a semana.

## Estrutura da sessão

| Bloco | Duração | O que acontece |
|---|---|---|
| 1. Perguntas | até 15 min | Você pergunta, o Beto responde. Sem código. |
| 2. Revisão | 30 min | Você trabalha sozinho, **sem interromper**. Reconhecimento em paralelo. |
| 3. Execução | o que sobrar | Frentes em paralelo, commits por frente em `develop`. |

Confirme os horários reais no começo (`date`) e anuncie os três marcos. O Beto controla o relógio
pelo que você declarou.

## Bloco 1 — as perguntas

Antes de perguntar, leia `docs/auditoria_consistencia_2026-08.md` (a seção "0. Andamento" e o
roadmap) e `git log --since=<7 dias>`. Perguntar sem isso gera pergunta cuja resposta já estava
escrita, e queima o tempo dele.

Pergunte só o que **muda materialmente o plano**. As quatro que sempre valem:

1. **Meta da janela** — o que ele quer poder dizer no fim. Ofereça as frentes concretas que estão
   abertas hoje, não categorias genéricas.
2. **Paralelismo autorizado** — agressivo / moderado / sequencial. Isso define quantos subagentes.
3. **Risco autorizado** — só localizado / inclui migração de banco / inclui refactor transversal.
4. **Decisões técnicas pendentes** que estão bloqueando itens do roadmap. Traga a medição/evidência
   junto com a pergunta; ele decide rápido quando o trade-off está quantificado.

Depois, conforme as respostas: profundidade de cada frente, uso de dados reais de cliente
(sempre ofereça anonimizar — regra da FITec), e o que ele quer verificar manualmente na semana.

Use `AskUserQuestion`, no máximo 4 por chamada, 2 chamadas no total. Recomende uma opção.

## Bloco 2 — a revisão (30 min, sem interromper)

Dispare subagentes `Explore` em paralelo, um por frente escolhida, com uma instrução decisiva:
**reconhecimento, não implementação — não edite nada.** Peça sempre evidência `arquivo:linha`,
estimativa em minutos e sinalização explícita de onde o desenho não encaixa no código.

Um subagente por **conjunto de arquivos**, nunca por tema: duas frentes que tocam `backend/main.py`
são uma frente só, ou conflitam. Enquanto eles rodam, levante o que não depende deles: commits da
semana, tamanho do código, estado do banco (`alembic current`), suíte verde.

Verifique se achados marcados como abertos na auditoria já não foram resolvidos sem registro.

## Bloco 3 — a saída

Dois documentos, sempre:

1. **Plano da janela** — frentes paralelas com arquivos, quem executa (você ou subagente), duração,
   e o que é commit separado. Guarde em `artefatos/gerente_de_projetos/janelas/AAAA-MM-DD.md`.
2. **Plano da semana (seg-qui)** — um dia, uma atividade dele, cada uma com roteiro executável:
   comandos para copiar, o que observar, onde anotar o resultado. Termina com quinta = consolidar
   achados em lista de ideias para a próxima janela.

O plano da semana é para **ele**, não para você: comando literal, critério de julgamento explícito,
e um lugar para ele escrever o que achou. Nada de "verificar se está tudo certo".

## Regras que valem sempre nesta rotina

- **O maior uso de IA fica na janela.** Se uma tarefa pode ser feita por IA agora, não a adie para
  a semana — na semana ele tem tempo de julgar, não de esperar.
- **Commits por frente, suíte verde em cada um.** Uma frente ruim vira um revert.
- **Nunca dado real de cliente em arquivo versionado.** Anonimize nomes, telefones, CNPJ, valores.
- **Não reabra decisão registrada em memória.** Verifique `MEMORY.md` antes de propor algo que já
  foi decidido (chip pré-pago, D1/D2/D3 da pilha, etc.).
- Ao fim da janela, atualize a tabela "0. Andamento" da auditoria com o que foi resolvido.
