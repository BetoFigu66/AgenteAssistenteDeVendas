"""
Agente Analista de Requisitos
Responsável por fazer brainstorms e elaborar requisitos do sistema.
"""
from .base_agente import BaseAgente


class AnalistaRequisitos(BaseAgente):
    """
    Analista de Requisitos - Faz brainstorms para elaborar as ideias do produto.
    
    Responsabilidades:
    - Conduzir sessões de brainstorm
    - Documentar requisitos funcionais e não-funcionais
    - Criar histórias de usuário
    - Mapear jornadas do cliente
    - Identificar casos de uso
    """
    
    def __init__(self, projeto_root: str = None):
        super().__init__(
            nome="Analista de Requisitos",
            papel="Elaborar e documentar requisitos do sistema através de brainstorms",
            projeto_root=projeto_root
        )
        self.contexto_projeto = self._carregar_contexto_projeto()
    
    def _carregar_contexto_projeto(self) -> dict:
        """Carrega o contexto inicial do projeto."""
        return {
            "produto": "Assistente de Vendas via WhatsApp com IA",
            "cliente_inicial": "Empresa de catracas para controle de acesso",
            "problema": "Automatizar atendimento via WhatsApp Business",
            "objetivos": [
                "Responder automaticamente quando possível",
                "Escalar para humano quando necessário",
                "Qualificar leads",
                "Tirar dúvidas técnicas"
            ]
        }
    
    def get_prompt_sistema(self) -> str:
        return """Você é um Analista de Requisitos experiente, especializado em sistemas de IA conversacional e automação de vendas.

Seu papel é:
1. Conduzir brainstorms estruturados para entender as necessidades do produto
2. Fazer perguntas relevantes para descobrir requisitos ocultos
3. Documentar requisitos de forma clara e organizada
4. Identificar riscos e dependências
5. Criar histórias de usuário no formato: "Como [persona], quero [ação] para [benefício]"

Contexto do Projeto:
- Produto: Assistente de vendas via WhatsApp com IA
- Cliente inicial: Empresa que vende catracas para controle de acesso
- Foco: Pré-venda, qualificação de leads, tirar dúvidas técnicas

Ao interagir:
- Faça perguntas abertas para explorar ideias
- Sugira funcionalidades baseadas em boas práticas
- Identifique requisitos funcionais e não-funcionais
- Considere a experiência do usuário final (cliente da empresa de catracas)
- Pense em cenários de erro e exceção

Sempre documente suas descobertas de forma estruturada."""

    def get_contexto(self) -> dict:
        return {
            "agente": self.nome,
            "papel": self.papel,
            "projeto": self.contexto_projeto,
            "artefatos": self.listar_artefatos(),
            "pendencias": self.obter_pendencias()
        }
    
    def iniciar_brainstorm(self, tema: str) -> str:
        """Inicia uma sessão de brainstorm sobre um tema específico."""
        self.registrar_interacao(
            tipo="brainstorm_inicio",
            conteudo=f"Iniciando brainstorm sobre: {tema}"
        )
        
        return f"""
# 🧠 Sessão de Brainstorm: {tema}

Vamos explorar este tema juntos. Algumas perguntas iniciais:

1. **Contexto**: Qual é o cenário atual? Como funciona hoje sem o sistema?
2. **Dores**: Quais são os principais problemas que queremos resolver?
3. **Usuários**: Quem são os usuários finais? Quais suas necessidades?
4. **Sucesso**: Como saberemos que o sistema está funcionando bem?
5. **Restrições**: Existem limitações técnicas, de tempo ou orçamento?

Vamos começar por qual aspecto?
"""

    def documentar_requisito(self, titulo: str, descricao: str, tipo: str = "funcional", prioridade: str = "media"):
        """Documenta um requisito identificado."""
        requisito = f"""# Requisito: {titulo}

**Tipo**: {tipo}
**Prioridade**: {prioridade}

## Descrição
{descricao}

## Critérios de Aceitação
- [ ] A definir durante refinamento

## Notas
- Documentado em: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
        nome_arquivo = f"REQ_{titulo.replace(' ', '_')[:30]}.md"
        return self.criar_artefato(nome_arquivo, requisito, tipo="requisito")

    def criar_historia_usuario(self, persona: str, acao: str, beneficio: str, criterios: list = None):
        """Cria uma história de usuário."""
        historia = f"""# História de Usuário

**Como** {persona}
**Quero** {acao}
**Para** {beneficio}

## Critérios de Aceitação
"""
        for i, criterio in enumerate(criterios or [], 1):
            historia += f"{i}. {criterio}\n"
        
        if not criterios:
            historia += "- [ ] A definir\n"
        
        nome_arquivo = f"US_{persona.replace(' ', '_')[:20]}_{acao.replace(' ', '_')[:20]}.md"
        return self.criar_artefato(nome_arquivo, historia, tipo="historia_usuario")
