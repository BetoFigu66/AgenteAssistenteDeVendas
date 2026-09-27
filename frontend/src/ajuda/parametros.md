# Parâmetros

Ajustes de funcionamento do assistente que podem ser alterados **sem reiniciar o
sistema**. O valor novo passa a valer nas próximas mensagens processadas.

Nome e descrição são apenas leitura. Você edita o campo **Valor** e clica em
**Salvar** na linha correspondente (o botão só habilita depois que algo muda); em seguida
aparece **Salvo** e a coluna **Atualizado** mostra a data da mudança. Toda alteração fica
registrada com autor e data. O botão **Atualizar** recarrega a lista.

O sistema confere o valor antes de gravar: número fora da faixa, texto onde se espera
número ou valor vazio são recusados, com a mensagem de erro no topo da tela.

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
em `_desambigua_min` definem a faixa em que a semelhança é duvidosa: nela o assistente
oferece opções ao cliente. `desambiguador_max_opcoes` diz quantas opções no máximo, e
`desambiguador_timeout_min` por quantos minutos a pergunta fica valendo.

**Busca na base de conhecimento dos produtos**

- `rag_enabled`: liga ou desliga a consulta aos documentos de produto.
- `rag_score_minimo`: o quanto o trecho precisa ser relevante para ser aproveitado (o
  mesmo campo **Score RAG** do Chat).
- `rag_top_k`: quantos trechos são considerados por pergunta.

**Interpretação da mensagem**

Os parâmetros `classificador_conf_*` definem a partir de que confiança o sistema aceita
a intenção detectada na mensagem do cliente. Quando a confiança fica baixa demais de
forma repetida, o atendimento é escalado para uma pessoa.

**Escalonamento**

- `escalonamento_limiar_funcionarios`: a partir de quantos funcionários o cliente é
  tratado como projeto complexo e o atendimento escala para humano. É o "limiar" que
  aparece nas evidências do bloco **Por que escalou**.

**Operação**

- `sla_aprovacao_minutos`: a partir de quantos minutos uma mensagem pendente passa a
  ser destacada em vermelho no Acompanhamento.
- `janela_continuacao_atendimento_horas`: por quanto tempo uma nova mensagem do mesmo
  cliente é tratada como continuação do atendimento anterior, em vez de abrir um novo.
- `catalogo_link_*`: links dos catálogos enviados ao cliente quando ele pede.
- `modo_execucao`: o mesmo modo do seletor do cabeçalho. Prefira trocar pelo cabeçalho:
  lá a passagem para Execução Normal mostra os indicadores e pede confirmação, e aqui não.

A lista mostra os parâmetros já gravados no banco. Um parâmetro que nunca foi ajustado
pode não aparecer e funcionar com o valor padrão do sistema.

## Se algo sair errado

Anote o valor anterior antes de alterar. Como não há botão de desfazer nesta tela,
voltar atrás significa digitar novamente o valor antigo e salvar.
