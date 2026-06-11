"""Módulo de consulta e persistência de dados de CNPJ."""

from .persistencia import obter_ou_criar_empresa, salvar_empresa_do_json
from .receitaws import ConsultaCnpjError, consultar_cnpj

__all__ = [
    "consultar_cnpj",
    "ConsultaCnpjError",
    "salvar_empresa_do_json",
    "obter_ou_criar_empresa",
]
