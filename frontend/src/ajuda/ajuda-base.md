# Base de Ajuda

Aqui se escreve a ajuda que a equipe lê nas telas do painel. É o conteúdo que aparece
quando alguém clica no **?** ao lado do título de uma tela e faz uma pergunta.

Não confunda com a **Base Q&A**: aquela guarda as respostas enviadas aos **clientes**
pelo WhatsApp. Esta é ajuda interna e nunca chega a um cliente — são bases separadas
justamente para que uma instrução de painel não seja enviada por engano.

## Duas camadas de ajuda

O botão **?** de cada tela mostra duas coisas:

1. **Perguntas e respostas** — o que você cadastra aqui. Serve para dúvidas pontuais
   ("como aprovo uma mensagem?").
2. **Explicação completa da tela** — um texto mais longo, mantido pelos desenvolvedores
   junto com o código. Não é editável por esta tela.

## Perguntas sem resposta

A faixa âmbar no topo mostra o que os usuários perguntaram e a base **não** soube
responder, com a quantidade de vezes quando repetida. É a melhor pauta de conteúdo que
existe: são dúvidas reais, não suposições.

Clique em qualquer uma delas para abrir o formulário já com a pergunta preenchida e a
tela onde foi perguntada.

## Cadastrar um conteúdo

1. Clique em **Novo conteúdo**.
2. Escreva a **pergunta como o usuário faria** — não como um título de manual. O sistema
   compara o que a pessoa digita com esse texto, então "como aprovo uma mensagem?"
   funciona melhor que "Aprovação de mensagens".
3. Escreva a **resposta**, em passos curtos. Aceita Markdown (negrito, listas, links).
4. Escolha a **tela**. Deixe em *Global* quando a dúvida valer em qualquer lugar do
   painel, como trocar de senha.
5. A **prioridade** ordena as sugestões que aparecem antes de a pessoa digitar: maior
   primeiro. Não influencia a busca.

O conteúdo entra em uso imediatamente, sem etapa de aprovação.

## Como a busca encontra a resposta

Em duas etapas, nesta ordem:

1. **Por palavras** — casa os termos digitados com os da pergunta cadastrada, ignorando
   acentuação e variações simples de plural e conjugação.
2. **Por significado** — só quando a primeira não acha nada. Encontra mesmo com outras
   palavras: quem digita "como mudo o parâmetro" chega à pergunta "como altero o valor de
   um parâmetro".

Por isso vale cadastrar a pergunta do jeito mais natural possível, sem tentar prever
todas as formas de escrever.

## Tela específica ou global

Quando alguém pergunta de dentro de uma tela, o conteúdo **daquela tela** tem preferência
sobre o global, mesmo que o global pareça mais parecido. É o que torna a ajuda
contextual: na tela de Reports, "como exporto os dados?" deve responder sobre o pacote de
análise, não sobre exportação em geral.

## Selo "sem índice semântico"

Indica que aquele conteúdo só é encontrado por palavras, sem a busca por significado.
Acontece quando o serviço de índice estava indisponível no momento de salvar — o conteúdo
é gravado mesmo assim, para não travar seu trabalho.

Quando houver algum nessa situação, aparece o botão **Reindexar** no topo, que resolve
todos de uma vez.

## Editar e desativar

- **Editar** (lápis): ajusta pergunta, resposta, tela ou prioridade. Mudar a pergunta
  refaz o índice de significado.
- **Desativar** (lixeira): tira de uso sem apagar. O histórico de consultas que aponta
  para ele continua íntegro. Para rever os desativados, troque o filtro para *Inativos*.

## Dicas de conteúdo

- Uma pergunta, uma resposta. Duas dúvidas juntas competem entre si na busca.
- Prefira o vocabulário de quem usa o sistema, não o interno do código.
- Se a resposta ficar longa demais, provavelmente ela pertence à explicação completa da
  tela — fale com quem desenvolve.
