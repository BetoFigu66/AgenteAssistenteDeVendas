"""Motor de execução de um cenário: aloca um telefone do pool, manda os turnos
em sequência pro backend real, compara a resposta observada contra o histórico
de respostas aceitas daquele turno, e registra o resultado.

Pendência de revisão (resposta não reconhecida) é delegada a um `revisor`
(callback) — o CLI implementa isso como pergunta no terminal; trocar por outra
interface (ex.: web) não exige tocar este módulo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional

from cliente_backend import ClienteBackend
from models import (
    Cenario,
    Execucao,
    NumeroTeste,
    RespostaAceita,
    ResultadoTurno,
    StatusExecucao,
    StatusNumero,
    Veredito,
)
from sqlalchemy.orm import Session


@dataclass
class DecisaoRevisor:
    aceitar: bool
    motivo: Optional[str] = None


# (mensagem_enviada, resposta_observada, respostas_ja_aceitas) -> decisão
Revisor = Callable[[str, str, list[str]], DecisaoRevisor]

MOTIVO_NAO_INTERATIVO = "nao_interativo"


def revisor_nao_interativo(
    mensagem_enviada: str, resposta_observada: str, aceitas: list[str]
) -> DecisaoRevisor:
    """Revisor de varredura: rejeita tudo que não bate com uma resposta já aceita,
    sem perguntar nada.

    Serve para a primeira passada de uma bateria nova, em que *toda* resposta é
    desconhecida e o modo interativo viraria dezenas de prompts seguidos. O que
    foi observado fica gravado em `resultados_turno`, então a segunda passada
    (interativa) revisa só o que divergiu.
    """
    return DecisaoRevisor(aceitar=False, motivo=MOTIVO_NAO_INTERATIVO)


class TelefoneIndisponivelError(Exception):
    pass


def _alocar_telefone(db: Session, cenario_id: int) -> NumeroTeste:
    numero = (
        db.query(NumeroTeste)
        .filter_by(status=StatusNumero.LIVRE)
        .with_for_update(skip_locked=True)
        .first()
    )
    if numero is None:
        raise TelefoneIndisponivelError(
            "Nenhum número livre no pool — cadastre mais com `cli.py numeros-adicionar`."
        )
    numero.status = StatusNumero.EM_USO
    numero.cenario_atual_id = cenario_id
    db.commit()
    return numero


def _liberar_telefone(db: Session, numero: NumeroTeste, cliente: ClienteBackend) -> None:
    cliente.limpar_telefone(numero.numero)
    numero.status = StatusNumero.LIVRE
    numero.cenario_atual_id = None
    db.commit()


def rodar_cenario(db: Session, cenario: Cenario, cliente: ClienteBackend, revisor: Revisor) -> Execucao:
    numero = _alocar_telefone(db, cenario.id)
    execucao = Execucao(cenario_id=cenario.id, numero_usado=numero.numero, status=StatusExecucao.RODANDO)
    db.add(execucao)
    db.commit()

    try:
        for turno in cenario.turnos:
            resposta_texto = cliente.enviar_mensagem(numero.numero, turno.mensagem_enviada)
            if not resposta_texto:
                resposta_texto = cliente.buscar_mensagem_pendente(numero.numero) or ""

            aceitas_ativas = [r.texto for r in turno.respostas_aceitas if r.ativo]

            if resposta_texto in aceitas_ativas:
                veredito = Veredito.ACEITO_AUTOMATICO
                decidido_por = None
                decidido_em = None
            else:
                decisao = revisor(turno.mensagem_enviada, resposta_texto, aceitas_ativas)
                decidido_por = decisao.motivo or "revisao_manual"
                decidido_em = datetime.now(timezone.utc)
                if decisao.aceitar:
                    db.add(RespostaAceita(turno_id=turno.id, texto=resposta_texto, criado_por=decidido_por))
                    veredito = Veredito.ACEITO_MANUAL
                else:
                    veredito = Veredito.REJEITADO

            db.add(
                ResultadoTurno(
                    execucao_id=execucao.id,
                    turno_id=turno.id,
                    mensagem_enviada=turno.mensagem_enviada,
                    resposta_observada=resposta_texto,
                    veredito=veredito,
                    decidido_por=decidido_por,
                    decidido_em=decidido_em,
                )
            )
            db.commit()

        execucao.status = StatusExecucao.CONCLUIDA
    except Exception:
        execucao.status = StatusExecucao.ABORTADA
        raise
    finally:
        execucao.finalizado_em = datetime.now(timezone.utc)
        db.commit()
        _liberar_telefone(db, numero, cliente)

    return execucao
