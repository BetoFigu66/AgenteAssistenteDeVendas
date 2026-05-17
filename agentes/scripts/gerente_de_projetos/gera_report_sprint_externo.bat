@echo off
REM Via cmd / PowerShell, na raiz do projeto
pushd "%~dp0\..\..\.."
if not exist ".venv\" (
  echo .venv não encontrado. Criando ambiente virtual e instalando dependências...
  python -m venv .venv
  call ".venv\Scripts\activate.bat"
  pip install -r backend\requirements.txt
) else (
  call ".venv\Scripts\activate.bat"
)
python agentes\scripts\gerente_de_projetos\gera_sprint_report.py artefatos\gerente_de_projetos\reports\sprint_02_20260510_externo.yaml artefatos\gerente_de_projetos\report_templates\template_sprint_review_externo.pptx -o .\artefatos\gerente_de_projetos\reports\sprint_02_20260510_externo.pptx
popd
