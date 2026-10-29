# Sistema

Mostra como o servidor está configurado e se o LLM (o modelo de linguagem que interpreta mensagens difíceis e redige respostas a partir da base de conhecimento) está funcionando. Nada aqui pode ser alterado pela tela: as configurações vêm do arquivo `.env` do servidor.

## LLM

A etiqueta no topo resume a situação:

- **Funcional**: o provedor respondeu ao teste.
- **Com erro**: o provedor está configurado, mas o teste falhou. A mensagem de erro do provedor aparece logo abaixo. Enquanto isso, o assistente segue só com regras e textos padrão.
- **Desligado**: o servidor subiu sem LLM.

O botão **Testar agora** faz uma chamada curta ao provedor. Sem ele, a tela reaproveita o último teste por até um minuto, para não gastar cota a cada atualização.

A linha **Uso real nas últimas 24h** conta os pontos em que o LLM foi usado ou seria usado nas conversas, e diz quando ele respondeu pela última vez.

## Sem LLM × com LLM

Cada mensagem de cliente em que o LLM foi consultado (ou seria, se estivesse disponível) gera um registro com o que o assistente faria sem ele e o que o LLM devolveu. As etapas são:

- **Classificação**: as regras não tiveram confiança suficiente para entender a mensagem.
- **Resposta da base**: havia trechos da base de conhecimento, e o LLM redigiria a resposta a partir deles. Sem LLM, vai um texto padrão.
- **Personalização**: um texto padrão que seria reescrito no tom da conversa.

A situação diz o que aconteceu: **LLM respondeu**, **LLM com erro** (o erro aparece na coluna "Com LLM"), **LLM vazio** ou **Sem LLM**. O filtro no canto mostra uma situação por vez.

Quando a classificação do LLM leva a conversa por outro caminho, só a classificação é comparada: o restante da resposta que as regras dariam não é calculado.

## Configurações do servidor

Agrupadas por assunto. Chaves, tokens, usuários e senhas aparecem só como "definido" ou "não definido" (com um cadeado); telefones mostram só os 4 últimos dígitos; endereços de banco escondem o usuário e a senha. A coluna da direita diz se o valor foi **configurado** no servidor ou é o **padrão** do sistema. Um aviso em amarelo marca valores que não deveriam ir para produção como estão.
