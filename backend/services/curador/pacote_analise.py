"""
Montagem do pacote de análise para o agente [curador_conhecimento].

Dado um report_id, extrai contexto do banco, reprocessa buscas Q&A/RAG e
classificação sobre a pergunta original, e produz estrutura pronta para YAML.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from config import settings
from models import (
    Atendimento,
    AtendimentoInfo,
    CategoriaReport,
    Mensagem,
    OrigemMensagem,
    ProcessamentoMensagem,
    ReportProblema,
)
from sqlalchemy.orm import Session

from services.classificador import ResultadoClassificacao, classificar, extrair_entidades
from services.curador.documentos_fonte import sugerir_documentos_fonte
from services.llm import get_llm_provider
from services.parametro_service import ParametroService

logger = logging.getLogger(__name__)

PACOTE_VERSAO = "1.0"
AGENTE_SUGERIDO_CURADOR = "curador_conhecimento"
CATEGORIAS_CURADOR = {
    CategoriaReport.RESPOSTA_INADEQUADA,
    CategoriaReport.TEMPLATE,
    CategoriaReport.OUTRO,
}


def _origem_valor(origem) -> str:
    return origem.value if hasattr(origem, "value") else str(origem)


def _resolver_par_mensagens(
    session: Session,
    report: ReportProblema,
    proc: Optional[ProcessamentoMensagem],
) -> tuple[Optional[Mensagem], Optional[Mensagem], Optional[ProcessamentoMensagem]]:
    """
    Resolve pergunta do cliente, resposta do sistema e processamento associado.

    Cenários:
    - report.mensagem_id aponta para SYSTEM → busca USER anterior no mesmo telefone.
    - report.mensagem_id aponta para USER → busca SYSTEM posterior.
    - só processamento_id → usa proc.mensagem (USER) e SYSTEM seguinte.
    """
    msg_report: Optional[Mensagem] = None
    if report.mensagem_id:
        msg_report = session.query(Mensagem).filter_by(id=report.mensagem_id).first()

    pergunta: Optional[Mensagem] = None
    resposta: Optional[Mensagem] = None
    proc_efetivo = proc

    if msg_report:
        origem = _origem_valor(msg_report.origem)
        if origem == OrigemMensagem.SYSTEM.value:
            resposta = msg_report
            pergunta = (
                session.query(Mensagem)
                .filter(
                    Mensagem.telefone == msg_report.telefone,
                    Mensagem.origem == OrigemMensagem.USER,
                    Mensagem.timestamp < msg_report.timestamp,
                )
                .order_by(Mensagem.timestamp.desc())
                .first()
            )
            if pergunta and pergunta.processamento_id and proc_efetivo is None:
                proc_efetivo = session.query(ProcessamentoMensagem).filter_by(
                    id=pergunta.processamento_id
                ).first()
        else:
            pergunta = msg_report
            resposta = (
                session.query(Mensagem)
                .filter(
                    Mensagem.telefone == msg_report.telefone,
                    Mensagem.origem == OrigemMensagem.SYSTEM,
                    Mensagem.timestamp > msg_report.timestamp,
                )
                .order_by(Mensagem.timestamp.asc())
                .first()
            )
            if pergunta.processamento_id and proc_efetivo is None:
                proc_efetivo = session.query(ProcessamentoMensagem).filter_by(
                    id=pergunta.processamento_id
                ).first()

    if pergunta is None and proc and proc.mensagem:
        pergunta = proc.mensagem
        resposta = (
            session.query(Mensagem)
            .filter(
                Mensagem.telefone == pergunta.telefone,
                Mensagem.origem == OrigemMensagem.SYSTEM,
                Mensagem.timestamp > pergunta.timestamp,
            )
            .order_by(Mensagem.timestamp.asc())
            .first()
        )

    if proc_efetivo is None and report.processamento_id:
        proc_efetivo = session.query(ProcessamentoMensagem).filter_by(
            id=report.processamento_id
        ).first()

    return pergunta, resposta, proc_efetivo


def _janela_mensagens(
    session: Session,
    msg_centro: Optional[Mensagem],
    antes: int,
    depois: int,
) -> list[dict]:
    if not msg_centro:
        return []
    antes_q = (
        session.query(Mensagem)
        .filter(
            Mensagem.telefone == msg_centro.telefone,
            Mensagem.timestamp < msg_centro.timestamp,
        )
        .order_by(Mensagem.timestamp.desc())
        .limit(antes)
        .all()
    )
    depois_q = (
        session.query(Mensagem)
        .filter(
            Mensagem.telefone == msg_centro.telefone,
            Mensagem.timestamp > msg_centro.timestamp,
        )
        .order_by(Mensagem.timestamp.asc())
        .limit(depois)
        .all()
    )
    return [m.to_dict() for m in reversed(antes_q)] + [msg_centro.to_dict()] + [m.to_dict() for m in depois_q]


def _carregar_atendimento_contexto(session: Session, atendimento_id: Optional[int]) -> Optional[dict]:
    if not atendimento_id:
        return None
    atendimento = session.query(Atendimento).filter_by(id=atendimento_id).first()
    if not atendimento:
        return None
    infos = (
        session.query(AtendimentoInfo)
        .filter_by(atendimento_id=atendimento_id)
        .all()
    )
    return {
        "atendimento": atendimento.to_dict(),
        "informacoes": [i.to_dict() for i in infos],
    }


def _serializar_classificacao(resultado: ResultadoClassificacao) -> dict:
    return {
        "intencao": resultado.intencao_principal.value,
        "intencoes": [i.value for i in resultado.intencoes],
        "confianca": resultado.confianca,
        "confianca_nivel": resultado.confianca_nivel.value,
        "origem": resultado.origem,
        "entidades": {
            "cnpjs": resultado.entidades.cnpjs,
            "cpfs": resultado.entidades.cpfs,
            "nomes": resultado.entidades.nomes,
            "tipos_produto": resultado.entidades.tipos_produto,
            "quantidades": resultado.entidades.quantidades,
            "emails": resultado.entidades.emails,
        },
    }


async def _reprocessar_classificacao(texto: str) -> dict:
    llm = None
    try:
        llm = get_llm_provider()
    except Exception as exc:
        logger.warning("[PacoteAnalise] LLM indisponível para reclassificação: %s", exc)
    resultado = await classificar(texto, llm=llm)
    return _serializar_classificacao(resultado)


async def _reprocessar_buscas(
    query: str,
    qa_service,
    retrieval_service,
    qa_score_minimo: float,
    rag_score_minimo: float,
    top_k: int = 10,
) -> dict:
    diagnostico: dict[str, Any] = {
        "qa_habilitado": qa_service is not None and getattr(qa_service, "habilitado", settings.QA_ENABLED),
        "rag_habilitado": retrieval_service is not None
        and getattr(retrieval_service, "habilitado", settings.RAG_ENABLED),
        "qa_top_candidatos": [],
        "rag_top_candidatos": [],
        "qa_hit_producao": None,
        "rag_hit_producao": None,
    }

    if qa_service is not None:
        candidatos_qa = await qa_service.buscar_candidatos(
            query=query,
            top_k=top_k,
            apenas_aprovados=False,
        )
        diagnostico["qa_top_candidatos"] = [p.to_dict() for p in candidatos_qa]
        hits_qa = await qa_service.buscar(
            query=query,
            top_k=1,
            score_minimo=qa_score_minimo,
            apenas_aprovados=settings.QA_APENAS_APROVADOS,
        )
        diagnostico["qa_hit_producao"] = hits_qa[0].to_dict() if hits_qa else None

    if retrieval_service is not None:
        candidatos_rag = await retrieval_service.buscar_candidatos(
            query=query,
            top_k=top_k,
            tipo="produto",
        )
        diagnostico["rag_top_candidatos"] = [d.to_dict() for d in candidatos_rag]
        hits_rag = await retrieval_service.buscar(
            query=query,
            top_k=1,
            score_minimo=rag_score_minimo,
            tipo="produto",
        )
        diagnostico["rag_hit_producao"] = hits_rag[0].to_dict() if hits_rag else None

    return diagnostico


def _hipoteses_automaticas(
    pergunta: str,
    proc: Optional[ProcessamentoMensagem],
    diagnostico: dict,
    parametros: dict,
    classificacao_nova: dict,
) -> list[dict]:
    hipoteses: list[dict] = []
    qa_cands = diagnostico.get("qa_top_candidatos") or []
    rag_cands = diagnostico.get("rag_top_candidatos") or []
    qa_min = parametros.get("qa_score_minimo", settings.QA_SCORE_MINIMO)
    rag_min = parametros.get("rag_score_minimo", settings.RAG_SCORE_MINIMO)

    melhor_qa = float(qa_cands[0]["score"]) if qa_cands else None
    melhor_rag = float(rag_cands[0]["score"]) if rag_cands else None

    if proc and proc.template_usado == "PRODUTO_SEM_CONTEXTO":
        hipoteses.append({
            "tipo": "fallback_template",
            "detalhe": "Resposta original usou PRODUTO_SEM_CONTEXTO (base insuficiente ou score baixo).",
        })

    if melhor_qa is not None and melhor_qa < qa_min:
        hipoteses.append({
            "tipo": "score_abaixo_limiar",
            "camada": "qa",
            "detalhe": f"Melhor par Q&A score={melhor_qa:.4f} < limiar {qa_min}",
            "melhor_score": melhor_qa,
            "limiar": qa_min,
        })
    elif not qa_cands:
        hipoteses.append({
            "tipo": "conteudo_ausente",
            "camada": "qa",
            "detalhe": "Nenhum par Q&A retornado na re-busca diagnóstica.",
        })

    if melhor_rag is not None and melhor_rag < rag_min:
        hipoteses.append({
            "tipo": "score_abaixo_limiar",
            "camada": "rag",
            "detalhe": f"Melhor trecho RAG score={melhor_rag:.4f} < limiar {rag_min}",
            "melhor_score": melhor_rag,
            "limiar": rag_min,
        })
    elif not rag_cands:
        hipoteses.append({
            "tipo": "conteudo_ausente",
            "camada": "rag",
            "detalhe": "Nenhum trecho RAG retornado na re-busca diagnóstica.",
        })

    if proc and proc.intencao and classificacao_nova.get("intencao"):
        # `intencoes` (lista completa) só existe em processamentos feitos após o motor
        # Intenção×Fase→Ações — processamentos mais antigos caem no fallback de
        # comparar só a intenção principal, único dado que tinham.
        intencoes_originais = set(proc.intencoes or [proc.intencao])
        intencoes_novas = set(classificacao_nova.get("intencoes") or [classificacao_nova["intencao"]])
        if intencoes_originais != intencoes_novas:
            hipoteses.append({
                "tipo": "classificacao_divergente",
                "detalhe": (
                    f"No processamento original: {sorted(intencoes_originais)}; "
                    f"na reclassificação atual: {sorted(intencoes_novas)}"
                ),
            })

    entidades = classificacao_nova.get("entidades") or {}
    quantidades = entidades.get("quantidades") or []
    if quantidades and any(q >= 20 for q in quantidades):
        hipoteses.append({
            "tipo": "porte_pode_exigir_humano",
            "detalhe": f"Quantidade/funcionários mencionados: {quantidades} (ver REQ-004.8).",
        })

    if not hipoteses:
        hipoteses.append({
            "tipo": "investigar_manualmente",
            "detalhe": "Nenhuma hipótese automática forte; revisar documentos sugeridos e resposta esperada.",
        })

    return hipoteses


def _agente_sugerido(categoria: CategoriaReport) -> str:
    if categoria in CATEGORIAS_CURADOR:
        return AGENTE_SUGERIDO_CURADOR
    if categoria == CategoriaReport.CLASSIFICACAO:
        return "ia_expert"
    if categoria in (CategoriaReport.FLUXO, CategoriaReport.DADOS, CategoriaReport.LLM):
        return "implementador"
    return AGENTE_SUGERIDO_CURADOR


async def montar_pacote_analise(
    session: Session,
    report_id: int,
    antes: int = 5,
    depois: int = 3,
    projeto_root: Optional[Path] = None,
) -> dict:
    """Monta o pacote completo de análise para um report."""
    report = session.query(ReportProblema).filter_by(id=report_id).first()
    if not report:
        raise ValueError(f"Report {report_id} não encontrado")

    proc = report.processamento
    pergunta_msg, resposta_msg, proc_efetivo = _resolver_par_mensagens(session, report, proc)

    pergunta_texto = pergunta_msg.conteudo if pergunta_msg else None
    if not pergunta_texto:
        raise ValueError(
            f"Não foi possível identificar a pergunta do cliente para o report {report_id}"
        )

    param_svc = ParametroService(session)
    parametros = {
        "qa_score_minimo": param_svc.get("qa_embedding_responde_min", settings.QA_SCORE_MINIMO, float)
        or settings.QA_SCORE_MINIMO,
        "rag_score_minimo": param_svc.get("rag_score_minimo", settings.RAG_SCORE_MINIMO, float)
        or settings.RAG_SCORE_MINIMO,
        "rag_top_k": settings.RAG_TOP_K,
        "qa_top_k": settings.QA_TOP_K,
    }

    qa_service = None
    retrieval_service = None
    try:
        from services.rag import get_qa_service

        qa_service = get_qa_service()
    except Exception as exc:
        logger.warning("[PacoteAnalise] QAService indisponível: %s", exc)
    try:
        from services.rag import get_retrieval_service

        retrieval_service = get_retrieval_service()
        parametros["rag_score_minimo"] = getattr(
            retrieval_service, "_score_minimo_padrao", parametros["rag_score_minimo"]
        )
    except Exception as exc:
        logger.warning("[PacoteAnalise] RetrievalService indisponível: %s", exc)

    classificacao_nova = await _reprocessar_classificacao(pergunta_texto)
    diagnostico = await _reprocessar_buscas(
        query=pergunta_texto,
        qa_service=qa_service,
        retrieval_service=retrieval_service,
        qa_score_minimo=float(parametros["qa_score_minimo"]),
        rag_score_minimo=float(parametros["rag_score_minimo"]),
    )

    tipos_produto = (classificacao_nova.get("entidades") or {}).get("tipos_produto") or []
    if not tipos_produto:
        tipos_produto = extrair_entidades(pergunta_texto).tipos_produto

    root = projeto_root or Path(__file__).resolve().parents[3]
    documentos_sugeridos = sugerir_documentos_fonte(
        pergunta=pergunta_texto,
        rag_candidatos=diagnostico.get("rag_top_candidatos") or [],
        tipos_produto=tipos_produto,
        projeto_root=root,
    )

    hipoteses = _hipoteses_automaticas(
        pergunta=pergunta_texto,
        proc=proc_efetivo,
        diagnostico=diagnostico,
        parametros=parametros,
        classificacao_nova=classificacao_nova,
    )

    atendimento_id = None
    if pergunta_msg:
        atendimento_id = pergunta_msg.atendimento_id
    elif proc_efetivo:
        atendimento_id = proc_efetivo.atendimento_id_ativa

    centro_janela = pergunta_msg or (proc_efetivo.mensagem if proc_efetivo else None)

    return {
        "meta": {
            "report_id": report_id,
            "gerado_em": datetime.now(timezone.utc).isoformat(),
            "versao_pacote": PACOTE_VERSAO,
            "agente_sugerido": _agente_sugerido(report.categoria),
        },
        "report": report.to_dict(),
        "par_problema": {
            "pergunta_cliente": pergunta_texto,
            "resposta_sistema": resposta_msg.conteudo if resposta_msg else None,
            "mensagem_cliente_id": pergunta_msg.id if pergunta_msg else None,
            "mensagem_sistema_id": resposta_msg.id if resposta_msg else None,
        },
        "processamento_original": proc_efetivo.to_dict() if proc_efetivo else None,
        "conversa": {
            "telefone": pergunta_msg.telefone if pergunta_msg else None,
            "atendimento_id": atendimento_id,
            "janela_mensagens": _janela_mensagens(session, centro_janela, antes, depois),
            "atendimento_contexto": _carregar_atendimento_contexto(session, atendimento_id),
        },
        "reprocessamento": {
            "classificacao_atual": classificacao_nova,
            "diagnostico_busca": diagnostico,
            "parametros_runtime": parametros,
        },
        "documentos_fonte_sugeridos": documentos_sugeridos,
        "hipoteses_automaticas": hipoteses,
        "notas_curador": [
            "Este pacote reprocessa buscas com o estado ATUAL da base (Q&A, RAG, parâmetros).",
            "Reports antigos já resolvidos ainda são úteis para validar se a correção aplicada funcionaria hoje.",
            "O agente [curador_conhecimento] deve propor mudanças em docs/FoldersProdutos/*.txt e/ou pares Q&A.",
            "Nenhuma alteração é aplicada automaticamente em produção (REQ-012.14).",
        ],
    }
