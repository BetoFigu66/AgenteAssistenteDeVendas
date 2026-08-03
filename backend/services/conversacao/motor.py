"""
Gerenciador do motor de roteamento Intenção×Fase→Ações.

`RegraIntencao` é o item de registro: liga uma Intenção (ou `None` = wildcard, roda
sempre — a "ação padrão" de uma Fase) e uma Fase (ou `None` = regra global, avaliada
independente da fase efetiva do atendimento) a um builder de `GrupoAcoes`.

`resolver_e_executar` é o "gerenciador": coleta as Regras cujo (intenção, fase) casam com
o que bateu nesta mensagem, mescla as 4 listas de todas elas, e executa — `exclusivo` tem
prioridade absoluta (se não vazio, só ele roda); senão roda `pre + processamento + pos`,
nessa ordem.

Ver `docs/arquitetura_motor_conversacao_2026-07.md` para o diagrama de fluxo completo e o
racional de cada peça (RegraIntencao, ContextoAcao, TipoExecucao).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from models import FaseAtendimento

from services.classificador import Intencao
from services.respostas import RespostaGerada

from .acoes import ContextoAcao, GrupoAcoes


@dataclass(frozen=True)
class RegraIntencao:
    """Um item do registro.

    `intencao=None` — wildcard, casa sempre (usado pela "ação padrão" de uma Fase).
    `fase=None` — regra global, avaliada em qualquer Fase efetiva (checada antes das
    regras específicas da fase, na mesma ordem em que foi registrada).
    """

    intencao: Optional[Intencao]
    fase: Optional[FaseAtendimento]
    builder: Callable[[ContextoAcao], GrupoAcoes]
    nome: str


def _fase_efetiva(ctx: ContextoAcao) -> FaseAtendimento:
    """Sem Atendimento ainda (NOVO/SEM_EMPRESA pré-atendimento) == Esclarecendo — mesmo
    default de `Atendimento.fase` no model."""
    return ctx.atendimento.fase if ctx.atendimento else FaseAtendimento.ESCLARECENDO


def _casa(regra: RegraIntencao, intencoes_batidas: list[Intencao]) -> bool:
    return regra.intencao is None or regra.intencao in intencoes_batidas


async def resolver_e_executar(
    ctx: ContextoAcao,
    regras_globais: list[RegraIntencao],
    registro_por_fase: dict[FaseAtendimento, list[RegraIntencao]],
) -> Optional[RespostaGerada]:
    """Executa o motor para uma mensagem já classificada. Retorna `None` se nenhuma Ação
    produziu fragmento (o chamador deve cair no fallback final, ex.: QA/NAO_ENTENDI)."""
    fase_efetiva = _fase_efetiva(ctx)
    intencoes = ctx.resultado_class.intencoes

    # Ordem importa: globais primeiro, depois específicas da fase — dentro de cada lista,
    # regras específicas devem ser registradas ANTES do wildcard da fase, para que a
    # "ação padrão" seja sempre a última do `pos` final (ela decide agir ou não olhando
    # pra `ctx.fragmentos_ate_agora`, que só reflete o que rodou antes dela).
    candidatas = [r for r in regras_globais if _casa(r, intencoes)]
    candidatas += [r for r in registro_por_fase.get(fase_efetiva, []) if _casa(r, intencoes)]

    grupo_final = GrupoAcoes()
    for regra in candidatas:
        grupo_final += regra.builder(ctx)

    acoes = grupo_final.exclusivo or (grupo_final.pre + grupo_final.processamento + grupo_final.pos)

    if ctx.dlog:
        ctx.dlog.log(
            "motor",
            f"intencoes={[i.value for i in intencoes]} fase={fase_efetiva.value} "
            f"regras={[r.nome for r in candidatas]} acoes={[a.nome for a in acoes]}"
            f"{' (exclusivo)' if grupo_final.exclusivo else ''}",
        )

    for acao in acoes:
        resultado = await acao.executar(ctx)
        if resultado is None:
            continue
        if isinstance(resultado, tuple):
            mensagem_id, contexto = resultado
            resultado = await ctx.processador._gerador.gerar(mensagem_id, contexto)
        ctx.fragmentos_ate_agora.append(resultado)

    return _compor_fragmentos(ctx.fragmentos_ate_agora)


def _compor_fragmentos(fragmentos: list[RespostaGerada]) -> Optional[RespostaGerada]:
    if not fragmentos:
        return None
    if len(fragmentos) == 1:
        return fragmentos[0]
    return RespostaGerada(
        texto="\n\n".join(f.texto for f in fragmentos if f.texto),
        template_usado="+".join(f.template_usado for f in fragmentos if f.template_usado) or None,
        personalizado_via_llm=any(f.personalizado_via_llm for f in fragmentos),
        llm_tokens_input=sum(f.llm_tokens_input or 0 for f in fragmentos) or None,
        llm_tokens_output=sum(f.llm_tokens_output or 0 for f in fragmentos) or None,
        rag_utilizada=any(f.rag_utilizada for f in fragmentos),
        trechos_rag=[t for f in fragmentos for t in (f.trechos_rag or [])],
        rag_score_maximo=max(
            (f.rag_score_maximo for f in fragmentos if f.rag_score_maximo is not None), default=None
        ),
    )
