"""Regressão: `ProcessamentoMensagem.fase_atendimento` deve guardar um snapshot da fase
*no momento em que a mensagem foi analisada* (pré-decisão) — não a fase atual do
atendimento, que pode já ter mudado por causa da própria mensagem (ex.: a transição
Esclarecendo → Finalizando acontece dentro de `_decidir_resposta`, depois do snapshot).
"""

from database import Database
from models import FaseAtendimento
from services import atendimentos as atendimentos_svc
from services.classificador import EntidadesExtraidas, Intencao, NivelConfianca, ResultadoClassificacao
from services.dev_limpeza_telefone import apagar_dados_telefone
from services.identificador import ResultadoIdentificacao, StatusIdentificacao, criar_contato_sem_empresa
from services.processador import ProcessadorMensagem
from services.respostas import RespostaGerada


def test_fase_atendimento_usa_snapshot_pre_decisao_nao_a_fase_atual():
    telefone = "5511999983002"
    database = Database()
    with database.get_session() as db:
        try:
            contato = criar_contato_sem_empresa(db, telefone, nome="Teste fase snapshot")
            atendimento = atendimentos_svc.obter_ou_criar_atendimento(db, contato)

            # Simula a mesma mensagem tendo disparado a transição Esclarecendo → Finalizando
            # DEPOIS do snapshot pré-decisão ser capturado.
            atendimento.fase = FaseAtendimento.FINALIZANDO
            db.commit()

            processador = ProcessadorMensagem()
            resultado_class = ResultadoClassificacao(
                intencoes=[Intencao.PEDIR_ORCAMENTO],
                confianca=0.9,
                confianca_nivel=NivelConfianca.ALTA,
                entidades=EntidadesExtraidas(),
                origem="regra",
            )
            identificacao = ResultadoIdentificacao(
                status=StatusIdentificacao.SEM_EMPRESA, contatos=[contato], empresas=[]
            )
            resposta = RespostaGerada(texto="ok", template_usado="TESTE")

            proc = processador._criar_processamento(
                db=db,
                resultado_class=resultado_class,
                identificacao=identificacao,
                contato_atual=contato,
                empresa_atual=None,
                atendimento_atual=atendimento,  # já em finalizando "depois" da decisão
                resposta=resposta,
                duracao_ms=1,
                fase_pre_decisao=FaseAtendimento.ESCLARECENDO,  # snapshot "antes"
            )

            assert proc.fase_atendimento == FaseAtendimento.ESCLARECENDO.value
            assert proc.to_dict()["fase_atendimento"] == FaseAtendimento.ESCLARECENDO.value
            assert proc.intencao == Intencao.PEDIR_ORCAMENTO.value
            assert proc.intencoes == [Intencao.PEDIR_ORCAMENTO.value]
            # a fase atual do atendimento já mudou — confirma que não é isso que foi lido
            assert atendimento.fase == FaseAtendimento.FINALIZANDO
        finally:
            db.commit()
            apagar_dados_telefone(db, telefone)
            db.commit()


def test_fase_atendimento_none_quando_nao_havia_atendimento_ainda():
    telefone = "5511999983003"
    database = Database()
    with database.get_session() as db:
        try:
            contato = criar_contato_sem_empresa(db, telefone, nome="Teste sem atendimento")

            processador = ProcessadorMensagem()
            resultado_class = ResultadoClassificacao(
                intencoes=[Intencao.SAUDACAO],
                confianca=0.75,
                confianca_nivel=NivelConfianca.MEDIA,
                entidades=EntidadesExtraidas(),
                origem="regra",
            )
            identificacao = ResultadoIdentificacao(status=StatusIdentificacao.NOVO, contatos=[], empresas=[])
            resposta = RespostaGerada(texto="ok", template_usado="TESTE")

            proc = processador._criar_processamento(
                db=db,
                resultado_class=resultado_class,
                identificacao=identificacao,
                contato_atual=contato,
                empresa_atual=None,
                atendimento_atual=None,
                resposta=resposta,
                duracao_ms=1,
                fase_pre_decisao=None,
            )

            assert proc.fase_atendimento is None
        finally:
            db.commit()
            apagar_dados_telefone(db, telefone)
            db.commit()
