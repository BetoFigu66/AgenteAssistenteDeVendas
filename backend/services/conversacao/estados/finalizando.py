"""`FinalizandoState` — comportamento da fase Finalizando (coleta ativa F1-F4, handoff G1-G3).

Todo o pipeline que antes vivia em `ProcessadorMensagem` (F1-F4/G1-G3) mora aqui agora —
essa era a violação de GRASP Information Expert identificada em code review: quem "sabe"
processar Finalizando deve ser uma classe da própria fase, não o orquestrador genérico.
Infra genuinamente cross-cutting (`GeradorRespostas`, persistência de `AtendimentoInfo`,
escalonamento) continua em `ProcessadorMensagem` — chamada aqui via `ctx.processador`, como
as Regras já faziam. Categoria_pergunta (dúvida produto/preço/fora de contexto) não é
infra cross-cutting — mora em `categoria_pergunta.py` (achado de review D02/D03), chamada
aqui via `responder_categoria_pergunta(intencao, ctx)`.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

from models import (
    Atendimento,
    AtributoAdicionalModelo,
    FaseAtendimento,
    ItemAtendimento,
    Modelo,
    ModoOperacao,
    MotivoEscalonamento,
    Produto,
    TipoEventoAtendimento,
)
from sqlalchemy.orm import Session

from services import atendimentos as atendimentos_svc
from services.classificador import Intencao
from services.conversacao.acoes import ContextoAcao
from services.conversacao.campos_pendentes import PERGUNTA_PRIORITARIA_CHAVE, campos_pendentes
from services.conversacao.catalogo_campos import (
    CAMPO_FAIXA_FUNCIONARIOS,
    CAMPO_HOMOLOGADO_SOFTWARE,
    CAMPO_INTERESSE_SISTEMA_NUVEM,
    CAMPO_MODELO,
    CAMPO_QUANTIDADE,
    CAMPO_SOFTWARE_ACESSO,
    CAMPO_SOFTWARE_PONTO,
    Pergunta,
    chave_perguntado,
)
from services.conversacao.categoria_pergunta import responder_categoria_pergunta
from services.respostas import MensagemId, RespostaGerada

from .base import EstadoAtendimento

# Fase F (F2): chave de AtendimentoInfo que conta tentativas sem correspondência de
# modelo_produto; após _MODELO_MAX_TENTATIVAS, escala para atendimento humano em vez de
# continuar perguntando (REQ-002.21, CAMPO-modelo — nunca aceita texto livre como modelo).
_MODELO_TENTATIVAS_CHAVE = "modelo_tentativas_falhas"
_MODELO_MAX_TENTATIVAS = 2

# Fase F (F1): captura "solta" para a pergunta pendente atual quando os extratores por
# palavra-gatilho (D3/D4) não reconheceram nada — ex.: "80" sozinho, ou um nome de
# software fora de `_SOFTWARES_PONTO_CONHECIDOS`. Só entra em jogo quando a intenção
# classificada é DESCONHECIDO (nenhuma regra bateu) — ver `_capturar_resposta_direta_pendente`.
_SOFTWARE_NENHUM_REGEX = re.compile(r"\b(n[aã]o|nenhum)\b", re.IGNORECASE)
_NUMERO_SOLTO_REGEX = re.compile(r"\b(\d{1,5})\b")
_RESPOSTA_SIM_REGEX = re.compile(r"\b(sim|s|claro|ok|parece|interesse|quero|pode ser)\b", re.IGNORECASE)
_RESPOSTA_NAO_REGEX = re.compile(r"\b(n[aã]o|n)\b", re.IGNORECASE)

# Fase G (G1): marca que o resumo (F4) já foi apresentado — um CONFIRMAR só conclui o
# handoff se for reply a um resumo que o cliente de fato viu; sem isso, a primeira
# mensagem "solta" a chegar depois de tudo capturado (ex.: um "ok" de preenchimento) seria
# tratada como confirmação de um resumo que nunca foi mostrado.
_RESUMO_APRESENTADO_CHAVE = "resumo_finalizando_apresentado"

# Intenções de "dúvida pura" (categoria_pergunta) que, se batidas durante a coleta ativa, devem
# ser respondidas via RAG/QA sem perder o progresso (F3) — ver `_retomar_apos_duvida`.
_INTENCOES_RAG = frozenset({"perguntar_produto", "perguntar_preco", "fora_contexto"})

_LABEL_PRODUTO_PERGUNTA = {
    "catraca": "a catraca",
    "relogio_ponto": "o relógio de ponto",
    "cancela": "a cancela",
    "leitor_facial": "o leitor facial",
    "leitor_biometrico": "o leitor biométrico",
    "camera": "a câmera",
    "controle_de_acesso": "o controle de acesso",
    "controle_por_cartao": "o controle por cartão",
    "bastao_de_ronda": "o bastão de ronda",
    "roteador": "o roteador",
}

def _label_tipo_produto(tipo_produto: Optional[str]) -> str:
    """Retorna o nome amigável de um tipo de produto para uso em mensagens."""
    if not tipo_produto:
        return "produto"
    return _LABEL_PRODUTO_PERGUNTA.get(tipo_produto, tipo_produto.replace("_", " "))


def _contexto_para_campo(campo: Pergunta, atendimento: Atendimento) -> Optional[dict]:
    """Contexto adicional para renderizar a pergunta de um campo pendente."""
    tipo_produto = atendimento.tipo_produto_atual()
    if campo.chave == CAMPO_FAIXA_FUNCIONARIOS.chave:
        return {"produto": _label_tipo_produto(tipo_produto)}
    if campo.chave == CAMPO_QUANTIDADE.chave:
        return {"tipo_produto": tipo_produto.replace("_", " ") if tipo_produto else "o equipamento"}
    if campo.chave == CAMPO_HOMOLOGADO_SOFTWARE.chave:
        software = next(
            (info.valor for info in atendimento.informacoes if info.chave == CAMPO_SOFTWARE_ACESSO.chave),
            None,
        )
        return {"software": software or "que vocês já usam"}
    return None


def _normalizar_sem_acento(texto: str) -> str:
    """Remove acentos para comparações case-insensitive em português."""
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    ).lower()


def _produto_ids_por_tipos(db: Session, tipos_produto: list[str]) -> list[int]:
    """Busca produtos ativos cujo nome contenha os tokens do tipo extraído."""
    if not tipos_produto:
        return []
    produtos = db.query(Produto).filter(Produto.ativo.is_(True)).all()
    ids: set[int] = set()
    for tipo in tipos_produto:
        tipo_norm = _normalizar_sem_acento(tipo.replace("_", " "))
        partes = [p for p in tipo_norm.split() if len(p) > 2]
        for produto in produtos:
            desc_norm = _normalizar_sem_acento(produto.descricao)
            if tipo_norm in desc_norm or all(part in desc_norm for part in partes):
                ids.add(produto.id)
    return list(ids)


class FinalizandoState(EstadoAtendimento):
    fase = FaseAtendimento.FINALIZANDO

    async def entrar(
        self,
        ctx: ContextoAcao,
        mensagem_abertura: MensagemId = MensagemId.INICIAR_FINALIZANDO,
        abertura_contexto: Optional[dict] = None,
        primeira_pergunta: Optional[Pergunta] = None,
    ) -> list[tuple[MensagemId, Optional[dict]]]:
        """E1+E3: transita `fase` para Finalizando (se ainda não estiver lá) e decide a
        próxima pergunta. Retorna as partes prontas para `gerar`/`gerar_composta`.

        A mensagem que disparou `PEDIR_ORCAMENTO` já foi processada por
        `_atualizar_infos_atendimento` antes desta chamada (D2/D3/D4) — então, se ela também
        trouxe uma resposta (ex.: "quero orçamento, já uso o Domínio"), `campos_pendentes()`
        já reflete isso e não repete a pergunta correspondente (`nao_perguntar_de_novo`, C3).

        `mensagem_abertura`, `abertura_contexto` e `primeira_pergunta` permitem que fluxos
        específicos (ex.: "vocês vendem X?") substituam a abertura padrão e a primeira
        pergunta do orçamento, sem alterar o catálogo de campos pendentes.
        """
        atendimento = ctx.atendimento
        if atendimento.fase != FaseAtendimento.FINALIZANDO:
            self.transicionar_para(ctx, FaseAtendimento.FINALIZANDO, motivo="PEDIR_ORCAMENTO recebido (E1)")

        pendentes = campos_pendentes(atendimento)
        if not pendentes:
            # Tipo de produto ainda não identificado (mais comum), ou — caso raro nesta
            # fatia — tudo já capturado; F4 vai substituir isto por um resumo real.
            if ctx.dlog:
                ctx.dlog.log("finalizando", "sem campos pendentes ainda → PEDIR_TIPO_PRODUTO")
            return [(MensagemId.PEDIR_TIPO_PRODUTO, None)]

        if primeira_pergunta is not None:
            campo = primeira_pergunta
            ctx.processador._salvar_info_atendimento(
                ctx.db, atendimento.id, PERGUNTA_PRIORITARIA_CHAVE, primeira_pergunta.chave
            )
        else:
            campo = pendentes[0]
        mensagem_id = campo.mensagem_id
        ctx_campo = _contexto_para_campo(campo, atendimento)
        ctx_abertura = abertura_contexto if abertura_contexto is not None else ctx_campo
        if ctx.dlog:
            ctx.dlog.log("finalizando", f"próxima pergunta: {campo.chave} ({mensagem_id.name})")
        return [(mensagem_abertura, ctx_abertura), (mensagem_id, ctx_campo)]

    async def tratamento_principal(self, ctx: ContextoAcao) -> RespostaGerada:
        """F1: loop de coleta ativa — roda a cada mensagem em Finalizando, testando contra
        todas as perguntas pendentes (não só "a próxima"), em vez de rotear só pela
        intenção classificada.

        `_atualizar_infos_atendimento` (D2/D3/D4) já rodou antes desta chamada e capturou o
        que os extratores por palavra-gatilho reconheceram. A partir daqui: (a) tenta
        resolver `modelo_produto` contra o catálogo real (F2) — a extração de
        `tipo_leitor_mencionado` independe da intenção classificada, então roda mesmo se a
        mensagem também parecer uma dúvida; (b) se for dúvida (categoria_pergunta), responde via
        Q&A/RAG e retoma a pergunta pendente (F3); (c) senão, tenta uma captura solta para
        a pergunta pendente atual (F1); (d) recalcula o que falta e pergunta, fecha com o
        resumo (F4), ou — se o resumo já tinha sido apresentado e o cliente confirma —
        conclui o handoff para o time humano (Fase G).
        """
        p = ctx.processador
        atendimento = ctx.atendimento
        resultado_class = ctx.resultado_class

        pendentes_antes = campos_pendentes(atendimento)
        tentou_modelo = bool(
            pendentes_antes
            and pendentes_antes[0].chave == CAMPO_MODELO.chave
            and resultado_class.entidades.tipo_leitor_mencionado
        )

        # F2/F3: se a mensagem for uma dúvida (categoria_pergunta) e não trouxer nenhum sinal
        # NOVO de modelo (marca/aplicação/tecnologia), não tenta resolver modelo usando só
        # sinais antigos já persistidos (ex.: `tecnologia_leitura` capturado numa mensagem
        # anterior) — isso sequestrava perguntas legítimas do cliente (ex.: "pode explicar
        # as diferenças entre as marcas?"), respondendo com MODELO_NAO_RECONHECIDO em vez de
        # tratar a dúvida, e ainda consumia uma tentativa de `_MODELO_MAX_TENTATIVAS`.
        entidades = resultado_class.entidades
        tem_sinal_modelo_fresco = bool(
            entidades.marca or entidades.aplicacao or entidades.tipo_leitor_mencionado or entidades.atributos
        )
        eh_duvida = resultado_class.intencao_principal.value in _INTENCOES_RAG
        if eh_duvida and not tem_sinal_modelo_fresco:
            return await self._retomar_apos_duvida(ctx)

        modelo_nao_reconhecido = await self._resolver_modelo(ctx)
        if atendimento.modo_operacao == ModoOperacao.HUMANO:
            # F2: acabou de escalar por falta de correspondência de modelo — não continua.
            return await p._gerador.gerar(MensagemId.ESCALADO_HUMANO)

        if modelo_nao_reconhecido:
            # F2: modelo não existe no catálogo (1ª tentativa) — informar e reapresentar opções.
            return await p._gerador.gerar(MensagemId.MODELO_NAO_RECONHECIDO)

        if eh_duvida:
            return await self._retomar_apos_duvida(ctx)

        if not tentou_modelo:
            self._capturar_resposta_direta_pendente(ctx)

        pendentes = campos_pendentes(atendimento)
        if not pendentes:
            tipo_produto_conhecido = bool(p._info_atendimento(ctx.db, atendimento.id, "tipos_produto"))
            if not tipo_produto_conhecido:
                # Ainda não sabemos o tipo de produto (não é "tudo capturado" — não dá pra
                # saber o que pedir sem isso) — reapresenta a pergunta inicial.
                if ctx.dlog:
                    ctx.dlog.log("finalizando", "tipo de produto ainda não identificado → PEDIR_TIPO_PRODUTO")
                return await p._gerador.gerar(MensagemId.PEDIR_TIPO_PRODUTO)
            # G1-G3 (confirmação do resumo → handoff) é tratado antes de chegar aqui, como
            # Regra exclusiva própria da fase Finalizando (ver regras_finalizando.py) —
            # se chegamos até este ponto, é porque não era o caso (resumo ainda não
            # apresentado, ou já concluído antes).
            return await self._gerar_resumo(ctx)

        campo = pendentes[0]
        mensagem_id = campo.mensagem_id
        ctx_campo = _contexto_para_campo(campo, atendimento)
        if ctx.dlog:
            ctx.dlog.log("finalizando", f"próxima pergunta pendente: {campo.chave} ({mensagem_id.name})")
        return await p._gerador.gerar(mensagem_id, ctx_campo)

    async def concluir(self, ctx: ContextoAcao) -> RespostaGerada:
        """G1-G3: cliente confirmou o resumo (F4) — transita para `EM_ORCAMENTACAO` e faz o
        handoff para o time humano montar o orçamento de verdade (REQ-004 /
        FASE-criando-orcamento). `modo_operacao = HUMANO` suprime respostas automáticas
        daqui em diante (mesmo mecanismo já usado pelo escalonamento do F2)."""
        atendimento = ctx.atendimento
        self.transicionar_para(ctx, FaseAtendimento.EM_ORCAMENTACAO, motivo="G1-G3: cliente confirmou o resumo")

        modo_anterior = atendimento.modo_operacao.value
        atendimento.modo_operacao = ModoOperacao.HUMANO
        ctx.db.commit()
        atendimentos_svc.registrar_evento_atendimento(
            ctx.db,
            atendimento,
            tipo=TipoEventoAtendimento.MODO_OPERACAO_ALTERADO,
            ator="sistema:motor_conversacao",
            estado_anterior=modo_anterior,
            estado_novo=ModoOperacao.HUMANO.value,
            motivo="Handoff para o time humano montar o orçamento",
        )
        if ctx.dlog:
            ctx.dlog.log(
                "fase",
                f"Finalizando → Em orçamentação (atendimento id={atendimento.id}) — handoff humano",
            )
        return await ctx.processador._gerador.gerar(MensagemId.ORCAMENTO_ENCAMINHADO)

    async def _resolver_modelo(self, ctx: ContextoAcao) -> bool:
        """F2: resolve `modelo_produto` para uma linha real de `Modelo`, ou escala para
        atendimento humano após `_MODELO_MAX_TENTATIVAS` sem correspondência — nunca aceita
        o texto do cliente como modelo (REQ-002.3B, CAMPO-modelo).

        Usa tipo de produto, tecnologia de leitura, marca e aplicação extraídos da
        conversa para desambiguar o catálogo.

        Retorna `True` se houve tentativa sem correspondência (mas sem escalar) — o
        chamador deve usar `MODELO_NAO_RECONHECIDO` em vez de `PEDIR_MODELO`.
        Retorna `False` em todos os outros casos (resolvido, não tentou, ou escalou).
        """
        db = ctx.db
        atendimento = ctx.atendimento
        resultado_class = ctx.resultado_class
        p = ctx.processador
        dlog = ctx.dlog

        pendentes = campos_pendentes(atendimento)
        if not pendentes or pendentes[0].chave != CAMPO_MODELO.chave:
            return False

        entidades = resultado_class.entidades
        tipo_leitor = entidades.tipo_leitor_mencionado
        marca = entidades.marca
        aplicacao = entidades.aplicacao

        # A mensagem ATUAL precisa trazer algum sinal novo (marca/aplicação/tecnologia) —
        # sem isso, usar só o que já está acumulado de turnos anteriores (D6) dispararia
        # uma tentativa de resolução em QUALQUER mensagem (mesmo uma pergunta aberta sem
        # relação com modelo), que falha com MODELO_NAO_RECONHECIDO de forma confusa (bug
        # real reportado em produção: "quero que você me explique..." → "Não encontrei
        # esse modelo..."). A mensagem que completa o sinal acumulado (ex.: "facial" numa
        # 2ª mensagem, depois de "biometria" numa 1ª) ainda traz sinal fresco, então a
        # acumulação multi-turno continua funcionando.
        if not (tipo_leitor or marca or aplicacao or entidades.atributos):
            return False

        # Produto já associado ao atendimento (MVP: item único) tem prioridade sobre
        # o matching por texto: usar o produto_id real evita resolver um modelo de um
        # produto diferente do item já criado (ex.: "controle de acesso" casando por
        # substring com produtos de outro tipo). Só recorre ao matching fuzzy por
        # tipos_produto quando ainda não existe item (primeira tentativa).
        valores = {info.chave: info.valor for info in atendimento.informacoes}
        item_atual = next(iter(atendimento.itens), None)
        if item_atual is not None:
            produto_ids = [item_atual.produto_id]
        else:
            tipos_produto = [t.strip() for t in (valores.get("tipos_produto") or "").split(",") if t.strip()]
            produto_ids = _produto_ids_por_tipos(db, tipos_produto)

        # D6: atributos genéricos do modelo já coletados (persistidos, já em união — ver
        # `_atualizar_infos_atendimento`) + extraídos agora. `valores` já reflete o
        # acumulado até esta mensagem, então é a fonte primária; `entidades.atributos` só
        # cobre o caso raro em que o mesmo turno ainda não foi persistido.
        atributos_mensagem: dict[str, str] = {}
        for chave, valor in valores.items():
            if chave in ("marca", "aplicacao", "tipo_leitor_mencionado", "tipos_produto", "quantidades"):
                continue
            atributos_mensagem[chave] = valor
        for chave, valor in entidades.atributos.items():
            atributos_mensagem.setdefault(chave, valor)
        if tipo_leitor:
            atributos_mensagem.setdefault("tecnologia_leitura", tipo_leitor)

        # "eletronico" é só a pergunta guarda-chuva do template PEDIR_MODELO ("cartográfico
        # ou eletrônico?") — nunca existe como valor real no catálogo (ver
        # `scripts/importar_catalogo_csv.py::_ATRIBUTOS_POR_PALAVRA`), então usá-lo como
        # filtro garantiria falha. Se for o único valor conhecido, remove a chave — ainda
        # falta a sub-tecnologia (cartão/biometria/facial) para resolver o modelo.
        if "tecnologia_leitura" in atributos_mensagem:
            tecnologias = [v for v in atributos_mensagem["tecnologia_leitura"].split(",") if v and v != "eletronico"]
            if tecnologias:
                atributos_mensagem["tecnologia_leitura"] = ",".join(tecnologias)
            else:
                del atributos_mensagem["tecnologia_leitura"]

        sinais = {k: v for k, v in {"marca": marca, "aplicacao": aplicacao, **atributos_mensagem}.items() if v}
        if not sinais:
            # produto_ids sozinho não é suficiente para resolver: sem marca/aplicação/
            # atributo, escolher `.first()` entre vários modelos do mesmo produto seria
            # arbitrário.
            return False  # mensagem não trouxe sinal para resolver modelo

        query = db.query(Modelo).join(Produto, Modelo.produto_id == Produto.id).filter(Modelo.ativo.is_(True))
        if produto_ids:
            query = query.filter(Modelo.produto_id.in_(produto_ids))
        if marca:
            query = query.filter(Modelo.marca == marca)
        if aplicacao:
            query = query.filter(Modelo.aplicacao == aplicacao)

        # D6: exige que o modelo possua todos os valores extraídos/coletados — cada chave
        # pode acumular mais de um valor ao longo da conversa (ex.: "biometria,facial"),
        # espelhando o catálogo real, onde um modelo pode ter várias linhas
        # (chave, valor) — ver `scripts/importar_catalogo_csv.py`.
        for chave, valor_bruto in atributos_mensagem.items():
            for valor in valor_bruto.split(","):
                if not valor:
                    continue
                subquery = (
                    db.query(AtributoAdicionalModelo.modelo_id)
                    .filter(
                        AtributoAdicionalModelo.modelo_id == Modelo.id,
                        AtributoAdicionalModelo.chave == chave,
                        AtributoAdicionalModelo.valor == valor,
                        AtributoAdicionalModelo.ativo.is_(True),
                    )
                    .exists()
                )
                query = query.filter(subquery)

        candidato = query.first()
        if candidato:
            item = self._item_atendimento_atual(ctx, candidato.produto_id)
            item.modelo_id = candidato.id
            db.commit()
            p._remover_info_atendimento(db, atendimento.id, _MODELO_TENTATIVAS_CHAVE)
            if dlog:
                dlog.log(
                    "finalizando",
                    f"modelo resolvido: produto_id={candidato.id} ({candidato.descricao})",
                )
            return False

        tentativas = int(p._info_atendimento(db, atendimento.id, _MODELO_TENTATIVAS_CHAVE) or 0) + 1
        p._salvar_info_atendimento(db, atendimento.id, _MODELO_TENTATIVAS_CHAVE, str(tentativas))
        if dlog:
            sinais = ", ".join(
                f"{k}={v}"
                for k, v in {
                    "marca": marca,
                    "aplicacao": aplicacao,
                    "tipo_leitor": tipo_leitor,
                    **atributos_mensagem,
                }.items()
                if v
            )
            dlog.log(
                "finalizando",
                f"modelo sem correspondência ({sinais}) tentativa={tentativas}",
            )

        if tentativas >= _MODELO_MAX_TENTATIVAS:
            # Débito técnico corrigido nesta migração: antes mutava `modo_operacao`
            # direto, sem passar pelo helper central de escalonamento (inconsistente com
            # todo o resto do sistema) — ver MotivoEscalonamento.MODELO_NAO_RECONHECIDO.
            await p._escalar_atendimento(
                db, atendimento, MotivoEscalonamento.MODELO_NAO_RECONHECIDO,
                ator="sistema:resolucao_modelo", dlog=dlog,
            )
            return False

        return True

    def _item_atendimento_atual(self, ctx: ContextoAcao, produto_id: int) -> ItemAtendimento:
        """MVP: um único item por atendimento (só relógio de ponto) — get-or-create."""
        atendimento = ctx.atendimento
        item = next(iter(atendimento.itens), None)
        if item is None:
            item = ItemAtendimento(atendimento_id=atendimento.id, produto_id=produto_id, quantidade=1)
            ctx.db.add(item)
            ctx.db.flush()
        return item

    def _capturar_resposta_direta_pendente(self, ctx: ContextoAcao) -> None:
        """F1: cobre respostas soltas que os extratores por palavra-gatilho (D3/D4) não
        reconhecem sozinhos — ex.: "80" sozinho para faixa de funcionários, ou um nome de
        software fora de `_SOFTWARES_PONTO_CONHECIDOS` (aceito livremente, ao contrário de
        modelo — CAMPO-software-ponto não exige catálogo). Só atua sobre a pergunta
        pendente atual (a que acabamos de fazer), e só quando a mensagem não bateu em
        nenhuma regra de intenção conhecida (DESCONHECIDO) — uma intenção reconhecida (ex.:
        "quero orçamento" repetido) não deve ser sequestrada como se fosse resposta.
        """
        resultado_class = ctx.resultado_class
        if resultado_class.intencao_principal != Intencao.DESCONHECIDO:
            return

        atendimento = ctx.atendimento
        conteudo = ctx.conteudo
        p = ctx.processador
        dlog = ctx.dlog
        db = ctx.db

        pendentes = campos_pendentes(atendimento)
        if not pendentes:
            return
        campo = pendentes[0]

        if campo.chave == CAMPO_FAIXA_FUNCIONARIOS.chave:
            match = _NUMERO_SOLTO_REGEX.search(conteudo)
            if match:
                p._salvar_info_atendimento(db, atendimento.id, campo.chave, match.group(1))
                if dlog:
                    dlog.log("finalizando", f"faixa_funcionarios capturado (resposta solta): {match.group(1)}")

        elif campo.chave == CAMPO_SOFTWARE_PONTO.chave:
            texto = conteudo.strip()
            if not texto:
                return
            valor = "nenhum" if _SOFTWARE_NENHUM_REGEX.search(texto) else texto
            p._salvar_info_atendimento(db, atendimento.id, campo.chave, valor)
            if dlog:
                dlog.log("finalizando", f"software_controle_ponto capturado (resposta livre): {valor}")

        elif campo.chave == CAMPO_SOFTWARE_ACESSO.chave:
            texto = conteudo.strip()
            if not texto:
                return
            valor = "nenhum" if _SOFTWARE_NENHUM_REGEX.search(texto) else texto
            p._salvar_info_atendimento(db, atendimento.id, campo.chave, valor)
            if dlog:
                dlog.log("finalizando", f"software_controle_acesso capturado (resposta livre): {valor}")

        elif campo.chave == CAMPO_INTERESSE_SISTEMA_NUVEM.chave:
            if _RESPOSTA_SIM_REGEX.search(conteudo):
                p._salvar_info_atendimento(db, atendimento.id, campo.chave, "sim")
                if dlog:
                    dlog.log("finalizando", "interesse_sistema_nuvem capturado: sim")
            elif _RESPOSTA_NAO_REGEX.search(conteudo):
                p._salvar_info_atendimento(db, atendimento.id, campo.chave, "não")
                if dlog:
                    dlog.log("finalizando", "interesse_sistema_nuvem capturado: não")

        elif campo.chave == CAMPO_QUANTIDADE.chave:
            match = _NUMERO_SOLTO_REGEX.search(conteudo)
            if match:
                p._salvar_info_atendimento(db, atendimento.id, campo.chave, match.group(1))
                if dlog:
                    dlog.log("finalizando", f"quantidade capturada (resposta solta): {match.group(1)}")

        elif campo.chave == CAMPO_HOMOLOGADO_SOFTWARE.chave:
            if _RESPOSTA_SIM_REGEX.search(conteudo):
                p._salvar_info_atendimento(db, atendimento.id, campo.chave, "sim")
                if dlog:
                    dlog.log("finalizando", "homologado_software capturado: sim")
            elif _RESPOSTA_NAO_REGEX.search(conteudo):
                p._salvar_info_atendimento(db, atendimento.id, campo.chave, "não")
                if dlog:
                    dlog.log("finalizando", "homologado_software capturado: não")

        # Campos não obrigatórios (ex.: alerta de homologação — REQ-002.14C/15) só são
        # perguntados uma vez: esta é a única tentativa de captura da resposta (acima).
        # Marcamos como "perguntado" aqui — depois deste turno, mesmo sem resposta
        # reconhecida, `campos_pendentes()` deixa de bloquear o fluxo por causa dele.
        if not campo.obrigatorio:
            self._marcar_pergunta_opcional_se_necessario(ctx, campo)

    def _marcar_pergunta_opcional_se_necessario(self, ctx: ContextoAcao, campo: Pergunta) -> None:
        if campo.obrigatorio:
            return
        ctx.processador._salvar_info_atendimento(ctx.db, ctx.atendimento.id, chave_perguntado(campo), "true")

    async def _retomar_apos_duvida(self, ctx: ContextoAcao) -> RespostaGerada:
        """F3: se a mensagem em Finalizando for uma dúvida (categoria_pergunta), responde via
        Q&A/RAG e reapresenta a última pergunta pendente — sem perder o progresso da
        coleta (a fase continua Finalizando)."""
        atendimento = ctx.atendimento
        resultado_class = ctx.resultado_class
        p = ctx.processador
        dlog = ctx.dlog

        resposta_duvida = await responder_categoria_pergunta(resultado_class.intencao_principal, ctx)

        if atendimento.modo_operacao == ModoOperacao.HUMANO:
            # A dúvida acabou de escalar para atendimento humano (base insuficiente,
            # REQ-003.7) — continuar retomando a pergunta pendente no mesmo turno
            # contradiria a mensagem de escalonamento que o cliente acabou de receber.
            if dlog:
                dlog.log("finalizando", "dúvida escalou para humano → não retoma pergunta pendente")
            return resposta_duvida

        if resposta_duvida.template_usado == MensagemId.RAG_PEDIR_CLARIFICACAO.name:
            # A própria resposta à dúvida já é uma pergunta em aberto (REQ-003.7, 1ª
            # tentativa de clarificação) — empilhar a retomada da pergunta pendente aqui
            # geraria duas perguntas simultâneas e contraditórias no mesmo turno.
            if dlog:
                dlog.log("finalizando", "dúvida pediu clarificação → não retoma pergunta pendente no mesmo turno")
            return resposta_duvida

        pendentes = campos_pendentes(atendimento)
        if not pendentes:
            if dlog:
                dlog.log("finalizando", "dúvida em Finalizando, sem pendências → só responde a dúvida")
            return resposta_duvida

        campo = pendentes[0]
        mensagem_id = campo.mensagem_id
        ctx_campo = _contexto_para_campo(campo, atendimento)
        resposta_pergunta = await p._gerador.gerar(mensagem_id, ctx_campo)
        resposta_retomada = await p._gerador.gerar(
            MensagemId.RETOMAR_PERGUNTA_PENDENTE, {"pergunta": resposta_pergunta.texto}
        )
        if dlog:
            dlog.log("finalizando", f"dúvida ({resultado_class.intencao_principal.value}) → retoma {campo.chave}")
        return RespostaGerada(
            texto=f"{resposta_duvida.texto}\n\n{resposta_retomada.texto}",
            template_usado=f"{resposta_duvida.template_usado}+{resposta_retomada.template_usado}",
            personalizado_via_llm=resposta_duvida.personalizado_via_llm,
            llm_tokens_input=resposta_duvida.llm_tokens_input,
            llm_tokens_output=resposta_duvida.llm_tokens_output,
            rag_utilizada=resposta_duvida.rag_utilizada,
            trechos_rag=resposta_duvida.trechos_rag,
            rag_score_maximo=resposta_duvida.rag_score_maximo,
        )

    async def _gerar_resumo(self, ctx: ContextoAcao) -> RespostaGerada:
        """F4: nada mais pendente — apresenta resumo do que foi coletado e pede confirmação.

        Marca `_RESUMO_APRESENTADO_CHAVE` (G1) — um `CONFIRMAR` só conclui o handoff se for
        resposta a um resumo que o cliente de fato viu numa mensagem anterior.
        """
        db = ctx.db
        atendimento = ctx.atendimento
        p = ctx.processador
        dlog = ctx.dlog

        valores = {info.chave: info.valor for info in atendimento.informacoes}
        item_resolvido = next((item for item in atendimento.itens if item.modelo_id is not None), None)
        modelo = item_resolvido.modelo if item_resolvido else None
        contexto = {
            "modelo": modelo.descricao if modelo else None,
            "marca": modelo.marca if modelo else None,
            "aplicacao": modelo.aplicacao if modelo else None,
            "categorias": ", ".join(c.descricao for c in modelo.categorias) if modelo else None,
            "atributos": {a.chave: a.valor for a in modelo.atributos} if modelo else {},
            "software": valores.get(CAMPO_SOFTWARE_PONTO.chave),
            "software_acesso": valores.get(CAMPO_SOFTWARE_ACESSO.chave),
            "interesse_sistema_nuvem": valores.get(CAMPO_INTERESSE_SISTEMA_NUVEM.chave),
            "homologado_software": valores.get(CAMPO_HOMOLOGADO_SOFTWARE.chave),
            "faixa_funcionarios": valores.get(CAMPO_FAIXA_FUNCIONARIOS.chave),
            "quantidade": valores.get(CAMPO_QUANTIDADE.chave),
        }
        p._salvar_info_atendimento(db, atendimento.id, _RESUMO_APRESENTADO_CHAVE, "true")
        if dlog:
            dlog.log("finalizando", f"tudo capturado → resumo (modelo={contexto['modelo']})")
        return await p._gerador.gerar(MensagemId.RESUMO_FINALIZANDO, contexto)


FINALIZANDO = FinalizandoState()
