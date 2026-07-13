"""Testes da extração passiva de software/tipo de leitor/faixa de funcionários (Fase D — D3/D4)."""

from services.classificador import extrair_entidades


def test_extrai_software_ponto_conhecido():
    e = extrair_entidades("Usamos o Domínio pra controlar o ponto")
    assert e.software_ponto == "Domínio"


def test_extrai_software_totvs_case_insensitive():
    e = extrair_entidades("nosso sistema é o TOTVS")
    assert e.software_ponto == "TOTVS"


def test_nao_extrai_software_quando_nao_mencionado():
    e = extrair_entidades("Vocês têm relógio de ponto biométrico?")
    assert e.software_ponto is None


def test_extrai_tipo_leitor_biometrico():
    e = extrair_entidades("Quero um relógio biométrico")
    assert e.tipo_leitor_mencionado == "biometria"


def test_extrai_tipo_leitor_facial():
    e = extrair_entidades("Prefiro o modelo com reconhecimento facial")
    assert e.tipo_leitor_mencionado == "facial"


def test_extrai_tipo_leitor_cartao():
    e = extrair_entidades("Pode ser o de cartão mesmo")
    assert e.tipo_leitor_mencionado == "cartao"


def test_nao_extrai_tipo_leitor_quando_nao_mencionado():
    e = extrair_entidades("Quero orçamento")
    assert e.tipo_leitor_mencionado is None


def test_extrai_faixa_funcionarios():
    e = extrair_entidades("Somos 80 funcionários")
    assert e.faixa_funcionarios == 80


def test_extrai_faixa_colaboradores():
    e = extrair_entidades("temos uns 50 colaboradores")
    assert e.faixa_funcionarios == 50


def test_nao_extrai_faixa_funcionarios_sem_palavra_gatilho():
    # "5 unidades" não deve virar faixa_funcionarios (isso é _REGEX_QUANTIDADE, outro campo).
    e = extrair_entidades("Preciso de 5 unidades")
    assert e.faixa_funcionarios is None


def test_extracao_composta_software_leitor_e_faixa_juntos():
    e = extrair_entidades("Preciso de relógio compatível com Domínio, uns 80 funcionários, biométrico")
    assert e.software_ponto == "Domínio"
    assert e.tipo_leitor_mencionado == "biometria"
    assert e.faixa_funcionarios == 80
