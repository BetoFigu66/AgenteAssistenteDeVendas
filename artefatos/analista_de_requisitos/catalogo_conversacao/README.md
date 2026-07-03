# Catálogo de Conversação

**Versão:** 0.1 (piloto)  
**Data:** 2026-07-03  
**Autor:** Beto + Cascade (rascunho para revisão da Kika)  
**Status:** Rascunho — aguardando revisão da analista de requisitos  
**Origem:** `docs/brainstorming_continuidade_2026-07.md` (modelo Estados → Perguntas → Respostas → Efeitos)

---

## Objetivo

Este catálogo é a **camada operacional** da conversa: textos que o assistente envia, opções que o cliente pode escolher e efeitos que mudam o atendimento.

A Kika (ou qualquer analista de requisitos) mantém este catálogo **sem precisar entender implementação**. Os REQs formais (`REQ-002`, `REQ-016`, etc.) continuam sendo a fonte das **políticas**; este diretório detalha **como a conversa se manifesta**.

```
REQs (políticas)  ──referencia──►  Catálogo (textos + opções + efeitos)
                                           │
                                           ▼
                                    Código (implementador traduz)
```

---

## Público e responsabilidades

| Papel | O que faz neste catálogo |
|-------|--------------------------|
| **Analista de requisitos (Kika)** | Escreve e revisa fichas; valida tom e regras de negócio; promove para REQ quando estável |
| **Rita (operação)** | Valida textos das mensagens e sinônimos do dia a dia (opcional, por ficha) |
| **Implementador (Beto)** | Traduz IDs (`FASE-xxx`, `PERG-xxx`, `CAMPO-xxx`) para código; não altera regras sem alinhar com a Kika |

---

## Vocabulário

Termos usados neste catálogo — alinhados ao REQ-002 §4.4 e ao brainstorming de continuidade (jul/2026).

| Termo neste catálogo | Significado | Não confundir com |
|----------------------|-------------|-------------------|
| **Fase do atendimento** | Momento da jornada conversacional (Esclarecendo, Finalizando, etc.) | `status` ativo/encerrado (REQ-016) |
| **Situação do atendimento** | Se a conversa está aberta (`ativo`) ou fechada (`encerrado`) | Fase — são eixos independentes |
| **Pergunta do sistema** | Mensagem que o assistente envia ao cliente | Pergunta do cliente sobre produto (REQ-003) |
| **Pergunta de coleta** | Pergunta cuja resposta vira um **campo** do atendimento (texto livre) | Pergunta de decisão |
| **Pergunta de decisão** | Pergunta com **opções enumeradas** que bifurcam o fluxo | Pergunta de qualificação livre |
| **Opção do cliente** | Uma das respostas aceitas a uma pergunta de decisão | Resposta de qualificação (campo) |
| **Efeito** | O que o sistema faz depois que o cliente responde ou ocorre um evento | Detalhe técnico de código |
| **Informação necessária** | Dado que o orçamento exige para um produto ou situação (`CAMPO-xxx`) | Interesse mencionado informalmente |
| **Interesse** | Produto, modelo ou tema que o cliente mencionou em Esclarecendo | Campo já validado para orçamento |
| **Disparo** | Evento que faz o sistema enviar uma pergunta ou mudar de fase | Gatilho técnico (timer, webhook) |

### Lista fechada de efeitos

Ao documentar uma opção ou saída de fase, usar **apenas** estes efeitos (ou propor novo à Kika antes de usar):

| ID do efeito | Significado para o negócio |
|--------------|--------------------------|
| `ir_para_fase` | Muda para outra fase (informar destino: ex. `FASE-finalizando`) |
| `encerrar_atendimento` | Fecha o atendimento com motivo (informar: desistência, abandono, concluído pelo cliente, etc.) |
| `criar_novo_atendimento` | Abre atendimento novo, numerado (REQ-016.6) |
| `registrar_informacao` | Grava dado no atendimento (referenciar `CAMPO-xxx`) |
| `nao_perguntar_de_novo` | Se a informação já foi capturada antes, pular a pergunta correspondente |
| `consultar_base` | Buscar resposta em Q&A/RAG (REQ-003) |
| `escalar_humano` | Passar para vendedor (REQ-004) |
| `notificar_vendedor` | Avisar operação que há solicitação pendente |
| `fazer_pergunta` | Enviar outra pergunta do catálogo (referenciar `PERG-xxx`) |
| `reabrir_atendimento` | Transição `encerrado` → `ativo` por decisão do cliente ou vendedor (REQ-016.5 / REQ-016.8) |
| `retomar_qualificacao` | Volta à última pergunta de coleta pendente sem perder dados (REQ-002.17) |
| `confirmar_dados` | Ecoar ao cliente o que foi entendido antes de seguir (REQ-002.16) |

---

## Tipos de ficha

### `FASE-xxx` — Fase do atendimento

Descreve em que momento da jornada o cliente está: propósito, entradas, saídas e comportamento do sistema.

→ Ver template em [templates/fase.md](templates/fase.md)  
→ Índice: [indice.md](indice.md)

### `PERG-xxx` — Pergunta de decisão

Mensagem com opções fixas; cada opção lista efeitos.

→ Ver template em [templates/pergunta-decisao.md](templates/pergunta-decisao.md)

### `CAMPO-xxx` — Informação necessária (pergunta de coleta)

Dado que o orçamento exige; inclui texto da pergunta, validação em linguagem de negócio e regras de quando perguntar ou pular.

→ Ver template em [templates/campo.md](templates/campo.md)

---

## Convenção de IDs

| Prefixo | Formato | Exemplo |
|---------|---------|---------|
| Fase | `FASE-<nome-curto>` | `FASE-esclarecendo` |
| Pergunta de decisão | `PERG-<origem>-<nome>` | `PERG-016-009` (espelha REQ-016.9) |
| Campo / informação | `CAMPO-<nome>` | `CAMPO-cnpj` |

- IDs são **estáveis** — não reciclar após publicar.
- Quando uma ficha espelha um REQ, incluir o número no ID ou na seção "REQs relacionados".

---

## O que a analista **não** precisa documentar aqui

Deixar para o implementador ou para REQ-014:

- Limiares numéricos do classificador
- Nomes de tabelas, colunas ou enums no banco
- Detalhes de API (Twilio, Receita Federal)
- Algoritmo exato de ordenação das perguntas dinâmicas

Basta documentar **"Cliente também pode dizer: sim, continua"** — a interpretação é responsabilidade do classificador (REQ-002.1).

---

## Fluxo de manutenção

1. **Rascunho** neste diretório (`catalogo_conversacao/`).
2. **Revisão** pela Kika (tom, completude, alinhamento com REQs).
3. **Validação opcional** pela Rita (mensagens ao cliente).
4. **Promoção** — quando estável, referenciar explicitamente nos REQs ou criar anexo formal em `artefatos/requisitos_formais/`.
5. **Implementação** — implementador mapeia IDs para o motor de fases; divergências viram DEC-XXX em `decisoes_requisitos.md`.

---

## Relação com outros artefatos

| Artefato | Relação |
|----------|---------|
| `REQ-002-fluxo-conversacional-guiado.md` | Políticas de qualificação, classificação, campos |
| `REQ-016-identificacao-numeracao-atendimentos.md` | Situação do atendimento, continuação, encerramento |
| `fluxo_end_to_end.md` | Cenários narrados — deve referenciar fichas deste catálogo |
| `docs/brainstorming_continuidade_2026-07.md` | Visão de fases e modelo Pergunta → Opção → Efeito |
| Base Q&A curada (REQ-003 / REQ-013) | Respostas a dúvidas do cliente — **não** entram neste catálogo |

---

## Histórico de versões

| Versão | Data | Autor | Alteração |
|--------|------|-------|-----------|
| 0.1 | 2026-07-03 | Beto + Cascade | Estrutura piloto: README, 5 fases, perguntas espelhando REQ-016.9/10 e REQ-002.22, campos CNPJ e software de ponto |
