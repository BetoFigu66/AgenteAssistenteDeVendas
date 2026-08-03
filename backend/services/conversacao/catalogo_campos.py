"""
Catálogo de campos de qualificação (MVP Continuidade, jul/2026 — passos B1-B4).

Espelha as fichas `CAMPO-xxx` de
`artefatos/analista_de_requisitos/catalogo_conversacao/campos/` em definições
declarativas que o motor de fases (Fase C do plano de MVP — `campos_pendentes()`) vai consumir.

Este módulo não conhece banco de dados nem SQLAlchemy: `se_aplica` recebe um snapshot dos
valores já capturados (chave -> valor, ex.: vindo de `AtendimentoInfo`) em vez de objetos
ORM, para manter o catálogo desacoplado da camada de persistência — por isso `Pergunta`
não tem métodos de captura de resposta nem de renderização de contexto (essas partes são
ORM/`ContextoAcao`-aware e vivem em `services/conversacao/estados/finalizando.py`, que já
lida com banco desde a Etapa 1 do redesenho State pattern; ver
`docs/arquitetura_motor_conversacao_2026-07.md`).
"""

from __future__ import annotations

from typing import ClassVar, Mapping

from services.respostas import MensagemId

Valores = Mapping[str, str]

# Destinos possíveis de `Pergunta.destino` — onde a Fase C deve gravar o valor capturado.
DESTINO_ATENDIMENTO_INFO = "atendimento_info"
DESTINO_ITEM_ATENDIMENTO_MODELO_ID = "item_atendimento.modelo_id"


class Pergunta:
    """Definição de um campo de qualificação — espelha uma ficha `CAMPO-xxx`.

    `se_aplica` é o único ponto de variação por subclasse (substitui o antigo campo
    `aplicavel: Callable` de `CampoDef` por um método real — a mesma ideia, agora como
    polimorfismo de verdade em vez de um callable solto)."""

    id_catalogo: ClassVar[str]
    chave: ClassVar[str]
    produtos_aplicaveis: ClassVar[frozenset[str]]
    pergunta: ClassVar[str]
    ordem: ClassVar[int]
    mensagem_id: ClassVar[MensagemId]
    destino: ClassVar[str] = DESTINO_ATENDIMENTO_INFO
    """Onde o valor capturado deve ser persistido (Fase C):

    - `DESTINO_ATENDIMENTO_INFO` (padrão) — grava em `AtendimentoInfo` (chave-valor).
    - `DESTINO_ITEM_ATENDIMENTO_MODELO_ID` — o valor precisa resolver para uma linha
      real do catálogo (`Modelo`) e gravar em `ItemAtendimento.modelo_id`, nunca texto
      livre. Ver risco/decisão #1 em §8 do plano de MVP: `produto` (categoria) já vai
      para `ItemAtendimento`; o modelo específico segue a mesma lógica.
    """
    obrigatorio: ClassVar[bool] = True
    """Se `False`, o campo é perguntado **no máximo uma vez** (marcado como
    "perguntado" — ver `chave_perguntado()`) e, a partir daí, deixa de bloquear
    `campos_pendentes()`/o resumo final, mesmo sem resposta do cliente. Usado para
    perguntas de alerta/orientação que não fazem parte dos dados obrigatórios do
    orçamento (ex.: `PerguntaHomologadoSoftware` — REQ-002.14C/15)."""

    def _aplicavel(self, tipo_produto: str, valores: Valores) -> bool:
        """Hook de aplicabilidade condicional — default sempre aplicável dentro de
        `produtos_aplicaveis`; subclasses sobrescrevem quando a pergunta só faz sentido
        dado o que já foi capturado (ex.: `PerguntaFaixaFuncionarios`)."""
        return True

    def se_aplica(self, tipo_produto: str, valores: Valores) -> bool:
        """True se o campo é relevante para `tipo_produto`, dado o que já foi capturado em `valores`."""
        if tipo_produto not in self.produtos_aplicaveis:
            return False
        return self._aplicavel(tipo_produto, valores)


def chave_perguntado(campo: Pergunta) -> str:
    """Chave de `AtendimentoInfo` usada para marcar que um campo **não obrigatório**
    (`Pergunta.obrigatorio = False`) já foi perguntado ao cliente ao menos uma vez —
    independente de ter recebido resposta. Ver `Pergunta.obrigatorio`."""
    return f"{campo.chave}__perguntado"


# ---------------------------------------------------------------------------
# CAMPO-modelo
# artefatos/analista_de_requisitos/catalogo_conversacao/campos/CAMPO-modelo.md
# ---------------------------------------------------------------------------
#
# A resposta do cliente deve sempre resolver para uma linha real do catálogo
# (`Modelo`) — nunca texto livre. Sem
# correspondência reconhecível após 1-2 tentativas de esclarecimento
# (REQ-002.21), o sistema escala para modo atendente (`escalar_humano`) em vez
# de gravar o texto do cliente. Essa resolução/validação é implementada em
# `estados/finalizando.py::FinalizandoState._resolver_modelo` (F2), não aqui:
# este módulo só declara o campo.


class PerguntaModelo(Pergunta):
    id_catalogo = "CAMPO-modelo"
    chave = "modelo_produto"
    produtos_aplicaveis = frozenset({
        "relogio_ponto",
        "catraca",
        "cancela",
        "leitor_facial",
        "leitor_biometrico",
        "camera",
        "controle_de_acesso",
        "controle_por_cartao",
        "bastao_de_ronda",
        "roteador",
    })
    pergunta = (
        "Qual modelo ou tecnologia você prefere? "
        "(ex.: cartográfico, eletrônico, cartão, biometria, facial, QR Code)"
    )
    ordem = 10
    destino = DESTINO_ITEM_ATENDIMENTO_MODELO_ID
    mensagem_id = MensagemId.PEDIR_MODELO


CAMPO_MODELO = PerguntaModelo()


# ---------------------------------------------------------------------------
# CAMPO-software-ponto
# artefatos/analista_de_requisitos/catalogo_conversacao/campos/CAMPO-software-ponto.md
# ---------------------------------------------------------------------------


class PerguntaSoftwarePonto(Pergunta):
    id_catalogo = "CAMPO-software-ponto"
    chave = "software_controle_ponto"
    produtos_aplicaveis = frozenset({"relogio_ponto"})
    pergunta = "Qual software de ponto vocês usam hoje? (ex.: Domínio, Alterdata, TOTVS, ou nenhum)"
    ordem = 20
    mensagem_id = MensagemId.PEDIR_SOFTWARE_PONTO


CAMPO_SOFTWARE_PONTO = PerguntaSoftwarePonto()


# ---------------------------------------------------------------------------
# CAMPO-software-acesso
# Controle de acesso: software já usado pelo cliente.
# ---------------------------------------------------------------------------


class PerguntaSoftwareAcesso(Pergunta):
    id_catalogo = "CAMPO-software-acesso"
    chave = "software_controle_acesso"
    produtos_aplicaveis = frozenset({
        "catraca",
        "cancela",
        "controle_de_acesso",
        "controle_por_cartao",
    })
    pergunta = (
        "Vocês já usam algum software de controle de acesso? "
        "(ex.: EVO, Pacto, SCA, Panobianco, Sky, outro, ou nenhum)"
    )
    ordem = 20
    mensagem_id = MensagemId.PEDIR_SOFTWARE_ACESSO


CAMPO_SOFTWARE_ACESSO = PerguntaSoftwareAcesso()


# ---------------------------------------------------------------------------
# CAMPO-interesse-sistema-nuvem
# Quando o cliente não tem software de acesso, pergunta se quer adquirir um
# sistema na nuvem — regra do atendente Inforrel.
# ---------------------------------------------------------------------------


class PerguntaInteresseSistemaNuvem(Pergunta):
    id_catalogo = "CAMPO-interesse-sistema-nuvem"
    chave = "interesse_sistema_nuvem"
    produtos_aplicaveis = frozenset({
        "catraca",
        "cancela",
        "controle_de_acesso",
        "controle_por_cartao",
    })
    pergunta = "Têm interesse em adquirir um sistema de controle de acesso na nuvem?"
    ordem = 25
    mensagem_id = MensagemId.PEDIR_INTERESSE_SISTEMA_NUVEM

    def _aplicavel(self, tipo_produto: str, valores: Valores) -> bool:
        """Aplica apenas se o cliente declarou não ter software de controle de acesso."""
        return valores.get("software_controle_acesso", "").strip().lower() == "nenhum"


CAMPO_INTERESSE_SISTEMA_NUVEM = PerguntaInteresseSistemaNuvem()


# ---------------------------------------------------------------------------
# CAMPO-faixa-funcionarios
# artefatos/analista_de_requisitos/catalogo_conversacao/campos/CAMPO-faixa-funcionarios.md
# ---------------------------------------------------------------------------
#
# Campo transversal: a faixa de pessoas que usarão o produto é relevante para
# orçamento independente do tipo (relógio de ponto, catraca, leitor facial etc.).
# Para catraca sem software e sem interesse em nuvem, a faixa não é perguntada.


class PerguntaFaixaFuncionarios(Pergunta):
    id_catalogo = "CAMPO-faixa-funcionarios"
    chave = "faixa_funcionarios"
    produtos_aplicaveis = frozenset({
        "relogio_ponto",
        "catraca",
        "cancela",
        "leitor_facial",
        "leitor_biometrico",
        "camera",
        "controle_de_acesso",
        "controle_por_cartao",
        "bastao_de_ronda",
        "roteador",
    })
    pergunta = "Qual a faixa de pessoas que vão usar {produto}?"
    ordem = 30
    mensagem_id = MensagemId.PEDIR_FAIXA_FUNCIONARIOS

    def _aplicavel(self, tipo_produto: str, valores: Valores) -> bool:
        """Regras de negócio para perguntar a faixa de pessoas:

        - Relógio de ponto sem software de ponto: sempre pergunta.
        - Catraca/cancela/controle de acesso/controle por cartão: só pergunta se
          não há software de acesso e há interesse em sistema na nuvem (senão o
          software já usado ou a ausência de interesse já dimensionam o projeto).
        - Demais produtos (leitor, câmera, bastão de ronda, roteador): sempre
          pergunta — não têm fluxo de software/nuvem que já dimensione o projeto
          (CAMPO_SOFTWARE_ACESSO/CAMPO_INTERESSE_SISTEMA_NUVEM não se aplicam a
          eles), então a condição de software nunca ficaria satisfeita.
        """
        tipo = tipo_produto.strip().lower()
        if tipo == "relogio_ponto":
            return valores.get("software_controle_ponto", "").strip().lower() == "nenhum"

        if tipo not in CAMPO_SOFTWARE_ACESSO.produtos_aplicaveis:
            return True

        software_acesso = valores.get("software_controle_acesso", "").strip().lower()
        interesse_nuvem = valores.get("interesse_sistema_nuvem", "").strip().lower()
        return software_acesso == "nenhum" and interesse_nuvem == "sim"


CAMPO_FAIXA_FUNCIONARIOS = PerguntaFaixaFuncionarios()


# ---------------------------------------------------------------------------
# CAMPO-quantidade
# Quantidade de equipamentos. Não aplica a relógio de ponto (onde a faixa de
# pessoas já dimensiona a necessidade).
# ---------------------------------------------------------------------------


class PerguntaQuantidade(Pergunta):
    id_catalogo = "CAMPO-quantidade"
    chave = "quantidade"
    produtos_aplicaveis = frozenset({
        "catraca",
        "cancela",
        "leitor_facial",
        "leitor_biometrico",
        "camera",
        "controle_de_acesso",
        "controle_por_cartao",
        "bastao_de_ronda",
        "roteador",
    })
    pergunta = "Quantas unidades você precisa?"
    ordem = 40
    mensagem_id = MensagemId.PEDIR_QUANTIDADE

    def _aplicavel(self, tipo_produto: str, valores: Valores) -> bool:
        """Quantidade de equipamentos é perguntada para todos os produtos de acesso
        (catraca, cancela, leitor, câmera, controle etc.). Não aplica a relógio de ponto."""
        return tipo_produto.strip().lower() != "relogio_ponto"


CAMPO_QUANTIDADE = PerguntaQuantidade()


# ---------------------------------------------------------------------------
# CAMPO-homologado-software
# REQ-002.14C/15: quando o cliente já usa QUALQUER software de controle de
# acesso (reconhecido — EVO/Pacto/SCA/franquias como Panobianco/Sky — ou não),
# o sistema exibe um alerta/orientação perguntando se o cliente já verificou a
# homologação entre o modelo desejado e aquele software. É apenas um
# alerta: a resposta é opcional e NÃO bloqueia a qualificação
# (`Pergunta.obrigatorio = False`) — o sistema só controla que a pergunta foi
# feita (ver `chave_perguntado()`), reforçando a importância de o cliente
# confirmar a compatibilidade antes da compra.
# ---------------------------------------------------------------------------


class PerguntaHomologadoSoftware(Pergunta):
    id_catalogo = "CAMPO-homologado-software"
    chave = "homologado_software"
    produtos_aplicaveis = frozenset({
        "catraca",
        "cancela",
        "controle_de_acesso",
        "controle_por_cartao",
    })
    pergunta = (
        "Antes de fechar o pedido, é importante confirmar com o fornecedor do "
        "software {software} se o modelo de catraca/leitor que você está "
        "adquirindo é homologado/compatível. Você já verificou isso?"
    )
    ordem = 35
    obrigatorio = False
    mensagem_id = MensagemId.PEDIR_HOMOLOGADO_SOFTWARE

    def _aplicavel(self, tipo_produto: str, valores: Valores) -> bool:
        """Aplica sempre que o cliente já tiver algum software de controle de acesso
        real informado (`software_controle_acesso` diferente de vazio/"nenhum"),
        reconhecido no catálogo ou não — REQ-002.14C (conhecido) e REQ-002.15 (outro)."""
        software = valores.get("software_controle_acesso", "").strip().lower()
        return bool(software) and software != "nenhum"


CAMPO_HOMOLOGADO_SOFTWARE = PerguntaHomologadoSoftware()


CAMPOS: dict[str, Pergunta] = {
    campo.chave: campo
    for campo in (
        CAMPO_MODELO,
        CAMPO_SOFTWARE_PONTO,
        CAMPO_SOFTWARE_ACESSO,
        CAMPO_INTERESSE_SISTEMA_NUVEM,
        CAMPO_FAIXA_FUNCIONARIOS,
        CAMPO_QUANTIDADE,
        CAMPO_HOMOLOGADO_SOFTWARE,
    )
}


def campos_do_produto(tipo_produto: str) -> list[Pergunta]:
    """Retorna as `Pergunta` cadastradas para um tipo de produto, na ordem de exibição sugerida.

    Não filtra por já-capturado/aplicável — isso é responsabilidade de
    `campos_pendentes()` (Fase C), que cruza este catálogo com o que já foi
    coletado no atendimento.
    """
    return sorted(
        (campo for campo in CAMPOS.values() if tipo_produto in campo.produtos_aplicaveis),
        key=lambda campo: campo.ordem,
    )
