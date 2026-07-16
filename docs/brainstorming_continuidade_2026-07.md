# Brainstorming — Continuidade do Projeto (jul/2026)

**Versão:** 1.0 (primeira rodada — Beto + Cascade)  
**Data:** 2026-07-02  
**Status:** Provisório — aguardando considerações da Kika  
**Participantes nesta rodada:** Beto (autor das ideias centrais) · Cascade/Auto no Cursor (análise, mapeamento e redação)

---

## Como ler este documento

### Legenda de autoria

| Marcador | Significado |
|----------|-------------|
| **[Beto]** | Ideia, visão ou decisão expressa pelo Beto na conversa de brainstorming |
| **[Cascade]** | Análise, síntese, mapeamento ao código/REQs, sugestões técnicas ou redação produzida pela IA (Cursor) |
| **[Kika]** | Espaço reservado para a Kika preencher ou revisar |

### Instruções para evoluir em outra IDE de IA

1. Leia as seções 1–6 (contexto e modelo proposto) antes de opinar.
2. Preencha a **seção 7** com suas considerações — concordâncias, discordâncias e propostas.
3. Atualize a **seção 8** (conclusões) e a **seção 9** (alternativas descartadas) após a rodada com a Kika.
4. Consulte os artefatos referenciados (`REQ-002`, `REQ-016`, `cobertura_reqs_sprint02.md`) para validar afirmações factuais.
5. Ao propor mudanças de requisito, registre em `artefatos/analista_de_requisitos/decisoes_requisitos.md` (padrão DEC-XXX).

---

## 1. Contexto e motivação [Beto]

Este projeto tem, no mínimo, **dois objetivos**:

1. **Beto e Kika aprenderem** a desenvolver usando IA como ferramenta de desenvolvimento e também como recurso do sistema.
2. **Criar um sistema "inteligente"** que faça atendimento via WhatsApp, usando uma base de conhecimento dos produtos da empresa cliente (Inforrel).

### Visões iniciais (antes do brainstorming formal)

| Pessoa | Visão resumida |
|--------|----------------|
| **[Beto]** | Uso de IA pelo sistema tem custo recorrente — melhor evitar. Preferir IA como ferramenta de **desenvolvimento**, deixando o sistema o mais **independente de IA** possível e usando IA em runtime apenas como **último recurso**. |
| **[Kika]** | Tentar fazer a IA resolver o máximo, sem perder tempo com a lógica fina dos atendimentos. |

**[Beto]** escreveu a introdução sozinho; este documento foi preparado para a Kika ler, refletir e acrescentar suas considerações antes de chegarem a uma conclusão conjunta.

---

## 2. Objetivos em camadas [Beto + Cascade]

### 2.1 Hierarquia acordada na conversa

**[Beto]** definiu três camadas de objetivo:

| Camada | Objetivo | Observação |
|--------|----------|------------|
| **Principal** | Laboratório de aprendizado (Beto + Kika + IA como ferramenta de dev) | Pode evoluir sem pressa; **pode abortar** se não quiserem continuar |
| **Intermediário** | Sistema utilizado em **produção pela Inforrel** (Rita) | Sem compromisso de prazo com a Rita |
| **Final** | Produto vendável para **qualquer empresa** com atendimento via WhatsApp | Horizonte de longo prazo |

**[Cascade]** formalizou: os dois objetivos originais (aprender + sistema inteligente) permanecem válidos; o **laboratório** é o norte imediato.

```
Laboratório (principal)
    → Inforrel em produção (intermediário, sem prazo fixo)
        → Produto genérico (final)
    ↘ pode abortar a qualquer momento
```

---

## 3. O eixo da tensão: quanto IA usar? [Beto + Cascade]

### 3.1 Reformulação do problema [Cascade]

**[Beto]** indicou que a tensão não é simplesmente "menos IA" vs "mais IA", mas em parte **falta de conhecimento** sobre o potencial e o custo de usar IA dentro do projeto.

Dois extremos imaginados:

| Extremo | Descrição | Custo de desenvolvimento | Custo operacional (APIs) | Tendência |
|---------|-----------|--------------------------|--------------------------|-----------|
| **A — LLM-orquestrador** | Passar o contexto do atendimento para uma LLM; ela responde tudo | Baixo | Alto | Visão da Kika |
| **B — Sistema convencional + IA mínima** | Modelagem OO/estados; IA só para interpretar mensagens | Alto | Baixo | Visão do Beto |

### 3.2 Pergunta levantada: OO ou IA "moderna"? [Beto → resposta Cascade]

**[Beto]** perguntou se faz sentido implementar tudo com Orientação a Objetos ou se IA resolveria de forma mais fácil e moderna.

**[Cascade]** — conclusão provisória (seção 8 detalha):

- **Sim**, faz sentido modelagem explícita (OO leve / máquina de estados) para o **fluxo de atendimento**.
- **Não** como arquitetura principal delegar toda a lógica à LLM em runtime.
- **Melhor caminho:** híbrido — motor determinístico + IA pontual (classificar, extrair entidades, responder dúvidas de produto).
- A visão da Kika ("não perder tempo com lógica fina") pode ser atendida usando **IA no desenvolvimento** (Cursor, agentes) sem delegar a lógica fina à **IA em produção**.

---

## 4. Modelo proposto pelo Beto [Beto]

### 4.1 Princípios do modelo

**[Beto]** — visão orientada a objetos:

- **Estados** do atendimento governam o que o sistema pode fazer.
- **Perguntas** são objetos associados a estados (ou eventos de entrada).
- **Respostas** são objetos associados a perguntas.
- **Ações** são efeitos colaterais de uma resposta escolhida (mudar estado, criar atendimento, etc.).
- **IA em runtime:** principalmente para **interpretar** mensagens do usuário (mapear texto livre → resposta enumerada; extrair entidades), **não** para gerar toda a conversa.

### 4.2 Estados do atendimento [Beto]

| # | Nome [Beto] | Papel | Terminal? |
|---|-------------|-------|-----------|
| 1 | **Esclarecendo** | Estado inicial. Cliente tira dúvidas sobre produto, empresa (Inforrel), etc. Sistema monta lista de interesses e dados para usar em Finalizando. | Não |
| 2 | **Encerrado por Inatividade** | Cliente parou de interagir por tempo configurável (1 dia, 1 semana, 1 mês). Ao retornar, dispara pergunta de continuação. | Não |
| 3 | **Finalizando** | Cliente quer orçamento. Sistema coleta CPF/CNPJ, endereço, condições de entrega, modelos, quantidades, etc. | Não |
| 4 | **Criando Orçamento** | Atendimento transferido ao vendedor para elaborar orçamento. | Não |
| 5 | **Encerrado** | Vendedor enviou orçamento e finalizou (com sucesso ou não), ou cliente desistiu durante esclarecimento. | Sim |

**[Cascade]** — nota técnica para implementação futura: o nome "Encerrado por Inatividade" pode conflitar com `StatusAtendimento.encerrado` (REQ-016). Sugestão: separar `status` (`ativo`/`encerrado`) de `fase` (`esclarecendo`, `encerrado_por_inatividade`, `finalizando`, `em_orcamentacao`). O estado 2 seria uma **fase dentro de `ativo`**, não um encerramento definitivo.

### 4.3 Regras em Esclarecendo [Beto]

**[Beto]** — a "lista" acumulada durante Esclarecendo contém **ambos**:

1. **Interesses** — produtos/modelos/temas mencionados pelo cliente.
2. **Perguntas de qualificação identificadas** — campos que serão necessários em Finalizando.

**Atributos por produto** — exemplo dado pelo Beto:

- Para comprar **Relógio de Ponto**, é necessário saber o **software** que a empresa usa (integração).
- Se o cliente **já revelou** o SW durante Esclarecendo → armazenar nos dados do atendimento → **não perguntar de novo** em Finalizando.
- Se **não revelou** → atributo pendente **gera pergunta** em Finalizando.

**Regra CNPJ flexível** — exemplo dado pelo Beto:

- Sistema pediu CNPJ, mas o cliente fez **outra pergunta** → sistema **responde a pergunta**, não insiste no CNPJ.
- CNPJ torna-se **obrigatório apenas** quando o cliente decidiu comprar (estado Finalizando).

### 4.4 Exemplo OO: reengajamento após inatividade [Beto]

**[Beto]** detalhou apenas este exemplo para ilustrar o padrão Pergunta → Resposta → Ação.

**Contexto:** atendimento em **Encerrado por Inatividade**; cliente retorna.

**Pergunta:**
> "Vi que já conversamos na data XXX, você tava interessado em YYY. Deseja continuar esta conversa ou vamos começar uma nova?"

| Resposta [Beto] | Ações [Beto] |
|-----------------|--------------|
| Começar uma nova | Cria um novo atendimento |
| Vamos continuar | 1. Muda estado para **Esclarecendo** · 2. Levanta produtos/modelos do atendimento anterior e pergunta se o cliente ainda tem interesse nos mesmos |

**[Cascade]** — papel da IA neste exemplo: classificador mapeia "sim, continuar" / "novo pedido" → resposta enumerada. O **texto da pergunta** vem de template (`{data}`, `{resumo_interesse}`), não de geração livre por LLM.

### 4.5 Diagrama de estados [Beto + Cascade]

```
                    ┌─────────────────┐
                    │  Esclarecendo   │◄────────────────────────┐
                    └────────┬────────┘                         │
           desistência       │ cliente_quer_orçamento            │ continuar /
                             ▼                                   │ novo atendimento
                    ┌─────────────────┐                         │
                    │   Finalizando   │                         │
                    └────────┬────────┘                         │
              dados_completos  │                                   │
                             ▼                                   │
                    ┌─────────────────┐      timeout              │
                    │ Criando Orçamento│◄─────┐                   │
                    └────────┬────────┘      │                   │
                             │               │                   │
                             ▼               ▼                   │
                    ┌─────────────────┐  ┌──────────────────────┴──┐
                    │    Encerrado    │  │ Encerrado por Inatividade │
                    └─────────────────┘  └─────────────────────────┘
```

---

## 5. Contribuições da análise (Cascade)

> Esta seção contém material que **não estava na cabeça do Beto** antes da conversa — mapeamento ao projeto existente, comparação com REQs e recomendações técnicas.

### 5.1 Mapeamento: modelo Beto ↔ REQs ↔ código

> **Atualizado em 2026-07-15** com o status real de cada item após o MVP Continuidade.

| Conceito [Beto] | REQ existente | Código hoje | Status |
|-----------------|---------------|-------------|--------|
| 5 fases conversacionais | REQ-002.1C + REQ-016 (DEC-006) | ✅ `FaseAtendimento` enum (`esclarecendo`, `finalizando`, `em_orcamentacao`) + coluna `fase` em `Atendimento`, ortogonal a `status`. Fases terminais (`encerrado`, `encerrado_por_inatividade`) ainda só no catálogo. | **Parcial** — 3 de 5 fases implementadas |
| Esclarecendo + atributos | REQ-002.3, REQ-002.14/14A/15, REQ-002.17, REQ-002.1C | ✅ `regras_esclarecendo.py` com motor Intenção×Fase→Ações. Catálogo declarativo de campos (`catalogo_campos.py`: `CAMPO-modelo`, `CAMPO-software-ponto`, `CAMPO-faixa-funcionarios`). Captura passiva de dados em Esclarecendo. | **Feito** (MVP relógio de ponto) |
| CNPJ flexível em Esclarecendo | REQ-002.1B, REQ-002.17 | ✅ CNPJ pedido uma vez em Esclarecendo, sem insistência; obrigatório só em Finalizando. `regras_esclarecendo._executar_acao_padrao_esclarecendo` governa isso via `fase`. | **Feito** |
| Encerrado por Inatividade | REQ-002.22, REQ-016.7 | ❌ Não implementado. Timer + transição automática + PERG-002-022 pendentes. | **Pendente** |
| Pergunta de continuação | REQ-016.9, PERG-016-009, PERG-016-009B | ❌ Não implementado. REQ formalizado, fichas PERG criadas (continuidade + confirmação de interesses), mas sem código. | **Pendente** |
| Finalizando | REQ-002.3–002.17, REQ-002.1C | ✅ `regras_finalizando.py` + `processador._processar_finalizando()` com loop F1-F4 (captura solta, resolução de modelo, dúvida com retomada, resumo). `campos_pendentes()` funcional. Transição Esclarecendo→Finalizando por `PEDIR_ORCAMENTO`. | **Feito** (MVP relógio de ponto) |
| Criando Orçamento | REQ-004, REQ-006 | ✅ Transição Finalizando→Em Orçamentação (`_concluir_finalizando` → handoff G1-G3). `ModoOperacao.HUMANO` ativado. Fase `em_orcamentacao` gravada. | **Feito** |
| Encerrado | REQ-016.4 | ⚠️ `StatusAtendimento.ENCERRADO` + `motivo_encerramento` existem no modelo. Motivos (`abandono`, `concluido_conversao`, `manual_vendedor`, `concluido_pelo_cliente`, `desistencia`) documentados no REQ. Lógica de transição parcial (sem timer automático de abandono). | **Parcial** — modelo ok, automação pendente |
| Pergunta→Resposta→Ação (motor) | REQ-002.21 | ✅ Motor `resolver_e_executar()` em `services/conversacao/motor.py` com `RegraIntencao` (intencao × fase → builder → ações). Registros por fase (`REGISTRO_ESCLARECENDO`, `REGISTRO_FINALIZANDO`, regras globais). Classificador com multi-intenção. | **Feito** |

**[Cascade — 2026-07-15]** — Resumo da evolução desde o brainstorming:

- **Resolvidos**: o gap principal (campo `fase` / máquina de estados) foi implementado. O motor Intenção×Fase→Ações substituiu o dispatch por `StatusIdentificacao`. O catálogo declarativo de campos (`CampoDef`) governa `campos_pendentes()`. As transições Esclarecendo↔Finalizando→Em Orçamentação funcionam end-to-end para relógio de ponto.
- **Pendentes**: (1) timer de inatividade + FASE-encerrado-por-inatividade (REQ-002.22); (2) pergunta de continuação após pausa (REQ-016.9 / PERG-016-009 / PERG-016-009B); (3) pergunta de fechamento (REQ-016.10 / PERG-016-010); (4) campos para outros produtos além de relógio de ponto (catraca, CFTV, etc.); (5) transição bidirecional Finalizando⇄Esclarecendo por dúvida (DEC-007 — REQ formalizado, implementação F3 atual responde inline sem trocar fase).

### 5.2 Proposta de modelagem técnica [Cascade]

Separar dois eixos ortogonais:

1. **`status`** (REQ-016): `ativo` | `encerrado` + `motivo_encerramento`
2. **`fase`** (modelo Beto): `esclarecendo` | `encerrado_por_inatividade` | `finalizando` | `em_orcamentacao`

Esboço conceitual (não é código a implementar agora):

```python
class Pergunta:
    id, texto_template, fase_origem, respostas: list[Resposta]

class Resposta:
    id, rotulo, sinonimos: list[str], acoes: list[Acao]

class Acao(ABC):
    executar(contexto: ContextoAtendimento)

class TipoProduto:
    atributos_obrigatorios: list[AtributoDef]  # ex: software_integracao

class Atendimento:
    status, fase, itens, informacoes
    def campos_pendentes() -> list[AtributoDef]: ...
```

### 5.3 Estado factual do projeto [Cascade]

Referência: `artefatos/gerente_de_projetos/cobertura_reqs_sprint02.md` (fim Sprint 2).

| Área | Cobertura estimada | Relevância para o modelo Beto |
|------|-------------------|-------------------------------|
| REQ-002 Fluxo conversacional | ~25% | **Gargalo principal** |
| REQ-003 RAG | ~60% | Já maduro |
| REQ-008 WhatsApp/Twilio | ~20% | Bloqueia produção Inforrel |
| REQ-013 Q&A curados | ~70% | Alinhado ao Esclarecendo |
| REQ-016 Atendimentos | Parcial | Só `ativo`/`encerrado` implementado |

**Arquitetura runtime atual** — híbrido pragmático, viés para extremo B:

1. Classificador: regras primeiro (confiança ≥ 0,7); LLM (Groq) se falhar
2. Q&A curada: resposta literal, sem LLM
3. RAG: embeddings + LLM só se Q&A não resolver
4. Templates fixos para preço, prazo, escalação
5. Sem API keys: sistema degrada para regras/templates

Arquivos centrais: `backend/services/processador.py`, `classificador.py`, `respostas/gerador.py`, `rag/`.

Decisões já tomadas que alinham com visão Beto: DEC-001 (RAG não em toda mensagem), ADR-004 (Groq chat + OpenAI embeddings, < $0,50/mês no POC).

---

## 6. Cenários possíveis [Cascade — para discussão]

| Cenário | Descrição | Prós | Contras |
|---------|-----------|------|---------|
| **1 — Laboratório OO** | Investir em `fase` + motor de perguntas/campos (REQ-002) | Alinha modelo Beto e REQs da Kika; auditável; baixo custo runtime | Mais esforço de dev; curva de aprendizado |
| **2 — Protótipo LLM-first** | Branch paralelo: contexto completo → LLM responde | Rápido para experimentar; calibra expectativa de custo/qualidade | Não escala como produto; regras frágeis |
| **3 — Híbrido atual + curadoria** | Manter código atual; evoluir base Q&A via reports | Menor risco imediato | Não resolve qualificação de leads |
| **4 — Pausar / abortar** | Encerrar laboratório | Libera tempo | Perde investimento e aprendizado |

**[Cascade]** — cenário recomendado provisoriamente: **1** como norte, com experimento opcional de **2** para comparar custos no mesmo conjunto de conversas de teste.

---

## 7. Considerações da Kika [Kika — a preencher]

> **Instrução:** Leia as seções 1–6. Escreva abaixo suas considerações. Não apague o conteúdo do Beto — acrescente, discorde ou proponha alternativas.
>
> **Catálogo piloto (2026-07-03):** O modelo Pergunta → Opção → Efeito foi materializado em `artefatos/analista_de_requisitos/catalogo_conversacao/` — vocabulário de negócio, 5 fases, perguntas espelhando REQ-016.9/10 e REQ-002.22, e campos CNPJ/software de ponto. Revise lá antes de opinar sobre formato de documentação.

### 7.1 Concordâncias

_(espaço em branco)_

### 7.2 Discordâncias ou ressalvas

_(espaço em branco)_

### 7.3 Respostas às perguntas em aberto

1. **Onde no espectro A↔B** vocês querem ficar no laboratório?
   - Resposta Kika: ___

2. **Volume de mensagens/mês** esperado na Inforrel em produção?
   - Resposta Kika: ___

3. **Quem cura a base de conhecimento** no dia a dia?
   - Resposta Kika: ___

4. **O que seria "sucesso" do laboratório** para você?
   - Resposta Kika: ___

5. **Critério de abortar** o projeto?
   - Resposta Kika: ___

6. **Multi-tenant desde já** ou Inforrel-first basta?
   - Resposta Kika: ___

### 7.4 Propostas adicionais

_(espaço em branco)_

---

## 8. Conclusões provisórias (rodada 1) [Cascade — sujeitas à revisão da Kika]

1. **[Beto]** O objetivo **principal** é laboratório; Inforrel em produção é intermediário; produto genérico é horizonte. Abortar é opção válida.

2. **[Beto + Cascade]** A tensão Beto/Kika é melhor entendida como um **espectro** (custo de dev vs custo operacional), não como posições irreconciliáveis.

3. **[Cascade]** O modelo OO do Beto **não contradiz** os REQs formais (especialmente REQ-002 e REQ-016) — **complementa e detalha** o que ainda não foi implementado.

4. **[Cascade]** O gargalo do projeto para virar algo útil à Rita **não é RAG** (~60% pronto) — é o **fluxo conversacional estruturado** (~25%).

5. **[Cascade]** Recomendação técnica: **modelagem explícita de fases + IA pontual** (classificar, extrair, Q&A/RAG), não LLM orquestrando todo o fluxo.

6. **[Cascade]** A visão da Kika pode ser parcialmente atendida com **IA no desenvolvimento** (gerar boilerplate, catálogo de campos, testes) sem delegar regras de negócio à IA em runtime.

7. **[Beto]** Estados, atributos por produto, CNPJ flexível e padrão Pergunta→Resposta→Ação formam a **primeira versão** do modelo de domínio — faltam exemplos dos outros estados (Esclarecendo, Finalizando, Criando Orçamento).

---

## 9. Alternativas descartadas ou em avaliação [Cascade + histórico do projeto]

| Alternativa | Quem propôs / onde surgiu | Por que descartada ou adiada |
|-------------|---------------------------|------------------------------|
| **LLM orquestra toda a conversa** (extremo A) | Visão inicial Kika; discutido na rodada 1 | Alto custo operacional; regras de negócio frágeis; difícil auditar (REQ-012). Mantida como possível **experimento**, não como arquitetura alvo. |
| **RAG em toda mensagem** | Hipótese de bug (jun/2026) | DEC-001: custo, latência, polui qualificação. |
| **Renomear estado 2 para "Suspenso"** | Sugestão Cascade | **[Beto]** preferiu manter **"Encerrado por Inatividade"**. No código, usar `fase` separada de `status` para evitar ambiguidade. |
| **Colapsar tudo em `ativo`/`encerrado` sem sub-fases** | REQ-016.4 atual | Insuficiente para o modelo Beto; proposta: adicionar `fase` sem alterar semântica de `status`. |
| **Embeddings locais** | ADR-004 | Adiado: atrasaria POC; revisar se custo > $20/mês. |

---

## 10. Próximos passos sugeridos [Cascade]

1. **[Kika]** Ler este documento e preencher seção 7.
2. **[Kika]** Revisar catálogo piloto em `artefatos/analista_de_requisitos/catalogo_conversacao/` (README + `indice.md` + fichas em `fases/`, `perguntas/`, `campos/`).
3. **[Beto + Kika]** Rodada de alinhamento: validar cenário (1, 2, 3 ou 4).
4. ~~**[Beto]** Detalhar exemplos Pergunta→Resposta→Ação para Esclarecendo, Finalizando e Criando Orçamento~~ → **feito em rascunho** no catálogo (fases + PERG/CAMPO); Kika valida e completa campos pendentes.
5. **[Beto + Kika]** Decidir se REQ-016 precisa de revisão para incluir `fase` explicitamente, ou se basta implementação + referência ao catálogo.
6. **[Implementador]** Se aprovado cenário 1: Sprint focada em `fase` + motor `campos_pendentes()` + REQ-016.9.

---

## Anexo A — Estimativa de custos (ordem de grandeza) [Cascade]

> Números indicativos para calibrar o espectro A↔B. Não substituem medição real.

### Runtime (por mês)

| Cenário | Premissa | Custo estimado |
|---------|----------|----------------|
| **Extremo B (atual)** | ~1.000 msgs/mês; LLM em ~30% das msgs; embeddings esporádicos | < $1–5/mês (ADR-004: < $0,50 só embeddings) |
| **Extremo A** | ~1.000 msgs/mês; LLM em 100% das msgs; contexto ~2.000 tokens/turno | $10–50+/mês (depende do modelo e tamanho do histórico) |

### Desenvolvimento (horas indicativas)

| Entrega | Extremo A | Extremo B (modelo Beto) |
|---------|-----------|-------------------------|
| MVP conversacional funcional | 10–20h (prompt + RAG) | 40–80h (fases + catálogo + motor) |
| Qualificação com atributos por produto | Difícil de garantir | 20–40h (após motor base) |
| Auditabilidade / reports | Fraco | Forte (já previsto REQ-005/012) |

---

## Anexo B — Referências do projeto

| Artefato | Caminho |
|----------|---------|
| Fluxo conversacional | `artefatos/requisitos_formais/REQ-002-fluxo-conversacional-guiado.md` |
| Atendimentos e continuação | `artefatos/requisitos_formais/REQ-016-identificacao-numeracao-atendimentos.md` |
| Decisões de requisitos | `artefatos/analista_de_requisitos/decisoes_requisitos.md` |
| Cobertura Sprint 2 | `artefatos/gerente_de_projetos/cobertura_reqs_sprint02.md` |
| Arquitetura POC / ADRs | `artefatos/arquiteto_de_sistemas/arquitetura_poc_v1.md` |
| Processador (código) | `backend/services/processador.py` |
| Modelos (código) | `backend/models.py` |
| Catálogo de conversação (piloto) | `artefatos/analista_de_requisitos/catalogo_conversacao/` |

---

## Histórico de versões

| Versão | Data | Autor | Alteração |
|--------|------|-------|-----------|
| 1.0 | 2026-07-02 | Beto + Cascade | Primeira versão após rodada 1 de brainstorming |
| 1.1 | 2026-07-03 | Beto + Cascade | Referência ao catálogo de conversação piloto; próximos passos atualizados |
