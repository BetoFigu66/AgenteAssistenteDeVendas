# Diretrizes do skill `revisao-codigo`

Regras operacionais numeradas (D01, D02, ...), no mesmo padrão usado pelos demais agentes em `agentes/*/diretrizes.md` (ver `AGENTS.md`). Cada diretriz nasce de uma validação real do Beto durante uma rodada de code review — não são inventadas pelo skill.

IDs nunca são reciclados. Se uma diretriz for removida ou superada, mantenha o ID como pointer para a diretriz que a substituiu.

Template para cada nova entrada:

```
### D0X — <título curto>

- **Categoria:** <correção | regra-de-projeto | reuso-simplificacao | processo | falso-positivo-recorrente>
- **Data:** <AAAA-MM-DD>
- **Regra:** <o que passa a valer>
- **Motivação:** <por que o Beto pediu isso — o que ele observou>
- **Contexto de origem:** <arquivo/PR/trecho que gerou a diretriz>
- **Aplicação prática:** <exemplo do que passa a ser sinalizado / ignorado>
```

---

### D01 — Não reportar concorrência entre requisições do mesmo atendimento

- **Categoria:** falso-positivo-recorrente
- **Data:** 2026-08-18
- **Regra:** não reportar como achado um cenário de bug que só se manifesta se duas requisições referentes ao **mesmo atendimento** forem processadas em paralelo (ex.: race entre ler `atendimento.status` e escalar; duplicar o usuário sentinela "Sistema"). Isso vale até essa diretriz ser atualizada/revogada.
- **Motivação:** o Beto confirmou que paralelismo de requisições para o mesmo atendimento não é uma preocupação atual — vai ser resolvido de forma centralizada com um semáforo por atendimento + agrupamento de mensagens por N segundos (debounce), ainda não implementado. Reportar esses cenários individualmente como "achado de correção" antecipa uma solução que já está planejada de forma diferente.
- **Contexto de origem:** revisão de `backend/services/processador.py` — achados #1 (`_escalar_atendimento` no-op silencioso) e #3 (usuário sentinela duplicado), ambos descartados pelo Beto pelo mesmo motivo.
- **Aplicação prática:** permitido — mencionar de passagem que um trecho pressupõe execução serial se for relevante para quem for implementar o semáforo. Proibido — listar como achado de confiança/severidade em uma revisão, ou tratar como bug pendente de correção isolada. Pendência de implementação rastreada em `AnotacoesPessoais/Beto/pendencias_tecnicas.md` (P01).

### D02 — Dispatch condicional externo (dict/if-elif/match/isinstance) por tipo é candidato a polimorfismo — regra geral, não só State

- **Categoria:** design-oo
- **Data:** 2026-08-19
- **Regra:** qualquer estrutura de despacho **fora** do(s) tipo(s) envolvido(s) — dict literal, cadeia `if/elif`, `match/case`, sequência de `isinstance` — que mapeia um discriminador de tipo (enum, string-tag, classe) para **comportamento que varia por esse tipo** é candidata a "Replace Conditional/Dict Dispatch with Polymorphism" (Fowler). Isso vale **independente de pattern nomeado**: não é só quando os tipos envolvidos são formalmente State/Strategy/Visitor — vale igual para um enum comum sem classe nenhuma, ou para duas classes quaisquer sem relação de pattern declarada. O que importa é a forma do problema (comportamento condicionado a tipo, decidido por fora), não o nome do pattern.
- **Motivação:** o Beto identificou o caso concreto em `REGISTRO_POR_FASE` (`backend/services/processador.py:90-93`) → `resolver_e_executar` (`services/conversacao/motor.py:58,70`), indexado por `FaseAtendimento`, e confirmou explicitamente que a regra deve valer para qualquer caso de polimorfismo, não só para esse exemplo ou para o State pattern especificamente. O projeto já declara esse princípio em `services/conversacao/estados/base.py`/`estados/esclarecendo.py` (GRASP Information Expert) — mas a motivação de fundo é o princípio geral, e o exemplo do State é só a primeira ocorrência encontrada, não o limite da regra.
- **Contexto de origem:** revisão manual do Beto em `backend/services/processador.py`, linhas 83-93 (`REGISTRO_POR_FASE`); generalizada nesta mesma sessão a pedido explícito do Beto.
- **Aplicação prática:** permitido — dispatch por tipo que só seleciona **dados/config** sem comportamento variável (ex.: dict de rótulos de exibição, links de catálogo, mensagens fixas) não é o mesmo smell — não sinalizar. Também não sinalizar quando o conjunto de casos é genuinamente fechado e não há indício de que vá crescer nem de duplicação do mesmo `if/dict` em outro lugar do código (evitar abstração especulativa só para "seguir a regra"). Proibido — deixar passar sem observação um dispatch externo que decide **comportamento** por tipo quando esse comportamento poderia/deveria morar no próprio tipo (classe existente, ou enum que ganharia método/atributo) — sinalizar como achado de design-oo mesmo que a correção não seja feita na hora, e mesmo que o tipo em questão não seja formalmente State/Strategy/Visitor.
