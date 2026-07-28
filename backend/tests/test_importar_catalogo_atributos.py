"""Testes de importação de catálogo com atributos adicionais do modelo."""

from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
from database import Database
from models import Modelo
from scripts.importar_catalogo_csv import EstatisticasImportacao, carregar_planilha, importar
from sqlalchemy.orm import Session


@pytest.fixture
def csv_temp_com_atributos() -> Path:
    """Planilha mínima com modelos que disparam atributos de tecnologia de leitura."""
    conteudo = (
        "id_linha;produto;modelo;Categoria;Marca;Aplicação;unidade;codigo\n"
        "1;Catraca;Catraca Biométrica X1;Controle de Acesso;Topdata;Condomínios;UN;CAT-X1\n"
        "2;Relógio de Ponto;Relógio de Ponto Cartão Proximidade;Controle de Ponto;Topdata;Escritórios;UN;REP-CARTAO\n"
        "3;Leitor Facial;Leitor Facial Hikvision;Controle de Acesso;Hikvision;Escritórios;UN;FACE-01\n"
    )
    with NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as tmp:
        tmp.write(conteudo)
        return Path(tmp.name)


def _limpar_modelos(session: Session, descricoes: set[str]) -> None:
    for modelo in session.query(Modelo).filter(Modelo.descricao.in_(descricoes)).all():
        session.delete(modelo)
    session.commit()


def test_importador_extrai_atributos_tecnologia_leitura(csv_temp_com_atributos: Path) -> None:
    db = Database()
    descricoes = {
        "Catraca Biométrica X1",
        "Relógio de Ponto Cartão Proximidade",
        "Leitor Facial Hikvision",
    }
    with db.get_session() as session:
        _limpar_modelos(session, descricoes)

    with db.get_session() as session:
        linhas, _stats = carregar_planilha(csv_temp_com_atributos)
        importar(session, linhas, EstatisticasImportacao())  # type: ignore
        session.commit()

        modelos = {m.descricao: m for m in session.query(Modelo).filter(Modelo.descricao.in_(descricoes)).all()}

        catraca = modelos["Catraca Biométrica X1"]
        relogio = modelos["Relógio de Ponto Cartão Proximidade"]
        leitor = modelos["Leitor Facial Hikvision"]

        def valores(modelo: Modelo) -> set[tuple[str, str]]:
            return {(a.chave, a.valor) for a in modelo.atributos if a.ativo}

        assert ("tecnologia_leitura", "biometria") in valores(catraca)
        assert ("tecnologia_leitura", "cartao") in valores(relogio)
        assert ("tecnologia_leitura", "facial") in valores(leitor)

    csv_temp_com_atributos.unlink()


def test_importador_reaproveira_atributos_inativos(csv_temp_com_atributos: Path) -> None:
    db = Database()
    descricoes = {"Catraca Biométrica X1"}
    with db.get_session() as session:
        _limpar_modelos(session, descricoes)

    # Primeira importação.
    with db.get_session() as session:
        linhas, _ = carregar_planilha(csv_temp_com_atributos)
        importar(session, linhas, EstatisticasImportacao())  # type: ignore
        session.commit()

    # Simula remoção do atributo na planilha alterando o modelo.
    conteudo_novo = (
        "id_linha;produto;modelo;Categoria;Marca;Aplicação;unidade;codigo\n"
        "1;Catraca;Catraca Biométrica X1;Controle de Acesso;Topdata;Condomínios;UN;CAT-X1\n"
    )
    with NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as tmp:
        tmp.write(conteudo_novo)
        caminho_novo = Path(tmp.name)

    # Reimporta: como a linha continua igual, o atributo deve continuar ativo.
    with db.get_session() as session:
        linhas, _ = carregar_planilha(caminho_novo)
        importar(session, linhas, EstatisticasImportacao())  # type: ignore
        session.commit()

        modelo = session.query(Modelo).filter_by(descricao="Catraca Biométrica X1").one()
        assert any(a.chave == "tecnologia_leitura" and a.valor == "biometria" and a.ativo for a in modelo.atributos)

    caminho_novo.unlink()
