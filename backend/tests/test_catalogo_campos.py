"""Testes do catálogo de campos de qualificação (MVP Continuidade, passos B1-B4)."""

from services.conversacao.catalogo_campos import (
    CAMPO_FAIXA_FUNCIONARIOS,
    CAMPO_MODELO,
    CAMPO_SOFTWARE_PONTO,
    DESTINO_ATENDIMENTO_INFO,
    DESTINO_ITEM_ATENDIMENTO_MODELO_ID,
    campos_do_produto,
)


def test_campos_do_produto_relogio_ponto_inclui_os_tres_campos_na_ordem():
    campos = campos_do_produto("relogio_ponto")
    assert campos == [CAMPO_MODELO, CAMPO_SOFTWARE_PONTO, CAMPO_FAIXA_FUNCIONARIOS]


def test_campos_do_produto_catraca_ainda_vazio():
    # Catraca ainda não tem campos mapeados nesta fatia (fora do MVP — ver §9 do plano).
    assert campos_do_produto("catraca") == []


def test_software_ponto_se_aplica_a_relogio_ponto():
    assert CAMPO_SOFTWARE_PONTO.se_aplica("relogio_ponto", {}) is True


def test_software_ponto_nao_se_aplica_a_outro_produto():
    assert CAMPO_SOFTWARE_PONTO.se_aplica("catraca", {}) is False


def test_chave_e_id_catalogo_do_software_ponto():
    assert CAMPO_SOFTWARE_PONTO.chave == "software_controle_ponto"
    assert CAMPO_SOFTWARE_PONTO.id_catalogo == "CAMPO-software-ponto"


def test_modelo_resolve_para_item_atendimento_modelo_id():
    assert CAMPO_MODELO.chave == "modelo_produto"
    assert CAMPO_MODELO.destino == DESTINO_ITEM_ATENDIMENTO_MODELO_ID


def test_software_e_faixa_funcionarios_vao_para_atendimento_info():
    assert CAMPO_SOFTWARE_PONTO.destino == DESTINO_ATENDIMENTO_INFO
    assert CAMPO_FAIXA_FUNCIONARIOS.destino == DESTINO_ATENDIMENTO_INFO


def test_faixa_funcionarios_nao_aplicavel_sem_resposta_de_software_ainda():
    # Dependência de aplicabilidade: sem saber a resposta de software, o campo não é pendência ainda.
    assert CAMPO_FAIXA_FUNCIONARIOS.se_aplica("relogio_ponto", {}) is False


def test_faixa_funcionarios_aplicavel_quando_software_e_nenhum():
    valores = {"software_controle_ponto": "nenhum"}
    assert CAMPO_FAIXA_FUNCIONARIOS.se_aplica("relogio_ponto", valores) is True


def test_faixa_funcionarios_nao_aplicavel_quando_ha_software():
    valores = {"software_controle_ponto": "Domínio"}
    assert CAMPO_FAIXA_FUNCIONARIOS.se_aplica("relogio_ponto", valores) is False


def test_faixa_funcionarios_aceita_variacao_de_caixa_e_espacos_em_nenhum():
    valores = {"software_controle_ponto": "  Nenhum  "}
    assert CAMPO_FAIXA_FUNCIONARIOS.se_aplica("relogio_ponto", valores) is True
