"""
Persistência de Pessoa Física (PF) identificada por CPF.
"""

import logging
from datetime import date
from typing import Optional

from models import Pessoa
from sqlalchemy.orm import Session
from utils.datetime_utils import utc_now

from .consulta_credito import ResultadoConsultaCredito, consultar_credito
from .validacao import formatar_cpf, normalizar_cpf

logger = logging.getLogger(__name__)


def _situacao_de_credito(resultado: ResultadoConsultaCredito) -> Optional[str]:
    if not resultado.consulta_realizada:
        return "consulta_indisponivel"
    if resultado.tem_restricao:
        return "restricao_financeira"
    return "regular"


async def obter_ou_criar_pessoa(
    db: Session,
    cpf: str,
    nome: Optional[str] = None,
    data_nascimento: Optional[date] = None,
    consultar_credito_flag: bool = True,
) -> tuple[Pessoa, ResultadoConsultaCredito]:
    """
    Obtém pessoa pelo CPF; se não existir, cria com dados informados.

    Opcionalmente consulta crédito (REQ-015.3) e atualiza situacao.
    """
    cpf_formatado = formatar_cpf(normalizar_cpf(cpf))

    pessoa = db.query(Pessoa).filter_by(cpf=cpf_formatado).first()
    criou = pessoa is None
    if criou:
        pessoa = Pessoa(cpf=cpf_formatado)
        db.add(pessoa)

    if nome:
        pessoa.nome = nome
    if data_nascimento:
        pessoa.data_nascimento = data_nascimento

    resultado_credito = ResultadoConsultaCredito(consulta_realizada=False)
    if consultar_credito_flag:
        resultado_credito = await consultar_credito(cpf_formatado)
        pessoa.situacao = _situacao_de_credito(resultado_credito)
        if resultado_credito.consulta_realizada:
            pessoa.ultima_atualizacao_api = utc_now()

    db.commit()
    db.refresh(pessoa)

    acao = "criada" if criou else "atualizada"
    logger.info("[CPF] Pessoa %s %s (id=%s)", cpf_formatado, acao, pessoa.id)
    return pessoa, resultado_credito
