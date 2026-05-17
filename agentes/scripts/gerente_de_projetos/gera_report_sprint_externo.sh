# Via WSL/Linux/macOS, na raiz do projeto
set -e
if [ ! -d ".venv" ]; then
  echo ".venv não encontrado. Criando ambiente virtual e instalando dependências..."
  if command -v python3 >/dev/null 2>&1; then
    python3 -m venv .venv
  else
    python -m venv .venv
  fi
  source .venv/bin/activate
  pip install -r backend/requirements.txt
else
  source .venv/bin/activate
fi
python agentes/scripts/gera_sprint_report.py artefatos/gerente_de_projetos/reports/sprint_02_20260510_externo.yaml artefatos/gerente_de_projetos/report_templates/template_sprint_review_externo.pptx -o ./artefatos/gerente_de_projetos/reports/sprint_02_20260510_externo.pptx