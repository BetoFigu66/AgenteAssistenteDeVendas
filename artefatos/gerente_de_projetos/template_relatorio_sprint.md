# 📊 Template de Relatório de Sprint

**Sprint**: Número X  
**Período**: DD/MM/AAAA → DD/MM/AAAA (14 dias)  
**Gerado em**: DD/MM/AAAA HH:MM

---

## 🎯 Visão Geral do Sprint

Resumo executivo do que foi alcançado neste Sprint, destacando os principais marcos e entregas de valor.

---

## ✅ Feito neste Sprint (Done)

### 1. [Título da entrega]
**Responsável**: [Agente/Nome]  
Descrição detalhada do que foi implementado, incluindo:
- Objetivo da entrega
- Decisões técnicas importantes
- Arquivos/artefatos criados ou modificados

### 2. [Título da entrega]
**Responsável**: [Agente/Nome]  
...

---

## 🎯 Próximo Sprint (Planejado)

Itens priorizados para as próximas 2 semanas:

1. 🔴 **[Título]** (alta prioridade)
2. 🟡 **[Título]** (média prioridade)
3. 🟢 **[Título]** (baixa prioridade)

---

## 📋 Backlog Total Pendente

Itens do escopo completo que ainda não foram iniciados:

1. [Título/descrição breve]
2. [Título/descrição breve]
3. ...

---

## 🚨 Bloqueios e Riscos

- 🔴 [Descrição do bloqueio e plano de mitigação]
- 🟡 [Risco identificado e ação preventiva]

---

## 📈 Métricas do Sprint

| Métrica | Valor |
|---------|-------|
| 📄 Artefatos criados | X |
| ✅ Pendências resolvidas | X |
| 🆕 Pendências novas | X |
| 🐛 Bugs corrigidos | X |
| 🕐 Total de reports | X |
| 🔧 Reports resolvidos | X |

---

## 💡 Insights e Próximos Passos

1. **Velocidade**: [Observações sobre capacidade de entrega]
2. **Qualidade**: [Observações sobre bugs e reports]
3. **Priorização**: [Ajustes necessários no backlog]

---

## 📝 Como Usar este Template

Para gerar um relatório de Sprint, use o agente Gerente de Projetos:

```python
from agentes import GerenteDeProjetos
from datetime import datetime

gp = GerenteDeProjetos()

caminho_relatorio = gp.gerar_relatorio_sprint(
    sprint_numero=1,
    data_inicio=datetime(2026, 4, 8),
    data_fim=datetime(2026, 4, 21),
    feito=[
        {
            "titulo": "Implementar sistema de triagem de reports",
            "descricao": "Criado workflow completo de captura, triagem e resolução de problemas em processamentos.",
            "agente": "Implementador"
        },
        {
            "titulo": "Corrigir extração de nomes em mensagens com CNPJ",
            "descricao": "Adicionado regex para extrair nomes quando regra detecta CNPJ, evitando perda de dados.",
            "agente": "Implementador"
        }
    ],
    proximo_sprint=[
        {"titulo": "Integrar relatórios de Sprint ao frontend", "prioridade": "alta"},
        {"titulo": "Implementar dashboard de métricas", "prioridade": "media"}
    ],
    backlog_pendente=[
        {"titulo": "Multi-tenancy da aplicação"},
        {"titulo": "Deploy em produção"}
    ],
    bloqueios=["Definir provedor LLM para produção"]
)

print(f"Relatório gerado em: {caminho_relatorio}")
```

---

*Template v1.0 - Gerente de Projetos*
