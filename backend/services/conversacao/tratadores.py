"""
Tratadores de resposta: *como ler* a resposta a uma pergunta que o sistema fez.

Terceira peça da pilha de perguntas pendentes (ver `pilha.py`): o Planejador decide *o
que* perguntar (`campos_pendentes()`), o Registro guarda *o que foi perguntado*
(`PerguntaPendente`) e o Tratador diz se a mensagem do cliente responde àquela pergunta.

Contrato: o tratador **interpreta e valida, não grava**. Devolve uma `Leitura`
(reconheceu, não reconheceu ou inválido, mais o valor já tipado) e quem persiste é a
pilha, pelo destino que a definição da pergunta declara. Motivos: manter este módulo e
`catalogo_campos.py` livres de ORM, deixar o mesmo tratador servir destinos diferentes, e
validar antes de escrever.

`discriminante` é o poder de a resposta se identificar sozinha (decisão D2): um CPF, uma
data por extenso ou um nome de software reconhecido só podem responder a uma pergunta,
então casam em qualquer posição da pilha. "sim", "50" ou texto livre podem responder a
qualquer coisa, então só casam com o topo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Mapping, Optional

from services.classificador import EntidadesExtraidas, Intencao
from services.cpf.validacao import parse_data_nascimento


class StatusLeitura(str, Enum):
    RECONHECEU = "reconheceu"
    NAO_RECONHECEU = "nao_reconheceu"
    # Tem a forma de uma resposta, mas o valor não serve (ex.: data no futuro para
    # data de nascimento). Conta como tentativa de captura falha (D3).
    INVALIDO = "invalido"


@dataclass(frozen=True)
class Leitura:
    status: StatusLeitura
    valor: Any = None
    # A resposta ocupa só um pedaço da mensagem e deixa o resto livre para outra
    # pergunta: "sim, biometria" confirma o nome (o "sim") e escolhe o modelo. Uma
    # leitura parcial não disputa com as outras na resolução de ambiguidade.
    parcial: bool = False
    # O pedaço que a leitura parcial consumiu, quando dá para dizer qual ("sim"). Se
    # outra pergunta aberta também aceitaria esse pedaço, não há como saber de quem ele é.
    trecho: Optional[str] = None

    @property
    def reconheceu(self) -> bool:
        return self.status == StatusLeitura.RECONHECEU


NAO_RECONHECEU = Leitura(StatusLeitura.NAO_RECONHECEU)


@dataclass(frozen=True)
class EntradaTratador:
    """O que um tratador pode olhar: a mensagem, a classificação dela e os dados que a
    pergunta guardou ao ser feita (ex.: o nome de perfil oferecido)."""

    conteudo: str
    intencoes: tuple[Intencao, ...]
    entidades: EntidadesExtraidas = field(default_factory=EntidadesExtraidas)
    dados: Mapping[str, Any] = field(default_factory=dict)


# Intenções que nunca impedem uma mensagem de ser resposta: "não reconheci nada" e
# "oi" na frente da resposta.
_INTENCOES_NEUTRAS = frozenset({Intencao.DESCONHECIDO, Intencao.SAUDACAO})


class Tratador:
    """Base. `intencoes_aceitas` é a versão por tratador do antigo
    `_INTENCOES_RESPOSTA_POR_CAMPO`: uma intenção reconhecida fora delas ("quero
    orçamento" repetido, uma dúvida) significa que a mensagem é sobre outra coisa e não
    deve ser sequestrada como resposta."""

    nome: str = "tratador"
    discriminante: bool = False
    intencoes_aceitas: frozenset[Intencao] = frozenset()

    def aceita_intencoes(self, entrada: EntradaTratador) -> bool:
        """A mensagem pode ser uma resposta a esta pergunta?"""
        return set(entrada.intencoes) <= (_INTENCOES_NEUTRAS | self.intencoes_aceitas)

    def conta_tentativa(self, entrada: EntradaTratador) -> bool:
        """Uma mensagem que este tratador não leu conta como tentativa de captura falha
        (D3)? Por padrão, só se ela podia ser a resposta: uma dúvida ou um pedido de
        outro assunto não é tentativa de responder."""
        return self.aceita_intencoes(entrada)

    def interpretar(self, entrada: EntradaTratador) -> Leitura:
        if not (entrada.conteudo or "").strip() or not self.aceita_intencoes(entrada):
            return NAO_RECONHECEU
        return self._interpretar(entrada)

    def _interpretar(self, entrada: EntradaTratador) -> Leitura:
        raise NotImplementedError


# A negação é avaliada antes do afirmativo de propósito: `_RE_SIM` contém "quero", então
# testar o sim primeiro fazia "não quero" ser lido como "sim".
_RE_SIM = re.compile(r"\b(sim|s|claro|ok|parece|interesse|quero|pode ser)\b", re.IGNORECASE)
_RE_NAO = re.compile(r"\b(n[aã]o|n)\b", re.IGNORECASE)


class SimNao(Tratador):
    """Resposta sim/não. A intenção classificada é evidência primária: o classificador
    já reconhece as formas isoladas ("sim", "ok", "isso mesmo", "não") com regras
    ancoradas. Os regexes locais cobrem as formas embutidas numa frase maior ("sim,
    temos interesse"), que o classificador deixa como DESCONHECIDO."""

    nome = "sim_nao"
    intencoes_aceitas = frozenset({Intencao.CONFIRMAR, Intencao.NEGAR})

    def _interpretar(self, entrada: EntradaTratador) -> Leitura:
        if Intencao.NEGAR in entrada.intencoes:
            return Leitura(StatusLeitura.RECONHECEU, "não")
        if Intencao.CONFIRMAR in entrada.intencoes:
            return Leitura(StatusLeitura.RECONHECEU, "sim")
        if _RE_NAO.search(entrada.conteudo):
            return Leitura(StatusLeitura.RECONHECEU, "não")
        if _RE_SIM.search(entrada.conteudo):
            return Leitura(StatusLeitura.RECONHECEU, "sim")
        return NAO_RECONHECEU


_RE_NUMERO_SOLTO = re.compile(r"\b(\d{1,6})\b")


class Numero(Tratador):
    """Um número solto ("80", "umas 30"). Fora de `[minimo, maximo]` é inválido."""

    nome = "numero"

    def __init__(self, minimo: int = 1, maximo: int = 99999):
        self.minimo = minimo
        self.maximo = maximo

    def _interpretar(self, entrada: EntradaTratador) -> Leitura:
        match = _RE_NUMERO_SOLTO.search(entrada.conteudo)
        if not match:
            return NAO_RECONHECEU
        valor = int(match.group(1))
        if not self.minimo <= valor <= self.maximo:
            return Leitura(StatusLeitura.INVALIDO, valor)
        return Leitura(StatusLeitura.RECONHECEU, str(valor))


_RE_SOFTWARE_NENHUM = re.compile(r"\b(n[aã]o|nenhum)\b", re.IGNORECASE)


class Software(Tratador):
    """Nome de software em texto livre, ou a sentinela "nenhum" quando o cliente nega
    ter um. Aceito livremente (ao contrário de modelo, o campo não exige catálogo).

    NEGAR conta como "nenhum" e não é refinamento: o classificador reconhece como NEGAR
    também "errado" e "incorreto", e sem isso um "errado" era gravado **como se fosse o
    nome do software do cliente**, indo parar no resumo e no handoff ao vendedor."""

    nome = "software"
    intencoes_aceitas = frozenset({Intencao.NEGAR})

    def _interpretar(self, entrada: EntradaTratador) -> Leitura:
        texto = entrada.conteudo.strip()
        if Intencao.NEGAR in entrada.intencoes or _RE_SOFTWARE_NENHUM.search(texto):
            return Leitura(StatusLeitura.RECONHECEU, "nenhum")
        return Leitura(StatusLeitura.RECONHECEU, texto)


class SinalDeModelo(Tratador):
    """Modelo do produto. Reconhece quando a mensagem traz sinal de modelo (marca,
    aplicação, tecnologia, atributo), que é discriminante: só a pergunta de modelo quer
    isso. A resolução contra o catálogo, que precisa do banco, fica com
    `FinalizandoState._resolver_modelo` (F2); por isso a pilha não grava este campo."""

    nome = "sinal_de_modelo"
    discriminante = True

    def aceita_intencoes(self, entrada: EntradaTratador) -> bool:
        return True

    def conta_tentativa(self, entrada: EntradaTratador) -> bool:
        # Quem conta é a resolução contra o catálogo: tentativa é sinal de modelo sem
        # correspondência, não mensagem sem sinal.
        return False

    def _interpretar(self, entrada: EntradaTratador) -> Leitura:
        e = entrada.entidades
        if e.marca or e.aplicacao or e.tipo_leitor_mencionado or e.atributos:
            return Leitura(StatusLeitura.RECONHECEU)
        return NAO_RECONHECEU


_DATA_MINIMA = date(1900, 1, 1)


class DataNascimento(Tratador):
    """Data de nascimento. Discriminante: uma data por extenso só responde a uma
    pergunta de data. Futuro ou antes de 1900 é inválido."""

    nome = "data_nascimento"
    discriminante = True
    intencoes_aceitas = frozenset({Intencao.FORNECER_DATA_NASCIMENTO})

    def _interpretar(self, entrada: EntradaTratador) -> Leitura:
        data = None
        if entrada.entidades.datas_nascimento:
            try:
                data = date.fromisoformat(entrada.entidades.datas_nascimento[0])
            except ValueError:
                data = None
        data = data or parse_data_nascimento(entrada.conteudo)
        if data is None:
            return NAO_RECONHECEU
        if not _DATA_MINIMA <= data < date.today():
            return Leitura(StatusLeitura.INVALIDO, data)
        return Leitura(StatusLeitura.RECONHECEU, data)


def entrada_de(
    conteudo: str,
    intencoes,
    entidades: Optional[EntidadesExtraidas] = None,
    dados: Optional[Mapping[str, Any]] = None,
) -> EntradaTratador:
    return EntradaTratador(
        conteudo=conteudo or "",
        intencoes=tuple(intencoes),
        entidades=entidades or EntidadesExtraidas(),
        dados=dados or {},
    )
