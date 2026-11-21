# Teste do backend pelo skill `testar-backend` (02/11/2026)

Bateria refeita do zero sobre o sistema atual, incluindo as entregas sem commit de 01-02/11 (cumprimentos cadastráveis, uma pergunta por mensagem, perguntas por produto). Backend dedicado na 8002 (sem LLM, `CANAL_SAIDA=simulado`, sem `--reload`), `ModoExecucao` lido e não alterado (`execucao_normal`).

## Limpeza da base

Backup do schema `teste_conversas` antes de apagar: `pg_dump` no scratchpad da sessão (não versionado). Apagados: as 27 propostas de 08/10 (todas pendentes), 141 execuções e 408 resultados. Mantidos: os 25 cenários com seus critérios (são a especificação, versionados nos YAML) e a única resposta aprovada por humano (`saudacao_simples`, `revisao_manual_cli`), que ficou desatualizada com a saudação nova e convive com a proposta nova.

## Cenários novos (5)

| Cenário | Exercita | Fonte |
|---|---|---|
| `cumprimento_boa_tarde_espelhado` | tabela `cumprimentos`, nome dito depois da saudação | regra de negócio do `CLAUDE.md` |
| `catraca_pergunta_identificacao_por_produto` | texto da pergunta do modelo para Catraca | `perguntas_produto`, folders de catraca |
| `leitor_facial_so_facial_ou_digital` | texto da pergunta do modelo para Leitor Facial | `perguntas_produto`, folders de leitor facial |
| `cancela_pergunta_modelo_padrao` | texto padrão para produto sem texto cadastrado, preço no meio da coleta | `PEDIR_MODELO`, divergência A |
| `relogio_modelo_nao_reconhecido` | `MODELO_NAO_RECONHECIDO` com a pergunta do produto | `perguntas_produto` |

## Placar

30 cenários (29 ativos), 75 turnos. **35 turnos propostos**, os demais inaceitáveis ou dependentes de decisão (abaixo). `cnpj_valido_mas_inexistente_na_receita` segue inativo (bate na ReceitaWS).

## Correções feitas (sem commit, junto das entregas de 01-02/11)

- **Nome dito depois da saudação dava "não entendi"** (`cumprimento_boa_tarde_espelhado` T2). A saudação pede nome e documento; "sou o Marcos" gravava o nome, mas `EsclarecendoState.tratamento_principal` tratava a mensagem sem documento como recusa, marcava `recusado` e respondia NAO_ENTENDI. Agora, se a mensagem só traz o nome e o documento está pedido, responde "Para prosseguir, poderia me informar o CNPJ da sua empresa ou seu CPF?" (template existente) e o documento segue pedido (`services/conversacao/estados/esclarecendo.py`).
- **"leitores faciais" não abria a coleta** (`leitor_facial_so_facial_ou_digital` T1): o casamento por palavra só aceita o plural com "s" final. Incluídos "leitores faciais" e "leitores biométricos" em `_TIPOS_PRODUTO_PALAVRAS` (`services/classificador.py`).
- **Código de modelo virava quantidade** ("o modelo XPTO-9000" dava quantidade 9000 e acendia o gatilho de projeto complexo por quantidade mínima). Nova máscara `_REGEX_MASCARA_CODIGO_MODELO` na extração de quantidades: número colado a letras é parte do nome do modelo.

Testes de regressão em `tests/test_processador_divergencias_bateria_cenarios.py`. Suíte do backend: 723 passed, 1 xfailed. `ruff` limpo.

## Pendências de decisão

1. **A aplicação sozinha resolve o modelo?** "2 catracas para a portaria do meu condomínio" e "3 leitores faciais para o escritório" não recebem a pergunta do modelo: a aplicação ("Condomínios", "Escritórios") casa um modelo do catálogo e o campo é dado como respondido. A pergunta cadastrada por produto (forma de identificação da catraca, só facial ou também digital) nunca é feita, e a resposta seguinte do cliente ("reconhecimento facial", "que leia digital também") cai no vazio. Opções: (a) manter, aplicação é sinal suficiente; (b) exigir tecnologia de leitura (ou marca) além da aplicação para dar o modelo por resolvido; a pergunta passa a ser feita e a aplicação vira filtro. Sugestão: (b). Não propus esses turnos.
2. **"Modelo não reconhecido" quando o cliente responde com a aplicação**: à pergunta do modelo, "pra uma academia" responde "Não encontrei esse modelo no nosso catálogo..." (a aplicação foi a tentativa, nenhum modelo de controle de acesso tem essa aplicação). Opções: (a) texto diferente quando o sinal foi só a aplicação ("Anotei que é para academia." e repete a pergunta), texto novo; (b) não contar aplicação como tentativa de modelo.
3. **Pendências de 08/10 ainda abertas** (comportamento igual nesta rodada, não propus): câmera ("Sim, vendemos... Intelbras" e fica preso na faixa de pessoas da câmera); leitor facial sempre projeto complexo (agora acontece também com "reconhecimento facial" respondido para catraca, que grava `escalonamento_adiado`); cortesia depois do pedido de documento ("Voltando à minha pergunta"); testar a base de conhecimento exige LLM (bastão de ronda, QR Code e ponto web: a 1ª mensagem só recebe a saudação, a pergunta do cliente é ignorada).
4. **Critérios desatualizados**: `cpf_pessoa_fisica_e_data_nascimento` T3 manda data de nascimento, que não é mais pedida (resposta NAO_ENTENDI); T1 ("não tenho empresa, sou pessoa física") recebe o pedido genérico "nome e o CNPJ da sua empresa ou seu CPF", que o critério proíbe. Reescrever o cenário (tirar a data, pedir só CPF a quem disse que é PF?).

## Bugs achados, não corrigidos (sem decisão necessária, só não deu tempo)

- **Preço no meio da coleta é ignorado**: "quanto custa mais ou menos?", "me passa só um valor aproximado", "é muito caro isso?", "quanto fica?" repetem só a pergunta pendente (classificado como `pedir_orcamento`). O prazo já tem tratamento igual desde `928dd20` ("Voltando ao orçamento: ..."); falta o mesmo para preço. 4 turnos em 3 cenários.
- **Endereço vira faixa de funcionários**: "Rua das Acácias, 120 - Sala 3" responde à pergunta da faixa com 120, que acende o gatilho de projeto complexo. E "é para instalar, não é retirada" gravou `software_controle_ponto = nenhum` (o "não" lido como resposta à pergunta do software).
- **Resposta ao modelo com código desconhecido vai para a RAG**: "o modelo XPTO-9000" é classificado como dúvida de produto e responde "Não tenho certeza se consigo te responder...", em vez de `MODELO_NAO_RECONHECIDO`.
- **"vou passar para a diretoria analisar"** foi tomado como resposta à pergunta do software e o fluxo seguiu para a nota fiscal.
- Seguem de 08/10: "pode ser o de cartão, o mais simples" vai para a RAG; "Posso te ajudar em mais alguma coisa?" repetido a cada resposta de compatibilidade; "é o seguinte" dá NAO_ENTENDI; troca de produto no meio não troca o produto; "isso mesmo", "Sim, é verdade" e "Eu quem agradeço" dão NAO_ENTENDI (a segunda escala por baixa confiança); a 1ª mensagem que já abre orçamento pede só o documento, sem o nome.

## Como aprovar

```bash
cd testador_conversas && source venv/bin/activate
python cli.py propostas-listar
python cli.py propostas-aprovar <ids> --por beto      # ou --por kika
python cli.py propostas-descartar <ids>
python cli.py exportar                                # e commitar os YAML
```

Os YAML em `cenarios_exportados/` já foram exportados com as 35 propostas (`ativo: false`, `criado_por: proposta_claude`), então o diff deles é a lista para revisar.
