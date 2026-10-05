"""
Pilha de perguntas pendentes: o registro do que o sistema perguntou e ainda espera.

Três peças (desenho de ago/2026 com o Beto): o **Planejador** decide o que perguntar
(`campos_pendentes()`, recalculável), o **Registro** guarda o fato de que uma pergunta
foi feita (`PerguntaPendente`, este módulo) e o **Tratador** lê a resposta
(`tratadores.py`). Antes, sem o Registro, cada turno recalculava o que *devia* ter sido
perguntado e lia a mensagem contra isso, não contra o que de fato foi perguntado.

Ciclo de uma pergunta: `empilhar` ao perguntar (reapresentar move para o topo, não
duplica); `resolver_resposta` a cada mensagem do cliente, antes do motor; sai da pilha
quando a resposta é capturada, quando a escada de erro acaba (D3), quando estoura o teto
ou quando o atendimento encerra. Em `ModoOperacao.HUMANO` a pilha é preservada mas não
consumida (o motor nem roda).

Qual pergunta a mensagem responde, nesta ordem:

0. **Reply-to**: o cliente citou a mensagem que levou a pergunta ("Responder" do
   WhatsApp ou da interface web). Evidência forte de *qual* pergunta, mas não prova de
   que é resposta: o tratador ainda valida.
1. **Validação** elimina candidatas (o tratador devolve não reconhecido ou inválido).
2. **Poder discriminante + recência**: tratadores que se identificam sozinhos (CPF, data,
   sinal de modelo) casam em qualquer posição; ambíguos ("sim", número solto, texto
   livre) só com o topo, que é a leva mais recente de perguntas.
3. **Fila serial**: se ainda sobra mais de uma, a resposta é descartada (não adivinhada)
   e o sistema diz que ficou confuso e retoma as perguntas uma por uma.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from models import Atendimento, Mensagem, PerguntaPendente, StatusPergunta
from sqlalchemy.orm import Session
from utils.datetime_utils import utc_now

from services.respostas import MensagemId, RespostaGerada

from .acoes import ContextoAcao
from .campos_pendentes import nao_perguntar_de_novo
from .catalogo_campos import CAMPOS, DESTINO_ATENDIMENTO_INFO, Pergunta
from .tratadores import Leitura, StatusLeitura, Tratador, entrada_de

TETO_PILHA = 3
"""Máximo de perguntas abertas. Passou disso, a mais antiga sai (descartada)."""


ParteResposta = tuple[MensagemId, Optional[dict]]


@dataclass(frozen=True)
class DefinicaoPergunta:
    """O que a pilha precisa saber de uma pergunta para tratá-la.

    - `grava`: a pilha grava a resposta (`aplicar`, ou `AtendimentoInfo[chave]` por
      padrão). `False` quando quem age é uma Regra do motor, que encontra a resposta já
      identificada em `ctx.captura_pilha` (ex.: a data que completa o cadastro PF).
    - `fecha_na_captura`: reconhecer a resposta encerra a pergunta. `False` para o modelo
      do produto, cuja resolução contra o catálogo ainda pode falhar (a Finalizando a
      tira da pilha quando resolve).
    - `trecho_vinculo`: o pedaço de texto que identifica a pergunta dentro da mensagem
      de saída, quando difere de `texto` (o que é reapresentado ao cliente).
    - `max_tentativas` / `ao_sair`: escada de erro (D3). Esgotadas as tentativas de
      captura, a pergunta sai da pilha e `ao_sair` decide o que isso significa (pular,
      escalar, marcar como ignorada). `ao_sair` também roda quando ela sai sem resposta
      por estourar o teto.
    - `confirmacao`: o que dizer ao capturar a resposta na fila serial, no lugar do
      "Anotado!" genérico.
    """

    chave: str
    tratador: Tratador
    grava: bool = True
    fecha_na_captura: bool = True
    aplicar: Optional[Callable[[ContextoAcao, PerguntaPendente, Leitura], None]] = None
    trecho_vinculo: Optional[Callable[[PerguntaPendente], str]] = None
    max_tentativas: Optional[int] = None
    ao_sair: Optional[Callable[[ContextoAcao, PerguntaPendente], None]] = None
    confirmacao: Optional[Callable[[ContextoAcao, PerguntaPendente], Optional[ParteResposta]]] = None


_DEFINICOES: dict[str, DefinicaoPergunta] = {}


def registrar_definicao(definicao: DefinicaoPergunta) -> DefinicaoPergunta:
    _DEFINICOES[definicao.chave] = definicao
    return definicao


def definicao(chave: str) -> Optional[DefinicaoPergunta]:
    return _DEFINICOES.get(chave)


def _definicao_de_campo(campo: Pergunta) -> DefinicaoPergunta:
    grava = campo.destino == DESTINO_ATENDIMENTO_INFO
    return DefinicaoPergunta(
        chave=campo.chave,
        tratador=campo.tratador,
        grava=grava,
        fecha_na_captura=grava,
        max_tentativas=campo.max_tentativas,
    )


for _campo in CAMPOS.values():
    registrar_definicao(_definicao_de_campo(_campo))


# ----------------------------------------------------------------------
# Leitura da pilha
# ----------------------------------------------------------------------


def abertas(atendimento: Optional[Atendimento]) -> list[PerguntaPendente]:
    """Perguntas abertas, da mais antiga para o topo."""
    if atendimento is None:
        return []
    return sorted((p for p in atendimento.perguntas_pendentes if p.aberta), key=lambda p: p.ordem)


def topo(atendimento: Optional[Atendimento]) -> Optional[PerguntaPendente]:
    pilha = abertas(atendimento)
    return pilha[-1] if pilha else None


def fila_serial(atendimento: Optional[Atendimento]) -> list[PerguntaPendente]:
    """Perguntas na fila serial, na ordem em que serão retomadas."""
    return sorted(
        (p for p in abertas(atendimento) if p.posicao_serial is not None), key=lambda p: p.posicao_serial
    )


# ----------------------------------------------------------------------
# Escrita
# ----------------------------------------------------------------------


def leva_atual(ctx: ContextoAcao) -> int:
    """Identificador do turno: o id da mensagem do cliente que provocou as perguntas.

    Sem ele (chamada direta do motor, como fazem vários testes), cada contexto vira um
    turno novo, depois do último registrado, para a recência continuar fazendo sentido.
    """
    if ctx.mensagem_id is not None:
        return ctx.mensagem_id
    if ctx.leva_sem_mensagem is None:
        levas = [p.leva_ultima for p in ctx.atendimento.perguntas_pendentes]
        ctx.leva_sem_mensagem = (max(levas) + 1) if levas else 1
    return ctx.leva_sem_mensagem


def encerrar(
    pergunta: PerguntaPendente,
    status: StatusPergunta,
    valor: Optional[str] = None,
    ctx: Optional[ContextoAcao] = None,
) -> None:
    pergunta.status = status.value
    pergunta.valor_capturado = valor
    pergunta.posicao_serial = None
    pergunta.encerrado_em = utc_now()
    if ctx is not None and status in (StatusPergunta.ESGOTADA, StatusPergunta.DESCARTADA):
        defn = definicao(pergunta.chave)
        if defn is not None and defn.ao_sair is not None:
            defn.ao_sair(ctx, pergunta)


def empilhar(ctx: ContextoAcao, chave: str, texto: str, dados: Optional[dict] = None) -> PerguntaPendente:
    """Registra que `texto` foi perguntado ao cliente neste turno.

    Se a mesma pergunta já está aberta, ela vai para o topo em vez de duplicar, e conta
    como reapresentação quando foi feita num turno anterior. Exige `ctx.atendimento`.
    """
    atendimento = ctx.atendimento
    leva = leva_atual(ctx)
    pilha = abertas(atendimento)
    proxima_ordem = max((p.ordem for p in atendimento.perguntas_pendentes), default=0) + 1

    existente = next((p for p in pilha if p.chave == chave), None)
    if existente is not None:
        if existente.leva_ultima != leva:
            existente.reapresentacoes += 1
        existente.ordem = proxima_ordem
        existente.leva_ultima = leva
        existente.texto = texto
        if dados is not None:
            existente.dados = dados
        if ctx.dlog:
            ctx.dlog.log("pilha", f"reapresenta {chave} (reapresentações={existente.reapresentacoes})")
        return existente

    defn = definicao(chave)
    pergunta = PerguntaPendente(
        chave=chave,
        tratador=defn.tratador.nome if defn else "nenhum",
        texto=texto,
        status=StatusPergunta.ABERTA.value,
        ordem=proxima_ordem,
        leva_criacao=leva,
        leva_ultima=leva,
        mensagens_ids=[],
        tentativas_captura=0,
        reapresentacoes=0,
        dados=dados,
    )
    atendimento.perguntas_pendentes.append(pergunta)
    if ctx.dlog:
        ctx.dlog.log("pilha", f"empilha {chave} (abertas={len(pilha) + 1})")

    excedentes = len(pilha) + 1 - TETO_PILHA
    for antiga in pilha[: max(excedentes, 0)]:
        encerrar(antiga, StatusPergunta.DESCARTADA, ctx=ctx)
        if ctx.dlog:
            ctx.dlog.log("pilha", f"teto de {TETO_PILHA} → descarta {antiga.chave}")
    # A sessão não faz autoflush: sem isto, quem recarregasse a coleção antes do commit
    # final de `processar()` perderia a pergunta recém-feita (mesmo motivo do `flush()`
    # em `_salvar_info_atendimento`).
    ctx.db.flush()
    return pergunta


def descartar_todas(atendimento: Atendimento) -> None:
    """Fecha a pilha (atendimento encerrado ou qualificação reiniciada). Sem `ao_sair`:
    o atendimento que as perguntas serviam acabou."""
    for pergunta in abertas(atendimento):
        encerrar(pergunta, StatusPergunta.DESCARTADA)


def sincronizar(ctx: ContextoAcao) -> None:
    """Tira da pilha os campos do catálogo que já foram respondidos por outro caminho: um
    extrator por palavra-gatilho capturou a resposta ("somos 80 funcionários") ou o
    modelo foi resolvido. Deixar de se aplicar não tira: a pergunta foi feita e vale até
    ser respondida (ver `proxima_pergunta`)."""
    atendimento = ctx.atendimento
    valores = atendimento.valores_capturados()
    for pergunta in abertas(atendimento):
        campo = CAMPOS.get(pergunta.chave)
        if campo is None or not nao_perguntar_de_novo(campo, atendimento):
            continue
        valor = valores.get(pergunta.chave)
        encerrar(pergunta, StatusPergunta.RESPONDIDA if valor else StatusPergunta.DESCARTADA, valor)
        if ctx.dlog:
            ctx.dlog.log("pilha", f"{pergunta.chave} não está mais pendente → sai da pilha")


def vincular_mensagens(db: Session, atendimento_id: Optional[int], leva: int, mensagens: list[Mensagem]) -> None:
    """Liga as perguntas feitas neste turno às mensagens de saída que as levaram.

    Só existe depois de as mensagens serem gravadas, no fim de `processar()`. É o que
    permite ao reply-to do cliente apontar para uma pergunta. Pergunta que não aparece
    em nenhuma mensagem (o LLM reescreveu o texto) fica sem vínculo e é tratada sem o
    atalho do reply-to.
    """
    if atendimento_id is None or not mensagens:
        return
    perguntas = (
        db.query(PerguntaPendente)
        .filter(
            PerguntaPendente.atendimento_id == atendimento_id,
            PerguntaPendente.leva_ultima == leva,
            PerguntaPendente.status == StatusPergunta.ABERTA.value,
        )
        .all()
    )
    for pergunta in perguntas:
        defn = definicao(pergunta.chave)
        trecho = (defn.trecho_vinculo(pergunta) if defn and defn.trecho_vinculo else None) or pergunta.texto
        mensagem = next((m for m in mensagens if trecho and trecho in (m.conteudo or "")), None)
        if mensagem is not None and mensagem.id not in (pergunta.mensagens_ids or []):
            # Lista nova, e não `append`: JSONB não detecta mutação in-place.
            pergunta.mensagens_ids = [*(pergunta.mensagens_ids or []), mensagem.id]


# ----------------------------------------------------------------------
# Resolução da resposta
# ----------------------------------------------------------------------


@dataclass
class Captura:
    pergunta: PerguntaPendente
    leitura: Leitura


def _entrada(ctx: ContextoAcao, pergunta: PerguntaPendente):
    return entrada_de(ctx.conteudo, ctx.resultado_class.intencoes, ctx.resultado_class.entidades, pergunta.dados)


def _ler(ctx: ContextoAcao, pergunta: PerguntaPendente) -> Optional[Leitura]:
    defn = definicao(pergunta.chave)
    if defn is None:
        return None
    return defn.tratador.interpretar(_entrada(ctx, pergunta))


def _discriminante(pergunta: PerguntaPendente) -> bool:
    defn = definicao(pergunta.chave)
    return bool(defn and defn.tratador.discriminante)


def _candidatas(
    ctx: ContextoAcao, pilha: list[PerguntaPendente], usar_reply_to: bool = True
) -> tuple[list[PerguntaPendente], str]:
    citada = ctx.resposta_a_mensagem_id if usar_reply_to else None
    if citada is not None:
        citadas = [p for p in pilha if citada in (p.mensagens_ids or [])]
        if citadas:
            return citadas, "reply-to"
    fila = [p for p in pilha if p.posicao_serial is not None]
    if fila:
        return [min(fila, key=lambda p: p.posicao_serial)], "fila serial"
    leva_topo = max(p.leva_ultima for p in pilha)
    return [p for p in pilha if _discriminante(p) or p.leva_ultima == leva_topo], "topo"


def _leitura_discriminante(captura: Captura) -> bool:
    if captura.leitura.discriminante is not None:
        return captura.leitura.discriminante
    return _discriminante(captura.pergunta)


def _ler_candidatas(
    ctx: ContextoAcao, pilha: list[PerguntaPendente], usar_reply_to: bool = True
) -> tuple[list[PerguntaPendente], str, list[tuple[PerguntaPendente, Leitura]]]:
    """Lê a mensagem contra as candidatas. Fora delas (abaixo do topo, ou fora da vez na
    fila serial), só conta uma leitura que se identifica sozinha ("conheço o Topdata"
    para "Você conhece?")."""
    candidatas, criterio = _candidatas(ctx, pilha, usar_reply_to)
    leituras = [(p, leitura) for p in candidatas if (leitura := _ler(ctx, p)) is not None]
    if criterio in ("topo", "fila serial"):
        for pergunta in pilha:
            if pergunta in candidatas:
                continue
            leitura = _ler(ctx, pergunta)
            if leitura is not None and leitura.reconheceu and leitura.discriminante:
                leituras.append((pergunta, leitura))
    return candidatas, criterio, leituras


def _desempatar(reconhecidas: list[Captura]) -> list[Captura]:
    """Desempate 2: quem se identifica sozinho ganha de quem é ambíguo; entre os que
    sobram, a leva mais recente."""
    discriminantes = [c for c in reconhecidas if _leitura_discriminante(c)]
    if discriminantes:
        reconhecidas = discriminantes
    if len(reconhecidas) > 1:
        leva_recente = max(c.pergunta.leva_ultima for c in reconhecidas)
        reconhecidas = [c for c in reconhecidas if c.pergunta.leva_ultima == leva_recente]
    return reconhecidas


def _trecho_disputado(ctx: ContextoAcao, captura: Captura, candidatas: list[PerguntaPendente]) -> bool:
    """O pedaço que a leitura parcial consumiu ("sim") também serviria de resposta a
    outra pergunta aberta? Então ele não é dela por direito: a leitura volta a disputar
    como resposta inteira, e a ambiguidade vai para a fila serial."""
    trecho = captura.leitura.trecho
    if not trecho:
        return False
    for pergunta in candidatas:
        defn = definicao(pergunta.chave)
        if pergunta is captura.pergunta or defn is None:
            continue
        entrada = entrada_de(trecho, (), dados=pergunta.dados)
        if defn.tratador.interpretar(entrada).reconheceu:
            return True
    return False


def _registrar_tentativas_falhas(ctx: ContextoAcao, leituras: list[tuple[PerguntaPendente, Leitura]]) -> None:
    """Escada de erro (D3). Só conta como tentativa falha a mensagem que podia ser a
    resposta (inválida, ou sem outro assunto) e não foi lida: um cliente que pergunta
    outra coisa não é tratado como quem não sabe responder."""
    for pergunta, leitura in leituras:
        defn = definicao(pergunta.chave)
        tentou = leitura.status == StatusLeitura.INVALIDO or defn.tratador.conta_tentativa(_entrada(ctx, pergunta))
        if not tentou:
            continue
        pergunta.tentativas_captura += 1
        if ctx.dlog:
            ctx.dlog.log(
                "pilha", f"{pergunta.chave}: tentativa falha {pergunta.tentativas_captura} ({leitura.status.value})"
            )
        if defn.max_tentativas is not None and pergunta.tentativas_captura >= defn.max_tentativas:
            if ctx.dlog:
                ctx.dlog.log("pilha", f"{pergunta.chave}: tentativas esgotadas → sai da pilha")
            encerrar(pergunta, StatusPergunta.ESGOTADA, ctx=ctx)


def capturar(ctx: ContextoAcao, captura: Captura) -> None:
    """Grava a resposta no destino declarado e tira a pergunta da pilha."""
    pergunta, leitura = captura.pergunta, captura.leitura
    defn = definicao(pergunta.chave)
    if defn is None:
        return
    if defn.aplicar is not None:
        defn.aplicar(ctx, pergunta, leitura)
    elif defn.grava:
        ctx.processador._salvar_info_atendimento(ctx.db, ctx.atendimento.id, pergunta.chave, leitura.valor)
    if not defn.fecha_na_captura:
        return
    valor = None if leitura.valor is None else str(leitura.valor)
    encerrar(pergunta, StatusPergunta.RESPONDIDA, valor)
    if ctx.dlog:
        ctx.dlog.log("pilha", f"{pergunta.chave} capturado: {valor!r}")


async def _reapresentar(
    ctx: ContextoAcao, pergunta: PerguntaPendente, antes: Optional[ParteResposta] = None
) -> RespostaGerada:
    """Pergunta de novo (move para o topo) precedida de `antes`, cada uma sua parte."""
    empilhar(ctx, pergunta.chave, pergunta.texto, pergunta.dados)
    partes = [antes] if antes else []
    partes.append((MensagemId.PILHA_PERGUNTA, {"pergunta": pergunta.texto.strip()}))
    return await ctx.processador._gerador.gerar_composta(partes)


async def _seguir_fila_serial(ctx: ContextoAcao, captura: Captura) -> Optional[RespostaGerada]:
    """Depois de capturar uma resposta da fila serial: confirma e retoma a próxima."""
    fila = fila_serial(ctx.atendimento)
    # Quem acabou de ser respondida pode ter reaberto a própria pergunta de outro jeito
    # (o nome de perfil recusado vira "Como posso te chamar?"): ela é a próxima da fila.
    reaberta = next(
        (p for p in abertas(ctx.atendimento) if p.chave == captura.pergunta.chave and p.posicao_serial is None),
        None,
    )
    if reaberta is not None:
        reaberta.posicao_serial = 0
        return await _reapresentar(ctx, reaberta)
    if not fila:
        if ctx.dlog:
            ctx.dlog.log("pilha", "fila serial esvaziada → fluxo normal")
        return None
    defn = definicao(captura.pergunta.chave)
    confirmacao = defn.confirmacao(ctx, captura.pergunta) if defn and defn.confirmacao else None
    if ctx.dlog:
        ctx.dlog.log("pilha", f"fila serial: próxima {fila[0].chave}")
    return await _reapresentar(ctx, fila[0], confirmacao or (MensagemId.PILHA_ANOTADO, None))


async def resolver_resposta(ctx: ContextoAcao) -> Optional[RespostaGerada]:
    """Roda antes do motor. Captura a resposta a uma pergunta da pilha, se houver.

    Devolve uma resposta pronta só quando a pilha é dona do turno: resposta ambígua
    (abre a fila serial) ou fila serial em andamento com mais perguntas para retomar.
    Nos demais casos devolve `None` e o motor responde, já enxergando o valor capturado
    (e, para quem não grava, a resposta identificada em `ctx.captura_pilha`).
    """
    if ctx.atendimento is None:
        return None
    resposta = await _resolver(ctx)
    # Contadores e status mudados aqui precisam ir ao banco já: a sessão não faz
    # autoflush, e um `refresh` do atendimento (o cascade inclui as perguntas) os
    # descartaria.
    ctx.db.flush()
    return resposta


async def _resolver(ctx: ContextoAcao) -> Optional[RespostaGerada]:
    sincronizar(ctx)
    pilha = abertas(ctx.atendimento)
    if not pilha:
        return None
    serial_antes = bool(fila_serial(ctx.atendimento))
    candidatas, criterio, leituras = _ler_candidatas(ctx, pilha)
    if criterio == "reply-to" and not any(leitura.reconheceu for _, leitura in leituras):
        # A pergunta citada não aceita a mensagem: o cliente pode ter citado a mensagem
        # errada. Segue a resolução normal, sem o atalho.
        candidatas, criterio, leituras = _ler_candidatas(ctx, pilha, usar_reply_to=False)
    capturas = [Captura(p, leitura) for p, leitura in leituras if leitura.reconheceu]
    parciais = [c for c in capturas if c.leitura.parcial and not _trecho_disputado(ctx, c, candidatas)]
    reconhecidas = _desempatar([c for c in capturas if c not in parciais])
    if ctx.dlog:
        ctx.dlog.log(
            "pilha",
            f"candidatas ({criterio})={[p.chave for p in candidatas]} "
            f"reconheceram={[c.pergunta.chave for c in reconhecidas]}"
            + (f" parciais={[c.pergunta.chave for c in parciais]}" if parciais else ""),
        )
    # Uma leitura parcial ocupa só um pedaço da mensagem: é capturada junto da resposta
    # principal, sem disputar com ela. Sozinha, é a resposta.
    for parcial in parciais:
        capturar(ctx, parcial)
    if parciais and not reconhecidas:
        ctx.captura_pilha = parciais[0]
        return await _seguir_fila_serial(ctx, parciais[0]) if serial_antes else None

    if len(reconhecidas) > 1:
        # Desempate 3: a resposta é descartada, não adivinhada.
        for posicao, pergunta in enumerate(pilha, start=1):
            pergunta.posicao_serial = posicao
        primeira = fila_serial(ctx.atendimento)[0]
        if ctx.dlog:
            ctx.dlog.log(
                "pilha",
                f"ambígua entre {[c.pergunta.chave for c in reconhecidas]} "
                f"→ fila serial começando por {primeira.chave}",
            )
        empilhar(ctx, primeira.chave, primeira.texto, primeira.dados)
        return await ctx.processador._gerador.gerar(MensagemId.PILHA_CONFUSO, {"pergunta": primeira.texto.strip()})

    if not reconhecidas:
        _registrar_tentativas_falhas(ctx, leituras)
        return None

    captura = reconhecidas[0]
    ctx.captura_pilha = captura
    capturar(ctx, captura)
    if serial_antes:
        return await _seguir_fila_serial(ctx, captura)
    return None
