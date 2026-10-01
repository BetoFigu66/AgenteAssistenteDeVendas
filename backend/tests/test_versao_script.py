"""Classificação de arquivos do `scripts/versao.py`: o que conta como mudança de cada lado.

Decisão do Beto (01/10/2026): só conta o que muda o sistema. Teste, documentação, scripts
de apoio e textos de ajuda das telas não sobem a versão.
"""

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "versao.py"
_spec = importlib.util.spec_from_file_location("versao", _SCRIPT)
versao = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(versao)


@pytest.mark.parametrize(
    "caminho, lado",
    [
        ("backend/main.py", "back"),
        ("backend/services/processador.py", "back"),
        ("backend/alembic/versions/2026092701_x.py", "back"),
        ("backend/requirements.txt", "back"),
        ("frontend/src/components/Footer.jsx", "front"),
        ("frontend/vite.config.js", "front"),
        ("frontend/package.json", "front"),
        ("backend/tests/test_cpf.py", None),
        ("backend/scripts/analisar_payloads_twilio.py", None),
        ("backend/logs/payloads_twilio.jsonl", None),
        ("backend/README.md", None),
        ("frontend/src/ajuda/chat.md", None),
        ("frontend/src/ajuda/_fontes.json", None),
        ("backend/VERSAO", None),
        ("frontend/VERSAO", None),
        ("docs/comandos_uteis.md", None),
        ("scripts/versao.py", None),
        ("testador_conversas/cli.py", None),
    ],
)
def test_lado_do_arquivo(caminho, lado):
    assert versao.lado_do_arquivo(caminho) == lado


def test_mudanca_so_num_lado_nao_toca_o_outro():
    assert versao.lados_alterados(["backend/main.py", "docs/x.md"]) == {"back"}
    assert versao.lados_alterados(["frontend/src/App.jsx"]) == {"front"}
    assert versao.lados_alterados(["backend/main.py", "frontend/src/App.jsx"]) == {"back", "front"}


def test_formato_da_versao():
    assert versao.FORMATO.match(versao.versao_agora())
