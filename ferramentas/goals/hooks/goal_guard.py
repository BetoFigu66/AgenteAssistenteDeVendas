#!/usr/bin/env python3
"""PreToolUse: trava das sessões executoras de goals.

Só age quando a variável GOAL_ID existe (sessões lançadas por `goal disparar`). Bloqueia ações que saem da
máquina (push, PR, escrita no Jira/Confluence, mensagens, deploy) e manda o executor registrar uma pergunta
com `goal perguntar`. Regra combinada em 2026-11-09 (ver ~/Work/Organizacao/README.md, seção Goals).
Sessões interativas normais não são afetadas.
"""
import json
import os
import re
import sys

MAPA = os.path.expanduser("~/.claude/state/goal_sessions.json")
CMD_RE = re.compile(r"<command-name>/goal-run</command-name>\s*<command-args>\s*([^\s<]+)")


def goal_da_sessao(data):
    """Sessão executora = registrada no mapa pelo `goal disparar`, ou cujo 1º prompt é /goal-run <id>
    (cobre os segundos entre o lançamento e a gravação do mapa). Variável de ambiente não serve: o daemon
    do `claude --bg` repassa a todas as sessões o ambiente da 1ª chamada."""
    sid = data.get("session_id") or ""
    try:
        with open(MAPA) as f:
            g = json.load(f).get("sessoes", {}).get(sid)
        if g:
            return g
    except Exception:
        pass
    tp = data.get("transcript_path")
    if not tp:
        return None
    try:
        with open(tp, encoding="utf-8", errors="ignore") as f:
            for _ in range(80):
                ln = f.readline(200_000)
                if not ln:
                    break
                if '"type":"user"' in ln:  # só o 1º prompt do usuário decide
                    content = json.loads(ln).get("message", {}).get("content")
                    m = CMD_RE.search(content) if isinstance(content, str) else None
                    return m.group(1) if m else None
    except Exception:
        return None
    return None


try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

GOAL = goal_da_sessao(data)
if not GOAL:
    sys.exit(0)

tool = data.get("tool_name", "")
inp = data.get("tool_input") or {}

BASH_DENY = [
    (r"\bgit\b[^;&|\n]*\spush\b", "git push"),
    (r"\bgh\s+pr\s+(create|merge|close|review|comment|edit|ready|reopen)\b", "gh pr (escrita)"),
    (r"\bgh\s+(issue|release|repo|secret|variable|workflow\s+run|run\s+(rerun|cancel))\b(?!\s+(list|view|status))",
     "gh (escrita)"),
    (r"\bgh\s+api\b.*(\s-X\s*(POST|PUT|PATCH|DELETE)|\s--method\s+(POST|PUT|PATCH|DELETE)|\s-[fF]\s)", "gh api (escrita)"),
    (r"\b(curl|wget)\b(?!.*\b(localhost|127\.0\.0\.1)\b).*(\s-X\s*(POST|PUT|PATCH|DELETE)|\s--data|\s-d\s|\s--post)",
     "HTTP de escrita para fora"),
    (r"\b(terraform|tofu)\s+(apply|destroy|import)\b", "terraform apply/destroy"),
    (r"\b(serverless|sls|sam|cdk)\s+(deploy|destroy|remove)\b", "deploy"),
    (r"\bkubectl\s+(apply|delete|create|patch|replace|scale|rollout)\b", "kubectl (escrita)"),
    (r"\b(npm|pnpm|yarn)\s+publish\b", "publish de pacote"),
    (r"\bclaude\s+.*--bg\b", "lançar outra sessão em background"),
]
AWS_READ = re.compile(r"\baws\s+(\S+\s+)?(describe-|get-|list-|filter-|lookup-|head-|ls\b|tail\b|sts\s+get-caller)")

motivo = None
if tool == "Bash":
    cmd = inp.get("command", "")
    if re.match(r"\s*goal\s", cmd):
        # chamadas do CLI goal: o texto entre aspas (log, pergunta) pode citar comandos; não é execução
        cmd = re.sub(r"'[^']*'|\"(\\.|[^\"\\])*\"", "''", cmd)
    for pat, nome in BASH_DENY:
        if re.search(pat, cmd, re.I | re.S):
            motivo = nome
            break
    if not motivo and re.search(r"(^|[;&|(\s])aws\s", cmd) and not AWS_READ.search(cmd):
        motivo = "aws (escrita/execução)"
elif tool.startswith("mcp__"):
    acao = tool.rsplit("__", 1)[-1]
    if re.match(r"(add|create|edit|transition|update|delete|send|post|reply|publish|upload|share|move|remove|batch)",
                acao, re.I):
        motivo = f"MCP de escrita ({tool})"
elif tool in ("Artifact", "ArtifactData", "ArtifactComments", "RemoteTrigger", "PushNotification", "SendMessage"):
    motivo = f"{tool} (publica/comunica para fora)"


def permissoes_do_goal(gid):
    """Campo `permite` do frontmatter do goal (ex.: "push:develop,deploy,concluir").

    Exceção por goal, combinada em 2026-11-21 para os goals de correção automática de reports do
    AgenteAssistenteDeVendas (projeto pessoal, sem revisão humana). Regex em vez de yaml: o hook
    roda com o python3 do sistema, que pode não ter o pyyaml.
    """
    org = os.path.expanduser("~/Work/Organizacao")
    for raiz in ("fitec/goals", "goals"):
        md = os.path.join(org, raiz, gid, "goal.md")
        try:
            with open(md, encoding="utf-8") as f:
                txt = f.read(4000)
        except OSError:
            continue
        m = re.search(r"^permite:\s*['\"]?([^'\"\n]*)", txt.split("\n---\n", 1)[0], re.M)
        return {x.strip() for x in m.group(1).split(",") if x.strip()} if m else set()
    return set()


def push_permitido(cmd, permite):
    """`git push origin HEAD:<branch>` (ou `<branch>`) para uma branch em `push:<branch>`, sem força nem remoção."""
    branches = {x.split(":", 1)[1] for x in permite if x.startswith("push:")}
    if not branches or re.search(r"\s(-f|--force\S*|-d|--delete|--mirror|--all|\+)", cmd):
        return False
    m = re.search(r"\bgit\b[^;&|\n]*\spush\s+origin\s+(?:HEAD:)?(?:refs/heads/)?([\w./-]+)\s*($|[;&|>2])", cmd)
    return bool(m) and m.group(1) in branches


if motivo == "git push" and push_permitido(inp.get("command", ""), permissoes_do_goal(GOAL)):
    motivo = None

if motivo:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            f"[goal {GOAL}] Bloqueado pela trava do executor: {motivo}. Executores de goal não fazem ações "
            f"externas. Prepare tudo (texto do PR/comentário em artefatos/, commit local) e registre o pedido com "
            f"`goal perguntar {GOAL} --tipo acao-humana --pergunta ... --contexto ...`, depois encerre o turno."),
    }}, ensure_ascii=False))
sys.exit(0)
