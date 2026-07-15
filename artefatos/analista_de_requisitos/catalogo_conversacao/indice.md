# Índice do Catálogo de Conversação

**Atualizado em:** 2026-07-15

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
| PERG-016-009 | Continuidade após pausa | Retorno fora da janela | [perguntas/PERG-016-009.md](perguntas/PERG-016-009.md) | REQ-016.9 (v0.2) |
| PERG-016-010 | Fechamento do atendimento | Fim de ciclo natural | [perguntas/PERG-016-010.md](perguntas/PERG-016-010.md) | REQ-016.10 (v0.2) |
| PERG-002-022 | Reengajamento por abandono | Inatividade 24h em qualificação | [perguntas/PERG-002-022.md](perguntas/PERG-002-022.md) | REQ-002.22 (v0.2) |
| PERG-016-009B | Confirmação de interesses anteriores após reengajamento | Após "Continuar" na PERG-016-009 | [perguntas/PERG-016-009B.md](perguntas/PERG-016-009B.md) | REQ-016.9 (v0.1) |
| PERG-002-2A | Identificação PF ou PJ | Ambiguidade em Esclarecendo | [perguntas/PERG-002-2A.md](perguntas/PERG-002-2A.md) | REQ-002.2A (v0.1) |

---

## Informações necessárias (campos)

| ID | Título | Produto / contexto | Arquivo | REQ espelho |
|----|--------|-------------------|---------|-------------|
| CAMPO-cnpj | CNPJ da empresa | PJ em Finalizando | [campos/CAMPO-cnpj.md](campos/CAMPO-cnpj.md) | REQ-002.2, REQ-001 |
| CAMPO-cpf | CPF do solicitante | PF em Finalizando | [campos/CAMPO-cpf.md](campos/CAMPO-cpf.md) | REQ-002.2A, REQ-015 |
| CAMPO-software-ponto | Software de ponto | Relógio de Ponto | [campos/CAMPO-software-ponto.md](campos/CAMPO-software-ponto.md) | REQ-002.3C, REQ-002.14 |
| CAMPO-modelo | Modelo/especificação do produto | Qualquer produto | [campos/CAMPO-modelo.md](campos/CAMPO-modelo.md) | REQ-002.3B |
| CAMPO-endereco | Endereço de entrega/instalação | Entrega/instalação | [campos/CAMPO-endereco.md](campos/CAMPO-endereco.md) | REQ-002.3D |
| CAMPO-contato | Contato para orçamento | Qualquer orçamento | [campos/CAMPO-contato.md](campos/CAMPO-contato.md) | REQ-002.3C |
| CAMPO-quantidade | Quantidade de equipamentos | Controle de acesso | [campos/CAMPO-quantidade.md](campos/CAMPO-quantidade.md) | REQ-002.14A, REQ-002.15 |
| CAMPO-faixa-funcionarios | Faixa de funcionários | Controle de ponto | [campos/CAMPO-faixa-funcionarios.md](campos/CAMPO-faixa-funcionarios.md) | REQ-002.14 |

---

## Pendências conhecidas (para a Kika)

- [x] ~~Completar fichas de campos de qualificação (modelo, endereço, contato, quantidade, faixa-funcionarios)~~ Criados (v0.1).
- [ ] Completar fichas `CAMPO-xxx` para demais produtos Inforrel (catraca, CFTV, roteadores, etc.) — campos específicos por produto
- [ ] Validar textos das mensagens com Rita
- [x] ~~Decidir se fase "Encerrado por Inatividade" permanece com este nome ou vira "Suspenso"~~ Manter nome atual.
- [x] ~~Referenciar este catálogo nos REQs-002 e REQ-016~~ Ajustado em REQ-002 v1.28 e REQ-016 v2.2.
- [x] ~~Adicionar `PERG-002-2A` (PF vs PJ)~~ Criado como ficha (v0.1).
- [x] ~~Espelhar "pré-requisitos para sair de Esclarecendo" em REQ-002~~ Ajustado via REQ-002.1C v1.28.
- [x] ~~Decidir como tratar motivo `desistencia` em REQ-016.4~~ Adicionado em REQ-016 v2.1.
- [x] ~~Formalizar `PERG-esclarecendo-confirmar-interesse` em um REQ~~ Incorporado em REQ-016.9 (v2.5).
