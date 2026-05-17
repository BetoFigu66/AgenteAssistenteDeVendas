# Plano de Evolução do Agente / Reports do Gerente de Projetos

## Objetivo
Este documento entrega um plano inicial de evolução para a manutenção e geração de reports do agente `gerente_de_projetos`.

O foco é:
- manter operação atual de geração de relatórios a partir de dados YAML e templates PPTX;
- orientar a Kika sobre como gerar reports, manter templates e evoluir o fluxo para uma cadência de sprint mais estruturada;
- considerar que os dados serão gerados pelo agente `gerente_de_projetos` com base no que foi feito desde a última apresentação de sprint.

## Estado atual

1. Script de geração:
   - `agentes/scripts/gera_sprint_report.py`
2. Templates de report:
   - `artefatos/gerente_de_projetos/report_templates/template_sprint_review_interno.pptx`
   - `artefatos/gerente_de_projetos/report_templates/template_sprint_review_externo.pptx`
   - `artefatos/gerente_de_projetos/report_templates/template_sprint_interno.yaml`
   - `artefatos/gerente_de_projetos/report_templates/template_sprint_externo.yaml`
3. Exemplos de execução:
   - `agentes/scripts/gera_report_sprint_interno.sh`
   - `agentes/scripts/gera_report_sprint_externo.sh`
4. Saída esperada:
   - `artefatos/gerente_de_projetos/reports/*.pptx`

## Como gerar um report hoje

1. Abrir o terminal na raiz do projeto.
2. Ativar o ambiente Python do backend:
   - `source backend/venv/bin/activate`
3. Rodar o script passando o arquivo YAML de dados e o template PPTX desejado.

Exemplo interno:
```bash
python agentes/scripts/gera_sprint_report.py \
  artefatos/gerente_de_projetos/reports/sprint_XX_interno.yaml \
  artefatos/gerente_de_projetos/report_templates/template_sprint_review_interno.pptx \
  -o ./artefatos/gerente_de_projetos/reports/sprint_XX_interno.pptx
```

Exemplo externo:
```bash
python agentes/scripts/gera_sprint_report.py \
  artefatos/gerente_de_projetos/reports/sprint_XX_externo.yaml \
  artefatos/gerente_de_projetos/report_templates/template_sprint_review_externo.pptx \
  -o ./artefatos/gerente_de_projetos/reports/sprint_XX_externo.pptx
```

4. Revisar o arquivo gerado em `artefatos/gerente_de_projetos/reports/`.

## Como manter os templates

### Manutenção do template de dados (`.yaml`)

- Use os arquivos de template YAML como esquema de referência.
- Mantenha os campos principais:
  - `sprint` / `periodo`
  - `objetivo`
  - `resultados` / `entregas`
  - `pendencias`
  - `riscos`
  - `lições_aprendidas`
  - `proximos_passos`
  - `backlog`
- Se precisar adicionar um novo campo de dados, inclua-o primeiro no YAML de template e depois crie o placeholder correspondente no PPTX.
- Prefira dados que possam ser preenchidos automaticamente pelo agente `gerente_de_projetos`:
  - itens concluídos desde a última apresentação;
  - decisões tomadas;
  - bloqueios removidos;
  - ações para o próximo período.
- Use nomenclatura consistente entre YAML e tokens PPTX: o script resolve chaves pelo nome e por aliases.

### Manutenção do template PPTX

- O template PPTX deve conter placeholders no formato `{{campo}}`.
- Para listas, o template pode usar limites, por exemplo `{{lista:3}}`.
- Se criar uma nova seção no PPTX, confirme que o token existe no YAML de dados ou que o agente `gerente_de_projetos` vai gerar essa chave.
- Ao copiar ou clonar slides, preserve os placeholders e evite duplicações indevidas de token.
- Valide o layout final abrindo o PPTX e conferindo a renderização do conteúdo.

### Estrutura recomendada de manutenção

- Atualize primeiro o YAML de dados.
- Depois atualize o template PPTX.
- Teste o report com um arquivo de dados real antes de considerar o template pronto.
- Versione os templates e mantenha histórico de alterações no repositório.

## Como o agente `gerente_de_projetos` deve alimentar os dados

- O agente deve considerar o que foi feito desde a última apresentação de sprint, não apenas o que está planejado.
- O foco inicial é registrar:
  - entregas concluídas;
  - pendências abertas;
  - riscos identificados;
  - decisões relevantes;
  - aprendizados e ajustes de processo;
  - itens de backlog priorizados.
- Para o primeiro estágio, aceite uma cadência flexível de sprint.
- Depois, evolua para um modelo de sprint mais rígido de ~2 semanas.

## Recomendações para evolução

### Fase 1: estabilizar geração de reports

- consolidar o fluxo atual de geração via `agentes/scripts/gera_sprint_report.py`
- usar os templates existentes como base
- documentar os campos obrigatórios do YAML
- entregar tanto report interno quanto externo

### Fase 2: formalizar dados e ritmo

- definir um padrão de `sprint_XX_YYYYMMDD` ou `sprint_n` para nomear relatórios
- rastrear a data do último review para gerar comparativos
- criar uma checklist de fechamento de sprint:
  - itens concluídos
  - itens em andamento
  - pendências críticas
  - lições aprendidas
  - próximos passos

### Fase 3: migrar para estrutura baseada em agente/skill/harness

- registrar em markdown a especificação do agente `gerente_de_projetos`:
  - quais dados coleta;
  - quais prompts ou regras usa;
  - quais outputs gera.
- avaliar a migração de `agentes/gerente_de_projetos.py` para um artefato `.md` ou skill, mantendo o script de geração como camada de template.
- separar responsabilidades:
  - `gerente_de_projetos` cuida da geração e priorização de dados;
  - `report` ou `presentation` cuida da montagem final em PPTX.

## Pontos importantes para a Kika

- O agente deve ser responsável por gerar os dados históricos desde a última apresentação de sprint.
- O script atual gera o PPTX a partir desses dados; isso deve continuar funcionando enquanto a migração de código ocorrer.
- A manutenção dos templates deve ser feita como dois lados de uma mesma máquina:
  1. dados YAML
  2. layout PPTX
- Não fechar a cadência de sprint agora; o importante é documentar o progresso.
- O plano é evoluir para sprints regulares de 2 semanas assim que houver disciplina suficiente de registro e revisão.

## Ações imediatas

- revisar os templates YAML e PPTX atuais para confirmar os campos usados em `template_sprint_review_interno.pptx` e `template_sprint_review_externo.pptx`.
- definir a primeira lista de campos mínimos obrigatórios para o report interno e externo.
- automatizar, se possível, a geração de `sprint_XX_*.yaml` pelo agente `gerente_de_projetos` a partir de bases de dados ou logs de trabalho.

---

Arquivo criado para apoiar a transição de responsabilidade à Kika e facilitar a evolução do agente/reports do gerente de projetos.