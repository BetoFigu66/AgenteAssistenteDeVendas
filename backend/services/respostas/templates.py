"""
Templates de respostas padrão para cada intenção/estado.

Regras de negócio aplicadas:
- NUNCA prometer prazo de entrega
- Sempre orientar validação de compatibilidade
- Escalar para humano quando cliente pedir
"""
from typing import Optional


# Saudações e identificação inicial
SAUDACAO_NOVO_CONTATO = (
    "Olá! 👋 Sou o assistente da Inforrel. "
    "Para te atender melhor, poderia me informar o CNPJ da sua empresa e seu nome?"
)

SAUDACAO_COM_NOME = "Olá, {nome}! 👋 Como posso te ajudar hoje?"

PERGUNTAR_CNPJ = (
    "Para prosseguir, você poderia me informar o CNPJ da sua empresa?"
)

PERGUNTAR_NOME = (
    "Como posso te chamar? 😊"
)

CONFIRMAR_EMPRESA = (
    "Identifiquei que você está falando em nome da empresa *{empresa}* "
    "(CNPJ {cnpj}). Está correto?"
)

MULTIPLAS_EMPRESAS = (
    "Vi que este número está associado a mais de uma empresa: {empresas}. "
    "Sobre qual delas vamos conversar hoje? Pode me informar o CNPJ, por favor."
)

CNPJ_INVALIDO = (
    "Hmm, não consegui validar esse CNPJ. Pode conferir e me enviar novamente?"
)

CNPJ_CONSULTADO_OK = (
    "Ótimo! Confirmei os dados da empresa *{nome}*. "
    "Em que posso ajudar hoje?"
)

# Orçamento / produtos
PEDIR_TIPO_PRODUTO = (
    "Que tipo de equipamento você precisa? "
    "Trabalhamos com:\n"
    "• Catracas (torniquetes, balcão, etc.)\n"
    "• Relógios de ponto (biométrico, facial, cartão)"
)

PEDIR_QUANTIDADE = (
    "Para montar o orçamento, quantas unidades você precisa de *{tipo_produto}*?"
)

PRAZO_NAO_PROMETIDO = (
    "O prazo depende do modelo escolhido e da disponibilidade em estoque. "
    "Nosso time comercial consegue confirmar um prazo preciso após definirmos o modelo. "
    "Posso te ajudar a escolher o modelo ideal?"
)

PRECO_NAO_NEGOCIADO = (
    "Os valores podem variar conforme quantidade e condições. "
    "Nosso vendedor pode avaliar as melhores condições para seu caso. "
    "Quer que eu prepare um orçamento?"
)

COMPATIBILIDADE_SISTEMA = (
    "Para garantir compatibilidade com o sistema da sua empresa, "
    "recomendo confirmar com o fornecedor do seu software. "
    "Se preferir, posso passar suas informações ao nosso time técnico."
)

# Escalonamento
ESCALADO_HUMANO = (
    "Claro! Vou passar sua solicitação para um de nossos atendentes. "
    "Em breve alguém entrará em contato por aqui. 🙋"
)

RECLAMACAO_ESCALADA = (
    "Lamento pelo inconveniente! Vou escalar sua solicitação para nosso "
    "time de suporte. Em breve alguém entrará em contato."
)

# Fallback
NAO_ENTENDI = (
    "Desculpa, não entendi muito bem. Pode reformular sua mensagem? "
    "Se preferir, posso transferir para um atendente humano."
)

FORA_CONTEXTO = (
    "Sou o assistente de vendas da Inforrel e posso ajudar com "
    "catracas e relógios de ponto. Em que posso te ajudar?"
)

# Fallback quando RAG nao encontra trechos com score suficiente
PRODUTO_SEM_CONTEXTO = (
    "Ainda não tenho uma resposta precisa sobre isso por aqui. "
    "Posso te passar para um de nossos atendentes para te ajudar melhor? 🙋"
)

# Orçamento (status)
ORCAMENTO_APROVADO = (
    "Perfeito! Orçamento aprovado registrado. Nosso time comercial dará "
    "continuidade ao processo e entrará em contato em breve. 🎉"
)

ORCAMENTO_REPROVADO = (
    "Tudo bem, agradeço o retorno. Se mudar de ideia ou precisar "
    "de algo mais, estou à disposição."
)


def formatar(template: str, **kwargs) -> str:
    """
    Formata um template com as variáveis fornecidas.
    Kwargs ausentes são substituídos por strings vazias (seguro).
    """
    class _SafeDict(dict):
        def __missing__(self, key):
            return ""
    
    return template.format_map(_SafeDict(**{k: str(v) for k, v in kwargs.items() if v is not None}))
