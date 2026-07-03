# Índice do Catálogo de Conversação

**Atualizado em:** 2026-07-03

---

## Fases

| ID | Nome | Situação típica | Arquivo | Status |
|----|------|-----------------|---------|--------|
| FASE-esclarecendo | Esclarecendo | ativo | [fases/FASE-esclarecendo.md](fases/FASE-esclarecendo.md) | Rascunho |
| FASE-encerrado-por-inatividade | Encerrado por Inatividade | ativo | [fases/FASE-encerrado-por-inatividade.md](fases/FASE-encerrado-por-inatividade.md) | Rascunho |
| FASE-finalizando | Finalizando | ativo | [fases/FASE-finalizando.md](fases/FASE-finalizando.md) | Rascunho |
| FASE-criando-orcamento | Criando Orçamento | ativo | [fases/FASE-criando-orcamento.md](fases/FASE-criando-orcamento.md) | Rascunho |
| FASE-encerrado | Encerrado | encerrado | [fases/FASE-encerrado.md](fases/FASE-encerrado.md) | Rascunho |

---

## Perguntas de decisão

| ID | Título | Fase / disparo | Arquivo | REQ espelho |
|----|--------|----------------|---------|-------------|
| PERG-016-009 | Continuidade após pausa | Retorno fora da janela | [perguntas/PERG-016-009.md](perguntas/PERG-016-009.md) | REQ-016.9 |
| PERG-016-010 | Fechamento do atendimento | Fim de ciclo natural | [perguntas/PERG-016-010.md](perguntas/PERG-016-010.md) | REQ-016.10 |
| PERG-002-022 | Reengajamento por abandono | Inatividade 24h em qualificação | [perguntas/PERG-002-022.md](perguntas/PERG-002-022.md) | REQ-002.22 |
| PERG-esclarecendo-confirmar-interesse | Confirmar interesses anteriores | Após "Continuar" na PERG-016-009 | [perguntas/PERG-esclarecendo-confirmar-interesse.md](perguntas/PERG-esclarecendo-confirmar-interesse.md) | Brainstorming §4.4 |

---

## Informações necessárias (campos)

| ID | Título | Produto / contexto | Arquivo | REQ espelho |
|----|--------|-------------------|---------|-------------|
| CAMPO-cnpj | CNPJ da empresa | PJ em Finalizando | [campos/CAMPO-cnpj.md](campos/CAMPO-cnpj.md) | REQ-002.2, REQ-001 |
| CAMPO-software-ponto | Software de ponto | Relógio de Ponto | [campos/CAMPO-software-ponto.md](campos/CAMPO-software-ponto.md) | REQ-002.3C, REQ-002.14 |

---

## Pendências conhecidas (para a Kika)

- [ ] Completar fichas `CAMPO-xxx` para demais produtos Inforrel (catraca, CFTV, etc.)
- [ ] Validar textos das mensagens com Rita
- [ ] Decidir se fase "Encerrado por Inatividade" permanece com este nome ou vira "Suspenso" (brainstorming §9)
- [ ] Referenciar este catálogo nos REQs-002 e REQ-016 na próxima revisão formal
- [ ] Adicionar `PERG-002-2A` (PF vs PJ) como pergunta de decisão ou manter só como CAMPO
