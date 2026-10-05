"""Pilha de perguntas pendentes (`services/conversacao/pilha.py`) e tratadores.

Os tratadores são puros e testados sem banco. A pilha é testada sobre um atendimento real
(base compartilhada, telefone único por caso, limpo ao final), com o modo de execução
vindo de um dublê, como em `test_processador_nome_perfil.py`.
"""

import asyncio

import pytest
from database import Database
from models import Atendimento, Mensagem, ModoExecucao, MotivoEncerramento, OrigemMensagem, StatusPergunta
from services import atendimentos as atendimentos_svc
from services.classificador import EntidadesExtraidas, Intencao, NivelConfianca, ResultadoClassificacao
from services.conversacao import pilha
from services.conversacao.acoes import ContextoAcao
from services.conversacao.tratadores import Numero, SimNao, SinalDeModelo, Software, StatusLeitura, entrada_de
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.parametro_service import ParametroService
from services.processador import ProcessadorMensagem

# ----------------------------------------------------------------------
# Tratadores
# ----------------------------------------------------------------------


def _ler(tratador, conteudo, *intencoes, **entidades):
    entrada = entrada_de(conteudo, intencoes or (Intencao.DESCONHECIDO,), EntidadesExtraidas(**entidades))
    return tratador.interpretar(entrada)


def test_sim_nao_usa_a_intencao_e_le_a_negacao_antes_do_sim():
    assert _ler(SimNao(), "sim", Intencao.CONFIRMAR).valor == "sim"
    assert _ler(SimNao(), "não", Intencao.NEGAR).valor == "não"
    assert _ler(SimNao(), "sim, temos interesse").valor == "sim"
    # "quero" está no regex do sim: a negação tem que ganhar.
    assert _ler(SimNao(), "não quero").valor == "não"
    assert _ler(SimNao(), "vou ver depois").status == StatusLeitura.NAO_RECONHECEU


def test_intencao_de_outro_assunto_nao_e_sequestrada_como_resposta():
    assert _ler(SimNao(), "sim, e quanto custa?", Intencao.PERGUNTAR_PRECO).status == StatusLeitura.NAO_RECONHECEU
    assert _ler(Numero(), "quero orçamento de 3", Intencao.PEDIR_ORCAMENTO).status == StatusLeitura.NAO_RECONHECEU


def test_numero_fora_da_faixa_e_invalido():
    assert _ler(Numero(), "umas 80").valor == "80"
    assert _ler(Numero(), "0").status == StatusLeitura.INVALIDO


def test_software_nega_com_nenhum_e_aceita_texto_livre():
    assert _ler(Software(), "errado", Intencao.NEGAR).valor == "nenhum"
    assert _ler(Software(), "nenhum").valor == "nenhum"
    assert _ler(Software(), "Ponto Certo").valor == "Ponto Certo"


def test_sinal_de_modelo_e_discriminante():
    assert SinalDeModelo.discriminante
    assert _ler(SinalDeModelo(), "biometria", tipo_leitor_mencionado="biometria").reconheceu
    assert not _ler(SinalDeModelo(), "50").reconheceu


# ----------------------------------------------------------------------
# Pilha
# ----------------------------------------------------------------------

# Levas artificiais bem acima de qualquer id real de mensagem: são sempre o turno mais
# recente da pilha.
_LEVA = 10**9


@pytest.fixture
def db_session(monkeypatch):
    monkeypatch.setattr(ParametroService, "modo_execucao", lambda self: ModoExecucao.EXECUCAO_NORMAL)
    with Database().get_session() as session:
        yield session
        session.rollback()


def _limpar(db_session, telefone):
    db_session.commit()
    apagar_dados_telefone(db_session, telefone)
    db_session.commit()


def _atendimento_catraca(db_session, telefone):
    """Atendimento em Finalizando para catraca (pergunta o modelo)."""
    resultado = asyncio.run(ProcessadorMensagem().processar(db_session, telefone, "Quero orçamento de catraca"))
    db_session.commit()
    return db_session.get(Atendimento, resultado.atendimento_id)


def _ctx(db_session, atendimento, conteudo="", intencoes=(Intencao.DESCONHECIDO,), leva=None, citada=None):
    resultado = ResultadoClassificacao(
        intencoes=list(intencoes),
        confianca=0.9,
        confianca_nivel=NivelConfianca.ALTA,
        entidades=EntidadesExtraidas(),
        origem="regra",
    )
    return ContextoAcao(
        db=db_session,
        telefone="",
        conteudo=conteudo,
        identificacao=None,
        resultado_class=resultado,
        processador=ProcessadorMensagem(),
        atendimento=atendimento,
        mensagem_id=leva,
        resposta_a_mensagem_id=citada,
    )


def _abertas(atendimento):
    return [p.chave for p in pilha.abertas(atendimento)]


def _valor(atendimento, chave):
    return atendimento.valores_capturados().get(chave)


def test_reapresentar_move_para_o_topo_sem_duplicar(db_session):
    telefone = "+5511999977301"
    try:
        atendimento = _atendimento_catraca(db_session, telefone)
        pilha.empilhar(_ctx(db_session, atendimento, leva=_LEVA), "quantidade", "Quantas unidades?")
        pilha.empilhar(_ctx(db_session, atendimento, leva=_LEVA + 1), "faixa_funcionarios", "Qual a faixa?")
        pilha.empilhar(_ctx(db_session, atendimento, leva=_LEVA + 2), "quantidade", "Quantas unidades?")

        assert _abertas(atendimento) == ["modelo_produto", "faixa_funcionarios", "quantidade"]
        quantidade = pilha.topo(atendimento)
        assert quantidade.reapresentacoes == 1
    finally:
        _limpar(db_session, telefone)


def test_teto_descarta_a_mais_antiga(db_session):
    telefone = "+5511999977302"
    try:
        atendimento = _atendimento_catraca(db_session, telefone)
        for i, chave in enumerate(("quantidade", "faixa_funcionarios", "software_controle_acesso")):
            pilha.empilhar(_ctx(db_session, atendimento, leva=_LEVA + i), chave, f"pergunta {chave}?")

        assert len(pilha.abertas(atendimento)) == pilha.TETO_PILHA
        assert "modelo_produto" not in _abertas(atendimento)
    finally:
        _limpar(db_session, telefone)


def test_resposta_ambigua_aciona_a_fila_serial_e_drena_uma_por_vez(db_session):
    """Duas perguntas numéricas na mesma leva: "50" pode ser qualquer uma. A resposta é
    descartada e o sistema retoma uma por uma (decisão do Beto, 05/10)."""
    telefone = "+5511999977303"
    try:
        atendimento = _atendimento_catraca(db_session, telefone)
        ctx_pergunta = _ctx(db_session, atendimento, leva=_LEVA)
        pilha.empilhar(ctx_pergunta, "faixa_funcionarios", "Qual a faixa de pessoas?")
        pilha.empilhar(ctx_pergunta, "quantidade", "Quantas unidades você precisa?")

        confuso = asyncio.run(pilha.resolver_resposta(_ctx(db_session, atendimento, "50", leva=_LEVA + 1)))
        assert confuso.template_usado == "PILHA_CONFUSO"
        # Começa pela pergunta mais antiga que ainda está aberta: a do modelo.
        assert confuso.texto.endswith(pilha.fila_serial(atendimento)[0].texto)
        assert _valor(atendimento, "faixa_funcionarios") is None
        assert _valor(atendimento, "quantidade") is None

        fila = [p.chave for p in pilha.fila_serial(atendimento)]
        assert fila == ["modelo_produto", "faixa_funcionarios", "quantidade"]

        # Na fila serial só a pergunta da vez é candidata: "50" não serve para o modelo.
        ninguem = asyncio.run(pilha.resolver_resposta(_ctx(db_session, atendimento, "50", leva=_LEVA + 2)))
        assert ninguem is None
        assert _valor(atendimento, "faixa_funcionarios") is None
    finally:
        _limpar(db_session, telefone)


def test_fila_serial_anota_e_retoma_a_proxima(db_session):
    telefone = "+5511999977304"
    try:
        atendimento = _atendimento_catraca(db_session, telefone)
        # Tira o modelo do caminho, para a fila ter só as duas numéricas.
        pilha.descartar_todas(atendimento)
        ctx_pergunta = _ctx(db_session, atendimento, leva=_LEVA)
        pilha.empilhar(ctx_pergunta, "faixa_funcionarios", "Qual a faixa de pessoas?")
        pilha.empilhar(ctx_pergunta, "quantidade", "Quantas unidades você precisa?")

        asyncio.run(pilha.resolver_resposta(_ctx(db_session, atendimento, "50", leva=_LEVA + 1)))
        anotado = asyncio.run(pilha.resolver_resposta(_ctx(db_session, atendimento, "50", leva=_LEVA + 2)))
        assert anotado.template_usado == "PILHA_ANOTADO+PILHA_PERGUNTA"
        assert anotado.mensagens() == ["Anotado! 👍\n\nQuantas unidades você precisa?"]
        assert _valor(atendimento, "faixa_funcionarios") == "50"

        # A última da fila: grava e devolve o turno ao fluxo normal.
        assert asyncio.run(pilha.resolver_resposta(_ctx(db_session, atendimento, "3", leva=_LEVA + 3))) is None
        assert _valor(atendimento, "quantidade") == "3"
        assert pilha.fila_serial(atendimento) == []
    finally:
        _limpar(db_session, telefone)


def test_reply_to_desempata_sem_fila_serial(db_session):
    telefone = "+5511999977305"
    try:
        atendimento = _atendimento_catraca(db_session, telefone)
        ctx_pergunta = _ctx(db_session, atendimento, leva=_LEVA)
        faixa = pilha.empilhar(ctx_pergunta, "faixa_funcionarios", "Qual a faixa de pessoas?")
        quantidade = pilha.empilhar(ctx_pergunta, "quantidade", "Quantas unidades você precisa?")
        faixa.mensagens_ids = [111]
        quantidade.mensagens_ids = [222]

        resposta = asyncio.run(pilha.resolver_resposta(_ctx(db_session, atendimento, "3", leva=_LEVA + 1, citada=222)))
        assert resposta is None
        assert _valor(atendimento, "quantidade") == "3"
        assert _abertas(atendimento) == ["modelo_produto", "faixa_funcionarios"]
    finally:
        _limpar(db_session, telefone)


def test_reply_to_nao_dispensa_a_validacao(db_session):
    """Citar a pergunta é evidência de qual pergunta, não de que a mensagem a responde."""
    telefone = "+5511999977306"
    try:
        atendimento = _atendimento_catraca(db_session, telefone)
        quantidade = pilha.empilhar(_ctx(db_session, atendimento, leva=_LEVA), "quantidade", "Quantas unidades?")
        quantidade.mensagens_ids = [222]

        ctx = _ctx(db_session, atendimento, "e qual o preço?", intencoes=(Intencao.PERGUNTAR_PRECO,), citada=222)
        assert asyncio.run(pilha.resolver_resposta(ctx)) is None
        assert quantidade.aberta
    finally:
        _limpar(db_session, telefone)


def test_resposta_ambigua_so_casa_com_o_topo(db_session):
    """"sim" responde à pergunta do turno mais recente, não a uma mais antiga."""
    telefone = "+5511999977307"
    try:
        atendimento = _atendimento_catraca(db_session, telefone)
        pilha.empilhar(_ctx(db_session, atendimento, leva=_LEVA), "interesse_sistema_nuvem", "Têm interesse?")
        pilha.empilhar(_ctx(db_session, atendimento, leva=_LEVA + 1), "quantidade", "Quantas unidades?")

        ctx = _ctx(db_session, atendimento, "sim", intencoes=(Intencao.CONFIRMAR,), leva=_LEVA + 2)
        assert asyncio.run(pilha.resolver_resposta(ctx)) is None
        assert _valor(atendimento, "interesse_sistema_nuvem") is None
    finally:
        _limpar(db_session, telefone)


def test_encerrar_atendimento_descarta_a_pilha(db_session):
    telefone = "+5511999977308"
    try:
        atendimento = _atendimento_catraca(db_session, telefone)
        assert pilha.abertas(atendimento)
        atendimentos_svc.encerrar_atendimento(
            db_session, atendimento, motivo=MotivoEncerramento.CONCLUIDO_PELO_CLIENTE, ator="teste"
        )
        db_session.refresh(atendimento)
        assert pilha.abertas(atendimento) == []
        assert {p.status for p in atendimento.perguntas_pendentes} == {StatusPergunta.DESCARTADA.value}
    finally:
        _limpar(db_session, telefone)


# ----------------------------------------------------------------------
# Ponta a ponta: a pergunta sabe em que mensagem foi
# ----------------------------------------------------------------------


def test_pergunta_vinculada_a_mensagem_que_a_levou_e_capturada_pelo_reply_to(db_session):
    telefone = "+5511999977309"
    try:
        processador = ProcessadorMensagem()
        primeiro = asyncio.run(
            processador.processar(
                db_session, telefone, "Bom dia, gostaria de informações sobre relógio de ponto.", nome_perfil="Bob Figu"
            )
        )
        db_session.commit()
        saidas = (
            db_session.query(Mensagem)
            .filter(Mensagem.id.in_(primeiro.mensagens_saida_ids))
            .order_by(Mensagem.id)
            .all()
        )
        pergunta_faixa = next(m for m in saidas if "faixa de pessoas" in m.conteudo)

        atendimento = db_session.get(Atendimento, primeiro.atendimento_id)
        faixa = next(p for p in pilha.abertas(atendimento) if p.chave == "faixa_funcionarios")
        assert faixa.mensagens_ids == [pergunta_faixa.id]

        asyncio.run(processador.processar(db_session, telefone, "80", responde_a_mensagem_id=pergunta_faixa.id))
        db_session.commit()
        db_session.refresh(atendimento)
        assert atendimento.valores_capturados().get("faixa_funcionarios") == "80"
        assert faixa.status == StatusPergunta.RESPONDIDA.value
    finally:
        _limpar(db_session, telefone)


def test_mensagem_de_saida_da_pergunta_e_do_proprio_telefone(db_session):
    """Sanidade do vínculo: só mensagens de saída do turno entram."""
    telefone = "+5511999977310"
    try:
        resultado = asyncio.run(ProcessadorMensagem().processar(db_session, telefone, "Quero orçamento de catraca"))
        db_session.commit()
        atendimento = db_session.get(Atendimento, resultado.atendimento_id)
        (modelo,) = pilha.abertas(atendimento)
        (msg,) = db_session.query(Mensagem).filter(Mensagem.id.in_(modelo.mensagens_ids)).all()
        assert msg.origem == OrigemMensagem.SYSTEM and msg.telefone.endswith("77310")
    finally:
        _limpar(db_session, telefone)


def test_modelo_resolvido_nao_e_perguntado_de_novo_no_mesmo_turno(db_session):
    """Regressão achada no smoke test da pilha: o item criado ao resolver o modelo não
    aparecia na coleção já carregada, e o bot perguntava de novo o modelo que acabara de
    resolver. O código antigo mascarava isso no turno seguinte, lendo a resposta do
    cliente contra uma pergunta (software) que nunca tinha feito."""
    from models import Modelo, Produto
    from services.identificador import ResultadoIdentificacao, StatusIdentificacao

    from tests.test_processador_finalizando_coleta_ativa import _iniciar_finalizando_com_software

    telefone = "+5511999977311"
    produto = Produto(descricao="Relógio de Ponto (teste pilha)", ativo=True)
    db_session.add(produto)
    db_session.flush()
    modelo = Modelo(
        produto_id=produto.id, codigo="TESTE-PILHA-001", descricao="Modelo teste pilha",
        marca="MarcaTestePilha", preco_tabela=0, ativo=True,
    )
    db_session.add(modelo)
    db_session.commit()
    try:
        processador = ProcessadorMensagem()
        contato = _iniciar_finalizando_com_software(db_session, processador, telefone)
        identificacao = ResultadoIdentificacao(status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[])
        resultado = ResultadoClassificacao(
            intencoes=[Intencao.DESCONHECIDO],
            confianca=0.9,
            confianca_nivel=NivelConfianca.ALTA,
            entidades=EntidadesExtraidas(marca="MarcaTestePilha"),
            origem="regra",
        )
        resposta = asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="MarcaTestePilha",
                identificacao=identificacao, resultado_class=resultado,
            )
        )
        assert resposta.template_usado == "PEDIR_SOFTWARE_PONTO"
        atendimento = contato.atendimentos[0]
        assert _abertas(atendimento) == ["software_controle_ponto"]
    finally:
        _limpar(db_session, telefone)
        db_session.delete(modelo)
        db_session.delete(produto)
        db_session.commit()


# ----------------------------------------------------------------------
# Passo 2: perguntas fora do catálogo (nome de perfil, "conhece?", data de nascimento)
# ----------------------------------------------------------------------

_SAUDACAO_RELOGIO = "Bom dia, gostaria de informações sobre relógio de ponto."


class _Conversa:
    """Conversa pelo `processar()` com nome de perfil, como chega do WhatsApp."""

    def __init__(self, db_session, telefone):
        self.db = db_session
        self.telefone = telefone
        self.processador = ProcessadorMensagem()
        self.ultimo = None

    def diz(self, texto, citando=None):
        self.ultimo = asyncio.run(
            self.processador.processar(
                self.db, self.telefone, texto, nome_perfil="Bob Figu", responde_a_mensagem_id=citando
            )
        )
        self.db.commit()
        return self.ultimo

    @property
    def atendimento(self):
        atendimento = self.db.get(Atendimento, self.ultimo.atendimento_id)
        self.db.refresh(atendimento)
        return atendimento

    def info(self, chave):
        return self.atendimento.valores_capturados().get(chave)


def test_perguntas_da_leva_entram_na_ordem_de_leitura_e_cada_uma_na_sua_mensagem(db_session):
    telefone = "+5511999977320"
    try:
        conversa = _Conversa(db_session, telefone)
        primeiro = conversa.diz(_SAUDACAO_RELOGIO)
        perguntas = pilha.abertas(conversa.atendimento)
        assert [p.chave for p in perguntas] == ["nome_perfil", "conhece_marcas", "faixa_funcionarios"]
        assert [p.mensagens_ids for p in perguntas] == [[i] for i in primeiro.mensagens_saida_ids]
    finally:
        _limpar(db_session, telefone)


def test_sim_solto_com_tres_perguntas_abertas_vai_para_a_fila_serial(db_session):
    """O caso que motivou a pilha: "sim" serve para o nome e para "conhece?". Decisão do
    Beto (05/10): descartar e retomar uma por uma, na ordem de leitura."""
    telefone = "+5511999977321"
    try:
        conversa = _Conversa(db_session, telefone)
        conversa.diz(_SAUDACAO_RELOGIO)

        confuso = conversa.diz("sim")
        assert confuso.partes_resposta == [
            "Fiquei confuso, não sei a qual das perguntas você respondeu. "
            "Vamos retomar uma por uma: Posso te chamar de Bob Figu, ou seu nome é outro?"
        ]
        assert conversa.info("nome_perfil_confirmacao") == "aguardando"

        nome = conversa.diz("sim")
        assert nome.partes_resposta == ["Combinado, Bob Figu! 😊\n\nVocê conhece esses relógios?"]
        assert conversa.info("nome_perfil_confirmacao") == "confirmado"

        conhece = conversa.diz("não")
        assert conhece.partes_resposta == ["Anotado! 👍\n\nQual a faixa de pessoas que vão usar o relógio de ponto?"]
        assert conversa.info("conhece_marcas") == "não"

        conversa.diz("30")
        assert conversa.info("faixa_funcionarios") == "30"
        assert pilha.fila_serial(conversa.atendimento) == []
    finally:
        _limpar(db_session, telefone)


def test_responder_citando_a_pergunta_tira_a_ambiguidade(db_session):
    telefone = "+5511999977322"
    try:
        conversa = _Conversa(db_session, telefone)
        _, msg_conhece, _ = conversa.diz(_SAUDACAO_RELOGIO).mensagens_saida_ids

        resposta = conversa.diz("sim", citando=msg_conhece)
        assert "Fiquei confuso" not in " ".join(resposta.partes_resposta)
        assert conversa.info("conhece_marcas") == "sim"
        # O nome não foi respondido, e o "sim" não foi para ele.
        assert conversa.info("nome_perfil_confirmacao") == "aguardando"
    finally:
        _limpar(db_session, telefone)


def test_citar_a_pergunta_errada_cai_na_resolucao_normal(db_session):
    telefone = "+5511999977323"
    try:
        conversa = _Conversa(db_session, telefone)
        _, _, msg_faixa = conversa.diz(_SAUDACAO_RELOGIO).mensagens_saida_ids

        conversa.diz("Carlos", citando=msg_faixa)
        assert conversa.info("nome_perfil_confirmacao") == "outro_nome"
        assert conversa.info("faixa_funcionarios") is None
    finally:
        _limpar(db_session, telefone)


def test_sim_que_tambem_serviria_a_outra_pergunta_nao_fica_com_o_nome(db_session):
    """"sim, 30": o "sim" pode ser do nome ou do "conhece?". Ambíguo, então fila serial,
    com o nome nela (e não confirmado por adivinhação)."""
    telefone = "+5511999977324"
    try:
        conversa = _Conversa(db_session, telefone)
        conversa.diz(_SAUDACAO_RELOGIO)
        conversa.diz("sim, 30")
        assert conversa.info("nome_perfil_confirmacao") == "aguardando"
        assert [p.chave for p in pilha.fila_serial(conversa.atendimento)][0] == "nome_perfil"
    finally:
        _limpar(db_session, telefone)


def test_sim_na_frente_de_outra_resposta_confirma_o_nome_e_deixa_o_resto(db_session):
    """Sem outra pergunta que aceite o "sim", ele é do nome, e o resto da mensagem
    responde à outra pergunta."""
    telefone = "+5511999977325"
    try:
        atendimento = _atendimento_catraca(db_session, telefone)
        pilha.descartar_todas(atendimento)
        ctx_pergunta = _ctx(db_session, atendimento, leva=_LEVA)
        from services.conversacao.confirmacao_nome_perfil import registrar_pergunta

        registrar_pergunta(ctx_pergunta, "Bob Figu")
        pilha.empilhar(ctx_pergunta, "quantidade", "Quantas unidades você precisa?")

        asyncio.run(pilha.resolver_resposta(_ctx(db_session, atendimento, "sim, 3", leva=_LEVA + 1)))
        assert _valor(atendimento, "nome_perfil_confirmacao") == "confirmado"
        assert _valor(atendimento, "quantidade") == "3"
        assert pilha.abertas(atendimento) == []
    finally:
        _limpar(db_session, telefone)


def test_nao_ao_nome_reabre_a_pergunta_como_pedido_de_nome(db_session):
    telefone = "+5511999977326"
    try:
        conversa = _Conversa(db_session, telefone)
        conversa.diz("Quero orçamento de relógio de ponto")
        resposta = conversa.diz("não")
        assert resposta.partes_resposta == ["Como posso te chamar? 😊"]
        (nome,) = [p for p in pilha.abertas(conversa.atendimento) if p.chave == "nome_perfil"]
        assert nome.texto == "Como posso te chamar?"

        conversa.diz("Roberto")
        assert conversa.info("nome_perfil_confirmacao") == "outro_nome"
    finally:
        _limpar(db_session, telefone)
