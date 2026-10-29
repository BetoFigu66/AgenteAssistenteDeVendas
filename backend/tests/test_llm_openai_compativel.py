"""Provedor genérico compatível com a API da OpenAI (`services/llm/openai_compativel_provider.py`).

Pedido do Beto (12/10/2026), depois do bloqueio da conta da Groq: um provedor só para
OpenAI, Ollama, Cloudflare, OpenRouter, Gemini etc. Os testes usam um servidor falso
(`httpx.MockTransport`): nenhuma chamada sai da máquina.
"""

import asyncio
import json

import httpx
import pytest
from services import diagnostico_sistema
from services.llm import factory
from services.llm.openai_compativel_provider import OpenAICompativelProvider, extrair_json


def _resposta(conteudo, modelo="modelo-x"):
    return {
        "id": "1",
        "object": "chat.completion",
        "created": 0,
        "model": modelo,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": conteudo}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10},
    }


def _provedor(tratar, **kwargs):
    pedidos = []

    def handler(request):
        corpo = json.loads(request.content)
        pedidos.append((request, corpo))
        return tratar(corpo)

    cliente = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    parametros = {"nome": "openai_compativel", "modelo": "modelo-x", "api_key": "k", "base_url": "http://falso/v1"}
    parametros.update(kwargs)
    return OpenAICompativelProvider(http_client=cliente, **parametros), pedidos


def test_completar_devolve_texto_e_tokens():
    llm, pedidos = _provedor(lambda corpo: httpx.Response(200, json=_resposta("Olá!")))
    resposta = asyncio.run(llm.completar("sistema", "usuário", max_tokens=20))

    assert resposta.conteudo == "Olá!"
    assert (resposta.tokens_input, resposta.tokens_output) == (7, 3)
    request, corpo = pedidos[0]
    assert str(request.url) == "http://falso/v1/chat/completions"
    assert request.headers["authorization"] == "Bearer k"
    assert corpo["model"] == "modelo-x" and corpo["max_tokens"] == 20
    assert [m["role"] for m in corpo["messages"]] == ["system", "user"]


def test_completar_json_pede_o_modo_json():
    llm, pedidos = _provedor(lambda corpo: httpx.Response(200, json=_resposta('{"intencao": "saudacao"}')))

    assert asyncio.run(llm.completar_json("s", "u")) == {"intencao": "saudacao"}
    assert pedidos[0][1]["response_format"] == {"type": "json_object"}


def test_modo_json_recusado_repete_sem_ele_e_nao_tenta_mais():
    def tratar(corpo):
        if "response_format" in corpo:
            return httpx.Response(400, json={"error": {"message": "response_format is not supported"}})
        return httpx.Response(200, json=_resposta('Claro: ```json\n{"intencao": "pedir_catalogo"}\n```'))

    llm, pedidos = _provedor(tratar)

    assert asyncio.run(llm.completar_json("s", "u")) == {"intencao": "pedir_catalogo"}
    assert asyncio.run(llm.completar_json("s", "u")) == {"intencao": "pedir_catalogo"}
    com_modo = [c for _, c in pedidos if "response_format" in c]
    assert len(com_modo) == 1
    assert len(pedidos) == 3


def test_outro_erro_400_nao_e_engolido():
    llm, _ = _provedor(lambda corpo: httpx.Response(400, json={"error": {"message": "organization_restricted"}}))

    with pytest.raises(Exception, match="organization_restricted"):
        asyncio.run(llm.completar_json("s", "u"))


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ('{"a": 1}', {"a": 1}),
        ('```json\n{"a": 1}\n```', {"a": 1}),
        ('Aqui está: {"a": {"b": 2}} espero ter ajudado', {"a": {"b": 2}}),
    ],
)
def test_extrair_json_tolera_texto_em_volta(texto, esperado):
    assert extrair_json(texto) == esperado


@pytest.mark.parametrize("texto", ["sem json", "[1, 2]", "{quebrado"])
def test_extrair_json_recusa_o_que_nao_e_objeto(texto):
    with pytest.raises(ValueError):
        extrair_json(texto)


def test_ollama_dispensa_chave_e_os_outros_exigem():
    OpenAICompativelProvider(nome="ollama", modelo="llama3.2", base_url="http://localhost:11434/v1")
    with pytest.raises(ValueError, match="LLM_API_KEY"):
        OpenAICompativelProvider(nome="openrouter", modelo="x")


@pytest.fixture
def fabrica(monkeypatch):
    def configurar(**valores):
        for nome, valor in valores.items():
            monkeypatch.setattr(factory.settings, nome, valor)
        factory.get_llm_provider.cache_clear()
        return factory.get_llm_provider()

    yield configurar
    factory.get_llm_provider.cache_clear()


def test_fabrica_usa_o_endereco_conhecido(fabrica):
    llm = fabrica(LLM_PROVIDER="ollama", LLM_MODEL="llama3.2", LLM_API_KEY=None, LLM_BASE_URL=None)

    assert llm.nome == "ollama"
    assert str(llm._client.base_url).startswith("http://localhost:11434/v1")


def test_fabrica_cloudflare_exige_endereco(fabrica):
    with pytest.raises(ValueError, match="LLM_BASE_URL"):
        fabrica(LLM_PROVIDER="cloudflare", LLM_MODEL="m", LLM_API_KEY="k", LLM_BASE_URL=None)


def test_fabrica_recusa_provedor_desconhecido(fabrica):
    with pytest.raises(ValueError, match="não suportado"):
        fabrica(LLM_PROVIDER="inexistente")


def test_id_da_conta_no_endereco_nao_aparece_na_aba_sistema():
    valor, mascarado = diagnostico_sistema.mascarar_valor(
        "LLM_BASE_URL", "https://api.cloudflare.com/client/v4/accounts/abc123def/ai/v1"
    )
    assert mascarado
    assert "abc123def" not in valor
    assert valor == "https://api.cloudflare.com/client/v4/accounts/***/ai/v1"
