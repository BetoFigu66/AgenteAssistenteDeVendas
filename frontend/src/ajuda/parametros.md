# Parâmetros

Ajustes de funcionamento do assistente que podem ser alterados **sem reiniciar o
sistema**. O valor novo passa a valer nas próximas mensagens processadas.

Nome e descrição são apenas leitura. Você edita o campo **Valor** e clica em
**Salvar** na linha correspondente — o botão só habilita depois que algo muda.
Toda alteração fica registrada com autor e data.

## Cuidado ao alterar

Estes valores afetam diretamente o que o cliente recebe. Prefira mudanças pequenas,
uma de cada vez, observando o efeito no Acompanhamento antes de seguir.

## O que costuma ser ajustado

**Quando o assistente considera que encontrou uma resposta**

Os parâmetros iniciados em `qa_` controlam o quanto a pergunta do cliente precisa se
parecer com uma pergunta da Base Q&A para o assistente usar aquela resposta. Valores
vão de 0 a 1.

- Aumentar torna o assistente mais exigente: responde menos, erra menos.
- Diminuir torna o assistente mais solto: responde mais, com mais risco de trazer
  a resposta errada.

Os terminados em `_responde_min` definem o limite para responder direto. Os terminados
em `_desambigua_min` definem a faixa em que a semelhança é duvidosa.

**Busca na base de conhecimento dos produtos**

- `rag_enabled` — liga ou desliga a consulta aos documentos de produto.
- `rag_score_minimo` — o quanto o trecho precisa ser relevante para ser aproveitado.
- `rag_top_k` — quantos trechos são considerados por pergunta.

**Interpretação da mensagem**

Os parâmetros `classificador_conf_*` definem a partir de que confiança o sistema aceita
a intenção detectada na mensagem do cliente. Quando a confiança fica baixa demais de
forma repetida, o atendimento é escalado para uma pessoa.

**Operação**

- `sla_aprovacao_minutos` — a partir de quantos minutos uma mensagem pendente passa a
  ser destacada em vermelho no Acompanhamento.
- `janela_continuacao_atendimento_horas` — por quanto tempo uma nova mensagem do mesmo
  cliente é tratada como continuação do atendimento anterior, em vez de abrir um novo.
- `modo_execucao` — o mesmo seletor que aparece no cabeçalho do painel.

## Se algo sair errado

Anote o valor anterior antes de alterar. Como não há botão de desfazer nesta tela,
voltar atrás significa digitar novamente o valor antigo e salvar.
