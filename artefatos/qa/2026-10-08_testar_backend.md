# Teste do backend pelo skill `testar-backend` (08/10/2026)

Primeira sessão do skill `.claude/skills/testar-backend/`. Backend dedicado na 8002 (sem LLM, `CANAL_SAIDA=simulado`, sem `--reload`), testador de conversas apontado para ele. `ModoExecucao` lido, não alterado (`execucao_normal`).

## O que mudou no testador

- Comandos novos no `cli.py`: `execucao-mostrar <cenario>` (critério, enviado e observado de cada turno da última execução), `propor <resultado_id>`, `propostas-listar`, `propostas-aprovar <ids> --por beto|kika`, `propostas-descartar <ids>`.
- Proposta = `RespostaAceita` com `ativo=false` e `criado_por=proposta_claude`. Não vale como aceita até alguém aprovar (aí vira `ativo=true`, `criado_por=aprovado:<quem>`). Sem mudança de schema. Os YAML exportados mostram as propostas, então o diff do commit é a lista para revisar.

## Cenários novos (7), da base crua e das regras de negócio

| Cenário | Fonte | Exercita |
|---|---|---|
| `bastao_de_ronda_vigilancia` | folder-bastao-de-ronda | REQ-002.1, REQ-003, compatibilidade |
| `relogio_cartografico_pequena_empresa` | folder-relogio-ponto-cartografico | REQ-002, REQ-004.8 (abaixo do limiar), preço |
| `ponto_web_software_nuvem` | folder-ponto-web | REQ-003, compatibilidade |
| `catraca_box_para_evento` | folder-catraca-balcao-box | REQ-002, prazo |
| `controle_acesso_qr_code_sala_ti` | folder-controle-de-acesso-QR-Code | REQ-002.1, REQ-003 |
| `preco_e_prazo_na_mesma_mensagem` | regras de negócio | preço e prazo na mesma mensagem |
| `pedido_humano_pelo_nome_do_vendedor` | REQ-004.1 | pedido de humano sem a palavra "atendente" |

## Placar

Bateria base (16 cenários antigos): 1 turno aceito (o já existente). Bateria final (23 cenários, 62 turnos, rodada 4): **27 turnos propostos**, os demais inaceitáveis ou dependentes de decisão (abaixo). Para revisar: `cd testador_conversas && python cli.py propostas-listar`.

## Correções feitas (commits em `develop`, não revistos)

- `9b91116` fix(classificador): nº de funcionários ("45 funcionários", "20 - 25 funcionários") e numeração de lista ("1) 2) 3)") viravam quantidade e disparavam projeto complexo na 1ª mensagem.
- `cc1aaf9` fix(classificador): reclamação de pós-venda não detectada ("não chegou", "absurdo", "ninguém me responde"); "sou pessoa física" transferia para humano (casava "pessoa"); "tudo bem?" dava NAO_ENTENDI; "preciso de relógio de ponto" ia para a RAG em vez de abrir a coleta; produto/software/marca casados por substring ("quero cancelar" virava o produto cancela, "levo" o software EVO, "busca" o SCA).
- `86aba21` fix(conversa): compatibilidade agora responde com `COMPATIBILIDADE_SISTEMA` (o template existia e nada o usava; antes caía na RAG e "funciona ou não funciona?" virava reclamação); qualquer "não" na resposta ao "Posso te ajudar em mais alguma coisa?" encerrava o atendimento, inclusive dentro de uma pergunta nova; cortesia logo depois do pedido de CNPJ/CPF era tomada como recusa do documento; "quero falar com o Ivan" não escalava.

- `928dd20` fix(finalizando): a tecnologia dita na mensagem que abre a coleta ("3 relógios biométricos") era perguntada logo em seguida (`entrar` não tentava resolver o modelo); pergunta de prazo no meio da coleta era ignorada.

Suíte do backend: 657 passed, 2 xfailed. `ruff` limpo.

## Pendências de decisão

1. **Pergunta de modelo fala de relógio para qualquer produto** (Divergência A, já marcada como `xfail` em `test_processador_divergencias_bateria_cenarios.py`). `PEDIR_MODELO` diz "O relógio seria cartográfico ou eletrônico?" também para catraca e controle de acesso. É o defeito de **maior alcance** da bateria: aparece em 4 cenários (catraca e controle de acesso), sempre na 1ª pergunta da coleta. Opções: (a) texto por tipo de produto, escrito por vocês (melhor resultado, exige redigir os textos); (b) texto neutro já existente em `CAMPO_MODELO.pergunta` ("Qual modelo ou tecnologia você prefere? (ex.: cartográfico, eletrônico, cartão, biometria, facial, QR Code)") para tudo que não for relógio (rápido, mas cita "cartográfico" para catraca).
2. **"Leitor facial é sempre projeto complexo?"** (aberta desde 25/09). Hoje "relógio de ponto facial" transfere já na 1ª mensagem, e a pergunta de prazo do cenário `prazo_entrega_pergunta_direta` nem chega à regra de prazo. O REQ-004.8 fala em "controle facial em porta". Patch pronto, se a decisão for "só controle de acesso": `artefatos/qa/2026-10-08_patches_propostos/facial_de_relogio_nao_e_projeto_complexo.patch` (com testes; `git apply` na raiz).
3. **A Inforrel vende câmera?** (aberta desde 25/09). O bot responde "Sim, vendemos. Trabalhamos com a marca Intelbras" e fica preso perguntando a faixa de pessoas da câmera, ignorando a pergunta seguinte (horário) e a troca para catraca.
4. **Cortesia depois do pedido de documento**: com a correção, "tudo bem?" responde "Voltando à minha pergunta: ... CNPJ ... ou seu CPF?". O critério do cenário `mensagens_quebradas_em_rajada` (25/09) diz "NÃO PODE pedir CNPJ de novo". Opções: (a) manter a retomada (como está); (b) responder só à cortesia ("Tudo ótimo, obrigado! 😊"), texto novo, deixando o pedido pendente. Não propus esses turnos.
5. **Testar a base de conhecimento exige LLM.** Os cenários tirados dos folders (bastão de ronda, QR Code, ponto web) param no classificador por regras: "controlar se o vigilante fez a ronda" ou "controlar quem entra na sala de TI" não têm palavra-chave de produto, e a resposta é saudação ou NAO_ENTENDI. Sem LLM a RAG não chega a ser exercitada. Opções: (a) segundo backend com LLM ligado só para esses cenários, com o Claude como juiz semântico (resposta varia, não serve para casamento exato, o testador precisaria de "aceite por critério"); (b) ampliar as palavras-chave do classificador (barato, mas é enxugar gelo); (c) deixar esses cenários como referência para quando o LLM estiver ligado.

## Bugs achados, ainda não corrigidos (sem decisão necessária, só não deu tempo)

- **Resposta "pode ser o de cartão, o mais simples" vai para a RAG** em vez de responder a pergunta de tecnologia ("cartão" casa `PERGUNTAR_PRODUTO`, vira dúvida).
- **Saudação sem o nome**: quando a 1ª mensagem já abre orçamento, o pedido é só "CNPJ ou CPF" (`PEDIR_DOCUMENTO`), sem o nome; na saudação simples pede os dois. Regra do `CLAUDE.md`: nome e documento juntos no início.
- **"Posso te ajudar em mais alguma coisa?" repetido** a cada resposta de compatibilidade (3 vezes seguidas no cenário).
- **"é o seguinte"** (cliente vai continuar) dá NAO_ENTENDI e conta para o escalonamento por baixa confiança.
- **Troca de produto no meio** ("esquece, o que eu preciso é catraca") não troca o produto do atendimento: segue perguntando o software de ponto.

## Como aprovar

```bash
cd testador_conversas && source venv/bin/activate
python cli.py propostas-listar
python cli.py propostas-aprovar <ids> --por beto      # ou --por kika
python cli.py propostas-descartar <ids>
python cli.py exportar                                # e commitar os YAML
```
