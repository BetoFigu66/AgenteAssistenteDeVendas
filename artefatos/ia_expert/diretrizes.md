# Diretrizes do Agente Especialista em IA

Este documento registra as diretrizes de governança de IA acumuladas ao longo do projeto. Cada diretriz tem ID estável (`IAxx`), categoria, data de registro, regra, motivação, contexto originário e aplicação prática.

> 🧭 **Regra de ouro:** antes de propor qualquer mudança na estrutura de agentes ou no harness, consultar este arquivo para verificar se já há diretriz cobrindo o caso.

---

## Diretrizes ativas

### IA01 — Novos agentes devem ser definidos como arquivos `.md`, não como classes Python

- **Categoria:** governança de agentes
- **Registrada em:** 2026-05-21
- **Regra:** Todo novo agente criado no projeto deve ser definido exclusivamente como `agentes/<nome>.md`, seguindo a convenção de identidade de agentes documentada em `AGENTS.md`. Não é necessário (nem desejável por padrão) criar uma classe Python (`agentes/<nome>.py`) para agentes que operam apenas como contexto/prompt para o Cascade.
- **Motivação:** As classes Python de agentes (`.py`) foram avaliadas em `artefatos/arquiteto_de_sistemas/analise_agentes_vs_skills_vs_harness.md` e conclui-se que são **subutilizadas frente ao custo de manutenção**. O Cascade carrega o `.md` diretamente como prompt de sistema — o `.py` adiciona overhead sem benefício proporcional quando o agente não tem lógica executável própria (métodos Python reais que são invocados programaticamente).
- **Contexto originário:** Ao criar o `[ia_expert]`, o arquivo `agentes/ia_expert.md` foi criado sem um correspondente `ia_expert.py`, consolidando o padrão. A análise estratégica do `[arquiteto]` já havia apontado que classes de agentes são a abordagem de menor ROI no projeto.
- **Aplicação prática:**
  - ✅ Novo agente `[qa]`: migrar o prompt de `agentes/qa_engineer.py` para `agentes/qa_engineer.md`; manter o `.py` apenas se houver métodos Python executáveis reais (ex: `executar_checks()`).
  - ✅ Criar `agentes/novo_agente.md` com papel, escopo, tom e templates de saída.
  - ❌ Criar `agentes/novo_agente.py` com uma classe cuja única função é `return open('novo_agente.md').read()`.
  - ⚠️ Agentes existentes com `.py` que possuem lógica executável real — ex: `[gerente]` com `gerar_relatorio_sprint()` e `gerar_apresentacao_pptx()`, `[implementador]` com `registrar_diretriz()` — **mantêm seus `.py`**. A diretriz se aplica a **criações futuras** e à decisão de migrar agentes existentes quando convir.
