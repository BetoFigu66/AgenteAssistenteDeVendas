"""
Registro do gatilho/evidências de cada escalonamento e avaliação humana (REQ-004.5B/5C).

Quem decide escalar continua sendo `ProcessadorMensagem._escalar_atendimento`; este módulo
só grava o `Escalonamento` ligado ao evento e trata a avaliação feita no painel.

Regra das evidências: valores extraídos, limiares vigentes, intenção/confiança e origem da
classificação. Nunca o texto da mensagem (ele já está em `mensagens`, e o vínculo basta).

Avaliação "indevido" abre um `ReportProblema` na fila de triagem (decisão do Beto,
27/09/2026), um só por escalonamento: ver `avaliar_escalonamento`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Sequence

from models import (
    GATILHO_UNICO_POR_MOTIVO,
    Atendimento,
    AvaliacaoEscalonamento,
    CategoriaReport,
    Escalonamento,
    EventoAtendimento,
    GatilhoEscalonamento,
    HistoricoStatusReport,
    MotivoEscalonamento,
    ReportProblema,
    SeveridadeReport,
)
from sqlalchemy.orm import Session
from utils.datetime_utils import utc_now

if TYPE_CHECKING:
    from services.classificador import ResultadoClassificacao


def evidencias_da_classificacao(resultado_class: Optional["ResultadoClassificacao"]) -> dict[str, Any]:
    """Intenções, confiança e origem (regra/llm) da classificação da mensagem que
    provocou o escalonamento. Vazio quando não há classificação (takeover manual)."""
    if resultado_class is None:
        return {}
    return {
        "intencoes": [i.value for i in resultado_class.intencoes],
        "confianca": round(float(resultado_class.confianca), 4),
        "confianca_nivel": resultado_class.confianca_nivel.value,
        "origem_classificacao": resultado_class.origem,
    }


def registrar_escalonamento(
    db: Session,
    atendimento: Atendimento,
    *,
    motivo: MotivoEscalonamento,
    ator: str,
    evento: Optional[EventoAtendimento] = None,
    gatilhos: Optional[Sequence[GatilhoEscalonamento]] = None,
    evidencias: Optional[dict[str, Any]] = None,
    mensagem_id: Optional[int] = None,
    processamento_id: Optional[int] = None,
) -> Escalonamento:
    """Grava o `Escalonamento` na mesma transação do evento `escalado` (só `flush`, como
    `registrar_evento_atendimento`).

    Sem `gatilhos`, usa o gatilho único do motivo (`GATILHO_UNICO_POR_MOTIVO`); projeto
    complexo não tem gatilho único e fica com lista vazia se o chamador não disser quais
    condições dispararam. `mensagem_id`/`processamento_id` ausentes aqui são preenchidos
    pelo back-fill do fim de `ProcessadorMensagem.processar()`, junto com os do evento.
    """
    if gatilhos is None:
        unico = GATILHO_UNICO_POR_MOTIVO.get(motivo)
        gatilhos = [unico] if unico else []
    escalonamento = Escalonamento(
        atendimento_id=atendimento.id,
        evento_id=evento.id if evento is not None else None,
        mensagem_id=mensagem_id,
        processamento_id=processamento_id,
        motivo=motivo.value,
        gatilhos=[g.value for g in gatilhos],
        evidencias=dict(evidencias or {}),
        ator=ator,
    )
    db.add(escalonamento)
    db.flush()
    return escalonamento


# Rótulos para texto gerado no backend (resumo para o vendedor, descrição do report). O
# frontend tem os seus em `frontend/src/utils/atendimento.js` e `utils/escalonamento.js`.
LABEL_MOTIVO_ESCALONAMENTO: dict[MotivoEscalonamento, str] = {
    MotivoEscalonamento.SOLICITADO_CLIENTE: "Cliente pediu para falar com atendente",
    MotivoEscalonamento.RECLAMACAO: "Reclamação/insatisfação do cliente",
    MotivoEscalonamento.PROJETO_COMPLEXO: "Projeto complexo (quantidade/porte/leitor facial)",
    MotivoEscalonamento.BAIXA_CONFIANCA: "Baixa confiança do classificador (mensagens repetidamente ambíguas)",
    MotivoEscalonamento.BASE_INSUFICIENTE: "Base de conhecimento sem conteúdo suficiente",
    MotivoEscalonamento.MANUAL_VENDEDOR: "Assumido manualmente pelo vendedor",
    MotivoEscalonamento.MODELO_NAO_RECONHECIDO: "Modelo não reconhecido no catálogo após tentativas",
}

LABEL_GATILHO_ESCALONAMENTO: dict[GatilhoEscalonamento, str] = {
    GatilhoEscalonamento.INTENCAO_ESCALAR_HUMANO: "Cliente pediu para falar com uma pessoa",
    GatilhoEscalonamento.INTENCAO_RECLAMAR: "Cliente reclamou ou demonstrou insatisfação",
    GatilhoEscalonamento.QUANTIDADE_MINIMA: "Cliente pediu muitos equipamentos de uma vez",
    GatilhoEscalonamento.FAIXA_FUNCIONARIOS: "Empresa do cliente tem muitos funcionários",
    GatilhoEscalonamento.LEITOR_FACIAL: "Cliente falou em leitor facial",
    GatilhoEscalonamento.BAIXA_CONFIANCA_REPETIDA: "O sistema não entendeu várias mensagens seguidas",
    GatilhoEscalonamento.BASE_SEM_RESPOSTA: "O sistema não tinha resposta para a pergunta",
    GatilhoEscalonamento.TENTATIVAS_ESGOTADAS: "O sistema não conseguiu identificar o modelo do equipamento",
    GatilhoEscalonamento.ASSUMIDO_PELO_VENDEDOR: "Vendedor assumiu a conversa",
}

# `HistoricoStatusReport.campo` das linhas que anotam no report a mudança de avaliação do
# escalonamento de origem. "nao_avaliado" é o valor gravado quando a avaliação é desfeita.
CAMPO_HISTORICO_AVALIACAO = "avaliacao_escalonamento"
VALOR_NAO_AVALIADO = "nao_avaliado"


def _rotulo(enum_cls, labels: dict, valor: Optional[str]) -> str:
    try:
        return labels[enum_cls(valor)]
    except (ValueError, KeyError):
        return str(valor)


def descricao_report_indevido(escalonamento: Escalonamento) -> str:
    """Texto do report de um escalonamento avaliado como indevido: motivo, gatilhos,
    evidências e comentário do avaliador. Os valores técnicos vão entre parênteses para
    quem for corrigir a regra achar o código correspondente."""
    motivo = _rotulo(MotivoEscalonamento, LABEL_MOTIVO_ESCALONAMENTO, escalonamento.motivo)
    linhas = [
        f"Escalonamento #{escalonamento.id} (atendimento #{escalonamento.atendimento_id}) "
        f"avaliado como indevido por {escalonamento.avaliado_por}.",
        f"Motivo: {motivo} ({escalonamento.motivo})",
    ]
    gatilhos = list(escalonamento.gatilhos or [])
    if gatilhos:
        linhas.append("Gatilhos:")
        linhas += [
            f"- {_rotulo(GatilhoEscalonamento, LABEL_GATILHO_ESCALONAMENTO, g)} ({g})" for g in gatilhos
        ]
    else:
        linhas.append("Gatilhos: não registrados")
    evidencias = dict(escalonamento.evidencias or {})
    if evidencias:
        linhas.append("Evidências:")
        linhas += [f"- {chave}: {valor}" for chave, valor in evidencias.items()]
    linhas.append(f"Comentário do avaliador: {escalonamento.avaliacao_comentario or '(sem comentário)'}")
    return "\n".join(linhas)


def _tem_origem_para_report(escalonamento: Escalonamento) -> bool:
    """Report exige mensagem ou processamento; o takeover manual não tem nenhum dos dois."""
    return escalonamento.mensagem_id is not None or escalonamento.processamento_id is not None


def _sincronizar_report(
    db: Session, escalonamento: Escalonamento, avaliacao_anterior: Optional[str], ator: str
) -> None:
    """Abre o report do escalonamento indevido ou anota nele a mudança de avaliação.

    - Primeira vez "indevido": cria o report (categoria `escalonamento_indevido`, autor =
      avaliador) ligado à mensagem e ao processamento do escalonamento.
    - Sem mensagem nem processamento (takeover manual pelo vendedor) não há report: a
      tabela exige um dos dois (`chk_processamento_ou_mensagem_not_null`), e um takeover
      indevido é decisão de uma pessoa, não regra do sistema a corrigir. A avaliação fica
      gravada do mesmo jeito.
    - "Indevido" de novo ou só comentário trocado: reusa o mesmo report e atualiza a
      descrição (texto gerado aqui, a triagem não o edita). Status, categoria e severidade
      ficam como a triagem deixou.
    - Saiu de "indevido" (procedente ou desfeita): o report fica, com a descrição de quando
      era indevido; a mudança vira uma linha no histórico do report, na mesma tela onde a
      triagem já lê as mudanças de status. Voltar a "indevido" também gera linha.
    """
    report = escalonamento.report
    indevido = escalonamento.avaliacao == AvaliacaoEscalonamento.INDEVIDO.value

    if report is None:
        if not indevido or not _tem_origem_para_report(escalonamento):
            return
        report = ReportProblema(
            processamento_id=escalonamento.processamento_id,
            mensagem_id=escalonamento.mensagem_id,
            descricao=descricao_report_indevido(escalonamento),
            autor=escalonamento.avaliado_por,
            categoria=CategoriaReport.ESCALONAMENTO_INDEVIDO,
            severidade=SeveridadeReport.MEDIA,
        )
        db.add(report)
        db.flush()
        escalonamento.report = report
        return

    if indevido:
        report.descricao = descricao_report_indevido(escalonamento)

    anterior = avaliacao_anterior or VALOR_NAO_AVALIADO
    nova = escalonamento.avaliacao or VALOR_NAO_AVALIADO
    if anterior != nova:
        db.add(
            HistoricoStatusReport(
                report_id=report.id,
                campo=CAMPO_HISTORICO_AVALIACAO,
                valor_anterior=anterior,
                valor_novo=nova,
                ator=ator,
            )
        )
        db.flush()


def avaliar_escalonamento(
    db: Session,
    escalonamento: Escalonamento,
    *,
    avaliacao: Optional[AvaliacaoEscalonamento],
    comentario: Optional[str],
    avaliado_por: str,
) -> Escalonamento:
    """REQ-004.5C: grava a avaliação (vale a última). `avaliacao=None` desfaz, voltando
    a "não avaliado" (limpa também comentário, autor e data).

    "Indevido" abre (uma vez só) um `ReportProblema`; ver `_sincronizar_report`. Só
    `flush`: o commit é de quem chamou, para avaliação e report caírem na mesma transação.
    """
    anterior = escalonamento.avaliacao
    if avaliacao is None:
        escalonamento.avaliacao = None
        escalonamento.avaliacao_comentario = None
        escalonamento.avaliado_por = None
        escalonamento.avaliado_em = None
    else:
        escalonamento.avaliacao = avaliacao.value
        escalonamento.avaliacao_comentario = (comentario or "").strip() or None
        escalonamento.avaliado_por = avaliado_por
        escalonamento.avaliado_em = utc_now()
    # `avaliado_por` como ator, e não o do escalonamento: desfazer limpa esse campo, e
    # quem desfez precisa ficar no histórico do report.
    _sincronizar_report(db, escalonamento, anterior, ator=avaliado_por)
    return escalonamento
