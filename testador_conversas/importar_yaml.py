"""Importa cenário + turnos + respostas aceitas de YAML para o banco: caminho
inverso de `exportar_yaml.py`.

O banco (schema `teste_conversas`) continua sendo a fonte da verdade; o YAML é a
fotografia versionada no git. Sem este módulo a fotografia era de mão única:
exportava e nunca restaurava, então um cenário escrito em YAML (ou um banco
recriado do zero) não chegava a rodar.

Regras de idempotência:

- `atualizar=False` (padrão): cenário já existente é deixado como está. Rodar a
  importação do diretório inteiro várias vezes é seguro.
- `atualizar=True`: o cenário existente é sincronizado com o YAML.

Sobre "substituir os turnos": `Cenario.turnos` tem `delete-orphan`, então
esvaziar a coleção apagaria os turnos de fato. Mesmo assim a atualização aqui
casa os turnos por `ordem` e altera no lugar, em vez de apagar e recriar, porque
`resultados_turno.turno_id` aponta para `turnos`: apagar um turno já executado
esbarraria na FK e derrubaria a importação. Só turno que sumiu do YAML é
removido (e aí a FK pode reclamar mesmo, o que é o aviso correto).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from exportar_yaml import DIR_EXPORTACAO
from models import Cenario, RespostaAceita, Turno
from sqlalchemy.orm import Session

CRIADO_POR_PADRAO = "importado_yaml"


class YamlInvalidoError(ValueError):
    """YAML fora do formato que `exportar_cenario` produz."""


@dataclass
class ResultadoImportacao:
    """Resultado por arquivo. `acao` é o que interessa para o log do CLI."""

    cenario: Cenario
    acao: str  # "criado" | "atualizado" | "pulado"
    caminho: Path


def listar_yamls(diretorio: Path = DIR_EXPORTACAO) -> list[Path]:
    """Todos os `*.yaml` do diretório, em ordem alfabética."""
    return sorted(Path(diretorio).glob("*.yaml"))


def _ler_dados(caminho: Path) -> dict[str, Any]:
    with Path(caminho).open("r", encoding="utf-8") as f:
        dados = yaml.safe_load(f)
    if not isinstance(dados, dict):
        raise YamlInvalidoError(f"{caminho}: o YAML deve ter um mapeamento no topo.")
    nome = dados.get("nome")
    if not isinstance(nome, str) or not nome.strip():
        raise YamlInvalidoError(f"{caminho}: campo 'nome' ausente ou vazio.")
    turnos = dados.get("turnos")
    if not isinstance(turnos, list) or not turnos:
        raise YamlInvalidoError(f"{caminho}: campo 'turnos' ausente ou vazio.")
    ordens = []
    for i, turno in enumerate(turnos, start=1):
        if not isinstance(turno, dict):
            raise YamlInvalidoError(f"{caminho}: turno #{i} não é um mapeamento.")
        ordem = turno.get("ordem")
        if not isinstance(ordem, int):
            raise YamlInvalidoError(f"{caminho}: turno #{i} sem 'ordem' inteira.")
        if turno.get("mensagem_enviada") is None:
            raise YamlInvalidoError(f"{caminho}: turno ordem={ordem} sem 'mensagem_enviada'.")
        ordens.append(ordem)
    if len(set(ordens)) != len(ordens):
        raise YamlInvalidoError(f"{caminho}: há 'ordem' repetida entre os turnos.")
    return dados


def _respostas_do_yaml(turno_yaml: dict[str, Any]) -> list[dict[str, Any]]:
    brutas = turno_yaml.get("respostas_aceitas") or []
    if not isinstance(brutas, list):
        raise YamlInvalidoError("'respostas_aceitas' deve ser uma lista.")
    respostas = []
    for r in brutas:
        if not isinstance(r, dict) or r.get("texto") is None:
            raise YamlInvalidoError("resposta aceita sem campo 'texto'.")
        respostas.append(
            {
                "texto": r["texto"],
                "ativo": bool(r.get("ativo", True)),
                "criado_por": r.get("criado_por") or CRIADO_POR_PADRAO,
            }
        )
    return respostas


def _sincronizar_turno(turno: Turno, turno_yaml: dict[str, Any]) -> None:
    turno.mensagem_enviada = turno_yaml["mensagem_enviada"]
    turno.observacoes = turno_yaml.get("observacoes")

    desejadas = _respostas_do_yaml(turno_yaml)
    por_texto = {r.texto: r for r in turno.respostas_aceitas}
    textos_desejados = {r["texto"] for r in desejadas}

    for dados in desejadas:
        existente = por_texto.get(dados["texto"])
        if existente is None:
            turno.respostas_aceitas.append(RespostaAceita(**dados))
        else:
            existente.ativo = dados["ativo"]

    # Nada aponta para `respostas_aceitas`, então remover o que saiu do YAML é seguro.
    for resposta in list(turno.respostas_aceitas):
        if resposta.texto not in textos_desejados:
            turno.respostas_aceitas.remove(resposta)


def importar_cenario_detalhado(
    db: Session, caminho: Path | str, *, atualizar: bool = False
) -> ResultadoImportacao:
    """Importa um arquivo e diz o que aconteceu (criado/atualizado/pulado)."""
    caminho = Path(caminho)
    dados = _ler_dados(caminho)
    nome = dados["nome"]

    cenario = db.query(Cenario).filter_by(nome=nome).first()
    if cenario is not None and not atualizar:
        return ResultadoImportacao(cenario=cenario, acao="pulado", caminho=caminho)

    acao = "atualizado" if cenario is not None else "criado"
    if cenario is None:
        cenario = Cenario(nome=nome)
        db.add(cenario)

    cenario.descricao = dados.get("descricao")
    cenario.ativo = bool(dados.get("ativo", True))

    turnos_yaml = sorted(dados["turnos"], key=lambda t: t["ordem"])
    ordens_desejadas = {t["ordem"] for t in turnos_yaml}
    por_ordem = {t.ordem: t for t in cenario.turnos}

    for turno_yaml in turnos_yaml:
        turno = por_ordem.get(turno_yaml["ordem"])
        if turno is None:
            turno = Turno(ordem=turno_yaml["ordem"], mensagem_enviada="")
            cenario.turnos.append(turno)
        _sincronizar_turno(turno, turno_yaml)

    for turno in list(cenario.turnos):
        if turno.ordem not in ordens_desejadas:
            cenario.turnos.remove(turno)  # delete-orphan apaga de fato

    db.commit()
    return ResultadoImportacao(cenario=cenario, acao=acao, caminho=caminho)


def importar_cenario(db: Session, caminho: Path | str, *, atualizar: bool = False) -> Cenario:
    """Simétrico de `exportar_cenario`: lê um YAML e devolve o cenário no banco."""
    return importar_cenario_detalhado(db, caminho, atualizar=atualizar).cenario


def importar_diretorio(
    db: Session, diretorio: Path | str = DIR_EXPORTACAO, *, atualizar: bool = False
) -> list[Cenario]:
    """Importa todos os `*.yaml` do diretório, em ordem alfabética."""
    return [
        importar_cenario(db, caminho, atualizar=atualizar)
        for caminho in listar_yamls(Path(diretorio))
    ]
