# Diretrizes do Arquiteto de Sistemas

> **Convenção:** este arquivo segue o padrão `artefatos/<nome>/diretrizes.md` definido em `AGENTS.md` (seção "Convencao: dois arquivos por agente").
>
> **Particularidade do `[arquiteto]`:** as decisões arquiteturais costumam ser longas demais para caber inline. Por isso, cada diretriz aqui é um **resumo + pointer** para o `.md` temático que contém a decisão completa. Os `.md` temáticos são a fonte da verdade; este documento é o **índice navegável** que registra a regra-síntese e quando ela foi tomada.
>
> **IDs:** prefixo `A` (de Arquiteto), nunca reciclados. Se uma diretriz for revogada, o ID vira pointer descrevendo a substituição.

---

## Diretrizes ativas

### A01 — Arquitetura do POC: stack mínima validada
- **Categoria:** arquitetura
- **Registrada em:** 2026-04-13
- **Regra:** A POC usa a stack definida em `arquitetura_poc_v1.md` (FastAPI + SQLAlchemy + PostgreSQL no backend; React + Vite + TailwindCSS no frontend; integração WhatsApp via Twilio). Mudanças de stack exigem ADR explícito antes da implementação.
- **Motivação:** congelar a stack durante a validação do POC para reduzir variáveis de risco.
- **Documento detalhado:** [`arquitetura_poc_v1.md`](./arquitetura_poc_v1.md) — escopo, critérios de sucesso, componentes, fluxos e custos.
- **Aplicação prática:**
  - ✅ Antes de propor uma biblioteca nova fora da stack listada, abrir uma decisão arquitetural complementar.
  - ❌ Proibido trocar componente core (ex.: SQLAlchemy → Tortoise ORM) sem ADR.

### A02 — Política de branches: `main` é produção
- **Categoria:** processo / git
- **Registrada em:** 2026-04-20
- **Regra:** O fluxo de branches segue `politica_branches.md`. `main` é a branch de produção (deploy automático), `develop` é a branch de integração, features usam o padrão `feature/REQ-XXX-descricao` e bugfixes `bugfix/BUG-XXX-descricao`. `homolog` será ativada pós-POC. Branch `qas` será criada quando o sistema entrar em produção.
- **Motivação:** evitar commits diretos em `main`, garantir rastreabilidade entre código e REQ/BUG e ter uma estrutura preparada para crescer com a maturidade do projeto.
- **Documento detalhado:** [`politica_branches.md`](./politica_branches.md) — tabela completa de branches, regras de merge, naming convention, hotfix process.
- **Aplicação prática:**
  - ✅ Toda feature começa com branch `feature/REQ-XXX-descricao` saindo de `develop`.
  - ✅ PR sempre para `develop`; merge para `main` é via release.
  - ❌ Proibido push direto em `main` ou `develop`.

### A03 — Disponibilização de versões: validadores recebem builds, não código
- **Categoria:** processo / release
- **Registrada em:** 2026-04-19
- **Regra:** Os validadores (Kika, Rita) **não executam código fonte**. Recebem versões empacotadas/disponibilizadas conforme o processo definido em `processo_disponibilizacao_versoes.md`. O Arquiteto define o canal (build, container, URL pública) por fase do projeto.
- **Motivação:** reduzir fricção de validação e evitar que problemas de ambiente local sejam confundidos com bugs do sistema.
- **Documento detalhado:** [`processo_disponibilizacao_versoes.md`](./processo_disponibilizacao_versoes.md) — fluxo de release, versionamento, comunicação aos validadores.
- **Aplicação prática:**
  - ✅ Validador recebe URL/binário pronto para uso.
  - ❌ Proibido pedir ao validador para `git clone` e `npm install` para validar feature.

### A04 — Deploy do POC via túnel local (Cloudflare Tunnel)
- **Categoria:** infra / deploy
- **Registrada em:** 2026-04-28
- **Regra:** Durante o POC, a aplicação roda na máquina do Beto e é exposta via Cloudflare Tunnel conforme `deploy_tunel_local.md`. Não há deploy em provedor cloud nesta fase. Limitação aceita: aplicação só fica no ar enquanto a máquina estiver ligada com os containers rodando.
- **Motivação:** custo zero para validação, sem comprometer com infraestrutura cloud antes de confirmar viabilidade do produto.
- **Documento detalhado:** [`deploy_tunel_local.md`](./deploy_tunel_local.md) — setup do túnel, URL pública, troubleshooting.
- **Aplicação prática:**
  - ✅ Para o POC, expor via `cloudflared` apontando para os containers locais.
  - ✅ Acesso via URL HTTPS gerada pelo Cloudflare.
  - ❌ Não migrar para Heroku/Vercel/AWS sem decisão explícita pós-POC.

### A05 — Direcionamento de IA: Cascade assume papéis textualmente, não executa os agentes
- **Categoria:** processo / arquitetura de agentes
- **Registrada em:** 2025-05
- **Regra:** O modelo definido em `analise_agentes_vs_skills_vs_harness.md` é o **harness textual**: o Cascade lê o `agentes/<nome>.md` e o `artefatos/<nome>/diretrizes.md` para assumir o papel. As classes Python em `agentes/*.py` **não são instanciadas** pelo Cascade durante a conversa; servem apenas como utilitários programáticos invocados explicitamente pelo usuário.
- **Motivação:** evitar a complexidade de orquestração de agentes Python quando o ganho prático vem da convenção textual + IA generalista.
- **Documento detalhado:** [`analise_agentes_vs_skills_vs_harness.md`](./analise_agentes_vs_skills_vs_harness.md) — comparação Agentes vs. Skills vs. Harness, diagnóstico do uso real, decisão.
- **Aplicação prática:**
  - ✅ Para invocar o agente, usar o prefixo `[nome]` na mensagem (ver `AGENTS.md`).
  - ✅ Para executar o código do agente, pedir explicitamente: "rode `GerenteDeProjetos.gerar_relatorio_sprint()`".
  - ❌ Não confundir "assumir o papel" com "instanciar a classe Python".

---

## Diretrizes movidas / revogadas

(nenhuma até o momento — manter este bloco para preservar histórico quando uma diretriz sair)

---

## Histórico

| Data | Mudança |
|------|---------|
| 2026-05-17 | Criação do índice consolidando os `.md` temáticos em A01-A05. Conteúdo detalhado permanece nos `.md` originais. |
