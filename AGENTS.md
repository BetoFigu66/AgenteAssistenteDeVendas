# Regras do Projeto - Assistente de Vendas via WhatsApp com IA

## Contexto

Este projeto e um sistema de automacao de atendimento via WhatsApp usando IA para a empresa Inforrel, com foco em venda de catracas, relogios de ponto e controle de acesso.

## Estrutura

- `backend/`: API FastAPI, SQLAlchemy, Alembic e PostgreSQL.
- `frontend/`: React, Vite e TailwindCSS.
- `agentes/`: agentes auxiliares criados para desenvolvimento.
- `artefatos/`: documentacao, requisitos e decisoes arquiteturais.
- `docs/comandos_uteis.md`: dicas, comandos e pequenas solucoes recorrentes.
- `AnotacoesPessoais/`: area pessoal de cada colaborador para rascunhos, mensagens de teste, planilhas e imagens. Conteudo nao e versionado (gitignore), apenas o `README.md` interno. Nao colocar dados reais de cliente nem segredos.

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

## Selecao de Agente por Pedido

O projeto tem varios agentes especializados em `agentes/` (cada um com seu proprio papel, estilo e diretorio de artefatos). No chat, usamos a convencao `[nome]` no inicio da mensagem para indicar qual agente deve tratar o pedido.

### Nomes validos

| Prefixo | Agente | Arquivo | Diretorio de artefatos | Responsabilidade principal |
|---------|--------|---------|------------------------|----------------------------|
| `[analista]` | Analista de Requisitos | `agentes/analista_requisitos.py` | `artefatos/analista_de_requisitos/` | Requisitos, historias de usuario, questionarios, entrevistas com cliente |
| `[auxiliar]` | Auxiliar de Negocios | `agentes/auxiliar_negocios.py` | `artefatos/auxiliar_negocios/` | MVP, roadmap, ideias de produto, analise de mercado |
| `[arquiteto]` | Arquiteto de Sistemas | `agentes/arquiteto_sistemas.py` | `artefatos/arquiteto_de_sistemas/` | Decisoes arquiteturais (ADRs), diagramas, politica de branches, deploy |
| `[planejador]` | Planejador de Negocios | `agentes/planejador_negocios.py` | `artefatos/planejador_negocios/` | Precificacao, marketing, concorrencia, projecoes financeiras |
| `[qa]` | QA Engineer | `agentes/qa_engineer.py` | `artefatos/qa/` | Testes, cobertura, revisao de PRs, qualidade de processo |
| `[implementador]` | Implementador | `agentes/implementador.py` | `artefatos/implementador/` | Codificacao de backend/frontend, migrations, fixes, diretrizes de implementacao |
| `[gerente]` | Gerente de Projetos | `agentes/gerente_de_projetos.py` | `artefatos/gerente_de_projetos/` | Coordenacao, relatorios de sprint, acompanhamento de pendencias, atas |

### Como usar

```
[arquiteto] avalie se vale migrar para event-driven
[qa] revise o PR #42 e aponte riscos
[implementador] corrija o bug BUG-012
[gerente] gere o relatorio de sprint
```

### Quando o usuario NAO usa prefixo

Cascade deve **inferir o agente mais apropriado** com base no conteudo do pedido, usando a tabela acima e a natureza da tarefa. Regras:

1. Identificar mentalmente qual agente e dono natural do pedido.
2. Iniciar a resposta com uma linha curta no formato: `**Agente:** [nome] (inferido)` para que o usuario possa discordar.
3. Se o pedido for ambiguo entre dois agentes, perguntar antes de prosseguir.
4. Se o pedido for puramente operacional (ex: "como rodar o backend", "como comparar commits", "configurar .gitignore"), nao precisa indicar agente - responder direto.
5. Se o pedido envolver **produzir um artefato**, salvar no diretorio do agente correspondente (coluna "Diretorio de artefatos" da tabela).

### Papel do agente no Cascade

Assumir o papel significa:

- Adotar o tom, foco e escopo daquele agente (ex: `[qa]` foca em riscos, criterios de aceite, cobertura).
- Usar o diretorio de artefatos correspondente ao salvar documentos.
- Seguir diretrizes especificas do agente se existirem (ex: `artefatos/implementador/diretrizes.md`).
- Nao significa executar o codigo Python do agente - o Cascade assume o papel textualmente. Para invocar o codigo real, o usuario pede explicitamente (ex: "rode `GerenteDeProjetos.gerar_relatorio_sprint()`").
