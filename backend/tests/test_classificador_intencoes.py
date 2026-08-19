"""Testes do motor de classificação Intenção×Fase→Ações (correção do bug da Diana):
`classificar_por_regras()` deixou de retornar só a primeira regra que bater — coleta
todas. `classificar()`/`_finalizar_intencoes()` juntam isso com intenções derivadas de
entidades (nome, data de nascimento).
"""

import asyncio

from services.classificador import (
    EntidadesExtraidas,
    Intencao,
    _finalizar_intencoes,
    classificar,
    classificar_por_regras,
)


def test_saudacao_nao_engole_pergunta_de_produto_na_mesma_mensagem():
    """Regressão do bug relatado: "Bom dia... quero informações sobre relogio de ponto
    biometrico" precisa reconhecer SAUDACAO **e** PERGUNTAR_PRODUTO, não só a primeira
    regra da lista (SAUDACAO vinha antes de PERGUNTAR_PRODUTO)."""
    matches = classificar_por_regras("Bom dia. Meu nome é Diana, quero informações sobre relogio de ponto biometrico.")
    intencoes_batidas = {i for i, _ in matches}
    assert Intencao.SAUDACAO in intencoes_batidas
    assert Intencao.PERGUNTAR_PRODUTO in intencoes_batidas


def test_cnpj_tem_prioridade_sobre_cpf_mutuamente_exclusivos():
    matches = classificar_por_regras("Meu CNPJ é 12.345.678/0001-95")
    assert matches == [(Intencao.FORNECER_CNPJ, 0.9)]


def test_mensagem_vazia_retorna_desconhecido():
    assert classificar_por_regras("") == [(Intencao.DESCONHECIDO, 0.0)]
    assert classificar_por_regras("   ") == [(Intencao.DESCONHECIDO, 0.0)]


def test_finalizar_intencoes_ordena_por_confianca_e_deduplica():
    matches = [(Intencao.SAUDACAO, 0.75), (Intencao.PERGUNTAR_PRODUTO, 0.75), (Intencao.FORNECER_CNPJ, 0.9)]
    intencoes = _finalizar_intencoes(matches, EntidadesExtraidas())
    assert intencoes[0] == Intencao.FORNECER_CNPJ  # maior confiança primeiro
    assert set(intencoes) == {Intencao.SAUDACAO, Intencao.PERGUNTAR_PRODUTO, Intencao.FORNECER_CNPJ}


def test_finalizar_intencoes_acrescenta_nome_e_data_nascimento_derivados_de_entidades():
    entidades = EntidadesExtraidas(nomes=["Diana"], datas_nascimento=["1990-01-01"])
    intencoes = _finalizar_intencoes([(Intencao.PEDIR_ORCAMENTO, 0.75)], entidades)
    assert Intencao.FORNECER_NOME in intencoes
    assert Intencao.FORNECER_DATA_NASCIMENTO in intencoes
    assert Intencao.PEDIR_ORCAMENTO in intencoes


def test_finalizar_intencoes_remove_desconhecido_quando_ha_nome():
    """Uma mensagem só com nome ("Meu nome é Bruno") não bate em nenhuma regra de
    _REGRAS_INTENCAO — mas não deveria ficar marcada como puramente DESCONHECIDO já que
    FORNECER_NOME é um sinal real."""
    entidades = EntidadesExtraidas(nomes=["Bruno"])
    intencoes = _finalizar_intencoes([(Intencao.DESCONHECIDO, 0.0)], entidades)
    assert intencoes == [Intencao.FORNECER_NOME]


def test_finalizar_intencoes_mantem_desconhecido_isolado_sem_nenhum_sinal():
    intencoes = _finalizar_intencoes([(Intencao.DESCONHECIDO, 0.0)], EntidadesExtraidas())
    assert intencoes == [Intencao.DESCONHECIDO]


def test_classificar_ponta_a_ponta_sem_llm_retorna_todas_as_intencoes():
    resultado = asyncio.run(
        classificar("Bom dia, quero orçamento de relógio de ponto", llm=None)
    )
    assert Intencao.SAUDACAO in resultado.intencoes
    assert Intencao.PEDIR_ORCAMENTO in resultado.intencoes
    # intencao_principal é a de maior confiança (ambas 0.75 aqui — a primeira da lista
    # ordenada estável mantém a ordem de _REGRAS_INTENCAO, SAUDACAO vem antes)
    assert resultado.intencao_principal in resultado.intencoes


# DEC-008: "vocês vendem/trabalham com X?" vira PERGUNTAR_DISPONIBILIDADE com produto,
# PEDIR_ORCAMENTO só para orçamento/cotação/preço explícitos.

def test_vendem_com_produto_eh_perguntar_disponibilidade():
    assert Intencao.PERGUNTAR_DISPONIBILIDADE in {
        i for i, _ in classificar_por_regras("Vocês vendem relógio de ponto?")}


def test_vendem_com_tecnologia_e_produto_eh_perguntar_disponibilidade():
    assert Intencao.PERGUNTAR_DISPONIBILIDADE in {
        i for i, _ in classificar_por_regras("Vocês vendem relógio de ponto biométrico?")}
    assert Intencao.PERGUNTAR_PRODUTO in {
        i for i, _ in classificar_por_regras("Vocês vendem relógio de ponto biométrico?")}


def test_trabalham_com_produto_eh_perguntar_disponibilidade():
    assert Intencao.PERGUNTAR_DISPONIBILIDADE in {i for i, _ in classificar_por_regras("Vocês trabalham com catraca?")}


def test_vendem_sem_produto_nao_eh_disponibilidade_nem_orcamento():
    """Perguntas genéricas como 'Vocês vendem para todo o Brasil?' não devem
    ser qualificação/orçamento sem produto."""
    resultado = asyncio.run(classificar("Vocês vendem para todo o Brasil?", llm=None))
    assert Intencao.PERGUNTAR_DISPONIBILIDADE not in resultado.intencoes
    assert Intencao.PEDIR_ORCAMENTO not in resultado.intencoes


def test_trabalham_sem_produto_nao_eh_disponibilidade_nem_orcamento():
    resultado = asyncio.run(classificar("Vocês trabalham com outras empresas?", llm=None))
    assert Intencao.PERGUNTAR_DISPONIBILIDADE not in resultado.intencoes
    assert Intencao.PEDIR_ORCAMENTO not in resultado.intencoes


def test_orcamento_explicito_sem_produto_continua_pedir_orcamento():
    """'Quanto custa?' sem produto continua sendo PEDIR_ORCAMENTO — o sistema
    pede o produto depois, preservando o comportamento antigo."""
    resultado = asyncio.run(classificar("Quanto custa?", llm=None))
    assert Intencao.PEDIR_ORCAMENTO in resultado.intencoes


def test_classificar_vendem_com_produto_eh_perguntar_disponibilidade():
    resultado = asyncio.run(classificar("Vocês vendem relógio de ponto?", llm=None))
    assert Intencao.PERGUNTAR_DISPONIBILIDADE in resultado.intencoes
    assert "relogio_ponto" in resultado.entidades.tipos_produto


def test_vendem_relogio_biometrico_sem_de_ponto_eh_perguntar_disponibilidade():
    """DEC-008: 'relógio biométrico' sem 'de ponto' ainda é reconhecido como produto."""
    resultado = asyncio.run(classificar("Vocês vendem relógio biométrico?", llm=None))
    assert Intencao.PERGUNTAR_DISPONIBILIDADE in resultado.intencoes
    assert "relogio_ponto" in resultado.entidades.tipos_produto


def test_vendem_relogio_com_cartao_eh_perguntar_disponibilidade():
    """DEC-008: 'relógio de cartão' (sem 'de ponto') é reconhecido como produto."""
    resultado = asyncio.run(classificar("Vocês vendem relógio de cartão?", llm=None))
    assert Intencao.PERGUNTAR_DISPONIBILIDADE in resultado.intencoes
    assert "relogio_ponto" in resultado.entidades.tipos_produto
