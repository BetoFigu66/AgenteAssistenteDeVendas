"""
Agente Gerente de Projetos
Responsável por gestão ágil do projeto, relatórios de Sprint e coordenação dos agentes.
"""
from .base_agente import BaseAgente
from pathlib import Path
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class GerenteDeProjetos(BaseAgente):
    """
    Gerente de Projetos - Gestão ágil, relatórios de Sprint e coordenação.
    
    Responsabilidades:
    - Conduzir cerimônias de Sprint (planning, daily, review, retrospectiva)
    - Gerar relatórios de Sprint (a cada 2 semanas)
    - Priorizar backlog e pendências
    - Coordenar trabalho entre agentes
    - Alertar sobre bloqueios e dependências
    - Manter visão geral do projeto
    """
    
    def __init__(self, projeto_root: str = None):
        super().__init__(
            nome="Gerente de Projetos",
            papel="Gerenciar o projeto de forma ágil, gerar relatórios de Sprint e coordenar agentes",
            projeto_root=projeto_root
        )
        self.agentes_gerenciados = [
            "Analista de Requisitos",
            "Auxiliar de Negocios", 
            "Arquiteto de Sistemas",
            "Planejador de Negocios",
            "QA Engineer",
            "Implementador"
        ]
        
        # Configurações de Sprint (padrão: 2 semanas)
        self.duracao_sprint_dias = 14
    
    def get_prompt_sistema(self) -> str:
        return """Você é o Gerente de Projetos do projeto, responsável por conduzir o desenvolvimento de forma ágil.

Seu papel é:
1. **Gestão de Sprint**: Relatórios a cada 2 semanas (feito → próximo → pendente)
2. **Cerimônias ágeis**: Planning, daily, review, retrospectiva
3. **Priorização**: Ordenar backlog e pendências por valor/urgência
4. **Coordenação**: Alinhar trabalho entre agentes e remover impedimentos
5. **Comunicação**: Relatórios claros de progresso para stakeholders

Agentes sob sua coordenação:
1. **Analista de Requisitos**: Brainstorms e documentação de requisitos
2. **Auxiliar de Negócios**: Transformar ideia em produto
3. **Arquiteto de Sistemas**: Propor arquiteturas (POC, single, multi-tenant)
4. **Planejador de Negócios**: Monetização e estratégia comercial
5. **QA Engineer**: Qualidade de código e processos
6. **Implementador**: Governança e padrões de implementação

Estrutura de Relatório de Sprint:
- 📊 **Visão Geral**: Resumo executivo do Sprint
- ✅ **Feito (Done)**: O que foi entregue neste Sprint
- 🎯 **Próximo Sprint**: O que está planejado para as próximas 2 semanas
- 📋 **Backlog Pendente**: O que ainda falta do escopo total
- 🚨 **Bloqueios/Riscos**: Impedimentos e mitigações
- 📈 **Métricas**: Artefatos criados, pendências resolvidas/novas, bugs corrigidos

Formato de status:
- 🟢 Concluído
- 🟡 Em andamento
- 🔴 Bloqueado
- ⚪ Não iniciado"""

    def get_contexto(self) -> dict:
        return {
            "agente": self.nome,
            "papel": self.papel,
            "agentes_gerenciados": self.agentes_gerenciados,
            "artefatos": self.listar_artefatos(),
            "pendencias": self.obter_pendencias()
        }
    
    def obter_status_geral(self) -> dict:
        """Obtém status de todos os agentes e suas pendências."""
        projeto_root = Path(self.projeto_root)
        artefatos_root = projeto_root / "artefatos"
        
        status = {
            "data": datetime.now().isoformat(),
            "agentes": {}
        }
        
        for agente in self.agentes_gerenciados:
            nome_pasta = agente.lower().replace(" ", "_").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
            pasta_agente = artefatos_root / nome_pasta
            
            artefatos = []
            pendencias = []
            
            if pasta_agente.exists():
                artefatos = [f.name for f in pasta_agente.iterdir() if f.is_file() and f.name != "pendencias.json"]
                
                arquivo_pendencias = pasta_agente / "pendencias.json"
                if arquivo_pendencias.exists():
                    with open(arquivo_pendencias, 'r', encoding='utf-8') as f:
                        pendencias = json.load(f)
            
            status["agentes"][agente] = {
                "artefatos": artefatos,
                "total_artefatos": len(artefatos),
                "pendencias": pendencias,
                "pendencias_abertas": len([p for p in pendencias if p.get("status") == "pendente"])
            }
        
        return status
    
    def gerar_relatorio_sprint(
        self,
        sprint_numero: int,
        data_inicio: datetime,
        data_fim: datetime,
        feito: List[Dict],
        proximo_sprint: List[Dict],
        backlog_pendente: List[Dict],
        bloqueios: List[str] = None,
        metricas: Dict = None
    ) -> str:
        """
        Gera relatório de Sprint no formato padrão (a cada 2 semanas).
        
        Args:
            sprint_numero: Número do Sprint (1, 2, 3...)
            data_inicio: Data de início do Sprint
            data_fim: Data de término do Sprint
            feito: Lista de itens entregues [{"titulo": str, "descricao": str, "agente": str}]
            proximo_sprint: Lista do planejado [{"titulo": str, "prioridade": str}]
            backlog_pendente: Itens ainda não iniciados do escopo total
            bloqueios: Lista de impedimentos atuais
            metricas: Dict com contagens (artefatos, pendencias, bugs, etc.)
        """
        if metricas is None:
            metricas = self._calcular_metricas_sprint(data_inicio, data_fim)
        
        if bloqueios is None:
            bloqueios = []
        
        # Cabeçalho
        conteudo = f"""# 📊 Relatório de Sprint {sprint_numero}

**Período**: {data_inicio.strftime('%d/%m/%Y')} → {data_fim.strftime('%d/%m/%Y')}  
**Gerado em**: {datetime.now().strftime('%d/%m/%Y %H:%M')}  
**Duração**: {self.duracao_sprint_dias} dias

---

## 🎯 Visão Geral do Sprint

Este relatório apresenta o progresso do projeto nas últimas 2 semanas, 
com entregas realizadas, planejamento para o próximo ciclo e itens pendentes.

---

## ✅ Feito neste Sprint (Done)

Itens entregues e concluídos:

"""
        
        # Seção Feito
        if feito:
            for i, item in enumerate(feito, 1):
                agente = item.get('agente', 'Time')
                conteudo += f"""### {i}. {item.get('titulo', 'Sem título')}
**Responsável**: {agente}  
{item.get('descricao', 'Sem descrição')}

"""
        else:
            conteudo += "_Nenhum item entregue neste período._\n\n"
        
        # Seção Próximo Sprint
        conteudo += f"""---

## 🎯 Próximo Sprint (Planejado)

Itens priorizados para as próximas 2 semanas ({(data_fim + timedelta(days=1)).strftime('%d/%m/%Y')} → {(data_fim + timedelta(days=self.duracao_sprint_dias)).strftime('%d/%m/%Y')}):

"""
        
        if proximo_sprint:
            for i, item in enumerate(proximo_sprint, 1):
                prioridade = item.get('prioridade', 'media')
                emoji_prio = {"alta": "🔴", "media": "🟡", "baixa": "🟢"}.get(prioridade, "⚪")
                conteudo += f"{i}. {emoji_prio} **{item.get('titulo', 'Sem título')}** ({prioridade})\n"
        else:
            conteudo += "_Backlog em definição._\n"
        
        # Seção Backlog Pendente
        conteudo += f"""
---

## 📋 Backlog Total Pendente

Itens do escopo completo que ainda não foram iniciados:

"""
        
        if backlog_pendente:
            for i, item in enumerate(backlog_pendente, 1):
                conteudo += f"{i}. {item.get('titulo', 'Sem título')}\n"
        else:
            conteudo += "_Todos os itens do escopo foram iniciados ou concluídos! 🎉_\n"
        
        # Seção Bloqueios
        conteudo += f"""
---

## 🚨 Bloqueios e Riscos

"""
        
        if bloqueios:
            conteudo += "Impedimentos identificados:\n\n"
            for bloqueio in bloqueios:
                conteudo += f"- 🔴 {bloqueio}\n"
        else:
            conteudo += "✅ Nenhum bloqueio crítico identificado.\n"
        
        # Seção Métricas
        conteudo += f"""
---

## � Métricas do Sprint

| Métrica | Valor |
|---------|-------|
| 📄 Artefatos criados | {metricas.get('artefatos_criados', 0)} |
| ✅ Pendências resolvidas | {metricas.get('pendencias_resolvidas', 0)} |
| 🆕 Pendências novas | {metricas.get('pendencias_novas', 0)} |
| 🐛 Bugs corrigidos | {metricas.get('bugs_corrigidos', 0)} |
| 🕐 Total de reports | {metricas.get('reports_total', 0)} |
| 🔧 Reports resolvidos | {metricas.get('reports_resolvidos', 0)} |

---

## 💡 Insights e Próximos Passos

Baseado no progresso atual:

1. **Velocidade**: Ajustar planejamento para próximo sprint baseado na capacidade de entrega
2. **Qualidade**: Monitorar métricas de bugs e reports para melhoria contínua
3. **Priorização**: Reavaliar backlog pendente conforme feedback de stakeholders

---

*Relatório gerado automaticamente pelo Agente Gerente de Projetos*  
*Template: Sprint Report v1.0*
"""
        
        nome_arquivo = f"relatorio_sprint_{sprint_numero:02d}_{data_fim.strftime('%Y%m%d')}.md"
        return str(self.criar_artefato(nome_arquivo, conteudo, tipo="relatorio_sprint"))
    
    def _calcular_metricas_sprint(self, data_inicio: datetime, data_fim: datetime) -> Dict:
        """Calcula métricas automáticas do período do Sprint."""
        status = self.obter_status_geral()
        
        # Contagem básica de artefatos e pendências
        total_artefatos = sum(d["total_artefatos"] for d in status["agentes"].values())
        total_pendencias = sum(d["pendencias_abertas"] for d in status["agentes"].values())
        
        # Contagem de pendências resolvidas (estimativa baseada no histórico)
        historico = self.listar_historico(dias=self.duracao_sprint_dias)
        interacoes = len(historico)
        
        return {
            "artefatos_criados": total_artefatos,
            "pendencias_resolvidas": max(0, interacoes - total_pendencias),  # Estimativa
            "pendencias_novas": total_pendencias,
            "bugs_corrigidos": 0,  # Será preenchido manualmente ou via integração futura
            "reports_total": 0,    # Via query ao banco futuramente
            "reports_resolvidos": 0
        }
    
    def gerar_relatorio_status(self) -> str:
        """Gera relatório de status do projeto (visualização rápida, não Sprint)."""
        status = self.obter_status_geral()
        
        conteudo = f"""# 📋 Relatório de Status do Projeto

**Data**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  
**Gerado por**: Gerente de Projetos

## Visão Geral por Agente

"""
        total_artefatos = 0
        total_pendencias = 0
        
        for agente, dados in status["agentes"].items():
            total_artefatos += dados["total_artefatos"]
            total_pendencias += dados["pendencias_abertas"]
            
            emoji = "🟢" if dados["pendencias_abertas"] == 0 and dados["total_artefatos"] > 0 else "🟡" if dados["total_artefatos"] > 0 else "⚪"
            
            conteudo += f"""### {emoji} {agente}
- **Artefatos**: {dados['total_artefatos']} | **Pendências abertas**: {dados['pendencias_abertas']}

"""
            if dados["pendencias"]:
                conteudo += "**Pendências ativas**:\n"
                for pend in dados["pendencias"][:5]:  # Limita a 5
                    status_emoji = "✅" if pend.get("status") == "concluido" else "⏳"
                    prio = pend.get("prioridade", "media")
                    conteudo += f"- {status_emoji} [{prio}] {pend.get('descricao', 'N/A')}\n"
                conteudo += "\n"
        
        conteudo += f"""## Resumo Executivo
- **Total de artefatos**: {total_artefatos}
- **Pendências abertas**: {total_pendencias}
- **Status geral**: {"🟢 Saudável" if total_pendencias < 5 else "🟡 Atenção" if total_pendencias < 10 else "🔴 Crítico"}

---
*Para relatório completo de Sprint, use `gerar_relatorio_sprint()`*
"""
        
        return str(self.criar_artefato(
            f"relatorio_status_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
            conteudo,
            tipo="relatorio_status"
        ))
    
    def listar_historico(self, dias: int = 7) -> list:
        """Lista histórico de interações dos últimos N dias."""
        historico_completo = []
        
        for arquivo in self.historico_dir.glob("ata_*.json"):
            with open(arquivo, 'r', encoding='utf-8') as f:
                registros = json.load(f)
                historico_completo.extend(registros)
        
        # Ordena por data
        historico_completo.sort(key=lambda x: x.get("data", ""), reverse=True)
        
        return historico_completo
    
    def gerar_ata_reuniao(self, participantes: list, pauta: list, decisoes: list, proximos_passos: list):
        """Gera ata de reunião formal."""
        conteudo = f"""# Ata de Reunião

**Data**: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Participantes
"""
        for p in participantes:
            conteudo += f"- {p}\n"
        
        conteudo += "\n## Pauta\n"
        for i, item in enumerate(pauta, 1):
            conteudo += f"{i}. {item}\n"
        
        conteudo += "\n## Decisões\n"
        for i, decisao in enumerate(decisoes, 1):
            conteudo += f"{i}. {decisao}\n"
        
        conteudo += "\n## Próximos Passos\n"
        for passo in proximos_passos:
            conteudo += f"- [ ] **{passo.get('responsavel', 'A definir')}**: {passo.get('acao', 'N/A')} (Prazo: {passo.get('prazo', 'A definir')})\n"
        
        nome_arquivo = f"ata_reuniao_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
        return self.criar_artefato(nome_arquivo, conteudo, tipo="ata")
    
    def alertar_pendencias_criticas(self) -> list:
        """Identifica e retorna pendências críticas de todos os agentes."""
        status = self.obter_status_geral()
        criticas = []
        
        for agente, dados in status["agentes"].items():
            for pend in dados["pendencias"]:
                if pend.get("prioridade") == "alta" and pend.get("status") == "pendente":
                    criticas.append({
                        "agente": agente,
                        "pendencia": pend
                    })
        
        return criticas
    
    def criar_pendencia_para_agente(self, agente: str, descricao: str, prioridade: str = "media"):
        """Cria uma pendência para um agente específico."""
        nome_pasta = agente.lower().replace(" ", "_").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
        pasta_agente = Path(self.projeto_root) / "artefatos" / nome_pasta
        pasta_agente.mkdir(parents=True, exist_ok=True)
        
        arquivo_pendencias = pasta_agente / "pendencias.json"
        pendencias = []
        
        if arquivo_pendencias.exists():
            with open(arquivo_pendencias, 'r', encoding='utf-8') as f:
                pendencias = json.load(f)
        
        pendencia = {
            "id": len(pendencias) + 1,
            "descricao": descricao,
            "prioridade": prioridade,
            "status": "pendente",
            "criado_em": datetime.now().isoformat(),
            "criado_por": self.nome
        }
        pendencias.append(pendencia)
        
        with open(arquivo_pendencias, 'w', encoding='utf-8') as f:
            json.dump(pendencias, f, ensure_ascii=False, indent=2)
        
        self.registrar_interacao(
            tipo="criacao_pendencia",
            conteudo=f"Pendência criada para {agente}: {descricao}",
            participantes=[self.nome, agente]
        )
        
        return pendencia
