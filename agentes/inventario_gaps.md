# Inventário de gaps — adoção da convenção de dois arquivos por agente

> **Convenção de referência:** `AGENTS.md` → seção "Convencao: dois arquivos por agente (identidade + diretrizes)".
>
> **Padrão-alvo:**
> - `agentes/<nome>.md` → identidade e prompt do agente (fonte da verdade do `get_prompt_sistema()`).
> - `artefatos/<nome>/diretrizes.md` → diretrizes operacionais numeradas (D01, D02, …).
>
> **Regra de migração:** incremental — só criar arquivos quando houver conteúdo real a registrar. Não inventar diretrizes para preencher.

**Última atualização:** 2026-05-17

---

## Visão consolidada

| Agente | `agentes/<nome>.md` | `artefatos/<nome>/diretrizes.md` | Prioridade |
|--------|--------------------|----------------------------------|------------|
| `[analista]` | ✅ existe | ➖ sem regras a registrar hoje | — |
| `[implementador]` | ✅ existe | ✅ existe (D01, D02, D03 pointer, D04, D05, D06) | — (concluído 2026-05-17) |
| `[gerente]` | ✅ existe | ✅ existe (G01-G05) | — (concluído 2026-05-17) |
| `[arquiteto]` | ✅ existe | ✅ existe (índice A01-A05 com pointers para `.md` temáticos) | — (concluído 2026-05-17) |
| `[qa]` | ❌ falta | ❌ falta (diretório `artefatos/qa_engineer/` vazio) | **média** |
| `[auxiliar]` | ❌ falta | ❌ falta (sem diretório de artefatos populado) | baixa |
| `[planejador]` | ❌ falta | ❌ falta (sem diretório de artefatos populado) | baixa |

---

## Detalhamento por agente

### `[analista]` — Analista de Requisitos

- **`agentes/analista_requisitos.md`:** ✅ existe (7,4 KB). Fonte da verdade. `analista_requisitos.py` carrega via `get_prompt_sistema()` lendo o `.md`.
- **`artefatos/analista_de_requisitos/diretrizes.md`:** não criado. As regras de redação de REQs (template, versionamento, checklist) estão dentro do `analista_requisitos.md` (identidade), o que é aceitável enquanto não houver regras operacionais distintas que mereçam IDs estáveis.
- **Gap real:** nenhum urgente. Avaliar futuramente se vale extrair o "checklist de revisão de consistência" do `.md` de identidade para um `diretrizes.md` numerado.

### `[implementador]` — Implementador ~~pendente~~ ✅ concluído (2026-05-17)

- **`agentes/implementador.md`:** ✅ criado. Contém papel, escopo, tom, contrato de conduta, templates de saída (commit/PR), checklist e regras de escalonamento.
- **`artefatos/implementador/diretrizes.md`:** ✅ já existia. Segue padrão IDs (D01, D02, D03 pointer, D04, D05, D06).
- **`implementador.py`:** ✅ atualizado. `get_prompt_sistema()` agora lê `agentes/implementador.md` + concatena `diretrizes.md`, espelhando o padrão do `analista_requisitos.py`.
- **Esforço real:** ~30 min.

### `[gerente]` — Gerente de Projetos ~~pendente~~ ✅ concluído (2026-05-17)

- **`agentes/gerente_de_projetos.md`:** ✅ criado. Contém papel, responsabilidades, agentes coordenados, tom, estrutura do relatório de Sprint, formato de status, templates de saída e regras de escalonamento.
- **`artefatos/gerente_de_projetos/diretrizes.md`:** ✅ criado. Cinco diretrizes registradas:
  - **G01** — Sprint Review: YAML é fonte única, PPTX é derivado (importada do `[implementador]` D03).
  - **G02** — Cadência de sprint: 2 semanas (14 dias).
  - **G03** — Versionamento da pasta de Sprint Review (o que entra/não entra no git).
  - **G04** — Tokens do template e YAML devem casar.
  - **G05** — PPTX é editável apenas para formatação visual (texto vem do YAML).
- **`gerente_de_projetos.py`:** ✅ atualizado. `get_prompt_sistema()` agora lê `agentes/gerente_de_projetos.md` + concatena `artefatos/gerente_de_projetos/diretrizes.md`. Adicionados `PROMPT_MD` e `DIRETRIZES_MD` como constantes da classe.
- **`README.md`:** ✅ atualizado. Cabeçalho aponta para `diretrizes.md` como fonte da verdade das regras; README mantém o conteúdo narrativo (fluxo, tokens, estrutura YAML).
- **`[implementador]` D03 pointer:** ✅ atualizado para apontar especificamente para a G01.
- **Esforço real:** ~45 min.

### `[arquiteto]` — Arquiteto de Sistemas ~~pendente~~ ✅ concluído (2026-05-17)

- **`agentes/arquiteto_sistemas.md`:** ✅ criado. Contém papel, responsabilidades, contexto técnico, três níveis de arquitetura, contrato de conduta, template de ADR e regras de escalonamento.
- **`artefatos/arquiteto_de_sistemas/diretrizes.md`:** ✅ já existia (criado na etapa 3 da sessão anterior). Índice A01-A05 com pointers para os `.md` temáticos:
  - **A01** Stack do POC → `arquitetura_poc_v1.md`
  - **A02** Política de branches → `politica_branches.md`
  - **A03** Disponibilização de versões → `processo_disponibilizacao_versoes.md`
  - **A04** Deploy via túnel local → `deploy_tunel_local.md`
  - **A05** Direcionamento de IA via harness textual → `analise_agentes_vs_skills_vs_harness.md`
- **`arquiteto_sistemas.py`:** ✅ atualizado. `get_prompt_sistema()` agora lê `agentes/arquiteto_sistemas.md` + concatena `artefatos/arquiteto_de_sistemas/diretrizes.md`. Constantes `PROMPT_MD` e `DIRETRIZES_MD` adicionadas.
- **Esforço real:** ~30 min (apenas o `.md` de identidade, já que o índice de diretrizes existia).

### `[qa]` — QA Engineer

- **`agentes/qa_engineer.md`:** ❌ não existe. Prompt hard-coded em `qa_engineer.py:367-…`.
- **`artefatos/qa_engineer/diretrizes.md`:** ❌ não existe. Diretório está **vazio** apesar de o `.py` ser o agente mais robusto do projeto (22 KB, com vários métodos auxiliares de revisão).
- **Gap real:** o agente tem código rico (provavelmente com regras embutidas em métodos), mas zero artefato externo consultável. Antes de criar `diretrizes.md`, vale auditar `qa_engineer.py` e extrair as regras que já existem em forma de código (ex.: critérios de cobertura, checklist de PR).
- **Esforço:** alto (auditoria do `.py` + extração + criação dos dois arquivos). 4-6 h.

### `[auxiliar]` — Auxiliar de Negócios

- **`agentes/auxiliar_negocios.md`:** ❌ não existe. Prompt hard-coded em `auxiliar_negocios.py:35-…`.
- **`artefatos/auxiliar_negocios/diretrizes.md`:** ❌ não existe. Diretório também não existe ainda.
- **Gap real:** nenhum urgente — agente pouco utilizado. Migrar oportunisticamente quando surgir a primeira regra real.
- **Esforço:** baixo, mas baixa prioridade.

### `[planejador]` — Planejador de Negócios

- **`agentes/planejador_negocios.md`:** ❌ não existe. Prompt hard-coded em `planejador_negocios.py:34-…`.
- **`artefatos/planejador_negocios/diretrizes.md`:** ❌ não existe. Diretório também não existe ainda.
- **Gap real:** mesma situação do `[auxiliar]`. Baixa prioridade.
- **Esforço:** baixo, mas baixa prioridade.

---

## Ordem sugerida de execução

1. **`[arquiteto]` — `diretrizes.md` como índice** (etapa 3 deste fluxo). Aproveita que o conteúdo já está escrito e dá visibilidade imediata.
2. **`[implementador]` — `agentes/implementador.md`**. Conteúdo curto, padroniza o agente que mais usa o sistema.
3. **`[gerente]` — extrair `diretrizes.md` do `README.md`**. Esforço médio mas alto valor (regra G01 acabou de ser movida para o gerente).
4. **`[qa]` — auditoria + criação dos dois arquivos**. Alto esforço, mas é onde há mais código não documentado.
5. **`[analista]` — opcional**: avaliar se vale extrair o checklist do `.md` de identidade.
6. **`[auxiliar]`, `[planejador]`** — só quando surgir necessidade.

---

## Histórico

| Data | Mudança |
|------|---------|
| 2026-05-17 | Criação do inventário após formalização da convenção em `AGENTS.md`. |
| 2026-05-17 | `[implementador]` migrado para o padrão (criado `agentes/implementador.md`, `.py` agora lê o `.md`). |
| 2026-05-17 | `[gerente]` migrado para o padrão (criados `agentes/gerente_de_projetos.md` e `artefatos/gerente_de_projetos/diretrizes.md` com G01-G05; `.py` agora lê os `.md`s). |
| 2026-05-17 | `[arquiteto]` migrado para o padrão (criado `agentes/arquiteto_sistemas.md`; `.py` agora lê os `.md`s; índice A01-A05 já existia). |
