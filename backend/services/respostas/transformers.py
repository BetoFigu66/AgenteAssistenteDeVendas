"""
Transformers de contexto para mensagens estruturadas.

Cada função recebe um dict de contexto e retorna o dict enriquecido.
As chaves dos transformers são serializáveis (futuro: coluna no banco).
"""

from __future__ import annotations

from typing import Callable

ContextoMensagem = dict
TransformerFn = Callable[[ContextoMensagem], ContextoMensagem]


def _juntar_lista(itens: list[str]) -> str:
    """Junta itens com vírgula e 'e' antes do último."""
    itens = [i for i in itens if i]
    if not itens:
        return ""
    if len(itens) == 1:
        return itens[0]
    if len(itens) == 2:
        return f"{itens[0]} e {itens[1]}"
    return f"{', '.join(itens[:-1])} e {itens[-1]}"


def _nome_informado(ctx: ContextoMensagem) -> str:
    return (ctx.get("nome") or "").strip()


def _tem_documento(ctx: ContextoMensagem) -> bool:
    if ctx.get("tem_documento"):
        return True
    return bool(ctx.get("cnpj") or ctx.get("cpf"))


def montar_pedido_identificacao(ctx: ContextoMensagem) -> ContextoMensagem:
    """Monta o trecho pedindo nome e/ou documento, conforme o que falta."""
    pedidos: list[str] = []
    if not _nome_informado(ctx):
        pedidos.append("o seu nome")
    if not _tem_documento(ctx):
        pedidos.append("o CNPJ da sua empresa ou seu CPF")
    ctx["pedido_identificacao"] = _juntar_lista(pedidos)
    return ctx


def montar_saudacao_novo(ctx: ContextoMensagem) -> ContextoMensagem:
    """
    Preenche saudacao e linha_pedido para SAUDACAO_NOVO_CONTATO.

    Contexto opcional:
    - nome: str
    - tem_documento: bool
    - modo: 'identificacao' (padrão) | 'orcamento'
    """
    nome = _nome_informado(ctx)
    modo = ctx.get("modo", "identificacao")

    ctx["saudacao"] = f"Olá, {nome}!" if nome else "Olá!"

    if modo == "orcamento":
        ctx["linha_pedido"] = ""
        return ctx

    ctx = montar_pedido_identificacao(ctx)
    pedido = ctx.get("pedido_identificacao", "")
    if pedido:
        ctx["linha_pedido"] = (
            f"\nPara te atender melhor, poderia me informar {pedido}?"
        )
    else:
        ctx["linha_pedido"] = ""
    return ctx


def montar_perguntar_cnpj(ctx: ContextoMensagem) -> ContextoMensagem:
    """Preenche pedido_identificacao para PERGUNTAR_CNPJ."""
    ctx = montar_pedido_identificacao(ctx)
    pedido = ctx.get("pedido_identificacao", "")
    if pedido:
        ctx["texto_corpo"] = f"Para prosseguir, poderia me informar {pedido}?"
    else:
        ctx["texto_corpo"] = "Em que posso te ajudar hoje?"
    return ctx


def montar_resumo_finalizando(ctx: ContextoMensagem) -> ContextoMensagem:
    """Monta a lista de itens do resumo (Fase F — F4) a partir do que foi capturado."""
    linhas: list[str] = []
    if ctx.get("modelo"):
        detalhes = ctx["modelo"]
        if ctx.get("marca"):
            detalhes += f" ({ctx['marca']})"
        linhas.append(f"- Modelo: {detalhes}")
    if ctx.get("categorias"):
        linhas.append(f"- Categorias: {ctx['categorias']}")
    if ctx.get("aplicacao"):
        linhas.append(f"- Aplicação: {ctx['aplicacao']}")
    if ctx.get("atributos"):
        atributos = ctx["atributos"]
        if isinstance(atributos, dict) and atributos:
            partes = [f"{k.replace('_', ' ')}: {v}" for k, v in atributos.items()]
            linhas.append(f"- Atributos: {', '.join(partes)}")
    if ctx.get("software"):
        linhas.append(f"- Software de ponto: {ctx['software']}")
    if ctx.get("software_acesso"):
        linhas.append(f"- Software de controle de acesso: {ctx['software_acesso']}")
    if ctx.get("interesse_sistema_nuvem"):
        linhas.append(f"- Interesse em sistema na nuvem: {ctx['interesse_sistema_nuvem']}")
    if ctx.get("homologado_software"):
        linhas.append(f"- Homologação: {ctx['homologado_software']}")
    if ctx.get("faixa_funcionarios"):
        linhas.append(f"- Funcionários: {ctx['faixa_funcionarios']}")
    if ctx.get("quantidade"):
        linhas.append(f"- Quantidade: {ctx['quantidade']}")
    ctx["itens_resumo"] = "\n".join(linhas)
    return ctx


TRANSFORMERS: dict[str, TransformerFn] = {
    "montar_saudacao_novo": montar_saudacao_novo,
    "montar_pedido_identificacao": montar_pedido_identificacao,
    "montar_perguntar_cnpj": montar_perguntar_cnpj,
    "montar_resumo_finalizando": montar_resumo_finalizando,
}
