"""
Catálogo de mensagens estruturadas.

Cada entrada: id estável, código (auditoria), corpo com placeholders e transformers.
Futuro: persistir id + mensagem + transformer_keys no banco; lógica nos transformers.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Union

from . import templates as fmt
from .transformers import TRANSFORMERS, ContextoMensagem


class MensagemId(IntEnum):
    """IDs estáveis — não reordenar valores existentes."""

    SAUDACAO_NOVO_CONTATO = 1
    SAUDACAO_COM_NOME = 2
    PERGUNTAR_CNPJ = 3
    PERGUNTAR_DATA_NASCIMENTO = 4
    CPF_INVALIDO = 5
    CPF_CONSULTADO_OK = 6
    PERGUNTAR_NOME = 7
    CONFIRMAR_EMPRESA = 8
    MULTIPLAS_EMPRESAS = 9
    CNPJ_INVALIDO = 10
    CNPJ_CONSULTADO_OK = 11
    PEDIR_TIPO_PRODUTO = 12
    PEDIR_QUANTIDADE = 13
    PRAZO_NAO_PROMETIDO = 14
    PRECO_NAO_NEGOCIADO = 15
    COMPATIBILIDADE_SISTEMA = 16
    ESCALADO_HUMANO = 17
    RECLAMACAO_ESCALADA = 18
    NAO_ENTENDI = 19
    FORA_CONTEXTO = 20
    PRODUTO_SEM_CONTEXTO = 21
    ORCAMENTO_APROVADO = 22
    ORCAMENTO_REPROVADO = 23
    PEDIR_MODELO = 24
    PEDIR_SOFTWARE_PONTO = 25
    PEDIR_FAIXA_FUNCIONARIOS = 26
    INICIAR_FINALIZANDO = 27
    RETOMAR_PERGUNTA_PENDENTE = 28
    RESUMO_FINALIZANDO = 29
    ORCAMENTO_ENCAMINHADO = 30
    MODELO_NAO_RECONHECIDO = 31
    PERGUNTA_CONTINUACAO_ATENDIMENTO = 32
    CONFIRMAR_INTERESSE_ANTERIOR = 33
    PERGUNTA_FECHAMENTO_ATENDIMENTO = 34
    DESPEDIDA_ATENDIMENTO_ENCERRADO = 35
    PEDIR_TIPO_CATALOGO = 36
    CATALOGO_ENVIADO = 37
    CATALOGO_INDISPONIVEL = 38
    RAG_PEDIR_CLARIFICACAO = 39
    RAG_ESCALADO_SEM_BASE = 40


@dataclass(frozen=True)
class MensagemTemplate:
    id: int
    codigo: str
    mensagem: str
    transformers: tuple[str, ...] = ()


CATALOGO: dict[int, MensagemTemplate] = {
    MensagemId.SAUDACAO_NOVO_CONTATO: MensagemTemplate(
        id=MensagemId.SAUDACAO_NOVO_CONTATO,
        codigo="SAUDACAO_NOVO_CONTATO",
        mensagem="{saudacao} 👋 Sou o assistente da Inforrel.{linha_pedido}",
        transformers=("montar_saudacao_novo",),
    ),
    MensagemId.SAUDACAO_COM_NOME: MensagemTemplate(
        id=MensagemId.SAUDACAO_COM_NOME,
        codigo="SAUDACAO_COM_NOME",
        mensagem="Olá, {nome}! 👋 Como posso te ajudar hoje?",
    ),
    MensagemId.PERGUNTAR_CNPJ: MensagemTemplate(
        id=MensagemId.PERGUNTAR_CNPJ,
        codigo="PERGUNTAR_CNPJ",
        mensagem="{texto_corpo}",
        transformers=("montar_perguntar_cnpj",),
    ),
    MensagemId.PERGUNTAR_DATA_NASCIMENTO: MensagemTemplate(
        id=MensagemId.PERGUNTAR_DATA_NASCIMENTO,
        codigo="PERGUNTAR_DATA_NASCIMENTO",
        mensagem=(
            "Anotei seu CPF. Para concluir o cadastro, qual é a sua data de nascimento? "
            "(formato DD/MM/AAAA)"
        ),
    ),
    MensagemId.CPF_INVALIDO: MensagemTemplate(
        id=MensagemId.CPF_INVALIDO,
        codigo="CPF_INVALIDO",
        mensagem="Hmm, não consegui validar esse CPF. Pode conferir os dígitos e me enviar novamente?",
    ),
    MensagemId.CPF_CONSULTADO_OK: MensagemTemplate(
        id=MensagemId.CPF_CONSULTADO_OK,
        codigo="CPF_CONSULTADO_OK",
        mensagem="Ótimo! Confirmei seus dados, {nome}. Em que posso ajudar hoje?",
    ),
    MensagemId.PERGUNTAR_NOME: MensagemTemplate(
        id=MensagemId.PERGUNTAR_NOME,
        codigo="PERGUNTAR_NOME",
        mensagem="Como posso te chamar? 😊",
    ),
    MensagemId.CONFIRMAR_EMPRESA: MensagemTemplate(
        id=MensagemId.CONFIRMAR_EMPRESA,
        codigo="CONFIRMAR_EMPRESA",
        mensagem=(
            "Identifiquei que você está falando em nome da empresa *{empresa}* (CNPJ {cnpj}).\n"
            "Está correto?"
        ),
    ),
    MensagemId.MULTIPLAS_EMPRESAS: MensagemTemplate(
        id=MensagemId.MULTIPLAS_EMPRESAS,
        codigo="MULTIPLAS_EMPRESAS",
        mensagem=(
            "Vi que este número está associado a mais de uma empresa: {empresas}.\n"
            "Sobre qual delas vamos conversar hoje? Pode me informar o CNPJ, por favor."
        ),
    ),
    MensagemId.CNPJ_INVALIDO: MensagemTemplate(
        id=MensagemId.CNPJ_INVALIDO,
        codigo="CNPJ_INVALIDO",
        mensagem="Hmm, não consegui validar esse CNPJ. Pode conferir e me enviar novamente?",
    ),
    MensagemId.CNPJ_CONSULTADO_OK: MensagemTemplate(
        id=MensagemId.CNPJ_CONSULTADO_OK,
        codigo="CNPJ_CONSULTADO_OK",
        mensagem="Ótimo! Confirmei os dados da empresa *{nome}*. Em que posso ajudar hoje?",
    ),
    MensagemId.PEDIR_TIPO_PRODUTO: MensagemTemplate(
        id=MensagemId.PEDIR_TIPO_PRODUTO,
        codigo="PEDIR_TIPO_PRODUTO",
        mensagem=(
            "Que tipo de equipamento você precisa? Trabalhamos com:\n"
            "• Catracas (torniquetes, balcão, etc.)\n"
            "• Relógios de ponto (biométrico, facial, cartão)"
        ),
    ),
    MensagemId.PEDIR_QUANTIDADE: MensagemTemplate(
        id=MensagemId.PEDIR_QUANTIDADE,
        codigo="PEDIR_QUANTIDADE",
        mensagem="Para montar o orçamento, quantas unidades você precisa de *{tipo_produto}*?",
    ),
    MensagemId.PRAZO_NAO_PROMETIDO: MensagemTemplate(
        id=MensagemId.PRAZO_NAO_PROMETIDO,
        codigo="PRAZO_NAO_PROMETIDO",
        mensagem=(
            "O prazo depende do modelo escolhido e da disponibilidade em estoque. "
            "Nosso time comercial consegue confirmar um prazo preciso após definirmos o modelo. "
            "Posso te ajudar a escolher o modelo ideal?"
        ),
    ),
    MensagemId.PRECO_NAO_NEGOCIADO: MensagemTemplate(
        id=MensagemId.PRECO_NAO_NEGOCIADO,
        codigo="PRECO_NAO_NEGOCIADO",
        mensagem=(
            "Os valores podem variar conforme quantidade e condições. "
            "Nosso vendedor pode avaliar as melhores condições para seu caso. "
            "Quer que eu prepare um orçamento?"
        ),
    ),
    MensagemId.COMPATIBILIDADE_SISTEMA: MensagemTemplate(
        id=MensagemId.COMPATIBILIDADE_SISTEMA,
        codigo="COMPATIBILIDADE_SISTEMA",
        mensagem=(
            "Para garantir compatibilidade com o sistema da sua empresa, "
            "recomendo confirmar com o fornecedor do seu software. "
            "Se preferir, posso passar suas informações ao nosso time técnico."
        ),
    ),
    MensagemId.ESCALADO_HUMANO: MensagemTemplate(
        id=MensagemId.ESCALADO_HUMANO,
        codigo="ESCALADO_HUMANO",
        mensagem=(
            "Claro! Vou passar sua solicitação para um de nossos atendentes.\n"
            "Em breve alguém entrará em contato por aqui. 🙋"
        ),
    ),
    MensagemId.RECLAMACAO_ESCALADA: MensagemTemplate(
        id=MensagemId.RECLAMACAO_ESCALADA,
        codigo="RECLAMACAO_ESCALADA",
        mensagem=(
            "Lamento pelo inconveniente! Vou escalar sua solicitação para nosso time de suporte.\n"
            "Em breve alguém entrará em contato."
        ),
    ),
    MensagemId.NAO_ENTENDI: MensagemTemplate(
        id=MensagemId.NAO_ENTENDI,
        codigo="NAO_ENTENDI",
        mensagem=(
            "Desculpa, não entendi muito bem. Pode reformular sua mensagem?\n"
            "Se preferir, posso transferir para um atendente humano."
        ),
    ),
    MensagemId.FORA_CONTEXTO: MensagemTemplate(
        id=MensagemId.FORA_CONTEXTO,
        codigo="FORA_CONTEXTO",
        mensagem=(
            "Sou o assistente de vendas da Inforrel e posso ajudar com catracas e relógios de ponto.\n"
            "Em que posso te ajudar?"
        ),
    ),
    MensagemId.PRODUTO_SEM_CONTEXTO: MensagemTemplate(
        id=MensagemId.PRODUTO_SEM_CONTEXTO,
        codigo="PRODUTO_SEM_CONTEXTO",
        mensagem=(
            "Ainda não tenho uma resposta precisa sobre isso por aqui.\n"
            "Posso te passar para um de nossos atendentes para te ajudar melhor? 🙋"
        ),
    ),
    MensagemId.ORCAMENTO_APROVADO: MensagemTemplate(
        id=MensagemId.ORCAMENTO_APROVADO,
        codigo="ORCAMENTO_APROVADO",
        mensagem=(
            "Perfeito! Orçamento aprovado registrado.\n"
            "Nosso time comercial dará continuidade ao processo e entrará em contato em breve. 🎉"
        ),
    ),
    MensagemId.ORCAMENTO_REPROVADO: MensagemTemplate(
        id=MensagemId.ORCAMENTO_REPROVADO,
        codigo="ORCAMENTO_REPROVADO",
        mensagem=(
            "Tudo bem, agradeço o retorno.\n"
            "Se mudar de ideia ou precisar de algo mais, estou à disposição."
        ),
    ),
    MensagemId.PEDIR_MODELO: MensagemTemplate(
        id=MensagemId.PEDIR_MODELO,
        codigo="PEDIR_MODELO",
        mensagem=(
            "O relógio seria cartográfico ou eletrônico? Se eletrônico: cartão de "
            "proximidade, cartão de barras, biometria ou reconhecimento facial?"
        ),
    ),
    MensagemId.PEDIR_SOFTWARE_PONTO: MensagemTemplate(
        id=MensagemId.PEDIR_SOFTWARE_PONTO,
        codigo="PEDIR_SOFTWARE_PONTO",
        mensagem="Qual software de ponto vocês usam hoje? (ex.: Domínio, Alterdata, TOTVS, ou nenhum)",
    ),
    MensagemId.PEDIR_FAIXA_FUNCIONARIOS: MensagemTemplate(
        id=MensagemId.PEDIR_FAIXA_FUNCIONARIOS,
        codigo="PEDIR_FAIXA_FUNCIONARIOS",
        mensagem="Quantos funcionários vão usar o relógio de ponto?",
    ),
    MensagemId.INICIAR_FINALIZANDO: MensagemTemplate(
        id=MensagemId.INICIAR_FINALIZANDO,
        codigo="INICIAR_FINALIZANDO",
        mensagem="Ótimo! Vou precisar de algumas informações para montar o orçamento.",
    ),
    MensagemId.RETOMAR_PERGUNTA_PENDENTE: MensagemTemplate(
        id=MensagemId.RETOMAR_PERGUNTA_PENDENTE,
        codigo="RETOMAR_PERGUNTA_PENDENTE",
        mensagem="Voltando ao orçamento: {pergunta}",
    ),
    MensagemId.RESUMO_FINALIZANDO: MensagemTemplate(
        id=MensagemId.RESUMO_FINALIZANDO,
        codigo="RESUMO_FINALIZANDO",
        mensagem=(
            "Show! Aqui está o resumo do que entendi:\n{itens_resumo}\n\n"
            "Posso encaminhar para nosso time preparar o orçamento?"
        ),
        transformers=("montar_resumo_finalizando",),
    ),
    MensagemId.ORCAMENTO_ENCAMINHADO: MensagemTemplate(
        id=MensagemId.ORCAMENTO_ENCAMINHADO,
        codigo="ORCAMENTO_ENCAMINHADO",
        mensagem="Recebi suas informações. Nossa equipe vai preparar o orçamento e retorna em breve.",
    ),
    MensagemId.MODELO_NAO_RECONHECIDO: MensagemTemplate(
        id=MensagemId.MODELO_NAO_RECONHECIDO,
        codigo="MODELO_NAO_RECONHECIDO",
        mensagem=(
            "Não encontrei esse modelo no nosso catálogo. "
            "O relógio seria cartográfico ou eletrônico? Se eletrônico: cartão de "
            "proximidade, cartão de barras, biometria ou reconhecimento facial?"
        ),
    ),
    MensagemId.PERGUNTA_CONTINUACAO_ATENDIMENTO: MensagemTemplate(
        id=MensagemId.PERGUNTA_CONTINUACAO_ATENDIMENTO,
        codigo="PERGUNTA_CONTINUACAO_ATENDIMENTO",
        mensagem=(
            "Oi! Vi que você já conversou conosco antes sobre {resumo_curto}. "
            "Quer continuar de onde paramos ou é um pedido novo?\n\n"
            "1) Continuar\n"
            "2) Novo pedido"
        ),
    ),
    MensagemId.CONFIRMAR_INTERESSE_ANTERIOR: MensagemTemplate(
        id=MensagemId.CONFIRMAR_INTERESSE_ANTERIOR,
        codigo="CONFIRMAR_INTERESSE_ANTERIOR",
        mensagem=(
            "Da última vez você se interessou por {produtos_anteriores}. "
            "Ainda quer continuar com isso ou mudou de ideia?"
        ),
    ),
    MensagemId.PERGUNTA_FECHAMENTO_ATENDIMENTO: MensagemTemplate(
        id=MensagemId.PERGUNTA_FECHAMENTO_ATENDIMENTO,
        codigo="PERGUNTA_FECHAMENTO_ATENDIMENTO",
        mensagem="Posso te ajudar em mais alguma coisa?",
    ),
    MensagemId.DESPEDIDA_ATENDIMENTO_ENCERRADO: MensagemTemplate(
        id=MensagemId.DESPEDIDA_ATENDIMENTO_ENCERRADO,
        codigo="DESPEDIDA_ATENDIMENTO_ENCERRADO",
        mensagem="Tudo bem! Qualquer coisa é só chamar por aqui. Até mais! 👋",
    ),
    MensagemId.PEDIR_TIPO_CATALOGO: MensagemTemplate(
        id=MensagemId.PEDIR_TIPO_CATALOGO,
        codigo="PEDIR_TIPO_CATALOGO",
        mensagem="Temos catálogo de catracas e de relógios de ponto. Qual te interessa?",
    ),
    MensagemId.CATALOGO_ENVIADO: MensagemTemplate(
        id=MensagemId.CATALOGO_ENVIADO,
        codigo="CATALOGO_ENVIADO",
        mensagem="Aqui está o catálogo de {tipo}: {link}",
    ),
    MensagemId.CATALOGO_INDISPONIVEL: MensagemTemplate(
        id=MensagemId.CATALOGO_INDISPONIVEL,
        codigo="CATALOGO_INDISPONIVEL",
        mensagem=(
            "No momento não tenho o link do catálogo de {tipo} configurado por aqui. "
            "Vou pedir para nosso time te enviar diretamente."
        ),
    ),
    MensagemId.RAG_PEDIR_CLARIFICACAO: MensagemTemplate(
        id=MensagemId.RAG_PEDIR_CLARIFICACAO,
        codigo="RAG_PEDIR_CLARIFICACAO",
        mensagem=(
            "Não tenho certeza se consigo te responder com precisão ainda. "
            "Pode me explicar com outras palavras o que você gostaria de saber sobre o produto?"
        ),
    ),
    MensagemId.RAG_ESCALADO_SEM_BASE: MensagemTemplate(
        id=MensagemId.RAG_ESCALADO_SEM_BASE,
        codigo="RAG_ESCALADO_SEM_BASE",
        mensagem=(
            "Ainda não encontrei uma resposta segura para isso na nossa base. "
            "Vou te transferir para um de nossos atendentes, que já assume a conversa por aqui. 🙋"
        ),
    ),
}


def resolver_mensagem(mensagem_id: Union[MensagemId, int]) -> MensagemTemplate:
    """Retorna a definição estruturada pelo ID estável."""
    chave = int(mensagem_id)
    try:
        return CATALOGO[chave]
    except KeyError as exc:
        raise ValueError(f"MensagemId desconhecido: {mensagem_id}") from exc


def aplicar_transformers(
    transformer_keys: tuple[str, ...],
    contexto: ContextoMensagem,
) -> ContextoMensagem:
    """Executa a cadeia de transformers sobre o contexto."""
    ctx = dict(contexto)
    for chave in transformer_keys:
        fn = TRANSFORMERS.get(chave)
        if fn is None:
            raise ValueError(f"Transformer não registrado: {chave}")
        ctx = fn(ctx)
    return ctx


def renderizar_mensagem(
    mensagem_id: Union[MensagemId, int],
    contexto: ContextoMensagem | None = None,
) -> tuple[str, str]:
    """
    Renderiza uma mensagem pelo ID.

    Returns:
        (texto, codigo) — codigo para auditoria (template_usado).
    """
    tpl = resolver_mensagem(mensagem_id)
    ctx = aplicar_transformers(tpl.transformers, contexto or {})
    texto = fmt.formatar(tpl.mensagem, **ctx)
    return texto, tpl.codigo
