"""
Orquestrador de Agentes
Interface principal para interação com todos os agentes do sistema.

Nota: [auxiliar], [arquiteto] e [planejador] foram convertidos para .md (IA01)
e não possuem mais classes Python. O orquestrador gerencia apenas os agentes
com lógica executável real.
"""

from pathlib import Path

from .analista_requisitos import AnalistaRequisitos
from .gerente_de_projetos import GerenteDeProjetos


class OrquestradorAgentes:
    """
    Orquestrador central que gerencia agentes com lógica Python executável.
    Facilita a interação e coordenação entre agentes.
    """

    def __init__(self, projeto_root: str = None):
        self.projeto_root = projeto_root or str(Path(__file__).parent.parent)

        # Agentes com lógica Python executável
        self.analista = AnalistaRequisitos(self.projeto_root)
        self.gerente_de_projetos = GerenteDeProjetos(self.projeto_root)

        self.agentes = {
            "analista": self.analista,
            "gerente_de_projetos": self.gerente_de_projetos,
        }

    def obter_agente(self, nome: str):
        """Retorna um agente pelo nome."""
        return self.agentes.get(nome.lower())

    def listar_agentes(self) -> list:
        """Lista todos os agentes disponíveis."""
        return [{"id": key, "nome": agente.nome, "papel": agente.papel} for key, agente in self.agentes.items()]

    def obter_contexto_completo(self) -> dict:
        """Obtém contexto de todos os agentes."""
        return {key: agente.get_contexto() for key, agente in self.agentes.items()}

    def obter_todos_prompts(self) -> dict:
        """Obtém prompts de sistema de todos os agentes."""
        return {key: agente.get_prompt_sistema() for key, agente in self.agentes.items()}

    def inicializar_projeto(self):
        """
        Inicializa o projeto criando estrutura base e artefatos iniciais.
        """
        # Cria pendências iniciais para agentes com lógica Python executável
        # [auxiliar], [arquiteto] e [planejador] são .md-only (IA01) — sem pendências programáticas
        pendencias_iniciais = [
            ("analista", "Realizar brainstorm inicial sobre funcionalidades do MVP", "alta"),
            ("analista", "Documentar requisitos funcionais principais", "alta"),
            ("analista", "Criar histórias de usuário para o MVP", "media"),
            ("gerente_de_projetos", "Gerar primeiro relatório de status", "baixa"),
        ]

        for agente_id, descricao, prioridade in pendencias_iniciais:
            agente = self.agentes[agente_id]
            agente.adicionar_pendencia(descricao, prioridade)

        # Registra inicialização
        self.gerente_de_projetos.registrar_interacao(
            tipo="inicializacao_projeto",
            conteudo="Projeto inicializado com pendências para todos os agentes",
            participantes=["Sistema", "Gerente de Projetos"],
        )

        return self.gerente_de_projetos.obter_status_geral()

    def gerar_relatorio_completo(self) -> str:
        """Gera relatório completo do projeto."""
        return self.gerente_de_projetos.gerar_relatorio_status()


def main():
    """Função principal para demonstração."""
    print("=" * 60)
    print("Sistema de Agentes - Assistente de Vendas via WhatsApp com IA")
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
