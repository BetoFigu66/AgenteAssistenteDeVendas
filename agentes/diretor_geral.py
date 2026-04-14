"""
Agente Diretor Geral
Responsável por orquestrar os outros agentes e acompanhar pendências.
"""
from .base_agente import BaseAgente
from pathlib import Path
import json
from datetime import datetime


class DiretorGeral(BaseAgente):
    """
    Diretor Geral - Orquestra agentes e acompanha pendências.
    
    Responsabilidades:
    - Coordenar trabalho entre agentes
    - Acompanhar pendências de todos os agentes
    - Alertar sobre bloqueios e dependências
    - Manter visão geral do projeto
    - Gerar relatórios de status
    """
    
    def __init__(self, projeto_root: str = None):
        super().__init__(
            nome="Diretor Geral",
            papel="Orquestrar agentes e acompanhar pendências do projeto",
            projeto_root=projeto_root
        )
        self.agentes_gerenciados = [
            "Analista de Requisitos",
            "Auxiliar de Negocios", 
            "Arquiteto de Sistemas",
            "Planejador de Negocios"
        ]
    
    def get_prompt_sistema(self) -> str:
        return """Você é o Diretor Geral do projeto, responsável por coordenar todos os agentes e garantir o progresso.

Seu papel é:
1. Manter visão geral do projeto
2. Coordenar trabalho entre agentes
3. Identificar bloqueios e dependências
4. Alertar sobre pendências críticas
5. Gerar relatórios de status

Agentes sob sua coordenação:
1. **Analista de Requisitos**: Brainstorms e documentação de requisitos
2. **Auxiliar de Negócios**: Transformar ideia em produto
3. **Arquiteto de Sistemas**: Propor arquiteturas (POC, single, multi-tenant)
4. **Planejador de Negócios**: Monetização e estratégia comercial

Ao interagir:
- Mantenha foco no progresso do projeto
- Identifique dependências entre agentes
- Priorize pendências críticas
- Sugira próximos passos
- Facilite comunicação entre agentes

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
    
    def gerar_relatorio_status(self) -> str:
        """Gera relatório de status do projeto."""
        status = self.obter_status_geral()
        
        conteudo = f"""# Relatório de Status do Projeto

**Data**: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Visão Geral

"""
        total_artefatos = 0
        total_pendencias = 0
        
        for agente, dados in status["agentes"].items():
            total_artefatos += dados["total_artefatos"]
            total_pendencias += dados["pendencias_abertas"]
            
            emoji = "🟢" if dados["pendencias_abertas"] == 0 and dados["total_artefatos"] > 0 else "🟡" if dados["total_artefatos"] > 0 else "⚪"
            
            conteudo += f"""### {emoji} {agente}
- **Artefatos criados**: {dados['total_artefatos']}
- **Pendências abertas**: {dados['pendencias_abertas']}

"""
            if dados["artefatos"]:
                conteudo += "**Artefatos**:\n"
                for art in dados["artefatos"]:
                    conteudo += f"- {art}\n"
                conteudo += "\n"
            
            if dados["pendencias"]:
                conteudo += "**Pendências**:\n"
                for pend in dados["pendencias"]:
                    status_emoji = "✅" if pend.get("status") == "concluido" else "⏳"
                    conteudo += f"- {status_emoji} {pend.get('descricao', 'N/A')}\n"
                conteudo += "\n"
        
        conteudo += f"""## Resumo
- **Total de artefatos**: {total_artefatos}
- **Total de pendências abertas**: {total_pendencias}

## Próximos Passos Sugeridos
1. Revisar pendências abertas
2. Verificar dependências entre agentes
3. Priorizar itens críticos
"""
        
        return self.criar_artefato(
            f"relatorio_status_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
            conteudo,
            tipo="relatorio"
        )
    
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
