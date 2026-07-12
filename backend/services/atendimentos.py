"""
Serviço de ciclo de vida de atendimentos (REQ-016).

Centraliza criação, numeração sequencial por contato e promoção PJ/PF.
"""

from __future__ import annotations

import logging
from typing import Optional

from models import Atendimento, Contato, Empresa, FaseAtendimento, Pessoa, StatusAtendimento, TipoDocumento
from sqlalchemy import func, text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def atendimento_ativo(db: Session, contato: Contato) -> Optional[Atendimento]:
    """Retorna o atendimento ativo mais recente do contato (se houver)."""
    return (
        db.query(Atendimento)
        .filter(Atendimento.contato_id == contato.id)
        .filter(Atendimento.status == StatusAtendimento.ATIVO)
        .order_by(Atendimento.created_at.desc())
        .first()
    )


def _lock_contato_para_numeracao(db: Session, contato_id: int) -> None:
    """Serializa numeração por contato (webhooks concorrentes)."""
    db.execute(text("SELECT pg_advisory_xact_lock(:chave)"), {"chave": contato_id})
    (
        db.query(Atendimento)
        .filter(Atendimento.contato_id == contato_id)
        .with_for_update()
        .all()
    )


def proximo_numero_atendimento_cliente(db: Session, contato_id: int) -> int:
    """
    Próximo número sequencial por contato (REQ-016.3).

    Inteiro positivo; primeiro atendimento do contato → 1.
    """
    _lock_contato_para_numeracao(db, contato_id)
    atual = (
        db.query(func.coalesce(func.max(Atendimento.numero_atendimento_cliente), 0))
        .filter(Atendimento.contato_id == contato_id)
        .scalar()
    )
    return int(atual) + 1


def _titulo_novo_atendimento(
    *,
    empresa: Optional[Empresa] = None,
    pessoa: Optional[Pessoa] = None,
    pf_pendente: bool = False,
) -> str:
    if pf_pendente:
        return "Atendimento - Pessoa Física (pendente)"
    if empresa:
        return f"Atendimento - {empresa.nome}"
    if pessoa:
        return f"Atendimento - {pessoa.nome or 'Pessoa Física'}"
    return "Atendimento (sem empresa)"


def promover_atendimento_empresa(
    db: Session,
    atendimento: Atendimento,
    empresa: Empresa,
) -> Atendimento:
    """Vincula empresa (PJ) a um atendimento existente."""
    if atendimento.empresa_id is None:
        atendimento.empresa_id = empresa.id
        if not atendimento.titulo or atendimento.titulo == "Atendimento (sem empresa)":
            atendimento.titulo = f"Atendimento - {empresa.nome}"
        db.commit()
        db.refresh(atendimento)
        logger.info(
            "[Atendimentos] Atendimento id=%s promovido para empresa id=%s",
            atendimento.id,
            empresa.id,
        )
    return atendimento


def promover_atendimento_pessoa(
    db: Session,
    atendimento: Atendimento,
    pessoa: Pessoa,
) -> Atendimento:
    """Vincula pessoa (PF) a um atendimento existente."""
    if atendimento.pessoa_id is None:
        atendimento.pessoa_id = pessoa.id
        atendimento.tipo_documento = TipoDocumento.CPF
        if not atendimento.titulo or atendimento.titulo.startswith("Atendimento (sem"):
            atendimento.titulo = f"Atendimento - {pessoa.nome or 'Pessoa Física'}"
        db.commit()
        db.refresh(atendimento)
        logger.info(
            "[Atendimentos] Atendimento id=%s promovido para pessoa id=%s",
            atendimento.id,
            pessoa.id,
        )
    return atendimento


def obter_ou_criar_atendimento(
    db: Session,
    contato: Contato,
    empresa: Optional[Empresa] = None,
    pessoa: Optional[Pessoa] = None,
) -> Atendimento:
    """
    Retorna atendimento ativo ou cria um novo com numeração sequencial.

    `empresa` ou `pessoa` identificam PJ ou PF respectivamente.
    """
    atendimento = atendimento_ativo(db, contato)
    if atendimento:
        if empresa is not None and atendimento.empresa_id is None:
            promover_atendimento_empresa(db, atendimento, empresa)
        if pessoa is not None and atendimento.pessoa_id is None:
            promover_atendimento_pessoa(db, atendimento, pessoa)
        return atendimento

    numero = proximo_numero_atendimento_cliente(db, contato.id)
    tipo_doc = TipoDocumento.CNPJ if empresa else TipoDocumento.CPF if pessoa else TipoDocumento.INDEFINIDO
    atendimento = Atendimento(
        contato_id=contato.id,
        empresa_id=empresa.id if empresa else None,
        pessoa_id=pessoa.id if pessoa else None,
        tipo_documento=tipo_doc,
        status=StatusAtendimento.ATIVO,
        fase=FaseAtendimento.ESCLARECENDO,
        titulo=_titulo_novo_atendimento(empresa=empresa, pessoa=pessoa),
        numero_atendimento_cliente=numero,
    )
    db.add(atendimento)
    db.commit()
    db.refresh(atendimento)
    logger.info(
        "[Atendimentos] Criado id=%s numero=%s contato_id=%s empresa_id=%s pessoa_id=%s",
        atendimento.id,
        atendimento.numero_atendimento_cliente,
        atendimento.contato_id,
        atendimento.empresa_id,
        atendimento.pessoa_id,
    )
    return atendimento


def obter_ou_criar_atendimento_pf_pendente(
    db: Session,
    contato: Contato,
    cpf_mascarado: str = "",
) -> Atendimento:
    """Cria ou retorna atendimento PF aguardando data de nascimento."""
    atendimento = atendimento_ativo(db, contato)
    if atendimento:
        atendimento.tipo_documento = TipoDocumento.CPF
        db.commit()
        db.refresh(atendimento)
        return atendimento

    numero = proximo_numero_atendimento_cliente(db, contato.id)
    atendimento = Atendimento(
        contato_id=contato.id,
        tipo_documento=TipoDocumento.CPF,
        status=StatusAtendimento.ATIVO,
        fase=FaseAtendimento.ESCLARECENDO,
        titulo=_titulo_novo_atendimento(pf_pendente=True),
        numero_atendimento_cliente=numero,
    )
    db.add(atendimento)
    db.commit()
    db.refresh(atendimento)
    logger.info(
        "[Atendimentos] PF pendente criado id=%s numero=%s cpf=%s",
        atendimento.id,
        atendimento.numero_atendimento_cliente,
        cpf_mascarado,
    )
    return atendimento
