"""
Orquestrador principal - processa mensagens recebidas do cliente.

Fluxo:
1. Salva mensagem recebida
2. Identifica contato/empresa pelo telefone
3. Carrega/cria atendimento ativo
4. Classifica intenção + extrai entidades
5. Atualiza estado (CNPJ, nome, itens, etc.)
6. Gera resposta
7. Salva resposta
"""

import logging
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from config import settings
from models import (
    Atendimento,
    AtendimentoInfo,
    Contato,
    Empresa,
    FaseAtendimento,
    Mensagem,
    ModoExecucao,
    ModoOperacao,
    MotivoEncerramento,
    MotivoEscalonamento,
    OrigemClassificacao,
    OrigemInfo,
    OrigemMensagem,
    Pessoa,
    ProcessamentoMensagem,
    StatusAtendimento,
    TipoEventoAtendimento,
    User,
)
from sqlalchemy.orm import Session
from utils.datetime_utils import utc_now

from services import atendimentos as atendimentos_svc
from services.classificador import NivelConfianca, ResultadoClassificacao, classificar
from services.cnpj import ConsultaCnpjError, obter_ou_criar_empresa
from services.cnpj.receitaws import validar_cnpj
from services.conversacao.acoes import ContextoAcao
from services.conversacao.campos_pendentes import campos_pendentes
from services.conversacao.catalogo_campos import (
    CAMPO_FAIXA_FUNCIONARIOS,
    CAMPO_HOMOLOGADO_SOFTWARE,
    CAMPO_INTERESSE_SISTEMA_NUVEM,
    CAMPO_QUANTIDADE,
    CAMPO_SOFTWARE_ACESSO,
    CAMPO_SOFTWARE_PONTO,
)
from services.conversacao.motor import resolver_e_executar
from services.conversacao.regras_esclarecendo import REGISTRO_ESCLARECENDO
from services.conversacao.regras_finalizando import REGISTRO_FINALIZANDO
from services.conversacao.regras_globais import REGRAS_GLOBAIS
from services.cpf.persistencia import obter_ou_criar_pessoa
from services.cpf.validacao import mascarar_cpf, parse_data_nascimento, validar_cpf
from services.debug_log import DebugLogger
from services.identificador import (
    ResultadoIdentificacao,
    StatusIdentificacao,
    criar_contato,
    criar_contato_sem_empresa,
    identificar_por_telefone,
    normalizar_telefone,
    vincular_empresa_ao_contato,
)
from services.llm import LLMProvider
from services.parametro_service import ParametroService
from services.rag import BuscadorQA, BuscadorRag, QAServiceNulo, RetrievalServiceNulo
from services.respostas import GeradorRespostas, MensagemId, RespostaGerada

logger = logging.getLogger(__name__)


# Intencoes que disparam busca na RAG. PERGUNTAR_PRECO esta presente para que possamos registrar os trechos
# relacionados em auditoria, mas a resposta continua sendo o template padrao de encaminhamento para orcamento humano.
# Motor Intenção×Fase→Ações: registro de Regras por Fase efetiva do atendimento.
# `EM_ORCAMENTACAO` não precisa de entrada — `modo_operacao` já vira HUMANO junto com a
# transição (`FinalizandoState.concluir`), e o nível acima (`processar()`) já suprime a
# geração de resposta nesse modo antes de `_decidir_resposta` ser chamado.
# Ver `docs/arquitetura_motor_conversacao_2026-07.md` para o funcionamento geral do motor.
REGISTRO_POR_FASE = {
    FaseAtendimento.ESCLARECENDO: REGISTRO_ESCLARECENDO,
    FaseAtendimento.FINALIZANDO: REGISTRO_FINALIZANDO,
}

# REQ-016.7/016.9: continuação de atendimento encerrado. Chaves de `AtendimentoInfo`
# gravadas no atendimento ENCERRADO (não no novo) enquanto se aguarda a resposta do
# cliente às perguntas PERG-016-009/009B.
_CONTINUACAO_PENDENTE_CHAVE = "continuacao_atendimento_pendente"
_CONFIRMAR_INTERESSE_PENDENTE_CHAVE = "confirmar_interesse_pendente"

# REQ-003.7: quando a RAG/QA não encontram conteúdo para uma dúvida de produto, marca que
# já fizemos a 1 pergunta de clarificação permitida — se a resposta a ela ainda não tiver
# base, escala para humano em vez de insistir de novo (mesmo padrão de "1 tentativa extra,
# depois escala" usado por `FinalizandoState._resolver_modelo`, mas booleano: no máximo 1
# tentativa extra, não N).
_RAG_CLARIFICACAO_PENDENTE_CHAVE = "rag_clarificacao_pendente"

# REQ-004.9 (Fase 5): confiança baixa do classificador 2x seguidas sem nada resolver
# escala para humano — mesmo padrão de "1 tentativa extra, depois escala" acima.
_CONFIANCA_BAIXA_TENTATIVA_CHAVE = "confianca_baixa_tentativas"

# REQ-003.11: tipos de produto com catálogo próprio, e o nome do Parametro (tabela
# `parametros`) que guarda o link público correspondente — configurável sem deploy.
_CATALOGO_TIPOS_LABEL = {
    "catraca": "catracas",
    "relogio_ponto": "relógios de ponto",
    "cancela": "cancelas",
    "leitor_facial": "leitores faciais",
    "leitor_biometrico": "leitores biométricos",
    "camera": "câmeras",
    "controle_de_acesso": "controles de acesso",
    "controle_por_cartao": "controles por cartão",
    "bastao_de_ronda": "bastões de ronda",
    "roteador": "roteadores",
}

_CATALOGO_PARAM_POR_TIPO = {
    "catraca": "catalogo_link_catraca",
    "relogio_ponto": "catalogo_link_relogio_ponto",
}

_REGEX_CONTINUAR_ATENDIMENTO = re.compile(r"\b(1|continuar|continua|de\s+onde\s+paramos)\b", re.IGNORECASE)
_REGEX_NOVO_PEDIDO = re.compile(r"\b(2|novo|outro|outra\s+coisa|pedido\s+novo)\b", re.IGNORECASE)
_REGEX_MUDOU_DE_IDEIA = re.compile(
    r"\b(mudei|mudou\s+de\s+ideia|outra\s+coisa|outro\s+produto|n[aã]o\s+[eé]\s+mais\s+isso)\b",
    re.IGNORECASE,
)
_REGEX_MANTEM_INTERESSE = re.compile(
    r"\b(sim|isso\s+mesmo|continua|quero\s+isso|mant[eé]m|pode\s+seguir|confirmo)\b",
    re.IGNORECASE,
)

# REQ-011.16: nome do `User` sentinela usado para marcar mensagens auto-enviadas em
# `execucao_normal` como já decididas (ver `_obter_user_sistema`).
_USER_SISTEMA_NOME = "Sistema (execução automática)"


def _dentro_da_janela(momento: Optional[datetime], horas: int) -> bool:
    """REQ-016.7: `momento` ausente é tratado como fora da janela (mais conservador —
    presume novo pedido em vez de reabrir silenciosamente algo sem histórico de tempo)."""
    if momento is None:
        return False
    return (utc_now() - momento) <= timedelta(hours=horas)


@dataclass
class ResultadoProcessamento:
    """Resultado do processamento de uma mensagem."""

    resposta: str
    contato_id: Optional[int] = None
    atendimento_id: Optional[int] = None
    processamento_id: Optional[int] = None
    intencao: Optional[str] = None
    origem_classificacao: Optional[str] = None


class ProcessadorMensagem:
    """Orquestrador central do cérebro do assistente."""

    def __init__(
        self,
        llm: Optional[LLMProvider] = None,
        retrieval: Optional[BuscadorRag] = None,
        qa: Optional[BuscadorQA] = None,
    ):
        self._llm = llm
        self._gerador = GeradorRespostas(llm=llm, usar_llm=llm is not None)
        self._retrieval: BuscadorRag = retrieval or RetrievalServiceNulo()
        if retrieval is None and settings.RAG_ENABLED:
            try:
                from services.rag import get_retrieval_service

                self._retrieval = get_retrieval_service()
                logger.info("[Processador] RetrievalService inicializado para RAG")
            except Exception as e:
                # Erro comum: EMBEDDING_API_KEY nao configurada em dev.
                logger.warning(
                    "[Processador] RAG desabilitada: falha ao inicializar retrieval: %s",
                    e,
                )
        self._qa: BuscadorQA = qa or QAServiceNulo()
        if qa is None and settings.QA_ENABLED:
            try:
                from services.rag import get_qa_service

                self._qa = get_qa_service()
                logger.info("[Processador] QAService inicializado")
            except Exception as e:
                logger.warning(
                    "[Processador] QA desabilitado: falha ao inicializar QAService: %s",
                    e,
                )

    # ------------------------------------------------------------------
    # Ponto de entrada
    # ------------------------------------------------------------------

    async def processar(
        self,
        db: Session,
        telefone: str,
        conteudo: str,
        message_sid: Optional[str] = None,
    ) -> ResultadoProcessamento:
        """
        Processa uma mensagem recebida e retorna a resposta a enviar.
        Registra todas as decisões em ProcessamentoMensagem para auditoria.
        """
        telefone_norm = normalizar_telefone(telefone)
        inicio_ms = time.monotonic()
        erro_processamento: Optional[str] = None

        # 1. Salva mensagem do cliente (ainda sem contato/atendimento)
        msg_in = Mensagem(
            telefone=telefone_norm,
            conteudo=conteudo,
            origem=OrigemMensagem.USER,
            message_sid=message_sid,
        )
        db.add(msg_in)
        db.commit()

        # Logger de debug vinculado a esta mensagem (prefixo para grep por telefone:msg_id)
        dlog = DebugLogger(telefone=telefone_norm, msg_id=msg_in.id)
        dlog.log("entrada", f'msg="{conteudo.replace(chr(10), " ")}"')

        # 2. Identifica remetente
        identificacao = identificar_por_telefone(db, telefone_norm)
        logger.info(f"[Processador] Identificação: {identificacao.status.value}")
        dlog.log(
            "identificacao",
            "status="
            + identificacao.status.value
            + (f" empresa='{identificacao.empresa.nome[:30]}'" if identificacao.empresa else "")
            + (f" contato_id={identificacao.contato.id}" if identificacao.contato else ""),
        )

        # 3. Classifica intenção e extrai entidades
        limiares_confianca = ParametroService(db).limiares_classificador()
        resultado_class = await classificar(conteudo, llm=self._llm, limiares_confianca=limiares_confianca)
        logger.info(
            f"[Processador] Intenção: {resultado_class.intencao_principal.value}"
            f" (confiança={resultado_class.confianca:.2f}, via {resultado_class.origem})"
        )
        _ent = resultado_class.entidades
        _ent_str = (
            (f" cnpjs={_ent.cnpjs}" if _ent.cnpjs else "")
            + (f" produtos={_ent.tipos_produto}" if _ent.tipos_produto else "")
            + (f" qtd={_ent.quantidades}" if _ent.quantidades else "")
            + (f" software={_ent.software_ponto}" if _ent.software_ponto else "")
            + (f" tipo_leitor={_ent.tipo_leitor_mencionado}" if _ent.tipo_leitor_mencionado else "")
            + (f" faixa_func={_ent.faixa_funcionarios}" if _ent.faixa_funcionarios is not None else "")
        )
        dlog.log(
            "intent",
            f"intencao={resultado_class.intencao_principal.value} confianca={resultado_class.confianca:.2f}"
            f" via={resultado_class.origem}{_ent_str}",
        )

        # 4. Verifica modo de operação do atendimento ativo (se existir)
        # Se modo=HUMANO, o sistema processa/classifica mas NÃO gera resposta.
        contato_inicial = identificacao.contato
        atendimento_inicial = self._atendimento_ativo(db, contato_inicial) if contato_inicial else None
        modo_humano = atendimento_inicial is not None and atendimento_inicial.modo_operacao == ModoOperacao.HUMANO
        if modo_humano:
            logger.info(f"[Processador] Atendimento {atendimento_inicial.id} em modo HUMANO — "
                "não gerando resposta automática.")
        dlog.log("modo", "HUMANO → resposta suprimida" if modo_humano else "AGENTE")

        # 4b. Modo de execução vigente (REQ-011) — independente do modo_operacao acima
        # (REQ-011.14: HUMANO sempre suprime, em qualquer modo de execução). Determina
        # se a resposta gerada pode sair automaticamente ou precisa ficar pendente de
        # aprovação no painel antes de qualquer envio real.
        modo_execucao = ParametroService(db).modo_execucao()
        requer_aprovacao = modo_execucao in (ModoExecucao.SIMULACAO, ModoExecucao.CONVERSA_CONTROLADA)
        dlog.log("modo_execucao", modo_execucao.value)

        # 5. Roteia conforme estado de identificação + intenção (só no modo AGENTE)
        if modo_humano:
            resposta = RespostaGerada(texto="", template_usado=None)
        else:
            try:
                resposta = await self._decidir_resposta(
                    db=db,
                    telefone=telefone_norm,
                    conteudo=conteudo,
                    identificacao=identificacao,
                    resultado_class=resultado_class,
                    dlog=dlog,
                )
            except Exception as e:
                logger.exception(f"[Processador] Erro gerando resposta: {e}")
                erro_processamento = str(e)
                resposta = RespostaGerada(
                    texto="Desculpe, tive um problema ao processar sua mensagem.",
                    template_usado=None,
                )

        # 6. Recarrega identificação (pode ter sido criado contato agora)
        ident_final = identificar_por_telefone(db, telefone_norm)
        contato = ident_final.contato
        atendimento = self._atendimento_ativo(db, contato) if contato else None

        # 7. Registra processamento (auditoria/debug) — sempre, independente do modo
        dlog.log(
            "saida",
            f"template={resposta.template_usado or 'nenhum'}"
            f" rag={resposta.rag_utilizada}"
            f" llm={resposta.personalizado_via_llm}"
            f' texto="{resposta.texto[:80].replace(chr(10), " ")}"',
        )
        duracao_ms = int((time.monotonic() - inicio_ms) * 1000)
        processamento = self._criar_processamento(
            db=db,
            resultado_class=resultado_class,
            identificacao=identificacao,
            contato_atual=contato,
            empresa_atual=ident_final.empresa,
            atendimento_atual=atendimento,
            resposta=resposta,
            duracao_ms=duracao_ms,
            erro=erro_processamento,
            fase_pre_decisao=atendimento_inicial.fase if atendimento_inicial else None,
        )

        dlog.log("processamento_id", f"id={processamento.id} duracao={duracao_ms}ms")

        # 8. Vincula mensagem do cliente ao processamento/contato/atendimento
        msg_in.processamento_id = processamento.id
        if contato:
            msg_in.contato_id = contato.id
            if atendimento:
                msg_in.atendimento_id = atendimento.id
                atendimento.registrar_ultima_mensagem_em(msg_in.timestamp)

        # 9. Persiste resposta do sistema APENAS quando modo=AGENTE.
        # No modo HUMANO, o operador enviará a resposta manualmente pela UI.
        # Mensagem nasce pendente de aprovação (aprovador_id/timestamp_aprovacao NULL)
        # em simulacao/conversa_controlada — REQ-011.5/011.10. Em execucao_normal, sem
        # etapa de aprovação humana (REQ-011.16), é marcada como decidida automaticamente
        # pelo próprio sistema, para não poluir a fila de pendências do painel com
        # mensagens que já foram entregues (permite feedback retroativo — REQ-011.17 —
        # sem confundir com "aguardando decisão").
        if not modo_humano:
            msg_out = Mensagem(
                telefone=telefone_norm,
                conteudo=resposta.texto,
                origem=OrigemMensagem.SYSTEM,
                contato_id=contato.id if contato else None,
                atendimento_id=atendimento.id if atendimento else None,
                aprovador_id=None,
                timestamp_aprovacao=None,
            )
            if resposta.texto and not requer_aprovacao:
                sistema_user = self._obter_user_sistema(db)
                msg_out.aprovador_id = sistema_user.id
                msg_out.timestamp_aprovacao = utc_now()
            db.add(msg_out)
        db.commit()

        # REQ-011.5/011.10: em simulacao/conversa_controlada, a resposta gerada fica
        # pendente no painel — não sai automaticamente pelo canal (webhook Twilio ou
        # simulador `/api/mensagem`). `msg_out` acima já preserva o texto completo para
        # quem for aprovar depois; só o valor devolvido ao chamador é suprimido aqui.
        resposta_entrega_imediata = resposta.texto
        if not modo_humano and requer_aprovacao and resposta.texto:
            resposta_entrega_imediata = ""
            dlog.log(
                "aprovacao",
                f"modo={modo_execucao.value} → resposta pendente, não entregue automaticamente",
            )

        return ResultadoProcessamento(
            resposta=resposta_entrega_imediata,
            contato_id=contato.id if contato else None,
            atendimento_id=atendimento.id if atendimento else None,
            processamento_id=processamento.id,
            intencao=resultado_class.intencao_principal.value,
            origem_classificacao=resultado_class.origem,
        )

    # ------------------------------------------------------------------
    # Registro de processamento (auditoria)
    # ------------------------------------------------------------------

    def _criar_processamento(
        self,
        db: Session,
        resultado_class: ResultadoClassificacao,
        identificacao: ResultadoIdentificacao,
        contato_atual: Optional[Contato],
        empresa_atual: Optional[Empresa],
        atendimento_atual: Optional[Atendimento],
        resposta: RespostaGerada,
        duracao_ms: int,
        erro: Optional[str] = None,
        fase_pre_decisao: Optional[FaseAtendimento] = None,
    ) -> ProcessamentoMensagem:
        """Persiste um registro auditvel do que o cérebro decidiu."""
        try:
            origem_enum = OrigemClassificacao(resultado_class.origem)
        except ValueError:
            origem_enum = None

        entidades_dict = {
            "cnpjs": resultado_class.entidades.cnpjs,
            "cpfs": [mascarar_cpf(c) for c in resultado_class.entidades.cpfs],
            "datas_nascimento": resultado_class.entidades.datas_nascimento,
            "nomes": resultado_class.entidades.nomes,
            "tipos_produto": resultado_class.entidades.tipos_produto,
            "quantidades": resultado_class.entidades.quantidades,
            "emails": resultado_class.entidades.emails,
            "software_ponto": resultado_class.entidades.software_ponto,
            "software_acesso": resultado_class.entidades.software_acesso,
            "tipo_leitor_mencionado": resultado_class.entidades.tipo_leitor_mencionado,
            "faixa_funcionarios": resultado_class.entidades.faixa_funcionarios,
        }

        # Somatrio de tokens (classificação + personalização da resposta)
        tokens_in = (resultado_class.llm_tokens_input or 0) + (resposta.llm_tokens_input or 0) or None
        tokens_out = (resultado_class.llm_tokens_output or 0) + (resposta.llm_tokens_output or 0) or None

        score_maximo = resposta.rag_score_maximo
        if score_maximo is not None:
            score_maximo = round(float(score_maximo), 4)
        proc = ProcessamentoMensagem(
            intencao=resultado_class.intencao_principal.value,
            intencoes=[i.value for i in resultado_class.intencoes],
            confianca=round(resultado_class.confianca, 2),
            confianca_nivel=resultado_class.confianca_nivel.value,
            origem_classificacao=origem_enum,
            entidades=entidades_dict,
            status_identificacao=identificacao.status.value,
            contato_id_identificado=contato_atual.id if contato_atual else None,
            empresa_id_identificada=empresa_atual.id if empresa_atual else None,
            atendimento_id_ativa=atendimento_atual.id if atendimento_atual else None,
            fase_atendimento=fase_pre_decisao.value if fase_pre_decisao else None,
            template_usado=resposta.template_usado,
            personalizado_via_llm=resposta.personalizado_via_llm,
            llm_provider=(self._llm.nome if self._llm else None),
            llm_modelo=(settings.LLM_MODEL if self._llm else None),
            llm_tokens_input=tokens_in,
            llm_tokens_output=tokens_out,
            llm_latencia_ms=resultado_class.llm_latencia_ms,
            llm_raw_resposta=resultado_class.raw_llm,
            rag_utilizada=resposta.rag_utilizada,
            rag_trechos=resposta.trechos_rag or None,
            rag_score_maximo=score_maximo,
            fallback_req003=resposta.fallback_req003,
            resultado_fallback=resposta.resultado_fallback,
            justificativa_curta=resposta.justificativa_curta,
            duracao_ms=duracao_ms,
            erro=erro,
        )
        db.add(proc)
        db.commit()
        db.refresh(proc)
        return proc

    # ------------------------------------------------------------------
    # Roteamento de decisão
    # ------------------------------------------------------------------

    async def _decidir_resposta(
        self,
        db: Session,
        telefone: str,
        conteudo: str,
        identificacao,
        resultado_class,
        dlog: Optional[DebugLogger] = None,
    ) -> RespostaGerada:
        """Decide o que responder com base na identificação e intenção.

        Motor Intenção×Fase→Ações (`services/conversacao/motor.py`): toda intenção que
        bater na mensagem é considerada (não só a de maior prioridade — era essa a raiz
        do bug em que uma saudação "engolia" uma pergunta de produto na mesma mensagem).
        `MULTIPLO` (status de identificação, não é Intenção nem Fase) continua como caso
        especial fora do motor.
        """
        if identificacao.status != StatusIdentificacao.MULTIPLO:
            resposta_continuacao = await self._resolver_continuacao_atendimento(
                db, identificacao.contato, conteudo, dlog=dlog
            )
            if resposta_continuacao is not None:
                return resposta_continuacao

        if identificacao.status == StatusIdentificacao.MULTIPLO:
            # Regras globais (ex.: cliente manda o CNPJ certo já aqui) ainda se aplicam —
            # só não há Fase/atendimento único pra desambiguar antes disso resolver.
            ctx = ContextoAcao(
                db=db,
                telefone=telefone,
                conteudo=conteudo,
                identificacao=identificacao,
                resultado_class=resultado_class,
                processador=self,
                dlog=dlog,
            )
            resposta = await resolver_e_executar(ctx, REGRAS_GLOBAIS, {})
            if resposta is not None:
                return resposta
            if dlog:
                dlog.log("rota", "MULTIPLO → MULTIPLAS_EMPRESAS")
            nomes_empresas = ", ".join(e.nome for e in identificacao.empresas[:5])
            return await self._gerador.gerar(
                MensagemId.MULTIPLAS_EMPRESAS,
                contexto={"empresas": nomes_empresas},
            )

        contato = identificacao.contato
        empresa = identificacao.empresa
        pessoa = None
        atendimento = None

        if contato:
            if empresa:
                # Identificado com empresa: atendimento sempre garantido, como já era.
                atendimento = self._obter_ou_criar_atendimento(db, contato, empresa)
            else:
                atendimento = self._atendimento_ativo(db, contato)
                if atendimento and atendimento.pessoa_id and atendimento.pessoa:
                    pessoa = atendimento.pessoa
            if atendimento:
                await self._atualizar_infos_atendimento(db, atendimento, resultado_class)

        ctx = ContextoAcao(
            db=db,
            telefone=telefone,
            conteudo=conteudo,
            identificacao=identificacao,
            resultado_class=resultado_class,
            processador=self,
            contato=contato,
            empresa=empresa,
            pessoa=pessoa,
            atendimento=atendimento,
            dlog=dlog,
        )
        resposta = await resolver_e_executar(ctx, REGRAS_GLOBAIS, REGISTRO_POR_FASE)
        if resposta is not None:
            return resposta
        return await self._fallback_qa_ou_nao_entendi(
            conteudo, resultado_class=resultado_class, db=db, atendimento=atendimento, dlog=dlog
        )

    async def _fallback_qa_ou_nao_entendi(
        self,
        conteudo_cliente: str,
        resultado_class: Optional[ResultadoClassificacao] = None,
        db: Optional[Session] = None,
        atendimento: Optional[Atendimento] = None,
        dlog: Optional[DebugLogger] = None,
    ) -> RespostaGerada:
        """Último recurso quando nenhuma Ação do motor (Intenção×Fase→Ações) produziu
        fragmento: tenta QA antes de NAO_ENTENDI.

        REQ-004.9 (Fase 5): quando a mensagem tem `confianca_nivel` BAIXA duas vezes
        seguidas sem nenhuma outra Ação resolver nada, escala para humano em vez de
        insistir com NAO_ENTENDI de novo — mesmo padrão de "1 tentativa extra, depois
        escala" já usado em REQ-002.21/REQ-003.7. `resultado_class`/`db`/`atendimento`
        são opcionais (contato totalmente novo, sem atendimento ainda, simplesmente não
        rastreia o contador — não vale criar atendimento só por isso)."""
        par = await self._qa.buscar_melhor(
            conteudo_cliente, apenas_aprovados=settings.QA_APENAS_APROVADOS, dlog=dlog
        )
        if par is not None:
            if db is not None and atendimento is not None:
                self._remover_info_atendimento(db, atendimento.id, _CONFIANCA_BAIXA_TENTATIVA_CHAVE)
            if dlog:
                dlog.log(
                    "qa_decisao",
                    f"hit QA (fallback) id={par.id_externo} score={par.score:.4f}",
                )
            return RespostaGerada(
                texto=par.resposta,
                template_usado="qa_pair",
                personalizado_via_llm=False,
                rag_utilizada=True,
                trechos_rag=[par.to_dict()],
                rag_score_maximo=par.score,
                fallback_req003=True,
                resultado_fallback="qa_encontrado",
                justificativa_curta=(
                    f"Nenhuma ação do motor respondeu; par Q&A encontrado no fallback "
                    f"(score={par.score:.2f})."
                ),
            )

        resultado_fallback = "nao_entendi"
        justificativa_curta = "Nenhuma ação do motor, QA ou escalonamento respondeu — fallback genérico."

        if (
            resultado_class is not None
            and resultado_class.confianca_nivel == NivelConfianca.BAIXA
            and db is not None
            and atendimento is not None
        ):
            aguardando = bool(self._info_atendimento(db, atendimento.id, _CONFIANCA_BAIXA_TENTATIVA_CHAVE))
            if aguardando:
                self._remover_info_atendimento(db, atendimento.id, _CONFIANCA_BAIXA_TENTATIVA_CHAVE)
                await self._escalar_atendimento(
                    db, atendimento, MotivoEscalonamento.BAIXA_CONFIANCA, ator="sistema:confianca_baixa", dlog=dlog
                )
                if dlog:
                    dlog.log("rota", "confiança baixa 2x seguidas → escalar_humano (REQ-004.9)")
                resposta = await self._gerador.gerar(MensagemId.ESCALADO_BAIXA_CONFIANCA)
                resposta.fallback_req003 = True
                resposta.resultado_fallback = "escalado_baixa_confianca"
                resposta.justificativa_curta = (
                    "Confiança baixa 2 mensagens seguidas sem nenhuma ação resolver — "
                    "escalado para humano (REQ-004.9)."
                )
                return resposta
            self._salvar_info_atendimento(db, atendimento.id, _CONFIANCA_BAIXA_TENTATIVA_CHAVE, "1")
            resultado_fallback = "nao_entendi_aguardando_confirmacao"
            justificativa_curta = (
                "Confiança baixa (1ª ocorrência) — respondendo NAO_ENTENDI e aguardando "
                "2ª ocorrência antes de escalar (REQ-004.9)."
            )
            if dlog:
                dlog.log("rota", "confiança baixa (1ª vez) → NAO_ENTENDI, aguardando 2ª ocorrência")
        elif db is not None and atendimento is not None:
            self._remover_info_atendimento(db, atendimento.id, _CONFIANCA_BAIXA_TENTATIVA_CHAVE)

        if dlog:
            dlog.log("rota", "nada respondeu → NAO_ENTENDI")
        resposta = await self._gerador.gerar(
            MensagemId.NAO_ENTENDI,
            personalizar=True,
            mensagem_cliente=conteudo_cliente,
        )
        resposta.fallback_req003 = True
        resposta.resultado_fallback = resultado_fallback
        resposta.justificativa_curta = justificativa_curta
        return resposta

    # ------------------------------------------------------------------
    # Continuação de atendimento encerrado (REQ-016.7/016.9)
    # ------------------------------------------------------------------

    async def _resolver_continuacao_atendimento(
        self,
        db: Session,
        contato: Optional[Contato],
        conteudo: str,
        dlog: Optional[DebugLogger] = None,
    ) -> Optional[RespostaGerada]:
        """Decide se esta mensagem deve ser tratada como resposta a uma pergunta de
        continuação (PERG-016-009/009B) pendente, ou se deve disparar a pergunta agora
        porque o atendimento mais recente do contato está `encerrado` (exceto
        `concluido_conversao`, que nunca pergunta — REQ-016.7). Retorna `None` quando não
        há nada a decidir aqui — o chamador segue o fluxo normal (que já cria um
        atendimento novo corretamente quando não há nenhum ativo)."""
        if not contato:
            return None

        ultimo = atendimentos_svc.atendimento_mais_recente(db, contato)
        if not ultimo:
            return None

        if ultimo.status == StatusAtendimento.ATIVO:
            # A confirmação de interesses (009B) roda com o atendimento já reaberto
            # (ATIVO) — a pergunta de continuação em si só existe enquanto ele está
            # `encerrado` (removida antes de reabrir, ver `_processar_resposta_continuacao`).
            if self._info_atendimento(db, ultimo.id, _CONFIRMAR_INTERESSE_PENDENTE_CHAVE) == "aguardando":
                return await self._processar_confirmacao_interesse(db, ultimo, conteudo, dlog=dlog)
            return None

        if ultimo.motivo_encerramento == MotivoEncerramento.CONCLUIDO_CONVERSAO.value:
            return None

        if self._info_atendimento(db, ultimo.id, _CONTINUACAO_PENDENTE_CHAVE) == "aguardando":
            return await self._processar_resposta_continuacao(db, ultimo, conteudo, dlog=dlog)

        self._salvar_info_atendimento(db, ultimo.id, _CONTINUACAO_PENDENTE_CHAVE, "aguardando")
        if dlog:
            dlog.log(
                "continuacao",
                f"atendimento {ultimo.id} encerrado (motivo={ultimo.motivo_encerramento}) → pergunta continuação",
            )
        resumo = self._resumo_curto_atendimento(db, ultimo)
        return await self._gerador.gerar(MensagemId.PERGUNTA_CONTINUACAO_ATENDIMENTO, {"resumo_curto": resumo})

    async def _processar_resposta_continuacao(
        self,
        db: Session,
        atendimento_encerrado: Atendimento,
        conteudo: str,
        dlog: Optional[DebugLogger] = None,
    ) -> Optional[RespostaGerada]:
        """Interpreta a resposta à PERG-016-009. Ambígua (nem 'continuar' nem 'novo'
        reconhecidos) aplica o default sugerido pela janela de continuação (REQ-016.7:
        dentro da janela presume continuação, fora presume novo pedido) — a política de
        retry formal (REQ-002.21) fica para a Fase 10."""
        self._remover_info_atendimento(db, atendimento_encerrado.id, _CONTINUACAO_PENDENTE_CHAVE)
        decisao = self._interpretar_resposta_continuacao(db, atendimento_encerrado, conteudo)

        if decisao == "novo":
            if dlog:
                dlog.log("continuacao", "cliente escolheu pedido novo")
            return None  # sem atendimento ativo → fluxo normal cria um atendimento novo

        atendimentos_svc.reabrir_atendimento(
            db,
            atendimento_encerrado,
            ator="cliente",
            justificativa="Cliente escolheu continuar em resposta à PERG-016-009",
        )
        if dlog:
            dlog.log("continuacao", f"atendimento {atendimento_encerrado.id} reaberto pelo cliente")

        interesses = self._resumo_produtos_anteriores(db, atendimento_encerrado)
        if not interesses:
            return None  # sem interesses anteriores registrados → segue fluxo normal

        self._salvar_info_atendimento(
            db, atendimento_encerrado.id, _CONFIRMAR_INTERESSE_PENDENTE_CHAVE, "aguardando"
        )
        return await self._gerador.gerar(
            MensagemId.CONFIRMAR_INTERESSE_ANTERIOR, {"produtos_anteriores": interesses}
        )

    async def _processar_confirmacao_interesse(
        self,
        db: Session,
        atendimento: Atendimento,
        conteudo: str,
        dlog: Optional[DebugLogger] = None,
    ) -> Optional[RespostaGerada]:
        """Interpreta a resposta à PERG-016-009B. 'Mudou de ideia' limpa os interesses
        capturados e volta para Esclarecendo do zero; qualquer outra coisa (inclusive
        ambígua) mantém o que já foi capturado — default menos destrutivo."""
        self._remover_info_atendimento(db, atendimento.id, _CONFIRMAR_INTERESSE_PENDENTE_CHAVE)

        if _REGEX_MUDOU_DE_IDEIA.search(conteudo) and not _REGEX_MANTEM_INTERESSE.search(conteudo):
            self._reiniciar_qualificacao(db, atendimento)
            if dlog:
                dlog.log("continuacao", f"atendimento {atendimento.id} — cliente mudou de ideia, reinicia qualificação")
        elif dlog:
            dlog.log("continuacao", f"atendimento {atendimento.id} — mantém interesses anteriores")

        return None  # segue fluxo normal (Esclarecendo do zero, ou fase em que já estava)

    def _interpretar_resposta_continuacao(
        self,
        db: Session,
        atendimento_encerrado: Atendimento,
        conteudo: str,
    ) -> str:
        """Retorna 'continuar' ou 'novo' — nunca ambíguo (ver docstring de
        `_processar_resposta_continuacao` sobre o default aplicado)."""
        continuar = bool(_REGEX_CONTINUAR_ATENDIMENTO.search(conteudo))
        novo = bool(_REGEX_NOVO_PEDIDO.search(conteudo))
        if continuar and not novo:
            return "continuar"
        if novo and not continuar:
            return "novo"

        janela_horas = ParametroService(db).janela_continuacao_atendimento_horas()
        dentro_da_janela = _dentro_da_janela(atendimento_encerrado.ultima_mensagem_at, janela_horas)
        return "continuar" if dentro_da_janela else "novo"

    def _reiniciar_qualificacao(self, db: Session, atendimento: Atendimento) -> None:
        """PERG-016-009B ('mudou de ideia'): limpa interesses de produto capturados e
        volta para Esclarecendo. Dados de identificação (CNPJ/CPF/contato) são
        preservados — só o interesse comercial é reiniciado."""
        chaves = (
            "tipos_produto",
            "quantidades",
            CAMPO_SOFTWARE_PONTO.chave,
            "tipo_leitor_mencionado",
            CAMPO_FAIXA_FUNCIONARIOS.chave,
        )
        for chave in chaves:
            self._remover_info_atendimento(db, atendimento.id, chave)
        for item in list(atendimento.itens):
            db.delete(item)
        fase_anterior = atendimento.fase.value
        atendimento.fase = FaseAtendimento.ESCLARECENDO
        db.commit()
        atendimentos_svc.registrar_evento_atendimento(
            db,
            atendimento,
            tipo=TipoEventoAtendimento.FASE_ALTERADA,
            ator="sistema:motor_conversacao",
            estado_anterior=fase_anterior,
            estado_novo=FaseAtendimento.ESCLARECENDO.value,
            motivo="PERG-016-009B: cliente mudou de ideia, reiniciando qualificação",
        )

    def _resumo_curto_atendimento(self, db: Session, atendimento: Atendimento) -> str:
        """`{resumo_curto}` da PERG-016-009 — texto genérico se não houver dado suficiente
        (REQ-016.9), sumarização semântica via LLM é evolução futura."""
        tipos = self._info_atendimento(db, atendimento.id, "tipos_produto")
        if not tipos:
            return "seu atendimento anterior"
        primeiro = tipos.split(",")[0].strip().replace("_", " ")
        return primeiro or "seu atendimento anterior"

    def _resumo_produtos_anteriores(self, db: Session, atendimento: Atendimento) -> Optional[str]:
        """`{produtos_anteriores}` da PERG-016-009B — `None` quando não há nada capturado
        (pula a confirmação de interesses, vai direto para Esclarecendo)."""
        tipos = self._info_atendimento(db, atendimento.id, "tipos_produto")
        if not tipos:
            return None
        return ", ".join(t.strip().replace("_", " ") for t in tipos.split(",") if t.strip())

    async def _responder_produto_com_clarificacao(
        self,
        db: Session,
        atendimento: Atendimento,
        conteudo_cliente: str,
        dlog: Optional[DebugLogger] = None,
    ) -> RespostaGerada:
        """REQ-003.7: quando a base (Q&A/RAG) não tem conteúdo sobre o produto perguntado,
        faz no máximo 1 pergunta de clarificação antes de escalar para atendimento humano —
        em vez de cair direto no fallback genérico `PRODUTO_SEM_CONTEXTO`.

        Estado rastreado em `AtendimentoInfo` (`_RAG_CLARIFICACAO_PENDENTE_CHAVE`), mesmo
        padrão já usado por `FinalizandoState._resolver_modelo` (F2)."""
        aguardando_clarificacao = bool(
            self._info_atendimento(db, atendimento.id, _RAG_CLARIFICACAO_PENDENTE_CHAVE)
        )

        resposta = await self._responder_com_rag(
            conteudo_cliente=conteudo_cliente,
            template_fallback=MensagemId.PRODUTO_SEM_CONTEXTO,
            dlog=dlog,
        )

        if resposta.trechos_rag:
            # Achou conteúdo (QA ou RAG) — limpa clarificação pendente, se houver.
            if aguardando_clarificacao:
                self._remover_info_atendimento(db, atendimento.id, _RAG_CLARIFICACAO_PENDENTE_CHAVE)
            return resposta

        if not aguardando_clarificacao:
            self._salvar_info_atendimento(db, atendimento.id, _RAG_CLARIFICACAO_PENDENTE_CHAVE, "1")
            if dlog:
                dlog.log("rag_decisao", "sem conteúdo → 1ª pergunta de clarificação (REQ-003.7)")
            return await self._gerador.gerar(MensagemId.RAG_PEDIR_CLARIFICACAO)

        # Já perguntamos uma vez e a base continua sem conteúdo — escala para humano
        # (REQ-004.9/REQ-004.2: motivo/timestamp/resumo via helper central da Fase 5).
        self._remover_info_atendimento(db, atendimento.id, _RAG_CLARIFICACAO_PENDENTE_CHAVE)
        await self._escalar_atendimento(
            db, atendimento, MotivoEscalonamento.BASE_INSUFICIENTE, ator="sistema:base_insuficiente", dlog=dlog
        )
        return await self._gerador.gerar(MensagemId.RAG_ESCALADO_SEM_BASE)

    async def _responder_pedir_catalogo(
        self,
        db: Session,
        resultado_class: ResultadoClassificacao,
        dlog: Optional[DebugLogger] = None,
    ) -> RespostaGerada:
        """REQ-003.11: envia o link do catálogo do tipo de produto identificado na mensagem;
        se o tipo não estiver claro (nenhum ou mais de um tipo suportado mencionado),
        pergunta qual catálogo o cliente quer antes de enviar."""
        tipos_suportados = [t for t in resultado_class.entidades.tipos_produto if t in _CATALOGO_PARAM_POR_TIPO]

        if len(tipos_suportados) != 1:
            if dlog:
                dlog.log("catalogo", f"tipo ambíguo/ausente ({tipos_suportados}) → pergunta qual catálogo")
            return await self._gerador.gerar(MensagemId.PEDIR_TIPO_CATALOGO)

        tipo = tipos_suportados[0]
        link = ParametroService(db).get_str(_CATALOGO_PARAM_POR_TIPO[tipo])
        rotulo = _CATALOGO_TIPOS_LABEL[tipo]
        if not link:
            if dlog:
                dlog.log("catalogo", f"link não configurado para tipo={tipo}")
            return await self._gerador.gerar(MensagemId.CATALOGO_INDISPONIVEL, {"tipo": rotulo})

        if dlog:
            dlog.log("catalogo", f"enviando catálogo tipo={tipo}")
        return await self._gerador.gerar(MensagemId.CATALOGO_ENVIADO, {"tipo": rotulo, "link": link})

    # ------------------------------------------------------------------
    # Escalonamento (REQ-004, Fase 5)
    # ------------------------------------------------------------------

    async def _escalar_atendimento(
        self,
        db: Session,
        atendimento: Atendimento,
        motivo: MotivoEscalonamento,
        ator: str,
        dlog: Optional[DebugLogger] = None,
    ) -> None:
        """REQ-004.2/004.4/004.5: marca modo humano, persiste motivo/timestamp/ator e
        gera o resumo de contexto para o vendedor — helper central reaproveitado por
        todo caminho de escalonamento (explícito, implícito, retrofit da Fase 3 e
        takeover manual do painel). Não faz nada se o atendimento já não está ATIVO
        (encerrado não deveria ser "escalado")."""
        if atendimento.status != StatusAtendimento.ATIVO:
            return
        modo_anterior = atendimento.modo_operacao.value
        atendimento.modo_operacao = ModoOperacao.HUMANO
        atendimento.escalado_em = utc_now()
        atendimento.escalado_por = ator
        atendimento.motivo_escalonamento = motivo.value
        atendimento.resumo_escalonamento = self._montar_resumo_escalonamento(db, atendimento, motivo)
        db.commit()
        atendimentos_svc.registrar_evento_atendimento(
            db,
            atendimento,
            tipo=TipoEventoAtendimento.ESCALADO,
            ator=ator,
            estado_anterior=modo_anterior,
            estado_novo=ModoOperacao.HUMANO.value,
            motivo=motivo.value,
        )
        if dlog:
            dlog.log(
                "escalonamento",
                f"atendimento {atendimento.id} → HUMANO (motivo={motivo.value}, ator={ator})",
            )

    _LABEL_MOTIVO_ESCALONAMENTO = {
        MotivoEscalonamento.SOLICITADO_CLIENTE: "Cliente pediu para falar com atendente",
        MotivoEscalonamento.RECLAMACAO: "Reclamação/insatisfação do cliente",
        MotivoEscalonamento.PROJETO_COMPLEXO: "Projeto complexo (quantidade/porte/leitor facial)",
        MotivoEscalonamento.BAIXA_CONFIANCA: "Baixa confiança do classificador (mensagens repetidamente ambíguas)",
        MotivoEscalonamento.BASE_INSUFICIENTE: "Base de conhecimento sem conteúdo suficiente",
        MotivoEscalonamento.MANUAL_VENDEDOR: "Assumido manualmente pelo vendedor",
        MotivoEscalonamento.MODELO_NAO_RECONHECIDO: "Modelo não reconhecido no catálogo após tentativas",
    }

    def _montar_resumo_escalonamento(
        self, db: Session, atendimento: Atendimento, motivo: MotivoEscalonamento
    ) -> str:
        """REQ-004.2: resumo de contexto para o vendedor — reaproveita a mesma leitura
        de dados de `FinalizandoState._gerar_resumo` (AtendimentoInfo + ItemAtendimento/Modelo),
        mas em prosa voltada para quem vai assumir a conversa, não para o cliente."""
        linhas = []
        contato = atendimento.contato
        if contato:
            linhas.append(f"Cliente: {contato.nome or 'sem nome'} ({contato.telefone})")
        if atendimento.empresa:
            linhas.append(f"Empresa: {atendimento.empresa.nome} (CNPJ {atendimento.empresa.cnpj})")
        elif atendimento.pessoa:
            linhas.append(f"Pessoa física: {atendimento.pessoa.nome or 'sem nome'}")

        valores = {info.chave: info.valor for info in atendimento.informacoes}
        if valores.get("tipos_produto"):
            linhas.append(f"Interesse: {valores['tipos_produto'].replace('_', ' ')}")
        item_resolvido = next((item for item in atendimento.itens if item.modelo_id is not None), None)
        if item_resolvido and item_resolvido.modelo:
            modelo = item_resolvido.modelo
            linhas.append(f"Modelo: {modelo.descricao}")
            if modelo.marca:
                linhas.append(f"Marca: {modelo.marca}")
            if modelo.aplicacao:
                linhas.append(f"Aplicação: {modelo.aplicacao}")
            categorias = ", ".join(c.descricao for c in modelo.categorias)
            if categorias:
                linhas.append(f"Categorias: {categorias}")
            atributos = ", ".join(f"{a.chave}: {a.valor}" for a in modelo.atributos)
            if atributos:
                linhas.append(f"Atributos: {atributos}")
        if valores.get(CAMPO_SOFTWARE_PONTO.chave):
            linhas.append(f"Software de ponto: {valores[CAMPO_SOFTWARE_PONTO.chave]}")
        if valores.get(CAMPO_SOFTWARE_ACESSO.chave):
            linhas.append(f"Software de controle de acesso: {valores[CAMPO_SOFTWARE_ACESSO.chave]}")
        if valores.get(CAMPO_INTERESSE_SISTEMA_NUVEM.chave):
            linhas.append(f"Interesse em sistema na nuvem: {valores[CAMPO_INTERESSE_SISTEMA_NUVEM.chave]}")
        if valores.get(CAMPO_HOMOLOGADO_SOFTWARE.chave):
            linhas.append(f"Homologação: {valores[CAMPO_HOMOLOGADO_SOFTWARE.chave]}")
        if valores.get(CAMPO_FAIXA_FUNCIONARIOS.chave):
            linhas.append(f"Funcionários: {valores[CAMPO_FAIXA_FUNCIONARIOS.chave]}")
        if valores.get(CAMPO_QUANTIDADE.chave):
            linhas.append(f"Quantidade: {valores[CAMPO_QUANTIDADE.chave]}")
        if valores.get("quantidades"):
            linhas.append(f"Quantidade mencionada na mensagem: {valores['quantidades']}")

        pendentes = campos_pendentes(atendimento)
        if pendentes:
            linhas.append("Pendente: " + ", ".join(c.chave for c in pendentes))

        linhas.append(f"Motivo do escalonamento: {self._LABEL_MOTIVO_ESCALONAMENTO[motivo]}")
        return "\n".join(linhas)

    # ------------------------------------------------------------------
    # RAG helpers
    # ------------------------------------------------------------------

    async def _responder_com_rag(
        self,
        conteudo_cliente: str,
        template_fallback: MensagemId,
        dlog: Optional[DebugLogger] = None,
    ) -> RespostaGerada:
        """Busca pares/trechos e gera resposta; Q&A tem prioridade sobre chunks."""
        codigo_fallback = template_fallback.name
        # Camada 1: Q&A pairs curados
        par = await self._qa.buscar_melhor(
            conteudo_cliente, apenas_aprovados=settings.QA_APENAS_APROVADOS, dlog=dlog
        )
        if par is not None:
            if dlog:
                dlog.log("qa_decisao", f"hit QA → resposta curada id={par.id_externo} score={par.score:.4f}")
            return RespostaGerada(
                texto=par.resposta,
                template_usado="qa_pair",
                personalizado_via_llm=False,
                rag_utilizada=True,
                trechos_rag=[par.to_dict()],
                rag_score_maximo=par.score,
            )
        # Camada 2: chunks de produto (RAG)
        trechos = await self._retrieval.buscar_trechos(conteudo_cliente, dlog=dlog)
        if not trechos:
            if dlog:
                dlog.log("rag_decisao", f"sem trechos → fallback template={codigo_fallback}")
            resposta = await self._gerador.gerar(template_fallback)
            resposta.rag_utilizada = self._retrieval.habilitado
            return resposta
        if dlog:
            dlog.log("rag_decisao", f"{len(trechos)} trechos → gerando com LLM+RAG")
        return await self._gerador.gerar_com_rag(
            pergunta_cliente=conteudo_cliente,
            trechos=trechos,
            permitir_sugestao_produto=settings.RAG_SUGERIR_PRODUTOS,
            template_fallback=template_fallback,
        )

    # ------------------------------------------------------------------
    # Processamento de CNPJ
    # ------------------------------------------------------------------

    async def _processar_cnpj_fornecido(
        self,
        db: Session,
        telefone: str,
        cnpj: str,
        nome_informado: Optional[str] = None,
    ) -> RespostaGerada:
        """Processa quando o cliente forneceu um CNPJ: consulta, cria empresa/contato."""
        if not validar_cnpj(cnpj):
            return await self._gerador.gerar(MensagemId.CNPJ_INVALIDO)

        try:
            empresa = await obter_ou_criar_empresa(db, cnpj)
        except ConsultaCnpjError as e:
            logger.warning(f"[Processador] Falha ao consultar CNPJ: {e}")
            return await self._gerador.gerar(MensagemId.CNPJ_INVALIDO)

        # Procura contato existente por telefone (telefone é unique no modelo).
        # Inclui contatos anônimos (empresa_id=None) criados antes do CNPJ.
        telefone_norm = normalizar_telefone(telefone)
        contato_existente = (
            db.query(Contato)
            .filter(Contato.telefone.in_([telefone_norm, telefone]))
            .first()
        )
        if not contato_existente:
            contato_existente = criar_contato(
                db=db,
                telefone=telefone,
                empresa=empresa,
                nome=nome_informado,
            )
        else:
            # Promove contato anônimo para a empresa identificada (se aplicável).
            if contato_existente.empresa_id is None:
                vincular_empresa_ao_contato(db, contato_existente, empresa)
            if nome_informado and not contato_existente.nome:
                contato_existente.nome = nome_informado
                db.commit()

        # Cria atendimento ativo se ainda não houver
        self._obter_ou_criar_atendimento(db, contato_existente, empresa)

        return await self._gerador.gerar(
            MensagemId.CNPJ_CONSULTADO_OK,
            contexto={"nome": empresa.nome},
            personalizar=False,
        )

    async def _processar_cpf_fornecido(
        self,
        db: Session,
        telefone: str,
        cpf: str,
        nome_informado: Optional[str] = None,
        data_nascimento: Optional[date] = None,
    ) -> RespostaGerada:
        """Processa quando o cliente forneceu CPF: valida, persiste pessoa e vincula atendimento."""
        if not validar_cpf(cpf):
            return await self._gerador.gerar(MensagemId.CPF_INVALIDO)

        if data_nascimento is None:
            telefone_norm = normalizar_telefone(telefone)
            contato = (
                db.query(Contato)
                .filter(Contato.telefone.in_([telefone_norm, telefone]))
                .first()
            )
            if not contato:
                contato = criar_contato(db=db, telefone=telefone, nome=nome_informado)
            elif nome_informado and not contato.nome:
                contato.nome = nome_informado
                db.commit()

            atendimento = self._obter_ou_criar_atendimento_pf_pendente(db, contato, cpf)
            self._salvar_info_atendimento(db, atendimento.id, "cpf_pendente", cpf)
            return await self._gerador.gerar(MensagemId.PERGUNTAR_DATA_NASCIMENTO)

        pessoa, resultado_credito = await obter_ou_criar_pessoa(
            db,
            cpf,
            nome=nome_informado,
            data_nascimento=data_nascimento,
        )

        telefone_norm = normalizar_telefone(telefone)
        contato_existente = (
            db.query(Contato)
            .filter(Contato.telefone.in_([telefone_norm, telefone]))
            .first()
        )
        if not contato_existente:
            contato_existente = criar_contato(
                db=db,
                telefone=telefone,
                nome=nome_informado or pessoa.nome,
            )
        else:
            nome_final = nome_informado or pessoa.nome
            if nome_final and not contato_existente.nome:
                contato_existente.nome = nome_final
                db.commit()

        atendimento = self._obter_ou_criar_atendimento(
            db,
            contato_existente,
            pessoa=pessoa,
        )
        self._registrar_resultado_credito(db, atendimento, resultado_credito)
        self._remover_info_atendimento(db, atendimento.id, "cpf_pendente")

        nome_exibicao = pessoa.nome or contato_existente.nome or "cliente"
        return await self._gerador.gerar(
            MensagemId.CPF_CONSULTADO_OK,
            contexto={"nome": nome_exibicao},
            personalizar=False,
        )

    # ------------------------------------------------------------------
    # Atendimento e informações
    # ------------------------------------------------------------------

    STATUS_ATIVOS = (StatusAtendimento.ATIVO,)

    def _atendimento_ativo(self, db: Session, contato: Contato) -> Optional[Atendimento]:
        """Retorna o atendimento ativo do contato (se houver)."""
        return atendimentos_svc.atendimento_ativo(db, contato)

    async def _garantir_contato_e_atendimento_qualificacao(
        self,
        db: Session,
        telefone: str,
        contato: Optional[Contato],
        resultado_class: ResultadoClassificacao,
        dlog: Optional[DebugLogger] = None,
    ) -> Atendimento:
        """REQ-002.1B / REQ-016.6: cria contato e atendimento anônimos na intenção comercial."""
        nome = resultado_class.entidades.nomes[0] if resultado_class.entidades.nomes else None
        if contato is None:
            contato = criar_contato_sem_empresa(db, telefone, nome=nome)
            if dlog:
                dlog.log("rota", f"contato anônimo criado id={contato.id} nome={nome or '—'}")
        elif nome and not contato.nome:
            contato.nome = nome
            db.commit()

        atendimento = self._obter_ou_criar_atendimento(db, contato)
        await self._atualizar_infos_atendimento(db, atendimento, resultado_class)
        if dlog:
            dlog.log(
                "rota",
                f"atendimento criado/ativo id={atendimento.id} "
                f"numero={atendimento.numero_atendimento_cliente}",
            )
        return atendimento

    def _obter_ou_criar_atendimento(
        self,
        db: Session,
        contato: Contato,
        empresa: Optional[Empresa] = None,
        pessoa: Optional[Pessoa] = None,
    ) -> Atendimento:
        """Retorna atendimento ativo ou cria um novo."""
        return atendimentos_svc.obter_ou_criar_atendimento(db, contato, empresa=empresa, pessoa=pessoa)

    def _obter_ou_criar_atendimento_pf_pendente(
        self,
        db: Session,
        contato: Contato,
        cpf: str,
    ) -> Atendimento:
        """Cria ou retorna atendimento PF aguardando data de nascimento."""
        return atendimentos_svc.obter_ou_criar_atendimento_pf_pendente(
            db, contato, cpf_mascarado=mascarar_cpf(cpf)
        )

    def _promover_atendimento_pessoa(
        self,
        db: Session,
        atendimento: Atendimento,
        pessoa: Pessoa,
    ) -> Atendimento:
        """Vincula pessoa (PF) a um atendimento existente."""
        return atendimentos_svc.promover_atendimento_pessoa(db, atendimento, pessoa)

    def _parse_data_entidade(self, entidades, conteudo: str) -> Optional[date]:
        """Obtém data de nascimento das entidades extraídas ou do texto bruto."""
        if entidades.datas_nascimento:
            try:
                return date.fromisoformat(entidades.datas_nascimento[0])
            except ValueError:
                pass
        return parse_data_nascimento(conteudo)

    def _info_atendimento(self, db: Session, atendimento_id: int, chave: str) -> Optional[str]:
        info = db.query(AtendimentoInfo).filter_by(atendimento_id=atendimento_id, chave=chave).first()
        return info.valor if info else None

    def _salvar_info_atendimento(
        self, db: Session, atendimento_id: int, chave: str, valor: str, pendente: bool = True
    ) -> None:
        info = db.query(AtendimentoInfo).filter_by(atendimento_id=atendimento_id, chave=chave).first()
        if info:
            info.valor = valor
            info.pendente = pendente
        else:
            db.add(
                AtendimentoInfo(
                    atendimento_id=atendimento_id,
                    chave=chave,
                    valor=valor,
                    pendente=pendente,
                    origem=OrigemInfo.USER,
                )
            )
        db.flush()

    def _remover_info_atendimento(self, db: Session, atendimento_id: int, chave: str) -> None:
        db.query(AtendimentoInfo).filter_by(atendimento_id=atendimento_id, chave=chave).delete()
        db.flush()

    def _obter_user_sistema(self, db: Session) -> User:
        """`User` sentinela usado para marcar mensagens auto-aprovadas em
        `execucao_normal` (REQ-011.16) como decididas — sem isso, `aprovador_id=None`
        faria toda mensagem já entregue aparecer como pendente na fila de aprovação."""
        user = db.query(User).filter_by(nome=_USER_SISTEMA_NOME).first()
        if user is None:
            user = User(nome=_USER_SISTEMA_NOME)
            db.add(user)
            db.flush()
        return user

    def _registrar_resultado_credito(self, db: Session, atendimento: Atendimento, resultado) -> None:
        """Registra resultado agregado da consulta de crédito no atendimento (REQ-015)."""
        registros = [
            ("consulta_credito_realizada", str(resultado.consulta_realizada).lower()),
            ("consulta_credito_provedor", resultado.provedor or "nenhum"),
        ]
        if resultado.consulta_realizada:
            registros.append(("restricao_financeira", str(resultado.tem_restricao).lower()))
            if resultado.quantidade_ocorrencias is not None:
                registros.append(("restricao_ocorrencias", str(resultado.quantidade_ocorrencias)))
            if resultado.score is not None:
                registros.append(("score_credito", str(resultado.score)))
        elif resultado.mensagem:
            registros.append(("consulta_credito_obs", resultado.mensagem))

        for chave, valor in registros:
            self._salvar_info_atendimento(db, atendimento.id, chave, valor, pendente=False)

    def _promover_atendimento_empresa(
        self,
        db: Session,
        atendimento: Atendimento,
        empresa: Empresa,
    ) -> Atendimento:
        """Vincula a empresa a um atendimento existente."""
        return atendimentos_svc.promover_atendimento_empresa(db, atendimento, empresa)

    async def _atualizar_infos_atendimento(
        self,
        db: Session,
        atendimento: Atendimento,
        resultado_class,
    ):
        """Registra informações coletadas na AtendimentoInfo."""
        entidades = resultado_class.entidades

        registros = []
        if entidades.nomes:
            registros.append(("nome_contato", entidades.nomes[0]))
        if entidades.emails:
            registros.append(("email_contato", entidades.emails[0]))
        # Fase F: uma vez identificado, o tipo de produto fica travado — uma dúvida
        # tangencial mencionando outro produto (ex.: "vocês têm catraca também?") não pode
        # reescrever `tipos_produto` e quebrar `campos_pendentes()` no meio da coleta. Só
        # grava na primeira vez (o valor ainda pode chegar depois de já estar em
        # Finalizando, ex.: resposta ao fallback PEDIR_TIPO_PRODUTO).
        if entidades.tipos_produto and not self._info_atendimento(db, atendimento.id, "tipos_produto"):
            registros.append(("tipos_produto", ",".join(entidades.tipos_produto)))
        if entidades.quantidades:
            registros.append(("quantidades", ",".join(str(q) for q in entidades.quantidades)))
        # D3: software de controle de ponto mencionado espontaneamente em Esclarecendo.
        if entidades.software_ponto:
            registros.append((CAMPO_SOFTWARE_PONTO.chave, entidades.software_ponto))
        # D3b: software de controle de acesso mencionado espontaneamente.
        if entidades.software_acesso:
            registros.append((CAMPO_SOFTWARE_ACESSO.chave, entidades.software_acesso))
        # D4: tecnologia de leitor mencionada espontaneamente — sinal cru; a Fase F resolve
        # para uma linha real do catálogo (Modelo), não grava direto em modelo_produto.
        if entidades.tipo_leitor_mencionado:
            registros.append(("tipo_leitor_mencionado", entidades.tipo_leitor_mencionado))
        # D4: faixa de funcionários mencionada espontaneamente.
        if entidades.faixa_funcionarios is not None:
            registros.append((CAMPO_FAIXA_FUNCIONARIOS.chave, str(entidades.faixa_funcionarios)))
        # D5: marca e aplicação mencionadas espontaneamente — enriquecem a resolução de modelo.
        if entidades.marca:
            registros.append(("marca", entidades.marca))
        if entidades.aplicacao:
            registros.append(("aplicacao", entidades.aplicacao))
        # D6: atributos genéricos do modelo extraídos da mensagem (ex.: tecnologia_leitura).
        # Cada chave deve coincidir com `atributos_adicionais_modelo.chave` para o filtro.
        chaves_atributos_d6 = set(entidades.atributos.keys())
        for chave, valor in entidades.atributos.items():
            registros.append((chave, valor))

        for chave, valor in registros:
            info = db.query(AtendimentoInfo).filter_by(atendimento_id=atendimento.id, chave=chave).first()
            if chave in chaves_atributos_d6 and info and info.valor:
                # D6: acumula (união) em vez de sobrescrever — o cliente pode mencionar
                # tecnologias diferentes em mensagens distintas (ex.: "biométrico" antes,
                # "ou facial" depois); perder o sinal antigo travaria a resolução do modelo.
                existentes = [v for v in info.valor.split(",") if v]
                novos = [v for v in valor.split(",") if v]
                valor = ",".join(sorted(set(existentes) | set(novos)))
            if info:
                info.valor = valor
                info.pendente = False
            else:
                db.add(
                    AtendimentoInfo(
                        atendimento_id=atendimento.id,
                        chave=chave,
                        valor=valor,
                        pendente=False,
                        origem=OrigemInfo.INFERIDO if resultado_class.origem == "llm" else OrigemInfo.USER,
                    )
                )

        if registros:
            db.commit()
