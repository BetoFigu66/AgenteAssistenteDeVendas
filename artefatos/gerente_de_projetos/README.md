# Gerente de Projetos — Artefatos

Diretório dos artefatos gerados pelo agente `GerenteDeProjetos`. O principal fluxo é o **Sprint Review**, regido pelas diretrizes [`G01`](./diretrizes.md#g01--sprint-review-yaml-é-fonte-única-pptx-é-derivado), [`G03`](./diretrizes.md#g03--versionamento-da-pasta-de-sprint-review), [`G04`](./diretrizes.md#g04--tokens-do-template-e-yaml-devem-casar) e [`G05`](./diretrizes.md#g05--pptx-é-editável-apenas-para-formatação-visual) deste agente.

> **Estrutura dos arquivos deste diretório:**
> - [`diretrizes.md`](./diretrizes.md) — regras numeradas (G01-G0N), curtas e estáveis. **Fonte da verdade das regras.**
> - `README.md` (este arquivo) — documentação narrativa: como o fluxo funciona, lista de tokens do template, estrutura do YAML, exemplos de uso.

Os scripts auxiliares de geração estão em `agentes/scripts/gerente_de_projetos/` e incluem versões para WSL/Linux/macOS (`.sh`) e Windows (`.bat`).

---

## Fluxo Sprint Review

```
gerar_dados_sprint_yaml(...)    →  sprint_NN_YYYYMMDD.yaml     (FONTE ÚNICA, versionado)
                                           │
                                           ▼
python agentes/scripts/gerente_de_projetos/gera_sprint_report.py <yaml> [template.pptx] -o <saida.pptx>
                                  usando  sprint_review_template_v01.pptx
```

**Regra:** conteúdo textual só é editado no YAML. O PPTX é regerado a cada alteração. Ajustes no PPTX são aceitáveis apenas para **formatação visual** (posição, fonte, cor), nunca para texto.

### Exemplo de uso

```python
from datetime import datetime
from agentes import GerenteDeProjetos

gp = GerenteDeProjetos()

yaml_path = gp.gerar_dados_sprint_yaml(
    sprint_numero=2,
    data_inicio=datetime(2026, 4, 22),
    data_fim=datetime(2026, 5, 5),
    feito=[
        {"titulo": "Refatorar provider LLM", "agente": "Implementador",
         "descricao": "Extraída interface base; Groq isolado."},
    ],
    proximasprint=[
        "Deploy via Cloudflare Tunnel - alta",
    ],
    backlogpendente=[
        "Multi-tenancy",
    ],
    bloqueios=["Decidir provider LLM de produção"],
    insights=["Ciclo de 2 semanas bate com a capacidade atual."],
)

# Gerar o PPTX a partir do YAML:
# bash/WSL:
# python agentes/scripts/gerente_de_projetos/gera_sprint_report.py artefatos/gerente_de_projetos/sprint_02_20260510_externo.yaml artefatos/gerente_de_projetos/sprint_review_template_externo_v01.pptx -o /tmp/sprint_02_20260510_externo.pptx
# PowerShell / cmd:
# .\.venv\Scripts\Activate.ps1
# python agentes\scripts\gerente_de_projetos\gera_sprint_report.py artefatos\gerente_de_projetos\sprint_02_20260510_externo.yaml artefatos\gerente_de_projetos\sprint_review_template_externo_v01.pptx -o C:\tmp\sprint_02_20260510_externo.pptx
```

## Executar via script

### WSL / Linux / macOS
```bash
./agentes/scripts/gerente_de_projetos/gera_report_sprint_interno.sh
./agentes/scripts/gerente_de_projetos/gera_report_sprint_externo.sh
```

### PowerShell / cmd
```powershell
.
# ou, se estiver em PowerShell:
Start-Process -NoNewWindow -FilePath ".\agentes\scripts\gerente_de_projetos\gera_report_sprint_interno.bat"
Start-Process -NoNewWindow -FilePath ".\agentes\scripts\gerente_de_projetos\gera_report_sprint_externo.bat"
```

---

## Tokens aceitos no template `.pptx`

Os nomes dos tokens são livres, porém devem estar compatíveis entre template e yaml de dados.
Para a primeira versão dos dados gerados (yaml), template `sprint_review_template_v01.pptx` deve conter os tokens abaixo no texto dos slides (e, se houver métrica em tabela, nas células). A substituição busca o texto **literal** `{{token}}`.

### Tokens simples (substituição de texto)

| Token | Descrição |
|-------|-----------|
| `{{sprint_numero}}` | Número do sprint |
| `{{data_inicio}}` | Data de início formatada `DD/MM/AAAA` |
| `{{data_fim}}` | Data de fim formatada `DD/MM/AAAA` |
| `{{duracao_dias}}` | Duração do sprint em dias |
| `{{proximo_sprint_numero}}` | Número do próximo sprint |
| `{{proximo_data_inicio}}` | Data de início do próximo sprint |
| `{{proximo_data_fim}}` | Data de fim do próximo sprint |
| `{{proximo_duracao_dias}}` | Duração do próximo sprint |
| `{{gerado_em}}` | Timestamp da geração dos dados |
| `{{revisado_em}}` | Timestamp da revisão dos dados |
| `{{metricas.artefatos_criados}}` | Contagem de artefatos |
| `{{metricas.pendencias_resolvidas}}` | Pendências resolvidas no sprint |
| `{{metricas.pendencias_novas}}` | Pendências novas |
| `{{metricas.bugs_corrigidos}}` | Bugs corrigidos |
| `{{metricas.reports_total}}` | Total de reports |
| `{{metricas.reports_resolvidos}}` | Reports resolvidos |
| `{{metricas.diretrizes_novas}}` | Diretrizes novas |
| `{{metricas.passos_qa_pairs_concluidos}}` | Pares de Q&A concluídos |
| `{{metricas.cobertura_req_atendidos}}` | Requisitos atendidos |

### Tokens de lista (duplicam o parágrafo)

Coloque **um parágrafo** no slide contendo o token. O gerador duplica o parágrafo (preservando formatação, bullets, fonte) uma vez para cada item. Se a lista estiver vazia, o parágrafo recebe um texto padrão do tipo `(nenhum)`.

| Token | Fonte no YAML | Formato do texto resultante |
|-------|---------------|------------------------------|
| `{{feito}}` | `feito[]` | texto do item de lista (geralmente `titulo` e/ou `descricao`) |
| `{{feito.titulo}}` | `feito[].titulo` | título de cada item |
| `{{feito.agente}}` | `feito[].agente` | agente de cada item |
| `{{proximasprint}}` / `{{proximo_sprint}}` | `proximasprint[]` ou `proximo_sprint[]` | texto literal de cada item |
| `{{backlogpendente}}` / `{{backlog_pendente}}` / `{{backlog}}` | `backlogpendente[]` ou `backlog_pendente[]` | texto literal de cada item |
| `{{riscos_e_impedimentos}}` / `{{bloqueios}}` *(alias legado)* | `riscos_e_impedimentos[]` (lista de dicts com `nome`, `tipo`, `motivo`, `acao_esperada`) | concatenação dos itens — use preferencialmente `{{SLIDE:riscos_e_impedimentos}}` |
| `{{insights}}` | `insights[]` | texto literal do item |
| `{{objetivos}}` | `objetivos[]` | texto literal do item |
| `{{proximo_objetivos}}` | `proximo_objetivos[]` | texto literal do item |

### Paginação por slide com limite de itens

O template também aceita sintaxe de limite para listas, com `{{chave:limite}}` ou `{{chave|limite}}`.

- Quando a lista tem mais itens do que o limite, o slide é clonado automaticamente.
- Cada slide recebe um subconjunto (chunk) da lista.
- A sintaxe funciona em qualquer token de lista suportado.

**Exemplo:** `{{backlogpendente:7}}` cria vários slides de backlog com no máximo 7 itens por slide.

### Tokens de replicação por slide

Se quiser que um **slide inteiro** seja replicado uma vez por item, use `{{SLIDE:chave}}` em qualquer caixa de texto do template. O gerador:
1. clona o slide N vezes (uma por item)
2. substitui sub-tokens em cada cópia
3. remove o slide template original

| Token no slide | Chave YAML | Sub-tokens disponíveis |
|---|---|---|
| `{{SLIDE:feito}}` | `feito` | `{{feito_titulo}}`, `{{feito_agente}}`, `{{feito_descricao}}` |
| `{{SLIDE:proximasprint}}` / `{{SLIDE:proximo_sprint}}` | `proximasprint` / `proximo_sprint` | `{{proximo_sprint_titulo}}`, `{{proximo_sprint_prioridade}}`, `{{proximo_sprint_emoji}}` |
| `{{SLIDE:backlogpendente}}` / `{{SLIDE:backlog_pendente}}` / `{{SLIDE:backlog}}` | `backlogpendente` / `backlog_pendente` | `{{backlog_titulo}}` |
| `{{SLIDE:riscos_e_impedimentos}}` / `{{SLIDE:bloqueios}}` *(alias legado)* | `riscos_e_impedimentos` | `{{riscos_e_impedimentos_nome}}`, `{{riscos_e_impedimentos_tipo}}`, `{{riscos_e_impedimentos_motivo}}`, `{{riscos_e_impedimentos_acao_esperada}}` (e equivalentes com ponto: `{{riscos_e_impedimentos.nome}}`, etc.) |
| `{{SLIDE:insights}}` | `insights` | `{{insight_texto}}` |
| `{{SLIDE:objetivos}}` | `objetivos` | `{{objetivo_texto}}` |
| `{{SLIDE:proximo_objetivos}}` | `proximo_objetivos` | `{{proximo_objetivo_texto}}` |

**Exemplo:** slide com layout de card para cada item de `feito`:
```
[caixa título]   {{feito_titulo}}  {{SLIDE:feito}}
[caixa agente]   {{feito_agente}}
[caixa desc]     {{feito_descricao}}
```

### Como inserir tokens no PowerPoint

1. Abrir `sprint_review_template_v01.pptx`.
2. No slide desejado, clicar na caixa de texto e digitar o token exatamente como documentado, **sem formatação extra no meio** (ex: evitar `{{` e `}}` com fontes diferentes, o que quebra a substituição).
3. Para listas: colocar **um único** parágrafo com o token. Se o parágrafo estiver com bullet, todos os itens gerados herdam o bullet.
4. Para métricas em tabela: colocar o token na célula correspondente.
5. Salvar o template e rodar `python agentes/scripts/gerente_de_projetos/gera_sprint_report.py`.

> **Dica:** se um token não estiver sendo substituído, o motivo mais comum é que o PowerPoint dividiu `{{...}}` em múltiplos "runs" com formatação diferente. Solução: selecionar o token inteiro, aplicar a mesma formatação ou retipar o texto.

---

## Estrutura proposta inicialmente para o YAML

```yaml
sprint_numero: 2
data_inicio: "2026-04-22"
data_fim: "2026-05-05"
duracao_dias: 14
proximo_sprint_numero: 3
proximo_data_inicio: "2026-05-06"
proximo_data_fim: "2026-05-19"
proximo_duracao_dias: 14
gerado_em: "2026-04-29 10:30"
revisado_em: "2026-04-29 15:00"

feito:
  - titulo: "Refatorar provider LLM"
    agente: "Implementador"
    descricao: "Extraída interface base; Groq isolado."

proximasprint:
  - "Deploy via Cloudflare Tunnel - alta"

backlogpendente:
  - "Multi-tenancy"

riscos_e_impedimentos:
  - nome: "Decidir provider LLM de produção"
    tipo: "🔴 alta"          # 🔴 alta | 🟡 media | 🟢 baixa
    motivo: "Sem decisão, deploy fica inviável (rate limits ou custo)."
    acao_esperada: "ADR conjunto [arquiteto] + [planejador] antes da Sprint N+1."

metricas:
  artefatos_criados: 12
  pendencias_resolvidas: 8
  pendencias_novas: 3
  bugs_corrigidos: 2
  reports_total: 0
  reports_resolvidos: 0
  diretrizes_novas: 1
  passos_qa_pairs_concluidos: 9
  cobertura_req_atendidos: 2

insights:
  - "Ciclo de 2 semanas bate com a capacidade atual."

objetivos:
  - "Melhorar cobertura de QA"

proximo_objetivos:
  - "Integrar WhatsApp Business"
```

***Observação:*** O script aceita variantes de chaves para compatibilidade com templates antigos. Por exemplo, `proximasprint` e `proximo_sprint` são equivalentes, assim como `backlogpendente`, `backlog_pendente` e `backlog`.

---

## O que é versionado nesta pasta

| Arquivo | Versionado? |
|---------|-------------|
| `sprint_NN_YYYYMMDD.yaml` | ✅ sim (fonte da verdade) |
| `sprint_review_NN_YYYYMMDD.pptx` | ❌ não (gerado, derivado) |
| `sprint_review_template_*.pptx` | ✅ sim (template) |
| `template_sprint.yaml` | ✅ sim (referência humana) |
| `README.md` (este arquivo) | ✅ sim |
| Demais `.md` históricos | ✅ sim (arquivos legados até migração completa) |
