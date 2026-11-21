"""Texto da pergunta do modelo como o assistente a envia: o cadastrado para o produto no
painel (`perguntas_produto`), ou o padrão do código. Os testes comparam com ele em vez de
fixar a frase, que é editável."""

from services import perguntas_produto
from services.respostas.catalogo import MensagemId, renderizar_mensagem


def pergunta_modelo(db, tipo_produto: str) -> str:
    cadastrado = perguntas_produto.texto_para(db, "modelo_produto", tipo_produto)
    return cadastrado or renderizar_mensagem(MensagemId.PEDIR_MODELO)[0]
