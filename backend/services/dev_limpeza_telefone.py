"""
Limpeza de dados de teste por telefone (ferramenta de desenvolvimento).

Remove em cascata (ordem de FKs):
  reports → escalonamentos → eventos_atendimento → mensagens → processamentos → orçamentos/itens →
  itens/infos de atendimento → atendimentos → contato →
  (atividades_empresa, socios_empresa, empresa) quando a empresa ficou órfã

A empresa criada pela consulta de CNPJ é removida de forma CONDICIONAL (achado B4,
auditoria 2026-08): só quando, depois da limpeza, nenhum outro contato, atendimento ou
processamento ainda apontar para ela. Ver `_remover_empresas_orfas`.

Não remove pessoa (PF) nem catálogo de produtos.
"""

from __future__ import annotations

from typing import Any

from models import (
    Atendimento,
    AtendimentoInfo,
    AtividadeEmpresa,
    Contato,
    Empresa,
    Escalonamento,
    EventoAtendimento,
    ItemAtendimento,
    ItemOrcamento,
    Mensagem,
    Orcamento,
    ProcessamentoMensagem,
    ReportProblema,
    SocioEmpresa,
)
from sqlalchemy import or_
from sqlalchemy.orm import Session

from services.identificador import normalizar_telefone


def _coletar_contatos(db: Session, telefone: str) -> list[Contato]:
    """Busca contatos pelo telefone (mesma lógica do identificador)."""
    tel_norm = normalizar_telefone(telefone)
    variantes = {tel_norm, telefone.strip()}
    contatos = db.query(Contato).filter(Contato.telefone.in_(list(variantes))).all()

    if not contatos and len(tel_norm) >= 9:
        sufixo = tel_norm[-9:]
        contatos = db.query(Contato).filter(Contato.telefone.like(f"%{sufixo}")).all()

    return contatos


def _coletar_variantes_telefone(contatos: list[Contato], telefone: str) -> set[str]:
    tel_norm = normalizar_telefone(telefone)
    variantes = {tel_norm, telefone.strip()}
    variantes.update(c.telefone for c in contatos)
    return variantes


def _coletar_empresas_candidatas(
    db: Session,
    contato_ids: list[int],
    atendimento_ids: list[int],
    processamento_ids: set[int],
) -> set[int]:
    """Empresas que ESTE telefone tocou, coletadas antes dos deletes.

    Só candidatas: quem decide a remoção é `_remover_empresas_orfas`, depois que as
    linhas do telefone já sairam. Inclui os processamentos porque a consulta de CNPJ
    pode gravar `empresa_id_identificada` num turno que não chegou a vincular a empresa
    ao atendimento.
    """
    candidatas: set[int] = set()

    if contato_ids:
        candidatas.update(
            row[0]
            for row in db.query(Contato.empresa_id)
            .filter(Contato.id.in_(contato_ids), Contato.empresa_id.isnot(None))
            .all()
        )
    if atendimento_ids:
        candidatas.update(
            row[0]
            for row in db.query(Atendimento.empresa_id)
            .filter(Atendimento.id.in_(atendimento_ids), Atendimento.empresa_id.isnot(None))
            .all()
        )
    if processamento_ids:
        candidatas.update(
            row[0]
            for row in db.query(ProcessamentoMensagem.empresa_id_identificada)
            .filter(
                ProcessamentoMensagem.id.in_(list(processamento_ids)),
                ProcessamentoMensagem.empresa_id_identificada.isnot(None),
            )
            .all()
        )

    return candidatas


def _remover_empresas_orfas(
    db: Session,
    empresa_ids: set[int],
    removidos: dict[str, int],
) -> tuple[list[int], list[int]]:
    """Remove as empresas que ficaram sem nenhum referenciador (achado B4).

    Por que condicional e não incondicional: uma `Empresa` não é simétrica a um
    `Contato`. O mesmo CNPJ pode estar ligado a contatos, atendimentos e processamentos
    de OUTROS telefones (dois funcionários da mesma empresa escrevendo de celulares
    diferentes é o caso comum). Apagar a empresa junto com um telefone destruiria dado de
    outra conversa, e este utilitário roda contra o mesmo banco da suíte e do painel.
    Então cada candidata só sai quando nada mais aponta para ela.

    Chamar SÓ depois dos deletes de contatos/atendimentos/processamentos: as contagens
    abaixo precisam enxergar o banco já limpo (os bulk deletes valem dentro da transação
    corrente, mesmo antes do commit).

    Ordem obrigatória: `atividades_empresa` e `socios_empresa` têm FK not-null para
    `empresas`, então saem antes da empresa.

    Returns:
        (ids removidos, ids preservados por ainda terem referências).
    """
    removidos.setdefault("atividades_empresa", 0)
    removidos.setdefault("socios_empresa", 0)
    removidos.setdefault("empresas", 0)

    orfas: list[int] = []
    preservadas: list[int] = []

    for empresa_id in sorted(empresa_ids):
        # `first()` e não `count()`: basta saber se sobrou alguma referência.
        ainda_referenciada = (
            db.query(Contato.id).filter(Contato.empresa_id == empresa_id).first() is not None
            or db.query(Atendimento.id).filter(Atendimento.empresa_id == empresa_id).first() is not None
            or db.query(ProcessamentoMensagem.id)
            .filter(ProcessamentoMensagem.empresa_id_identificada == empresa_id)
            .first()
            is not None
        )
        if ainda_referenciada:
            preservadas.append(empresa_id)
        else:
            orfas.append(empresa_id)

    if orfas:
        removidos["atividades_empresa"] = (
            db.query(AtividadeEmpresa)
            .filter(AtividadeEmpresa.empresa_id.in_(orfas))
            .delete(synchronize_session=False)
        )
        removidos["socios_empresa"] = (
            db.query(SocioEmpresa)
            .filter(SocioEmpresa.empresa_id.in_(orfas))
            .delete(synchronize_session=False)
        )
        removidos["empresas"] = (
            db.query(Empresa).filter(Empresa.id.in_(orfas)).delete(synchronize_session=False)
        )

    return orfas, preservadas


def apagar_dados_telefone(db: Session, telefone: str) -> dict[str, Any]:
    """
    Apaga todos os registros vinculados ao telefone informado.

    Returns:
        Dict com telefone normalizado, ids afetados e contagem por entidade.
    """
    contatos = _coletar_contatos(db, telefone)
    contato_ids = [c.id for c in contatos]
    variantes_tel = _coletar_variantes_telefone(contatos, telefone)

    atendimento_ids = [
        row[0]
        for row in db.query(Atendimento.id)
        .filter(Atendimento.contato_id.in_(contato_ids))
        .all()
    ] if contato_ids else []

    filtros_mensagem = [Mensagem.telefone.in_(list(variantes_tel))]
    if contato_ids:
        filtros_mensagem.append(Mensagem.contato_id.in_(contato_ids))
    if atendimento_ids:
        filtros_mensagem.append(Mensagem.atendimento_id.in_(atendimento_ids))

    mensagens = db.query(Mensagem).filter(or_(*filtros_mensagem)).all()
    mensagem_ids = [m.id for m in mensagens]

    processamento_ids: set[int] = {m.processamento_id for m in mensagens if m.processamento_id}
    if contato_ids or atendimento_ids:
        filtros_proc = []
        if contato_ids:
            filtros_proc.append(ProcessamentoMensagem.contato_id_identificado.in_(contato_ids))
        if atendimento_ids:
            filtros_proc.append(ProcessamentoMensagem.atendimento_id_ativa.in_(atendimento_ids))
        extras = (
            db.query(ProcessamentoMensagem.id)
            .filter(or_(*filtros_proc))
            .all()
        )
        processamento_ids.update(row[0] for row in extras)

    orcamento_ids = [
        row[0]
        for row in db.query(Orcamento.id)
        .filter(Orcamento.atendimento_id.in_(atendimento_ids))
        .all()
    ] if atendimento_ids else []

    # Coletado ANTES dos deletes: depois que contatos/atendimentos/processamentos saem,
    # não há mais como saber que empresa este telefone tocou (achado B4).
    empresas_candidatas = _coletar_empresas_candidatas(
        db, contato_ids, atendimento_ids, processamento_ids
    )

    removidos: dict[str, int] = {}

    if mensagem_ids or processamento_ids:
        filtros_report = []
        if mensagem_ids:
            filtros_report.append(ReportProblema.mensagem_id.in_(mensagem_ids))
        if processamento_ids:
            filtros_report.append(ReportProblema.processamento_id.in_(list(processamento_ids)))
        removidos["reports"] = (
            db.query(ReportProblema).filter(or_(*filtros_report)).delete(synchronize_session=False)
        )
    else:
        removidos["reports"] = 0

    # REQ-005 (Fase 6): eventos_atendimento tem FK not-null pra atendimentos — bulk
    # delete não aciona o cascade do ORM (`Atendimento.eventos`), precisa ser explícito.
    #
    # Tem que vir ANTES de mensagens e processamentos: desde que `mensagem_id` e
    # `processamento_id` passaram a ser preenchidos (achado A2), essas FKs deixaram de ser
    # sempre NULL e passaram a bloquear a remoção das mensagens. Antes disso a ordem não
    # importava, e por isso este delete ficava lá embaixo, junto dos atendimentos.
    # REQ-004.5B: escalonamentos apontam para eventos, mensagens, processamentos e
    # atendimentos, então saem antes de todos eles.
    if atendimento_ids:
        removidos["escalonamentos"] = (
            db.query(Escalonamento)
            .filter(Escalonamento.atendimento_id.in_(atendimento_ids))
            .delete(synchronize_session=False)
        )
    else:
        removidos["escalonamentos"] = 0

    if atendimento_ids:
        removidos["eventos_atendimento"] = (
            db.query(EventoAtendimento)
            .filter(EventoAtendimento.atendimento_id.in_(atendimento_ids))
            .delete(synchronize_session=False)
        )
    else:
        removidos["eventos_atendimento"] = 0

    removidos["mensagens"] = (
        db.query(Mensagem).filter(or_(*filtros_mensagem)).delete(synchronize_session=False)
    )

    if processamento_ids:
        removidos["processamentos"] = (
            db.query(ProcessamentoMensagem)
            .filter(ProcessamentoMensagem.id.in_(list(processamento_ids)))
            .delete(synchronize_session=False)
        )
    else:
        removidos["processamentos"] = 0

    if orcamento_ids:
        removidos["itens_orcamento"] = (
            db.query(ItemOrcamento)
            .filter(ItemOrcamento.orcamento_id.in_(orcamento_ids))
            .delete(synchronize_session=False)
        )
        removidos["orcamentos"] = (
            db.query(Orcamento).filter(Orcamento.id.in_(orcamento_ids)).delete(synchronize_session=False)
        )
    else:
        removidos["itens_orcamento"] = 0
        removidos["orcamentos"] = 0

    if atendimento_ids:
        removidos["itens_atendimento"] = (
            db.query(ItemAtendimento)
            .filter(ItemAtendimento.atendimento_id.in_(atendimento_ids))
            .delete(synchronize_session=False)
        )
        removidos["atendimento_infos"] = (
            db.query(AtendimentoInfo)
            .filter(AtendimentoInfo.atendimento_id.in_(atendimento_ids))
            .delete(synchronize_session=False)
        )
        removidos["atendimentos"] = (
            db.query(Atendimento)
            .filter(Atendimento.id.in_(atendimento_ids))
            .delete(synchronize_session=False)
        )
    else:
        removidos["itens_atendimento"] = 0
        removidos["atendimento_infos"] = 0
        removidos["atendimentos"] = 0

    if contato_ids:
        removidos["contatos"] = (
            db.query(Contato).filter(Contato.id.in_(contato_ids)).delete(synchronize_session=False)
        )
    else:
        removidos["contatos"] = 0

    # Por último: a empresa só pode ser avaliada depois que as linhas deste telefone já
    # sairam, senão ela pareceria sempre referenciada por si mesma (achado B4).
    empresas_removidas, empresas_preservadas = _remover_empresas_orfas(
        db, empresas_candidatas, removidos
    )

    return {
        "telefone": telefone,
        "telefone_normalizado": normalizar_telefone(telefone),
        "contato_ids": contato_ids,
        "atendimento_ids": atendimento_ids,
        "empresa_ids_removidas": empresas_removidas,
        # Compartilhadas com outro contato/atendimento/processamento: ficaram de pé de
        # propósito, e quem chamou precisa saber disso para não achar que o banco ficou
        # virgem para aquele CNPJ.
        "empresa_ids_preservadas": empresas_preservadas,
        "removidos": removidos,
    }
