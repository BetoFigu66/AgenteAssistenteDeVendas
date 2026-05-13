"""
Agente Analista de Requisitos (Kika)
Responsavel por elaborar, documentar e revisar requisitos formais do sistema.

A fonte da verdade das regras de trabalho deste agente esta em:
    agentes/analista_requisitos.md

Este modulo Python apenas provem utilitarios para:
  - Carregar o prompt de sistema a partir do .md
  - Gerar um esqueleto de REQ formal seguindo a estrutura padrao
  - Executar um check de consistencia basico sobre os REQs existentes
"""
from pathlib import Path
from datetime import datetime
import re

from .base_agente import BaseAgente


class AnalistaRequisitos(BaseAgente):
    """
    Analista de Requisitos (Kika) - elabora e revisa requisitos formais.

    Responsabilidades:
    - Conduzir brainstorms estruturados
    - Documentar requisitos funcionais e nao-funcionais em REQ-XXX
    - Manter historico de versoes dentro de cada REQ
    - Revisar consistencia do conjunto de REQs
    - Identificar sobreposicoes e duplicacoes
    """

    REQS_DIR = "artefatos/requisitos_formais"
    PROMPT_MD = "agentes/analista_requisitos.md"

    def __init__(self, projeto_root: str = None):
        super().__init__(
            nome="Analista de Requisitos",
            papel="Elaborar, documentar e revisar requisitos formais do sistema (REQ-XXX)",
            projeto_root=projeto_root,
        )
        self.contexto_projeto = self._carregar_contexto_projeto()

    def _carregar_contexto_projeto(self) -> dict:
        return {
            "produto": "Assistente de Vendas via WhatsApp com IA",
            "cliente_inicial": "Inforrel (catracas, relogios de ponto, controle de acesso)",
            "stakeholder_principal": "Rita (operacao/atendimento)",
            "problema": "Automatizar atendimento via WhatsApp Business com qualificacao de leads e escalonamento",
            "objetivos": [
                "Responder automaticamente com RAG quando possivel",
                "Escalar para humano quando necessario",
                "Qualificar leads via fluxo conversacional adaptativo",
                "Rastrear orcamentos e conversoes",
                "Tratar reclamacoes de pos-venda com identificacao de pedido",
            ],
            "reqs_dir": self.REQS_DIR,
        }

    # ------------------------------------------------------------------
    # Prompt de sistema (fonte: .md)
    # ------------------------------------------------------------------

    def get_prompt_sistema(self) -> str:
        """Le o prompt de sistema a partir do arquivo .md (fonte da verdade)."""
        prompt_path = Path(self.projeto_root) / self.PROMPT_MD
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        # Fallback minimo caso o .md seja apagado
        return (
            "Voce e a Kika, Analista de Requisitos da Inforrel. "
            "Documente requisitos em artefatos/requisitos_formais/ seguindo "
            "a estrutura de 12 secoes e mantendo historico de versoes. "
            "(Prompt completo em agentes/analista_requisitos.md nao encontrado.)"
        )

    def get_contexto(self) -> dict:
        return {
            "agente": self.nome,
            "papel": self.papel,
            "projeto": self.contexto_projeto,
            "artefatos": self.listar_artefatos(),
            "reqs_existentes": self._listar_reqs(),
            "pendencias": self.obter_pendencias(),
        }

    # ------------------------------------------------------------------
    # Criacao de REQ formal com a estrutura padrao (12 secoes)
    # ------------------------------------------------------------------

    def gerar_esqueleto_req(
        self,
        req_id: str,
        titulo: str,
        categoria: str = "A definir",
        prioridade: str = "Media",
        solicitante: str = "A definir",
        tipo: str = "Funcional",
    ) -> str:
        """
        Gera o conteudo de um REQ formal seguindo a estrutura de 12 secoes
        documentada em agentes/analista_requisitos.md.

        Args:
            req_id: ex "REQ-011"
            titulo: ex "Integracao com API de Pagamento"
            categoria: ex "Integracao Externa"
            prioridade: Alta | Media | Baixa
            solicitante: ex "Rita (Inforrel)"
            tipo: Funcional | Nao-Funcional | Integracao

        Returns:
            Conteudo markdown pronto para ser salvo em requisitos_formais/.
        """
        data = datetime.now().strftime("%Y-%m-%d")
        data_br = datetime.now().strftime("%d/%m/%Y")
        return f"""# {req_id}: {titulo}

**Versao**: 1.0
**Data**: {data}
**Autor**: Kika (Analista de Requisitos)
**Status**: Em Elaboracao
**Prioridade**: {prioridade}

---

## 1. Identificacao do Requisito

**ID**: {req_id}
**Tipo**: {tipo}
**Categoria**: {categoria}
**Solicitante**: {solicitante}

---

## 2. Descricao

(Paragrafo curto explicando o que o requisito garante.)

---

## 3. Justificativa de Negocio

**Problema Atual**:
- ...

**Beneficio Esperado**:
- ...

---

## 4. Criterios de Aceite

### 4.1 Funcionalidades Obrigatorias

- [ ] **{req_id}.1 — Titulo descritivo**: descricao completa

### 4.2 Regras de Negocio

- [ ] **{req_id}.N — Titulo descritivo**: descricao completa

### 4.3 Requisitos Nao-Funcionais

- [ ] **{req_id}.M — Titulo descritivo**: descricao completa

---

## 5. Integracao com Requisitos Existentes

- **REQ-XXX**: (descrever a relacao)

---

## 6. Fluxo / Exemplos (quando aplicavel)

```
(exemplo de fluxo ou diagrama)
```

---

## 7. Limitacoes Aceitas no POC

- [ ] ...

---

## 8. Dependencias

### 8.1 Dependencias Tecnicas
- ...

### 8.2 Dependencias de Negocio
- ...

---

## 9. Riscos e Mitigacoes

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|---------------|---------|-----------|
| ... | ... | ... | ... |

---

## 10. Estimativas

| Atividade | Horas |
|-----------|-------|
| ... | Xh |
| **Total** | **Xh** |

---

## 11. Historico de Alteracoes

| Data | Versao | Alteracao | Autor |
|------|--------|-----------|-------|
| {data_br} | 1.0 | Criacao inicial do requisito | Kika |

---

## 12. Aprovacoes

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| Analista de Requisitos | Kika | {data_br} | [ ] |
| Cliente (Inforrel) | Rita | ____/____/____ | [ ] |
| Lider Tecnico | Beto | ____/____/____ | [ ] |
"""

    def criar_req_formal(
        self,
        req_id: str,
        titulo: str,
        slug: str,
        **kwargs,
    ) -> Path:
        """
        Cria um novo arquivo de REQ formal em artefatos/requisitos_formais/
        usando o esqueleto padrao.

        Args:
            req_id: ex "REQ-011"
            titulo: titulo descritivo
            slug: parte do nome do arquivo depois do req_id (ex "integracao-pagamento")
            **kwargs: repassados para gerar_esqueleto_req
        """
        conteudo = self.gerar_esqueleto_req(req_id, titulo, **kwargs)
        reqs_dir = Path(self.projeto_root) / self.REQS_DIR
        reqs_dir.mkdir(parents=True, exist_ok=True)
        arquivo = reqs_dir / f"{req_id}-{slug}.md"
        if arquivo.exists():
            raise FileExistsError(f"{arquivo} ja existe. Use versionamento interno.")
        arquivo.write_text(conteudo, encoding="utf-8")
        self.registrar_interacao(
            tipo="criacao_req_formal",
            conteudo=f"Criado {arquivo.name} ({titulo})",
            participantes=[self.nome],
        )
        return arquivo

    # ------------------------------------------------------------------
    # Revisao de consistencia
    # ------------------------------------------------------------------

    def revisar_consistencia(self) -> dict:
        """
        Varredura simples dos REQs formais para detectar problemas basicos.

        Verifica:
          - Sub-requisitos sem titulo descritivo (formato REQ-XXX.Y sem " — ")
          - Referencias cruzadas a REQs que nao existem
          - REQs sem secao "Historico de Alteracoes"

        Returns:
            dict com listas de achados por categoria.
        """
        reqs_dir = Path(self.projeto_root) / self.REQS_DIR
        if not reqs_dir.exists():
            return {"erro": f"{self.REQS_DIR} nao encontrado"}

        arquivos = sorted(reqs_dir.glob("REQ-*.md"))
        ids_existentes = set()
        for f in arquivos:
            m = re.match(r"(REQ-\d+)", f.name)
            if m:
                ids_existentes.add(m.group(1))

        sem_titulo: list[str] = []
        refs_quebradas: list[str] = []
        sem_historico: list[str] = []
        # So considera declaracao de sub-requisito as linhas que comecam com
        # checkbox de aceite ("- [ ]" ou "- [x]"). Referencias em texto corrido
        # sao ignoradas.
        padrao_subreq = re.compile(
            r"^\s*-\s*\[[ xX]\]\s*\*\*REQ-\d+\.\w+\*\*(?!\s*\u2014)",
            re.MULTILINE,
        )
        padrao_ref = re.compile(r"REQ-\d+")

        for f in arquivos:
            texto = f.read_text(encoding="utf-8")

            # Sub-requisitos sem titulo
            for m in padrao_subreq.finditer(texto):
                linha = texto[:m.start()].count("\n") + 1
                sem_titulo.append(f"{f.name}:{linha} {m.group(0)}")

            # Referencias a REQs inexistentes
            for m in padrao_ref.finditer(texto):
                ref = m.group(0)
                if ref not in ids_existentes:
                    linha = texto[:m.start()].count("\n") + 1
                    refs_quebradas.append(f"{f.name}:{linha} {ref}")

            # Sem historico
            if "Historico de Alteracoes" not in texto and "Histórico de Alterações" not in texto:
                sem_historico.append(f.name)

        return {
            "total_reqs": len(arquivos),
            "ids_existentes": sorted(ids_existentes),
            "sub_requisitos_sem_titulo": sem_titulo,
            "referencias_a_reqs_inexistentes": sorted(set(refs_quebradas)),
            "reqs_sem_historico_alteracoes": sem_historico,
        }

    # ------------------------------------------------------------------
    # Utilitarios
    # ------------------------------------------------------------------

    def _listar_reqs(self) -> list[str]:
        reqs_dir = Path(self.projeto_root) / self.REQS_DIR
        if not reqs_dir.exists():
            return []
        return sorted(f.name for f in reqs_dir.glob("REQ-*.md"))

    def iniciar_brainstorm(self, tema: str) -> str:
        """Inicia uma sessao de brainstorm sobre um tema especifico."""
        self.registrar_interacao(
            tipo="brainstorm_inicio",
            conteudo=f"Iniciando brainstorm sobre: {tema}",
        )
        return f"""# Sessao de Brainstorm: {tema}

Perguntas iniciais:

1. **Contexto**: Qual e o cenario atual? Como funciona hoje sem o sistema?
2. **Dores**: Quais sao os principais problemas que queremos resolver?
3. **Usuarios**: Quem sao os usuarios finais? Quais suas necessidades?
4. **Sucesso**: Como saberemos que o sistema esta funcionando bem?
5. **Restricoes**: Existem limitacoes tecnicas, de tempo ou orcamento?
6. **REQs relacionados**: Este tema se sobrepoe a algum REQ existente?
   (Listar via `revisar_consistencia()` para ver o inventario)

Vamos comecar por qual aspecto?
"""
