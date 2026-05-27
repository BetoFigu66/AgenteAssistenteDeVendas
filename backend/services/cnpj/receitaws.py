"""
Consulta de dados de CNPJ via ReceitaWS.

API pública: https://www.receitaws.com.br/
- Tier gratuito: 3 requisições/minuto
- Retorna dados cadastrais da Receita Federal
"""

import logging
import re

import httpx
from config import settings

logger = logging.getLogger(__name__)


class ConsultaCnpjError(Exception):
    """Erro ao consultar CNPJ."""

    pass


def normalizar_cnpj(cnpj: str) -> str:
    """
    Remove formatação do CNPJ, mantendo apenas dígitos.

    Exemplo:
        '03.965.806/0001-02' -> '03965806000102'
    """
    return re.sub(r"\D", "", cnpj or "")


def validar_cnpj(cnpj: str) -> bool:
    """
    Valida se o CNPJ tem formato válido (14 dígitos e dígitos verificadores corretos).
    """
    cnpj_limpo = normalizar_cnpj(cnpj)

    if len(cnpj_limpo) != 14:
        return False

    # Rejeita CNPJs com todos os dígitos iguais (ex: 00000000000000)
    if cnpj_limpo == cnpj_limpo[0] * 14:
        return False

    # Validação dos dígitos verificadores
    def calcular_digito(cnpj_parcial: str, pesos: list[int]) -> int:
        soma = sum(int(d) * p for d, p in zip(cnpj_parcial, pesos))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    pesos_primeiro = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos_segundo = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    digito1 = calcular_digito(cnpj_limpo[:12], pesos_primeiro)
    if digito1 != int(cnpj_limpo[12]):
        return False

    digito2 = calcular_digito(cnpj_limpo[:13], pesos_segundo)
    if digito2 != int(cnpj_limpo[13]):
        return False

    return True


def formatar_cnpj(cnpj: str) -> str:
    """
    Formata CNPJ com máscara padrão.

    Exemplo:
        '03965806000102' -> '03.965.806/0001-02'
    """
    c = normalizar_cnpj(cnpj)
    if len(c) != 14:
        return cnpj
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"


async def consultar_cnpj(cnpj: str, timeout_s: float = 15.0) -> dict:
    """
    Consulta dados de um CNPJ na API ReceitaWS.

    Args:
        cnpj: CNPJ (com ou sem formatação)
        timeout_s: Timeout da requisição em segundos

    Returns:
        Dicionário com os dados retornados pela API.

    Raises:
        ConsultaCnpjError: Se o CNPJ for inválido ou a consulta falhar.
    """
    cnpj_limpo = normalizar_cnpj(cnpj)

    if not validar_cnpj(cnpj_limpo):
        raise ConsultaCnpjError(f"CNPJ inválido: {cnpj}")

    url = f"{settings.RECEITAWS_BASE_URL.rstrip('/')}/{cnpj_limpo}"
    logger.info(f"[ReceitaWS] Consultando CNPJ {formatar_cnpj(cnpj_limpo)}")

    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            dados = resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            raise ConsultaCnpjError("Limite de consultas ReceitaWS atingido (3/min no tier grátis)."
            "Aguarde e tente novamente.") from e
        raise ConsultaCnpjError(f"Erro HTTP {e.response.status_code} ao consultar CNPJ") from e
    except httpx.RequestError as e:
        raise ConsultaCnpjError(f"Erro de conexão ao consultar CNPJ: {e}") from e

    status = dados.get("status", "").upper()
    if status == "ERROR":
        mensagem = dados.get("message", "CNPJ não encontrado")
        raise ConsultaCnpjError(f"ReceitaWS: {mensagem}")

    return dados
