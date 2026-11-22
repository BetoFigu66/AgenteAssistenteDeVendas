"""Correção automática de reports por goals do Claude.

Um report marcado com `correcao_automatica` na triagem entra na fila. A ponte
(`backend/scripts/ponte_reports_goals.py`, rodada por tarefa agendada do Windows) cria
um goal para cada um, e o executor do goal analisa a causa raiz, escreve o teste que
falha, corrige num worktree, roda a suíte, publica em develop e faz o deploy. Este módulo
é o lado do banco: a fila, o vínculo report → goal e a resolução, sempre com a linha de
histórico (REQ-012.8) na mesma transação.
"""

import re
from datetime import timedelta
from typing import Optional

from models import (
    CategoriaReport,
    HistoricoStatusReport,
    Mensagem,
    OrigemRespostaReport,
    ReportProblema,
    RespostaReport,
    StatusReport,
)
from sqlalchemy.orm import Session
from utils.datetime_utils import utc_now

# Dado pessoal no texto das mensagens (CPF/CNPJ com ou sem pontuação, e-mail, data completa,
# que na conversa costuma ser a de nascimento) sai mascarado do contexto que vai para o goal:
# o executor é uma sessão do Claude, e CPF não entra em conversa com ele (regra 1 da Fitec).
_DADO_PESSOAL = re.compile(
    r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"  # CNPJ
    r"|\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"  # CPF
    r"|[\w.+-]+@[\w-]+\.[\w.]+"  # e-mail
    r"|\b\d{1,2}/\d{1,2}/\d{4}\b"  # data completa
)


def mascarar(texto: str) -> str:
    """Troca cada dado pessoal por um marcador do tipo, preservando o tamanho em dígitos."""

    def troca(m: re.Match) -> str:
        v = m.group(0)
        if "@" in v:
            return "<email>"
        digitos = len(re.sub(r"\D", "", v))
        if "/" in v and digitos <= 8:
            return "<data>"
        return f"<documento {digitos} dígitos>"

    return _DADO_PESSOAL.sub(troca, texto or "")


# Quem aparece no histórico do report quando a mudança veio da automação.
ATOR = "correcao-automatica"

_STATUS_TERMINAIS = (StatusReport.RESOLVIDO, StatusReport.DESCARTADO)
CARENCIA = timedelta(minutes=2)
_ORDEM_SEVERIDADE = {"critica": 0, "alta": 1, "media": 2, "baixa": 3}


def registrar_alteracao_report(session: Session, report, campo, valor_anterior, valor_novo, ator) -> None:
    """Anota no histórico do report que `campo` mudou (REQ-012.8).

    Só `add` + `flush`: o commit é de quem chamou, para que a alteração e o registro
    dela caiam na mesma transação. Estado e evento de auditoria em dois commits
    separados abrem a janela em que um existe sem o outro.
    """
    session.add(
        HistoricoStatusReport(
            report_id=report.id,
            campo=campo,
            valor_anterior=valor_anterior,
            valor_novo=valor_novo,
            ator=ator,
        )
    )
    session.flush()


def _mudar_status(session: Session, report: ReportProblema, novo: StatusReport, ator: str = ATOR) -> None:
    if report.status == novo:
        return
    registrar_alteracao_report(session, report, "status", report.status.value, novo.value, ator)
    report.status = novo
    if novo in _STATUS_TERMINAIS:
        report.resolvido_em = utc_now()
        report.resolvido_por = ator
    else:
        report.resolvido_em = None
        report.resolvido_por = None


def listar_fila(session: Session, carencia: timedelta = CARENCIA) -> list[ReportProblema]:
    """Reports marcados para correção automática que ainda não viraram goal.

    Só entra quem está parado há `carencia`: dá tempo de desmarcar um clique errado, e um
    report criado por teste automatizado (o pytest usa o mesmo banco) é apagado antes de a
    ponte enxergá-lo. Mais severo primeiro; no empate, o mais antigo.
    """
    reports = (
        session.query(ReportProblema)
        .filter(
            ReportProblema.correcao_automatica.is_(True),
            ReportProblema.goal_id.is_(None),
            ReportProblema.status.notin_(_STATUS_TERMINAIS),
            ReportProblema.updated_at <= utc_now() - carencia,
        )
        .all()
    )
    return sorted(
        reports,
        key=lambda r: (_ORDEM_SEVERIDADE.get(r.severidade.value if r.severidade else "", 9), r.created_at),
    )


def vincular_goal(session: Session, report_id: int, goal_id: str) -> ReportProblema:
    """Registra o goal criado para o report e o põe em análise."""
    report = session.query(ReportProblema).filter_by(id=report_id).one()
    registrar_alteracao_report(session, report, "goal_id", report.goal_id, goal_id[:30], ATOR)
    report.goal_id = goal_id
    _mudar_status(session, report, StatusReport.EM_ANALISE)
    session.commit()
    return report


def resolver(session: Session, report_id: int, resolucao: str) -> ReportProblema:
    """Marca o report como resolvido pela automação (depois do deploy).

    Passa por `em_analise` quando preciso, para respeitar as transições do workflow
    de triagem (`aberto` não vai direto para `resolvido`).
    """
    report = session.query(ReportProblema).filter_by(id=report_id).one()
    if report.status == StatusReport.ABERTO:
        _mudar_status(session, report, StatusReport.EM_ANALISE)
    _mudar_status(session, report, StatusReport.RESOLVIDO)
    report.resolucao = resolucao
    session.commit()
    return report


def adicionar_resposta(
    session: Session, report_id: int, texto: str, origem: OrigemRespostaReport, autor: str
) -> RespostaReport:
    """Grava uma resposta ao report; numa Dúvida ainda aberta, a resposta a resolve.

    Serve aos dois caminhos: a equipe pela tela (`POST /api/reports/{id}/respostas`) e o
    Claude pela ponte (`ponte_reports_goals responder`). A mudança de status leva o mesmo
    `autor` no histórico, para a linha dizer quem respondeu. Outras categorias recebem a
    resposta sem mudar de status: ali quem decide o fim é a triagem.
    """
    texto = (texto or "").strip()
    if not texto:
        raise ValueError("Resposta vazia")
    report = session.query(ReportProblema).filter_by(id=report_id).one()
    resposta = RespostaReport(report_id=report.id, texto=texto, origem=origem, autor=autor)
    session.add(resposta)
    if report.categoria == CategoriaReport.DUVIDA and report.status not in _STATUS_TERMINAIS:
        if report.status == StatusReport.ABERTO:
            _mudar_status(session, report, StatusReport.EM_ANALISE, autor)
        _mudar_status(session, report, StatusReport.RESOLVIDO, autor)
    session.commit()
    session.refresh(resposta)
    return resposta


def contexto_markdown(session: Session, report_id: int, janela: int = 12) -> str:
    """Texto que o executor do goal recebe: o report, o processamento e a conversa em volta.

    É o mesmo recorte de `GET /api/reports/{id}/contexto`, com janela maior, em markdown
    para caber direto num artefato do goal.
    """
    report = session.query(ReportProblema).filter_by(id=report_id).one()
    proc = report.processamento
    msg = proc.mensagem if proc else None
    if not msg and report.mensagem_id:
        msg = session.query(Mensagem).filter_by(id=report.mensagem_id).first()

    linhas = [
        f"# Report #{report.id}",
        "",
        f"- Categoria: {report.categoria.value}",
        f"- Severidade: {report.severidade.value}",
        f"- Status: {report.status.value}",
        f"- Autor: {report.autor or '(não informado)'}",
        f"- Criado em (UTC): {report.created_at:%Y-%m-%d %H:%M}",
        f"- processamento_id: {report.processamento_id}  mensagem_id: {report.mensagem_id}",
        "",
        "## Descrição de quem reportou",
        "",
        mascarar(report.descricao),
        "",
    ]

    if proc:
        p = proc.to_dict()
        linhas += ["## Processamento da mensagem", "", "```"]
        for chave in ("intencao", "intencoes", "confianca", "origem_classificacao", "entidades",
                      "status_identificacao", "fase_atendimento", "template_usado", "rag_utilizada",
                      "rag_score_maximo", "resultado_fallback", "justificativa_curta", "erro"):
            if p.get(chave) not in (None, "", [], {}):
                linhas.append(f"{chave}: {mascarar(str(p[chave]))}")
        linhas += ["```", ""]

    if msg:
        anteriores = (
            session.query(Mensagem)
            .filter(Mensagem.telefone == msg.telefone, Mensagem.timestamp < msg.timestamp)
            .order_by(Mensagem.timestamp.desc())
            .limit(janela)
            .all()
        )
        posteriores = (
            session.query(Mensagem)
            .filter(Mensagem.telefone == msg.telefone, Mensagem.timestamp > msg.timestamp)
            .order_by(Mensagem.timestamp.asc())
            .limit(3)
            .all()
        )
        linhas += ["## Conversa (a mensagem reportada está marcada com >>)", ""]
        for m in [*reversed(anteriores), msg, *posteriores]:
            origem = m.origem.value if hasattr(m.origem, "value") else m.origem
            marca = ">> " if m.id == msg.id else "   "
            texto = mascarar(m.conteudo).replace("\n", " / ")
            linhas.append(f"{marca}[{m.timestamp:%d/%m %H:%M}] {origem}: {texto}")
        linhas += ["", f"Telefone da conversa: {msg.telefone} (atendimento_id {msg.atendimento_id})"]

    return "\n".join(linhas) + "\n"


def goal_do_report(session: Session, report_id: int) -> Optional[str]:
    report = session.query(ReportProblema).filter_by(id=report_id).first()
    return report.goal_id if report else None
