"""Módulo de consulta e persistência de dados de CNPJ."""
from .receitaws import consultar_cnpj, ConsultaCnpjError
from .persistencia import salvar_empresa_do_json, obter_ou_criar_empresa

__all__ = [
    "consultar_cnpj",
    "ConsultaCnpjError",
    "salvar_empresa_do_json",
    "obter_ou_criar_empresa",
]
