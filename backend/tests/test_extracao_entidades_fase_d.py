"""Testes da extração passiva de software/tipo de leitor/faixa de funcionários/marca/aplicação (Fase D — D3/D4/D5)."""

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


def test_extrai_marca_topdata():
    e = extrair_entidades("Quero uma catraca Topdata")
    assert e.marca == "Topdata"


def test_extrai_marca_control_id_com_hifen():
    e = extrair_entidades("Vocês têm leitor facial Control-ID?")
    assert e.marca == "Control-ID"


def test_nao_extrai_marca_quando_nao_mencionada():
    e = extrair_entidades("Quero orçamento")
    assert e.marca is None


def test_extrai_aplicacao_condominio():
    e = extrair_entidades("Preciso de catraca para condomínio")
    assert e.aplicacao == "Condomínios"


def test_extrai_aplicacao_grande_empresa():
    e = extrair_entidades("Somos uma grande empresa, precisamos de relógio de ponto")
    assert e.aplicacao == "Grandes Empresas"


def test_extrai_aplicacao_pme():
    e = extrair_entidades("Solução para PME")
    assert e.aplicacao == "Pequenas e médias empresas"


def test_nao_extrai_aplicacao_quando_nao_mencionada():
    e = extrair_entidades("Quero orçamento")
    assert e.aplicacao is None


def test_extrai_atributo_generico_tecnologia_leitura_biometria():
    e = extrair_entidades("Quero uma catraca com biometria")
    assert e.atributos.get("tecnologia_leitura") == "biometria"


def test_extrai_atributo_generico_tecnologia_leitura_facial():
    e = extrair_entidades("Preciso de leitor facial")
    assert e.atributos.get("tecnologia_leitura") == "facial"


def test_extrai_atributo_generico_tecnologia_leitura_cartao():
    e = extrair_entidades("Quero relógio de ponto de cartão de proximidade")
    assert e.atributos.get("tecnologia_leitura") == "cartao"


def test_atributo_generico_persiste_tipo_leitor_mencionado():
    # Garante que tipo_leitor_mencionado continua preenchido para compatibilidade.
    e = extrair_entidades("Quero relógio de ponto biométrico")
    assert e.tipo_leitor_mencionado == "biometria"
    assert e.atributos.get("tecnologia_leitura") == "biometria"


def test_extrai_software_acesso_evo():
    e = extrair_entidades("Usamos o EVO para controle de acesso")
    assert e.software_acesso == "EVO"


def test_extrai_software_acesso_pacto():
    e = extrair_entidades("Nosso sistema é o Pacto")
    assert e.software_acesso == "Pacto"


def test_nao_extrai_software_acesso_quando_nao_mencionado():
    e = extrair_entidades("Quero orçamento de catraca")
    assert e.software_acesso is None
