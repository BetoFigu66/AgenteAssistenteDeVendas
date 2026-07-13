"""Testes do pacote de análise e sugestão de documentos fonte."""

from pathlib import Path

from services.curador.documentos_fonte import sugerir_documentos_fonte

PROJETO_ROOT = Path(__file__).resolve().parents[2]


class TestSugerirDocumentosFonte:
    def test_sugere_por_trecho_rag_metadata(self):
        rag = [{
            "score": 0.52,
            "metadata": {
                "arquivo": "docs/FoldersProdutos/folder-controle-de-ponto.txt",
                "origem": "folder_produto",
            },
        }]
        resultado = sugerir_documentos_fonte(
            pergunta="Qual relogio de ponto para restaurante?",
            rag_candidatos=rag,
            projeto_root=PROJETO_ROOT,
        )
        caminhos = [r["caminho"] for r in resultado]
        assert "docs/FoldersProdutos/folder-controle-de-ponto.txt" in caminhos
        assert resultado[0]["motivo"] == "trecho_rag_diagnostico"

    def test_sugere_por_tipo_produto(self):
        resultado = sugerir_documentos_fonte(
            pergunta="Preciso de catraca",
            rag_candidatos=[],
            tipos_produto=["catraca"],
            projeto_root=PROJETO_ROOT,
        )
        assert any("Catracas.txt" in r["caminho"] for r in resultado)

    def test_overlap_tokens_no_nome_arquivo(self):
        resultado = sugerir_documentos_fonte(
            pergunta="voces tem relogio de ponto biometrico?",
            rag_candidatos=[],
            projeto_root=PROJETO_ROOT,
        )
        assert len(resultado) >= 1
        assert any("relogio" in r["caminho"].lower() or "ponto" in r["caminho"].lower() for r in resultado)

    def test_existe_no_disco_flag(self):
        resultado = sugerir_documentos_fonte(
            pergunta="catraca",
            tipos_produto=["catraca"],
            rag_candidatos=[],
            projeto_root=PROJETO_ROOT,
        )
        if resultado:
            assert "existe_no_disco" in resultado[0]
