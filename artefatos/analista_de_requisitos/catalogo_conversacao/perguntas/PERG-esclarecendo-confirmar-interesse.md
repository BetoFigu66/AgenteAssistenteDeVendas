# PERG-esclarecendo-confirmar-interesse

> ⚠️ **SUPERSEDED** — Este arquivo foi substituído por **[PERG-016-009B.md](PERG-016-009B.md)** (v0.1, 2026-07-15), que segue o padrão de nomenclatura do catálogo e está referenciado no REQ-016.9. Manter este arquivo apenas como histórico.

**Título:** Confirmar interesses do atendimento anterior  
**Tipo:** Decisão  
**Versão:** 0.2  
**Status:** Superseded → ver PERG-016-009B

---

## Contexto

- **Fase(s):** FASE-esclarecendo (logo após continuidade)
- **Disparo:** Cliente escolheu "Continuar" na PERG-016-009 **e** existem interesses/produtos registrados no atendimento anterior
- **REQ espelho:** Brainstorming §4.4 (complemento ao exemplo Beto) — **não** há REQ formal dedicado ainda; validar com Kika

---

## Mensagem ao cliente

> Vi que na nossa conversa de **{data_ultima_interacao}** você estava interessado em **{lista_interesses}**. Você ainda tem interesse nisso?
>
> 1) Sim, continuo interessado  
> 2) Não, quero algo diferente  
> 3) Quero rever item por item

---

## Opções

| Opção | Cliente também pode dizer | Efeitos |
|-------|----------------------------|---------|
| Sim, continuo interessado | sim, mesmos produtos, continua igual, 1 | Manter interesses registrados; `ir_para_fase` permanece FASE-esclarecendo; seguir conversa normalmente |
| Quero algo diferente | não, outro produto, mudou, 2 | Limpar ou arquivar interesses anteriores; `ir_para_fase` FASE-esclarecendo com lista vazia |
| Rever item por item | um de cada vez, não lembro, 3 | `fazer_pergunta` (variante futura PERG-esclarecendo-item-a-item — **pendente Kika**) |

---

## Se não entender

Aplicar REQ-002.21. Padrão após esgotar tentativas: tratar como "Sim, continuo interessado" (menos fricção para retomada).

---

## Desvios e robustez

| Situação | Tratamento |
|----------|------------|
| Cliente responde com uma **pergunta sobre produto/serviço** em vez de escolher uma opção | Aplicar REQ-002.17 / REQ-002.1A Caso 3: responder a dúvida via REQ-003 e retomar a pergunta de confirmação de interesses |
| Cliente usa **citação do WhatsApp** (responder a pergunta anterior) | Aplicar REQ-002.1A Caso 4: usar o texto citado para identificar a qual pergunta a resposta se refere; se a citação for a pergunta desta PERG, vincular a resposta a esta opção |
| Cliente demonstra **insatisfação** ou sinal de situação crítica | Aplicar REQ-004.7 / REQ-007: marcar conversa como crítica e escalar para humano, interrompendo o fluxo de perguntas |

---

## Placeholders

| Nome | Origem do valor |
|------|-----------------|
| `{data_ultima_interacao}` | Data da última mensagem antes da pausa (formato amigável: "15 de junho") |
| `{lista_interesses}` | Produtos/modelos do atendimento — ex.: "relógio de ponto biométrico e catraca pedestal" |

---

## REQs relacionados

- REQ-016.9 (gatilho anterior)
- REQ-002.17 / REQ-002.1A Caso 3 (responder dúvida embutida e retomar)
- REQ-002.1A Caso 4 (resposta com citação de pergunta no WhatsApp)
- REQ-002.21 (tratamento de não entendimento / ambiguidade)
- REQ-004.7 / REQ-007 (escalonamento por insatisfação ou conversa crítica)
- Brainstorming §4.4 — ação Beto: "levanta produtos/modelos e pergunta se ainda tem interesse"

---

## Pendências

- [ ] Kika: decidir se vira REQ formal ou permanece só no catálogo
- [ ] Rita: validar tom da mensagem
