"""
Service de identificação de remetente.

Dado um telefone, determina:
- Se é um contato conhecido (0, 1 ou vários)
- Qual a empresa associada
- Se precisa de clarificação (novo telefone, múltiplos contatos)
"""
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from sqlalchemy.orm import Session

from models import Contato, Empresa

logger = logging.getLogger(__name__)


class StatusIdentificacao(str, Enum):
    """Status possíveis da identificação do remetente."""
    NOVO = "novo"                          # Telefone nunca visto
    UNICO = "unico"                        # Um contato só, identificado
    MULTIPLO = "multiplo"                  # Mesmo telefone em várias empresas
    SEM_EMPRESA = "sem_empresa"            # Contato existe mas sem empresa vinculada


@dataclass
class ResultadoIdentificacao:
    """Resultado da identificação de um telefone."""
    status: StatusIdentificacao
    contatos: List[Contato]
    empresas: List[Empresa]
    
    @property
    def contato(self) -> Optional[Contato]:
        """Retorna o contato quando há apenas um."""
        return self.contatos[0] if len(self.contatos) == 1 else None
    
    @property
    def empresa(self) -> Optional[Empresa]:
        """Retorna a empresa quando há apenas uma."""
        return self.empresas[0] if len(self.empresas) == 1 else None
    
    @property
    def precisa_clarificacao(self) -> bool:
        """Indica se precisa perguntar algo ao usuário para identificar."""
        return self.status in (StatusIdentificacao.NOVO, StatusIdentificacao.MULTIPLO)


def normalizar_telefone(telefone: str) -> str:
    """
    Normaliza telefone removendo caracteres não numéricos e prefixos.
    
    Exemplos:
        'whatsapp:+5511999999999' -> '+5511999999999'
        '(11) 99999-9999' -> '11999999999'
    """
    if not telefone:
        return ""
    
    tel = telefone.strip()
    
    # Remove prefixo whatsapp:
    tel = re.sub(r"^whatsapp:", "", tel, flags=re.IGNORECASE)
    
    # Mantém apenas dígitos e +
    tel = re.sub(r"[^\d+]", "", tel)
    
    return tel


def identificar_por_telefone(db: Session, telefone: str) -> ResultadoIdentificacao:
    """
    Busca todos os contatos vinculados a um telefone e suas empresas.
    
    Args:
        db: Sessão SQLAlchemy
        telefone: Telefone do remetente (qualquer formato)
    
    Returns:
        ResultadoIdentificacao com status e contatos/empresas encontrados.
    """
    tel_norm = normalizar_telefone(telefone)
    logger.debug(f"[Identificador] Buscando telefone normalizado: {tel_norm}")
    
    # Busca contatos por telefone (pode haver variações de formato salvos)
    # Estratégia: buscar pelo telefone normalizado E pelo original
    contatos = (
        db.query(Contato)
        .filter(Contato.telefone.in_([tel_norm, telefone]))
        .all()
    )
    
    # Se não achou pelo match exato, tenta por "contains" dos últimos 9 dígitos
    if not contatos and len(tel_norm) >= 9:
        sufixo = tel_norm[-9:]
        contatos = (
            db.query(Contato)
            .filter(Contato.telefone.like(f"%{sufixo}"))
            .all()
        )
    
    if not contatos:
        return ResultadoIdentificacao(
            status=StatusIdentificacao.NOVO,
            contatos=[],
            empresas=[],
        )
    
    empresas_por_id = {c.empresa_id: c.empresa for c in contatos if c.empresa}
    empresas = list(empresas_por_id.values())
    
    if len(contatos) > 1 and len(empresas) > 1:
        return ResultadoIdentificacao(
            status=StatusIdentificacao.MULTIPLO,
            contatos=contatos,
            empresas=empresas,
        )
    
    if not empresas:
        return ResultadoIdentificacao(
            status=StatusIdentificacao.SEM_EMPRESA,
            contatos=contatos,
            empresas=[],
        )
    
    return ResultadoIdentificacao(
        status=StatusIdentificacao.UNICO,
        contatos=contatos,
        empresas=empresas,
    )


def criar_contato(
    db: Session,
    telefone: str,
    empresa: Optional[Empresa] = None,
    nome: Optional[str] = None,
    email: Optional[str] = None,
    cargo: Optional[str] = None,
) -> Contato:
    """
    Cria um novo contato, vinculado ou não a uma empresa.
    
    Nota: Por enquanto empresa_id é obrigatório no modelo.
    Se vier None, precisaremos criar uma empresa "placeholder" ou
    ajustar o modelo para permitir nullable. Ver discussão no README.
    """
    if empresa is None:
        raise ValueError(
            "Contato requer empresa. "
            "Se empresa ainda desconhecida, use criar_contato_sem_empresa()."
        )
    
    contato = Contato(
        empresa_id=empresa.id,
        telefone=normalizar_telefone(telefone),
        nome=nome,
        email=email,
        cargo=cargo,
    )
    db.add(contato)
    db.commit()
    db.refresh(contato)
    
    logger.info(
        f"[Identificador] Contato criado: id={contato.id} "
        f"telefone={contato.telefone} empresa={empresa.nome}"
    )
    return contato
