# Status de execucao dos cenarios de teste

> Arquivo gerado automaticamente pelo QA Runner. Nao editar a mao.
>
> **Plano:** `cenarios_teste_funcionais_sprint02.md`  
> **Atualizado em:** 2026-06-04 20:14 (UTC)  
> **Resumo:** 62 cenarios | OK 6 | FAIL 6 | N/A 0 | Pend 50

| Cenario | Titulo | Cobre | Status | Observacao | Bugs |
|---------|--------|-------|--------|------------|------|
| `CTF-001-01` | Cliente envia mensagem com CNPJ válido | REQ-001.1, REQ-001.2, REQ-001.3, REQ-001.7 | OK | — | — |
| `CTF-001-02` | Mensagem sem CNPJ válido | REQ-001.2 | OK | A mensagem que enviou foi "Hmm, não consegui validar esse CNPJ. Pode conferir e me enviar novamente?" | — |
| `CTF-001-03` | Reuso de empresa já consultada | REQ-001.7, REQ-002.10 | FAIL | — | CTF-001-03-01.md |
| `CTF-001-04` | Empresa visível em consulta direta | REQ-001.7 | OK | Está sendo exibido o CNPJ. Penso que o ideal é exibir o nome da empresa. | — |
| `CTF-001-05` | Empresa associada à negociação | REQ-001.5 | PENDENTE | — | — |
| `CTF-002-01` | Saudação | REQ-002.1 | OK | — | — |
| `CTF-002-02` | Pergunta sobre preço aciona base de conhecimento | REQ-002.1, REQ-003 (geração) | PENDENTE | — | — |
| `CTF-002-03` | Quantidade e tipo de produto extraídos | REQ-002.2, REQ-002.3, REQ-002.3A | FAIL | — | CTF-002-03-01.md |
| `CTF-002-04` | E-mail extraído | REQ-002.2 | FAIL | — | CTF-002-04-01.md |
| `CTF-002-05` | Tipo de produto fora do catálogo suportado | REQ-002.3A (limitação conhecida) | PENDENTE | — | — |
| `CTF-002-06` | Painel mostra estado dos campos da negociação | REQ-002.3 | PENDENTE | — | — |
| `CTF-002-07` | Pergunta livre durante qualificação consulta a base | REQ-002.17 | PENDENTE | — | — |
| `CTF-002-08` | Pergunta sobre catálogo da empresa é atendida pela base de Q&A | REQ-002.1, REQ-002.1A (caso 1), REQ-002.1B (telefone novo) | PENDENTE | — | — |
| `CTF-002-09` | Fallback condicional acionado em mensagem ambígua | REQ-002.1A (caso 2 — fallback por baixa confiança) | PENDENTE | — | — |
| `CTF-002-10` | Anti-padrão: fallback NÃO acontece em resposta de qualificação | REQ-002.1A (anti-padrão — não consultar REQ-003 em toda mensagem) | PENDENTE | — | — |
| `CTF-003-01` | Pergunta técnica retorna conteúdo da base | REQ-003.2, REQ-003.3 | PENDENTE | — | — |
| `CTF-003-02` | Auditoria da resposta no painel | REQ-003.5, REQ-005.6 | PENDENTE | — | — |
| `CTF-003-03` | Par Q&A aprovado precede a base documental | REQ-003 ↔ REQ-013 | FAIL | — | CTF-003-03-01.md |
| `CTF-003-04` | Mudança de configuração afeta busca | REQ-014, REQ-003.2 | PENDENTE | — | — |
| `CTF-004-01` | Cliente pede atendimento humano | REQ-004.1, REQ-004.6 | PENDENTE | — | — |
| `CTF-004-02` | Vendedor assume conversa pelo painel | REQ-004.3, REQ-004.4 | PENDENTE | — | — |
| `CTF-004-03` | Modo humano suspende respostas automáticas | REQ-004.10 | PENDENTE | — | — |
| `CTF-004-04` | Reclamação é detectada | REQ-004.7 | PENDENTE | — | — |
| `CTF-005-01` | Mensagem do cliente aparece no histórico | REQ-005.1 | PENDENTE | — | — |
| `CTF-005-02` | Resposta automática aparece no histórico | REQ-005.2 | PENDENTE | — | — |
| `CTF-005-03` | Auditoria completa por mensagem | REQ-005.6 | PENDENTE | — | — |
| `CTF-005-04` | Histórico por telefone | REQ-005.5 | PENDENTE | — | — |
| `CTF-005-05` | Listagem de negociações ativas no painel | REQ-005.5, REQ-010.7 | PENDENTE | — | — |
| `CTF-006-01` | Criar orçamento associado a cliente | REQ-006.1, REQ-006.2 | PENDENTE | — | — |
| `CTF-006-02` | Cliente pode ter múltiplos orçamentos | REQ-006.3 | PENDENTE | — | — |
| `CTF-006-03` | Item de orçamento | REQ-006.4 | PENDENTE | — | — |
| `CTF-008-01` | Webhook aceita mensagem entrante | REQ-008.1, REQ-008.2 | PENDENTE | — | — |
| `CTF-008-02` | Mensagens do mesmo telefone permanecem em uma conversa | REQ-008.4 | OK | Fiz o teste com o painel e deu certo, porém precisamos testar com o whatsapp pra garantir que está ok. | — |
| `CTF-008-03` | Confirmação de gap: agente não envia mensagens reais | REQ-008.5 (gap conhecido) | PENDENTE | — | — |
| `CTF-010-01` | Cockpit lista negociações | REQ-010.7 | PENDENTE | — | — |
| `CTF-010-02` | Detalhe da conversa | REQ-010.7 | FAIL | — | CTF-010-02-01.md |
| `CTF-010-03` | Modal de raciocínio | REQ-010.7, REQ-005.6 | PENDENTE | — | — |
| `CTF-010-04` | Filtro por modo humano | REQ-010.8 | PENDENTE | — | — |
| `CTF-010-05` | Confirmação de gap: painel sem login | REQ-010.1 (gap conhecido) | PENDENTE | — | — |
| `CTF-011-01` | Mensagem pendente aparece na fila | REQ-011 (workflow) | PENDENTE | — | — |
| `CTF-011-02` | Aprovar uma mensagem | REQ-011 (aprovação) | PENDENTE | — | — |
| `CTF-011-03` | Reprovar uma mensagem com resposta correta | REQ-011 (reprovação) ↔ REQ-013 (criação de Q&A) | PENDENTE | — | — |
| `CTF-011-04` | Bug fix: mensagem reprovada não fica pendente | REQ-011 (estabilização da Sprint 2) | PENDENTE | — | — |
| `CTF-011-05` | Confirmação de gap: três modos formais | REQ-011 (gap conhecido) | PENDENTE | — | — |
| `CTF-012-01` | Criar report a partir do painel | REQ-012 (criação) | FAIL | — | — |
| `CTF-012-02` | Filtrar reports por status | REQ-012 | OK | — | — |
| `CTF-012-03` | Detalhe do report | REQ-012 | PENDENTE | — | — |
| `CTF-012-04` | Transição de status | REQ-012 | PENDENTE | — | — |
| `CTF-013-01` | Listar Q&As | REQ-013 | PENDENTE | — | — |
| `CTF-013-02` | Criar par Q&A manualmente | REQ-013 | PENDENTE | — | — |
| `CTF-013-03` | Aprovar e usar par Q&A | REQ-013, REQ-003 | PENDENTE | — | — |
| `CTF-013-04` | Buscar Q&A no painel | REQ-013 | PENDENTE | — | — |
| `CTF-013-05` | Editar e desativar par | REQ-013 | PENDENTE | — | — |
| `CTF-013-06` | Par criado por reprovação aparece como rascunho | REQ-013 ↔ REQ-011 | PENDENTE | — | — |
| `CTF-014-01` | Consultar configuração atual | REQ-014 | PENDENTE | — | — |
| `CTF-014-02` | Alterar configuração | REQ-014 | PENDENTE | — | — |
| `CTF-014-03` | Configuração afeta o comportamento | REQ-014, REQ-003 | PENDENTE | — | — |
| `CTF-014-04` | Confirmação de gap: configuração de Q&A | REQ-014 (gap conhecido) | PENDENTE | — | — |
| `CTF-014-05` | Confirmação de gap: persistência entre reinícios | REQ-014 (gap conhecido) | PENDENTE | — | — |
| `CTF-E2E-01` | Conversa completa com qualificação | REQ-001, REQ-002, REQ-003, REQ-005, REQ-008, REQ-011 | PENDENTE | — | — |
| `CTF-E2E-02` | Reprovação vira par Q&A | REQ-011, REQ-013, REQ-005 | PENDENTE | — | — |
| `CTF-E2E-03` | Takeover humano interrompe agente | REQ-004, REQ-010, REQ-005 | PENDENTE | — | — |
