# Regras do Projeto - Assistente de Vendas Inforrel

## Contexto

Este projeto e um sistema de automacao de atendimento via WhatsApp usando IA para a empresa Inforrel, com foco em venda de catracas, relogios de ponto e controle de acesso.

## Estrutura

- `backend/`: API FastAPI, SQLAlchemy, Alembic e PostgreSQL.
- `frontend/`: React, Vite e TailwindCSS.
- `agentes/`: agentes auxiliares criados para desenvolvimento.
- `artefatos/`: documentacao, requisitos e decisoes arquiteturais.
- `docs/comandos_uteis.md`: dicas, comandos e pequenas solucoes recorrentes.

## Regras de Trabalho

- Manter documentacao em portugues.
- Ao criar codigo Python, preferir SQLAlchemy e os padroes existentes do backend.
- Ao criar migrations, usar Alembic.
- Ao mexer no frontend, seguir os componentes e cores ja usados no projeto.
- Nunca prometer prazo de entrega em respostas do agente.
- Para compatibilidade com sistemas de terceiros, orientar validacao tecnica.
- Escalar para humano quando o cliente pedir atendimento humano ou quando a resposta nao for segura.

## Comandos Uteis

Sempre consulte `docs/comandos_uteis.md` antes de sugerir comandos, atalhos ou dicas operacionais.

Quando o usuario fizer uma pergunta do tipo "como configurar", "como fazer", "qual comando", "qual atalho", ou pedir uma dica operacional reutilizavel, responda normalmente e tambem atualize `docs/comandos_uteis.md` com a dica, quando ela ainda nao estiver registrada.

Exemplos de conteudo que deve ser registrado:

- atalhos de VSCode/Windsurf;
- comandos de Git, Docker, PowerShell, backend ou frontend;
- procedimentos de ambiente;
- dicas de debug recorrentes;
- pequenas configuracoes de IDE.

Evite duplicar entradas. Se uma dica parecida ja existir, apenas melhore a entrada existente.
