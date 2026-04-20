"""
Agente QA Engineer - Responsável pela qualidade do projeto.

Responsabilidades:
1. Revisar documentação (coerência, completude, padrões)
2. Definir e revisar cobertura de testes
3. Validar fluxo de branches e PRs
4. Sugerir melhorias de processo
5. Checklist de qualidade antes de releases
"""

from typing import Dict, List, Optional
from base_agente import BaseAgente


class QAEngineer(BaseAgente):
    """
    Agente responsável pela qualidade geral do projeto.
    
    Atua em três frentes:
    - Qualidade de Documentação
    - Qualidade de Código
    - Qualidade de Processo
    """
    
    def __init__(self):
        super().__init__(
            nome="QA Engineer",
            papel="Garantir a qualidade do projeto em documentação, código e processos",
            objetivo="Manter padrões de qualidade, identificar gaps e sugerir melhorias"
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
            ]
        }
    
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
            "status": "pendente"
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
            "status": "pendente"
        }
    
    def revisar_processo(self) -> Dict:
        """
        Revisa o processo de desenvolvimento.
        
        Returns:
            Relatório com findings e sugestões
        """
        return {
            "tipo": "revisao_processo",
            "checklist": self.checklists["processo"],
            "findings": [],
            "sugestoes": [],
            "status": "pendente"
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
            "observacoes": []
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
            ]
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
            "proximos_passos": []
        }


# Instância do agente para uso direto
qa_engineer = QAEngineer()
