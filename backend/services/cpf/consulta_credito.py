"""
Consulta de restrições financeiras / crédito para CPF (REQ-015.3).

Provedor ainda não definido (Serasa, SPC, Boa Vista, Quod). Este módulo expõe
a interface e um stub que retorna consulta indisponível quando não configurado.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from config import settings

from .validacao import mascarar_cpf, normalizar_cpf

logger = logging.getLogger(__name__)


@dataclass
class ResultadoConsultaCredito:
    """Resultado agregado da consulta de débitos (REQ-015.3)."""

    consulta_realizada: bool
    tem_restricao: bool = False
    quantidade_ocorrencias: Optional[int] = None
    score: Optional[int] = None
    provedor: str = "nenhum"
    mensagem: Optional[str] = None
    data_consulta: Optional[datetime] = None


async def consultar_credito(cpf: str) -> ResultadoConsultaCredito:
    """
    Consulta serviço externo de crédito/débitos para o CPF informado.

    Quando CPF_CONSULTA_CREDITO_ENABLED=false ou credenciais ausentes,
    retorna consulta_realizada=False (REQ-015.12 — não bloqueia o fluxo).
    """
    cpf_limpo = normalizar_cpf(cpf)
    cpf_mascarado = mascarar_cpf(cpf_limpo)

    if not settings.CPF_CONSULTA_CREDITO_ENABLED:
        logger.info("[CPF/Credito] Consulta desabilitada (CPF_CONSULTA_CREDITO_ENABLED=false)")
        return ResultadoConsultaCredito(
            consulta_realizada=False,
            provedor="desabilitado",
            mensagem="Consulta de crédito desabilitada",
        )

    provider = (settings.CPF_CONSULTA_CREDITO_PROVIDER or "").strip().lower()
    if not provider or provider == "stub":
        logger.info("[CPF/Credito] Provedor não configurado para CPF %s", cpf_mascarado)
        return ResultadoConsultaCredito(
            consulta_realizada=False,
            provedor="pendente",
            mensagem="Provedor de consulta de crédito ainda não configurado (REQ-015)",
        )

    # Ponto de extensão para integração futura (Serasa, SPC, etc.)
    logger.warning(
        "[CPF/Credito] Provedor '%s' configurado mas integração não implementada",
        provider,
    )
    return ResultadoConsultaCredito(
        consulta_realizada=False,
        provedor=provider,
        mensagem=f"Integração com provedor '{provider}' pendente de implementação",
    )
