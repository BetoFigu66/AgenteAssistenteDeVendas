"""
Confirmação do nome de perfil do WhatsApp (`ProfileName`) antes de gravá-lo.

Decisão do Beto (26/09): o nome do perfil não vira `Contato.nome` sozinho. No início do
atendimento, se ele passar em `utils.nome_perfil.nome_perfil_aproveitavel`, o bot pergunta
"Olá, <nome>! Posso te chamar assim ou seu nome é outro?" no lugar em que hoje pediria o
nome. Só a resposta do cliente decide o que é gravado.

Estado da pergunta, por atendimento, em `AtendimentoInfo` (sem migração):

- `nome_perfil_proposto`: o nome que foi oferecido ao cliente, para confirmar exatamente
  ele (o `ProfileName` pode mudar entre mensagens e a interface web nem o manda).
- `nome_perfil_confirmacao`: `aguardando` enquanto a pergunta está em aberto; depois,
  o desfecho, que é também o registro de origem do nome:
  `confirmado` (o nome do perfil foi aceito pelo cliente), `outro_nome` (o cliente deu
  outro nome), `pedido_nome` (disse "não" sem dar nome; o bot pergunta o nome uma vez)
  ou `ignorado` (respondeu outra coisa; não se pergunta de novo neste atendimento).

Fluxo:

1. Quem montaria o pedido de nome chama `saudacao_primeiro_contato` ou
   `nome_perfil_a_confirmar`/`registrar_pergunta` (ver `estados/esclarecendo.py` e
   `regras_esclarecendo.py`).
2. Na mensagem seguinte, `tratar_resposta` roda **antes** do motor
   (`ProcessadorMensagem._decidir_resposta`): grava o nome e o desfecho. Fica fora do
   motor de propósito, porque `FORNECER_CNPJ`/`FORNECER_CPF` são `exclusivo` e
   descartariam uma Ação `pre` da mesma mensagem ("sim, o CNPJ é ...").
3. Se a mensagem era só a resposta ao nome ("sim", "Carlos", "não"), a Regra global
   `REGRA_RESPOSTA_SO_AO_NOME` responde e retoma o que estava em aberto (pedido de
   documento ou pergunta do orçamento). Se trazia mais coisa, o fluxo normal responde.
"""

from __future__ import annotations

import re
from typing import Optional

from models import FaseAtendimento, OrigemInfo

from services.classificador import Intencao, _limpar_nome
from services.conversacao.campos_pendentes import campos_pendentes
from services.respostas import MensagemId

from .acoes import Acao, ContextoAcao, GrupoAcoes
from .motor import RegraIntencao

CHAVE_NOME_PERFIL_PROPOSTO = "nome_perfil_proposto"
CHAVE_NOME_PERFIL_CONFIRMACAO = "nome_perfil_confirmacao"
CHAVES_CONFIRMACAO_NOME_PERFIL = frozenset({CHAVE_NOME_PERFIL_PROPOSTO, CHAVE_NOME_PERFIL_CONFIRMACAO})
"""Para quem varre `AtendimentoInfo` inteiro (ex.: `FinalizandoState._resolver_modelo`)
saber que estas chaves são controle da conversa, não dado do orçamento."""

AGUARDANDO = "aguardando"
CONFIRMADO = "confirmado"
OUTRO_NOME = "outro_nome"
PEDIDO_NOME = "pedido_nome"
IGNORADO = "ignorado"

# Mesma chave de `estados/esclarecendo.py::_CHAVE_DOC_PENDENTE` (import direto seria
# circular: `estados/esclarecendo.py` importa este módulo).
_CHAVE_DOC_PENDENTE = "documento_fiscal_pendente"

# Uma "palavra" de confirmação. A mensagem inteira pode ser uma sequência delas
# ("sim, pode", "pode sim!", "claro 👍").
_CONFIRMACAO = (
    r"(?:sim|s|ss|pode(?:\s+sim|\s+ser|\s+(?:me\s+)?chamar(?:\s+assim)?)?|isso(?:\s+mesmo|\s+a[ií])?"
    r"|ok|okay|okey|claro(?:\s+que\s+sim)?|certo|correto|exato|perfeito|beleza|blz"
    r"|com\s+certeza|t[aá]\s+(?:bom|certo|[oó]timo)|tudo\s+bem|confirmo|assim\s+mesmo|[eé]\s+isso)"
)
_RE_CONFIRMACAO_PURA = re.compile(rf"{_CONFIRMACAO}(?:\s+{_CONFIRMACAO})*", re.IGNORECASE)

# Início de mensagem que confirma e continua com outro assunto ("sim, quero orçamento").
# Mais restrito que `_CONFIRMACAO`: "pode me mandar o catálogo?" e "ok, e o preço?" não
# são resposta à pergunta do nome.
_RE_CONFIRMACAO_NO_INICIO = re.compile(
    r"^\s*(?:sim|pode\s+sim|pode\s+ser|pode\s+(?:me\s+)?chamar\s+assim|isso\s+mesmo|claro|com\s+certeza)"
    r"(?=[\s,.!;:]|$)",
    re.IGNORECASE,
)

# Emoji de positivo (joinha, ok, check), com variação de tom de pele ou seletor de emoji.
_RE_EMOJI_POSITIVO = re.compile("[\U0001F44D\U0001F44C✅✔☑]️?[\U0001F3FB-\U0001F3FF]?")

_RE_NEGACAO_PURA = re.compile(r"^\s*(?:n[aã]o|n)(?:\s*,?\s*obrigad[oa])?\s*[.!]*\s*$", re.IGNORECASE)

# Resposta de nome sem gatilho ("Carlos", "é Carlos", "sou Carlos"). Palavras que
# aparecem sozinhas numa resposta e não são nome.
_RE_PREFIXO_NOME_SOLTO = re.compile(r"^(?:[ée]|sou|aqui\s+[ée])\s+", re.IGNORECASE)
_PALAVRAS_NAO_NOME = frozenset({
    "oi", "ola", "olá", "bom", "boa", "dia", "tarde", "noite", "tudo", "bem", "obrigado",
    "obrigada", "valeu", "nao", "não", "sim", "ok", "pode", "isso", "claro", "certo", "blz",
    "beleza", "quero", "queria", "preciso", "eu", "meu", "minha", "nome", "empresa",
    "cnpj", "cpf", "orçamento", "orcamento", "catraca", "relógio", "relogio", "ponto",
})
_MAXIMO_PALAVRAS_NOME_SOLTO = 4

# Intenções que uma resposta "só ao nome" pode ter. Qualquer outra (orçamento, dúvida,
# escalonamento...) significa que a mensagem traz outro assunto e o fluxo normal responde.
_INTENCOES_RESPOSTA_AO_NOME = frozenset({
    Intencao.CONFIRMAR, Intencao.NEGAR, Intencao.FORNECER_NOME, Intencao.SAUDACAO, Intencao.DESCONHECIDO,
})


def _tem_outras_entidades(entidades) -> bool:
    """True se a mensagem traz algo além de nome (documento, produto, resposta do
    orçamento...), ou seja, não é só a resposta à pergunta do nome."""
    return bool(
        entidades.cnpjs or entidades.cpfs or entidades.datas_nascimento or entidades.tipos_produto
        or entidades.quantidades or entidades.emails or entidades.software_ponto or entidades.software_acesso
        or entidades.tipo_leitor_mencionado or entidades.faixa_funcionarios is not None or entidades.marca
        or entidades.aplicacao or entidades.atributos
    )


def _status(ctx: ContextoAcao) -> Optional[str]:
    if not ctx.atendimento:
        return None
    return ctx.processador._info_atendimento(ctx.db, ctx.atendimento.id, CHAVE_NOME_PERFIL_CONFIRMACAO)


def _salvar(ctx: ContextoAcao, chave: str, valor: str, pendente: bool) -> None:
    ctx.processador._salvar_info_atendimento(
        ctx.db, ctx.atendimento.id, chave, valor, pendente=pendente, origem=OrigemInfo.SISTEMA
    )


def eh_confirmacao_pura(texto: str) -> bool:
    """True se a mensagem inteira é uma confirmação ("sim", "pode sim", "ok", "👍")."""
    sem_emoji, emojis = _RE_EMOJI_POSITIVO.subn(" ", texto or "")
    resto = re.sub(r"[\s,.!;:]+", " ", sem_emoji).strip()
    if not resto:
        return emojis > 0
    return bool(_RE_CONFIRMACAO_PURA.fullmatch(resto))


def _comeca_com_confirmacao(texto: str) -> bool:
    return bool(_RE_CONFIRMACAO_NO_INICIO.match(texto or "")) or bool(
        _RE_EMOJI_POSITIVO.match((texto or "").lstrip())
    )


def _nome_solto(texto: str) -> Optional[str]:
    """Nome dado sem gatilho, só como resposta à pergunta ("Carlos", "é o Cadu" já é
    pego pelo classificador). Só é chamada com a pergunta do nome em aberto."""
    candidato = _RE_PREFIXO_NOME_SOLTO.sub("", (texto or "").strip().strip(".!,;"))
    palavras = candidato.split()
    if not 1 <= len(palavras) <= _MAXIMO_PALAVRAS_NOME_SOLTO:
        return None
    if any(not p.isalpha() or len(p) < 2 or p.lower() in _PALAVRAS_NAO_NOME for p in palavras):
        return None
    return _limpar_nome(candidato)


def nome_perfil_a_confirmar(ctx: ContextoAcao) -> Optional[str]:
    """Nome de perfil a oferecer na pergunta de confirmação, ou None se não cabe perguntar:
    sem nome de perfil aproveitável, cliente já escreveu um nome nesta mensagem, contato já
    tem nome, ou a pergunta já foi feita neste atendimento (não insiste)."""
    if not ctx.nome_perfil or ctx.resultado_class.entidades.nomes:
        return None
    if ctx.contato and ctx.contato.nome:
        return None
    if _status(ctx):
        return None
    return ctx.nome_perfil


def registrar_pergunta(ctx: ContextoAcao, nome: str) -> None:
    """Marca a pergunta de confirmação como feita, guardando o nome oferecido. Exige
    `ctx.atendimento` (quem pergunta já garantiu o atendimento)."""
    _salvar(ctx, CHAVE_NOME_PERFIL_PROPOSTO, nome, pendente=True)
    _salvar(ctx, CHAVE_NOME_PERFIL_CONFIRMACAO, AGUARDANDO, pendente=True)
    if ctx.dlog:
        ctx.dlog.log("nome_perfil", f"pergunta de confirmação feita nome={nome!r} (atendimento {ctx.atendimento.id})")


def contexto_confirmacao(nome: str, apresentar: bool, pedir_documento: bool) -> dict:
    """Contexto de `MensagemId.CONFIRMAR_NOME_PERFIL` (ver `montar_confirmar_nome_perfil`)."""
    return {"nome": nome, "apresentar": apresentar, "pedir_documento": pedir_documento}


def saudacao_primeiro_contato(ctx: ContextoAcao, modo: str) -> tuple[MensagemId, dict]:
    """Saudação de um contato totalmente novo (`StatusIdentificacao.NOVO`).

    Com nome de perfil a confirmar, a pergunta de confirmação substitui o pedido de nome
    e o pedido de CNPJ/CPF continua como era (só no `modo="identificacao"`; no orçamento
    ele nunca vinha). Sem isso, é a `SAUDACAO_NOVO_CONTATO` de sempre, com o nome que o
    cliente escreveu nesta mensagem, se escreveu. Exige `ctx.atendimento`.
    """
    entidades = ctx.resultado_class.entidades
    tem_documento = bool(entidades.cnpjs or entidades.cpfs)
    nome_perfil = nome_perfil_a_confirmar(ctx)
    if nome_perfil:
        registrar_pergunta(ctx, nome_perfil)
        pedir_documento = modo == "identificacao" and not tem_documento
        return (MensagemId.CONFIRMAR_NOME_PERFIL, contexto_confirmacao(nome_perfil, True, pedir_documento))
    contexto = {"nome": entidades.nomes[0] if entidades.nomes else None, "modo": modo}
    if modo == "identificacao":
        contexto["tem_documento"] = tem_documento
    return (MensagemId.SAUDACAO_NOVO_CONTATO, contexto)


def _gravar_nome(ctx: ContextoAcao, nome: str, desfecho: str) -> None:
    # Não sobrescreve um nome que um operador tenha posto enquanto a pergunta esperava.
    if ctx.contato and not ctx.contato.nome:
        ctx.contato.nome = nome
    _salvar(ctx, CHAVE_NOME_PERFIL_CONFIRMACAO, desfecho, pendente=False)
    ctx.nome_resposta_confirmacao = nome
    if ctx.dlog:
        contato_id = ctx.contato.id if ctx.contato else None
        ctx.dlog.log("nome_perfil", f"desfecho={desfecho} nome={nome!r} contato_id={contato_id}")


def tratar_resposta(ctx: ContextoAcao) -> None:
    """Interpreta a resposta à pergunta de confirmação, se ela estiver em aberto.

    Ordem: nome escrito pelo cliente (classificador) → confirmação → nome solto
    ("Carlos") → "não" → qualquer outra coisa, que é "ignorado" e não trava nada. Grava o
    nome em `Contato.nome` e o desfecho em `nome_perfil_confirmacao`; marca
    `ctx.resposta_so_ao_nome` quando a mensagem não trazia mais nada, para
    `REGRA_RESPOSTA_SO_AO_NOME` responder.
    """
    status = _status(ctx)
    if status not in (AGUARDANDO, PEDIDO_NOME):
        return

    conteudo = ctx.conteudo or ""
    entidades = ctx.resultado_class.entidades
    sem_outro_assunto = set(ctx.resultado_class.intencoes) <= _INTENCOES_RESPOSTA_AO_NOME and not (
        _tem_outras_entidades(entidades)
    )
    proposto = ctx.processador._info_atendimento(ctx.db, ctx.atendimento.id, CHAVE_NOME_PERFIL_PROPOSTO)

    # "sim, 11.222.333/0001-81" faz o classificador extrair "Sim" como nome sem gatilho.
    nomes_digitados = [n for n in entidades.nomes if not eh_confirmacao_pura(n)]
    confirmacao_pura = eh_confirmacao_pura(conteudo)
    confirmou = status == AGUARDANDO and bool(proposto) and (confirmacao_pura or _comeca_com_confirmacao(conteudo))

    if nomes_digitados:
        nome = nomes_digitados[0]
        _gravar_nome(ctx, nome, CONFIRMADO if nome == proposto else OUTRO_NOME)
        ctx.resposta_so_ao_nome = sem_outro_assunto
    elif confirmou:
        _gravar_nome(ctx, proposto, CONFIRMADO)
        # "sim, biometria" confirma e responde a pergunta do orçamento: o resto é do fluxo normal.
        ctx.resposta_so_ao_nome = sem_outro_assunto and confirmacao_pura
    elif sem_outro_assunto and (nome := _nome_solto(conteudo)):
        _gravar_nome(ctx, nome, CONFIRMADO if nome == proposto else OUTRO_NOME)
        ctx.resposta_so_ao_nome = True
    elif status == AGUARDANDO and sem_outro_assunto and _RE_NEGACAO_PURA.match(conteudo):
        _salvar(ctx, CHAVE_NOME_PERFIL_CONFIRMACAO, PEDIDO_NOME, pendente=True)
        ctx.pedir_nome_apos_negacao = True
        ctx.resposta_so_ao_nome = True
        if ctx.dlog:
            ctx.dlog.log("nome_perfil", "cliente recusou o nome do perfil sem dar outro → pergunta o nome")
    else:
        _salvar(ctx, CHAVE_NOME_PERFIL_CONFIRMACAO, IGNORADO, pendente=False)
        if ctx.dlog:
            ctx.dlog.log("nome_perfil", "resposta não tratou do nome → ignorado, não pergunta de novo")


async def _executar_resposta_so_ao_nome(ctx: ContextoAcao):
    """Responde a uma mensagem que só tratava do nome e retoma o que estava em aberto:
    a pergunta do orçamento (Finalizando), o pedido de CNPJ/CPF (se foi feito e ainda não
    respondido) ou um "em que posso ajudar"."""
    if ctx.pedir_nome_apos_negacao:
        return (MensagemId.PERGUNTAR_NOME, None)

    p = ctx.processador
    atendimento = ctx.atendimento
    contexto = {"nome": ctx.nome_resposta_confirmacao}

    if atendimento.fase == FaseAtendimento.FINALIZANDO:
        # Import local: `estados/__init__.py` importa `estados/esclarecendo.py`, que
        # importa este módulo; no topo, o import ficaria circular.
        from services.conversacao.estados.finalizando import _contexto_para_campo

        pendentes = campos_pendentes(atendimento)
        if pendentes:
            campo = pendentes[0]
            contexto["segue_pergunta"] = True
            return await p._gerador.gerar_composta(
                [(MensagemId.NOME_ANOTADO, contexto), (campo.mensagem_id, _contexto_para_campo(campo, atendimento))]
            )
        if not atendimento.tipo_produto_atual():
            contexto["segue_pergunta"] = True
            return await p._gerador.gerar_composta(
                [(MensagemId.NOME_ANOTADO, contexto), (MensagemId.PEDIR_TIPO_PRODUTO, None)]
            )
        return (MensagemId.NOME_ANOTADO, contexto)

    sem_documento = not (ctx.empresa or ctx.pessoa)
    doc_pedido = p._info_atendimento(ctx.db, atendimento.id, _CHAVE_DOC_PENDENTE) == "solicitado"
    contexto["pedir_documento"] = sem_documento and doc_pedido
    return (MensagemId.NOME_ANOTADO, contexto)


def _builder_resposta_so_ao_nome(ctx: ContextoAcao) -> GrupoAcoes:
    if not (ctx.resposta_so_ao_nome and ctx.atendimento):
        return GrupoAcoes()
    return GrupoAcoes(exclusivo=[Acao("resposta_so_ao_nome", _executar_resposta_so_ao_nome)])


REGRA_RESPOSTA_SO_AO_NOME = RegraIntencao(
    intencao=None,
    fase=None,
    builder=_builder_resposta_so_ao_nome,
    nome="resposta_so_ao_nome",
)
