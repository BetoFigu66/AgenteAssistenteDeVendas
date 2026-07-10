# Análise — Transição Esclarecendo → Finalizando

**Versão:** 1.0  
**Data:** 2026-07-10  
**Autor:** Beto (pedido) + Cursor (análise)  
**Status:** Provisório — aguardando análise da Kika  
**Contexto:** Divergência entre REQ-002.1C / fichas de fase (Kika) e plano MVP v1.2 (decisão 2026-07-09)

---
Prompt: 
"Existem 2 ideias antagônicas sobre os estados Esclarecendo e Finalizando:
1. Considera que só deve ir para o estado Finalizando depois que o cliente forneceu todas as informações para a criação do orçamento;
2. Considera que deve ir para o estado finalizando quando o cliente sinalizar que quer orçamento, só então, no estado finalizando, todas as perguntas pendentes seriam respondidas.
Quero que você faça uma análise de pros e contras de cada uma delas e dê sua opinião de qual é a melhor.
"

## 1. Objetivo deste documento

Registrar, de forma estruturada, a análise de **duas visões antagônicas** sobre quando o atendimento deve sair da fase **Esclarecendo** e entrar em **Finalizando**, com prós/contras de cada abordagem e recomendação provisória — para revisão da Kika antes de formalizar alteração em REQ-002.1C e nas fichas `FASE-esclarecendo.md` / `FASE-finalizando.md`.

---

## 2. As duas visões

| | **Opção 1 — "Pré-qualificar em Esclarecendo"** | **Opção 2 — "Transitar na intenção"** |
|---|---|---|
| **Gatilho para Finalizando** | Intenção de orçamento **+** dados mínimos já confirmados (tipo, modelo, quantidade/faixa) | Intenção de orçamento **sozinha** (categoria 1 do REQ-002.1) |
| **Onde perguntar modelo/software** | Em Esclarecendo, via `qualificar_interesse`, se ainda faltarem | Em Finalizando, via `campos_pendentes()` |
| **Fonte hoje** | REQ-002.1C, `FASE-esclarecendo.md` v0.2 | `docs/plano_implementacao_mvp_continuidade_2026-07.md` v1.2 (decisão 2026-07-09) |
| **Papel de Finalizando** | Coleta "formal" — sobretudo fiscal, endereço, confirmação | Coleta **ativa de tudo** que falta para o orçamento |

### Texto de referência — Opção 1 (REQ-002.1C)

> O sistema só deve transitar de FASE-esclarecendo para FASE-finalizando quando:
> 1. O cliente manifestar intenção explícita de orçamento/compra (categoria 1 do REQ-002.1); **E**
> 2. O sistema já tiver confirmado ou extraído os dados mínimos: tipo de produto, modelo/especificação e quantidade/faixa de pessoas (quando aplicável).
>
> Se faltar algum dos dados mínimos, o sistema permanece em FASE-esclarecendo e faz as perguntas necessárias antes de transitar.

### Texto de referência — Opção 2 (plano MVP v1.2)

> O sistema **transita imediatamente para Finalizando** ao reconhecer a intenção (categoria 1 do REQ-002.1) — não espera ter modelo/quantidade confirmados antes de sair de Esclarecendo. Uma vez em Finalizando, cobra **todos** os campos obrigatórios, em qualquer ordem.

---

## 3. Enquadramento

A divergência não é só de implementação: é sobre **o que cada fase significa** e **quando o compromisso do cliente fica explícito no sistema**.

- **Opção 1** tenta que **Finalizando = "produto já definido, falta burocracia"**.
- **Opção 2** tenta que **Finalizando = "cliente comprometido, falta qualquer dado do orçamento"**.

No MVP de relógio de ponto, essa distinção enfraquece: **software de ponto** não é só burocracia — é requisito técnico de integração e pode até orientar a resposta em Esclarecendo. Separar "perguntas de produto em Esclarecendo" e "perguntas de produto em Finalizando" não reflete bem o domínio Inforrel.

---

## 4. Opção 1 — Só vai para Finalizando com dados mínimos já preenchidos

### Prós

1. **Semântica de fase mais "comercial"**  
   Esclarecendo = explorar; Finalizando = cliente já sabe *o quê* quer, falta fechar *com quem/como*. Para o vendedor, entrar em Finalizando sinaliza lead mais quente.

2. **Fila operacional mais limpa**  
   No painel, Finalizando tende a mostrar casos com produto já definido — menos ruído de quem disse "quero orçamento" sem saber modelo.

3. **Transição menos abrupta para o cliente**  
   "Quero orçamento" → "qual modelo?" ainda em tom de esclarecimento; só depois entra a fase "oficial" de fechamento.

4. **Alinhamento com o catálogo/REQ atual**  
   REQ-002.1C e as fichas de fase já descrevem esse comportamento — menos retrabalho documental.

5. **Separação conceitual produto × burocracia**  
   Encaixa na intuição: modelo/quantidade = fit de produto; CNPJ/endereço = dados para emitir orçamento.

### Contras

1. **Fronteira artificial entre fases**  
   Perguntar modelo em Esclarecendo e em Finalizando é a mesma pergunta (`CAMPO-modelo`) com regras diferentes. Duplica lógica ou exige um motor de coleta que já funciona nas duas fases.

2. **Conflito com extração passiva**  
   O brainstorming (§4.3) e o plano MVP dizem: em Esclarecendo captura-se software/modelo *sem pressionar*. Se, após "quero orçamento", o sistema **insiste** em modelo antes de transitar, Esclarecendo deixa de ser só "tirar dúvidas" e vira coleta ativa — só que sem o nome da fase.

3. **Gatilho composto e frágil**  
   "Dados mínimos" mudam por produto (relógio usa `faixa_funcionarios` condicional, catraca usa `quantidade`). A condição de transição vira uma segunda cópia de `campos_pendentes()`, com risco de divergir.

4. **Mensagens compostas mais difíceis**  
   *"Quero orçamento, já usamos Domínio"*: na Opção 1 você fica em Esclarecendo, processa Domínio, pergunta modelo. Funciona, mas o padrão "transitar + reprocessar a mesma mensagem em Finalizando" (plano MVP §3) fica menos natural.

5. **Não resolve indecisão real**  
   Se o cliente quer orçamento mas ainda compara biométrico vs facial, você pergunta modelo em Esclarecendo ou em Finalizando — a pergunta é a mesma; só muda o rótulo da fase.

---

## 5. Opção 2 — Transita na intenção; coleta tudo em Finalizando

### Prós

1. **Gatilho simples e auditável**  
   Uma regra: categoria 1 (intenção de orçamento) → `ir_para_fase(finalizando)`. Fácil de testar, logar e explicar.

2. **Um único motor de coleta**  
   `campos_pendentes()` governa o que falta em Finalizando; Esclarecendo só faz Q&A/RAG + captura passiva. Menos duplicação, alinhado ao padrão Estado/Pergunta do plano.

3. **Coerente com "CNPJ flexível"**  
   Em Esclarecendo nada é obrigatório; a coleta **obrigatória** começa quando o cliente manifesta compra — um único momento de compromisso.

4. **Mensagens compostas**  
   Transição imediata + reprocessamento da mesma mensagem contra as `Pergunta`s de Finalizando (ex.: "quero orçamento, uso Domínio" captura software no mesmo turno).

5. **Captura passiva ganha sentido**  
   Esclarecendo acumula o que vier espontâneo; Finalizando completa o que faltar, com `nao_perguntar_de_novo`. A divisão fica: *explorar* vs *fechar dados*.

6. **REQ-002.4 já prevê ordem flexível**  
   O cliente pode responder campos em qualquer ordem; isso combina melhor com "tudo em Finalizando" do que com um pré-requisito rígido na fronteira.

### Contras

1. **Diverge do REQ-002.1C e das fichas v0.2**  
   Exige alinhamento formal com a Kika — não é só renomear.

2. **Finalizando fica "grande"**  
   Mistura fit de produto (modelo, software) e dados administrativos (CNPJ, endereço). Métricas por fase ficam menos granulares.

3. **Sensação de interrogatório**  
   "Quero orçamento" → imediatamente "qual modelo?" pode parecer seco. Mitigável com mensagem de transição ("Ótimo! Vou precisar de algumas informações…").

4. **Mais casos "incompletos" em Finalizando**  
   Operacionalmente, a fase abrange desde "só disse que quer orçamento" até "pronto para handoff". Pode precisar de indicadores extras (ex.: % campos preenchidos).

5. **Risco de transição prematura**  
   Falso positivo do classificador em "quero orçamento" dispara coleta ativa. Exige confiança alta na categoria 1 (já previsto no REQ-002.1A).

---

## 6. Recomendação provisória (Cursor)

**Opção 2 é a melhor para este projeto** — transitar na intenção e cobrar todos os campos obrigatórios em Finalizando, como no plano MVP v1.2.

### Motivos

1. **Arquitetura** — Um gatilho, um motor (`campos_pendentes`), uma fase de coleta ativa. A Opção 1 tende a duplicar regras ou a fazer Esclarecendo coletar ativamente sem admitir que já é coleta.

2. **Modelo mental do Beto (brainstorming §4.3)** — Esclarecendo acumula interesses e dados espontâneos; obrigatoriedade começa quando o cliente decide comprar. A Opção 2 materializa isso de forma direta.

3. **WhatsApp B2B** — "Quero orçamento" já muda o tom da conversa; perguntar modelo em seguida é esperado. O que importa é não pedir CNPJ *antes* da intenção — e isso as duas opções respeitam.

4. **Produtos com atributos condicionais** — Relógio (software → talvez faixa de funcionários), catraca (quantidade, software de acesso) pedem um motor único de aplicabilidade; usar esse motor só em Finalizando é mais simples que replicá-lo como "pré-requisito de transição".

5. **Custo de manutenção** — A Opção 1 exige atualizar REQ *e* manter duas semânticas para a mesma pergunta. A Opção 2 exige sobretudo **atualizar REQ-002.1C** e as fichas de fase — débito documental, não estrutural.

### O que **não** descartar da Opção 1

- **Captura passiva agressiva em Esclarecendo** (modelo, software mencionados na dúvida) — vale nas duas opções.
- **Indicadores no painel** além da fase (campos preenchidos, "pronto para handoff") — compensa a Opção 2 operacionalmente.
- **Mensagem de transição** ao entrar em Finalizando — reduz o choque da Opção 2.

---

## 7. Sugestão de redação (se adotarem Opção 2)

REQ-002.1C poderia ficar assim, em essência:

> Transitar de Esclarecendo para Finalizando quando o cliente manifestar intenção explícita de orçamento/compra (categoria 1), com confiança adequada. Campos obrigatórios ainda pendentes são coletados **em** Finalizando. Dados já capturados passivamente em Esclarecendo não são perguntados de novo (`nao_perguntar_de_novo`). Exceção: primeiro contato já com todos os dados pode iniciar direto em Finalizando (REQ-002.2).

Isso preserva o espírito das duas visões: Esclarecendo sem pressão; Finalizando como modo de coleta ativa após compromisso — sem duplicar o motor de campos na fronteira.

---

## 8. Espaço para a Kika

### 8.1 Concordâncias

_(espaço em branco)_

### 8.2 Discordâncias ou ressalvas

_(espaço em branco)_

### 8.3 Decisão proposta

- [ ] Manter Opção 1 (REQ-002.1C atual)
- [ ] Adotar Opção 2 (transitar na intenção)
- [ ] Híbrido / outra (descrever abaixo)

_(descrição, se híbrido ou outra)_

### 8.4 Impacto em artefatos (se mudar)

| Artefato | Ação necessária |
|----------|-----------------|
| `REQ-002-fluxo-conversacional-guiado.md` §002.1C | Reescrever regra de transição |
| `FASE-esclarecendo.md` | Remover "não transita só porque disse quero orçamento"; ajustar §Como sair |
| `FASE-finalizando.md` | Ajustar §Como chega aqui |
| `docs/plano_implementacao_mvp_continuidade_2026-07.md` | Já alinhado à Opção 2 — marcar decisão como validada ou reverter |
| `artefatos/analista_de_requisitos/decisoes_requisitos.md` | Registrar DEC-XXX |

---

## 9. Referências

| Artefato | Caminho |
|----------|---------|
| Plano MVP continuidade | `docs/plano_implementacao_mvp_continuidade_2026-07.md` |
| Brainstorming continuidade | `docs/brainstorming_continuidade_2026-07.md` |
| REQ-002 (§002.1C) | `artefatos/requisitos_formais/REQ-002-fluxo-conversacional-guiado.md` |
| Fase Esclarecendo | `artefatos/analista_de_requisitos/catalogo_conversacao/fases/FASE-esclarecendo.md` |
| Fase Finalizando | `artefatos/analista_de_requisitos/catalogo_conversacao/fases/FASE-finalizando.md` |
| Dicionário de termos | `docs/dicionario_termos.md` |

---

## Histórico de versões

| Versão | Data | Autor | Alteração |
|--------|------|-------|-----------|
| 1.0 | 2026-07-10 | Cursor | Primeira versão — análise para revisão da Kika |
