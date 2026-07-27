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
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from config import settings
from models import (
    Atendimento,
    AtendimentoInfo,
    AtributoAdicionalModelo,
    Contato,
    Empresa,
    FaseAtendimento,
    ItemAtendimento,
    Mensagem,
    Modelo,
    ModoExecucao,
    ModoOperacao,
    MotivoEncerramento,
    MotivoEscalonamento,
    OrigemClassificacao,
    OrigemInfo,
    OrigemMensagem,
    Pessoa,
    ProcessamentoMensagem,
    Produto,
    StatusAtendimento,
    TipoEventoAtendimento,
    User,
)
from sqlalchemy import and_
from sqlalchemy.orm import Session
from utils.datetime_utils import utc_now

from services import atendimentos as atendimentos_svc
from services.classificador import Intencao, NivelConfianca, ResultadoClassificacao, classificar
from services.cnpj import ConsultaCnpjError, obter_ou_criar_empresa
from services.cnpj.receitaws import validar_cnpj
from services.conversacao.acoes import ContextoAcao
from services.conversacao.campos_pendentes import campos_pendentes
from services.conversacao.catalogo_campos import (
    CAMPO_FAIXA_FUNCIONARIOS,
    CAMPO_HOMOLOGADO_SOFTWARE,
    CAMPO_INTERESSE_SISTEMA_NUVEM,
    CAMPO_MODELO,
    CAMPO_QUANTIDADE,
    CAMPO_SOFTWARE_ACESSO,
    CAMPO_SOFTWARE_PONTO,
    CampoDef,
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

# Motor Intenção×Fase→Ações: registro de Regras por Fase efetiva do atendimento.
# `EM_ORCAMENTACAO` não precisa de entrada — `modo_operacao` já vira HUMANO junto com a
# transição (`_concluir_finalizando`), e o nível acima (`processar()`) já suprime a
# geração de resposta nesse modo antes de `_decidir_resposta` ser chamado.
REGISTRO_POR_FASE = {
    FaseAtendimento.ESCLARECENDO: REGISTRO_ESCLARECENDO,
    FaseAtendimento.FINALIZANDO: REGISTRO_FINALIZANDO,
}

# Fase E: mapeia a chave técnica de cada CampoDef (catalogo_campos.py) para o template de
# pergunta correspondente (respostas/catalogo.py) — os dois catálogos são propositalmente
# desacoplados (um não conhece o outro), essa é a ponte entre eles.
_MENSAGEM_ID_POR_CAMPO = {
    CAMPO_MODELO.chave: MensagemId.PEDIR_MODELO,
    CAMPO_SOFTWARE_PONTO.chave: MensagemId.PEDIR_SOFTWARE_PONTO,
    CAMPO_SOFTWARE_ACESSO.chave: MensagemId.PEDIR_SOFTWARE_ACESSO,
    CAMPO_INTERESSE_SISTEMA_NUVEM.chave: MensagemId.PEDIR_INTERESSE_SISTEMA_NUVEM,
    CAMPO_FAIXA_FUNCIONARIOS.chave: MensagemId.PEDIR_FAIXA_FUNCIONARIOS,
    CAMPO_QUANTIDADE.chave: MensagemId.PEDIR_QUANTIDADE,
    CAMPO_HOMOLOGADO_SOFTWARE.chave: MensagemId.PEDIR_HOMOLOGADO_SOFTWARE,
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
_RESPOSTA_SIM_REGEX = re.compile(r"\b(sim|s|claro|ok|parece|interesse|quero|pode ser)\b", re.IGNORECASE)
_RESPOSTA_NAO_REGEX = re.compile(r"\b(n[aã]o|n)\b", re.IGNORECASE)

# Fase G (G1): marca que o resumo (F4) já foi apresentado — um CONFIRMAR só conclui o
# handoff se for reply a um resumo que o cliente de fato viu; sem isso, a primeira
# mensagem "solta" a chegar depois de tudo capturado (ex.: um "ok" de preenchimento) seria
# tratada como confirmação de um resumo que nunca foi mostrado.
_RESUMO_APRESENTADO_CHAVE = "resumo_finalizando_apresentado"

# REQ-016.7/016.9: continuação de atendimento encerrado. Chaves de `AtendimentoInfo`
# gravadas no atendimento ENCERRADO (não no novo) enquanto se aguarda a resposta do
# cliente às perguntas PERG-016-009/009B.
_CONTINUACAO_PENDENTE_CHAVE = "continuacao_atendimento_pendente"
_CONFIRMAR_INTERESSE_PENDENTE_CHAVE = "confirmar_interesse_pendente"

# REQ-003.7: quando a RAG/QA não encontram conteúdo para uma dúvida de produto, marca que
# já fizemos a 1 pergunta de clarificação permitida — se a resposta a ela ainda não tiver
# base, escala para humano em vez de insistir de novo (mesmo padrão de
# `_MODELO_TENTATIVAS_CHAVE`, mas booleano: no máximo 1 tentativa extra, não N).
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

# Label com artigo para uso direto em perguntas (ex.: "Qual a faixa de pessoas
# que vão usar o relógio de ponto?" / "... que vão usar a catraca?").
_LABEL_PRODUTO_PERGUNTA = {
    "catraca": "a catraca",
    "relogio_ponto": "o relógio de ponto",
    "cancela": "a cancela",
    "leitor_facial": "o leitor facial",
    "leitor_biometrico": "o leitor biométrico",
    "camera": "a câmera",
    "controle_de_acesso": "o controle de acesso",
    "controle_por_cartao": "o controle por cartão",
    "bastao_de_ronda": "o bastão de ronda",
    "roteador": "o roteador",
}


def _label_tipo_produto(tipo_produto: Optional[str]) -> str:
    """Retorna o nome amigável de um tipo de produto para uso em mensagens."""
    if not tipo_produto:
        return "produto"
    return _LABEL_PRODUTO_PERGUNTA.get(tipo_produto, tipo_produto.replace("_", " "))


def _contexto_para_campo(campo: CampoDef, atendimento: Atendimento) -> Optional[dict]:
    """Contexto adicional para renderizar a pergunta de um campo pendente."""
    tipo_produto = _tipo_produto_atual(atendimento)
    if campo.chave == CAMPO_FAIXA_FUNCIONARIOS.chave:
        return {"produto": _label_tipo_produto(tipo_produto)}
    if campo.chave == CAMPO_QUANTIDADE.chave:
        return {"tipo_produto": tipo_produto.replace("_", " ") if tipo_produto else "o equipamento"}
    return None


def _tipo_produto_atual(atendimento: Atendimento) -> Optional[str]:
    """Tipo de produto de interesse do atendimento, se já identificado."""
    for info in atendimento.informacoes:
        if info.chave == "tipos_produto" and info.valor:
            primeiro = info.valor.split(",")[0].strip()
            return primeiro or None
    return None
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


def _normalizar_sem_acento(texto: str) -> str:
    """Remove acentos para comparações case-insensitive em português."""
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    ).lower()


def _produto_ids_por_tipos(db: Session, tipos_produto: list[str]) -> list[int]:
    """Busca produtos ativos cujo nome contenha os tokens do tipo extraído."""
    if not tipos_produto:
        return []
    produtos = db.query(Produto).filter(Produto.ativo.is_(True)).all()
    ids: set[int] = set()
    for tipo in tipos_produto:
        tipo_norm = _normalizar_sem_acento(tipo.replace("_", " "))
        partes = [p for p in tipo_norm.split() if len(p) > 2]
        for produto in produtos:
            desc_norm = _normalizar_sem_acento(produto.descricao)
            if tipo_norm in desc_norm or all(part in desc_norm for part in partes):
                ids.add(produto.id)
    return list(ids)


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
                self._atualizar_ultima_mensagem_at(atendimento, msg_in.timestamp)

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
        par = await self._buscar_resposta_qa(conteudo_cliente, dlog=dlog)
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

    async def _responder_categoria3(
        self,
        intencao: Intencao,
        conteudo_cliente: str,
        db: Optional[Session] = None,
        atendimento: Optional[Atendimento] = None,
        dlog: Optional[DebugLogger] = None,
    ) -> RespostaGerada:
        """Responde intenção de categoria 3 (REQ-002.1) — dúvida sobre produto/preço/fora de
        contexto — via Q&A/RAG.

        Reaproveitado pelas Regras de categoria 3 da fase Esclarecendo
        (`regras_esclarecendo.py`) e pela retomada de dúvida em Finalizando (F3,
        `_retomar_apos_duvida`) — mesmo comportamento, não importa se o CNPJ/CPF já foi
        informado.

        `db`/`atendimento` são opcionais e usados apenas por PERGUNTAR_PRODUTO para o
        fluxo de clarificação/escalonamento (REQ-003.7) — sem eles (ex.: atendimento ainda
        não garantido), cai no fallback genérico de sempre.
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
            if db is not None and atendimento is not None:
                return await self._responder_produto_com_clarificacao(
                    db, atendimento, conteudo_cliente, dlog=dlog
                )
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
        padrão já usado por `_MODELO_TENTATIVAS_CHAVE` (F2)."""
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
            fase_anterior = atendimento.fase.value
            atendimento.fase = FaseAtendimento.FINALIZANDO
            db.commit()
            atendimentos_svc.registrar_evento_atendimento(
                db,
                atendimento,
                tipo=TipoEventoAtendimento.FASE_ALTERADA,
                ator="sistema:motor_conversacao",
                estado_anterior=fase_anterior,
                estado_novo=FaseAtendimento.FINALIZANDO.value,
                motivo="PEDIR_ORCAMENTO recebido (E1)",
            )
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
        ctx_campo = _contexto_para_campo(campo, atendimento)
        if dlog:
            dlog.log("finalizando", f"próxima pergunta: {campo.chave} ({mensagem_id.name})")
        return [(MensagemId.INICIAR_FINALIZANDO, None), (mensagem_id, ctx_campo)]

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
        a pergunta pendente atual (F1); (d) recalcula o que falta e pergunta, fecha com o
        resumo (F4), ou — se o resumo já tinha sido apresentado e o cliente confirma —
        conclui o handoff para o time humano (Fase G).
        """
        pendentes_antes = campos_pendentes(atendimento)
        tentou_modelo = bool(
            pendentes_antes
            and pendentes_antes[0].chave == CAMPO_MODELO.chave
            and resultado_class.entidades.tipo_leitor_mencionado
        )

        modelo_nao_reconhecido = await self._tentar_resolver_modelo(db, atendimento, resultado_class, dlog=dlog)
        if atendimento.modo_operacao == ModoOperacao.HUMANO:
            # F2: acabou de escalar por falta de correspondência de modelo — não continua.
            return await self._gerador.gerar(MensagemId.ESCALADO_HUMANO)

        if modelo_nao_reconhecido:
            # F2: modelo não existe no catálogo (1ª tentativa) — informar e reapresentar opções.
            return await self._gerador.gerar(MensagemId.MODELO_NAO_RECONHECIDO)

        if resultado_class.intencao_principal.value in _INTENCOES_RAG:
            return await self._retomar_apos_duvida(db, atendimento, conteudo, resultado_class, dlog=dlog)

        if not tentou_modelo:
            self._capturar_resposta_direta_pendente(db, atendimento, conteudo, resultado_class, dlog=dlog)

        pendentes = campos_pendentes(atendimento)
        if not pendentes:
            tipo_produto_conhecido = bool(self._info_atendimento(db, atendimento.id, "tipos_produto"))
            if not tipo_produto_conhecido:
                # Ainda não sabemos o tipo de produto (não é "tudo capturado" — não dá pra
                # saber o que pedir sem isso) — reapresenta a pergunta inicial.
                if dlog:
                    dlog.log("finalizando", "tipo de produto ainda não identificado → PEDIR_TIPO_PRODUTO")
                return await self._gerador.gerar(MensagemId.PEDIR_TIPO_PRODUTO)
            # G1-G3 (confirmação do resumo → handoff) é tratado antes de chegar aqui, como
            # Regra exclusiva própria da fase Finalizando (ver regras_finalizando.py) —
            # se chegamos até este ponto, é porque não era o caso (resumo ainda não
            # apresentado, ou já concluído antes).
            return await self._gerar_resumo_finalizando(db, atendimento, dlog=dlog)

        campo = pendentes[0]
        mensagem_id = _MENSAGEM_ID_POR_CAMPO.get(campo.chave, MensagemId.PEDIR_TIPO_PRODUTO)
        ctx_campo = _contexto_para_campo(campo, atendimento)
        if dlog:
            dlog.log("finalizando", f"próxima pergunta pendente: {campo.chave} ({mensagem_id.name})")
        return await self._gerador.gerar(mensagem_id, ctx_campo)

    async def _concluir_finalizando(
        self,
        db: Session,
        atendimento: Atendimento,
        dlog: Optional[DebugLogger] = None,
    ) -> RespostaGerada:
        """G1-G3: cliente confirmou o resumo (F4) — transita para `EM_ORCAMENTACAO` e faz o
        handoff para o time humano montar o orçamento de verdade (REQ-004 /
        FASE-criando-orcamento). `modo_operacao = HUMANO` suprime respostas automáticas
        daqui em diante (mesmo mecanismo já usado pelo escalonamento do F2)."""
        fase_anterior = atendimento.fase.value
        modo_anterior = atendimento.modo_operacao.value
        atendimento.fase = FaseAtendimento.EM_ORCAMENTACAO
        atendimento.modo_operacao = ModoOperacao.HUMANO
        db.commit()
        atendimentos_svc.registrar_evento_atendimento(
            db,
            atendimento,
            tipo=TipoEventoAtendimento.FASE_ALTERADA,
            ator="sistema:motor_conversacao",
            estado_anterior=fase_anterior,
            estado_novo=FaseAtendimento.EM_ORCAMENTACAO.value,
            motivo="G1-G3: cliente confirmou o resumo",
        )
        atendimentos_svc.registrar_evento_atendimento(
            db,
            atendimento,
            tipo=TipoEventoAtendimento.MODO_OPERACAO_ALTERADO,
            ator="sistema:motor_conversacao",
            estado_anterior=modo_anterior,
            estado_novo=ModoOperacao.HUMANO.value,
            motivo="Handoff para o time humano montar o orçamento",
        )
        if dlog:
            dlog.log(
                "fase",
                f"Finalizando → Em orçamentação (atendimento id={atendimento.id}) — handoff humano",
            )
        return await self._gerador.gerar(MensagemId.ORCAMENTO_ENCAMINHADO)

    async def _tentar_resolver_modelo(
        self,
        db: Session,
        atendimento: Atendimento,
        resultado_class: ResultadoClassificacao,
        dlog: Optional[DebugLogger] = None,
    ) -> bool:
        """F2: resolve `modelo_produto` para uma linha real de `Modelo`, ou escala para
        atendimento humano após `_MODELO_MAX_TENTATIVAS` sem correspondência — nunca aceita
        o texto do cliente como modelo (REQ-002.3B, CAMPO-modelo).

        Usa tipo de produto, tecnologia de leitura, marca e aplicação extraídos da
        conversa para desambiguar o catálogo.

        Retorna `True` se houve tentativa sem correspondência (mas sem escalar) — o
        chamador deve usar `MODELO_NAO_RECONHECIDO` em vez de `PEDIR_MODELO`.
        Retorna `False` em todos os outros casos (resolvido, não tentou, ou escalou).
        """
        pendentes = campos_pendentes(atendimento)
        if not pendentes or pendentes[0].chave != CAMPO_MODELO.chave:
            return False

        entidades = resultado_class.entidades
        tipo_leitor = entidades.tipo_leitor_mencionado
        marca = entidades.marca
        aplicacao = entidades.aplicacao

        # Produto(s) alinhados ao interesse já declarado em AtendimentoInfo.
        valores = {info.chave: info.valor for info in atendimento.informacoes}
        tipos_produto = [t.strip() for t in (valores.get("tipos_produto") or "").split(",") if t.strip()]
        produto_ids = _produto_ids_por_tipos(db, tipos_produto)

        # D6: atributos genéricos do modelo já coletados + extraídos agora.
        atributos_mensagem: dict[str, str] = dict(entidades.atributos)
        if tipo_leitor:
            atributos_mensagem.setdefault("tecnologia_leitura", tipo_leitor)
        for chave, valor in valores.items():
            if chave in ("marca", "aplicacao", "tipo_leitor_mencionado", "tipos_produto", "quantidades"):
                continue
            # Preserva valor da mensagem atual sobre valor salvo anteriormente.
            atributos_mensagem.setdefault(chave, valor)

        sinais = {k: v for k, v in {"marca": marca, "aplicacao": aplicacao, **atributos_mensagem}.items() if v}
        if not sinais and not produto_ids:
            return False  # mensagem não trouxe sinal para resolver modelo

        query = db.query(Modelo).join(Produto, Modelo.produto_id == Produto.id).filter(Modelo.ativo.is_(True))
        if produto_ids:
            query = query.filter(Modelo.produto_id.in_(produto_ids))
        if marca:
            query = query.filter(Modelo.marca == marca)
        if aplicacao:
            query = query.filter(Modelo.aplicacao == aplicacao)

        # D6: exige que o modelo possua todos os atributos extraídos/coletados.
        for chave, valor in atributos_mensagem.items():
            subquery = (
                db.query(AtributoAdicionalModelo.modelo_id)
                .filter(
                    AtributoAdicionalModelo.modelo_id == Modelo.id,
                    AtributoAdicionalModelo.chave == chave,
                    AtributoAdicionalModelo.valor == valor,
                    AtributoAdicionalModelo.ativo.is_(True),
                )
                .exists()
            )
            query = query.filter(subquery)

        candidato = query.first()
        if candidato:
            item = self._item_atendimento_atual(db, atendimento, candidato.produto_id)
            item.modelo_id = candidato.id
            db.commit()
            self._remover_info_atendimento(db, atendimento.id, _MODELO_TENTATIVAS_CHAVE)
            if dlog:
                dlog.log(
                    "finalizando",
                    f"modelo resolvido: produto_id={candidato.id} ({candidato.descricao})",
                )
            return False

        tentativas = int(self._info_atendimento(db, atendimento.id, _MODELO_TENTATIVAS_CHAVE) or 0) + 1
        self._salvar_info_atendimento(db, atendimento.id, _MODELO_TENTATIVAS_CHAVE, str(tentativas))
        if dlog:
            sinais = ", ".join(
                f"{k}={v}"
                for k, v in {
                    "marca": marca,
                    "aplicacao": aplicacao,
                    "tipo_leitor": tipo_leitor,
                    **atributos_mensagem,
                }.items()
                if v
            )
            dlog.log(
                "finalizando",
                f"modelo sem correspondência ({sinais}) tentativa={tentativas}",
            )

        if tentativas >= _MODELO_MAX_TENTATIVAS:
            atendimento.modo_operacao = ModoOperacao.HUMANO
            db.commit()
            if dlog:
                dlog.log(
                    "finalizando",
                    f"modelo sem correspondência após {tentativas} tentativas → escalar_humano",
                )
            return False

        return True

    def _item_atendimento_atual(
        self,
        db: Session,
        atendimento: Atendimento,
        produto_id: int,
    ) -> ItemAtendimento:
        """MVP: um único item por atendimento (só relógio de ponto) — get-or-create."""
        item = next(iter(atendimento.itens), None)
        if item is None:
            item = ItemAtendimento(atendimento_id=atendimento.id, produto_id=produto_id, quantidade=1)
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
        if resultado_class.intencao_principal != Intencao.DESCONHECIDO:
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

        elif campo.chave == CAMPO_SOFTWARE_ACESSO.chave:
            texto = conteudo.strip()
            if not texto:
                return
            valor = "nenhum" if _SOFTWARE_NENHUM_REGEX.search(texto) else texto
            self._salvar_info_atendimento(db, atendimento.id, campo.chave, valor)
            if dlog:
                dlog.log("finalizando", f"software_controle_acesso capturado (resposta livre): {valor}")

        elif campo.chave == CAMPO_INTERESSE_SISTEMA_NUVEM.chave:
            if _RESPOSTA_SIM_REGEX.search(conteudo):
                self._salvar_info_atendimento(db, atendimento.id, campo.chave, "sim")
                if dlog:
                    dlog.log("finalizando", "interesse_sistema_nuvem capturado: sim")
            elif _RESPOSTA_NAO_REGEX.search(conteudo):
                self._salvar_info_atendimento(db, atendimento.id, campo.chave, "não")
                if dlog:
                    dlog.log("finalizando", "interesse_sistema_nuvem capturado: não")

        elif campo.chave == CAMPO_QUANTIDADE.chave:
            match = _NUMERO_SOLTO_REGEX.search(conteudo)
            if match:
                self._salvar_info_atendimento(db, atendimento.id, campo.chave, match.group(1))
                if dlog:
                    dlog.log("finalizando", f"quantidade capturada (resposta solta): {match.group(1)}")

        elif campo.chave == CAMPO_HOMOLOGADO_SOFTWARE.chave:
            if _RESPOSTA_SIM_REGEX.search(conteudo):
                self._salvar_info_atendimento(db, atendimento.id, campo.chave, "sim")
                if dlog:
                    dlog.log("finalizando", "homologado_software capturado: sim")
            elif _RESPOSTA_NAO_REGEX.search(conteudo):
                self._salvar_info_atendimento(db, atendimento.id, campo.chave, "não")
                if dlog:
                    dlog.log("finalizando", "homologado_software capturado: não")

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
        resposta_duvida = await self._responder_categoria3(
            resultado_class.intencao_principal, conteudo, db=db, atendimento=atendimento, dlog=dlog
        )

        pendentes = campos_pendentes(atendimento)
        if not pendentes:
            if dlog:
                dlog.log("finalizando", "dúvida em Finalizando, sem pendências → só responde a dúvida")
            return resposta_duvida

        campo = pendentes[0]
        mensagem_id = _MENSAGEM_ID_POR_CAMPO.get(campo.chave, MensagemId.PEDIR_TIPO_PRODUTO)
        ctx_campo = _contexto_para_campo(campo, atendimento)
        resposta_pergunta = await self._gerador.gerar(mensagem_id, ctx_campo)
        resposta_retomada = await self._gerador.gerar(
            MensagemId.RETOMAR_PERGUNTA_PENDENTE, {"pergunta": resposta_pergunta.texto}
        )
        if dlog:
            dlog.log("finalizando", f"dúvida ({resultado_class.intencao_principal.value}) → retoma {campo.chave}")
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
        db: Session,
        atendimento: Atendimento,
        dlog: Optional[DebugLogger] = None,
    ) -> RespostaGerada:
        """F4: nada mais pendente — apresenta resumo do que foi coletado e pede confirmação.

        Marca `_RESUMO_APRESENTADO_CHAVE` (G1) — um `CONFIRMAR` só conclui o handoff se for
        resposta a um resumo que o cliente de fato viu numa mensagem anterior.
        """
        valores = {info.chave: info.valor for info in atendimento.informacoes}
        item_resolvido = next((item for item in atendimento.itens if item.modelo_id is not None), None)
        modelo = item_resolvido.modelo if item_resolvido else None
        ctx = {
            "modelo": modelo.descricao if modelo else None,
            "marca": modelo.marca if modelo else None,
            "aplicacao": modelo.aplicacao if modelo else None,
            "categorias": ", ".join(c.descricao for c in modelo.categorias) if modelo else None,
            "atributos": {a.chave: a.valor for a in modelo.atributos} if modelo else {},
            "software": valores.get(CAMPO_SOFTWARE_PONTO.chave),
            "software_acesso": valores.get(CAMPO_SOFTWARE_ACESSO.chave),
            "interesse_sistema_nuvem": valores.get(CAMPO_INTERESSE_SISTEMA_NUVEM.chave),
            "homologado_software": valores.get(CAMPO_HOMOLOGADO_SOFTWARE.chave),
            "faixa_funcionarios": valores.get(CAMPO_FAIXA_FUNCIONARIOS.chave),
            "quantidade": valores.get(CAMPO_QUANTIDADE.chave),
        }
        self._salvar_info_atendimento(db, atendimento.id, _RESUMO_APRESENTADO_CHAVE, "true")
        if dlog:
            dlog.log("finalizando", f"tudo capturado → resumo (modelo={ctx['modelo']})")
        return await self._gerador.gerar(MensagemId.RESUMO_FINALIZANDO, ctx)

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
    }

    def _montar_resumo_escalonamento(
        self, db: Session, atendimento: Atendimento, motivo: MotivoEscalonamento
    ) -> str:
        """REQ-004.2: resumo de contexto para o vendedor — reaproveita a mesma leitura
        de dados do `_gerar_resumo_finalizando` (AtendimentoInfo + ItemAtendimento/Modelo),
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

    async def _buscar_resposta_qa(
        self,
        query: str,
        dlog: Optional[DebugLogger] = None,
    ) -> Optional[ParRecuperado]:
        """Busca o melhor par Q&A para a query; retorna None se nao encontrado."""
        if self._qa is None or not self._qa.habilitado:
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
        if self._retrieval is None or not self._retrieval.habilitado:
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
            resposta.rag_utilizada = self._retrieval is not None and self._retrieval.habilitado
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
        for chave, valor in entidades.atributos.items():
            registros.append((chave, valor))

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
