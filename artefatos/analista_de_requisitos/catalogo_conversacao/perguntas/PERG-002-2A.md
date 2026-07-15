# PERG-002-2A

**Título:** Identificação PF ou PJ  
**Tipo:** Decisão  
**Versão:** 0.1  
**Status:** Rascunho

---

## Contexto

- **Fase(s):** FASE-esclarecendo (tentativa inicial) / FASE-finalizando (obrigatória se não respondida em Esclarecendo)
- **Disparo:** Sistema não conseguiu inferir automaticamente se o cliente é Pessoa Física ou Pessoa Jurídica a partir da mensagem inicial. Em FASE-esclarecendo, a pergunta é feita **uma única vez no início da conversa** — se o cliente não responder, o sistema **não insiste** e segue a conversa normalmente. Caso não tenha sido respondida até a entrada em FASE-finalizando, ela se torna **obrigatória** como campo pendente da coleta.
- **REQ espelho:** REQ-002.2A

---

## Mensagem ao cliente

> O orçamento é para uma **empresa** (CNPJ) ou para **pessoa física** (CPF)?

---

## Opções

| Opção | Cliente também pode dizer | Efeitos |
|-------|----------------------------|---------|
| Empresa / PJ | empresa, minha empresa, CNPJ, razão social, escritório, loja, para a firma | Marcar `tipo_cliente = PJ`; seguir para coleta de CNPJ (REQ-001) |
| Pessoa física / PF | para mim, pessoa física, CPF, residencial, para minha casa, uso pessoal | Marcar `tipo_cliente = PF`; seguir para coleta de CPF (REQ-015) |
| _(silêncio)_ | _(sem resposta)_ | Após prazo REQ-002.22 → reengajamento e eventual abandono |

---

## Se não entender

Aplicar REQ-002.21 — reformular: "Só pra eu entender: o orçamento é pra uma empresa ou é pra uso pessoal?" Com opções: (1) Empresa (2) Pessoal.

---

## Desvios e robustez

| Situação | Tratamento |
|----------|------------|
| Cliente responde com CNPJ direto (ex.: "12.345.678/0001-00") | Inferir PJ, capturar CNPJ como CAMPO-cnpj, pular esta pergunta |
| Cliente responde com CPF direto (ex.: "123.456.789-00") | Inferir PF, capturar CPF como CAMPO-cpf, pular esta pergunta |
| Cliente muda de tipo no meio da conversa (ex.: começa PF, depois informa CNPJ) | Confirmar troca pontualmente (REQ-002.10) e reiniciar coleta do documento fiscal |

---

## Placeholders

Nenhum.

---

## REQs relacionados

- REQ-002.2A (regras de inferência e roteamento PF/PJ)
- REQ-001 (consulta CNPJ na Receita Federal)
- REQ-015 (validação de CPF)
- REQ-002.10 (reuso de documento fiscal / troca de tipo)
- REQ-002.21 (ambiguidade / não entendimento)
- CAMPO-cnpj, CAMPO-cpf (campos associados)
