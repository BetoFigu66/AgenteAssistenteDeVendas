"""
Orquestrador principal - processa mensagens recebidas do cliente.

Fluxo:
1. Salva mensagem recebida
2. Identifica contato/empresa pelo telefone
3. Carrega/cria negociação ativa
4. Classifica intenção + extrai entidades
5. Atualiza estado (CNPJ, nome, itens, etc.)
6. Gera resposta
7. Salva resposta
"""
import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional

from sqlalchemy.orm import Session

from config import settings
from models import (
    Contato,
    Empresa,
    Mensagem,
    ModoOperacao,
    Negociacao,
    NegociacaoInfo,
    OrigemClassificacao,
    OrigemInfo,
    OrigemMensagem,
    ProcessamentoMensagem,
    StatusNegociacao,
)
from services.classificador import Intencao, ResultadoClassificacao, classificar
from services.cnpj import ConsultaCnpjError, obter_ou_criar_empresa
from services.cnpj.receitaws import formatar_cnpj, normalizar_cnpj, validar_cnpj
from services.identificador import (
    ResultadoIdentificacao,
    StatusIdentificacao,
    criar_contato,
    identificar_por_telefone,
    normalizar_telefone,
)
from services.llm import LLMProvider
from services.debug_log import DebugLogger
from services.rag import DocumentoRecuperado, ParRecuperado, QAService, RetrievalService
from services.respostas import GeradorRespostas, RespostaGerada
from services.respostas import templates as T

logger = logging.getLogger(__name__)


# Intencoes que disparam busca na RAG. PERGUNTAR_PRECO esta presente para que
# possamos registrar os trechos relacionados em auditoria, mas a resposta
# continua sendo o template padrao de encaminhamento para orcamento humano.
_INTENCOES_RAG = frozenset({
    "perguntar_produto",
    "perguntar_preco",
    "fora_contexto",
})


@dataclass
class ResultadoProcessamento:
    """Resultado do processamento de uma mensagem."""
    resposta: str
    contato_id: Optional[int] = None
    negociacao_id: Optional[int] = None
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
        
        # 1. Salva mensagem do cliente (ainda sem contato/negociação)
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
        dlog.log("entrada", f'msg="{conteudo[:120].replace(chr(10), " ")}"')

        # 2. Identifica remetente
        identificacao = identificar_por_telefone(db, telefone_norm)
        logger.info(f"[Processador] Identificação: {identificacao.status.value}")
        dlog.log(
            "identificacao",
            "status=" + identificacao.status.value
            + (f" empresa='{identificacao.empresa.nome[:30]}'" if identificacao.empresa else "")
            + (f" contato_id={identificacao.contato.id}" if identificacao.contato else ""),
        )
        
        # 3. Classifica intenção e extrai entidades
        resultado_class = await classificar(conteudo, llm=self._llm)
        logger.info(
            f"[Processador] Intenção: {resultado_class.intencao.value} "
            f"(confiança={resultado_class.confianca:.2f}, via {resultado_class.origem})"
        )
        _ent = resultado_class.entidades
        _ent_str = (
            (f" cnpjs={_ent.cnpjs}" if _ent.cnpjs else "")
            + (f" produtos={_ent.tipos_produto}" if _ent.tipos_produto else "")
            + (f" qtd={_ent.quantidades}" if _ent.quantidades else "")
        )
        dlog.log(
            "intent",
            f"intencao={resultado_class.intencao.value} confianca={resultado_class.confianca:.2f}"
            f" via={resultado_class.origem}{_ent_str}",
        )
        
        # 4. Verifica modo de operação da negociação ativa (se existir)
        # Se modo=HUMANO, o sistema processa/classifica mas NÃO gera resposta.
        contato_inicial = identificacao.contato
        negociacao_inicial = (
            self._negociacao_ativa(db, contato_inicial) if contato_inicial else None
        )
        modo_humano = (
            negociacao_inicial is not None
            and negociacao_inicial.modo_operacao == ModoOperacao.HUMANO
        )
        if modo_humano:
            logger.info(
                f"[Processador] Negociação {negociacao_inicial.id} em modo HUMANO — "
                f"não gerando resposta automática."
            )
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
        negociacao = self._negociacao_ativa(db, contato) if contato else None
        
        # 7. Registra processamento (auditoria/debug) — sempre, independente do modo
        dlog.log(
            "saida",
            f'template={resposta.template_usado or "nenhum"}'
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
            negociacao_atual=negociacao,
            resposta=resposta,
            duracao_ms=duracao_ms,
            erro=erro_processamento,
        )
        
        dlog.log("processamento_id", f"id={processamento.id} duracao={duracao_ms}ms")

        # 8. Vincula mensagem do cliente ao processamento/contato/negociação
        msg_in.processamento_id = processamento.id
        if contato:
            msg_in.contato_id = contato.id
            if negociacao:
                msg_in.negociacao_id = negociacao.id
        
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
                negociacao_id=negociacao.id if negociacao else None,
                aprovador_id=None,
                timestamp_aprovacao=None,
            )
            db.add(msg_out)
        db.commit()
        
        return ResultadoProcessamento(
            resposta=resposta.texto,
            contato_id=contato.id if contato else None,
            negociacao_id=negociacao.id if negociacao else None,
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
        negociacao_atual: Optional[Negociacao],
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
            "nomes": resultado_class.entidades.nomes,
            "tipos_produto": resultado_class.entidades.tipos_produto,
            "quantidades": resultado_class.entidades.quantidades,
            "emails": resultado_class.entidades.emails,
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
            origem_classificacao=origem_enum,
            entidades=entidades_dict,
            status_identificacao=identificacao.status.value,
            contato_id_identificado=contato_atual.id if contato_atual else None,
            empresa_id_identificada=empresa_atual.id if empresa_atual else None,
            negociacao_id_ativa=negociacao_atual.id if negociacao_atual else None,
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
            return await self._gerador.gerar(T.ESCALADO_HUMANO)
        
        # Regra: Reclamação também escala
        if intencao == Intencao.RECLAMAR:
            if dlog:
                dlog.log("rota", "RECLAMAR → RECLAMACAO_ESCALADA")
            return await self._gerador.gerar(T.RECLAMACAO_ESCALADA)
        
        # Se o cliente forneceu CNPJ, processa
        if entidades.cnpjs:
            if dlog:
                dlog.log("rota", f"cnpj_fornecido={entidades.cnpjs[0]}")
            return await self._processar_cnpj_fornecido(
                db, telefone, entidades.cnpjs[0],
                nome_informado=entidades.nomes[0] if entidades.nomes else None,
            )
        
        # Telefone novo ou sem empresa -> pedir identificação
        if identificacao.status == StatusIdentificacao.NOVO:
            if dlog:
                dlog.log("rota", "NOVO → SAUDACAO_NOVO_CONTATO")
            return await self._gerador.gerar(T.SAUDACAO_NOVO_CONTATO)
        
        if identificacao.status == StatusIdentificacao.MULTIPLO:
            if dlog:
                dlog.log("rota", "MULTIPLO → MULTIPLAS_EMPRESAS")
            nomes_empresas = ", ".join(e.nome for e in identificacao.empresas[:5])
            return await self._gerador.gerar(
                T.MULTIPLAS_EMPRESAS,
                contexto={"empresas": nomes_empresas},
            )
        
        if identificacao.status == StatusIdentificacao.SEM_EMPRESA:
            if dlog:
                dlog.log("rota", "SEM_EMPRESA → PERGUNTAR_CNPJ")
            return await self._gerador.gerar(T.PERGUNTAR_CNPJ)
        
        # A partir daqui: contato identificado com empresa
        contato = identificacao.contato
        empresa = identificacao.empresa
        
        # Atualiza nome se cliente informou
        if entidades.nomes and contato and not contato.nome:
            contato.nome = entidades.nomes[0]
            db.commit()
        
        # Carrega/cria negociação ativa
        negociacao = self._obter_ou_criar_negociacao(db, contato, empresa)
        
        # Salva informações coletadas
        await self._atualizar_infos_negociacao(db, negociacao, resultado_class)
        
        # Roteia por intenção
        return await self._gerar_resposta_por_intencao(
            intencao=intencao,
            contato=contato,
            empresa=empresa,
            conteudo_cliente=conteudo,
            dlog=dlog,
        )
    
    async def _gerar_resposta_por_intencao(
        self,
        intencao: Intencao,
        contato: Contato,
        empresa: Empresa,
        conteudo_cliente: str,
        dlog: Optional[DebugLogger] = None,
    ) -> RespostaGerada:
        """Gera resposta baseado na intenção (com contato já identificado)."""
        nome = contato.nome or ""
        if dlog:
            dlog.log("rota", f"identificado empresa='{empresa.nome[:30]}' intencao={intencao.value}")
        
        if intencao == Intencao.SAUDACAO:
            if nome:
                return await self._gerador.gerar(T.SAUDACAO_COM_NOME, {"nome": nome})
            return await self._gerador.gerar(T.PERGUNTAR_NOME)
        
        if intencao == Intencao.PERGUNTAR_PRAZO:
            return await self._gerador.gerar(
                T.PRAZO_NAO_PROMETIDO,
                personalizar=True,
                mensagem_cliente=conteudo_cliente,
            )

        if intencao == Intencao.PERGUNTAR_PRECO:
            # Plano v1: para perguntas de preco a resposta e sempre o template
            # padrao de encaminhamento. Ainda assim, rodamos a RAG para
            # registrar trechos relacionados em auditoria.
            trechos_preco = await self._buscar_trechos_rag(conteudo_cliente, dlog=dlog)
            resposta = await self._gerador.gerar(
                T.PRECO_NAO_NEGOCIADO,
                personalizar=True,
                mensagem_cliente=conteudo_cliente,
            )
            _anexar_trechos_para_auditoria(resposta, trechos_preco)
            return resposta

        if intencao == Intencao.PEDIR_ORCAMENTO:
            return await self._gerador.gerar(T.PEDIR_TIPO_PRODUTO)

        if intencao == Intencao.PERGUNTAR_PRODUTO:
            return await self._responder_com_rag(
                conteudo_cliente=conteudo_cliente,
                template_fallback=T.PRODUTO_SEM_CONTEXTO,
                template_fallback_nome="PRODUTO_SEM_CONTEXTO",
                dlog=dlog,
            )

        if intencao == Intencao.APROVAR_ORCAMENTO:
            return await self._gerador.gerar(T.ORCAMENTO_APROVADO)
        
        if intencao == Intencao.REPROVAR_ORCAMENTO:
            return await self._gerador.gerar(T.ORCAMENTO_REPROVADO)
        
        if intencao == Intencao.FORA_CONTEXTO:
            return await self._responder_com_rag(
                conteudo_cliente=conteudo_cliente,
                template_fallback=T.FORA_CONTEXTO,
                template_fallback_nome="FORA_CONTEXTO",
                dlog=dlog,
            )

        # Fallback
        if dlog:
            dlog.log("rota", f"intencao={intencao.value} não mapeada → NAO_ENTENDI")
        return await self._gerador.gerar(
            T.NAO_ENTENDI,
            personalizar=True,
            mensagem_cliente=conteudo_cliente,
        )

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
                        f"hit score={top.score:.4f} id={top.id_externo}"
                        f" pergunta='{top.pergunta[:50]}'",
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
                        f"encontrados={len(trechos)} melhor_score={top.score:.4f}"
                        f" titulo='{str(top.titulo)[:50]}'",
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
        template_fallback: str,
        template_fallback_nome: str,
        dlog: Optional[DebugLogger] = None,
    ) -> RespostaGerada:
        """Busca pares/trechos e gera resposta; Q&A tem prioridade sobre chunks."""
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
                dlog.log("rag_decisao", f"sem trechos → fallback template={template_fallback_nome}")
            resposta = await self._gerador.gerar(
                template_fallback,
                template_nome=template_fallback_nome,
            )
            resposta.rag_utilizada = settings.RAG_ENABLED and self._retrieval is not None
            return resposta
        if dlog:
            dlog.log("rag_decisao", f"{len(trechos)} trechos → gerando com LLM+RAG")
        return await self._gerador.gerar_com_rag(
            pergunta_cliente=conteudo_cliente,
            trechos=trechos,
            permitir_sugestao_produto=settings.RAG_SUGERIR_PRODUTOS,
            template_fallback=template_fallback,
            template_fallback_nome=template_fallback_nome,
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
            return await self._gerador.gerar(T.CNPJ_INVALIDO)
        
        try:
            empresa = await obter_ou_criar_empresa(db, cnpj)
        except ConsultaCnpjError as e:
            logger.warning(f"[Processador] Falha ao consultar CNPJ: {e}")
            return await self._gerador.gerar(T.CNPJ_INVALIDO)
        
        # Cria contato se ainda não existir para essa combinação telefone+empresa
        contato_existente = (
            db.query(Contato)
            .filter_by(telefone=telefone, empresa_id=empresa.id)
            .first()
        )
        if not contato_existente:
            contato_existente = criar_contato(
                db=db,
                telefone=telefone,
                empresa=empresa,
                nome=nome_informado,
            )
        elif nome_informado and not contato_existente.nome:
            contato_existente.nome = nome_informado
            db.commit()
        
        # Cria negociação ativa se ainda não houver
        self._obter_ou_criar_negociacao(db, contato_existente, empresa)
        
        return await self._gerador.gerar(
            T.CNPJ_CONSULTADO_OK,
            contexto={"nome": empresa.nome},
            personalizar=False,
        )
    
    # ------------------------------------------------------------------
    # Negociação e informações
    # ------------------------------------------------------------------
    
    STATUS_ATIVOS = (
        StatusNegociacao.NOVO,
        StatusNegociacao.EM_CONTATO,
        StatusNegociacao.AGUARDANDO_ORCAMENTO,
        StatusNegociacao.ORCAMENTO_ENVIADO,
        StatusNegociacao.EM_NEGOCIACAO,
    )
    
    def _negociacao_ativa(self, db: Session, contato: Contato) -> Optional[Negociacao]:
        """Retorna a negociação ativa do contato (se houver)."""
        return (
            db.query(Negociacao)
            .filter(Negociacao.contato_id == contato.id)
            .filter(Negociacao.status.in_([s.value for s in self.STATUS_ATIVOS]))
            .order_by(Negociacao.created_at.desc())
            .first()
        )
    
    def _obter_ou_criar_negociacao(self, db: Session, contato: Contato, empresa: Empresa,) -> Negociacao:
        """Retorna negociação ativa ou cria uma nova."""
        negociacao = self._negociacao_ativa(db, contato)
        if negociacao:
            return negociacao
        
        negociacao = Negociacao(
            contato_id=contato.id,
            empresa_id=empresa.id,
            status=StatusNegociacao.NOVO,
            titulo=f"Atendimento - {empresa.nome}",
        )
        db.add(negociacao)
        db.commit()
        db.refresh(negociacao)
        logger.info(f"[Processador] Negociação criada id={negociacao.id}")
        return negociacao
    
    async def _atualizar_infos_negociacao(
        self,
        db: Session,
        negociacao: Negociacao,
        resultado_class,
    ):
        """Registra informações coletadas na NegociacaoInfo."""
        entidades = resultado_class.entidades
        
        registros = []
        if entidades.nomes:
            registros.append(("nome_contato", entidades.nomes[0]))
        if entidades.emails:
            registros.append(("email_contato", entidades.emails[0]))
        if entidades.tipos_produto:
            registros.append(("tipos_produto", ",".join(entidades.tipos_produto)))
        if entidades.quantidades:
            registros.append(("quantidades", ",".join(str(q) for q in entidades.quantidades)))
        
        for chave, valor in registros:
            info = (
                db.query(NegociacaoInfo)
                .filter_by(negociacao_id=negociacao.id, chave=chave)
                .first()
            )
            if info:
                info.valor = valor
                info.pendente = False
            else:
                db.add(NegociacaoInfo(
                    negociacao_id=negociacao.id,
                    chave=chave,
                    valor=valor,
                    pendente=False,
                    origem=OrigemInfo.INFERIDO if resultado_class.origem == "llm" else OrigemInfo.USER,
                ))
        
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
