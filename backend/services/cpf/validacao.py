"""
Validação algorítmica de CPF (REQ-015.2).

Não há API pública gratuita da Receita Federal para consulta cadastral de CPF;
a validação é local (formato + dígitos verificadores).
"""

import re
from datetime import date, datetime
from typing import Optional

_REGEX_CPF_FORMATADO = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_REGEX_CPF_ESPACOS = re.compile(r"\b\d{3}\s\d{3}\s\d{3}\s\d{2}\b")
_REGEX_CPF_DIGITOS = re.compile(r"\b\d{11}\b")
_REGEX_DATA_NASC = re.compile(
    r"(?:nasc(?:imento|\.|ido)?|data\s+de\s+nascimento|nasc\.?\s+em)\s*[:\-]?\s*"
    r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})",
    re.IGNORECASE,
)
_REGEX_DATA_ISOLADA = re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b")

_CPF_SEQUENCIAS_INVALIDAS = {str(i) * 11 for i in range(10)}


def normalizar_cpf(cpf: str) -> str:
    """Remove formatação, mantendo apenas dígitos."""
    return re.sub(r"\D", "", cpf or "")


def validar_cpf(cpf: str) -> bool:
    """
    Valida CPF: 11 dígitos, não sequência trivial, dígitos verificadores corretos.
    """
    cpf_limpo = normalizar_cpf(cpf)
    if len(cpf_limpo) != 11:
        return False
    if cpf_limpo in _CPF_SEQUENCIAS_INVALIDAS:
        return False

    def calcular_digito(cpf_parcial: str, peso_inicial: int) -> int:
        soma = sum(int(d) * (peso_inicial - i) for i, d in enumerate(cpf_parcial))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    digito1 = calcular_digito(cpf_limpo[:9], 10)
    if digito1 != int(cpf_limpo[9]):
        return False
    digito2 = calcular_digito(cpf_limpo[:10], 11)
    if digito2 != int(cpf_limpo[10]):
        return False
    return True


def formatar_cpf(cpf: str) -> str:
    """Formata CPF com máscara XXX.XXX.XXX-XX."""
    c = normalizar_cpf(cpf)
    if len(c) != 11:
        return cpf
    return f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}"


def mascarar_cpf(cpf: str) -> str:
    """Mascara CPF para logs/auditoria (REQ-015.13): ***.456.789-**."""
    c = normalizar_cpf(cpf)
    if len(c) != 11:
        return "***"
    return f"***.{c[3:6]}.{c[6:9]}-**"


def extrair_cpfs(texto: str) -> list[str]:
    """
    Extrai CPFs em formatos XXX.XXX.XXX-XX, XXXXXXXXXXX ou XXX XXX XXX XX.
    Filtra candidatos inválidos algoritmicamente.
    """
    if not texto:
        return []

    candidatos: list[str] = []
    for regex in (_REGEX_CPF_FORMATADO, _REGEX_CPF_ESPACOS, _REGEX_CPF_DIGITOS):
        for match in regex.findall(texto):
            valor = match if isinstance(match, str) else match[0]
            cpf_limpo = normalizar_cpf(valor)
            if len(cpf_limpo) == 11 and cpf_limpo not in candidatos:
                candidatos.append(cpf_limpo)

    return [c for c in candidatos if validar_cpf(c)]


def parse_data_nascimento(texto: str) -> Optional[date]:
    """
    Extrai data de nascimento de texto livre.

    Prioriza padrões com gatilho ('nascimento em DD/MM/AAAA');
    caso contrário, usa a primeira data válida encontrada.
    """
    if not texto:
        return None

    for match in _REGEX_DATA_NASC.finditer(texto):
        parsed = _parse_data_grupos(match.group(1), match.group(2), match.group(3))
        if parsed:
            return parsed

    for match in _REGEX_DATA_ISOLADA.finditer(texto):
        parsed = _parse_data_grupos(match.group(1), match.group(2), match.group(3))
        if parsed:
            return parsed

    return None


def _parse_data_grupos(dia: str, mes: str, ano: str) -> Optional[date]:
    try:
        dt = date(int(ano), int(mes), int(dia))
    except ValueError:
        return None
    if dt > date.today():
        return None
    if dt.year < 1900:
        return None
    return dt
