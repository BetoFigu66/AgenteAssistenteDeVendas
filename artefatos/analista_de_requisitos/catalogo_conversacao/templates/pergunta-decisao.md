# PERG-<origem>-<nome>

**Título:** (nome curto para humanos)  
**Tipo:** Decisão  
**Versão:** 0.1  
**Status:** Rascunho | Em revisão | Aprovado

---

## Contexto

- **Fase(s):** FASE-xxx
- **Disparo:** (evento que faz o sistema enviar esta pergunta)
- **REQ espelho:** REQ-xxx.y

---

## Mensagem ao cliente

> (Texto com `{placeholders}` em linguagem natural.)

---

## Opções

| Opção | Cliente também pode dizer | Efeitos |
|-------|----------------------------|---------|
| (rótulo curto) | (sinônimos, frases típicas) | (lista de efeitos da lista fechada) |

---

## Se não entender

(Referência a REQ-002.21 ou comportamento padrão.)

---

## Desvios e robustez

| Situação | Tratamento |
|----------|------------|
| Cliente responde com uma **pergunta sobre produto/serviço** em vez de escolher uma opção | Aplicar REQ-002.17 / REQ-002.1A Caso 3: responder a dúvida via REQ-003 e retomar esta pergunta |
| Cliente usa **citação do WhatsApp** (responder a esta pergunta) | Aplicar REQ-002.1A Caso 4: usar o texto citado para identificar que a resposta se refere a esta PERG; vincular a resposta à opção correspondente |
| Cliente demonstra **insatisfação** ou sinal de situação crítica | Aplicar REQ-004.7 / REQ-007: marcar conversa como crítica e escalar para humano, interrompendo o fluxo desta pergunta |

---

## Placeholders

| Nome | Origem do valor |
|------|-----------------|
| `{exemplo}` | (de onde vem o texto substituído) |

---

## REQs relacionados

- REQ-xxx
