# Diretrizes — Curador de Conhecimento

<!-- CLASSIFICACAO: PROCESSO -->

Regras operacionais do agente `[curador_conhecimento]`. IDs estáveis; não reciclar.

---

## C01 — Pacote de análise é a fonte de fatos

**Categoria:** processo  
**Data:** 2026-06-18

**Regra:** Toda análise de report começa pelo pacote gerado em `GET /api/reports/{id}/pacote-analise`. Não inferir contexto só pelo texto do report.

**Motivação:** O pacote inclui re-busca Q&A/RAG no estado atual da base, classificação reprocessada e documentos sugeridos.

**Aplicação:** Baixar YAML → salvar no diretório de trabalho do curador (ex.: `AnotacoesPessoais/<colaborador>/Curadoria/` ou `artefatos/curador_conhecimento/pacotes/`) → só então produzir proposta (C06).

---

## C02 — Propostas não alteram produção

**Categoria:** governança  
**Data:** 2026-06-18

**Regra:** O curador **propõe**; humano aprova; `[implementador]` ou operador aplica (par Q&A no painel, edição de `.txt`, re-ingestão RAG).

**Motivação:** Alinhado a REQ-012.14.

---

## C03 — Prioridade de correção de conteúdo

**Categoria:** curadoria  
**Data:** 2026-06-18

**Regra:** Ordem preferencial:

1. Par Q&A curado (perguntas recorrentes, resposta estável)
2. Enriquecimento de `docs/FoldersProdutos/*.txt` (campos estruturados: segmento, porte, capacidade)
3. Re-ingestão RAG (após mudança nos fontes)
4. Ajuste de limiar (`rag_score_minimo`, `qa_score_minimo`) — último recurso, com justificativa

**Motivação:** Q&A resolve mismatch pergunta-vs-prosa (plano_qa_pairs_v1); limiar alto demais mascara conteúdo existente.

---

## C04 — Edição permitida em docs/FoldersProdutos

**Categoria:** escopo  
**Data:** 2026-06-18

**Regra:** O curador pode editar arquivos em `docs/FoldersProdutos/*.txt` quando a proposta for aprovada. Mudanças em `WebScrapping/` exigem validação do `[implementador]` (pipeline de ingestão).

---

## C05 — Fechamento do ciclo

**Categoria:** processo  
**Data:** 2026-06-18

**Regra:** Após aplicar correção, mover report para `resolvido` com link à proposta (no mesmo diretório do pacote, C06) e ao par Q&A / commit de documento. Reexecutar pacote-analise para confirmar `qa_hit_producao` ou `rag_hit_producao`.

---

## C06 — Proposta co-localizada com o pacote

**Categoria:** processo  
**Data:** 2026-07-02

**Regra:** A proposta (`report_XXX_proposta.md`) deve ser salva **no mesmo diretório** do pacote YAML que originou a análise (`report_XXX_pacote_analise.yaml` ou equivalente).

**Motivação:** O curador costuma trabalhar em `AnotacoesPessoais/<colaborador>/Curadoria/`; manter pacote e proposta juntos facilita revisão, arquivamento em `DONE/` e rastreio por report.

**Contexto originário:** pedido operacional do Beto (2026-07-02).

**Aplicação prática:**

- **Permitido:** `AnotacoesPessoais/Beto/Curadoria/report_006_pacote_analise.yaml` + `.../report_006_proposta.md`
- **Permitido:** `artefatos/curador_conhecimento/pacotes/report_042.yaml` + `.../report_042_proposta.md` (se o pacote estiver nessa pasta)
- **Proibido:** salvar proposta em `artefatos/curador_conhecimento/propostas/` quando o pacote analisado está em outro diretório
- **Fallback:** sem caminho de pacote informado → `artefatos/curador_conhecimento/propostas/report_XXX_proposta.md`

O campo **Pacote:** no cabeçalho da proposta deve registrar o caminho relativo real do YAML analisado.
