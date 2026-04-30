"""
Agente Auxiliar de Desenvolvimento de Negócios
Responsável por transformar a ideia em produto para o mercado.
"""
from .base_agente import BaseAgente


class AuxiliarNegocios(BaseAgente):
    """
    Auxiliar de Desenvolvimento de Negócios - Transforma ideias em produtos.
    
    Responsabilidades:
    - Analisar viabilidade do produto
    - Definir MVP e roadmap
    - Identificar diferenciais competitivos
    - Planejar fases de lançamento
    - Estratégia de atendimento ao primeiro cliente (Rita/Ivan)
    """
    
    def __init__(self, projeto_root: str = None):
        super().__init__(
            nome="Auxiliar de Negocios",
            papel="Transformar a ideia em produto viável para o mercado",
            projeto_root=projeto_root
        )
        self.cliente_inicial = {
            "nome": "Rita/Ivan",
            "negocio": "Venda de catracas para controle de acesso",
            "canal_principal": "WhatsApp Business",
            "necessidade": "Automatizar atendimento e qualificar leads"
        }
    
    def get_prompt_sistema(self) -> str:
        return """Você é um Auxiliar de Desenvolvimento de Negócios experiente em produtos de tecnologia e SaaS.

Seu papel é:
1. Ajudar a transformar ideias em produtos viáveis
2. Definir MVPs realistas e incrementais
3. Criar roadmaps de desenvolvimento
4. Identificar oportunidades de mercado
5. Planejar estratégias de go-to-market

Contexto do Projeto:
- Produto: Assistente de vendas via WhatsApp com IA
- Primeiro cliente: Rita/Ivan (empresa de catracas)
- Objetivo inicial: Atender demanda específica deste cliente
- Objetivo futuro: Escalar para mais clientes

Estratégia recomendada:
1. Fase 1: POC para validação com cliente inicial
2. Fase 2: Produto customizado para Rita/Ivan
3. Fase 3: Produto escalável multi-tenant

Ao interagir:
- Foque em entregas incrementais de valor
- Considere custos vs benefícios
- Pense em métricas de sucesso
- Identifique riscos de negócio
- Sugira pivots quando necessário"""

    def get_contexto(self) -> dict:
        return {
            "agente": self.nome,
            "papel": self.papel,
            "cliente_inicial": self.cliente_inicial,
            "artefatos": self.listar_artefatos(),
            "pendencias": self.obter_pendencias()
        }
    
    def definir_mvp(self, funcionalidades: list, prazo_estimado: str = None):
        """Define o escopo do MVP."""
        conteudo = """# Definição do MVP - Assistente de Vendas via WhatsApp com IA

## Objetivo
Criar uma versão mínima funcional que demonstre valor para o cliente inicial.

## Funcionalidades do MVP
"""
        for i, func in enumerate(funcionalidades, 1):
            conteudo += f"{i}. {func}\n"
        
        if prazo_estimado:
            conteudo += f"\n## Prazo Estimado\n{prazo_estimado}\n"
        
        conteudo += """
## Critérios de Sucesso
- [ ] Cliente consegue receber mensagens automatizadas
- [ ] IA responde perguntas básicas sobre produtos
- [ ] Vendedor é alertado quando necessário
- [ ] Sistema funciona de forma estável

## Fora do Escopo (para versões futuras)
- Multi-tenant
- Analytics avançados
- Integração com CRM
- Suporte a áudio
"""
        return self.criar_artefato("MVP_definicao.md", conteudo, tipo="planejamento")

    def criar_roadmap(self, fases: list):
        """Cria roadmap de desenvolvimento."""
        conteudo = """# Roadmap de Desenvolvimento

## Visão Geral
Evolução do produto desde POC até versão escalável.

"""
        for fase in fases:
            conteudo += f"""### {fase.get('nome', 'Fase')}
**Duração estimada**: {fase.get('duracao', 'A definir')}
**Objetivo**: {fase.get('objetivo', 'A definir')}

**Entregas**:
"""
            for entrega in fase.get('entregas', []):
                conteudo += f"- {entrega}\n"
            conteudo += "\n"
        
        return self.criar_artefato("roadmap.md", conteudo, tipo="planejamento")

    def analisar_cliente(self, nome: str, necessidades: list, restricoes: list = None):
        """Documenta análise de um cliente potencial."""
        conteudo = f"""# Análise de Cliente: {nome}

## Necessidades Identificadas
"""
        for need in necessidades:
            conteudo += f"- {need}\n"
        
        if restricoes:
            conteudo += "\n## Restrições\n"
            for rest in restricoes:
                conteudo += f"- {rest}\n"
        
        conteudo += """
## Proposta de Valor
A definir com base nas necessidades.

## Próximos Passos
- [ ] Validar entendimento com cliente
- [ ] Apresentar proposta inicial
- [ ] Definir escopo de POC
"""
        nome_arquivo = f"cliente_{nome.replace(' ', '_').replace('/', '_')}.md"
        return self.criar_artefato(nome_arquivo, conteudo, tipo="analise_cliente")
