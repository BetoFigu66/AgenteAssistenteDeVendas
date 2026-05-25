"""
Agente Implementador — responsável por implementar.

A fonte da verdade da identidade e do prompt deste agente esta em:
    agentes/implementador.md

E o harness de diretrizes operacionais em:
    artefatos/implementador/diretrizes.md

Este modulo Python apenas:
  - Carrega o prompt de sistema concatenando o .md de identidade + o .md de diretrizes
  - Oferece utilitarios para registrar e listar diretrizes programaticamente

Diferente dos outros agentes, o Implementador e operacional: e quem efetivamente
escreve o codigo. Diretrizes sao acumulativas: uma vez registrada, vale para sempre
(ate ser revisada explicitamente).
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .base_agente import BaseAgente


class Implementador(BaseAgente):
    """Agente que executa a implementação seguindo um conjunto versionado de diretrizes."""

    PROMPT_MD = "agentes/implementador.md"

    def __init__(self, projeto_root: str = None):
        super().__init__(
            nome="Implementador",
            papel="Executar a implementação do código seguindo as diretrizes acumuladas do projeto",
            projeto_root=projeto_root,
        )
        self.arquivo_diretrizes = self.artefatos_dir / "diretrizes.md"

    # ------------------------------------------------------------------
    # Harness — leitura / escrita de diretrizes
    # ------------------------------------------------------------------
    def carregar_diretrizes(self) -> str:
        """Retorna o conteúdo textual do harness, ou string vazia se não existir."""
        if self.arquivo_diretrizes.exists():
            return self.arquivo_diretrizes.read_text(encoding="utf-8")
        return ""

    def registrar_diretriz(
        self,
        titulo: str,
        regra: str,
        motivacao: str = "",
        contexto: str = "",
        categoria: str = "geral",
    ) -> Dict:
        """
        Acrescenta uma nova diretriz ao harness.

        Args:
            titulo: título curto (ex: "Não trocar stack por problema de ambiente")
            regra: regra imperativa a seguir
            motivacao: por que essa regra existe
            contexto: episódio que originou a regra (opcional)
            categoria: ex. "arquitetura", "migrations", "git", "qualidade"
        """
        conteudo = self.carregar_diretrizes()
        if not conteudo:
            conteudo = self._cabecalho_harness()

        data = datetime.now().strftime("%Y-%m-%d")
        numero = conteudo.count("\n### D") + 1
        bloco = f"\n### D{numero:02d} — {titulo}\n- **Categoria:** {categoria}\n- **Registrada em:** {data}\n- **Regra:** {regra}\n"
        if motivacao:
            bloco += f"- **Motivação:** {motivacao}\n"
        if contexto:
            bloco += f"- **Contexto:** {contexto}\n"

        self.arquivo_diretrizes.write_text(conteudo + bloco, encoding="utf-8")

        self.registrar_interacao(
            tipo="nova_diretriz",
            conteudo=f"D{numero:02d} — {titulo}",
            participantes=[self.nome, "Usuário"],
        )
        return {"numero": numero, "titulo": titulo, "arquivo": str(self.arquivo_diretrizes)}

    def listar_diretrizes(self) -> List[Dict]:
        """Parsing simples das diretrizes registradas."""
        texto = self.carregar_diretrizes()
        blocos = [b for b in texto.split("\n### ") if b.startswith("D")]
        out = []
        for b in blocos:
            linha1 = b.splitlines()[0]
            numero, _, titulo = linha1.partition(" — ")
            out.append({"numero": numero, "titulo": titulo})
        return out

    # ------------------------------------------------------------------
    # Harness — template inicial
    # ------------------------------------------------------------------
    def _cabecalho_harness(self) -> str:
        return (
            "# Harness do Agente Implementador\n\n"
            "Este documento é o **contrato de conduta** que toda implementação neste repositório deve seguir. "
            "Cada diretriz foi acumulada a partir de um episódio real do projeto e permanece ativa até ser revisada explicitamente.\n\n"
            "> 🧭 **Regra de ouro:** leia este arquivo antes de implementar algo não-trivial. "
            "Se uma situação nova não estiver coberta, pergunte ao usuário e registre a decisão como nova diretriz.\n\n"
            "---\n"
            "## Diretrizes ativas\n"
        )

    # ------------------------------------------------------------------
    # BaseAgente hooks
    # ------------------------------------------------------------------
    def get_prompt_sistema(self) -> str:
        """
        Le o prompt de sistema concatenando:
          1. agentes/implementador.md (identidade — fonte da verdade)
          2. artefatos/implementador/diretrizes.md (harness operacional)
        """
        prompt_path = Path(self.projeto_root) / self.PROMPT_MD
        if prompt_path.exists():
            identidade = prompt_path.read_text(encoding="utf-8")
        else:
            # Fallback minimo caso o .md seja apagado
            identidade = (
                "Voce e o Agente Implementador do projeto Assistente de Vendas. "
                "Sua funcao e escrever codigo de producao seguindo RIGOROSAMENTE o "
                "harness de diretrizes abaixo. Diretrizes tem precedencia sobre atalhos, "
                "conveniencia e problemas temporarios de ambiente. "
                "(Prompt completo em agentes/implementador.md nao encontrado.)"
            )

        diretrizes = self.carregar_diretrizes() or "(nenhuma diretriz registrada ainda)"
        return f"{identidade}\n\n---\n\n{diretrizes}"

    def get_contexto(self) -> Dict:
        return {
            "agente": self.nome,
            "papel": self.papel,
            "arquivo_diretrizes": str(self.arquivo_diretrizes),
            "total_diretrizes": len(self.listar_diretrizes()),
        }


# Instância para uso direto
implementador = Implementador()
