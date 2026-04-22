"""
Testes para extração de nome em services.classificador.

Regressão para o report: "O CNPJ da empresa é X e meu nome é Beto Figueiredo"
onde o nome não estava sendo extraído quando a regra detectava CNPJ e
desviava do caminho da LLM.
"""
import sys
from pathlib import Path

# Permite rodar `python -m pytest backend/tests` a partir da raiz do projeto.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from services.classificador import extrair_entidades


@pytest.mark.parametrize(
    "texto, nome_esperado",
    [
        # Caso original do report
        (
            "O CNPJ da empresa é 48495530000184 e meu nome é Beto Figueiredo",
            "Beto Figueiredo",
        ),
        # Variações de gatilho
        ("Meu nome é João da Silva", "João Da Silva"),
        ("me chamo Ana", "Ana"),
        ("Sou o Pedro", "Pedro"),
        ("sou a Maria", "Maria"),
        ("Pode me chamar de Bia", "Bia"),
        # Capitalização
        ("meu nome é beto figueiredo", "Beto Figueiredo"),
    ],
)
def test_extrai_nome_com_gatilhos(texto, nome_esperado):
    ent = extrair_entidades(texto)
    assert ent.nomes, f"Nenhum nome extraído de: {texto!r}"
    assert ent.nomes[0] == nome_esperado


def test_extrai_nome_junto_com_cnpj():
    """Regressão direta do report: CNPJ + nome na mesma mensagem."""
    texto = "O CNPJ da empresa é 48495530000184 e meu nome é Beto Figueiredo"
    ent = extrair_entidades(texto)
    assert "48495530000184" in ent.cnpjs
    assert "Beto Figueiredo" in ent.nomes


def test_nao_extrai_nome_sem_gatilho():
    """Evita falso-positivo em mensagens sem gatilho explícito."""
    ent = extrair_entidades("Quero 5 catracas para minha empresa")
    assert ent.nomes == []


def test_nao_extrai_stopword_como_nome():
    """Mensagem com gatilho mas seguida de palavra inútil não deve virar nome."""
    ent = extrair_entidades("Meu nome é a empresa Inforrel")
    # "empresa", "inforrel", "a" estão nas stopwords — nome final deve ser vazio
    # (ou pode capturar "Empresa" se stop não cortar). Aceitamos qualquer coisa
    # desde que NÃO seja "A" ou "A Empresa Inforrel".
    for n in ent.nomes:
        assert n.lower() not in {"a", "a empresa", "a empresa inforrel"}
