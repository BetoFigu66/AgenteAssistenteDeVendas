"""Cliente HTTP do backend real — fala com ele exatamente como um cliente de
fora falaria: `/webhook` (mesmo formato form-encoded que o Twilio usa) pra
mandar mensagem, API autenticada do painel pra ver pendências e limpar depois.
"""

from __future__ import annotations

import re
from typing import Optional
from xml.sax.saxutils import unescape

import httpx
from config import BACKEND_BASE_URL, TESTADOR_LOGIN, TESTADOR_SENHA

# `[^>]*` cobre os atributos que a tag passou a ter no backend (`statusCallback`).
_RE_TWIML_MESSAGE = re.compile(r"<Message[^>]*>(.*?)</Message>", re.DOTALL)

# Uma resposta com várias perguntas sai em várias mensagens de WhatsApp (uma tag
# `<Message>` cada). O testador as junta com o mesmo separador que o backend usa para
# compor a resposta inteira, então o texto comparado com `respostas_aceitas` é o mesmo
# de quando tudo saía numa mensagem só.
_SEPARADOR_MENSAGENS = "\n\n"


class ClienteBackend:
    def __init__(self, base_url: str = BACKEND_BASE_URL):
        self._http = httpx.Client(base_url=base_url, timeout=30.0)
        self._autenticado = False
        # Maior id de mensagem pendente já lido por telefone. As pendentes não são
        # aprovadas por ninguém e se acumulam; este marco separa as do turno atual.
        self._ultima_pendente_lida: dict[str, int] = {}

    def _garantir_sessao(self) -> None:
        if self._autenticado:
            return
        r = self._http.post(
            "/api/auth/login", json={"login": TESTADOR_LOGIN, "senha": TESTADOR_SENHA}
        )
        r.raise_for_status()
        self._autenticado = True

    def enviar_mensagem(self, telefone: str, conteudo: str) -> str:
        """Simula o Twilio chamando `/webhook`. Devolve o texto da resposta, ou
        `""` se nada voltou de imediato (modo HUMANO, ou aprovação pendente em
        SIMULACAO/CONVERSA_CONTROLADA — nesse caso ver `buscar_mensagem_pendente`)."""
        r = self._http.post("/webhook", data={"From": f"whatsapp:{telefone}", "Body": conteudo})
        r.raise_for_status()
        # O backend escapa o texto ao montar o TwiML (senão um `&` na resposta gera XML
        # inválido). Desescapar aqui devolve o texto como o cliente o veria.
        textos = [unescape(m).strip() for m in _RE_TWIML_MESSAGE.findall(r.text)]
        return _SEPARADOR_MENSAGENS.join(t for t in textos if t)

    def buscar_mensagem_pendente(self, telefone: str) -> Optional[str]:
        """Quando `enviar_mensagem` devolve vazio, busca o texto gerado mas ainda
        pendente de aprovação, via `/api/mensagens/pendentes`.

        Devolve as mensagens do **turno mais recente** daquele telefone, unidas como em
        `enviar_mensagem` (um turno pode gerar várias). O endpoint lista todas as
        pendentes e nada as aprova sozinho: em SIMULACAO/CONVERSA_CONTROLADA elas se
        acumulam, e pegar a primeira que casasse com o telefone faria o testador ler
        para sempre a resposta do turno 1, em silêncio. O turno atual é o das pendentes
        com id acima da última já lida neste telefone.
        """
        self._garantir_sessao()
        r = self._http.get("/api/mensagens/pendentes")
        r.raise_for_status()
        # Ordena só por `id`, que é autoincremento e portanto já é a ordem de criação.
        #
        # Uma versão anterior ordenava pelo `timestamp` como texto, supondo formato fixo.
        # Não é: o backend serializa com `datetime.isoformat()`, que **omite os
        # microssegundos quando são zero**. Então "2026-09-19T10:00:00Z" e
        # "2026-09-19T10:00:00.500000Z" divergem já na posição 19, onde 'Z' (0x5A) é maior
        # que '.' (0x2E), e a mensagem anterior ganhava da posterior. Medido, não deduzido.
        marco = self._ultima_pendente_lida.get(telefone, 0)
        novas = sorted(
            (
                m
                for m in r.json().get("mensagens", [])
                if m.get("telefone") == telefone and (m.get("id") or 0) > marco
            ),
            key=lambda m: m.get("id") or 0,
        )
        if not novas:
            return None
        self._ultima_pendente_lida[telefone] = novas[-1].get("id") or marco
        return _SEPARADOR_MENSAGENS.join(m.get("conteudo") or "" for m in novas if m.get("conteudo"))

    def limpar_telefone(self, telefone: str) -> None:
        self._garantir_sessao()
        r = self._http.delete(f"/api/dev/telefones/{telefone}")
        self._ultima_pendente_lida.pop(telefone, None)
        if r.status_code not in (200, 404):
            r.raise_for_status()

    def fechar(self) -> None:
        self._http.close()
