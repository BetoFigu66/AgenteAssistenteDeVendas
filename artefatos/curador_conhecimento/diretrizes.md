# Diretrizes — Curador de Conhecimento

Regras operacionais do agente `[curador_conhecimento]`. IDs estáveis; não reciclar.

---

## C01 — Pacote de análise é a fonte de fatos

**Categoria:** processo  
**Data:** 2026-06-18

**Regra:** Toda análise de report começa pelo pacote gerado em `GET /api/reports/{id}/pacote-analise`. Não inferir contexto só pelo texto do report.

**Motivação:** O pacote inclui re-busca Q&A/RAG no estado atual da base, classificação reprocessada e documentos sugeridos.

**Aplicação:** Baixar YAML → salvar em `artefatos/curador_conhecimento/pacotes/` → só então produzir proposta.

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

**Regra:** Após aplicar correção, mover report para `resolvido` com link à proposta e ao par Q&A / commit de documento. Reexecutar pacote-analise para confirmar `qa_hit_producao` ou `rag_hit_producao`.
