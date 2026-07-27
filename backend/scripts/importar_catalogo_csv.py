"""Importa o catálogo de produtos e modelos de uma planilha CSV."""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
RAIZ_PROJETO = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config import settings  # noqa: E402
from models import AtributoAdicionalModelo, Categoria, Modelo, Produto  # noqa: E402
from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import Session, selectinload  # noqa: E402

ENTRADA_PADRAO = RAIZ_PROJETO / "artefatos" / "implementador" / "planilha_catalogo_modelos_v2.csv"
MARCAS_PERMITIDAS = {"Topdata", "Control-ID", "Intelbras", "Hikvision", "PPA"}
APLICACOES_PERMITIDAS = {
    "Pedágio",
    "Pequenas e médias empresas",
    "Condomínios",
    "Residências",
    "Academias",
    "Escritórios",
    "Bancos",
    "Rodoviárias",
    "Grandes Empresas",
    "Não se aplica",
}
ALIASES_CATEGORIAS = {"Roteador": "Roteadores"}
CAMPOS_OBRIGATORIOS = {"produto", "modelo", "Categoria", "Marca", "Aplicação", "unidade"}

# Palavras na coluna `modelo` que disparam atributos genéricos no catálogo.
# Chave do atributo deve coincidir com a chave usada em AtendimentoInfo pelo
# classificador (ex.: tipo_leitor_mencionado -> tecnologia_leitura).
_ATRIBUTOS_POR_PALAVRA: dict[tuple[str, ...], tuple[str, str]] = {
    ("biométrico", "biometrico", "biometria", "bio"): ("tecnologia_leitura", "biometria"),
    ("facial", "face", "reconhecimento facial"): ("tecnologia_leitura", "facial"),
    ("cartão", "cartao", "proximidade", "prox"): ("tecnologia_leitura", "cartao"),
    ("cartográfico", "cartografico", "cartografia"): ("tecnologia_leitura", "cartografico"),
    ("barras", "codigo de barras", "código de barras"): ("tecnologia_leitura", "barras"),
    ("qr code", "qrcode", "qr-code"): ("tecnologia_leitura", "qr_code"),
}


@dataclass(frozen=True)
class LinhaCatalogo:
    """Representa um modelo validado da planilha."""

    numero_linha: int
    id_linha: int | None
    produto: str
    modelo: str
    categorias: tuple[str, ...]
    marca: str
    aplicacao: str
    codigo: str | None
    unidade: str
    atributos: frozenset[tuple[str, str]] = field(default_factory=frozenset)


@dataclass
class EstatisticasImportacao:
    """Agrupa os contadores da importação."""

    linhas_lidas: int = 0
    duplicados_entrada: int = 0
    produtos_novos: int = 0
    produtos_atualizados: int = 0
    modelos_novos: int = 0
    modelos_atualizados: int = 0
    categorias_novas: int = 0
    categorias_atualizadas: int = 0
    associacoes_finais: int = 0


def normalizar_chave(valor: str) -> str:
    """Normaliza espaços e caixa para comparar chaves naturais."""
    return " ".join(valor.split()).casefold()


def texto_limpo(valor: str | None) -> str:
    """Remove espaços externos e normaliza campos ausentes."""
    return (valor or "").strip()


def _extrair_atributos(descricao: str) -> frozenset[tuple[str, str]]:
    """Mapeia palavras-chave da descrição do modelo em atributos genéricos."""
    texto = normalizar_chave(descricao)
    encontrados: set[tuple[str, str]] = set()
    for palavras, (chave, valor) in _ATRIBUTOS_POR_PALAVRA.items():
        if any(palavra in texto for palavra in palavras):
            encontrados.add((chave, valor))
    return frozenset(encontrados)


def carregar_planilha(caminho: Path) -> tuple[list[LinhaCatalogo], EstatisticasImportacao]:
    """Carrega, valida e deduplica os modelos da planilha."""
    stats = EstatisticasImportacao()
    modelos: dict[str, LinhaCatalogo] = {}
    ids_informados: dict[int, int] = {}

    with caminho.open("r", encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo, delimiter=";")
        campos_ausentes = CAMPOS_OBRIGATORIOS - set(leitor.fieldnames or [])
        if campos_ausentes:
            raise ValueError(f"Colunas obrigatórias ausentes: {', '.join(sorted(campos_ausentes))}")

        for numero_linha, registro in enumerate(leitor, start=2):
            stats.linhas_lidas += 1
            id_texto = texto_limpo(registro.get("id_linha"))
            if id_texto and not id_texto.isdigit():
                raise ValueError(f"Linha {numero_linha}: id_linha inválido: {id_texto!r}")
            id_linha = int(id_texto) if id_texto else None
            if id_linha is not None and id_linha in ids_informados:
                raise ValueError(
                    f"Linhas {ids_informados[id_linha]} e {numero_linha}: id_linha {id_linha} duplicado"
                )
            if id_linha is not None:
                ids_informados[id_linha] = numero_linha

            produto = texto_limpo(registro.get("produto"))
            modelo = texto_limpo(registro.get("modelo"))
            marca = texto_limpo(registro.get("Marca"))
            aplicacao = texto_limpo(registro.get("Aplicação"))
            unidade = texto_limpo(registro.get("unidade"))
            codigo = texto_limpo(registro.get("codigo")) or None
            categorias = tuple(
                dict.fromkeys(
                    ALIASES_CATEGORIAS.get(item.strip(), item.strip())
                    for item in texto_limpo(registro.get("Categoria")).split(",")
                    if item.strip()
                )
            )

            if not produto or not modelo or not categorias or not marca or not aplicacao or not unidade:
                raise ValueError(f"Linha {numero_linha}: há campos obrigatórios vazios")

            atributos = _extrair_atributos(modelo)
            if marca not in MARCAS_PERMITIDAS:
                raise ValueError(f"Linha {numero_linha}: marca não permitida: {marca!r}")
            if aplicacao not in APLICACOES_PERMITIDAS:
                raise ValueError(f"Linha {numero_linha}: aplicação não permitida: {aplicacao!r}")
            if len(produto) > 100 or len(modelo) > 300 or len(marca) > 100 or len(aplicacao) > 300:
                raise ValueError(f"Linha {numero_linha}: valor excede o limite do banco")
            if codigo and len(codigo) > 50:
                raise ValueError(f"Linha {numero_linha}: código excede 50 caracteres")
            if len(unidade) > 20 or any(len(categoria) > 100 for categoria in categorias):
                raise ValueError(f"Linha {numero_linha}: unidade ou categoria excede o limite do banco")

            linha = LinhaCatalogo(
                numero_linha=numero_linha,
                id_linha=id_linha,
                produto=produto,
                modelo=modelo,
                categorias=categorias,
                marca=marca,
                aplicacao=aplicacao,
                codigo=codigo,
                unidade=unidade,
                atributos=atributos,
            )
            chave = normalizar_chave(modelo)
            anterior = modelos.get(chave)
            if anterior is not None:
                comparavel_anterior = (
                    anterior.produto,
                    anterior.modelo,
                    anterior.categorias,
                    anterior.marca,
                    anterior.aplicacao,
                    anterior.codigo,
                    anterior.unidade,
                    anterior.atributos,
                )
                comparavel_atual = (
                    linha.produto,
                    linha.modelo,
                    linha.categorias,
                    linha.marca,
                    linha.aplicacao,
                    linha.codigo,
                    linha.unidade,
                    linha.atributos,
                )
                if comparavel_anterior != comparavel_atual:
                    raise ValueError(
                        f"Linhas {anterior.numero_linha} e {numero_linha}: modelo duplicado com dados divergentes"
                    )
                stats.duplicados_entrada += 1
                continue
            modelos[chave] = linha

    if not modelos:
        raise ValueError("A planilha não contém modelos")
    return list(modelos.values()), stats


def indexar_unicos(registros: list[Produto] | list[Categoria], entidade: str) -> dict[str, Produto | Categoria]:
    """Indexa descrições e rejeita duplicidades semânticas existentes."""
    indice: dict[str, Produto | Categoria] = {}
    for registro in registros:
        chave = normalizar_chave(registro.descricao)
        if chave in indice:
            raise ValueError(f"Banco contém {entidade} duplicado por descrição: {registro.descricao!r}")
        indice[chave] = registro
    return indice


def _indexar_atributos_existentes(modelos: list[Modelo]) -> dict[int, dict[tuple[str, str], AtributoAdicionalModelo]]:
    """Indexa atributos ativos por modelo_id -> (chave, valor)."""
    indice: dict[int, dict[tuple[str, str], AtributoAdicionalModelo]] = {}
    for modelo in modelos:
        for atributo in modelo.atributos:
            if not atributo.ativo:
                continue
            indice.setdefault(modelo.id, {})[(atributo.chave, atributo.valor)] = atributo
    return indice


def importar(session: Session, linhas: list[LinhaCatalogo], stats: EstatisticasImportacao) -> None:
    """Aplica a planilha à sessão SQLAlchemy atual."""
    produtos = indexar_unicos(list(session.scalars(select(Produto))), "produto")
    categorias = indexar_unicos(list(session.scalars(select(Categoria))), "categoria")
    modelos_existentes = list(
        session.scalars(select(Modelo).options(selectinload(Modelo.categorias), selectinload(Modelo.atributos)))
    )
    modelos_por_descricao: dict[str, Modelo] = {}
    for modelo in modelos_existentes:
        chave = normalizar_chave(modelo.descricao)
        if chave in modelos_por_descricao:
            raise ValueError(f"Banco contém modelo duplicado por descrição: {modelo.descricao!r}")
        modelos_por_descricao[chave] = modelo
    atributos_por_modelo = _indexar_atributos_existentes(modelos_existentes)

    for linha in linhas:
        chave_produto = normalizar_chave(linha.produto)
        produto = produtos.get(chave_produto)
        if produto is None:
            produto = Produto(descricao=linha.produto, ativo=True)
            session.add(produto)
            produtos[chave_produto] = produto
            stats.produtos_novos += 1
        elif not produto.ativo or produto.descricao != linha.produto:
            produto.descricao = linha.produto
            produto.ativo = True
            stats.produtos_atualizados += 1

        categorias_modelo: list[Categoria] = []
        for descricao_categoria in linha.categorias:
            chave_categoria = normalizar_chave(descricao_categoria)
            categoria = categorias.get(chave_categoria)
            if categoria is None:
                categoria = Categoria(descricao=descricao_categoria, ativo=True)
                session.add(categoria)
                categorias[chave_categoria] = categoria
                stats.categorias_novas += 1
            elif not categoria.ativo or categoria.descricao != descricao_categoria:
                categoria.descricao = descricao_categoria
                categoria.ativo = True
                stats.categorias_atualizadas += 1
            categorias_modelo.append(categoria)

        chave_modelo = normalizar_chave(linha.modelo)
        modelo = modelos_por_descricao.get(chave_modelo)
        if modelo is None:
            modelo = Modelo(
                produto=produto,
                descricao=linha.modelo,
                codigo=linha.codigo,
                unidade=linha.unidade,
                marca=linha.marca,
                aplicacao=linha.aplicacao,
                ativo=True,
            )
            session.add(modelo)
            modelos_por_descricao[chave_modelo] = modelo
            stats.modelos_novos += 1
        else:
            chave_antiga = normalizar_chave(modelo.descricao)
            modelo.produto = produto
            modelo.descricao = linha.modelo
            if linha.codigo is not None:
                modelo.codigo = linha.codigo
            modelo.unidade = linha.unidade
            modelo.marca = linha.marca
            modelo.aplicacao = linha.aplicacao
            modelo.ativo = True
            if chave_antiga != chave_modelo:
                modelos_por_descricao.pop(chave_antiga, None)
                modelos_por_descricao[chave_modelo] = modelo
            stats.modelos_atualizados += 1
        modelo.categorias = categorias_modelo
        stats.associacoes_finais += len(categorias_modelo)

        # Sincroniza atributos adicionais do modelo.
        atributos_existentes = atributos_por_modelo.get(modelo.id, {})
        atributos_desejados: set[tuple[str, str]] = set(linha.atributos)
        for (chave, valor), atributo in atributos_existentes.items():
            if (chave, valor) not in atributos_desejados:
                atributo.ativo = False
        for chave, valor in atributos_desejados:
            if (chave, valor) not in atributos_existentes:
                novo = AtributoAdicionalModelo(modelo=modelo, chave=chave, valor=valor, ativo=True)
                session.add(novo)


def exibir_resumo(stats: EstatisticasImportacao, aplicar: bool) -> None:
    """Exibe os contadores finais da carga."""
    modo = "APLICADO" if aplicar else "SIMULAÇÃO"
    print(f"[catalogo] modo={modo}")
    print(
        f"[catalogo] linhas={stats.linhas_lidas} duplicados_entrada={stats.duplicados_entrada} "
        f"modelos_unicos={stats.linhas_lidas - stats.duplicados_entrada}"
    )
    print(
        f"[catalogo] produtos_novos={stats.produtos_novos} produtos_atualizados={stats.produtos_atualizados} "
        f"categorias_novas={stats.categorias_novas} categorias_atualizadas={stats.categorias_atualizadas}"
    )
    print(
        f"[catalogo] modelos_novos={stats.modelos_novos} modelos_atualizados={stats.modelos_atualizados} "
        f"associacoes_finais={stats.associacoes_finais}"
    )


def main() -> None:
    """Executa a importação transacional do catálogo."""
    parser = argparse.ArgumentParser(description="Importa produtos, modelos e categorias de um CSV")
    parser.add_argument("--arquivo", type=Path, default=ENTRADA_PADRAO)
    parser.add_argument("--aplicar", action="store_true", help="Confirma a gravação; sem esta opção faz rollback")
    args = parser.parse_args()

    linhas, stats = carregar_planilha(args.arquivo.resolve())
    engine = create_engine(settings.DATABASE_URL, future=True)
    with Session(engine) as session:
        try:
            importar(session, linhas, stats)
            if args.aplicar:
                session.commit()
            else:
                session.rollback()
        except Exception:
            session.rollback()
            raise
    exibir_resumo(stats, args.aplicar)


if __name__ == "__main__":
    main()
