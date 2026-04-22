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
from services.respostas import GeradorRespostas, RespostaGerada
from services.respostas import templates as T

logger = logging.getLogger(__name__)


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
    
    def __init__(self, llm: Optional[LLMProvider] = None):
        self._llm = llm
        self._gerador = GeradorRespostas(llm=llm, usar_llm=llm is not None)
    
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
        
        # 2. Identifica remetente
        identificacao = identificar_por_telefone(db, telefone_norm)
        logger.info(f"[Processador] Identificação: {identificacao.status.value}")
        
        # 3. Classifica intenção e extrai entidades
        resultado_class = await classificar(conteudo, llm=self._llm)
        logger.info(
            f"[Processador] Intenção: {resultado_class.intencao.value} "
            f"(confiança={resultado_class.confianca:.2f}, via {resultado_class.origem})"
        )
        
        # 4. Roteia conforme estado de identificação + intenção
        try:
            resposta = await self._decidir_resposta(
                db=db,
                telefone=telefone_norm,
                conteudo=conteudo,
                identificacao=identificacao,
                resultado_class=resultado_class,
            )
        except Exception as e:
            logger.exception(f"[Processador] Erro gerando resposta: {e}")
            erro_processamento = str(e)
            resposta = RespostaGerada(
                texto="Desculpe, tive um problema ao processar sua mensagem.",
                template_usado=None,
            )
        
        # 5. Recarrega identificação (pode ter sido criado contato agora)
        ident_final = identificar_por_telefone(db, telefone_norm)
        contato = ident_final.contato
        negociacao = self._negociacao_ativa(db, contato) if contato else None
        
        # 6. Registra processamento (auditoria/debug)
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
        
        # 7. Vincula mensagem do cliente ao processamento/contato/negociação
        msg_in.processamento_id = processamento.id
        if contato:
            msg_in.contato_id = contato.id
            if negociacao:
                msg_in.negociacao_id = negociacao.id
        
        # 8. Persiste resposta do sistema
        msg_out = Mensagem(
            telefone=telefone_norm,
            conteudo=resposta.texto,
            origem=OrigemMensagem.SYSTEM,
            contato_id=contato.id if contato else None,
            negociacao_id=negociacao.id if negociacao else None,
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
    ) -> RespostaGerada:
        """Decide o que responder com base na identificação e intenção."""
        intencao = resultado_class.intencao
        entidades = resultado_class.entidades
        
        # Regra: Escalar humano sempre tem prioridade
        if intencao == Intencao.ESCALAR_HUMANO:
            return await self._gerador.gerar(T.ESCALADO_HUMANO)
        
        # Regra: Reclamação também escala
        if intencao == Intencao.RECLAMAR:
            return await self._gerador.gerar(T.RECLAMACAO_ESCALADA)
        
        # Se o cliente forneceu CNPJ, processa
        if entidades.cnpjs:
            return await self._processar_cnpj_fornecido(
                db, telefone, entidades.cnpjs[0],
                nome_informado=entidades.nomes[0] if entidades.nomes else None,
            )
        
        # Telefone novo ou sem empresa -> pedir identificação
        if identificacao.status == StatusIdentificacao.NOVO:
            return await self._gerador.gerar(T.SAUDACAO_NOVO_CONTATO)
        
        if identificacao.status == StatusIdentificacao.MULTIPLO:
            nomes_empresas = ", ".join(e.nome for e in identificacao.empresas[:5])
            return await self._gerador.gerar(
                T.MULTIPLAS_EMPRESAS,
                contexto={"empresas": nomes_empresas},
            )
        
        if identificacao.status == StatusIdentificacao.SEM_EMPRESA:
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
        )
    
    async def _gerar_resposta_por_intencao(
        self,
        intencao: Intencao,
        contato: Contato,
        empresa: Empresa,
        conteudo_cliente: str,
    ) -> RespostaGerada:
        """Gera resposta baseado na intenção (com contato já identificado)."""
        nome = contato.nome or ""
        
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
            return await self._gerador.gerar(
                T.PRECO_NAO_NEGOCIADO,
                personalizar=True,
                mensagem_cliente=conteudo_cliente,
            )
        
        if intencao == Intencao.PEDIR_ORCAMENTO:
            return await self._gerador.gerar(T.PEDIR_TIPO_PRODUTO)
        
        if intencao == Intencao.PERGUNTAR_PRODUTO:
            return await self._gerador.gerar(T.PEDIR_TIPO_PRODUTO)
        
        if intencao == Intencao.APROVAR_ORCAMENTO:
            return await self._gerador.gerar(T.ORCAMENTO_APROVADO)
        
        if intencao == Intencao.REPROVAR_ORCAMENTO:
            return await self._gerador.gerar(T.ORCAMENTO_REPROVADO)
        
        if intencao == Intencao.FORA_CONTEXTO:
            return await self._gerador.gerar(T.FORA_CONTEXTO)
        
        # Fallback
        return await self._gerador.gerar(
            T.NAO_ENTENDI,
            personalizar=True,
            mensagem_cliente=conteudo_cliente,
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
    
    def _obter_ou_criar_negociacao(
        self,
        db: Session,
        contato: Contato,
        empresa: Empresa,
    ) -> Negociacao:
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
