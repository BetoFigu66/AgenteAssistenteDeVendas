"""
Agente Gerente de Projetos
Responsavel por gestao agil do projeto, relatorios de Sprint e coordenacao dos agentes.

A fonte da verdade da identidade e do prompt deste agente esta em:
    agentes/gerente_de_projetos.md

E o harness de diretrizes operacionais em:
    artefatos/gerente_de_projetos/diretrizes.md

Exemplo de uso:
    Atue como [gerente] e gere um relatorio da Sprint 2.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from .base_agente import BaseAgente, nome_pasta


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

    PROMPT_MD = "agentes/gerente_de_projetos.md"
    DIRETRIZES_MD = "artefatos/gerente_de_projetos/diretrizes.md"

    def __init__(self, projeto_root: str = None):
        super().__init__(
            nome="Gerente de Projetos",
            papel="Gerenciar o projeto de forma ágil, gerar relatórios de Sprint e coordenar agentes",
            projeto_root=projeto_root,
        )
        self.agentes_gerenciados = [
            "Analista de Requisitos",
            "Auxiliar de Negocios",
            "Arquiteto de Sistemas",
            "Planejador de Negocios",
            "QA Engineer",
            "Implementador",
        ]

        # Configurações de Sprint (padrão: 2 semanas) — ver diretriz G02
        self.duracao_sprint_dias = 14

    def get_prompt_sistema(self) -> str:
        """
        Le o prompt de sistema concatenando:
          1. agentes/gerente_de_projetos.md (identidade — fonte da verdade)
          2. artefatos/gerente_de_projetos/diretrizes.md (diretrizes operacionais G01-G0N)
        """
        prompt_path = Path(self.projeto_root) / self.PROMPT_MD
        if prompt_path.exists():
            identidade = prompt_path.read_text(encoding="utf-8")
        else:
            # Fallback minimo caso o .md seja apagado
            identidade = (
                "Voce e o Gerente de Projetos do projeto Assistente de Vendas. "
                "Conduza o desenvolvimento de forma agil, gere relatorios de Sprint "
                "a cada 2 semanas e coordene os demais agentes. "
                "(Prompt completo em agentes/gerente_de_projetos.md nao encontrado.)"
            )

        diretrizes_path = Path(self.projeto_root) / self.DIRETRIZES_MD
        diretrizes = diretrizes_path.read_text(encoding="utf-8") if diretrizes_path.exists() else "(nenhuma diretriz registrada ainda)"
        return f"{identidade}\n\n---\n\n{diretrizes}"

    def get_contexto(self) -> dict:
        return {
            "agente": self.nome,
            "papel": self.papel,
            "agentes_gerenciados": self.agentes_gerenciados,
            "artefatos": self.listar_artefatos(),
            "pendencias": self.obter_pendencias(),
        }

    def obter_status_geral(self) -> dict:
        """Obtém status de todos os agentes e suas pendências."""
        projeto_root = Path(self.projeto_root)
        artefatos_root = projeto_root / "artefatos"

        status = {"data": datetime.now().isoformat(), "agentes": {}}

        for agente in self.agentes_gerenciados:
            pasta_agente = artefatos_root / nome_pasta(agente)

            artefatos = []
            pendencias = []

            if pasta_agente.exists():
                artefatos = [f.name for f in pasta_agente.iterdir() if f.is_file() and f.name != "pendencias.json"]

                arquivo_pendencias = pasta_agente / "pendencias.json"
                if arquivo_pendencias.exists():
                    with open(arquivo_pendencias, "r", encoding="utf-8") as f:
                        pendencias = json.load(f)

            status["agentes"][agente] = {
                "artefatos": artefatos,
                "total_artefatos": len(artefatos),
                "pendencias": pendencias,
                "pendencias_abertas": len([p for p in pendencias if p.get("status") == "pendente"]),
            }

        return status

    # ------------------------------------------------------------------
    # Sprint Review — fluxo YAML (fonte da verdade) + PPTX (apresentacao)
    # ------------------------------------------------------------------
    def gerar_dados_sprint_yaml(
        self,
        sprint_numero: int,
        data_inicio: datetime,
        data_fim: datetime,
        feito: List[Dict],
        proximo_sprint: List[Dict],
        backlog_pendente: List[Dict],
        bloqueios: Optional[List[str]] = None,
        metricas: Optional[Dict] = None,
        insights: Optional[List[str]] = None,
    ) -> Path:
        """
        Gera o arquivo YAML com os dados do Sprint.

        O YAML e a FONTE UNICA da verdade do Sprint Review e eh o unico
        artefato versionado. A apresentacao .pptx eh derivada dele via
        `gera_sprint_report.py` e NAO deve ser editada diretamente
        (exceto para formatacao visual).

        Args:
            sprint_numero: Numero do Sprint (1, 2, 3...).
            data_inicio: Data de inicio do Sprint.
            data_fim: Data de termino do Sprint.
            feito: Itens entregues. Cada item:
                `{"titulo": str, "descricao": str, "agente": str}`.
            proximo_sprint: Itens planejados. Cada item:
                `{"titulo": str, "prioridade": "alta"|"media"|"baixa"}`.
            backlog_pendente: Itens do escopo total ainda nao iniciados.
                Cada item: `{"titulo": str}`.
            bloqueios: Lista de impedimentos (strings).
            metricas: Dict com contagens. Se None, eh calculado automaticamente.
            insights: Observacoes livres para a secao de insights.

        Returns:
            Path do arquivo YAML gerado.
        """
        import yaml

        if metricas is None:
            metricas = self._calcular_metricas_sprint(data_inicio, data_fim)
        if bloqueios is None:
            bloqueios = []
        if insights is None:
            insights = []

        proximo_inicio = data_fim + timedelta(days=1)
        proximo_fim = data_fim + timedelta(days=self.duracao_sprint_dias)

        dados = {
            "sprint_numero": sprint_numero,
            "data_inicio": data_inicio.strftime("%Y-%m-%d"),
            "data_fim": data_fim.strftime("%Y-%m-%d"),
            "duracao_dias": self.duracao_sprint_dias,
            "proximo_sprint_inicio": proximo_inicio.strftime("%Y-%m-%d"),
            "proximo_sprint_fim": proximo_fim.strftime("%Y-%m-%d"),
            "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "feito": feito or [],
            "proximo_sprint": proximo_sprint or [],
            "backlog_pendente": backlog_pendente or [],
            "bloqueios": bloqueios,
            "metricas": metricas,
            "insights": insights,
        }

        nome_arquivo = f"sprint_{sprint_numero:02d}_{data_fim.strftime('%Y%m%d')}.yaml"
        caminho = self.artefatos_dir / nome_arquivo
        with open(caminho, "w", encoding="utf-8") as f:
            yaml.safe_dump(dados, f, allow_unicode=True, sort_keys=False, width=120)

        self.registrar_interacao(
            tipo="geracao_dados_sprint",
            conteudo=f"Dados do Sprint {sprint_numero} gerados: {nome_arquivo}",
            participantes=[self.nome],
        )
        return caminho

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
            "reports_total": 0,  # Via query ao banco futuramente
            "reports_resolvidos": 0,
        }

    def gerar_relatorio_status(self) -> str:
        """Gera relatório de status do projeto (visualização rápida, não Sprint)."""
        status = self.obter_status_geral()

        conteudo = f"""# 📋 Relatório de Status do Projeto

**Data**: {datetime.now().strftime("%Y-%m-%d %H:%M")}  
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
- **Artefatos**: {dados["total_artefatos"]} | **Pendências abertas**: {dados["pendencias_abertas"]}

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
*Para o Sprint Review, use `gerar_dados_sprint_yaml()` e gere a apresentação com `gera_sprint_report.py`.*
"""

        return str(self.criar_artefato(f"relatorio_status_{datetime.now().strftime('%Y%m%d_%H%M')}.md", conteudo, tipo="relatorio_status"))

    def listar_historico(self, dias: int = 7) -> list:
        """Lista histórico de interações dos últimos N dias."""
        historico_completo = []

        for arquivo in self.historico_dir.glob("ata_*.json"):
            with open(arquivo, "r", encoding="utf-8") as f:
                registros = json.load(f)
                historico_completo.extend(registros)

        # Ordena por data
        historico_completo.sort(key=lambda x: x.get("data", ""), reverse=True)

        return historico_completo

    def gerar_ata_reuniao(self, participantes: list, pauta: list, decisoes: list, proximos_passos: list):
        """Gera ata de reunião formal."""
        conteudo = f"""# Ata de Reunião

**Data**: {datetime.now().strftime("%Y-%m-%d %H:%M")}

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
            conteudo += f"- [ ] **{passo.get('responsavel', 'A definir')}**: {passo.get('acao', 'N/A')} \
                (Prazo: {passo.get('prazo', 'A definir')})\n"

        nome_arquivo = f"ata_reuniao_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
        return self.criar_artefato(nome_arquivo, conteudo, tipo="ata")

    def alertar_pendencias_criticas(self) -> list:
        """Identifica e retorna pendências críticas de todos os agentes."""
        status = self.obter_status_geral()
        criticas = []

        for agente, dados in status["agentes"].items():
            for pend in dados["pendencias"]:
                if pend.get("prioridade") == "alta" and pend.get("status") == "pendente":
                    criticas.append({"agente": agente, "pendencia": pend})

        return criticas

    def criar_pendencia_para_agente(self, agente: str, descricao: str, prioridade: str = "media"):
        """Cria uma pendência para um agente específico."""
        pasta_agente = Path(self.projeto_root) / "artefatos" / nome_pasta(agente)
        pasta_agente.mkdir(parents=True, exist_ok=True)

        arquivo_pendencias = pasta_agente / "pendencias.json"
        pendencias = []

        if arquivo_pendencias.exists():
            with open(arquivo_pendencias, "r", encoding="utf-8") as f:
                pendencias = json.load(f)

        pendencia = {
            "id": len(pendencias) + 1,
            "descricao": descricao,
            "prioridade": prioridade,
            "status": "pendente",
            "criado_em": datetime.now().isoformat(),
            "criado_por": self.nome,
        }
        pendencias.append(pendencia)

        with open(arquivo_pendencias, "w", encoding="utf-8") as f:
            json.dump(pendencias, f, ensure_ascii=False, indent=2)

        self.registrar_interacao(tipo="criacao_pendencia", conteudo=f"Pendência criada para {agente}: {descricao}", participantes=[self.nome, agente])

        return pendencia
