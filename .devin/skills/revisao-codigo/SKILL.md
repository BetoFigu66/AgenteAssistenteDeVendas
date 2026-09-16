---
name: revisao-codigo
description: Faz a primeira passada de code review (correção, aderência às regras do projeto, diretrizes acumuladas do Beto, reuso/simplificação) sobre um arquivo, diff ou trecho de código deste repositório, antes da análise humana do Beto. Use sempre que o Beto pedir para "revisar", "dar uma olhada", "fazer code review", "analisar esse arquivo/diff/PR" ou colar um trecho de código pedindo avaliação — mesmo sem a palavra "revisão" explícita, se a intenção for avaliar qualidade/corretude de código antes de aprovar.
---

# Revisão de código — AgenteAssistenteDeVendas

Primeira passada de revisão, complementar ao skill nativo `code-review` (que atua sobre PRs do GitHub). Este skill é local ao repositório e carrega o contexto específico do projeto (CLAUDE.md/AGENTS.md) e as diretrizes que o Beto já validou em rodadas anteriores.

**Papel:** apontar achados para quem revisar. Nunca aprova, nunca decide "está pronto para merge" — isso é sempre decisão humana.

**Este é o arquivo-fonte.** Ele é espelhado automaticamente (hook `sync-skill-windsurf` em `.pre-commit-config.yaml`, script `scripts/sync_skill_windsurf.py`) para `.windsurf/skills/revisao-codigo/`, onde o Devin Desktop/Windsurf da Kika descobre o mesmo skill (formato "Agent Skills" — SKILL.md + frontmatter, sem adaptação). **Edite só aqui** (`.claude/skills/revisao-codigo/`) — o espelho é gerado no próximo commit que tocar esta pasta; editar o espelho direto se perde no próximo sync. Ver `docs/comandos_uteis.md` — seção "Skill de code review — sincronização com Windsurf".

## Antes de revisar

1. Leia `.claude/skills/revisao-codigo/diretrizes.md` — regras acumuladas de rodadas anteriores (D01, D02, ...). Elas têm prioridade sobre uma checklist genérica: refletem o que o Beto já validou como relevante para este projeto.
2. Se o alvo tocar áreas com regras explícitas no `CLAUDE.md`/`AGENTS.md` deste repo, releia a seção pertinente antes de avaliar:
   - pipeline do "cérebro" (`backend/services/processador.py`) e a ordem de camadas de resposta (Q&A → RAG → templates);
   - `backend/models/` — import sempre via `from models import X` (pacote), nunca do submódulo direto;
   - acesso a dados — sempre SQLAlchemy, nunca psycopg cru fora de `services/`; mudança de schema sempre via Alembic;
   - ordenação de rotas em `main.py` (estáticas antes de dinâmicas);
   - regras de negócio do agente: nunca prometer prazo (`PERGUNTAR_PRAZO`), nunca responder definitivamente sobre compatibilidade técnica, sempre escalar humano em reclamação/pedido explícito;
   - aprovação de mensagem de saída — **não é uma regra única**, são dois eixos ortogonais (ver `CLAUDE.md` § "Modos de execução e aprovação (REQ-011)"): `ModoExecucao` global (`SIMULACAO`/`CONVERSA_CONTROLADA` exigem aprovação humana; `EXECUCAO_NORMAL` se auto-aprova e envia sincronamente, sem humano) e `ModoOperacao` por atendimento (`HUMANO` suprime geração, independente do `ModoExecucao`). Achado de severidade alta é código que ignora esse cruzamento (ex.: enviar automaticamente em `SIMULACAO`/`CONVERSA_CONTROLADA`, ou gerar resposta com `ModoOperacao.HUMANO` ativo) — não simplesmente "pular aprovação".
   - envio real via WhatsApp — hoje só existe o caminho síncrono do webhook Twilio em `EXECUCAO_NORMAL`; não existe client Twilio REST (gap conhecido, REQ-011.11/REQ-008.5, "Fase 10" de `docs/plano_implementacao_requisitos_formais_2026-07.md`). Não reporte "mensagem aprovada/manual não é enviada ao cliente" como bug novo — é gap rastreado; só é achado se o código *fingir* que envia (ex.: marcar como entregue sem checar se `EXECUCAO_NORMAL`).
3. Identifique claramente o alvo (arquivo colado, diff, caminho de arquivo, branch/PR) antes de começar.

## Dimensões da revisão, nesta ordem

1. **Correção** — bugs reais introduzidos no trecho: `None`/`null` não tratado, off-by-one, condição de corrida, exceção engolida ou não tratada, contrato de função/API violado, mudança de comportamento não intencional.
2. **Aderência às regras do projeto** — específicas do CLAUDE.md/AGENTS.md (ver lista acima).
3. **Diretrizes acumuladas** — qualquer regra listada em `diretrizes.md`.
4. **Reuso / simplificação / eficiência** — só reportar quando o ganho é claro e concreto; é complementar, não o foco principal da revisão.

Não é escopo deste skill: nitpicks de estilo que o linter (`ruff`) já cobre, e problemas pré-existentes não introduzidos pelo trecho revisado — a menos que o trecho os agrave.

## Score de confiança

Para cada achado, atribua uma confiança de 0 a 100:
- **0** — não confiante, provável falso positivo.
- **25** — pode ser real, mas incerto.
- **50** — moderadamente confiante, real porém de impacto menor.
- **75** — bastante confiante, real e relevante.
- **100** — certeza absoluta.

Separe a saída em dois blocos:
- **Achados com confiança ≥70** — apresente primeiro, é o resultado principal.
- **Achados com confiança <70** — liste depois, rotulados "baixa confiança", sem inflar a contagem total do resumo.

Se descartar algo por parecer pedante, coberto por lint, ou pré-existente, diga o que descartou e por quê ao final — não descarte em silêncio.

## Formato de saída

- Se a tool `ReportFindings` estiver disponível na sessão e o contexto for compatível (revisão de diff/PR), use-a.
- Caso contrário, liste em texto: `arquivo:linha` — resumo do problema — cenário concreto que o dispara (input/estado → falha).
- Não inclua seção de "aprovado"/"pronto para merge"/conclusão de qualidade — isso é decisão do Beto.

## Depois da revisão — loop de aprendizado

Este skill evolui com o code review do Beto. Fluxo esperado:

1. Apresente sua análise primeiro, com o formato acima.
2. Espere a análise do Beto — ele vai confirmar, corrigir, apontar algo que você perdeu, ou dizer que um achado seu era falso positivo/irrelevante.
3. Quando o Beto validar explicitamente um critério (confirmar uma prioridade, corrigir um achado, apontar um padrão recorrente que deveria ter sido pego), registre em `diretrizes.md` seguindo o padrão D0X já usado no projeto (ver `AGENTS.md`): ID estável (nunca reciclado), categoria, data, regra, motivação, contexto de origem, aplicação prática (o que passa a ser permitido/proibido).
4. Nunca crie uma diretriz nova por conta própria sem o Beto ter validado o critério na conversa — o objetivo é capturar o julgamento dele, não inventar critério novo. **Vale também nas sessões do Windsurf (Kika):** ela pode rodar este skill e receber achados normalmente, mas uma diretriz nova só é registrada depois que o Beto validar — mesmo que a rodada tenha sido no Windsurf, não no Claude Code. Se o Beto não estiver na conversa, guarde o achado (ex.: como pendência) em vez de registrar diretriz sozinho.
5. Antes de registrar, confira se já não existe diretriz equivalente em `diretrizes.md` (evitar duplicação, mesma regra do AGENTS.md para os demais agentes).
