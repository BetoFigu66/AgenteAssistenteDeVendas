"""O telefone tem uma forma canônica só: `+55DDD9NNNNNNNN`.

Por que isso tem teste próprio: `Mensagem.telefone` é a chave por onde o histórico de uma
conversa é montado. Enquanto a normalização devolvia o que recebia, o mesmo cliente virava
chaves diferentes conforme a porta de entrada, e em 24/09/2026 isso fez o painel não mostrar
**nenhuma** mensagem vinda do WhatsApp: a tela procurava pelo telefone do contato, gravado
noutra forma. O banco tinha 3 formatos convivendo.

A regra interpreta pelo tamanho, e não completa prefixo à esquerda. A diferença importa:
completar à esquerda empurra os dígitos originais para a direita, e em `1999854265` o `19`
que era DDD viraria parte do número, com o DDD virando `11`.
"""

import pytest
from services.identificador import normalizar_telefone

CANONICO = "+5519991931173"


@pytest.mark.parametrize(
    "entrada",
    [
        "whatsapp:+5519991931173",  # como a Twilio entrega
        "whatsapp:5519991931173",  # sem o +
        "+5519991931173",  # já canônico
        "5519991931173",  # DDI sem +
        "19991931173",  # DDD + celular, como se digita no painel
        "(19) 99193-1173",  # com máscara
        "19 99193-1173",
        "991931173",  # sem DDD, assume 19
    ],
)
def test_formas_do_mesmo_numero_convergem(entrada):
    """Todas as portas de entrada precisam produzir a mesma chave, senão o histórico parte."""
    assert normalizar_telefone(entrada) == CANONICO


def test_numero_de_oito_digitos_ganha_o_nove_do_celular():
    """Número antigo (DDD + 8) recebe o 9, preservando o DDD original.

    É o caso que a regra de completar prefixo errava: ela empurrava o `19` para dentro do
    número e trocava o DDD por `11`.
    """
    assert normalizar_telefone("1999854265") == "+5519999854265"
    assert normalizar_telefone("551999854265") == "+5519999854265"


def test_ddd_de_outra_regiao_e_preservado():
    """A regra não pode assumir DDD 19 para quem já informou o seu."""
    assert normalizar_telefone("11987654321") == "+5511987654321"
    assert normalizar_telefone("whatsapp:+5511987654321") == "+5511987654321"


@pytest.mark.parametrize("entrada", ["", None])
def test_vazio_devolve_vazio(entrada):
    assert normalizar_telefone(entrada) == ""


def test_numero_irreconhecivel_nao_e_deformado():
    """Melhor um registro fora do padrão, visível, do que um telefone plausível e errado.

    Estes são os que apareceram no banco em 2026-09-24, digitados a esmo em testes. A regra
    de completar prefixo transformava o primeiro em `+1895489265546`, um número dos EUA.
    """
    assert normalizar_telefone("1895489265546") == "1895489265546"
    assert normalizar_telefone("119632587455") == "119632587455"


def test_normalizacao_e_idempotente():
    """Aplicar duas vezes não pode mudar o resultado: a função roda em vários pontos do
    pipeline, e um valor já canônico passa por ela de novo."""
    uma_vez = normalizar_telefone("19991931173")
    assert normalizar_telefone(uma_vez) == uma_vez
