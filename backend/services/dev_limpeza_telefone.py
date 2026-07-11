"""
Limpeza de dados de teste por telefone (ferramenta de desenvolvimento).

Remove em cascata (ordem de FKs):
  reports → mensagens → processamentos → orçamentos/itens → atendimentos → contato

Não remove empresa, pessoa nem catálogo de produtos.
"""

from __future__ import annotations

from typing import Any

from models import (
    Atendimento,
    AtendimentoInfo,
    Contato,
    ItemAtendimento,
    ItemOrcamento,
    Mensagem,
    Orcamento,
    ProcessamentoMensagem,
    ReportProblema,
)
from services.identificador import normalizar_telefone
from sqlalchemy import or_
from sqlalchemy.orm import Session


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

    return {
        "telefone": telefone,
        "telefone_normalizado": normalizar_telefone(telefone),
        "contato_ids": contato_ids,
        "atendimento_ids": atendimento_ids,
        "removidos": removidos,
    }
