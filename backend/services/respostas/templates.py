"""
Formatação de placeholders em mensagens.

Regras de negócio aplicadas nos textos do catálogo (catalogo.py):
- NUNCA prometer prazo de entrega
- Sempre orientar validação de compatibilidade
- Escalar para humano quando cliente pedir
"""


def formatar(template: str, **kwargs) -> str:
    """
    Formata um template com as variáveis fornecidas.
    Kwargs ausentes são substituídos por strings vazias (seguro).
    """

    class _SafeDict(dict):
        def __missing__(self, key):
            return ""

    return template.format_map(_SafeDict(**{k: str(v) for k, v in kwargs.items() if v is not None}))
