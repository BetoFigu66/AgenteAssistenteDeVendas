"""
Agente Gerente de Projetos
Responsável por gestão ágil do projeto, relatórios de Sprint e coordenação dos agentes.
"""
from .base_agente import BaseAgente
from pathlib import Path
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class GerenteDeProjetos(BaseAgente):
    """
    Gerente de Projetos - Gestão ágil, relatórios de Sprint e coordenação.
    
    Responsabilidades:
    - Conduzir cerimônias de Sprint (planning, daily, review, retrospectiva)
    - Gerar relatórios de Sprint (a cada 2 semanas)
    - Priorizar backlog e pendências
    - Coordenar trabalho entre agentes
    - Alertar sobre bloqueios e dependências
    - Manter visão geral do projeto
    """
    
    def __init__(self, projeto_root: str = None):
        super().__init__(
            nome="Gerente de Projetos",
            papel="Gerenciar o projeto de forma ágil, gerar relatórios de Sprint e coordenar agentes",
            projeto_root=projeto_root
        )
        self.agentes_gerenciados = [
            "Analista de Requisitos",
            "Auxiliar de Negocios", 
            "Arquiteto de Sistemas",
            "Planejador de Negocios",
            "QA Engineer",
            "Implementador"
        ]
        
        # Configurações de Sprint (padrão: 2 semanas)
        self.duracao_sprint_dias = 14
    
    def get_prompt_sistema(self) -> str:
        return """Você é o Gerente de Projetos do projeto, responsável por conduzir o desenvolvimento de forma ágil.

Seu papel é:
1. **Gestão de Sprint**: Relatórios a cada 2 semanas (feito → próximo → pendente)
2. **Cerimônias ágeis**: Planning, daily, review, retrospectiva
3. **Priorização**: Ordenar backlog e pendências por valor/urgência
4. **Coordenação**: Alinhar trabalho entre agentes e remover impedimentos
5. **Comunicação**: Relatórios claros de progresso para stakeholders

Agentes sob sua coordenação:
1. **Analista de Requisitos**: Brainstorms e documentação de requisitos
2. **Auxiliar de Negócios**: Transformar ideia em produto
3. **Arquiteto de Sistemas**: Propor arquiteturas (POC, single, multi-tenant)
4. **Planejador de Negócios**: Monetização e estratégia comercial
5. **QA Engineer**: Qualidade de código e processos
6. **Implementador**: Governança e padrões de implementação

Estrutura de Relatório de Sprint:
- 📊 **Visão Geral**: Resumo executivo do Sprint
- ✅ **Feito (Done)**: O que foi entregue neste Sprint
- 🎯 **Próximo Sprint**: O que está planejado para as próximas 2 semanas
- 📋 **Backlog Pendente**: O que ainda falta do escopo total
- 🚨 **Bloqueios/Riscos**: Impedimentos e mitigações
- 📈 **Métricas**: Artefatos criados, pendências resolvidas/novas, bugs corrigidos

Formato de status:
- 🟢 Concluído
- 🟡 Em andamento
- 🔴 Bloqueado
- ⚪ Não iniciado"""

    def get_contexto(self) -> dict:
        return {
            "agente": self.nome,
            "papel": self.papel,
            "agentes_gerenciados": self.agentes_gerenciados,
            "artefatos": self.listar_artefatos(),
            "pendencias": self.obter_pendencias()
        }
    
    def obter_status_geral(self) -> dict:
        """Obtém status de todos os agentes e suas pendências."""
        projeto_root = Path(self.projeto_root)
        artefatos_root = projeto_root / "artefatos"
        
        status = {
            "data": datetime.now().isoformat(),
            "agentes": {}
        }
        
        for agente in self.agentes_gerenciados:
            nome_pasta = agente.lower().replace(" ", "_").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
            pasta_agente = artefatos_root / nome_pasta
            
            artefatos = []
            pendencias = []
            
            if pasta_agente.exists():
                artefatos = [f.name for f in pasta_agente.iterdir() if f.is_file() and f.name != "pendencias.json"]
                
                arquivo_pendencias = pasta_agente / "pendencias.json"
                if arquivo_pendencias.exists():
                    with open(arquivo_pendencias, 'r', encoding='utf-8') as f:
                        pendencias = json.load(f)
            
            status["agentes"][agente] = {
                "artefatos": artefatos,
                "total_artefatos": len(artefatos),
                "pendencias": pendencias,
                "pendencias_abertas": len([p for p in pendencias if p.get("status") == "pendente"])
            }
        
        return status
    
    # ------------------------------------------------------------------
    # Sprint Review — fluxo YAML (fonte da verdade) + PPTX (apresentacao)
    # ------------------------------------------------------------------
    def gerar_dados_sprint_yaml(
        self,
        sprint_numero: int,
        data_inicio: datetime,
        data_fim: datetime,
        feito: List[Dict],
        proximo_sprint: List[Dict],
        backlog_pendente: List[Dict],
        bloqueios: Optional[List[str]] = None,
        metricas: Optional[Dict] = None,
        insights: Optional[List[str]] = None,
    ) -> Path:
        """
        Gera o arquivo YAML com os dados do Sprint.

        O YAML e a FONTE UNICA da verdade do Sprint Review e eh o unico
        artefato versionado. A apresentacao .pptx eh derivada dele via
        `gerar_apresentacao_pptx()` e NAO deve ser editada diretamente
        (exceto para formatacao visual).

        Args:
            sprint_numero: Numero do Sprint (1, 2, 3...).
            data_inicio: Data de inicio do Sprint.
            data_fim: Data de termino do Sprint.
            feito: Itens entregues. Cada item:
                `{"titulo": str, "descricao": str, "agente": str}`.
            proximo_sprint: Itens planejados. Cada item:
                `{"titulo": str, "prioridade": "alta"|"media"|"baixa"}`.
            backlog_pendente: Itens do escopo total ainda nao iniciados.
                Cada item: `{"titulo": str}`.
            bloqueios: Lista de impedimentos (strings).
            metricas: Dict com contagens. Se None, eh calculado automaticamente.
            insights: Observacoes livres para a secao de insights.

        Returns:
            Path do arquivo YAML gerado.
        """
        import yaml

        if metricas is None:
            metricas = self._calcular_metricas_sprint(data_inicio, data_fim)
        if bloqueios is None:
            bloqueios = []
        if insights is None:
            insights = []

        proximo_inicio = data_fim + timedelta(days=1)
        proximo_fim = data_fim + timedelta(days=self.duracao_sprint_dias)

        dados = {
            "sprint_numero": sprint_numero,
            "data_inicio": data_inicio.strftime("%Y-%m-%d"),
            "data_fim": data_fim.strftime("%Y-%m-%d"),
            "duracao_dias": self.duracao_sprint_dias,
            "proximo_sprint_inicio": proximo_inicio.strftime("%Y-%m-%d"),
            "proximo_sprint_fim": proximo_fim.strftime("%Y-%m-%d"),
            "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "feito": feito or [],
            "proximo_sprint": proximo_sprint or [],
            "backlog_pendente": backlog_pendente or [],
            "bloqueios": bloqueios,
            "metricas": metricas,
            "insights": insights,
        }

        nome_arquivo = (
            f"sprint_{sprint_numero:02d}_{data_fim.strftime('%Y%m%d')}.yaml"
        )
        caminho = self.artefatos_dir / nome_arquivo
        with open(caminho, "w", encoding="utf-8") as f:
            yaml.safe_dump(
                dados, f, allow_unicode=True, sort_keys=False, width=120
            )

        self.registrar_interacao(
            tipo="geracao_dados_sprint",
            conteudo=f"Dados do Sprint {sprint_numero} gerados: {nome_arquivo}",
            participantes=[self.nome],
        )
        return caminho

    def gerar_apresentacao_pptx(
        self,
        yaml_path,
        template_path=None,
        saida=None,
    ) -> Path:
        """
        Gera a apresentacao .pptx a partir do YAML + template.

        O arquivo gerado NAO eh versionado (ver .gitignore) e serve apenas
        para a cerimonia de Sprint Review. Ajustes de conteudo devem ser
        feitos no YAML, nao no .pptx.

        Args:
            yaml_path: Caminho do .yaml gerado por `gerar_dados_sprint_yaml()`.
            template_path: Caminho do template .pptx. Se None, usa
                `artefatos/gerente_projetos/sprint_review_template_v01.pptx`.
            saida: Caminho do .pptx de saida. Se None, gera nome automatico
                no diretorio do agente.

        Returns:
            Path do .pptx gerado.
        """
        import yaml
        from pptx import Presentation

        yaml_path = Path(yaml_path)
        with open(yaml_path, "r", encoding="utf-8") as f:
            dados = yaml.safe_load(f)

        if template_path is None:
            template_path = (
                self.artefatos_dir / "sprint_review_template_v01.pptx"
            )
        template_path = Path(template_path)
        if not template_path.exists():
            raise FileNotFoundError(
                f"Template pptx nao encontrado: {template_path}"
            )

        tokens_simples, tokens_lista = self._preparar_tokens_pptx(dados)

        prs = Presentation(str(template_path))
        for slide in prs.slides:
            for shape in slide.shapes:
                if shape.has_text_frame:
                    self._substituir_tokens_em_textframe(
                        shape.text_frame, tokens_simples, tokens_lista
                    )
                if shape.has_table:
                    for row in shape.table.rows:
                        for cell in row.cells:
                            self._substituir_tokens_em_textframe(
                                cell.text_frame, tokens_simples, tokens_lista
                            )

        if saida is None:
            sprint_n = int(dados.get("sprint_numero", 0))
            data_fim_str = str(dados.get("data_fim", "")).replace("-", "")
            saida = (
                self.artefatos_dir
                / f"sprint_review_{sprint_n:02d}_{data_fim_str}.pptx"
            )
        saida = Path(saida)
        prs.save(str(saida))

        self.registrar_interacao(
            tipo="geracao_apresentacao_sprint",
            conteudo=f"Apresentacao gerada: {saida.name}",
            participantes=[self.nome],
        )
        return saida

    def _preparar_tokens_pptx(self, dados: Dict):
        """
        Monta os dicts de tokens (simples e lista) a partir dos dados YAML.

        Returns:
            (tokens_simples, tokens_lista):
            - tokens_simples: {str: str} substituicao direta dentro do texto.
            - tokens_lista: {str: List[str]} quando o parrafo eh duplicado,
              uma copia por item (preservando formatacao do paragrafo).
        """
        metricas = dados.get("metricas") or {}

        def _fmt_data(s: str) -> str:
            try:
                return datetime.strptime(s, "%Y-%m-%d").strftime("%d/%m/%Y")
            except Exception:
                return s or ""

        tokens_simples = {
            "{{sprint_numero}}": f"{int(dados.get('sprint_numero', 0)):02d}",
            "{{data_inicio}}": _fmt_data(dados.get("data_inicio", "")),
            "{{data_fim}}": _fmt_data(dados.get("data_fim", "")),
            "{{duracao_dias}}": str(dados.get("duracao_dias", "")),
            "{{proximo_sprint_inicio}}": _fmt_data(
                dados.get("proximo_sprint_inicio", "")
            ),
            "{{proximo_sprint_fim}}": _fmt_data(
                dados.get("proximo_sprint_fim", "")
            ),
            "{{gerado_em}}": dados.get("gerado_em", ""),
            "{{metrica_artefatos_criados}}": str(
                metricas.get("artefatos_criados", 0)
            ),
            "{{metrica_pendencias_resolvidas}}": str(
                metricas.get("pendencias_resolvidas", 0)
            ),
            "{{metrica_pendencias_novas}}": str(
                metricas.get("pendencias_novas", 0)
            ),
            "{{metrica_bugs_corrigidos}}": str(
                metricas.get("bugs_corrigidos", 0)
            ),
            "{{metrica_reports_total}}": str(metricas.get("reports_total", 0)),
            "{{metrica_reports_resolvidos}}": str(
                metricas.get("reports_resolvidos", 0)
            ),
        }

        emoji_prio = {"alta": "🔴", "media": "🟡", "baixa": "🟢"}

        def _fmt_feito(item: Dict) -> str:
            titulo = item.get("titulo", "Sem titulo")
            agente = item.get("agente", "Time")
            desc = item.get("descricao", "")
            if desc:
                return f"{titulo} — {agente}: {desc}"
            return f"{titulo} — {agente}"

        def _fmt_proximo(item: Dict) -> str:
            prio = item.get("prioridade", "media")
            return f"{emoji_prio.get(prio, '⚪')} {item.get('titulo', 'Sem titulo')} ({prio})"

        def _fmt_backlog(item: Dict) -> str:
            return item.get("titulo", "Sem titulo")

        tokens_lista = {
            "{{feito}}": [_fmt_feito(i) for i in (dados.get("feito") or [])]
            or ["(nenhum)"],
            "{{proximo_sprint}}": [
                _fmt_proximo(i) for i in (dados.get("proximo_sprint") or [])
            ]
            or ["(nenhum)"],
            "{{backlog_pendente}}": [
                _fmt_backlog(i) for i in (dados.get("backlog_pendente") or [])
            ]
            or ["(nenhum)"],
            "{{bloqueios}}": list(dados.get("bloqueios") or [])
            or ["(nenhum bloqueio)"],
            "{{insights}}": list(dados.get("insights") or [])
            or ["(sem observacoes)"],
        }
        return tokens_simples, tokens_lista

    @staticmethod
    def _substituir_tokens_em_textframe(text_frame, tokens_simples, tokens_lista):
        """
        Substitui tokens dentro de um text_frame do python-pptx.

        - Tokens simples: substituicao de texto direto.
        - Tokens de lista: o paragrafo que contem o token eh duplicado
          uma vez por item da lista, preservando a formatacao.
        """
        from copy import deepcopy

        # Primeira passada: duplicar paragrafos para tokens de lista.
        paragrafos = list(text_frame.paragraphs)
        for paragraph in paragrafos:
            texto_paragrafo = "".join(run.text for run in paragraph.runs)
            token_lista_encontrado = None
            for token in tokens_lista:
                if token in texto_paragrafo:
                    token_lista_encontrado = token
                    break
            if not token_lista_encontrado:
                continue

            itens = tokens_lista[token_lista_encontrado]
            # Substitui o token no paragrafo original pelo primeiro item.
            GerenteDeProjetos._substituir_texto_no_paragrafo(
                paragraph,
                token_lista_encontrado,
                itens[0] if itens else "",
            )
            # Para os itens restantes, duplica o paragrafo apos o original.
            p_anchor = paragraph._p
            for item in itens[1:]:
                novo_p = deepcopy(paragraph._p)
                p_anchor.addnext(novo_p)
                p_anchor = novo_p
                # Substituicao no novo paragrafo (ainda contem o token original
                # antes da substituicao). Precisamos trocar pelo valor do item.
                # Reusa helper via wrapper leve.
                GerenteDeProjetos._substituir_texto_em_p_xml(
                    novo_p, itens[0] if itens else "", item
                )

        # Segunda passada: tokens simples em todos os paragrafos (inclusive
        # os recem-duplicados).
        for paragraph in text_frame.paragraphs:
            for token, valor in tokens_simples.items():
                texto = "".join(run.text for run in paragraph.runs)
                if token in texto:
                    GerenteDeProjetos._substituir_texto_no_paragrafo(
                        paragraph, token, valor
                    )

    @staticmethod
    def _substituir_texto_no_paragrafo(paragraph, alvo: str, novo: str):
        """
        Substitui `alvo` por `novo` dentro de um paragrafo, preservando a
        formatacao do primeiro run que contem o alvo.

        Estrategia: concatena o texto de todos os runs, aplica replace,
        coloca o resultado inteiro no primeiro run e zera os demais.
        """
        if not paragraph.runs:
            return
        texto_total = "".join(run.text for run in paragraph.runs)
        if alvo not in texto_total:
            return
        novo_texto = texto_total.replace(alvo, novo)
        paragraph.runs[0].text = novo_texto
        for run in paragraph.runs[1:]:
            run.text = ""

    @staticmethod
    def _substituir_texto_em_p_xml(p_element, alvo: str, novo: str):
        """
        Variante de `_substituir_texto_no_paragrafo` operando direto em um
        elemento <a:p> (lxml). Usada para paragrafos recem-duplicados antes
        de serem reencontrados pela API de alto nivel.
        """
        from pptx.oxml.ns import qn

        runs = p_element.findall(qn("a:r"))
        if not runs:
            return
        textos = []
        for r in runs:
            t = r.find(qn("a:t"))
            textos.append(t.text or "" if t is not None else "")
        texto_total = "".join(textos)
        if alvo not in texto_total:
            return
        novo_texto = texto_total.replace(alvo, novo)
        primeiro_t = runs[0].find(qn("a:t"))
        if primeiro_t is None:
            return
        primeiro_t.text = novo_texto
        for r in runs[1:]:
            t = r.find(qn("a:t"))
            if t is not None:
                t.text = ""
    
    def _calcular_metricas_sprint(self, data_inicio: datetime, data_fim: datetime) -> Dict:
        """Calcula métricas automáticas do período do Sprint."""
        status = self.obter_status_geral()
        
        # Contagem básica de artefatos e pendências
        total_artefatos = sum(d["total_artefatos"] for d in status["agentes"].values())
        total_pendencias = sum(d["pendencias_abertas"] for d in status["agentes"].values())
        
        # Contagem de pendências resolvidas (estimativa baseada no histórico)
        historico = self.listar_historico(dias=self.duracao_sprint_dias)
        interacoes = len(historico)
        
        return {
            "artefatos_criados": total_artefatos,
            "pendencias_resolvidas": max(0, interacoes - total_pendencias),  # Estimativa
            "pendencias_novas": total_pendencias,
            "bugs_corrigidos": 0,  # Será preenchido manualmente ou via integração futura
            "reports_total": 0,    # Via query ao banco futuramente
            "reports_resolvidos": 0
        }
    
    def gerar_relatorio_status(self) -> str:
        """Gera relatório de status do projeto (visualização rápida, não Sprint)."""
        status = self.obter_status_geral()
        
        conteudo = f"""# 📋 Relatório de Status do Projeto

**Data**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  
**Gerado por**: Gerente de Projetos

## Visão Geral por Agente

"""
        total_artefatos = 0
        total_pendencias = 0
        
        for agente, dados in status["agentes"].items():
            total_artefatos += dados["total_artefatos"]
            total_pendencias += dados["pendencias_abertas"]
            
            emoji = "🟢" if dados["pendencias_abertas"] == 0 and dados["total_artefatos"] > 0 else "🟡" if dados["total_artefatos"] > 0 else "⚪"
            
            conteudo += f"""### {emoji} {agente}
- **Artefatos**: {dados['total_artefatos']} | **Pendências abertas**: {dados['pendencias_abertas']}

"""
            if dados["pendencias"]:
                conteudo += "**Pendências ativas**:\n"
                for pend in dados["pendencias"][:5]:  # Limita a 5
                    status_emoji = "✅" if pend.get("status") == "concluido" else "⏳"
                    prio = pend.get("prioridade", "media")
                    conteudo += f"- {status_emoji} [{prio}] {pend.get('descricao', 'N/A')}\n"
                conteudo += "\n"
        
        conteudo += f"""## Resumo Executivo
- **Total de artefatos**: {total_artefatos}
- **Pendências abertas**: {total_pendencias}
- **Status geral**: {"🟢 Saudável" if total_pendencias < 5 else "🟡 Atenção" if total_pendencias < 10 else "🔴 Crítico"}

---
*Para o Sprint Review, use `gerar_dados_sprint_yaml()` seguido de `gerar_apresentacao_pptx()`*
"""
        
        return str(self.criar_artefato(
            f"relatorio_status_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
            conteudo,
            tipo="relatorio_status"
        ))
    
    def listar_historico(self, dias: int = 7) -> list:
        """Lista histórico de interações dos últimos N dias."""
        historico_completo = []
        
        for arquivo in self.historico_dir.glob("ata_*.json"):
            with open(arquivo, 'r', encoding='utf-8') as f:
                registros = json.load(f)
                historico_completo.extend(registros)
        
        # Ordena por data
        historico_completo.sort(key=lambda x: x.get("data", ""), reverse=True)
        
        return historico_completo
    
    def gerar_ata_reuniao(self, participantes: list, pauta: list, decisoes: list, proximos_passos: list):
        """Gera ata de reunião formal."""
        conteudo = f"""# Ata de Reunião

**Data**: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Participantes
"""
        for p in participantes:
            conteudo += f"- {p}\n"
        
        conteudo += "\n## Pauta\n"
        for i, item in enumerate(pauta, 1):
            conteudo += f"{i}. {item}\n"
        
        conteudo += "\n## Decisões\n"
        for i, decisao in enumerate(decisoes, 1):
            conteudo += f"{i}. {decisao}\n"
        
        conteudo += "\n## Próximos Passos\n"
        for passo in proximos_passos:
            conteudo += f"- [ ] **{passo.get('responsavel', 'A definir')}**: {passo.get('acao', 'N/A')} (Prazo: {passo.get('prazo', 'A definir')})\n"
        
        nome_arquivo = f"ata_reuniao_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
        return self.criar_artefato(nome_arquivo, conteudo, tipo="ata")
    
    def alertar_pendencias_criticas(self) -> list:
        """Identifica e retorna pendências críticas de todos os agentes."""
        status = self.obter_status_geral()
        criticas = []
        
        for agente, dados in status["agentes"].items():
            for pend in dados["pendencias"]:
                if pend.get("prioridade") == "alta" and pend.get("status") == "pendente":
                    criticas.append({
                        "agente": agente,
                        "pendencia": pend
                    })
        
        return criticas
    
    def criar_pendencia_para_agente(self, agente: str, descricao: str, prioridade: str = "media"):
        """Cria uma pendência para um agente específico."""
        nome_pasta = agente.lower().replace(" ", "_").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
        pasta_agente = Path(self.projeto_root) / "artefatos" / nome_pasta
        pasta_agente.mkdir(parents=True, exist_ok=True)
        
        arquivo_pendencias = pasta_agente / "pendencias.json"
        pendencias = []
        
        if arquivo_pendencias.exists():
            with open(arquivo_pendencias, 'r', encoding='utf-8') as f:
                pendencias = json.load(f)
        
        pendencia = {
            "id": len(pendencias) + 1,
            "descricao": descricao,
            "prioridade": prioridade,
            "status": "pendente",
            "criado_em": datetime.now().isoformat(),
            "criado_por": self.nome
        }
        pendencias.append(pendencia)
        
        with open(arquivo_pendencias, 'w', encoding='utf-8') as f:
            json.dump(pendencias, f, ensure_ascii=False, indent=2)
        
        self.registrar_interacao(
            tipo="criacao_pendencia",
            conteudo=f"Pendência criada para {agente}: {descricao}",
            participantes=[self.nome, agente]
        )
        
        return pendencia
