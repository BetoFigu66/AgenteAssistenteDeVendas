"""
Persistência de dados de CNPJ no banco.
Converte o JSON do ReceitaWS para as entidades Empresa, AtividadeEmpresa, SocioEmpresa.
"""

import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from models import AtividadeEmpresa, Empresa, SocioEmpresa, TipoEmpresa
from sqlalchemy.orm import Session

from .receitaws import consultar_cnpj, formatar_cnpj, normalizar_cnpj

logger = logging.getLogger(__name__)


def _parse_data_br(data_str: Optional[str]):
    """Converte data no formato dd/mm/yyyy para date."""
    if not data_str:
        return None
    try:
        return datetime.strptime(data_str, "%d/%m/%Y").date()
    except ValueError:
        return None


def _parse_decimal(valor: Optional[str]) -> Optional[Decimal]:
    """Converte string numérica para Decimal."""
    if valor is None or valor == "":
        return None
    try:
        return Decimal(str(valor))
    except (InvalidOperation, ValueError):
        return None


def _parse_datetime_iso(data_str: Optional[str]):
    """Converte data ISO 8601 para datetime."""
    if not data_str:
        return None
    try:
        return datetime.fromisoformat(data_str.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_tipo(tipo_str: Optional[str]) -> Optional[TipoEmpresa]:
    """Converte string para enum TipoEmpresa."""
    if not tipo_str:
        return None
    try:
        return TipoEmpresa(tipo_str.upper())
    except ValueError:
        return None


def salvar_empresa_do_json(db: Session, dados: dict) -> Empresa:
    """
    Cria ou atualiza uma Empresa no banco a partir do JSON do ReceitaWS.

    Args:
        db: Sessão SQLAlchemy
        dados: Dicionário retornado por consultar_cnpj()

    Returns:
        Instância de Empresa (persistida e com ID).
    """
    cnpj_limpo = normalizar_cnpj(dados.get("cnpj", ""))
    cnpj_formatado = formatar_cnpj(cnpj_limpo)

    empresa = db.query(Empresa).filter_by(cnpj=cnpj_formatado).first()
    criou = empresa is None
    if criou:
        empresa = Empresa(cnpj=cnpj_formatado)
        db.add(empresa)

    # Dados básicos
    empresa.nome = dados.get("nome") or empresa.nome or ""
    empresa.fantasia = dados.get("fantasia") or None
    empresa.tipo = _parse_tipo(dados.get("tipo"))
    empresa.porte = dados.get("porte") or None
    empresa.natureza_juridica = dados.get("natureza_juridica") or None
    empresa.capital_social = _parse_decimal(dados.get("capital_social"))
    empresa.abertura = _parse_data_br(dados.get("abertura"))

    # Situação cadastral
    empresa.situacao = dados.get("situacao") or None
    empresa.data_situacao = _parse_data_br(dados.get("data_situacao"))
    empresa.motivo_situacao = dados.get("motivo_situacao") or None
    empresa.situacao_especial = dados.get("situacao_especial") or None
    empresa.data_situacao_especial = _parse_data_br(dados.get("data_situacao_especial"))

    # Endereço
    empresa.logradouro = dados.get("logradouro") or None
    empresa.numero = dados.get("numero") or None
    empresa.complemento = dados.get("complemento") or None
    empresa.bairro = dados.get("bairro") or None
    empresa.municipio = dados.get("municipio") or None
    empresa.uf = dados.get("uf") or None
    empresa.cep = dados.get("cep") or None

    # Contato
    empresa.email = dados.get("email") or None
    empresa.telefone = dados.get("telefone") or None

    # Simples Nacional
    simples = dados.get("simples") or {}
    empresa.simples_optante = simples.get("optante")
    empresa.simples_data_opcao = _parse_data_br(simples.get("data_opcao"))
    empresa.simples_data_exclusao = _parse_data_br(simples.get("data_exclusao"))

    simei = dados.get("simei") or {}
    empresa.simei_optante = simei.get("optante")

    empresa.ultima_atualizacao_api = _parse_datetime_iso(dados.get("ultima_atualizacao"))

    db.flush()  # garante ID para os relacionamentos

    # Atividades (reset e recria)
    db.query(AtividadeEmpresa).filter_by(empresa_id=empresa.id).delete()

    atividade_principal = dados.get("atividade_principal") or []
    for ativ in atividade_principal:
        db.add(
            AtividadeEmpresa(
                empresa_id=empresa.id,
                codigo=ativ.get("code", ""),
                descricao=ativ.get("text", ""),
                is_principal=True,
            )
        )

    atividades_secundarias = dados.get("atividades_secundarias") or []
    for ativ in atividades_secundarias:
        codigo = ativ.get("code", "")
        # ReceitaWS retorna '00.00-0-00' quando não há secundárias
        if codigo and codigo != "00.00-0-00":
            db.add(
                AtividadeEmpresa(
                    empresa_id=empresa.id,
                    codigo=codigo,
                    descricao=ativ.get("text", ""),
                    is_principal=False,
                )
            )

    # Sócios (reset e recria)
    db.query(SocioEmpresa).filter_by(empresa_id=empresa.id).delete()

    for socio in dados.get("qsa") or []:
        nome = socio.get("nome")
        if nome:
            db.add(
                SocioEmpresa(
                    empresa_id=empresa.id,
                    nome=nome,
                    qualificacao=socio.get("qual"),
                )
            )

    db.commit()
    db.refresh(empresa)

    acao = "criada" if criou else "atualizada"
    logger.info(f"[CNPJ] Empresa {empresa.cnpj} - '{empresa.nome}' {acao}")

    return empresa


async def obter_ou_criar_empresa(db: Session, cnpj: str) -> Empresa:
    """
    Obtém empresa pelo CNPJ; se não existir, consulta ReceitaWS e cria.

    Args:
        db: Sessão SQLAlchemy
        cnpj: CNPJ (com ou sem formatação)

    Returns:
        Instância de Empresa.
    """
    cnpj_formatado = formatar_cnpj(normalizar_cnpj(cnpj))

    empresa = db.query(Empresa).filter_by(cnpj=cnpj_formatado).first()
    if empresa:
        return empresa

    dados = await consultar_cnpj(cnpj)
    return salvar_empresa_do_json(db, dados)
