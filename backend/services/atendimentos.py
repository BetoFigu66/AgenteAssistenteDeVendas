"""
Serviço de ciclo de vida de atendimentos (REQ-016).

Centraliza criação, numeração sequencial por contato e promoção PJ/PF.
"""

from __future__ import annotations

import logging
from typing import Optional

from models import (
    Atendimento,
    Contato,
    Empresa,
    FaseAtendimento,
    MotivoEncerramento,
    Pessoa,
    StatusAtendimento,
    TipoDocumento,
)
from sqlalchemy import func, text
from sqlalchemy.orm import Session
from utils.datetime_utils import utc_now

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


def atendimento_mais_recente(db: Session, contato: Contato) -> Optional[Atendimento]:
    """Atendimento mais recente do contato, independente de status (REQ-016.7).

    Usado para decidir a matriz de continuação: `atendimento_ativo` sozinho não basta
    porque um atendimento `encerrado` recente ainda pode disparar a pergunta de
    continuação (REQ-016.9) em vez de criar um atendimento novo silenciosamente.
    """
    return (
        db.query(Atendimento)
        .filter(Atendimento.contato_id == contato.id)
        .order_by(Atendimento.created_at.desc())
        .first()
    )


def encerrar_atendimento(
    db: Session,
    atendimento: Atendimento,
    *,
    motivo: MotivoEncerramento,
    ator: str,
) -> Atendimento:
    """Transição `ativo` → `encerrado` (REQ-016.4/016.5).

    `ator` identifica quem/o que decidiu (ex.: "cliente", "vendedor:Rita",
    "sistema:abandono") — auditoria simplificada até a tabela de eventos da Fase 5
    (REQ-005) existir, conforme decisão registrada no plano de implementação.
    """
    if atendimento.status == StatusAtendimento.ENCERRADO:
        raise ValueError(f"Atendimento {atendimento.id} já está encerrado")
    atendimento.status = StatusAtendimento.ENCERRADO
    atendimento.motivo_encerramento = motivo.value
    atendimento.encerrado_em = utc_now()
    atendimento.encerrado_por = ator
    db.commit()
    db.refresh(atendimento)
    logger.info(
        "[Atendimentos] Atendimento id=%s encerrado motivo=%s ator=%s",
        atendimento.id,
        motivo.value,
        ator,
    )
    return atendimento


def reabrir_atendimento(
    db: Session,
    atendimento: Atendimento,
    *,
    ator: str,
    justificativa: Optional[str] = None,
) -> Atendimento:
    """Transição `encerrado` → `ativo` (REQ-016.8).

    Bloqueada quando `motivo_encerramento = concluido_conversao`: a compra já foi
    concluída, não admite reabertura (REQ-016.7/016.8) — qualquer novo contato deve
    virar atendimento novo.
    """
    if atendimento.status == StatusAtendimento.ATIVO:
        raise ValueError(f"Atendimento {atendimento.id} já está ativo")
    if atendimento.motivo_encerramento == MotivoEncerramento.CONCLUIDO_CONVERSAO.value:
        raise ValueError(
            f"Atendimento {atendimento.id} concluído por conversão de orçamento não pode ser reaberto"
        )
    atendimento.status = StatusAtendimento.ATIVO
    atendimento.motivo_encerramento = None
    atendimento.reaberto_em = utc_now()
    atendimento.reaberto_por = ator
    atendimento.reabertura_justificativa = justificativa
    db.commit()
    db.refresh(atendimento)
    logger.info(
        "[Atendimentos] Atendimento id=%s reaberto ator=%s",
        atendimento.id,
        ator,
    )
    return atendimento


def encerrar_por_conversao(db: Session, atendimento_id: int) -> Atendimento:
    """REQ-016.12: encerramento automático quando um orçamento é marcado `convertido`.

    Isolado numa função própria — sem acoplar este módulo ao schema de `Orcamento` —
    para a Fase 14 (REQ-006) apenas chamar diretamente quando o CRUD de orçamento
    existir (contorno explícito registrado no plano de implementação da Fase 1).
    """
    atendimento = db.query(Atendimento).filter_by(id=atendimento_id).first()
    if atendimento is None:
        raise ValueError(f"Atendimento {atendimento_id} não encontrado")
    return encerrar_atendimento(
        db, atendimento, motivo=MotivoEncerramento.CONCLUIDO_CONVERSAO, ator="sistema:orcamento_convertido"
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
