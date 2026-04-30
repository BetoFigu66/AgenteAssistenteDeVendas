# Gerente de Projetos — Artefatos

Diretório dos artefatos gerados pelo agente `GerenteDeProjetos`. O principal fluxo é o **Sprint Review**, que segue a diretriz **D03** (`artefatos/implementador/diretrizes.md`).

---

## Fluxo Sprint Review

```
gerar_dados_sprint_yaml(...)    →  sprint_NN_YYYYMMDD.yaml     (FONTE ÚNICA, versionado)
                                           │
                                           ▼
gerar_apresentacao_pptx(yaml)   →  sprint_review_NN_YYYYMMDD.pptx  (apresentação, NÃO versionado)
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
    proximo_sprint=[
        {"titulo": "Deploy via Cloudflare Tunnel", "prioridade": "alta"},
    ],
    backlog_pendente=[
        {"titulo": "Multi-tenancy"},
    ],
    bloqueios=["Decidir provider LLM de produção"],
    insights=["Ciclo de 2 semanas bate com a capacidade atual."],
)

gp.gerar_apresentacao_pptx(yaml_path)
```

---

## Tokens aceitos no template `.pptx`

O template `sprint_review_template_v01.pptx` deve conter os tokens abaixo no texto dos slides (e, se houver métrica em tabela, nas células). A substituição busca o texto **literal** `{{token}}`.

### Tokens simples (substituição de texto)

| Token | Descrição |
|-------|-----------|
| `{{sprint_numero}}` | Número do sprint com 2 dígitos (ex: `02`) |
| `{{data_inicio}}` | Data de início formatada `DD/MM/AAAA` |
| `{{data_fim}}` | Data de fim formatada `DD/MM/AAAA` |
| `{{duracao_dias}}` | Duração do sprint em dias |
| `{{proximo_sprint_inicio}}` | Data de início do próximo sprint |
| `{{proximo_sprint_fim}}` | Data de fim do próximo sprint |
| `{{gerado_em}}` | Timestamp da geração dos dados |
| `{{metrica_artefatos_criados}}` | Contagem de artefatos |
| `{{metrica_pendencias_resolvidas}}` | Pendências resolvidas no sprint |
| `{{metrica_pendencias_novas}}` | Pendências novas |
| `{{metrica_bugs_corrigidos}}` | Bugs corrigidos |
| `{{metrica_reports_total}}` | Total de reports |
| `{{metrica_reports_resolvidos}}` | Reports resolvidos |

### Tokens de lista (duplicam o parágrafo)

Para estes tokens, coloque **um parágrafo** no slide contendo o token. O gerador duplica o parágrafo (preservando formatação, bullets, fonte) uma vez para cada item. Se a lista estiver vazia, o parágrafo recebe um texto padrão do tipo `(nenhum)`.

| Token | Fonte no YAML | Formato do texto resultante |
|-------|---------------|------------------------------|
| `{{feito}}` | `feito[]` | `titulo — agente: descricao` |
| `{{proximo_sprint}}` | `proximo_sprint[]` | `🔴 titulo (alta)` (emoji depende da prioridade) |
| `{{backlog_pendente}}` | `backlog_pendente[]` | `titulo` |
| `{{bloqueios}}` | `bloqueios[]` | texto literal do item |
| `{{insights}}` | `insights[]` | texto literal do item |

### Como inserir tokens no PowerPoint

1. Abrir `sprint_review_template_v01.pptx`.
2. No slide desejado, clicar na caixa de texto e digitar o token exatamente como documentado, **sem formatação extra no meio** (ex: evitar `{{` e `}}` com fontes diferentes, o que quebra a substituição).
3. Para listas: colocar **um único** parágrafo com o token. Se o parágrafo estiver com bullet, todos os itens gerados herdam o bullet.
4. Para métricas em tabela: colocar o token na célula correspondente.
5. Salvar o template e rodar `gerar_apresentacao_pptx(...)`.

> **Dica:** se um token não estiver sendo substituído, o motivo mais comum é que o PowerPoint dividiu `{{...}}` em múltiplos "runs" com formatação diferente. Solução: selecionar o token inteiro, aplicar a mesma formatação (ex: `Ctrl+Barra` ou retipar).

---

## Estrutura do YAML

```yaml
sprint_numero: 2
data_inicio: "2026-04-22"
data_fim: "2026-05-05"
duracao_dias: 14
proximo_sprint_inicio: "2026-05-06"
proximo_sprint_fim: "2026-05-19"
gerado_em: "2026-04-29 10:30"

feito:
  - titulo: "Refatorar provider LLM"
    agente: "Implementador"
    descricao: "Extraída interface base; Groq isolado."

proximo_sprint:
  - titulo: "Deploy via Cloudflare Tunnel"
    prioridade: "alta"

backlog_pendente:
  - titulo: "Multi-tenancy"

bloqueios:
  - "Decidir provider LLM de produção"

metricas:
  artefatos_criados: 12
  pendencias_resolvidas: 8
  pendencias_novas: 3
  bugs_corrigidos: 2
  reports_total: 0
  reports_resolvidos: 0

insights:
  - "Ciclo de 2 semanas bate com a capacidade atual."
```

Template de referência: `template_sprint.yaml`.

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
