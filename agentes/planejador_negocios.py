"""
Agente Planejador de Negócios (Estrategista de Negócios)
Responsável por transformar o produto em empreendimento rentável.
"""
from .base_agente import BaseAgente


class PlanejadorNegocios(BaseAgente):
    """
    Planejador de Negócios - Foca em rentabilidade e estratégia comercial.
    
    Responsabilidades:
    - Estratégias de precificação
    - Planos de divulgação e marketing
    - Análise de mercado e concorrência
    - Modelos de monetização
    - Projeções financeiras
    """
    
    def __init__(self, projeto_root: str = None):
        super().__init__(
            nome="Planejador de Negocios",
            papel="Transformar o produto em empreendimento rentável",
            projeto_root=projeto_root
        )
        self.modelos_monetizacao = [
            "SaaS (assinatura mensal)",
            "Pay-per-use (por mensagem/conversa)",
            "Freemium (básico grátis + premium)",
            "Setup + mensalidade",
            "Revenue share (% das vendas)"
        ]
    
    def get_prompt_sistema(self) -> str:
        return """Você é um Planejador de Negócios experiente em startups de tecnologia e produtos SaaS.

Seu papel é:
1. Desenvolver estratégias de monetização
2. Criar planos de precificação competitivos
3. Propor estratégias de marketing e divulgação
4. Analisar mercado e concorrência
5. Fazer projeções financeiras realistas

Contexto do Projeto:
- Produto: Assistente de vendas via WhatsApp com IA
- Mercado: PMEs que usam WhatsApp para vendas
- Diferenciais: 
    - IA que sabe quando escalar para humano
    - Interface para acompanhamento de atendimentos que permite:
        - Dar feedback em relação às conversas com os clientes.
        - Fornecer maid informações para alimentar dinamicamente a base de conhecimento
    - Acesso rápido a situação do cliente, incluindo tipo de contrato de manutenção.
- Primeiro cliente: Empresa de catracas Inforrel. Contato: Rita Conti

Modelos de monetização a considerar:
1. SaaS (assinatura mensal fixa)
2. Pay-per-use (por mensagem ou conversa)
3. Freemium (básico grátis, recursos premium pagos)
4. Setup + mensalidade
5. Revenue share (% das vendas geradas)

Ao interagir:
- Baseie-se em dados de mercado quando possível
- Considere o contexto brasileiro
- Pense em escalabilidade do modelo
- Sugira métricas de acompanhamento
- Seja realista com projeções"""

    def get_contexto(self) -> dict:
        return {
            "agente": self.nome,
            "papel": self.papel,
            "modelos_monetizacao": self.modelos_monetizacao,
            "artefatos": self.listar_artefatos(),
            "pendencias": self.obter_pendencias()
        }
    
    def criar_modelo_precificacao(self, modelo: str, faixas: list, justificativa: str):
        """Cria documento de modelo de precificação."""
        conteudo = f"""# Modelo de Precificação

## Modelo Escolhido
**{modelo}**

## Justificativa
{justificativa}

## Faixas de Preço

| Plano | Preço | Inclui |
|-------|-------|--------|
"""
        for faixa in faixas:
            conteudo += f"| {faixa.get('nome', '-')} | {faixa.get('preco', '-')} | {faixa.get('inclui', '-')} |\n"
        
        conteudo += """
## Comparativo de Mercado
A ser preenchido com análise de concorrentes.

## Projeção de Receita
A ser calculada com base em estimativas de clientes.

## Custos Variáveis por Cliente
- OpenAI API: ~R$ X por 1000 mensagens
- WhatsApp API: ~R$ X por mensagem
- Infraestrutura: ~R$ X por cliente

## Margem Estimada
A calcular após definição de custos.
"""
        return self.criar_artefato("modelo_precificacao.md", conteudo, tipo="financeiro")

    def criar_plano_marketing(self, canais: list, acoes: list, orcamento: str = "A definir"):
        """Cria plano de marketing e divulgação."""
        conteudo = f"""# Plano de Marketing e Divulgação

## Orçamento Disponível
{orcamento}

## Canais de Divulgação
"""
        for canal in canais:
            conteudo += f"- **{canal.get('nome')}**: {canal.get('estrategia', 'A definir')}\n"
        
        conteudo += "\n## Ações Planejadas\n"
        for acao in acoes:
            conteudo += f"""
### {acao.get('nome', 'Ação')}
- **Prazo**: {acao.get('prazo', 'A definir')}
- **Responsável**: {acao.get('responsavel', 'A definir')}
- **Custo estimado**: {acao.get('custo', 'A definir')}
- **Métrica de sucesso**: {acao.get('metrica', 'A definir')}
"""
        
        conteudo += """
## Métricas de Acompanhamento
- Leads gerados
- Taxa de conversão
- CAC (Custo de Aquisição de Cliente)
- LTV (Lifetime Value)
- Churn rate

## Cronograma
A ser definido após aprovação do plano.
"""
        return self.criar_artefato("plano_marketing.md", conteudo, tipo="marketing")

    def analisar_concorrencia(self, concorrentes: list):
        """Cria análise de concorrência."""
        conteudo = """# Análise de Concorrência

## Visão Geral do Mercado
Assistentes de vendas via WhatsApp com IA.

## Concorrentes Identificados
"""
        for conc in concorrentes:
            conteudo += f"""
### {conc.get('nome', 'Concorrente')}
- **Site**: {conc.get('site', 'N/A')}
- **Preço**: {conc.get('preco', 'A pesquisar')}
- **Pontos fortes**: {conc.get('pontos_fortes', 'A analisar')}
- **Pontos fracos**: {conc.get('pontos_fracos', 'A analisar')}
"""
        
        conteudo += """
## Nossos Diferenciais
- [ ] A definir com base na análise

## Oportunidades
- [ ] A identificar

## Ameaças
- [ ] A identificar

## Estratégia Competitiva
A ser definida após análise completa.
"""
        return self.criar_artefato("analise_concorrencia.md", conteudo, tipo="mercado")

    def criar_projecao_financeira(self, cenarios: list):
        """Cria projeção financeira com cenários."""
        conteudo = """# Projeção Financeira

## Premissas
- Preço médio por cliente: A definir
- Custo variável por cliente: A definir
- Custos fixos mensais: A definir

## Cenários
"""
        for cenario in cenarios:
            conteudo += f"""
### {cenario.get('nome', 'Cenário')}
- **Clientes em 6 meses**: {cenario.get('clientes_6m', 'A definir')}
- **Clientes em 12 meses**: {cenario.get('clientes_12m', 'A definir')}
- **Receita mensal projetada**: {cenario.get('receita', 'A calcular')}
- **Ponto de equilíbrio**: {cenario.get('break_even', 'A calcular')}
"""
        
        conteudo += """
## Investimento Inicial Necessário
- Desenvolvimento: X horas × R$ Y = R$ Z
- Infraestrutura (3 meses): R$ X
- Marketing inicial: R$ X
- **Total**: R$ X

## ROI Esperado
A calcular após definição de receitas e custos.
"""
        return self.criar_artefato("projecao_financeira.md", conteudo, tipo="financeiro")
