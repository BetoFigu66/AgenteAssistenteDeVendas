"""
Agente QA Engineer - Responsável pela qualidade do projeto.

Responsabilidades:
1. Revisar documentação (coerência, completude, padrões)
2. Definir e revisar cobertura de testes
3. Validar fluxo de branches e PRs
4. Sugerir melhorias de processo
5. Checklist de qualidade antes de releases
"""

import ast
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional

from .base_agente import BaseAgente

try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        tomllib = None

# ----------------------------------------------------------------------
# Infra de checks: resultado padronizado + registry global.
# ----------------------------------------------------------------------

SEVERIDADES = ("error", "warning", "info")
ESCOPOS = ("sempre", "pre-commit", "pre-push", "release")


@dataclass
class CheckResult:
    """Resultado padronizado de um check de QA."""

    passou: bool
    severidade: str = "warning"  # sobrescreve a severidade default do Check
    findings: List[str] = field(default_factory=list)
    comandos_uteis: List[str] = field(default_factory=list)
    mensagem: str = ""
    dica_correcao: str = ""


@dataclass
class Check:
    """Metadados de um check registrado."""

    id: str
    titulo: str
    severidade: str
    escopos: List[str]
    funcao: Callable[[Path], CheckResult]


_REGISTRY: Dict[str, Check] = {}


def registrar_check(
    id: str,
    titulo: str,
    severidade: str = "warning",
    escopos: Optional[List[str]] = None,
):
    """
    Decorator para registrar um check no registry global.

    Args:
        id: Identificador unico do check (kebab-case).
        titulo: Titulo humano do check.
        severidade: "error" | "warning" | "info". Apenas `error` bloqueia commit.
        escopos: Onde o check deve rodar. Default: ["sempre"].
    """
    if severidade not in SEVERIDADES:
        raise ValueError(f"severidade invalida: {severidade}. Use uma de {SEVERIDADES}")
    escopos = escopos or ["sempre"]
    for e in escopos:
        if e not in ESCOPOS:
            raise ValueError(f"escopo invalido: {e}. Use um de {ESCOPOS}")

    def decorator(funcao: Callable[[Path], CheckResult]) -> Callable[[Path], CheckResult]:
        if id in _REGISTRY:
            raise ValueError(f"Check duplicado: {id}")
        _REGISTRY[id] = Check(id=id, titulo=titulo, severidade=severidade, escopos=escopos, funcao=funcao)
        return funcao

    return decorator


# Diretorios sempre ignorados pelas varreduras dos checks.
_DIRS_IGNORADOS = {
    ".git",
    ".idea",
    ".vscode",
    ".history",
    ".windsurf",
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
    "dist",
    "build",
    ".pytest_cache",
    "historico",
}


def _deve_ignorar(caminho: Path, raiz: Path) -> bool:
    try:
        rel = caminho.relative_to(raiz)
    except ValueError:
        return False
    return any(parte in _DIRS_IGNORADOS for parte in rel.parts)


def _iter_arquivos(raiz: Path, nome_exato: Optional[str] = None, sufixo: Optional[str] = None) -> Iterable[Path]:
    """
    Itera sobre arquivos do repositorio, tolerando erros de I/O do Windows
    (ex.: arquivos de lock do LibreOffice que disparam OSError em stat).

    Filtra por `nome_exato` OU `sufixo` (ex.: ".py"). Pula diretorios
    listados em `_DIRS_IGNORADOS`.
    """
    raiz_str = str(raiz)
    for dirpath, dirnames, filenames in os.walk(raiz_str, onerror=lambda e: None):
        # Poda dirs ignorados in-place para nao descer neles
        dirnames[:] = [d for d in dirnames if d not in _DIRS_IGNORADOS]
        for fname in filenames:
            if nome_exato is not None and fname != nome_exato:
                continue
            if sufixo is not None and not fname.endswith(sufixo):
                continue
            caminho = Path(dirpath) / fname
            try:
                # Testa acesso basico; pula se Windows recusar (ex.: lock file)
                if not caminho.is_file():
                    continue
            except OSError:
                continue
            yield caminho


# ----------------------------------------------------------------------
# Checks concretos
# ----------------------------------------------------------------------


@registrar_check(
    id="gitkeep-redundantes",
    titulo="Arquivos .gitkeep em diretorios nao-vazios",
    severidade="warning",
    escopos=["sempre", "pre-commit"],
)
def _check_gitkeep_redundantes(raiz: Path) -> CheckResult:
    """`.gitkeep` so faz sentido em diretorios vazios. Acusa os demais."""
    redundantes: List[str] = []
    comandos: List[str] = []
    for gitkeep in _iter_arquivos(raiz, nome_exato=".gitkeep"):
        try:
            irmaos = [p for p in gitkeep.parent.iterdir() if p.name != ".gitkeep"]
        except OSError:
            continue
        if irmaos:
            root = str(gitkeep.relative_to(raiz)).replace("\\", "/")
            redundantes.append(root)
            comandos.append(f"ls {root.replace('.gitkeep', '')}")
            comandos.append(f"rm {root}")
    return CheckResult(
        passou=not redundantes,
        findings=redundantes,
        comandos_uteis=comandos,
        mensagem=(
            f"{len(redundantes)} .gitkeep(s) redundante(s) encontrados" if redundantes
                else "Nenhum .gitkeep redundante."
        ),
        dica_correcao="Remova os arquivos .gitkeep listados (o diretorio ja tem conteudo).",
    )


@registrar_check(
    id="max-linhas-por-extensao",
    titulo="Arquivos excedendo o limite maximo de linhas por extensao",
    severidade="warning",
    escopos=["sempre", "pre-commit"],
)
def _check_max_linhas_por_extensao(raiz: Path) -> CheckResult:
    """
    Verifica se arquivos excedem o limite de linhas configurado no pyproject.toml.

    Configuracao esperada (exemplo):
        [tool.qa.max-lines-per-extension]
        py = 900
        yaml = 800
        txt = 1500
    """
    if tomllib is None:
        return CheckResult(
            passou=True,
            mensagem="tomllib/tomli nao disponivel; check ignorado.",
        )

    pyproject = raiz / "pyproject.toml"
    if not pyproject.exists():
        return CheckResult(
            passou=True,
            mensagem="pyproject.toml nao encontrado; check ignorado.",
        )

    try:
        with pyproject.open("rb") as f:
            config = tomllib.load(f)
    except Exception as exc:
        return CheckResult(
            passou=False,
            severidade="warning",
            mensagem=f"Erro ao ler pyproject.toml: {exc}",
            dica_correcao="Verifique sintaxe do pyproject.toml.",
        )

    limites = config.get("tool", {}).get("qa", {}).get("max-lines-per-extension", {})
    if not limites:
        return CheckResult(
            passou=True,
            mensagem="[tool.qa.max-lines-per-extension] nao configurado; check ignorado.",
        )

    excedentes: List[str] = []
    comandos: List[str] = []

    # Mapeia extensao (com ponto) -> limite
    limites_normalizado = {ext if ext.startswith(".") else f".{ext}": limite for ext, limite in limites.items()}

    for arquivo in _iter_arquivos(raiz):
        if _deve_ignorar(arquivo, raiz):
            continue
        ext = arquivo.suffix.lower()
        limite = limites_normalizado.get(ext)
        if limite is None:
            continue
        try:
            with arquivo.open("r", encoding="utf-8", errors="replace") as f:
                total_linhas = sum(1 for _ in f)
        except (OSError, UnicodeDecodeError):
            continue
        if total_linhas > limite:
            rel = str(arquivo.relative_to(raiz)).replace("\\", "/")
            excedentes.append(f"{rel} ({total_linhas} linhas, limite {limite})")
            comandos.append(f"wc -l {rel}")

    return CheckResult(
        passou=not excedentes,
        findings=excedentes,
        comandos_uteis=comandos,
        mensagem=(
            f"{len(excedentes)} arquivo(s) excede(m) o limite de linhas"
            if excedentes
            else "Nenhum arquivo excede o limite de linhas."
        ),
        dica_correcao="Quebre arquivos grandes em modulos menores ou ajuste o limite em pyproject.toml.",
    )


@registrar_check(
    id="imports-quebrados",
    titulo="Imports relativos apontando para modulos inexistentes",
    severidade="error",
    escopos=["sempre", "pre-commit"],
)
def _check_imports_quebrados(raiz: Path) -> CheckResult:
    """
    Parseia arquivos .py e checa `from .modulo import ...` onde `modulo.py`
    nem pacote `modulo/__init__.py` existem. Foca em imports RELATIVOS
    (level > 0) para evitar falsos positivos em libs instaladas.
    """
    quebrados: List[str] = []
    for py_file in _iter_arquivos(raiz, sufixo=".py"):
        try:
            fonte = py_file.read_text(encoding="utf-8")
            tree = ast.parse(fonte)
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.level == 0 or not node.module:
                continue
            base = py_file.parent
            for _ in range(node.level - 1):
                base = base.parent
            parts = node.module.split(".")
            alvo_modulo = base.joinpath(*parts).with_suffix(".py")
            alvo_pacote = base.joinpath(*parts, "__init__.py")
            if not alvo_modulo.exists() and not alvo_pacote.exists():
                rel = str(py_file.relative_to(raiz)).replace("\\", "/")
                quebrados.append(f"{rel}:{node.lineno} — from {'.' * node.level}{node.module} (nao existe)")
    return CheckResult(
        passou=not quebrados,
        findings=quebrados,
        mensagem=(
            f"{len(quebrados)} import(s) relativo(s) quebrado(s)" if quebrados else "Nenhum import relativo quebrado."
        ),
        dica_correcao="Corrija o nome do modulo ou remova o import se obsoleto.",
    )


# Regex para citacoes no formato `@<caminho absoluto>[:linhas]` em .md
# Ex: @c:/proj/file.py:12-20  ou  @/home/u/file.ts:5
_RE_CITACAO_MD = re.compile(r"@([A-Za-z]:[\\/][^\s`\n]+|/[^\s`\n]+)")


@registrar_check(
    id="referencias-orfas-em-docs",
    titulo="Citacoes @caminho em .md apontando para arquivos inexistentes",
    severidade="warning",
    escopos=["sempre", "pre-commit"],
)
def _check_referencias_orfas_em_docs(raiz: Path) -> CheckResult:
    """
    Procura citacoes no formato `@<path_absoluto>[:linhas]` em arquivos .md
    e acusa as que apontam para arquivos que nao existem mais.
    So analisa citacoes dentro do proprio repositorio (caminhos que
    comecam pela raiz do projeto); caminhos externos sao ignorados.
    """
    orfas: List[str] = []
    raiz_str = str(raiz.resolve()).replace("\\", "/").rstrip("/").lower()
    for md_file in _iter_arquivos(raiz, sufixo=".md"):
        try:
            texto = md_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for linha_num, linha in enumerate(texto.splitlines(), start=1):
            for match in _RE_CITACAO_MD.finditer(linha):
                caminho_bruto = match.group(1)
                # Remove sufixo :N ou :N-M (linha/range)
                caminho_sem_linhas = re.sub(r":\d+(-\d+)?$", "", caminho_bruto)
                caminho_norm = caminho_sem_linhas.replace("\\", "/").lower()
                # So checamos caminhos dentro do repo
                if not caminho_norm.startswith(raiz_str):
                    continue
                alvo = Path(caminho_sem_linhas)
                if not alvo.exists():
                    rel_md = str(md_file.relative_to(raiz)).replace("\\", "/")
                    orfas.append(f"{rel_md}:{linha_num} — {caminho_bruto}")
    return CheckResult(
        passou=not orfas,
        findings=orfas,
        mensagem=(f"{len(orfas)} citacao(oes) orfas em .md" if orfas else "Nenhuma citacao orfa."),
        dica_correcao="Atualize o caminho na citacao ou remova a referencia.",
    )


@registrar_check(
    id="pgvector-op-sem-return-type",
    titulo="Operador pgvector <=> sem return_type=Float() explícito",
    severidade="error",
    escopos=["sempre", "pre-commit"],
)
def _check_pgvector_op_sem_return_type(raiz: Path) -> CheckResult:
    """
    O operador `<=>` (distancia cosseno do pgvector) em SQLAlchemy herda o tipo
    da coluna esquerda. Quando a coluna e do tipo customizado `Vector`, o
    `result_processor` do Vector e aplicado ao float de distancia retornado,
    causando `AttributeError: 'float' object has no attribute 'strip'`.

    Toda chamada `.op('<=>') deve ter `return_type=Float()` explicito para que
    SQLAlchemy saiba que o resultado e um float, nao um vector.
    """
    problemas: List[str] = []
    backend = raiz / "backend"
    if not backend.is_dir():
        return CheckResult(
            passou=True,
            mensagem="Diretorio backend/ nao encontrado; check ignorado.",
        )
    for py_file in _iter_arquivos(backend, sufixo=".py"):
        try:
            texto = py_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for i, linha in enumerate(texto.splitlines(), 1):
            if '.op("<=>"' in linha and "return_type=" not in linha:
                rel = str(py_file.relative_to(raiz)).replace("\\", "/")
                problemas.append(f"{rel}:{i} — .op('<=>') sem return_type=Float()")
    return CheckResult(
        passou=not problemas,
        findings=problemas,
        mensagem=(
            f"{len(problemas)} chamada(s) .op('<=>') sem return_type=Float()"
            if problemas
            else "Todas as chamadas .op('<=>') têm return_type=Float()."
        ),
        dica_correcao=(
            "Adicione return_type=Float() ao .op('<=>') para evitar que o "
            "result_processor do Vector seja aplicado ao float de distancia. "
            "Exemplo: .op('<=>', return_type=Float())(param)"
        ),
    )


@registrar_check(
    id="cobertura-evolucao-desatualizada",
    titulo="cobertura_evolucao.yaml desincronizado dos sprint_NN_*_interno.yaml",
    severidade="error",
    escopos=["sempre", "pre-commit"],
)
def _check_cobertura_evolucao_desatualizada(raiz: Path) -> CheckResult:
    """
    Verifica se `artefatos/gerente_de_projetos/cobertura_evolucao.yaml` está
    em sincronia com os yaml de report (`sprint_NN_*_interno.yaml`).

    Comportamento (padrão B + bypass, ver discussão na implementação da G06):
    - Se o conteúdo bate com o esperado → passa em silêncio.
    - Se diverge → **reescreve o arquivo** com o conteúdo correto e falha,
      pedindo `git add` + retry do commit.

    Diretriz relacionada: G06 (artefatos/gerente_de_projetos/diretrizes.md).
    """
    # Import preguiçoso para evitar custo quando o check não roda.
    script_path = (
        raiz / "agentes" / "scripts" / "gerente_de_projetos"
        / "atualiza_cobertura_evolucao.py"
    )
    if not script_path.exists():
        return CheckResult(
            passou=True,
            mensagem=(
                "Script atualiza_cobertura_evolucao.py nao encontrado; "
                "check ignorado."
            ),
        )

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "atualiza_cobertura_evolucao", script_path
    )
    if spec is None or spec.loader is None:
        return CheckResult(
            passou=True,
            mensagem="Nao foi possivel carregar atualiza_cobertura_evolucao.py; check ignorado.",
        )
    modulo = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(modulo)
    except Exception as exc:  # pragma: no cover - defensivo
        return CheckResult(
            passou=False,
            severidade="error",
            mensagem=f"Erro ao carregar atualiza_cobertura_evolucao.py: {exc}",
            dica_correcao=(
                "Corrija o script atualiza_cobertura_evolucao.py antes de comitar."
            ),
        )

    try:
        esperado = modulo.gerar_conteudo_esperado()
        atual = modulo.ler_conteudo_atual()
    except Exception as exc:
        return CheckResult(
            passou=False,
            severidade="error",
            mensagem=f"Erro ao calcular conteudo esperado: {exc}",
            dica_correcao=(
                "Rode 'python agentes/scripts/gerente_de_projetos/"
                "atualiza_cobertura_evolucao.py' manualmente para reproduzir o erro."
            ),
        )

    if atual == esperado:
        return CheckResult(
            passou=True,
            mensagem="cobertura_evolucao.yaml esta atualizado.",
        )

    # Diverge: reescreve o arquivo (bypass quando ja estava certo evita esta linha).
    try:
        modulo.EVOLUCAO_PATH.parent.mkdir(parents=True, exist_ok=True)
        modulo.EVOLUCAO_PATH.write_text(esperado, encoding="utf-8")
    except OSError as exc:
        return CheckResult(
            passou=False,
            severidade="error",
            mensagem=f"Nao foi possivel reescrever cobertura_evolucao.yaml: {exc}",
            dica_correcao=(
                "Verifique permissoes de escrita em "
                "artefatos/gerente_de_projetos/cobertura_evolucao.yaml."
            ),
        )

    rel = modulo.EVOLUCAO_PATH.relative_to(raiz).as_posix()
    return CheckResult(
        passou=False,
        severidade="error",
        findings=[f"{rel} foi regenerado automaticamente."],
        mensagem=(
            "cobertura_evolucao.yaml estava desatualizado e foi regenerado "
            "automaticamente a partir dos sprint_NN_*_interno.yaml."
        ),
        dica_correcao=(
            f"Rode 'git add {rel}' e tente o commit novamente. "
            "O arquivo correto ja esta no disco; basta inclui-lo no stage."
        ),
    )


@registrar_check(
    id="ruff-lint",
    titulo="Lint e imports via Ruff",
    severidade="error",
    escopos=["sempre", "pre-commit"],
)
def _check_ruff(raiz: Path) -> CheckResult:
    """
    Invoca Ruff para verificar qualidade de codigo e imports.
    Ruff cobre: imports nao usados, isort, erros de sintaxe, warnings, etc.
    Configuracao em pyproject.toml.
    """
    import subprocess

    try:
        result = subprocess.run(
            ["ruff", "check", str(raiz)],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        return CheckResult(
            passou=True,
            mensagem="Ruff nao instalado; check ignorado. Instale: pip install ruff",
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            passou=False,
            severidade="warning",
            mensagem="Ruff timeout (30s); check ignorado.",
        )

    passou = result.returncode == 0
    findings = result.stdout.splitlines() if not passou else []
    comandos = ["ruff check .", "ruff check --fix ."] if not passou else []

    return CheckResult(
        passou=passou,
        severidade="error",
        findings=findings,
        comandos_uteis=comandos,
        mensagem="Ruff: OK" if passou else f"Ruff: {len(findings)} problema(s)",
        dica_correcao="Rode `ruff check --fix .` para correcoes automaticas.",
    )


@registrar_check(
    id="mypy-type-check",
    titulo="Checagem de tipos via mypy (backend)",
    severidade="warning",
    escopos=["sempre", "pre-commit"],
)
def _check_mypy(raiz: Path) -> CheckResult:
    """
    Invoca mypy sobre backend/ (mesma raiz de import usada em runtime — ver
    CLAUDE.md, "uvicorn main:app" a partir de backend/; rodar da raiz do repo
    degrada a inferencia de tipo pra `Any` em boa parte do codigo).

    Severidade `warning` (nao bloqueia commit) de proposito: o projeto nunca rodou
    type-checker antes, ha uma divida pre-existente relevante (140 erros/24 arquivos
    em 2026-08-20). Endurecer para `error` e uma decisao futura, depois que essa
    divida for equacionada — nao adicionar baseline/exclusao por modulo sem decisao
    explicita nesse sentido.

    Usa `sys.executable -m mypy` (o interprete que ja esta rodando este check —
    `backend/venv/bin/python` quando chamado via hook) em vez de um `mypy` bruto
    dependendo do PATH global: o hook (`run_qa_check_precommit.sh`) roda com o PATH
    herdado do processo do `git commit`, que nao inclui `backend/venv/bin` so por
    esse venv existir — precisa do pacote instalado no MESMO interpretador.
    """
    import subprocess
    import sys

    backend_dir = raiz / "backend"
    config_file = raiz / "pyproject.toml"
    try:
        result = subprocess.run(
            [sys.executable, "-m", "mypy", "--config-file", str(config_file), "."],
            cwd=str(backend_dir),
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            passou=False,
            severidade="warning",
            mensagem="mypy timeout (120s); check ignorado.",
        )

    if result.returncode != 0 and "No module named mypy" in result.stderr:
        return CheckResult(
            passou=True,
            mensagem=(
                f"mypy nao instalado em {sys.executable}; check ignorado. "
                "Instale no venv do projeto: cd backend && pip install mypy"
            ),
        )

    passou = result.returncode == 0
    findings = result.stdout.splitlines() if not passou else []
    comandos = ["cd backend && mypy --config-file ../pyproject.toml ."] if not passou else []

    return CheckResult(
        passou=passou,
        severidade="warning",
        findings=findings,
        comandos_uteis=comandos,
        mensagem="mypy: OK" if passou else f"mypy: {len(findings)} linha(s) de saida (erros + resumo)",
        dica_correcao=(
            "Severidade `warning` de proposito — e so relatorio, nao bloqueia commit "
            "(ha divida pre-existente). Rode o comando acima pra ver os erros com contexto completo."
        ),
    )


# ----------------------------------------------------------------------
# QAEngineer — agente executor da checklist
# ----------------------------------------------------------------------


class QAEngineer(BaseAgente):
    """
    Agente responsável pela qualidade geral do projeto.

    Atua em três frentes:
    - Qualidade de Documentação
    - Qualidade de Código
    - Qualidade de Processo
    """

    def __init__(self, projeto_root: str = None):
        super().__init__(
            nome="QA Engineer",
            papel="Garantir a qualidade do projeto em documentação, código e processos",
            projeto_root=projeto_root,
        )

        self.checklists = {
            "documentacao": [
                "Todos os arquivos de requisitos estão completos",
                "Documentação técnica está atualizada",
                "README está claro e funcional",
                "Decisões arquiteturais (ADRs) estão documentadas",
                "Histórico de alterações está atualizado",
            ],
            "codigo": [
                "Código segue padrões do projeto",
                "Funções e classes estão documentadas",
                "Não há código duplicado desnecessário",
                "Tratamento de erros está adequado",
                "Testes cobrem funcionalidades críticas",
            ],
            "processo": [
                "Branches seguem nomenclatura definida",
                "PRs têm descrição adequada",
                "Commits são atômicos e bem descritos",
                "CI/CD está configurado e funcionando",
                "Fluxo de trabalho está sendo seguido",
            ],
            "release": [
                "Todos os requisitos da versão foram implementados",
                "Testes passaram",
                "Documentação foi atualizada",
                "Changelog foi atualizado",
                "Versão foi tagueada corretamente",
            ],
        }

    # ------------------------------------------------------------------
    # Metodos abstratos do BaseAgente
    # ------------------------------------------------------------------
    def get_prompt_sistema(self) -> str:
        return (
            "Voce e o QA Engineer do projeto. Seu papel e garantir qualidade "
            "em documentacao, codigo e processos, apoiando revisoes de PR, "
            "checklists de release e executando os checks automatizados "
            "registrados no registry. Severidade `error` bloqueia commits; "
            "`warning` e `info` apenas alertam."
        )

    def get_contexto(self) -> dict:
        return {
            "agente": self.nome,
            "papel": self.papel,
            "checks_registrados": [c.id for c in _REGISTRY.values()],
            "artefatos": self.listar_artefatos(),
            "pendencias": self.obter_pendencias(),
        }

    # ------------------------------------------------------------------
    # Execucao da checklist de checks automatizados
    # ------------------------------------------------------------------
    def listar_checks(self, escopo: Optional[str] = None) -> List[Dict]:
        """
        Lista os checks registrados.

        Args:
            escopo: Se informado, filtra por escopo (ex: "pre-commit").
        """
        resultado = []
        for check in _REGISTRY.values():
            if escopo and escopo not in check.escopos:
                continue
            resultado.append(
                {
                    "id": check.id,
                    "titulo": check.titulo,
                    "severidade": check.severidade,
                    "escopos": list(check.escopos),
                }
            )
        return resultado

    def executar_checks(
        self,
        escopo: Optional[str] = None,
        check_id: Optional[str] = None,
        formato: str = "dict",
    ) -> Dict:
        """
        Executa os checks registrados e retorna o relatorio consolidado.

        Args:
            escopo: Filtra checks pelo escopo (pre-commit, pre-push, release, sempre).
                Se None, roda TODOS os registrados.
            check_id: Se informado, roda apenas o check com esse id (ignora escopo).
            formato: "dict" (padrao) retorna o dicionario; "json" retorna string
                JSON formatada com indentacao, pronta para print.

        Returns:
            Dict com:
            - `resultados`: list de {id, titulo, severidade, passou, findings, mensagem}
            - `total`: total de checks executados
            - `passaram`: quantos passaram
            - `falharam_error`: quantos falharam com severidade `error`
            - `falharam_warning`: quantos falharam com severidade `warning`
            - `bloqueia_commit`: bool, True se algum `error` falhou
        """
        raiz = Path(self.projeto_root).resolve()

        if check_id is not None:
            checks = [_REGISTRY[check_id]] if check_id in _REGISTRY else []
            if not checks:
                raise KeyError(f"Check nao encontrado: {check_id}")
        else:
            checks = [c for c in _REGISTRY.values() if escopo is None or escopo in c.escopos]

        resultados = []
        falharam_error = 0
        falharam_warning = 0
        passaram = 0
        for check in checks:
            try:
                result = check.funcao(raiz)
            except Exception as exc:  # defensivo: um check quebrado nao derruba o resto
                result = CheckResult(
                    passou=False,
                    severidade="error",
                    findings=[f"Excecao ao executar: {exc!r}"],
                    mensagem=f"Check {check.id} lancou excecao",
                )
            severidade_efetiva = result.severidade or check.severidade
            resultados.append(
                {
                    "id": check.id,
                    "titulo": check.titulo,
                    "severidade": severidade_efetiva,
                    "passou": result.passou,
                    "findings": result.findings,
                    "comandos_uteis": result.comandos_uteis,
                    "mensagem": result.mensagem,
                    "dica_correcao": result.dica_correcao,
                }
            )
            if result.passou:
                passaram += 1
            else:
                if severidade_efetiva == "error":
                    falharam_error += 1
                elif severidade_efetiva == "warning":
                    falharam_warning += 1

        relatorio = {
            "resultados": resultados,
            "total": len(checks),
            "passaram": passaram,
            "falharam_error": falharam_error,
            "falharam_warning": falharam_warning,
            "bloqueia_commit": falharam_error > 0,
        }
        if formato == "json":
            return json.dumps(relatorio, indent=2, ensure_ascii=False)
        return relatorio

    def revisar_documentacao(self, artefatos: List[str]) -> Dict:
        """
        Revisa a documentação do projeto.

        Args:
            artefatos: Lista de caminhos dos artefatos a revisar

        Returns:
            Relatório com findings e sugestões
        """
        return {
            "tipo": "revisao_documentacao",
            "checklist": self.checklists["documentacao"],
            "artefatos_revisados": artefatos,
            "findings": [],
            "sugestoes": [],
            "status": "pendente",
        }

    def revisar_codigo(self, arquivos: List[str]) -> Dict:
        """
        Revisa a qualidade do código.

        Args:
            arquivos: Lista de arquivos a revisar

        Returns:
            Relatório com findings e sugestões
        """
        return {
            "tipo": "revisao_codigo",
            "checklist": self.checklists["codigo"],
            "arquivos_revisados": arquivos,
            "findings": [],
            "sugestoes": [],
            "cobertura_testes": None,
            "status": "pendente",
        }

    def revisar_processo(self) -> Dict:
        """
        Revisa o processo de desenvolvimento.

        Returns:
            Relatório com findings e sugestões
        """
        return {
            "tipo": "revisao_processo",
            "checklist": self.checklists["processo"], "findings": [], "sugestoes": [], "status": "pendente"
        }

    def checklist_release(self, versao: str, requisitos: List[str]) -> Dict:
        """
        Executa checklist de qualidade antes de release.

        Args:
            versao: Versão a ser liberada
            requisitos: Lista de requisitos incluídos na versão

        Returns:
            Checklist de release com status de cada item
        """
        return {
            "tipo": "checklist_release",
            "versao": versao,
            "requisitos": requisitos,
            "checklist": self.checklists["release"],
            "itens_verificados": [],
            "aprovado": False,
            "observacoes": [],
        }

    def sugerir_melhorias(self, area: str) -> List[str]:
        """
        Sugere melhorias para uma área específica.

        Args:
            area: Área para sugestões (documentacao, codigo, processo)

        Returns:
            Lista de sugestões de melhoria
        """
        sugestoes_base = {
            "documentacao": [
                "Adicionar diagramas de arquitetura",
                "Criar glossário de termos do domínio",
                "Documentar decisões de design",
            ],
            "codigo": [
                "Aumentar cobertura de testes unitários",
                "Implementar testes de integração",
                "Adicionar linting automático",
            ],
            "processo": [
                "Configurar CI/CD completo",
                "Implementar code review obrigatório",
                "Adicionar métricas de qualidade",
            ],
        }
        return sugestoes_base.get(area, [])

    def gerar_relatorio_qualidade(self) -> Dict:
        """
        Gera relatório consolidado de qualidade do projeto.

        Returns:
            Relatório com status geral e recomendações
        """
        return {
            "tipo": "relatorio_qualidade",
            "data": None,  # Será preenchido na execução
            "areas": {
                "documentacao": {"status": "pendente", "score": None},
                "codigo": {"status": "pendente", "score": None},
                "processo": {"status": "pendente", "score": None},
            },
            "recomendacoes_prioritarias": [],
            "proximos_passos": [],
        }


# Instância do agente para uso direto
qa_engineer = QAEngineer()
