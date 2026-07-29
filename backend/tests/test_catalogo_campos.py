"""Testes do catálogo de campos de qualificação (MVP Continuidade, passos B1-B4)."""

from services.conversacao.catalogo_campos import (
    CAMPO_FAIXA_FUNCIONARIOS,
    CAMPO_HOMOLOGADO_SOFTWARE,
    CAMPO_INTERESSE_SISTEMA_NUVEM,
    CAMPO_MODELO,
    CAMPO_QUANTIDADE,
    CAMPO_SOFTWARE_ACESSO,
    CAMPO_SOFTWARE_PONTO,
    DESTINO_ATENDIMENTO_INFO,
    DESTINO_ITEM_ATENDIMENTO_MODELO_ID,
    campos_do_produto,
)


def test_campos_do_produto_relogio_ponto_inclui_os_tres_campos_na_ordem():
    campos = campos_do_produto("relogio_ponto")
    assert campos == [CAMPO_MODELO, CAMPO_SOFTWARE_PONTO, CAMPO_FAIXA_FUNCIONARIOS]


def test_campos_do_produto_catraca_inclui_modelo_software_acesso_interesse_faixa_homologacao_e_quantidade():
    assert campos_do_produto("catraca") == [
        CAMPO_MODELO,
        CAMPO_SOFTWARE_ACESSO,
        CAMPO_INTERESSE_SISTEMA_NUVEM,
        CAMPO_FAIXA_FUNCIONARIOS,
        CAMPO_HOMOLOGADO_SOFTWARE,
        CAMPO_QUANTIDADE,
    ]


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


def test_faixa_funcionarios_aplicavel_a_relogio_ponto_sem_software():
    assert CAMPO_FAIXA_FUNCIONARIOS.se_aplica("relogio_ponto", {"software_controle_ponto": "nenhum"}) is True


def test_faixa_funcionarios_aplicavel_a_catraca_sem_software_com_interesse_nuvem():
    valores = {"software_controle_acesso": "nenhum", "interesse_sistema_nuvem": "sim"}
    assert CAMPO_FAIXA_FUNCIONARIOS.se_aplica("catraca", valores) is True


def test_faixa_funcionarios_nao_aplicavel_quando_tem_software_real():
    assert CAMPO_FAIXA_FUNCIONARIOS.se_aplica("relogio_ponto", {"software_controle_ponto": "Domínio"}) is False
    assert CAMPO_FAIXA_FUNCIONARIOS.se_aplica("catraca", {"software_controle_acesso": "EVO"}) is False


def test_faixa_funcionarios_sempre_aplicavel_a_produtos_sem_fluxo_de_software_acesso():
    """Regressão: câmera, leitor facial/biométrico, bastão de ronda e roteador não têm
    CAMPO_SOFTWARE_ACESSO/CAMPO_INTERESSE_SISTEMA_NUVEM (não estão em
    `produtos_aplicaveis` desses campos) — a condição "software == nenhum" nunca seria
    satisfeita para eles, então a faixa precisa ser sempre perguntada."""
    for tipo in ("camera", "leitor_facial", "leitor_biometrico", "bastao_de_ronda", "roteador"):
        assert CAMPO_FAIXA_FUNCIONARIOS.se_aplica(tipo, {}) is True


def test_interesse_sistema_nuvem_aplicavel_quando_catraca_sem_software():
    assert CAMPO_INTERESSE_SISTEMA_NUVEM.se_aplica("catraca", {"software_controle_acesso": "nenhum"}) is True
    assert CAMPO_INTERESSE_SISTEMA_NUVEM.se_aplica("catraca", {"software_controle_acesso": "EVO"}) is False


def test_homologado_software_aplicavel_para_qualquer_software_real():
    """REQ-002.14C (software conhecido) e REQ-002.15 (outro/não reconhecido): o alerta de
    homologação aparece sempre que há um software real informado, reconhecido ou não."""
    assert CAMPO_HOMOLOGADO_SOFTWARE.se_aplica("catraca", {"software_controle_acesso": "EVO"}) is True
    assert CAMPO_HOMOLOGADO_SOFTWARE.se_aplica("catraca", {"software_controle_acesso": "Outro Software X"}) is True
    assert CAMPO_HOMOLOGADO_SOFTWARE.se_aplica("catraca", {"software_controle_acesso": "nenhum"}) is False
    assert CAMPO_HOMOLOGADO_SOFTWARE.se_aplica("catraca", {}) is False


def test_homologado_software_nao_e_obrigatorio():
    """A pergunta é um alerta/orientação — não bloqueia a qualificação (REQ-002.14C/15)."""
    assert CAMPO_HOMOLOGADO_SOFTWARE.obrigatorio is False


def test_quantidade_nao_aplicavel_a_relogio_ponto():
    assert CAMPO_QUANTIDADE.se_aplica("relogio_ponto", {}) is False


def test_quantidade_aplicavel_a_catraca():
    assert CAMPO_QUANTIDADE.se_aplica("catraca", {}) is True
