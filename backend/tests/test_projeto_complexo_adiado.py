"""Projeto complexo adiado, pedido de documento e o caso do +5519991931173 (05/10).

Na conversa real: o cliente respondeu "45" à faixa de pessoas, o classificador leu o
número também como quantidade de equipamentos, a regra de projeto complexo transferiu na
hora, e o software de ponto e o CPF/CNPJ nunca chegaram a ser perguntados. Decisões do
Beto: a transferência por projeto complexo espera cada pendência ser perguntada uma vez;
o documento é pedido no início, junto com o nome, e uma vez mais só no Finalizando.
"""

import asyncio
from types import SimpleNamespace

import pytest
from database import Database
from models import Atendimento, Escalonamento, GatilhoEscalonamento, Modelo, ModoExecucao, ModoOperacao, Produto
from services.classificador import EntidadesExtraidas
from services.conversacao import pilha
from services.conversacao.projeto_complexo import gatilhos
from services.conversacao.tratadores import Conhece, entrada_de
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.parametro_service import ParametroService
from services.processador import ProcessadorMensagem

_SAUDACAO_RELOGIO = "Bom dia, gostaria de informações sobre relógio de ponto."
_PEDE_DOCUMENTO = "poderia me informar o CNPJ da sua empresa ou seu CPF?"


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


class _Conversa:
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
    def texto(self):
        return "\n\n".join(self.ultimo.partes_resposta)

    @property
    def atendimento(self):
        atendimento = self.db.get(Atendimento, self.ultimo.atendimento_id)
        self.db.refresh(atendimento)
        return atendimento


# ----------------------------------------------------------------------
# Unidade
# ----------------------------------------------------------------------


def _captura(chave, valor):
    return SimpleNamespace(pergunta=SimpleNamespace(chave=chave), leitura=SimpleNamespace(valor=valor))


def test_numero_que_respondia_a_faixa_nao_vira_quantidade():
    entidades = EntidadesExtraidas(quantidades=[45])
    assert gatilhos(entidades, 50) == [GatilhoEscalonamento.QUANTIDADE_MINIMA]
    assert gatilhos(entidades, 50, _captura("faixa_funcionarios", "45")) == []


def test_faixa_capturada_pela_pilha_conta_para_o_limiar():
    """Um "80" solto respondendo à faixa escapava do gatilho: o classificador só lê faixa
    com palavra-chave ("80 funcionários")."""
    assert gatilhos(EntidadesExtraidas(), 50, _captura("faixa_funcionarios", "80")) == [
        GatilhoEscalonamento.FAIXA_FUNCIONARIOS
    ]


def test_quantidade_capturada_continua_quantidade():
    entidades = EntidadesExtraidas(quantidades=[5])
    assert gatilhos(entidades, 50, _captura("quantidade", "5")) == [GatilhoEscalonamento.QUANTIDADE_MINIMA]


@pytest.mark.parametrize(
    "texto, marca, esperado",
    [
        ("Conheço o Topdata, gosto dele.", "Topdata", "sim"),
        ("conheço sim", None, "sim"),
        ("não conheço", None, "não"),
        ("gosto muito da Control-ID", "Control-ID", "sim"),
    ],
)
def test_conhece_le_o_verbo_e_a_marca(texto, marca, esperado):
    leitura = Conhece().interpretar(entrada_de(texto, (), EntidadesExtraidas(marca=marca)))
    assert leitura.valor == esperado
    assert leitura.discriminante is True


# ----------------------------------------------------------------------
# Ponta a ponta
# ----------------------------------------------------------------------


def test_documento_pedido_no_inicio_junto_com_o_nome(db_session):
    telefone = "+5511999977401"
    try:
        conversa = _Conversa(db_session, telefone)
        partes = conversa.diz(_SAUDACAO_RELOGIO).partes_resposta
        assert partes[0].endswith("Posso te chamar assim ou seu nome é outro?")
        assert partes[1] == f"Para te atender melhor, {_PEDE_DOCUMENTO}"
    finally:
        _limpar(db_session, telefone)


def test_conheco_responde_mesmo_fora_do_topo(db_session):
    telefone = "+5511999977402"
    try:
        conversa = _Conversa(db_session, telefone)
        conversa.diz(_SAUDACAO_RELOGIO)
        conversa.diz("sim, pode chamar assim")  # nova leva: a faixa volta para o topo
        conversa.diz("Conheço o Topdata, gosto dele.")
        assert conversa.atendimento.valores_capturados().get("conhece_marcas") == "sim"
    finally:
        _limpar(db_session, telefone)


def test_caso_45_nao_transfere_e_segue_a_coleta(db_session):
    telefone = "+5511999977403"
    try:
        conversa = _Conversa(db_session, telefone)
        conversa.diz(_SAUDACAO_RELOGIO)
        conversa.diz("Sim, pode chamar assim.")
        conversa.diz("45")
        atendimento = conversa.atendimento
        assert atendimento.modo_operacao == ModoOperacao.AGENTE
        assert atendimento.valores_capturados().get("faixa_funcionarios") == "45"
        assert "cartográfico ou eletrônico" in conversa.texto
    finally:
        _limpar(db_session, telefone)


def test_projeto_complexo_espera_cada_pendencia_ser_perguntada_uma_vez(db_session):
    """Faixa 80 (>= 50) → transferência adiada: pergunta o que nunca foi perguntado
    (modelo, software de ponto), pede o documento de novo, e só então transfere. O que
    já foi perguntado ("Você conhece?") não se repete."""
    telefone = "+5511999977404"
    try:
        conversa = _Conversa(db_session, telefone)
        conversa.diz(_SAUDACAO_RELOGIO)
        conversa.diz("Sim, pode chamar assim.")

        conversa.diz("80")
        assert conversa.atendimento.modo_operacao == ModoOperacao.AGENTE
        assert "cartográfico ou eletrônico" in conversa.texto

        conversa.diz("ainda não sei")
        assert "software de ponto" in conversa.texto

        conversa.diz("nenhum")
        assert _PEDE_DOCUMENTO_NF in conversa.texto  # o da nota, antes de transferir

        conversa.diz("prefiro não passar")
        assert "análise mais detalhada" in conversa.texto
        atendimento = conversa.atendimento
        assert atendimento.modo_operacao == ModoOperacao.HUMANO
        (escalonamento,) = db_session.query(Escalonamento).filter_by(atendimento_id=atendimento.id).all()
        assert escalonamento.gatilhos == [GatilhoEscalonamento.FAIXA_FUNCIONARIOS.value]
        assert escalonamento.evidencias["adiado_ate_fim_da_coleta"] is True
        assert "conhece_marcas" in [p.chave for p in pilha.abertas(atendimento)]
    finally:
        _limpar(db_session, telefone)


_PEDE_DOCUMENTO_NF = "Para a nota fiscal: ela sai no CNPJ da empresa ou no seu CPF?"
_CONFIRMA_CPF_NF = "A nota fiscal sai no CPF que você me informou, certo?"
# CPF e CNPJ sintéticos válidos (passam no dígito verificador), sem relação com pessoa ou
# empresa real.
_CPF_SINTETICO, _CPF_SINTETICO_FORMATADO = "11144477735", "111.444.777-35"
_CNPJ_SINTETICO = "11.222.333/0001-81"


def test_documento_da_nota_pedido_uma_vez_no_finalizando(db_session):
    """Sem documento dado no início, o Finalizando pergunta o da nota fiscal uma vez, antes
    do resumo; sem resposta, o resumo segue."""
    telefone = "+5511999977405"
    try:
        conversa = _Conversa(db_session, telefone)
        conversa.diz("Quero orçamento de relógio de ponto, já uso o Domínio")
        assert _PEDE_DOCUMENTO in conversa.texto

        conversa.diz("biometria")
        assert _PEDE_DOCUMENTO_NF in conversa.texto  # o modelo resolveu: pergunta da nota

        conversa.diz("não quero passar")
        assert "resumo" in conversa.texto
    finally:
        _limpar(db_session, telefone)


def _apagar_pessoa(db_session):
    from models import Pessoa

    db_session.query(Pessoa).filter_by(cpf=_CPF_SINTETICO_FORMATADO).delete()
    db_session.commit()


def test_cpf_do_inicio_e_confirmado_como_documento_da_nota(db_session):
    """CPF dado no início: sem data de nascimento, é anotado na hora, e o Finalizando só
    confirma que a nota sai nele."""
    telefone = "+5511999977407"
    _apagar_pessoa(db_session)
    try:
        conversa = _Conversa(db_session, telefone)
        conversa.diz("Quero orçamento de relógio de ponto, já uso o Domínio")
        conversa.diz(f"meu cpf é {_CPF_SINTETICO}")
        assert conversa.texto.startswith("Anotei seu CPF.")
        assert "nascimento" not in conversa.texto
        assert conversa.atendimento.pessoa.data_nascimento is None

        conversa.diz("biometria")
        assert _CONFIRMA_CPF_NF in conversa.texto
        assert _CPF_SINTETICO not in conversa.texto  # o CPF não é ecoado (REQ-005)

        conversa.diz("sim")
        assert "resumo" in conversa.texto
        assert conversa.atendimento.tipo_documento.value == "cpf"
    finally:
        _limpar(db_session, telefone)
        _apagar_pessoa(db_session)


def test_outro_documento_na_resposta_vira_o_da_nota(db_session):
    """O cliente diz que a nota não sai no CPF do início: "não" sem documento pede o da
    nota (uma vez); o CNPJ que chega passa a ser o documento do atendimento."""
    from models import Empresa

    telefone = "+5511999977408"
    _apagar_pessoa(db_session)
    empresa = db_session.query(Empresa).filter_by(cnpj=_CNPJ_SINTETICO).first()
    criou_empresa = empresa is None
    if criou_empresa:
        empresa = Empresa(cnpj=_CNPJ_SINTETICO, nome="Empresa Teste NF")
        db_session.add(empresa)
        db_session.commit()
    try:
        conversa = _Conversa(db_session, telefone)
        conversa.diz("Quero orçamento de relógio de ponto, já uso o Domínio")
        conversa.diz(f"meu cpf é {_CPF_SINTETICO}")
        conversa.diz("biometria")
        assert _CONFIRMA_CPF_NF in conversa.texto

        conversa.diz("não")
        assert _PEDE_DOCUMENTO_NF in conversa.texto

        conversa.diz(f"é no CNPJ {_CNPJ_SINTETICO}")
        assert "resumo" in conversa.texto
        atendimento = conversa.atendimento
        assert atendimento.tipo_documento.value == "cnpj"
        assert atendimento.empresa_id == empresa.id
    finally:
        _limpar(db_session, telefone)
        _apagar_pessoa(db_session)
        if criou_empresa:
            db_session.query(Empresa).filter_by(cnpj=_CNPJ_SINTETICO).delete()
            db_session.commit()


def test_modelo_resolve_com_outros_dados_ja_coletados(db_session):
    """Regressão: toda chave de `AtendimentoInfo` virava filtro de atributo do catálogo
    (`faixa_funcionarios=45` incluída) e nenhum modelo casava. Só chaves que existem como
    atributo no catálogo filtram."""
    from tests.test_processador_finalizando_coleta_ativa import _iniciar_finalizando_com_software

    telefone = "+5511999977406"
    produto = Produto(descricao="Relógio de Ponto (teste filtro)", ativo=True)
    db_session.add(produto)
    db_session.flush()
    modelo = Modelo(
        produto_id=produto.id, codigo="TESTE-FILTRO-001", descricao="Modelo teste filtro",
        marca="MarcaTesteFiltro", preco_tabela=0, ativo=True,
    )
    db_session.add(modelo)
    db_session.commit()
    try:
        processador = ProcessadorMensagem()
        contato = _iniciar_finalizando_com_software(db_session, processador, telefone)
        atendimento = contato.atendimentos[0]
        processador._salvar_info_atendimento(db_session, atendimento.id, "faixa_funcionarios", "45")
        db_session.commit()

        from services.classificador import Intencao, NivelConfianca, ResultadoClassificacao
        from services.identificador import ResultadoIdentificacao, StatusIdentificacao

        resultado = ResultadoClassificacao(
            intencoes=[Intencao.DESCONHECIDO], confianca=0.9, confianca_nivel=NivelConfianca.ALTA,
            entidades=EntidadesExtraidas(marca="MarcaTesteFiltro"), origem="regra",
        )
        asyncio.run(
            processador._decidir_resposta(
                db=db_session, telefone=telefone, conteudo="MarcaTesteFiltro",
                identificacao=ResultadoIdentificacao(
                    status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[]
                ),
                resultado_class=resultado,
            )
        )
        assert atendimento.modelo_ja_resolvido()
    finally:
        _limpar(db_session, telefone)
        db_session.delete(modelo)
        db_session.delete(produto)
        db_session.commit()
