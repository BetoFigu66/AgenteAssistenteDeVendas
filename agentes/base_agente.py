"""
Classe base para todos os agentes do sistema.
Define a interface comum e funcionalidades compartilhadas.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
import json
import os


class BaseAgente(ABC):
    """Classe base abstrata para todos os agentes."""
    
    def __init__(self, nome: str, papel: str, projeto_root: str = None):
        self.nome = nome
        self.papel = papel
        self.projeto_root = projeto_root or Path(__file__).parent.parent
        self.artefatos_dir = Path(self.projeto_root) / "artefatos" / self._nome_pasta()
        self.historico_dir = Path(self.projeto_root) / "historico"
        self._garantir_diretorios()
    
    def _nome_pasta(self) -> str:
        """Retorna nome da pasta baseado no nome do agente."""
        return self.nome.lower().replace(" ", "_").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    
    def _garantir_diretorios(self):
        """Cria diretórios necessários se não existirem."""
        self.artefatos_dir.mkdir(parents=True, exist_ok=True)
        self.historico_dir.mkdir(parents=True, exist_ok=True)
    
    def registrar_interacao(self, tipo: str, conteudo: str, participantes: list = None):
        """
        Registra uma interação/reunião no histórico.
        
        Args:
            tipo: Tipo da interação (brainstorm, reuniao, decisao, etc.)
            conteudo: Conteúdo da interação
            participantes: Lista de participantes
        """
        timestamp = datetime.now()
        registro = {
            "data": timestamp.isoformat(),
            "data_formatada": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "agente": self.nome,
            "tipo": tipo,
            "participantes": participantes or ["Usuário", self.nome],
            "conteudo": conteudo
        }
        
        # Salva no arquivo de histórico do dia
        arquivo_historico = self.historico_dir / f"ata_{timestamp.strftime('%Y%m%d')}.json"
        
        historico = []
        if arquivo_historico.exists():
            with open(arquivo_historico, 'r', encoding='utf-8') as f:
                historico = json.load(f)
        
        historico.append(registro)
        
        with open(arquivo_historico, 'w', encoding='utf-8') as f:
            json.dump(historico, f, ensure_ascii=False, indent=2)
        
        return registro
    
    def criar_artefato(self, nome_arquivo: str, conteudo: str, tipo: str = "documento"):
        """
        Cria um artefato (documento, diagrama, especificação, etc.).
        
        Args:
            nome_arquivo: Nome do arquivo a ser criado
            conteudo: Conteúdo do artefato
            tipo: Tipo do artefato
        """
        caminho = self.artefatos_dir / nome_arquivo
        
        with open(caminho, 'w', encoding='utf-8') as f:
            f.write(conteudo)
        
        # Registra criação do artefato
        self.registrar_interacao(
            tipo="criacao_artefato",
            conteudo=f"Artefato criado: {nome_arquivo} (tipo: {tipo})",
            participantes=[self.nome]
        )
        
        return caminho
    
    def listar_artefatos(self) -> list:
        """Lista todos os artefatos criados por este agente."""
        if not self.artefatos_dir.exists():
            return []
        return [f.name for f in self.artefatos_dir.iterdir() if f.is_file()]
    
    def obter_pendencias(self) -> list:
        """Retorna lista de pendências deste agente."""
        arquivo_pendencias = self.artefatos_dir / "pendencias.json"
        if arquivo_pendencias.exists():
            with open(arquivo_pendencias, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def adicionar_pendencia(self, descricao: str, prioridade: str = "media", dependencias: list = None):
        """Adiciona uma pendência para este agente."""
        pendencias = self.obter_pendencias()
        pendencia = {
            "id": len(pendencias) + 1,
            "descricao": descricao,
            "prioridade": prioridade,
            "status": "pendente",
            "criado_em": datetime.now().isoformat(),
            "dependencias": dependencias or []
        }
        pendencias.append(pendencia)
        
        arquivo_pendencias = self.artefatos_dir / "pendencias.json"
        with open(arquivo_pendencias, 'w', encoding='utf-8') as f:
            json.dump(pendencias, f, ensure_ascii=False, indent=2)
        
        return pendencia
    
    @abstractmethod
    def get_prompt_sistema(self) -> str:
        """Retorna o prompt de sistema específico do agente."""
        pass
    
    @abstractmethod
    def get_contexto(self) -> dict:
        """Retorna o contexto atual do agente."""
        pass
    
    def __repr__(self):
        return f"{self.__class__.__name__}(nome='{self.nome}', papel='{self.papel}')"
