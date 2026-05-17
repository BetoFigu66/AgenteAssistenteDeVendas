# Análise: Agentes vs. Skills vs. Harness para Direcionamento de IA em Desenvolvimento

**Autores:** Arquiteto de Sistemas + Beto (análise conjunta)  
**Data:** 2025-05  
**Contexto:** Projeto Assistente de Vendas Inforrel — avaliação da estrutura atual (`agentes/`) e comparação com abordagens alternativas.

---

## 1. O que temos hoje (diagnóstico honesto)

Antes de comparar abordagens, é importante entender o que o projeto **realmente usa** hoje:

| Elemento | O que é no código | Como é usado na prática |
|---|---|---|
| `BaseAgente` + subclasses | Classes Python com `get_prompt_sistema()` | **Nunca instanciadas** pelo Cascade; ele assume o papel *textualmente* via `[prefixo]` |
| `Implementador.diretrizes.md` | Harness acumulativo de regras | **Lido pelo Cascade** como contrato ativo — o mais efetivo do projeto |
| `QAEngineer._REGISTRY` + `@registrar_check` | Registry de checks com decorator | **Executável** — único agente com lógica real rodável |
| `GerenteDeProjetos.gerar_relatorio_sprint()` | Gerador de texto estruturado | Chamado explicitamente quando pedido |
| `OrquestradorAgentes` | Coordenador centralizador | Nunca usado; coordenação acontece via chat |
| `AGENTS.md` / memória do Cascade | Regras globais de projeto | **O harness mais poderoso** — lido automaticamente em toda sessão |

**Conclusão do diagnóstico:** o projeto já usa as três abordagens, mas de forma desigual. O **harness** (`diretrizes.md` + `AGENTS.md`) é o que **realmente governa** o comportamento da IA. Os agentes Python são principalmente contêineres de prompts com pouca execução real.

---

## 2. Definição das três abordagens

### 2.1 Agentes (Approach atual)

Persona especializada com identidade, escopo e responsabilidade próprios. No projeto: classes Python com `get_prompt_sistema()` e diretório de artefatos dedicado.

```
[analista] → AnalistaRequisitos → prompt + dir artefatos/analista_de_requisitos/
[qa]       → QAEngineer          → prompt + checks executáveis
[gerente]  → GerenteDeProjetos   → prompt + gerador de relatórios
```

### 2.2 Skills

Capacidades discretas e reutilizáveis, **sem persona**. Não é "quem faz", mas "o que fazer". O QA já usa isso via `@registrar_check`.

```python
@registrar_check("imports-no-topo", "Imports devem estar no topo do arquivo", severidade="error")
def check_imports(projeto: Path) -> CheckResult: ...
```

Uma skill é uma função/ferramenta com contrato definido (entrada, saída, critério de aceite). Pode ser composta, encadeada, invocada por qualquer agente.

### 2.3 Harness

Documento/configuração que governa **como a IA deve se comportar** em qualquer contexto — independente de qual "papel" esteja exercendo. É o conjunto de regras, restrições e padrões acumulados do projeto.

No projeto: `artefatos/implementador/diretrizes.md` (D01–D04) e `AGENTS.md` na memória do Cascade.

---

## 3. Comparação detalhada

### 3.1 Agentes

| | Detalhe |
|---|---|
| **Ponto forte** | Contextualização rica: cada agente tem persona, tom e foco bem definidos |
| **Ponto forte** | Separação de responsabilidades clara (analista não faz código, QA não faz arquitetura) |
| **Ponto forte** | Diretório de artefatos por agente facilita rastreabilidade |
| **Ponto fraco** | Classes Python subutilizadas — o Cascade nunca chama `AnalistaRequisitos()` de verdade |
| **Ponto fraco** | Overhead de manutenção: 7 arquivos `.py` para funcionalidade principalmente textual |
| **Ponto fraco** | Duplicação: o contexto de cada agente existe tanto no `.py` quanto na memória do Cascade |
| **Ponto fraco** | Persona pode **restringir** respostas transversais — quando o problema é interdisciplinar, o prefixo atrapalha |
| **Quando usar** | Quando há tarefas bem delimitadas com persona distinta (entrevista de requisitos, revisão de PR, ADR) |

### 3.2 Skills

| | Detalhe |
|---|---|
| **Ponto forte** | Executáveis, testáveis, determinísticos — resultado não depende do "humor" da IA |
| **Ponto forte** | Composição fácil: skills podem ser encadeadas por qualquer agente ou workflow |
| **Ponto forte** | Contrato claro: assinatura `(Path) -> CheckResult` é mais confiável que texto gerado |
| **Ponto forte** | O QA já prova o valor: `@registrar_check` é o elemento mais *robusto* de toda a estrutura |
| **Ponto fraco** | Requer implementação real em Python — mais esforço inicial que um prompt |
| **Ponto fraco** | Cobre apenas tarefas automatizáveis; análise qualitativa ainda depende da IA |
| **Ponto fraco** | Manutenção de código extra (testes, versão, compatibilidade) |
| **Quando usar** | Validações repetíveis (linting, cobertura, padrões de commit, consistência de schema) |

### 3.3 Harness

| | Detalhe |
|---|---|
| **Ponto forte** | **O mais efetivo para governar comportamento da IA** — lido em toda sessão |
| **Ponto forte** | Acumulativo e versionado: cada erro vira regra permanente |
| **Ponto forte** | Baixo custo de manutenção: é só Markdown |
| **Ponto forte** | Agnóstico de papel — D01 "não mudar stack por ambiente" vale para qualquer prefixo de agente |
| **Ponto fraco** | Não executa nada — é apenas leitura de contexto; não detecta violações automaticamente |
| **Ponto fraco** | Pode crescer demais e perder sinal (regras antigas obscurecem novas) |
| **Ponto fraco** | Depende de o Cascade ler e respeitar as regras — sem enforcement automático |
| **Quando usar** | Sempre, como camada base. É o "sistema nervoso" sobre o qual agents e skills operam |

---

## 4. Análise de adequação por tipo de tarefa

| Tipo de tarefa | Agente | Skill | Harness |
|---|---|---|---|
| Entrevista de requisitos | ✅ ideal | ❌ | ✅ (via regras de tom) |
| Revisão de PR | 🟡 suficiente | ✅ ideal (checks automáticos) | ✅ (critérios de aceite) |
| Gerar ADR / decisão arquitetural | ✅ ideal | ❌ | ✅ (via template) |
| Detectar import fora do topo | ❌ | ✅ ideal | 🟡 (regra sem enforcement) |
| Criar migration Alembic | 🟡 | ❌ | ✅ ideal (D02 é suficiente) |
| Relatório de sprint | ✅ suficiente | 🟡 (template) | ✅ (via estrutura obrigatória) |
| Refactoring de código | ❌ | ❌ | ✅ ideal |
| Validar cobertura de testes | ❌ | ✅ ideal | 🟡 |

---

## 5. O problema real da abordagem atual

O projeto sofre de **estratificação invertida**: as classes Python (mais complexas) têm menos impacto prático que os documentos Markdown (mais simples). Isso cria:

1. **Ilusão de sistema** — parece que há um sistema sofisticado, mas o que governa o Cascade é `AGENTS.md` e `diretrizes.md`
2. **Manutenção desnecessária** — modificar `analista_requisitos.py` não muda nada na sessão atual do Cascade
3. **Confusão de propósito** — os agentes Python parecem código de produção, mas são scaffolding documental

A **exceção honrosa** é `QAEngineer` — ele tem checks executáveis reais e deveria ser o modelo a seguir para os demais.

---

## 6. Recomendação

### Abordagem recomendada: **Harness como base + Skills onde possível + Agentes como prompts leves**

```
┌─────────────────────────────────────────────────────────┐
│  HARNESS  (AGENTS.md + diretrizes.md)                   │
│  Governa: padrões, restrições, tom, D01..Dn             │
├─────────────────────────────────────────────────────────┤
│  SKILLS executáveis  (QA checks, validadores)           │
│  Governa: verificações automáticas, CI/CD               │
├─────────────────────────────────────────────────────────┤
│  AGENTES como prompts leves  (AGENTS.md, não .py)       │
│  Governa: contextualização, tom, diretório de artefatos │
└─────────────────────────────────────────────────────────┘
```

### Ações concretas sugeridas

**Manter (alto valor, baixo custo):**
- `AGENTS.md` com tabela de agentes e convenção `[prefixo]` → é o harness mais efetivo
- `artefatos/implementador/diretrizes.md` → continuar acumulando D0N
- `QAEngineer._REGISTRY` → expandir checks executáveis

**Simplificar (baixo valor, alto custo de manutenção):**
- `analista_requisitos.py`, `arquiteto_sistemas.py`, `auxiliar_negocios.py`, `planejador_negocios.py` → condensar `get_prompt_sistema()` de cada um em seções do `AGENTS.md`; remover a classe Python ou deixar como rascunho não versionado
- `OrquestradorAgentes` → não tem uso real; pode ser removido

**Evoluir (potencial não explorado):**
- Transformar regras do harness em **checks executáveis** onde possível  
  Ex: D02 "toda migration via Alembic" → skill que verifica se há DDL solto em `*.py`
- Criar `skills/` com funções puras e testáveis para as validações mais críticas

**Não fazer:**
- Não integrar os agentes Python ao ciclo de conversação com chamadas reais — a latência e complexidade não compensam versus simplesmente usar `[prefixo]` como convenção textual

---

## 7. Resumo visual

```
Abordagem   Custo impl.  Efetividade atual  Escalabilidade  Executável?
─────────────────────────────────────────────────────────────────────────
Agentes .py    Alto          Baixa              Média            Não*
Skills         Médio         Alta (onde usada)  Alta             Sim
Harness .md    Baixo         Alta               Média            Não

* Exceto QAEngineer que tem checks reais
```

**Bottom line:** o harness (`AGENTS.md` + `diretrizes.md`) é o elemento mais valioso e de menor custo. Skills executáveis são o investimento com maior ROI. As classes Python de agente adicionam pouca margem sobre simplesmente escrever o prompt no `AGENTS.md`.
