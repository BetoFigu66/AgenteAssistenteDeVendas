"""
Orquestrador de Agentes
Interface principal para interação com todos os agentes do sistema.
"""
from pathlib import Path
from datetime import datetime
import json

from .analista_requisitos import AnalistaRequisitos
from .auxiliar_negocios import AuxiliarNegocios
from .arquiteto_sistemas import ArquitetoSistemas
from .planejador_negocios import PlanejadorNegocios
from .diretor_geral import DiretorGeral


class OrquestradorAgentes:
    """
    Orquestrador central que gerencia todos os agentes.
    Facilita a interação e coordenação entre agentes.
    """
    
    def __init__(self, projeto_root: str = None):
        self.projeto_root = projeto_root or str(Path(__file__).parent.parent)
        
        # Inicializa todos os agentes
        self.analista = AnalistaRequisitos(self.projeto_root)
        self.auxiliar_negocios = AuxiliarNegocios(self.projeto_root)
        self.arquiteto = ArquitetoSistemas(self.projeto_root)
        self.planejador = PlanejadorNegocios(self.projeto_root)
        self.diretor = DiretorGeral(self.projeto_root)
        
        self.agentes = {
            "analista": self.analista,
            "auxiliar": self.auxiliar_negocios,
            "arquiteto": self.arquiteto,
            "planejador": self.planejador,
            "diretor": self.diretor
        }
    
    def obter_agente(self, nome: str):
        """Retorna um agente pelo nome."""
        return self.agentes.get(nome.lower())
    
    def listar_agentes(self) -> list:
        """Lista todos os agentes disponíveis."""
        return [
            {
                "id": key,
                "nome": agente.nome,
                "papel": agente.papel
            }
            for key, agente in self.agentes.items()
        ]
    
    def obter_contexto_completo(self) -> dict:
        """Obtém contexto de todos os agentes."""
        return {
            key: agente.get_contexto()
            for key, agente in self.agentes.items()
        }
    
    def obter_todos_prompts(self) -> dict:
        """Obtém prompts de sistema de todos os agentes."""
        return {
            key: agente.get_prompt_sistema()
            for key, agente in self.agentes.items()
        }
    
    def inicializar_projeto(self):
        """
        Inicializa o projeto criando estrutura base e artefatos iniciais.
        """
        # Cria pendências iniciais para cada agente
        pendencias_iniciais = [
            ("analista", "Realizar brainstorm inicial sobre funcionalidades do MVP", "alta"),
            ("analista", "Documentar requisitos funcionais principais", "alta"),
            ("analista", "Criar histórias de usuário para o MVP", "media"),
            ("auxiliar", "Definir escopo do MVP", "alta"),
            ("auxiliar", "Criar roadmap de desenvolvimento", "media"),
            ("auxiliar", "Documentar análise do cliente inicial (Rita/Ivan)", "alta"),
            ("arquiteto", "Propor arquitetura para POC", "alta"),
            ("arquiteto", "Documentar decisões técnicas iniciais", "media"),
            ("planejador", "Pesquisar concorrentes no mercado", "media"),
            ("planejador", "Propor modelo de precificação inicial", "media"),
            ("diretor", "Gerar primeiro relatório de status", "baixa"),
        ]
        
        for agente_id, descricao, prioridade in pendencias_iniciais:
            agente = self.agentes[agente_id]
            agente.adicionar_pendencia(descricao, prioridade)
        
        # Registra inicialização
        self.diretor.registrar_interacao(
            tipo="inicializacao_projeto",
            conteudo="Projeto inicializado com pendências para todos os agentes",
            participantes=["Sistema", "Diretor Geral"]
        )
        
        return self.diretor.obter_status_geral()
    
    def gerar_relatorio_completo(self) -> str:
        """Gera relatório completo do projeto."""
        return self.diretor.gerar_relatorio_status()


def main():
    """Função principal para demonstração."""
    print("=" * 60)
    print("Sistema de Agentes - Assistente de Vendas WhatsApp")
    print("=" * 60)
    
    orquestrador = OrquestradorAgentes()
    
    print("\n📋 Agentes Disponíveis:")
    for agente in orquestrador.listar_agentes():
        print(f"  - {agente['nome']}: {agente['papel']}")
    
    print("\n🚀 Inicializando projeto...")
    status = orquestrador.inicializar_projeto()
    
    print("\n📊 Status Inicial:")
    for agente, dados in status["agentes"].items():
        print(f"  {agente}:")
        print(f"    - Pendências: {dados['pendencias_abertas']}")
    
    print("\n✅ Sistema de agentes pronto para uso!")
    print("\nPróximos passos sugeridos:")
    print("  1. Iniciar brainstorm com Analista de Requisitos")
    print("  2. Definir MVP com Auxiliar de Negócios")
    print("  3. Propor arquitetura POC com Arquiteto de Sistemas")


if __name__ == "__main__":
    main()
