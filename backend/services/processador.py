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
from datetime import date, datetime
from typing import Optional

from config import settings
from models import (
    Atendimento,
    AtendimentoInfo,
    Contato,
    Empresa,
    FaseAtendimento,
    ItemAtendimento,
    Mensagem,
    ModoOperacao,
    OrigemClassificacao,
    OrigemInfo,
    OrigemMensagem,
    Pessoa,
    ProcessamentoMensagem,
    Produto,
    StatusAtendimento,
    TipoDocumento,
    TipoProduto,
)
from sqlalchemy.orm import Session
from utils.datetime_utils import utc_now

from services import atendimentos as atendimentos_svc
from services.classificador import Intencao, ResultadoClassificacao, classificar
from services.cnpj import ConsultaCnpjError, obter_ou_criar_empresa
from services.cnpj.receitaws import validar_cnpj
from services.conversacao.campos_pendentes import campos_pendentes
from services.conversacao.catalogo_campos import CAMPO_FAIXA_FUNCIONARIOS, CAMPO_MODELO, CAMPO_SOFTWARE_PONTO
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
from services.rag import DocumentoRecuperado, ParRecuperado, QAService, RetrievalService
from services.respostas import GeradorRespostas, MensagemId, RespostaGerada

logger = logging.getLogger(__name__)


# Intencoes que disparam busca na RAG. PERGUNTAR_PRECO esta presente para que possamos registrar os trechos
# relacionados em auditoria, mas a resposta continua sendo o template padrao de encaminhamento para orcamento humano.
_INTENCOES_RAG = frozenset(
    {
        "perguntar_produto",
        "perguntar_preco",
        "fora_contexto",
    }
)

# Intenções comerciais que disparam contato + atendimento anônimos (REQ-002.1B, REQ-016.6).
_INTENCOES_QUALIFICACAO = frozenset(
    {
        Intencao.PEDIR_ORCAMENTO,
        Intencao.PERGUNTAR_PRECO,
        Intencao.PERGUNTAR_PRODUTO,
        Intencao.PERGUNTAR_PRAZO,
    }
)

# Fase E: mapeia a chave técnica de cada CampoDef (catalogo_campos.py) para o template de
# pergunta correspondente (respostas/catalogo.py) — os dois catálogos são propositalmente
# desacoplados (um não conhece o outro), essa é a ponte entre eles.
_MENSAGEM_ID_POR_CAMPO = {
    CAMPO_MODELO.chave: MensagemId.PEDIR_MODELO,
    CAMPO_SOFTWARE_PONTO.chave: MensagemId.PEDIR_SOFTWARE_PONTO,
    CAMPO_FAIXA_FUNCIONARIOS.chave: MensagemId.PEDIR_FAIXA_FUNCIONARIOS,
}

# Fase F (F2): chave de AtendimentoInfo que conta tentativas sem correspondência de
# modelo_produto; após _MODELO_MAX_TENTATIVAS, escala para atendimento humano em vez de
# continuar perguntando (REQ-002.21, CAMPO-modelo — nunca aceita texto livre como modelo).
_MODELO_TENTATIVAS_CHAVE = "modelo_tentativas_falhas"
_MODELO_MAX_TENTATIVAS = 2

# Fase F (F1): captura "solta" para a pergunta pendente atual quando os extratores por
# palavra-gatilho (D3/D4) não reconheceram nada — ex.: "80" sozinho, ou um nome de
# software fora de `_SOFTWARES_PONTO_CONHECIDOS`. Só entra em jogo quando a intenção
# classificada é DESCONHECIDO (nenhuma regra bateu) — ver `_capturar_resposta_direta_pendente`.
_SOFTWARE_NENHUM_REGEX = re.compile(r"\b(n[aã]o|nenhum)\b", re.IGNORECASE)
_NUMERO_SOLTO_REGEX = re.compile(r"\b(\d{1,5})\b")


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
        retrieval: Optional[RetrievalService] = None,
        qa: Optional[QAService] = None,
    ):
        self._llm = llm
        self._gerador = GeradorRespostas(llm=llm, usar_llm=llm is not None)
        self._retrieval = retrieval
        if self._retrieval is None and settings.RAG_ENABLED:
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
                self._retrieval = None
        self._qa = qa
        if self._qa is None and settings.QA_ENABLED:
            try:
                from services.rag import get_qa_service

                self._qa = get_qa_service()
                logger.info("[Processador] QAService inicializado")
            except Exception as e:
                logger.warning(
                    "[Processador] QA desabilitado: falha ao inicializar QAService: %s",
                    e,
                )
                self._qa = None

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
        resultado_class = await classificar(conteudo, llm=self._llm)
        logger.info(
            f"[Processador] Intenção: {resultado_class.intencao.value} (confiança={resultado_class.confianca:.2f},"
            f" via {resultado_class.origem})"
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
            f"intencao={resultado_class.intencao.value} confianca={resultado_class.confianca:.2f}"
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
        )

        dlog.log("processamento_id", f"id={processamento.id} duracao={duracao_ms}ms")

        # 8. Vincula mensagem do cliente ao processamento/contato/atendimento
        msg_in.processamento_id = processamento.id
        if contato:
            msg_in.contato_id = contato.id
            if atendimento:
                msg_in.atendimento_id = atendimento.id
                self._atualizar_ultima_mensagem_at(atendimento, msg_in.timestamp)

        # 9. Persiste resposta do sistema APENAS quando modo=AGENTE.
        # No modo HUMANO, o operador enviará a resposta manualmente pela UI.
        # Mensagem nasce pendente de aprovação: aprovador_id e timestamp_aprovacao
        # ficam NULL até alguém aprovar via POST /api/mensagens/{id}/aprovar.
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
            db.add(msg_out)
        db.commit()

        return ResultadoProcessamento(
            resposta=resposta.texto,
            contato_id=contato.id if contato else None,
            atendimento_id=atendimento.id if atendimento else None,
            processamento_id=processamento.id,
            intencao=resultado_class.intencao.value,
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
            intencao=resultado_class.intencao.value,
            confianca=round(resultado_class.confianca, 2),
            confianca_nivel=resultado_class.confianca_nivel.value,
            origem_classificacao=origem_enum,
            entidades=entidades_dict,
            status_identificacao=identificacao.status.value,
            contato_id_identificado=contato_atual.id if contato_atual else None,
            empresa_id_identificada=empresa_atual.id if empresa_atual else None,
            atendimento_id_ativa=atendimento_atual.id if atendimento_atual else None,
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
        """Decide o que responder com base na identificação e intenção."""
        intencao = resultado_class.intencao
        entidades = resultado_class.entidades

        # Regra: Escalar humano sempre tem prioridade
        if intencao == Intencao.ESCALAR_HUMANO:
            if dlog:
                dlog.log("rota", "ESCALAR_HUMANO → ESCALADO_HUMANO")
            return await self._gerador.gerar(MensagemId.ESCALADO_HUMANO)

        # Regra: Reclamação também escala
        if intencao == Intencao.RECLAMAR:
            if dlog:
                dlog.log("rota", "RECLAMAR → RECLAMACAO_ESCALADA")
            return await self._gerador.gerar(MensagemId.RECLAMACAO_ESCALADA)

        # Se o cliente forneceu CNPJ, processa fluxo PJ
        if entidades.cnpjs:
            if dlog:
                dlog.log("rota", f"cnpj_fornecido={entidades.cnpjs[0]}")
            return await self._processar_cnpj_fornecido(
                db,
                telefone,
                entidades.cnpjs[0],
                nome_informado=entidades.nomes[0] if entidades.nomes else None,
            )

        # Se o cliente forneceu CPF, processa fluxo PF
        if entidades.cpfs:
            if dlog:
                dlog.log("rota", f"cpf_fornecido={mascarar_cpf(entidades.cpfs[0])}")
            data_nasc = self._parse_data_entidade(entidades, conteudo)
            return await self._processar_cpf_fornecido(
                db,
                telefone,
                entidades.cpfs[0],
                nome_informado=entidades.nomes[0] if entidades.nomes else None,
                data_nascimento=data_nasc,
            )

        # Data de nascimento sem CPF na mesma mensagem (continuação do fluxo PF)
        data_nasc_avulsa = self._parse_data_entidade(entidades, conteudo)
        if data_nasc_avulsa:
            contato_pendente = identificacao.contato
            if contato_pendente:
                neg_pendente = self._atendimento_ativo(db, contato_pendente)
                if neg_pendente and neg_pendente.tipo_documento == TipoDocumento.CPF and not neg_pendente.pessoa_id:
                    cpf_pendente = self._info_atendimento(db, neg_pendente.id, "cpf_pendente")
                    if cpf_pendente:
                        if dlog:
                            dlog.log("rota", f"data_nasc_complemento cpf={mascarar_cpf(cpf_pendente)}")
                        return await self._processar_cpf_fornecido(
                            db,
                            telefone,
                            cpf_pendente,
                            nome_informado=contato_pendente.nome,
                            data_nascimento=data_nasc_avulsa,
                        )

        # Telefone novo ou sem empresa -> pedir identificação
        if identificacao.status == StatusIdentificacao.NOVO:
            nome_novo = entidades.nomes[0] if entidades.nomes else None
            tem_documento = bool(entidades.cnpjs or entidades.cpfs)
            ctx_novo = {
                "nome": nome_novo,
                "tem_documento": tem_documento,
            }

            atendimento_novo = None
            if intencao in _INTENCOES_QUALIFICACAO:
                atendimento_novo = await self._garantir_contato_e_atendimento_qualificacao(
                    db, telefone, None, resultado_class, dlog=dlog
                )
            elif nome_novo:
                criar_contato_sem_empresa(db, telefone, nome=nome_novo)

            # D1 (REQ-002.1B): categoria 3 (dúvida sobre produto/preço/fora de contexto) é
            # respondida via Q&A/RAG imediatamente — não espera CNPJ/CPF nem intenção de orçamento.
            if intencao.value in _INTENCOES_RAG:
                if dlog:
                    dlog.log("rota", f"NOVO + categoria 3 ({intencao.value}) → Q&A/RAG sem pedir documento")
                return await self._responder_categoria3(intencao, conteudo, dlog=dlog)

            if intencao == Intencao.PEDIR_ORCAMENTO:
                if dlog:
                    dlog.log("rota", "NOVO + PEDIR_ORCAMENTO → composta (Finalizando)")
                ctx_novo["modo"] = "orcamento"
                partes_finalizando = await self._iniciar_ou_continuar_finalizando(db, atendimento_novo, dlog=dlog)
                return await self._gerador.gerar_composta(
                    [(MensagemId.SAUDACAO_NOVO_CONTATO, ctx_novo), *partes_finalizando]
                )

            if dlog:
                dlog.log("rota", "NOVO → SAUDACAO_NOVO_CONTATO")
            ctx_novo["modo"] = "identificacao"
            return await self._gerador.gerar(MensagemId.SAUDACAO_NOVO_CONTATO, ctx_novo)

        if identificacao.status == StatusIdentificacao.MULTIPLO:
            if dlog:
                dlog.log("rota", "MULTIPLO → MULTIPLAS_EMPRESAS")
            nomes_empresas = ", ".join(e.nome for e in identificacao.empresas[:5])
            return await self._gerador.gerar(
                MensagemId.MULTIPLAS_EMPRESAS,
                contexto={"empresas": nomes_empresas},
            )

        if identificacao.status == StatusIdentificacao.SEM_EMPRESA:
            contato = identificacao.contato
            if contato:
                neg = self._atendimento_ativo(db, contato)
                if neg and neg.fase == FaseAtendimento.FINALIZANDO:
                    await self._atualizar_infos_atendimento(db, neg, resultado_class)
                    if dlog:
                        dlog.log("rota", f"SEM_EMPRESA + Finalizando → coleta ativa (atendimento id={neg.id})")
                    return await self._processar_finalizando(db, neg, conteudo, resultado_class, dlog=dlog)
                if neg and neg.pessoa_id and neg.pessoa:
                    if entidades.nomes and not contato.nome:
                        contato.nome = entidades.nomes[0]
                        db.commit()
                    await self._atualizar_infos_atendimento(db, neg, resultado_class)
                    if dlog:
                        dlog.log("rota", f"PF identificada pessoa_id={neg.pessoa_id} intencao={intencao.value}")
                    return await self._gerar_resposta_por_intencao(
                        db=db,
                        atendimento=neg,
                        intencao=intencao,
                        contato=contato,
                        empresa=None,
                        pessoa=neg.pessoa,
                        conteudo_cliente=conteudo,
                        dlog=dlog,
                    )
                if intencao in _INTENCOES_QUALIFICACAO:
                    if entidades.nomes and not contato.nome:
                        contato.nome = entidades.nomes[0]
                        db.commit()
                    neg = self._obter_ou_criar_atendimento(db, contato)
                    await self._atualizar_infos_atendimento(db, neg, resultado_class)
                    if dlog:
                        dlog.log("rota", f"SEM_EMPRESA + qualificação → atendimento id={neg.id}")
                    return await self._gerar_resposta_por_intencao(
                        db=db,
                        atendimento=neg,
                        intencao=intencao,
                        contato=contato,
                        empresa=None,
                        pessoa=None,
                        conteudo_cliente=conteudo,
                        dlog=dlog,
                    )
                # D1 (REQ-002.1B): categoria 3 responde via Q&A/RAG mesmo sem CNPJ ainda
                # (ex.: FORA_CONTEXTO, que não entra em _INTENCOES_QUALIFICACAO acima).
                if intencao.value in _INTENCOES_RAG:
                    if dlog:
                        dlog.log("rota", f"SEM_EMPRESA + categoria 3 ({intencao.value}) → Q&A/RAG sem pedir CNPJ")
                    return await self._responder_categoria3(intencao, conteudo, dlog=dlog)
            if dlog:
                dlog.log("rota", "SEM_EMPRESA → PERGUNTAR_CNPJ")
            nome_contato = contato.nome if contato else None
            return await self._gerador.gerar(
                MensagemId.PERGUNTAR_CNPJ,
                contexto={"nome": nome_contato},
            )

        # A partir daqui: contato identificado com empresa
        contato = identificacao.contato
        empresa = identificacao.empresa

        # Atualiza nome se cliente informou
        if entidades.nomes and contato and not contato.nome:
            contato.nome = entidades.nomes[0]
            db.commit()

        # Carrega/cria atendimento ativo
        atendimento = self._obter_ou_criar_atendimento(db, contato, empresa)

        # Salva informações coletadas
        await self._atualizar_infos_atendimento(db, atendimento, resultado_class)

        if atendimento.fase == FaseAtendimento.FINALIZANDO:
            if dlog:
                dlog.log("rota", f"identificado + Finalizando → coleta ativa (atendimento id={atendimento.id})")
            return await self._processar_finalizando(db, atendimento, conteudo, resultado_class, dlog=dlog)

        # Roteia por intenção
        return await self._gerar_resposta_por_intencao(
            db=db,
            atendimento=atendimento,
            intencao=intencao,
            contato=contato,
            empresa=empresa,
            pessoa=None,
            conteudo_cliente=conteudo,
            dlog=dlog,
        )

    async def _gerar_resposta_por_intencao(
        self,
        db: Session,
        atendimento: Atendimento,
        intencao: Intencao,
        contato: Contato,
        empresa: Optional[Empresa],
        conteudo_cliente: str,
        pessoa: Optional[Pessoa] = None,
        dlog: Optional[DebugLogger] = None,
    ) -> RespostaGerada:
        """Gera resposta baseado na intenção (com contato já identificado)."""
        nome = contato.nome or (pessoa.nome if pessoa else "") or ""
        if dlog:
            if empresa:
                dlog.log("rota", f"identificado empresa='{empresa.nome[:30]}' intencao={intencao.value}")
            elif pessoa:
                dlog.log("rota", f"identificado PF pessoa_id={pessoa.id} intencao={intencao.value}")

        if intencao == Intencao.SAUDACAO:
            if nome:
                return await self._gerador.gerar(MensagemId.SAUDACAO_COM_NOME, {"nome": nome})
            return await self._gerador.gerar(MensagemId.PERGUNTAR_NOME)

        if intencao == Intencao.PERGUNTAR_PRAZO:
            return await self._gerador.gerar(
                MensagemId.PRAZO_NAO_PROMETIDO,
                personalizar=True,
                mensagem_cliente=conteudo_cliente,
            )

        if intencao in (Intencao.PERGUNTAR_PRECO, Intencao.PERGUNTAR_PRODUTO, Intencao.FORA_CONTEXTO):
            return await self._responder_categoria3(intencao, conteudo_cliente, dlog=dlog)

        if intencao == Intencao.PEDIR_ORCAMENTO:
            partes = await self._iniciar_ou_continuar_finalizando(db, atendimento, dlog=dlog)
            if len(partes) == 1:
                mensagem_id, ctx = partes[0]
                return await self._gerador.gerar(mensagem_id, ctx)
            return await self._gerador.gerar_composta(partes)

        if intencao == Intencao.APROVAR_ORCAMENTO:
            return await self._gerador.gerar(MensagemId.ORCAMENTO_APROVADO)

        if intencao == Intencao.REPROVAR_ORCAMENTO:
            return await self._gerador.gerar(MensagemId.ORCAMENTO_REPROVADO)

        # Fallback: tenta QA/RAG antes de NAO_ENTENDI
        par = await self._buscar_resposta_qa(conteudo_cliente, dlog=dlog)
        if par is not None:
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
            )

        if dlog:
            dlog.log("rota", f"intencao={intencao.value} não mapeada → NAO_ENTENDI")
        return await self._gerador.gerar(
            MensagemId.NAO_ENTENDI,
            personalizar=True,
            mensagem_cliente=conteudo_cliente,
        )

    async def _responder_categoria3(
        self,
        intencao: Intencao,
        conteudo_cliente: str,
        dlog: Optional[DebugLogger] = None,
    ) -> RespostaGerada:
        """Responde intenção de categoria 3 (REQ-002.1) — dúvida sobre produto/preço/fora de
        contexto — via Q&A/RAG.

        Compartilhado entre clientes já identificados (`_gerar_resposta_por_intencao`) e o
        roteamento pré-identificação do D1/REQ-002.1B (`_decidir_resposta`) — mesmo
        comportamento, não importa se o CNPJ/CPF já foi informado.
        """
        if intencao == Intencao.PERGUNTAR_PRECO:
            # Plano v1: para perguntas de preco a resposta e sempre o template
            # padrao de encaminhamento. Ainda assim, rodamos a RAG para
            # registrar trechos relacionados em auditoria.
            trechos_preco = await self._buscar_trechos_rag(conteudo_cliente, dlog=dlog)
            resposta = await self._gerador.gerar(
                MensagemId.PRECO_NAO_NEGOCIADO,
                personalizar=True,
                mensagem_cliente=conteudo_cliente,
            )
            _anexar_trechos_para_auditoria(resposta, trechos_preco)
            return resposta

        if intencao == Intencao.PERGUNTAR_PRODUTO:
            return await self._responder_com_rag(
                conteudo_cliente=conteudo_cliente,
                template_fallback=MensagemId.PRODUTO_SEM_CONTEXTO,
                dlog=dlog,
            )

        # FORA_CONTEXTO
        return await self._responder_com_rag(
            conteudo_cliente=conteudo_cliente,
            template_fallback=MensagemId.FORA_CONTEXTO,
            dlog=dlog,
        )

    # ------------------------------------------------------------------
    # Transição Esclarecendo → Finalizando (Fase E)
    # ------------------------------------------------------------------

    async def _iniciar_ou_continuar_finalizando(
        self,
        db: Session,
        atendimento: Atendimento,
        dlog: Optional[DebugLogger] = None,
    ) -> list[tuple[MensagemId, Optional[dict]]]:
        """E1 + E3: transita `fase` para Finalizando (se ainda não estiver lá) e decide a
        próxima pergunta. Retorna as partes prontas para `gerar`/`gerar_composta`.

        A mensagem que disparou `PEDIR_ORCAMENTO` já foi processada por
        `_atualizar_infos_atendimento` antes desta chamada (D2/D3/D4) — então, se ela também
        trouxe uma resposta (ex.: "quero orçamento, já uso o Domínio"), `campos_pendentes()`
        já reflete isso e não repete a pergunta correspondente (`nao_perguntar_de_novo`, C3).
        """
        if atendimento.fase != FaseAtendimento.FINALIZANDO:
            atendimento.fase = FaseAtendimento.FINALIZANDO
            db.commit()
            if dlog:
                dlog.log("fase", f"Esclarecendo → Finalizando (atendimento id={atendimento.id})")

        pendentes = campos_pendentes(atendimento)
        if not pendentes:
            # Tipo de produto ainda não identificado (mais comum), ou — caso raro nesta
            # fatia — tudo já capturado; Fase F (F4) vai substituir isto por um resumo real.
            if dlog:
                dlog.log("finalizando", "sem campos pendentes ainda → PEDIR_TIPO_PRODUTO")
            return [(MensagemId.PEDIR_TIPO_PRODUTO, None)]

        campo = pendentes[0]
        mensagem_id = _MENSAGEM_ID_POR_CAMPO.get(campo.chave, MensagemId.PEDIR_TIPO_PRODUTO)
        if dlog:
            dlog.log("finalizando", f"próxima pergunta: {campo.chave} ({mensagem_id.name})")
        return [(MensagemId.INICIAR_FINALIZANDO, None), (mensagem_id, None)]

    # ------------------------------------------------------------------
    # Coleta ativa em Finalizando (Fase F)
    # ------------------------------------------------------------------

    async def _processar_finalizando(
        self,
        db: Session,
        atendimento: Atendimento,
        conteudo: str,
        resultado_class: ResultadoClassificacao,
        dlog: Optional[DebugLogger] = None,
    ) -> RespostaGerada:
        """F1: loop de coleta ativa — roda a cada mensagem em Finalizando, testando contra
        todas as perguntas pendentes (não só "a próxima"), em vez de rotear só pela
        intenção classificada.

        `_atualizar_infos_atendimento` (D2/D3/D4) já rodou antes desta chamada e capturou o
        que os extratores por palavra-gatilho reconheceram. A partir daqui: (a) tenta
        resolver `modelo_produto` contra o catálogo real (F2) — a extração de
        `tipo_leitor_mencionado` independe da intenção classificada, então roda mesmo se a
        mensagem também parecer uma dúvida; (b) se for dúvida (categoria 3), responde via
        Q&A/RAG e retoma a pergunta pendente (F3); (c) senão, tenta uma captura solta para
        a pergunta pendente atual (F1); (d) recalcula o que falta e pergunta, ou fecha com
        o resumo (F4).
        """
        pendentes_antes = campos_pendentes(atendimento)
        tentou_modelo = bool(
            pendentes_antes
            and pendentes_antes[0].chave == CAMPO_MODELO.chave
            and resultado_class.entidades.tipo_leitor_mencionado
        )

        await self._tentar_resolver_modelo(db, atendimento, resultado_class, dlog=dlog)
        if atendimento.modo_operacao == ModoOperacao.HUMANO:
            # F2: acabou de escalar por falta de correspondência de modelo — não continua.
            return await self._gerador.gerar(MensagemId.ESCALADO_HUMANO)

        if resultado_class.intencao.value in _INTENCOES_RAG:
            return await self._retomar_apos_duvida(db, atendimento, conteudo, resultado_class, dlog=dlog)

        if not tentou_modelo:
            self._capturar_resposta_direta_pendente(db, atendimento, conteudo, resultado_class, dlog=dlog)

        pendentes = campos_pendentes(atendimento)
        if not pendentes:
            return await self._gerar_resumo_finalizando(atendimento, dlog=dlog)

        campo = pendentes[0]
        mensagem_id = _MENSAGEM_ID_POR_CAMPO.get(campo.chave, MensagemId.PEDIR_TIPO_PRODUTO)
        if dlog:
            dlog.log("finalizando", f"próxima pergunta pendente: {campo.chave} ({mensagem_id.name})")
        return await self._gerador.gerar(mensagem_id)

    async def _tentar_resolver_modelo(
        self,
        db: Session,
        atendimento: Atendimento,
        resultado_class: ResultadoClassificacao,
        dlog: Optional[DebugLogger] = None,
    ) -> None:
        """F2: resolve `modelo_produto` para uma linha real de `Produto`, ou escala para
        atendimento humano após `_MODELO_MAX_TENTATIVAS` sem correspondência — nunca aceita
        o texto do cliente como modelo (REQ-002.21, CAMPO-modelo).

        `Produto`/`TipoProduto` ainda não têm dados semeados neste ambiente — a busca
        abaixo é a correta para quando houver catálogo real, mas hoje sempre cai no
        caminho "sem correspondência" e conta como tentativa.
        """
        pendentes = campos_pendentes(atendimento)
        if not pendentes or pendentes[0].chave != CAMPO_MODELO.chave:
            return

        tipo_leitor = resultado_class.entidades.tipo_leitor_mencionado
        if not tipo_leitor:
            return  # mensagem não tentou responder o modelo — não conta tentativa

        candidato = (
            db.query(Produto)
            .join(TipoProduto, Produto.tipo_produto_id == TipoProduto.id)
            .filter(
                TipoProduto.descricao.ilike("%ponto%"),
                Produto.descricao.ilike(f"%{tipo_leitor}%"),
                Produto.ativo.is_(True),
            )
            .first()
        )
        if candidato:
            item = self._item_atendimento_atual(db, atendimento, candidato.tipo_produto_id)
            item.produto_id = candidato.id
            db.commit()
            self._remover_info_atendimento(db, atendimento.id, _MODELO_TENTATIVAS_CHAVE)
            if dlog:
                dlog.log("finalizando", f"modelo resolvido: produto_id={candidato.id} ({candidato.descricao})")
            return

        tentativas = int(self._info_atendimento(db, atendimento.id, _MODELO_TENTATIVAS_CHAVE) or 0) + 1
        self._salvar_info_atendimento(db, atendimento.id, _MODELO_TENTATIVAS_CHAVE, str(tentativas))
        if dlog:
            dlog.log(
                "finalizando",
                f"modelo sem correspondência (tipo_leitor={tipo_leitor}) tentativa={tentativas}",
            )

        if tentativas >= _MODELO_MAX_TENTATIVAS:
            atendimento.modo_operacao = ModoOperacao.HUMANO
            db.commit()
            if dlog:
                dlog.log(
                    "finalizando",
                    f"modelo sem correspondência após {tentativas} tentativas → escalar_humano",
                )

    def _item_atendimento_atual(
        self,
        db: Session,
        atendimento: Atendimento,
        tipo_produto_id: int,
    ) -> ItemAtendimento:
        """MVP: um único item por atendimento (só relógio de ponto) — get-or-create."""
        item = next(iter(atendimento.itens), None)
        if item is None:
            item = ItemAtendimento(atendimento_id=atendimento.id, tipo_produto_id=tipo_produto_id, quantidade=1)
            db.add(item)
            db.flush()
        return item

    def _capturar_resposta_direta_pendente(
        self,
        db: Session,
        atendimento: Atendimento,
        conteudo: str,
        resultado_class: ResultadoClassificacao,
        dlog: Optional[DebugLogger] = None,
    ) -> None:
        """F1: cobre respostas soltas que os extratores por palavra-gatilho (D3/D4) não
        reconhecem sozinhos — ex.: "80" sozinho para faixa de funcionários, ou um nome de
        software fora de `_SOFTWARES_PONTO_CONHECIDOS` (aceito livremente, ao contrário de
        modelo — CAMPO-software-ponto não exige catálogo). Só atua sobre a pergunta
        pendente atual (a que acabamos de fazer), e só quando a mensagem não bateu em
        nenhuma regra de intenção conhecida (DESCONHECIDO) — uma intenção reconhecida (ex.:
        "quero orçamento" repetido) não deve ser sequestrada como se fosse resposta.
        """
        if resultado_class.intencao != Intencao.DESCONHECIDO:
            return

        pendentes = campos_pendentes(atendimento)
        if not pendentes:
            return
        campo = pendentes[0]

        if campo.chave == CAMPO_FAIXA_FUNCIONARIOS.chave:
            match = _NUMERO_SOLTO_REGEX.search(conteudo)
            if match:
                self._salvar_info_atendimento(db, atendimento.id, campo.chave, match.group(1))
                if dlog:
                    dlog.log("finalizando", f"faixa_funcionarios capturado (resposta solta): {match.group(1)}")

        elif campo.chave == CAMPO_SOFTWARE_PONTO.chave:
            texto = conteudo.strip()
            if not texto:
                return
            valor = "nenhum" if _SOFTWARE_NENHUM_REGEX.search(texto) else texto
            self._salvar_info_atendimento(db, atendimento.id, campo.chave, valor)
            if dlog:
                dlog.log("finalizando", f"software_controle_ponto capturado (resposta livre): {valor}")

    async def _retomar_apos_duvida(
        self,
        db: Session,
        atendimento: Atendimento,
        conteudo: str,
        resultado_class: ResultadoClassificacao,
        dlog: Optional[DebugLogger] = None,
    ) -> RespostaGerada:
        """F3: se a mensagem em Finalizando for uma dúvida (categoria 3), responde via
        Q&A/RAG e reapresenta a última pergunta pendente — sem perder o progresso da
        coleta (a fase continua Finalizando)."""
        resposta_duvida = await self._responder_categoria3(resultado_class.intencao, conteudo, dlog=dlog)

        pendentes = campos_pendentes(atendimento)
        if not pendentes:
            if dlog:
                dlog.log("finalizando", "dúvida em Finalizando, sem pendências → só responde a dúvida")
            return resposta_duvida

        campo = pendentes[0]
        mensagem_id = _MENSAGEM_ID_POR_CAMPO.get(campo.chave, MensagemId.PEDIR_TIPO_PRODUTO)
        resposta_pergunta = await self._gerador.gerar(mensagem_id)
        resposta_retomada = await self._gerador.gerar(
            MensagemId.RETOMAR_PERGUNTA_PENDENTE, {"pergunta": resposta_pergunta.texto}
        )
        if dlog:
            dlog.log("finalizando", f"dúvida ({resultado_class.intencao.value}) → retoma {campo.chave}")
        return RespostaGerada(
            texto=f"{resposta_duvida.texto}\n\n{resposta_retomada.texto}",
            template_usado=f"{resposta_duvida.template_usado}+{resposta_retomada.template_usado}",
            personalizado_via_llm=resposta_duvida.personalizado_via_llm,
            llm_tokens_input=resposta_duvida.llm_tokens_input,
            llm_tokens_output=resposta_duvida.llm_tokens_output,
            rag_utilizada=resposta_duvida.rag_utilizada,
            trechos_rag=resposta_duvida.trechos_rag,
            rag_score_maximo=resposta_duvida.rag_score_maximo,
        )

    async def _gerar_resumo_finalizando(
        self,
        atendimento: Atendimento,
        dlog: Optional[DebugLogger] = None,
    ) -> RespostaGerada:
        """F4: nada mais pendente — apresenta resumo do que foi coletado e pede confirmação."""
        valores = {info.chave: info.valor for info in atendimento.informacoes}
        item_resolvido = next((item for item in atendimento.itens if item.produto_id is not None), None)
        ctx = {
            "modelo": item_resolvido.produto.descricao if item_resolvido and item_resolvido.produto else None,
            "software": valores.get(CAMPO_SOFTWARE_PONTO.chave),
            "faixa_funcionarios": valores.get(CAMPO_FAIXA_FUNCIONARIOS.chave),
        }
        if dlog:
            dlog.log("finalizando", f"tudo capturado → resumo (modelo={ctx['modelo']})")
        return await self._gerador.gerar(MensagemId.RESUMO_FINALIZANDO, ctx)

    # ------------------------------------------------------------------
    # RAG helpers
    # ------------------------------------------------------------------

    async def _buscar_resposta_qa(
        self,
        query: str,
        dlog: Optional[DebugLogger] = None,
    ) -> Optional[ParRecuperado]:
        """Busca o melhor par Q&A para a query; retorna None se nao encontrado."""
        if not settings.QA_ENABLED or self._qa is None:
            if dlog:
                dlog.log("qa_busca", "QA desabilitado ou servico nao inicializado")
            return None
        if dlog:
            dlog.log("qa_busca", f'query="{query[:80]}" score_min={self._qa._score_minimo_padrao}')
        try:
            pares = await self._qa.buscar(
                query=query,
                apenas_aprovados=settings.QA_APENAS_APROVADOS,
            )
            if pares:
                top = pares[0]
                if dlog:
                    dlog.log(
                        "qa_resultado",
                        f"hit score={top.score:.4f} id={top.id_externo} pergunta='{top.pergunta[:50]}'",
                    )
                return top
            if dlog:
                dlog.log("qa_resultado", f"sem hits (score_min={self._qa._score_minimo_padrao})")
            return None
        except Exception as e:
            logger.warning("[Processador] Falha na busca QA: %s", e)
            if dlog:
                dlog.log("qa_erro", f"{type(e).__name__}: {str(e)[:80]}")
            return None

    async def _buscar_trechos_rag(
        self,
        query: str,
        dlog: Optional[DebugLogger] = None,
    ) -> list[DocumentoRecuperado]:
        """Busca trechos na RAG, tolerando RAG desabilitada ou em falha."""
        if not settings.RAG_ENABLED or self._retrieval is None:
            if dlog:
                dlog.log("rag_busca", "RAG desabilitada ou retrieval não inicializado")
            return []
        score_min = self._retrieval._score_minimo_padrao
        if dlog:
            dlog.log("rag_busca", f'query="{query[:80]}" score_min={score_min}')
        try:
            trechos = await self._retrieval.buscar(query=query, tipo=None)
            if dlog:
                if trechos:
                    top = trechos[0]
                    dlog.log(
                        "rag_resultado",
                        f"encontrados={len(trechos)} melhor_score={top.score:.4f} titulo='{str(top.titulo)[:50]}'",
                    )
                else:
                    dlog.log("rag_resultado", f"encontrados=0 (score_min={score_min})")
            return trechos
        except Exception as e:
            logger.warning("[Processador] Falha na busca RAG: %s", e)
            if dlog:
                dlog.log("rag_erro", f"{type(e).__name__}: {str(e)[:80]}")
            return []

    async def _responder_com_rag(
        self,
        conteudo_cliente: str,
        template_fallback: MensagemId,
        dlog: Optional[DebugLogger] = None,
    ) -> RespostaGerada:
        """Busca pares/trechos e gera resposta; Q&A tem prioridade sobre chunks."""
        codigo_fallback = template_fallback.name
        # Camada 1: Q&A pairs curados
        par = await self._buscar_resposta_qa(conteudo_cliente, dlog=dlog)
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
        trechos = await self._buscar_trechos_rag(conteudo_cliente, dlog=dlog)
        if not trechos:
            if dlog:
                dlog.log("rag_decisao", f"sem trechos → fallback template={codigo_fallback}")
            resposta = await self._gerador.gerar(template_fallback)
            resposta.rag_utilizada = settings.RAG_ENABLED and self._retrieval is not None
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

    @staticmethod
    def _atualizar_ultima_mensagem_at(
        atendimento: Atendimento,
        quando: Optional[datetime] = None,
    ) -> None:
        """Atualiza timestamp da última mensagem do cliente (REQ-016 T-A3)."""
        atendimento.ultima_mensagem_at = quando or utc_now()

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

    def _salvar_info_atendimento(self, db: Session, atendimento_id: int, chave: str, valor: str) -> None:
        info = db.query(AtendimentoInfo).filter_by(atendimento_id=atendimento_id, chave=chave).first()
        if info:
            info.valor = valor
            info.pendente = True
        else:
            db.add(
                AtendimentoInfo(
                    atendimento_id=atendimento_id,
                    chave=chave,
                    valor=valor,
                    pendente=True,
                    origem=OrigemInfo.USER,
                )
            )
        db.commit()

    def _remover_info_atendimento(self, db: Session, atendimento_id: int, chave: str) -> None:
        db.query(AtendimentoInfo).filter_by(atendimento_id=atendimento_id, chave=chave).delete()
        db.commit()

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
            self._salvar_info_atendimento(db, atendimento.id, chave, valor)
            info = db.query(AtendimentoInfo).filter_by(atendimento_id=atendimento.id, chave=chave).first()
            if info:
                info.pendente = False
                db.commit()

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
        # Fase F: uma vez em Finalizando, o tipo de produto já está decidido — uma dúvida
        # tangencial mencionando outro produto (ex.: "vocês têm catraca também?") não pode
        # reescrever `tipos_produto` e quebrar `campos_pendentes()` no meio da coleta.
        if entidades.tipos_produto and atendimento.fase != FaseAtendimento.FINALIZANDO:
            registros.append(("tipos_produto", ",".join(entidades.tipos_produto)))
        if entidades.quantidades:
            registros.append(("quantidades", ",".join(str(q) for q in entidades.quantidades)))
        # D3: software de controle de ponto mencionado espontaneamente em Esclarecendo.
        if entidades.software_ponto:
            registros.append((CAMPO_SOFTWARE_PONTO.chave, entidades.software_ponto))
        # D4: tecnologia de leitor mencionada espontaneamente — sinal cru; a Fase F resolve
        # para uma linha real do catálogo (Modelo), não grava direto em modelo_produto.
        if entidades.tipo_leitor_mencionado:
            registros.append(("tipo_leitor_mencionado", entidades.tipo_leitor_mencionado))
        # D4: faixa de funcionários mencionada espontaneamente.
        if entidades.faixa_funcionarios is not None:
            registros.append((CAMPO_FAIXA_FUNCIONARIOS.chave, str(entidades.faixa_funcionarios)))

        for chave, valor in registros:
            info = db.query(AtendimentoInfo).filter_by(atendimento_id=atendimento.id, chave=chave).first()
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


def _anexar_trechos_para_auditoria(
    resposta: RespostaGerada,
    trechos: list[DocumentoRecuperado],
) -> None:
    """Popula `trechos_rag` e `rag_score_maximo` sem alterar o texto da resposta.

    Usado quando a RAG e acionada apenas para auditoria (ex: PERGUNTAR_PRECO),
    mantendo o template padrao como resposta ao cliente.
    """
    if not trechos:
        return
    resumo = [
        {
            "id": getattr(t, "id", None),
            "id_externo": getattr(t, "id_externo", None),
            "tipo": getattr(t, "tipo", None),
            "titulo": getattr(t, "titulo", None),
            "score": float(getattr(t, "score", 0.0) or 0.0),
            "distancia": float(getattr(t, "distancia", 0.0) or 0.0),
            "url": (getattr(t, "metadados", None) or {}).get("url"),
        }
        for t in trechos
    ]
    resposta.rag_utilizada = True
    resposta.trechos_rag = resumo
    resposta.rag_score_maximo = max(r["score"] for r in resumo)
