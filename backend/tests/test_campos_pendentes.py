"""Testes do motor de campos pendentes (MVP Continuidade, Fase C).

Usa stubs leves (sem tocar o banco) em vez de instâncias reais de
`Atendimento`/`AtendimentoInfo`/`ItemAtendimento` — as funções testadas só
acessam `.informacoes` (chave/valor) e `.itens` (modelo_id) por duck typing.
"""

from dataclasses import dataclass, field
from typing import Optional

from services.conversacao.campos_pendentes import (
    campos_pendentes,
    nao_perguntar_de_novo,
    proxima_pergunta,
)
from services.conversacao.catalogo_campos import (
    CAMPO_FAIXA_FUNCIONARIOS,
    CAMPO_MODELO,
    CAMPO_SOFTWARE_PONTO,
)


@dataclass
class _InfoStub:
    chave: str
    valor: Optional[str]


@dataclass
class _ItemStub:
    modelo_id: Optional[int] = None


@dataclass
class _AtendimentoStub:
    informacoes: list = field(default_factory=list)
    itens: list = field(default_factory=list)


def _atendimento(*, tipo_produto=None, infos=None, modelo_id=None):
    informacoes = list(infos or [])
    if tipo_produto is not None:
        informacoes.append(_InfoStub(chave="tipos_produto", valor=tipo_produto))
    itens = [_ItemStub(modelo_id=modelo_id)] if modelo_id is not None else []
    return _AtendimentoStub(informacoes=informacoes, itens=itens)


def test_sem_tipo_produto_identificado_nao_ha_pendentes():
    atendimento = _atendimento()
    assert campos_pendentes(atendimento) == []
    assert proxima_pergunta(atendimento) is None


def test_relogio_ponto_recem_identificado_pendentes_sao_modelo_e_software():
    # faixa_funcionarios ainda não é pendência: depende da resposta de software (C4).
    atendimento = _atendimento(tipo_produto="relogio_ponto")
    assert campos_pendentes(atendimento) == [CAMPO_MODELO, CAMPO_SOFTWARE_PONTO]


def test_proxima_pergunta_e_modelo_primeiro_na_ordem():
    atendimento = _atendimento(tipo_produto="relogio_ponto")
    assert proxima_pergunta(atendimento) is CAMPO_MODELO


def test_modelo_ja_resolvido_nao_e_mais_pendente():
    atendimento = _atendimento(tipo_produto="relogio_ponto", modelo_id=42)
    pendentes = campos_pendentes(atendimento)
    assert CAMPO_MODELO not in pendentes
    assert CAMPO_SOFTWARE_PONTO in pendentes


def test_software_ja_capturado_nao_e_mais_pendente_e_libera_faixa_funcionarios():
    atendimento = _atendimento(
        tipo_produto="relogio_ponto",
        infos=[_InfoStub(chave="software_controle_ponto", valor="nenhum")],
    )
    pendentes = campos_pendentes(atendimento)
    assert CAMPO_SOFTWARE_PONTO not in pendentes
    assert CAMPO_FAIXA_FUNCIONARIOS in pendentes
    assert CAMPO_MODELO in pendentes


def test_software_com_valor_real_nao_libera_faixa_funcionarios():
    atendimento = _atendimento(
        tipo_produto="relogio_ponto",
        infos=[_InfoStub(chave="software_controle_ponto", valor="Domínio")],
    )
    assert CAMPO_FAIXA_FUNCIONARIOS not in campos_pendentes(atendimento)


def test_todos_os_campos_capturados_nenhuma_pendencia():
    atendimento = _atendimento(
        tipo_produto="relogio_ponto",
        modelo_id=42,
        infos=[
            _InfoStub(chave="software_controle_ponto", valor="nenhum"),
            _InfoStub(chave="faixa_funcionarios", valor="80"),
        ],
    )
    assert campos_pendentes(atendimento) == []
    assert proxima_pergunta(atendimento) is None


def test_nao_perguntar_de_novo_modelo_usa_item_atendimento():
    sem_modelo = _atendimento(tipo_produto="relogio_ponto")
    com_modelo = _atendimento(tipo_produto="relogio_ponto", modelo_id=7)
    assert nao_perguntar_de_novo(CAMPO_MODELO, sem_modelo) is False
    assert nao_perguntar_de_novo(CAMPO_MODELO, com_modelo) is True


def test_nao_perguntar_de_novo_software_usa_atendimento_info():
    sem_software = _atendimento(tipo_produto="relogio_ponto")
    com_software = _atendimento(
        tipo_produto="relogio_ponto",
        infos=[_InfoStub(chave="software_controle_ponto", valor="TOTVS")],
    )
    assert nao_perguntar_de_novo(CAMPO_SOFTWARE_PONTO, sem_software) is False
    assert nao_perguntar_de_novo(CAMPO_SOFTWARE_PONTO, com_software) is True


def test_produto_sem_campos_mapeados_retorna_vazio():
    # Catraca ainda não tem campos mapeados nesta fatia (fora do MVP — ver §9 do plano).
    atendimento = _atendimento(tipo_produto="catraca")
    assert campos_pendentes(atendimento) == []
