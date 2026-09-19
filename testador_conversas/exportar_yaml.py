"""Exporta cenário + turnos + respostas aceitas pra YAML — histórico/backup
versionado no git. O banco (schema `teste_conversas`) continua sendo a fonte da
verdade; isto é só uma fotografia legível, pra ter `git diff`/revisão de PR
sobre as mudanças de roteiro e do que passou a ser aceito.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from models import Cenario

DIR_EXPORTACAO = Path(__file__).parent / "cenarios_exportados"


def exportar_cenario(cenario: Cenario) -> Path:
    DIR_EXPORTACAO.mkdir(exist_ok=True)
    dados = {
        "nome": cenario.nome,
        "descricao": cenario.descricao,
        "ativo": cenario.ativo,
        "turnos": [
            {
                "ordem": turno.ordem,
                "mensagem_enviada": turno.mensagem_enviada,
                "observacoes": turno.observacoes,
                "respostas_aceitas": [
                    {"texto": r.texto, "ativo": r.ativo, "criado_por": r.criado_por}
                    for r in sorted(turno.respostas_aceitas, key=lambda r: r.id)
                ],
            }
            for turno in sorted(cenario.turnos, key=lambda t: t.ordem)
        ],
    }
    caminho = DIR_EXPORTACAO / f"{cenario.nome}.yaml"
    with caminho.open("w", encoding="utf-8") as f:
        yaml.safe_dump(dados, f, allow_unicode=True, sort_keys=False)
    return caminho
