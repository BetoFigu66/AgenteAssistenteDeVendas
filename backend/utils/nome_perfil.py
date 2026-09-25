"""
Validação do nome de perfil do WhatsApp (`ProfileName` da Twilio).

A Twilio manda em todo `/webhook` o nome que o cliente configurou no próprio WhatsApp.
É um campo livre: pode vir um nome de verdade ("Ana Souza"), um apelido, só emoji, só
pontuação ("~~~") ou nada. Antes de usar esse valor para chamar o cliente pelo nome, ele
passa por aqui, para nunca gerar coisas como "Olá, ~~~, tudo bem?".

**Regra PROVISÓRIA.** Por ora só existe o critério de tamanho mínimo (ver
`MINIMO_LETRAS_NOME_PERFIL`). A regra definitiva ainda será definida (ex.: lista de
palavras que não são nome, "Empresa X", "Loja", números, apelidos de uma letra repetida)
e entra em `_passa_regra_nome_perfil`, sem mudar a assinatura de
`nome_perfil_aproveitavel`, que é o que o resto do sistema chama.
"""

from __future__ import annotations

import unicodedata
from typing import Optional

MINIMO_LETRAS_NOME_PERFIL = 3
"""Quantidade mínima de caracteres alfabéticos (letras acentuadas contam, ver
`str.isalpha`). Emoji, dígitos, pontuação e espaços não contam."""

TAMANHO_MAXIMO_NOME_PERFIL = 200
"""Espelha `Contato.nome` (`String(200)`): um valor maior não caberia na coluna. O
WhatsApp limita o nome de perfil bem abaixo disso, então na prática é só uma trava."""


def _passa_regra_nome_perfil(nome: str) -> bool:
    """Regra provisória: pelo menos `MINIMO_LETRAS_NOME_PERFIL` letras.

    `nome` já chega normalizado (NFC, sem espaços sobrando). É aqui que a regra
    definitiva deve entrar.
    """
    letras = sum(1 for c in nome if c.isalpha())
    return letras >= MINIMO_LETRAS_NOME_PERFIL


def nome_perfil_aproveitavel(nome_perfil: Optional[str]) -> Optional[str]:
    """Devolve o nome de perfil pronto para uso, ou `None` se não servir como nome.

    Normaliza antes de validar: Unicode NFC (um "é" decomposto em "e" + acento
    combinante vira um caractere só) e espaços colapsados/aparados. O valor devolvido é
    esse texto normalizado, sem outras alterações (um emoji junto do nome, como em
    "Ana 😊", é mantido; quem decide se isso fica ou sai é a regra definitiva).
    """
    if not nome_perfil:
        return None
    nome = " ".join(unicodedata.normalize("NFC", nome_perfil).split())
    if not nome or len(nome) > TAMANHO_MAXIMO_NOME_PERFIL:
        return None
    if not _passa_regra_nome_perfil(nome):
        return None
    return nome
