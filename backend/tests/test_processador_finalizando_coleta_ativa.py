"""Testes da coleta ativa em Finalizando (Fase F — F1/F2/F3/F4).

Mesma estratégia de `test_processador_transicao_finalizando.py`: injeta um
`ResultadoClassificacao` já pronto e chama `_decidir_resposta` diretamente via
`asyncio.run`, sem depender do classificador (regra ou LLM) acertar a intenção.
"""

import asyncio

import pytest
from database import Database
from models import Contato, FaseAtendimento, ItemAtendimento, Modelo, ModoOperacao, Produto
from services.classificador import EntidadesExtraidas, Intencao, NivelConfianca, ResultadoClassificacao
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.identificador import ResultadoIdentificacao, StatusIdentificacao
from services.processador import ProcessadorMensagem


def _resultado(intencao: Intencao, **entidades_kwargs) -> ResultadoClassificacao:
    return ResultadoClassificacao(
        intencoes=[intencao],
        confianca=0.9,
        confianca_nivel=NivelConfianca.ALTA,
        entidades=EntidadesExtraidas(**entidades_kwargs),
        origem="regra",
    )


@pytest.fixture
def db_session():
    database = Database()
    with database.get_session() as session:
        yield session


@pytest.fixture
def processador():
    return ProcessadorMensagem()


def _limpar(db_session, telefone):
    db_session.commit()
    apagar_dados_telefone(db_session, telefone)
    db_session.commit()


def _iniciar_finalizando_com_software(db_session, processador, telefone, software=None):
    """Ajuda os testes a colocarem um atendimento anônimo direto em Finalizando, com
    modelo pendente e (opcionalmente) software já capturado no mesmo turno inicial."""
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    kwargs = {"tipos_produto": ["relogio_ponto"]}
    if software:
        kwargs["software_ponto"] = software
    resultado = _resultado(Intencao.PEDIR_ORCAMENTO, **kwargs)
    asyncio.run(
        processador._decidir_resposta(
            db=db_session,
            telefone=telefone,
            conteudo="Quero orçamento de relógio de ponto",
            identificacao=identificacao,
            resultado_class=resultado,
        )
    )
    contato = db_session.query(Contato).filter_by(telefone=telefone).first()
    return contato


def _resolver_modelo_manual(db_session, atendimento):
    """Simula uma resolução de modelo bem-sucedida (F2 feliz) sem depender de dados reais
    no catálogo — cria o Produto/Modelo de teste e vincula via ItemAtendimento."""
    produto = db_session.query(Produto).filter_by(descricao="Relógio de Ponto (teste F)").first()
    if produto is None:
        produto = Produto(descricao="Relógio de Ponto (teste F)", ativo=True)
        db_session.add(produto)
        db_session.commit()
    modelo = db_session.query(Modelo).filter_by(codigo="TESTE-REP-F001").first()
    if modelo is None:
        modelo = Modelo(
            produto_id=produto.id,
            codigo="TESTE-REP-F001",
            descricao="Modelo de teste (Fase F)",
            preco_tabela=0,
            ativo=True,
        )
        db_session.add(modelo)
        db_session.commit()
    item = ItemAtendimento(
        atendimento_id=atendimento.id, produto_id=produto.id, modelo_id=modelo.id, quantidade=1
    )
    db_session.add(item)
    db_session.commit()
    return modelo


def _resolver_modelo_catraca_manual(db_session, atendimento):
    """Simula resolução de modelo para catraca em testes."""
    produto = db_session.query(Produto).filter_by(descricao="Catraca (teste F)").first()
    if produto is None:
        produto = Produto(descricao="Catraca (teste F)", ativo=True)
        db_session.add(produto)
        db_session.commit()
    modelo = db_session.query(Modelo).filter_by(codigo="TESTE-CAT-F001").first()
    if modelo is None:
        modelo = Modelo(
            produto_id=produto.id,
            codigo="TESTE-CAT-F001",
            descricao="Catraca de teste (Fase F)",
            preco_tabela=0,
            ativo=True,
        )
        db_session.add(modelo)
        db_session.commit()
    item = ItemAtendimento(
        atendimento_id=atendimento.id, produto_id=produto.id, modelo_id=modelo.id, quantidade=1
    )
    db_session.add(item)
    db_session.commit()
    return modelo


def _iniciar_finalizando_catraca(db_session, processador, telefone):
    """Coloca um atendimento direto em Finalizando para produto catraca."""
    identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
    resultado = _resultado(Intencao.PEDIR_ORCAMENTO, tipos_produto=["catraca"])
    asyncio.run(
        processador._decidir_resposta(
            db=db_session,
            telefone=telefone,
            conteudo="Quero orçamento de catraca",
            identificacao=identificacao,
            resultado_class=resultado,
        )
    )
    contato = db_session.query(Contato).filter_by(telefone=telefone).first()
    return contato


def test_f1_resposta_solta_faixa_funcionarios_sem_palavra_gatilho(db_session, processador):
    """F1: "80" sozinho (sem a palavra "funcionários") deve ser capturado quando a
    pergunta pendente atual é faixa_funcionarios — os extratores D3/D4 exigem gatilho."""
    telefone = "5511999981001"
    try:
        contato = _iniciar_finalizando_com_software(db_session, processador, telefone, software="nenhum")
        atendimento = contato.atendimentos[0]
        _resolver_modelo_manual(db_session, atendimento)

        identificacao = ResultadoIdentificacao(status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[])
        resultado = _resultado(Intencao.DESCONHECIDO)
        resposta = asyncio.run(
            processador._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="80",
                identificacao=identificacao,
                resultado_class=resultado,
            )
        )
        assert resposta.template_usado == "RESUMO_FINALIZANDO"
        db_session.refresh(atendimento)
        valores = {info.chave: info.valor for info in atendimento.informacoes}
        assert valores.get("faixa_funcionarios") == "80"
    finally:
        _limpar(db_session, telefone)


def test_f1_resposta_livre_software_fora_do_catalogo_conhecido(db_session, processador):
    """F1: nome de software fora de `_SOFTWARES_PONTO_CONHECIDOS` deve ser aceito como
    texto livre quando é a pergunta pendente atual (CAMPO-software-ponto não exige
    catálogo, ao contrário de modelo). Quando o software é real, faixa não é perguntada."""
    telefone = "5511999981002"
    try:
        contato = _iniciar_finalizando_com_software(db_session, processador, telefone)
        atendimento = contato.atendimentos[0]
        _resolver_modelo_manual(db_session, atendimento)

        identificacao = ResultadoIdentificacao(status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[])
        resultado = _resultado(Intencao.DESCONHECIDO)
        resposta_software = asyncio.run(
            processador._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="Ponto Certo",
                identificacao=identificacao,
                resultado_class=resultado,
            )
        )
        assert resposta_software.template_usado == "RESUMO_FINALIZANDO"
        db_session.refresh(atendimento)
        valores = {info.chave: info.valor for info in atendimento.informacoes}
        assert valores.get("software_controle_ponto") == "Ponto Certo"
        assert "faixa_funcionarios" not in valores
    finally:
        _limpar(db_session, telefone)


def test_f1_resposta_software_ponto_nenhum_pergunta_faixa(db_session, processador):
    """F1: quando o software de ponto é 'nenhum', a faixa de pessoas deve ser perguntada."""
    telefone = "5511999981020"
    try:
        contato = _iniciar_finalizando_com_software(db_session, processador, telefone)
        atendimento = contato.atendimentos[0]
        _resolver_modelo_manual(db_session, atendimento)

        identificacao = ResultadoIdentificacao(status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[])
        resposta_software = asyncio.run(
            processador._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="nenhum",
                identificacao=identificacao,
                resultado_class=_resultado(Intencao.DESCONHECIDO),
            )
        )
        assert resposta_software.template_usado == "PEDIR_FAIXA_FUNCIONARIOS"
        db_session.refresh(atendimento)
        valores = {info.chave: info.valor for info in atendimento.informacoes}
        assert valores.get("software_controle_ponto") == "nenhum"
    finally:
        _limpar(db_session, telefone)


def test_f1_nao_sequestra_intencao_reconhecida_como_resposta(db_session, processador):
    """F1 (regressão): uma mensagem que já bate numa intenção conhecida (ex.:
    "quero orçamento" de novo) não deve ser sequestrada como resposta livre — só
    DESCONHECIDO passa pela captura solta."""
    telefone = "5511999981003"
    try:
        contato = _iniciar_finalizando_com_software(db_session, processador, telefone)
        atendimento = contato.atendimentos[0]
        _resolver_modelo_manual(db_session, atendimento)

        identificacao = ResultadoIdentificacao(status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[])
        resultado = _resultado(Intencao.PEDIR_ORCAMENTO, tipos_produto=["relogio_ponto"])
        resposta = asyncio.run(
            processador._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="Quero orçamento",
                identificacao=identificacao,
                resultado_class=resultado,
            )
        )
        assert resposta.template_usado == "PEDIR_SOFTWARE_PONTO"
        db_session.refresh(atendimento)
        valores = {info.chave: info.valor for info in atendimento.informacoes}
        assert "software_controle_ponto" not in valores
    finally:
        _limpar(db_session, telefone)


def test_f3_duvida_sobre_outro_produto_nao_reescreve_tipos_produto(db_session, processador):
    """Regressão descoberta em smoke test manual: uma dúvida tangencial mencionando outro
    produto (ex.: "vocês têm catraca também?") não pode sobrescrever `tipos_produto` e
    esvaziar `campos_pendentes()` no meio da coleta — o tipo já está decidido em Finalizando."""
    telefone = "5511999981008"
    try:
        contato = _iniciar_finalizando_com_software(db_session, processador, telefone)
        atendimento = contato.atendimentos[0]
        _resolver_modelo_manual(db_session, atendimento)

        identificacao = ResultadoIdentificacao(status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[])
        resultado = _resultado(Intencao.PERGUNTAR_PRODUTO, tipos_produto=["catraca"])
        resposta = asyncio.run(
            processador._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="Vocês têm catraca também?",
                identificacao=identificacao,
                resultado_class=resultado,
            )
        )
        assert resposta.template_usado.endswith("+RETOMAR_PERGUNTA_PENDENTE")
        db_session.refresh(atendimento)
        valores = {info.chave: info.valor for info in atendimento.informacoes}
        assert valores.get("tipos_produto") == "relogio_ponto"
    finally:
        _limpar(db_session, telefone)


def test_f2_modelo_escala_para_humano_apos_tentativas_sem_correspondencia(db_session, processador):
    """F2: catálogo de Produto vazio para o tipo_leitor mencionado → após 2 tentativas
    sem correspondência, escala para atendimento humano (nunca aceita texto livre)."""
    telefone = "5511999981004"
    try:
        contato = _iniciar_finalizando_com_software(db_session, processador, telefone)
        atendimento = contato.atendimentos[0]
        identificacao = ResultadoIdentificacao(status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[])

        resultado_1 = _resultado(Intencao.DESCONHECIDO, tipo_leitor_mencionado="biometria_inexistente_teste")
        resposta_1 = asyncio.run(
            processador._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="Seria biométrico",
                identificacao=identificacao,
                resultado_class=resultado_1,
            )
        )
        db_session.refresh(atendimento)
        assert resposta_1.template_usado == "MODELO_NAO_RECONHECIDO"
        assert atendimento.modo_operacao == ModoOperacao.AGENTE
        assert atendimento.fase == FaseAtendimento.FINALIZANDO

        resultado_2 = _resultado(Intencao.DESCONHECIDO, tipo_leitor_mencionado="biometria_inexistente_teste")
        resposta_2 = asyncio.run(
            processador._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="Biométrico mesmo",
                identificacao=identificacao,
                resultado_class=resultado_2,
            )
        )
        db_session.refresh(atendimento)
        assert atendimento.modo_operacao == ModoOperacao.HUMANO
        assert resposta_2.template_usado == "ESCALADO_HUMANO"
        # resposta_1: 1ª tentativa sem correspondência → informa que não reconheceu
        assert resposta_1.template_usado == "MODELO_NAO_RECONHECIDO"
    finally:
        _limpar(db_session, telefone)


def test_f2_nao_conta_tentativa_quando_mensagem_nao_tenta_responder_modelo(db_session, processador):
    """F2: mensagens que não mencionam nenhuma tecnologia de leitor não devem consumir
    as tentativas de resolução de modelo (só contam quando há um sinal real)."""
    telefone = "5511999981005"
    try:
        contato = _iniciar_finalizando_com_software(db_session, processador, telefone)
        atendimento = contato.atendimentos[0]
        identificacao = ResultadoIdentificacao(status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[])

        for _ in range(3):
            resultado = _resultado(Intencao.DESCONHECIDO)
            asyncio.run(
                processador._decidir_resposta(
                    db=db_session,
                    telefone=telefone,
                    conteudo="oi, ainda estou pensando",
                    identificacao=identificacao,
                    resultado_class=resultado,
                )
            )
        db_session.refresh(atendimento)
        assert atendimento.modo_operacao == ModoOperacao.AGENTE
    finally:
        _limpar(db_session, telefone)


def test_f3_duvida_em_finalizando_retoma_pergunta_pendente(db_session, processador):
    """F3: uma dúvida de categoria 3 (perguntar_preco) durante Finalizando é respondida
    e a última pergunta pendente é reapresentada, sem perder a fase/progresso."""
    telefone = "5511999981006"
    try:
        contato = _iniciar_finalizando_com_software(db_session, processador, telefone)
        atendimento = contato.atendimentos[0]
        _resolver_modelo_manual(db_session, atendimento)

        identificacao = ResultadoIdentificacao(status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[])
        resultado = _resultado(Intencao.PERGUNTAR_PRECO)
        resposta = asyncio.run(
            processador._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="Quanto custa?",
                identificacao=identificacao,
                resultado_class=resultado,
            )
        )
        assert resposta.template_usado.endswith("+RETOMAR_PERGUNTA_PENDENTE")
        assert "software" in resposta.texto.lower() or "qual software" in resposta.texto.lower()
        db_session.refresh(atendimento)
        assert atendimento.fase == FaseAtendimento.FINALIZANDO
    finally:
        _limpar(db_session, telefone)


def test_f4_resumo_quando_tudo_capturado(db_session, processador):
    """F4: quando modelo (resolvido) + software 'nenhum' + faixa estão completos, apresenta o
    resumo pedindo confirmação."""
    telefone = "5511999981007"
    try:
        contato = _iniciar_finalizando_com_software(db_session, processador, telefone, software="nenhum")
        atendimento = contato.atendimentos[0]
        modelo = _resolver_modelo_manual(db_session, atendimento)

        identificacao = ResultadoIdentificacao(status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[])
        resultado = _resultado(Intencao.DESCONHECIDO)
        resposta_faixa = asyncio.run(
            processador._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="80",
                identificacao=identificacao,
                resultado_class=resultado,
            )
        )
        assert resposta_faixa.template_usado == "RESUMO_FINALIZANDO"
        assert modelo.descricao in resposta_faixa.texto
        assert "nenhum" in resposta_faixa.texto.lower()
        assert "80" in resposta_faixa.texto
    finally:
        _limpar(db_session, telefone)


def test_f1_resposta_livre_software_acesso(db_session, processador):
    """F1: software de controle de acesso fora da lista curta deve ser aceito como texto
    livre. Por ser não reconhecido, REQ-002.15 também aciona o alerta de homologação
    (opcional) antes da quantidade."""
    telefone = "5511999981010"
    try:
        contato = _iniciar_finalizando_catraca(db_session, processador, telefone)
        atendimento = contato.atendimentos[0]
        _resolver_modelo_catraca_manual(db_session, atendimento)

        identificacao = ResultadoIdentificacao(status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[])
        resposta = asyncio.run(
            processador._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="Outro Software X",
                identificacao=identificacao,
                resultado_class=_resultado(Intencao.DESCONHECIDO),
            )
        )
        assert resposta.template_usado == "PEDIR_HOMOLOGADO_SOFTWARE"
        db_session.refresh(atendimento)
        valores = {info.chave: info.valor for info in atendimento.informacoes}
        assert valores.get("software_controle_acesso") == "Outro Software X"

        # Cliente não responde à pergunta de homologação (alerta opcional, sem "sim"/"não"
        # reconhecíveis) — o sistema não insiste e avança direto para a quantidade.
        resposta_seguinte = asyncio.run(
            processador._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="ainda vou verificar isso com o pessoal",
                identificacao=identificacao,
                resultado_class=_resultado(Intencao.DESCONHECIDO),
            )
        )
        assert resposta_seguinte.template_usado == "PEDIR_QUANTIDADE"
    finally:
        _limpar(db_session, telefone)


def test_f1_catraca_sem_software_interesse_nuvem_pergunta_faixa(db_session, processador):
    """F1: catraca sem software + interesse em nuvem → pergunta faixa de pessoas e quantidade."""
    telefone = "5511999981011"
    try:
        contato = _iniciar_finalizando_catraca(db_session, processador, telefone)
        atendimento = contato.atendimentos[0]
        _resolver_modelo_catraca_manual(db_session, atendimento)

        identificacao = ResultadoIdentificacao(status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[])
        resposta_software = asyncio.run(
            processador._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="nenhum",
                identificacao=identificacao,
                resultado_class=_resultado(Intencao.DESCONHECIDO),
            )
        )
        assert resposta_software.template_usado == "PEDIR_INTERESSE_SISTEMA_NUVEM"

        resposta_interesse = asyncio.run(
            processador._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="sim",
                identificacao=identificacao,
                resultado_class=_resultado(Intencao.DESCONHECIDO),
            )
        )
        assert resposta_interesse.template_usado == "PEDIR_FAIXA_FUNCIONARIOS"
    finally:
        _limpar(db_session, telefone)


def test_f1_catraca_com_software_homologavel_pergunta_homologacao(db_session, processador):
    """F1: catraca com software EVO/Pacto/SCA/Panobianco/Sky → pergunta homologação."""
    telefone = "5511999981012"
    try:
        contato = _iniciar_finalizando_catraca(db_session, processador, telefone)
        atendimento = contato.atendimentos[0]
        _resolver_modelo_catraca_manual(db_session, atendimento)

        identificacao = ResultadoIdentificacao(status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[])
        resposta_software = asyncio.run(
            processador._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="EVO",
                identificacao=identificacao,
                resultado_class=_resultado(Intencao.DESCONHECIDO),
            )
        )
        assert resposta_software.template_usado == "PEDIR_HOMOLOGADO_SOFTWARE"

        # Cliente responde "sim" — captura a resposta (opcional) e avança para quantidade.
        resposta_homologacao = asyncio.run(
            processador._decidir_resposta(
                db=db_session,
                telefone=telefone,
                conteudo="sim, já verifiquei",
                identificacao=identificacao,
                resultado_class=_resultado(Intencao.DESCONHECIDO),
            )
        )
        assert resposta_homologacao.template_usado == "PEDIR_QUANTIDADE"
        db_session.refresh(atendimento)
        valores = {info.chave: info.valor for info in atendimento.informacoes}
        assert valores.get("homologado_software") == "sim"
    finally:
        _limpar(db_session, telefone)
