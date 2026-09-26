#!/usr/bin/env python3
"""
Consulta o uso da quota do plano Claude (janela de 5 horas e semanal).

Usa o endpoint NÃO documentado oficialmente que o Claude Code usa no /usage:
    GET https://api.anthropic.com/api/oauth/usage

O token OAuth é lido localmente (nunca é impresso), nesta ordem:
  1. variável de ambiente CLAUDE_CODE_OAUTH_TOKEN
  2. macOS Keychain ("Claude Code-credentials")
  3. ~/.claude/.credentials.json (Linux/Windows)

Pré-requisito: estar logado no Claude Code com a conta Pro/Max/Team.
Só usa a biblioteca padrão do Python 3.

Uso:
    python3 claude_quota.py          # saída legível
    python3 claude_quota.py --json   # JSON bruto da API
    python3 claude_quota.py --csv    # acrescenta uma linha em ~/.local/share/claude-quota/usage.csv

Com --csv, se a última linha do arquivo tiver menos de 3 minutos, a API não é consultada de
novo (evita o 429) e a última linha é reaproveitada. Em ambos os casos imprime a linha
vigente, para quem chamou não precisar abrir o arquivo.
"""
import csv
import json
import os
import platform
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

URL = "https://api.anthropic.com/api/oauth/usage"

CSV_PATH = Path.home() / ".local" / "share" / "claude-quota" / "usage.csv"
CSV_INTERVALO_MIN_S = 180
CSV_COLUNAS = [
    "consultado_em",
    "five_hour_pct",
    "five_hour_reseta",
    "seven_day_pct",
    "seven_day_reseta",
    "seven_day_opus_pct",
    "seven_day_sonnet_pct",
    "extra_pct",
]

LABELS = {
    "five_hour": "Janela de 5 horas",
    "seven_day": "Semanal (todos os modelos)",
    "seven_day_opus": "Semanal (Opus)",
    "seven_day_sonnet": "Semanal (Sonnet)",
}


def load_credentials():
    """Retorna (access_token, expires_at_ms ou None)."""
    env = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    if env:
        return env.strip(), None

    raw = None
    if platform.system() == "Darwin":
        try:
            raw = subprocess.run(
                ["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"],
                capture_output=True, text=True, check=True,
            ).stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            raw = None

    if raw is None:
        path = Path.home() / ".claude" / ".credentials.json"
        if not path.exists():
            sys.exit("Credenciais não encontradas. Faça login no Claude Code (`claude`) primeiro.")
        raw = path.read_text()

    data = json.loads(raw)
    oauth = data.get("claudeAiOauth", data)
    token = oauth.get("accessToken")
    if not token:
        sys.exit("accessToken não encontrado nas credenciais.")
    return token, oauth.get("expiresAt")


def claude_version():
    try:
        out = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=10).stdout
        return out.split()[0]
    except Exception:
        return "2.0.0"


def fetch_usage(token):
    req = urllib.request.Request(URL, headers={
        "Authorization": f"Bearer {token}",
        "anthropic-beta": "oauth-2025-04-20",
        # Sem este User-Agent a API tende a responder 429 persistente
        "User-Agent": f"claude-code/{claude_version()}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        if e.code == 401:
            sys.exit("401: token inválido/expirado. Abra o Claude Code uma vez para renovar e tente de novo.")
        if e.code == 429:
            sys.exit("429: rate limit. Espere alguns minutos (não consulte mais que ~1x a cada 3 min).")
        sys.exit(f"Erro HTTP {e.code}: {body}")


def bar(pct, width=30):
    filled = int(round(width * min(pct, 100) / 100))
    return "█" * filled + "░" * (width - filled)


def fmt_reset(iso):
    if not iso:
        return "-"
    dt = datetime.fromisoformat(iso).astimezone()  # fuso local
    delta = dt - datetime.now().astimezone()
    secs = max(int(delta.total_seconds()), 0)
    d, rem = divmod(secs, 86400)
    h, rem = divmod(rem, 3600)
    m = rem // 60
    falta = (f"{d}d " if d else "") + f"{h}h{m:02d}m"
    return f"{dt:%d/%m %H:%M} (em {falta})"


def _ultima_linha_csv():
    if not CSV_PATH.exists():
        return None
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    return linhas[-1] if linhas else None


def _linha_csv(data):
    def pct(key):
        w = data.get(key) or {}
        return "" if w.get("utilization") is None else f"{float(w['utilization']):.1f}"

    def reseta(key):
        iso = (data.get(key) or {}).get("resets_at")
        return datetime.fromisoformat(iso).astimezone().isoformat(timespec="minutes") if iso else ""

    extra = data.get("extra_usage") or {}
    return {
        "consultado_em": datetime.now().astimezone().isoformat(timespec="seconds"),
        "five_hour_pct": pct("five_hour"),
        "five_hour_reseta": reseta("five_hour"),
        "seven_day_pct": pct("seven_day"),
        "seven_day_reseta": reseta("seven_day"),
        "seven_day_opus_pct": pct("seven_day_opus"),
        "seven_day_sonnet_pct": pct("seven_day_sonnet"),
        "extra_pct": str(extra.get("utilization") or "") if extra.get("is_enabled") else "",
    }


def gravar_csv():
    """Acrescenta uma linha ao CSV, ou reaproveita a última se ela for recente."""
    ultima = _ultima_linha_csv()
    if ultima:
        idade = datetime.now().astimezone() - datetime.fromisoformat(ultima["consultado_em"])
        if idade.total_seconds() < CSV_INTERVALO_MIN_S:
            print(",".join(ultima[c] for c in CSV_COLUNAS), "(reaproveitada)")
            return

    token, expires_at = load_credentials()
    if expires_at and expires_at / 1000 < time.time():
        print("Aviso: o token parece expirado; abra o Claude Code para renová-lo.", file=sys.stderr)
    linha = _linha_csv(fetch_usage(token))

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    novo = not CSV_PATH.exists()
    with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=CSV_COLUNAS)
        if novo:
            escritor.writeheader()
        escritor.writerow(linha)
    print(",".join(linha[c] for c in CSV_COLUNAS))


def main():
    if "--csv" in sys.argv:
        gravar_csv()
        return

    token, expires_at = load_credentials()
    if expires_at and expires_at / 1000 < time.time():
        print("Aviso: o token parece expirado; abra o Claude Code para renová-lo.", file=sys.stderr)

    data = fetch_usage(token)

    if "--json" in sys.argv:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return

    for key, label in LABELS.items():
        w = data.get(key)
        if not w or w.get("utilization") is None:
            continue
        pct = float(w["utilization"])
        print(f"{label:<28} {bar(pct)} {pct:5.1f}%   reseta: {fmt_reset(w.get('resets_at'))}")

    extra = data.get("extra_usage") or {}
    if extra.get("is_enabled"):
        print(f"{'Uso extra':<28} utilização: {extra.get('utilization')}%  "
              f"créditos usados: {extra.get('used_credits')} / limite: {extra.get('monthly_limit')}")


if __name__ == "__main__":
    main()
