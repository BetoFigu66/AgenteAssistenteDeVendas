"""
Ponte entre os reports de problema e o sistema de goals do Claude.

Um report marcado com "Correção automática" na triagem (`reports_problema.correcao_automatica`)
vira um goal pessoal (`~/Work/Organizacao/goals/report-<id>/`) com worktree próprio na branch
`fix/report-<id>`, e o executor do goal (skill goal-run, sessão `claude --bg`) faz o resto:
causa raiz, teste que falha, correção, suíte completa, commit, push em develop, deploy
(`scripts/deploy_auto.sh`) e a resolução do report (subcomando `resolver` daqui).

Uso (a partir de backend/, com o venv):
    venv/bin/python -m scripts.ponte_reports_goals fila
    venv/bin/python -m scripts.ponte_reports_goals despachar [--max-simultaneos 1] [--aguardar] [--dry-run]
    venv/bin/python -m scripts.ponte_reports_goals contexto <report_id>
    venv/bin/python -m scripts.ponte_reports_goals resolver <report_id> --goal <id> --commit <sha> --resumo "..."
    venv/bin/python -m scripts.ponte_reports_goals responder <report_id> --goal <id> --arquivo <resposta.md>

Report da categoria Dúvida vira um goal que só responde (sem código, push nem deploy): o
executor grava a resposta com `responder`, e ela aparece na tela do report como "Claude".

`despachar` é o que a tarefa agendada do Windows roda (scripts/instalar_ponte_goals.ps1).
Com `--aguardar` o processo fica vivo enquanto houver goal de report executando: é o que
mantém o WSL acordado, já que a tarefa chama `wsl.exe` e o WSL desliga quando nada mais roda.
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import yaml
from database import Database
from services import correcao_automatica as svc

BACKEND = Path(__file__).resolve().parents[1]
GOAL = str(Path.home() / "bin" / "goal")
GOALS_PESSOAIS = Path.home() / "Work" / "Organizacao" / "goals"
TAG = "report"
EM_ANDAMENTO = ("pronto", "executando")
# Exceções à trava dos executores (~/.claude/hooks/goal_guard.py e skill goal-run): este goal
# publica em develop, faz o deploy e conclui sozinho. Projeto não oficial, sem revisão humana
# por decisão do Beto (21/11/2026).
PERMITE = "push:develop,deploy,concluir"
# Dúvida só é respondida: nada de push nem deploy.
PERMITE_DUVIDA = "concluir"
ESPERA_MAX_S = 4 * 3600

# Trava de quota: só despacha se o uso semanal estiver dentro do ritmo proporcional ao tempo
# útil decorrido desde o reinício (cada hora entre HORA_INICIO e HORA_FIM conta igual; fora
# disso o orçamento não cresce). NIVEL_QUOTA multiplica esse ritmo: 1 = 100% do proporcional,
# 0.8 = exige estar 20% abaixo dele. Configurável por --nivel-quota ou PONTE_NIVEL_QUOTA.
NIVEL_QUOTA = float(os.environ.get("PONTE_NIVEL_QUOTA", "1"))
HORA_INICIO, HORA_FIM = 8, 18


def log(msg: str) -> None:
    print(f"{time.strftime('%d/%m %H:%M:%S')} [ponte] {msg}", flush=True)


def raiz_repo() -> Path:
    """Checkout principal, mesmo quando o script roda de dentro de um worktree."""
    comum = git("rev-parse", "--git-common-dir", cwd=BACKEND)  # relativo ao cwd no git 2.25
    return (BACKEND / comum).resolve().parent


def goal(*args: str, entrada: str | None = None) -> str:
    r = subprocess.run([GOAL, *args], input=entrada, capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        raise RuntimeError(f"goal {' '.join(args[:2])} falhou: {(r.stderr or r.stdout).strip()}")
    return r.stdout.strip()


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def goals_de_report() -> list[dict]:
    """Frontmatter dos goals pessoais com a tag `report`."""
    saida = []
    for md in sorted(GOALS_PESSOAIS.glob("*/goal.md")):
        txt = md.read_text(encoding="utf-8")
        if not txt.startswith("---\n"):
            continue
        meta = yaml.safe_load(txt[4:txt.find("\n---\n", 4)]) or {}
        if TAG in (meta.get("tags") or []):
            saida.append(meta)
    return saida


def status_do_goal(gid: str) -> str | None:
    return next((g.get("status") for g in goals_de_report() if g.get("id") == gid), None)


def em_andamento() -> list[dict]:
    return [g for g in goals_de_report() if g.get("status") in EM_ANDAMENTO]


def ocupando_vaga(fila) -> list[dict]:
    """Goals de report que ocupam vaga, menos os dos reports que estão na fila.

    Report na fila ainda não foi vinculado, então o goal dele (sobra de uma rodada que falhou,
    talvez já posto em `pronto` à mão) não está executando nada: contá-lo travaria a vaga que
    ele mesmo precisa (caso do report-7 em 22/11/2026).
    """
    da_fila = {f"report-{r.id}" for r in fila}
    return [g for g in em_andamento() if g.get("id") not in da_fila]


# ------------------------------------------------------------------ quota
def horas_uteis(inicio: datetime, fim: datetime, h_ini: int = HORA_INICIO, h_fim: int = HORA_FIM) -> float:
    """Horas de [inicio, fim] que caem dentro do expediente diário [h_ini, h_fim)."""
    total = 0.0
    dia = inicio.replace(hour=0, minute=0, second=0, microsecond=0)
    while dia < fim:
        a = max(inicio, dia.replace(hour=h_ini))
        b = min(fim, dia.replace(hour=h_fim))
        if b > a:
            total += (b - a).total_seconds() / 3600
        dia += timedelta(days=1)
    return total


def uso_esperado(agora: datetime, proximo_reinicio: datetime) -> float:
    """Fração da quota semanal (0 a 1) que o ritmo proporcional permite ter gasto até `agora`.

    A semana vai de `proximo_reinicio - 7 dias` até `proximo_reinicio`; com reinício no sábado
    10:00 e expediente 8h-18h são 70 horas úteis, e cada uma soma 1/70.
    """
    inicio = proximo_reinicio - timedelta(days=7)
    return horas_uteis(inicio, agora) / horas_uteis(inicio, proximo_reinicio)


def ler_quota(repo: Path) -> tuple[float, datetime]:
    """(uso semanal em %, próximo reinício) via scripts/claude_quota.py --csv."""
    r = subprocess.run([sys.executable, str(repo / "scripts" / "claude_quota.py"), "--csv"],
                       capture_output=True, text=True, timeout=60)
    linha = next(csv.reader(io.StringIO(r.stdout.strip().splitlines()[-1])))
    return float(linha[3]), datetime.fromisoformat(linha[4])


def quota_permite(repo: Path, nivel: float) -> bool:
    try:
        uso_pct, reinicio = ler_quota(repo)
    except Exception as exc:  # sem leitura da quota, não arrisca
        log(f"quota ilegível, não despacho: {exc}")
        return False
    agora = datetime.now(reinicio.tzinfo)
    limite_pct = 100 * nivel * uso_esperado(agora, reinicio)
    if uso_pct > limite_pct:
        log(f"quota semanal em {uso_pct:.0f}%, acima do limite de agora ({limite_pct:.1f}% = "
            f"{nivel:g} x proporcional): não despacho")
        return False
    log(f"quota semanal em {uso_pct:.0f}%, limite de agora {limite_pct:.1f}%")
    return True


# ------------------------------------------------------------------ texto do goal
def objetivo(report_id: int, gid: str, py: str) -> str:
    return f"""Corrigir o defeito do report #{report_id} do AgenteAssistenteDeVendas de ponta a ponta, sem revisão humana, nesta ordem:

1. Ler `artefatos/contexto-report.md` (report, processamento e conversa). Para mais dados, consultar o banco só com SELECT: `docker.exe exec inforrel_postgres psql -U inforrel -d assistente_vendas -c "..."`. CPF, CNPJ, e-mail e datas de nascimento vistos no banco não vão para artefatos, log nem commit (o contexto já vem mascarado).
2. Causa raiz: reproduzir o comportamento, achar o mecanismo no código e gravar `artefatos/causa-raiz.md` (sintoma, causa com arquivo:linha, por que os testes atuais não pegaram). Se o report não descreve um defeito reproduzível (pedido de funcionalidade, regra de negócio a decidir, descrição ambígua), não corrija: registre `goal perguntar {gid} --tipo decisao` e encerre.
3. Teste novo em `backend/tests/` que reproduz o defeito. Rodar e confirmar que FALHA antes da correção; guardar a saída em `artefatos/teste-falhando.txt`.
4. Correção mínima, no worktree.
5. Suíte completa, toda verde (o teste novo passando): em `backend/`, `{py} -m pytest -q`; na raiz, `ruff check .` e `{py} scripts/qa_check.py --escopo pre-commit`; se mexeu em `frontend/`, `npm run lint && npm run build` dentro de `frontend/`. Guardar o resumo em `artefatos/testes.txt`.
6. `git add` só dos arquivos da mudança, `{py} scripts/versao.py atualizar`, commit em português citando "report #{report_id}".
7. Publicar: `git fetch origin develop && git rebase origin/develop`; se o rebase trouxe commits, rodar o pytest de novo; então `git push origin HEAD:develop`. Conflito só no `VERSAO`: resolver rodando `scripts/versao.py atualizar` de novo. Push recusado: repetir fetch, rebase e testes (até 3 vezes).
8. Deploy: `bash scripts/deploy_auto.sh` (espera o /health responder com a versão nova).
9. Fechar o report: em `backend/`, `{py} -m scripts.ponte_reports_goals resolver {report_id} --goal {gid} --commit <sha> --resumo "<causa e correção em 1-2 frases>"`.
10. `artefatos/resumo.md`, `goal estado`, e `goal status {gid} concluido --motivo "<resumo>"`.

Exceções deste goal à trava do executor (frontmatter `permite: {PERMITE}`): pode dar push em develop, fazer o deploy e concluir o goal sem revisão humana. Nunca: `--force`, `--no-verify`, apagar ou pular teste existente para passar, push em outra branch. Se a suíte não ficar verde, o rebase tiver conflito fora do `VERSAO` ou o deploy falhar, pare e registre `goal perguntar {gid} --tipo decisao` com a saída."""  # noqa: E501 (texto do goal, um passo por linha)


def objetivo_duvida(report_id: int, gid: str, py: str) -> str:
    return f"""Responder a dúvida do report #{report_id} do AgenteAssistenteDeVendas. Quem perguntou é usuário do painel (equipe Inforrel ou de desenvolvimento) e vai ler a resposta na tela do report. Não altere código, não faça commit, push nem deploy.

1. Ler `artefatos/contexto-report.md` (a dúvida, o processamento e a conversa em volta). Para mais dados, consultar o banco só com SELECT: `docker.exe exec inforrel_postgres psql -U inforrel -d assistente_vendas -c "..."`. CPF, CNPJ, e-mail e datas de nascimento vistos no banco não vão para a resposta, artefatos nem log.
2. Investigar no código deste worktree (origin/develop), no CLAUDE.md, em `docs/` e nos requisitos (`artefatos/requisitos_formais/`) até ter uma resposta fundamentada. Se a dúvida é sobre o comportamento numa conversa, explicar o porquê olhando o processamento (intenção, regra, template, RAG).
3. Escrever a resposta em `artefatos/resposta.md`, em português, para quem usa o painel: direta, sem jargão de código quando não for preciso (arquivo:linha só se ajudar), sem travessões em excesso. Se a dúvida revelar um defeito, diga isso na resposta e sugira registrar um report de correção. Se não houver como responder com segurança, diga o que falta, em vez de inventar.
4. Gravar: em `backend/`, `{py} -m scripts.ponte_reports_goals responder {report_id} --goal {gid} --arquivo <caminho absoluto de artefatos/resposta.md>`.
5. `goal estado` e `goal status {gid} concluido --motivo "dúvida respondida"`.

Exceção deste goal à trava do executor (frontmatter `permite: {PERMITE_DUVIDA}`): pode concluir sem revisão humana. Se não conseguir gravar a resposta, registre `goal perguntar {gid} --tipo decisao` com a saída."""  # noqa: E501 (texto do goal, um passo por linha)


PRONTO_DUVIDA = (
    "Resposta fundamentada gravada no report (aparece na tela como respondida pelo Claude); "
    "nenhum código alterado."
)


def texto_contexto(report_id: int, py: str) -> str:
    return (
        f"Criado pela ponte `backend/scripts/ponte_reports_goals.py` a partir do report #{report_id}, "
        "marcado para correção automática na triagem. O recorte do report está em "
        "`artefatos/contexto-report.md`. Python com as dependências: "
        f"`{py}` (o venv do checkout principal; `backend/venv` do worktree é um link para ele). "
        "Arquitetura e regras do projeto: CLAUDE.md da raiz."
    )


PRONTO = (
    "Teste novo que falhava antes e passa depois; suíte completa verde; commit em origin/develop; "
    "deploy feito com /health na versão nova; report resolvido com o commit na resolução."
)


# ------------------------------------------------------------------ worktree
def preparar_worktree(repo: Path, gid: str, branch: str) -> Path:
    """Worktree em origin/develop com o que o git não traz: venv, node_modules e .env.

    Feito aqui e não pelo `goal disparar --worktree` porque o executor precisa disso já na
    primeira instrução, e o `disparar` lança a sessão logo depois de criar o worktree.
    """
    wt = repo / ".worktrees" / gid
    excl = repo / ".git" / "info" / "exclude"
    if "/.worktrees/" not in (excl.read_text().splitlines() if excl.exists() else []):
        with open(excl, "a") as f:
            f.write("/.worktrees/\n")
    git("fetch", "origin", "develop", cwd=repo)
    if not wt.is_dir():
        existe = subprocess.run(["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"],
                                cwd=repo, capture_output=True).returncode == 0
        if existe:
            git("worktree", "add", str(wt), branch, cwd=repo)
        else:
            git("worktree", "add", "-b", branch, str(wt), "origin/develop", cwd=repo)
    for rel in ("backend/venv", "frontend/node_modules"):
        origem, destino = repo / rel, wt / rel
        if origem.exists() and not destino.exists():
            destino.symlink_to(origem)
    env = repo / "backend" / ".env"
    if env.exists():
        shutil.copy2(env, wt / "backend" / ".env")
    return wt


# ------------------------------------------------------------------ comandos
def cmd_fila(_a) -> None:
    db = Database()
    with db.get_session() as session:
        fila = svc.listar_fila(session)
        print(f"Na fila: {len(fila)}")
        for r in fila:
            print(f"  #{r.id} [{r.severidade.value}] {svc.mascarar(r.descricao)[:90]!r}")
    print("Goals de report:")
    for g in goals_de_report():
        print(f"  {g['id']}: {g.get('status')}")


def eh_duvida(report) -> bool:
    categoria = getattr(report, "categoria", None)
    return categoria is not None and categoria.value == "duvida"


def despachar_um(session, report, repo: Path, py: str) -> str:
    gid = f"report-{report.id}"
    duvida = eh_duvida(report)
    branch = f"{'duvida' if duvida else 'fix'}/{gid}"
    rotulo = "Dúvida" if duvida else "Report"
    titulo = f"{rotulo} #{report.id}: {' '.join(svc.mascarar(report.descricao).split())[:70]}"
    if not (GOALS_PESSOAIS / gid).is_dir():  # reaproveita o goal de uma rodada que caiu no meio
        goal("novo", "--contexto", "pessoal", "--id", gid, "--titulo", titulo, "--workdir", str(repo),
             "--status", "pronto",  # o padrão é rascunho, e o `goal disparar` só aceita pronto
             "--prioridade", "alta" if report.severidade.value in ("alta", "critica") else "media",
             "--tag", TAG,
             "--objetivo", objetivo_duvida(report.id, gid, py) if duvida else objetivo(report.id, gid, py),
             "--texto-contexto", texto_contexto(report.id, py),
             "--pronto", PRONTO_DUVIDA if duvida else PRONTO)
    elif status_do_goal(gid) != "pronto":
        goal("status", gid, "pronto", "--motivo", "redespacho pela ponte depois de uma rodada interrompida")
    goal("set", gid, f"permite={PERMITE_DUVIDA if duvida else PERMITE}")
    goal("artefato", gid, "contexto-report.md", entrada=svc.contexto_markdown(session, report.id))
    wt = preparar_worktree(repo, gid, branch)
    goal("set", gid, f"worktree={wt}", f"branch={branch}")
    log(goal("disparar", gid))
    # Só vincula depois do disparo: com o goal_id gravado o report sai da fila, e uma falha antes
    # disso o deixaria órfão (fora da fila e sem executor). Falhou antes, tenta de novo na próxima.
    svc.vincular_goal(session, report.id, gid)
    return gid


def cmd_despachar(a) -> None:
    repo = raiz_repo()
    py = str(repo / "backend" / "venv" / "bin" / "python")
    db = Database()
    with db.get_session() as session:
        fila = svc.listar_fila(session)
        ativos = ocupando_vaga(fila)
        vagas = a.max_simultaneos - len(ativos)
        if not fila:
            log(f"fila vazia ({len(ativos)} goal(s) de report em andamento)")
        elif vagas <= 0:
            log(f"{len(fila)} na fila, sem vaga: em andamento {[g['id'] for g in ativos]}")
        elif not quota_permite(repo, a.nivel_quota):
            vagas = 0
        for report in fila[:max(vagas, 0)]:
            if a.dry_run:
                log(f"[dry-run] criaria goal report-{report.id}")
                continue
            try:
                log(f"report #{report.id} → goal {despachar_um(session, report, repo, py)}")
            except Exception as exc:  # um report com problema não trava os outros
                session.rollback()
                log(f"report #{report.id}: falha ao despachar: {exc}")
    if a.aguardar and not a.dry_run:
        inicio = time.time()
        while time.time() - inicio < ESPERA_MAX_S:
            executando = [g["id"] for g in goals_de_report() if g.get("status") == "executando"]
            if not executando:
                break
            time.sleep(60)
        log("fim da espera")


def cmd_contexto(a) -> None:
    db = Database()
    with db.get_session() as session:
        sys.stdout.write(svc.contexto_markdown(session, a.report_id))


def cmd_resolver(a) -> None:
    resolucao = (
        f"Corrigido automaticamente pelo goal {a.goal} (commit {a.commit[:12]} em develop, "
        f"com deploy).\n\n{a.resumo}"
    )
    db = Database()
    with db.get_session() as session:
        r = svc.resolver(session, a.report_id, resolucao)
        print(f"report #{r.id}: {r.status.value}")


def cmd_responder(a) -> None:
    texto = Path(a.arquivo).read_text(encoding="utf-8") if a.arquivo else a.texto
    if not (texto or "").strip():
        sys.exit("resposta vazia: passe --arquivo ou --texto")
    db = Database()
    with db.get_session() as session:
        svc.adicionar_resposta(session, a.report_id, texto, svc.OrigemRespostaReport.CLAUDE,
                               f"Claude (goal {a.goal})")
        r = session.query(svc.ReportProblema).filter_by(id=a.report_id).one()
        print(f"report #{r.id}: resposta gravada, status {r.status.value}")


def main() -> None:
    p = argparse.ArgumentParser(description="Ponte reports de problema → goals do Claude")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fila").set_defaults(f=cmd_fila)
    d = sub.add_parser("despachar")
    d.add_argument("--max-simultaneos", type=int, default=1)
    d.add_argument("--aguardar", action="store_true", help="fica vivo enquanto houver goal de report executando")
    d.add_argument("--dry-run", action="store_true")
    d.add_argument("--nivel-quota", type=float, default=NIVEL_QUOTA,
                   help="1 = pode gastar até 100%% do ritmo proporcional da semana (padrão: PONTE_NIVEL_QUOTA ou 1)")
    d.set_defaults(f=cmd_despachar)
    c = sub.add_parser("contexto")
    c.add_argument("report_id", type=int)
    c.set_defaults(f=cmd_contexto)
    r = sub.add_parser("resolver")
    r.add_argument("report_id", type=int)
    r.add_argument("--goal", required=True)
    r.add_argument("--commit", required=True)
    r.add_argument("--resumo", required=True)
    r.set_defaults(f=cmd_resolver)
    resp = sub.add_parser("responder", help="grava a resposta do Claude a um report (Dúvida)")
    resp.add_argument("report_id", type=int)
    resp.add_argument("--goal", required=True)
    fonte = resp.add_mutually_exclusive_group(required=True)
    fonte.add_argument("--arquivo", help="arquivo com a resposta (markdown/texto)")
    fonte.add_argument("--texto")
    resp.set_defaults(f=cmd_responder)
    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
