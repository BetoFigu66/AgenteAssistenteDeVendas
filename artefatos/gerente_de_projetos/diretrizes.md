# Diretrizes do Gerente de Projetos

> **Convenção:** este arquivo segue o padrão `artefatos/<nome>/diretrizes.md` definido em `AGENTS.md` (seção "Convencao: dois arquivos por agente").
>
> **IDs:** prefixo `G` (de Gerente), nunca reciclados. Quando uma diretriz for movida para outro lugar, o ID original vira pointer.
>
> **Conteúdo de referência:** o `README.md` deste diretório mantém a documentação **narrativa** (fluxo, tokens do template, estrutura YAML, exemplos de uso). Este `diretrizes.md` registra apenas as **regras** com IDs estáveis. As duas fontes coexistem: regras curtas aqui, detalhes lá.

---

## Diretrizes ativas

### G01 — Sprint Review: YAML é fonte única, PPTX é derivado
- **Categoria:** processo / artefatos
- **Registrada em:** 2026-04-22
- **Origem:** anteriormente registrada como D03 do `[implementador]`; movida em 2026-05-17 para o `[gerente]` por ser decisão de processo de gestão.
- **Regra:** O Sprint Review é composto por dois artefatos:
  1. **`sprint_NN_YYYYMMDD.yaml`** — fonte única da verdade, **versionado**. Gerado por `GerenteDeProjetos.gerar_dados_sprint_yaml()`.
  2. **`sprint_review_NN_YYYYMMDD.pptx`** — derivado do YAML via `python gera_sprint_report.py`, preenchendo o template `sprint_review_template_*.pptx` por substituição de tokens `{{...}}`. **Não é versionado** (ver `.gitignore`).
- **Motivação:** um único formato estruturado elimina retrabalho de copiar dados do `.md` para o `.pptx`. YAML é legível/editável por humano, fácil de revisar em PR. O `.pptx` passa a ser artefato descartável de apresentação, regerado sempre que o YAML mudar.
- **Contexto originário:** versão anterior gerava um `.md` que depois era copiado manualmente para o `.pptx`. O usuário pediu para automatizar. Decidimos unificar no YAML e eliminar o `.md` para evitar duas fontes de verdade.
- **Aplicação prática:**
  - ✅ Editar conteúdo só no YAML; regerar o PPTX.
  - ✅ Tokens aceitos pelo template documentados no `README.md` deste diretório.
  - ❌ Proibido criar novo `.md` de Sprint Review solto ou editar conteúdo textual direto no PPTX.
  - ❌ Proibido commitar `sprint_review_*.pptx` (exceto templates, que têm `template` no nome).
- **Detalhes:** `README.md` → seção "Fluxo Sprint Review".

### G02 — Cadência de sprint: 2 semanas (14 dias)
- **Categoria:** processo
- **Registrada em:** 2026-05-17
- **Regra:** O sprint padrão tem **14 dias corridos**. O atributo `duracao_sprint_dias` em `GerenteDeProjetos.__init__()` é a fonte da verdade desse valor. Mudanças na cadência exigem aprovação explícita do usuário e devem ser registradas como nova diretriz (não basta alterar o valor no código).
- **Motivação:** cadência fixa permite previsibilidade de relatórios, ritmo de revisão e expectativa de stakeholders.
- **Aplicação prática:**
  - ✅ Sprint NN começa logo após o fim do sprint NN-1.
  - ✅ Relatório (YAML + PPTX) é gerado ao final de cada sprint.
  - ❌ Não criar sprints "bônus" de 1 semana ou "longos" de 4 semanas sem registrar exceção.

### G03 — Versionamento da pasta de Sprint Review
- **Categoria:** git / artefatos
- **Registrada em:** 2026-05-17
- **Regra:** O que é versionado em `artefatos/gerente_de_projetos/`:
  | Arquivo | Versionado? |
  |---------|-------------|
  | `sprint_NN_YYYYMMDD.yaml` | ✅ sim (fonte da verdade) |
  | `sprint_review_NN_YYYYMMDD.pptx` | ❌ não (derivado) |
  | `sprint_review_template_*.pptx` | ✅ sim (template) |
  | `template_sprint.yaml` | ✅ sim (referência humana) |
  | `README.md`, `diretrizes.md` | ✅ sim |
  | Demais `.md` históricos | ✅ sim (legados, até migração completa) |
- **Motivação:** evitar que PPTXs derivados gerem ruído em diffs e que templates sejam tratados como artefatos descartáveis.
- **Aplicação prática:**
  - ✅ `.gitignore` deve cobrir `sprint_review_*.pptx` exceto os com `template` no nome.
  - ❌ Não commitar `.pptx` gerado.

### G04 — Tokens do template e YAML devem casar
- **Categoria:** integridade do template
- **Registrada em:** 2026-05-17
- **Regra:** Os nomes dos tokens (`{{xxx}}`) usados no template `.pptx` devem corresponder exatamente às chaves declaradas no YAML de dados. A lista canônica de tokens aceitos está no `README.md` deste diretório (seção "Tokens aceitos no template `.pptx`"). Adicionar token novo exige:
  1. Documentar o token no `README.md`.
  2. Atualizar `gera_sprint_report.py` se for um caso novo (não coberto pelas regras genéricas).
  3. Garantir que a chave correspondente exista no YAML ou tenha fallback.
- **Motivação:** divergência silenciosa entre template e gerador é a causa mais comum de slides com `{{xxx}}` aparecendo no PPTX final.
- **Aplicação prática:**
  - ✅ Antes de adicionar token no PowerPoint, conferir se já existe no `README.md`.
  - ✅ Se token não estiver sendo substituído: verificar se o PowerPoint dividiu `{{...}}` em múltiplos "runs" com formatação diferente (causa #1). Solução: retipar o token com formatação uniforme.
  - ❌ Não inventar token sem registrar no `README.md`.

### G05 — PPTX é editável apenas para formatação visual
- **Categoria:** processo / artefatos
- **Registrada em:** 2026-05-17
- **Regra:** Edições manuais no `.pptx` gerado são aceitáveis **apenas para ajustes visuais** (posição, fonte, cor, alinhamento). **Texto nunca é editado no PPTX** — texto vem do YAML, sempre. Se o texto está errado no PPTX, a correção é no YAML + regerar.
- **Motivação:** preserva a regra G01 (YAML como fonte única). Editar texto no PPTX cria divergência silenciosa que se perpetua a cada nova geração.
- **Aplicação prática:**
  - ✅ Mover caixa de texto, mudar cor de fundo, ajustar tamanho da fonte — OK.
  - ❌ Trocar "Refatorar provider LLM" por "Refatorou provider LLM" direto no PPTX — proibido. Editar no YAML.

---

## Diretrizes movidas / revogadas

(nenhuma até o momento — manter este bloco para preservar histórico quando uma diretriz sair.)

---

## Histórico

| Data | Mudança |
|------|---------|
| 2026-05-17 | Criação do arquivo. G01 importada do `[implementador]` (era D03, agora pointer lá). G02-G05 extraídas do `README.md` deste diretório. |
