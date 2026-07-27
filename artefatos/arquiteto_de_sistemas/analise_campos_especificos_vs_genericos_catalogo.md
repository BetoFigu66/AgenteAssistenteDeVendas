# Análise: campos específicos vs. genéricos no catálogo e classificador

<!-- CLASSIFICACAO: DECISAO -->

## Contexto

O classificador de intenções e o processador de mensagens carregam hoje estruturas
hardcoded para os dois primeiros tipos de produto do catálogo:

- `classificador.py`: `_TIPOS_PRODUTO_PALAVRAS`, `_SOFTWARES_PONTO_CONHECIDOS`,
  `_TIPO_LEITOR_PALAVRAS`, `_MARCAS_PALAVRAS`, `_APLICACOES_PALAVRAS` e campos do
  dataclass `EntidadesExtraidas` (`software_ponto`, `tipo_leitor_mencionado`,
  `faixa_funcionarios`, `marca`, `aplicacao`).
- `processador.py`: `catalogo_campos.py` define `CAMPO_MODELO`,
  `CAMPO_SOFTWARE_PONTO` e `CAMPO_FAIXA_FUNCIONARIOS`, todos com
  `produtos_aplicaveis=frozenset({"relogio_ponto"})` e perguntas escritas para
  relógio de ponto.
- `processador.py`: `_tentar_resolver_modelo` ainda usa sinais como
  `tipo_leitor_mencionado`, `marca` e `aplicacao`, mas a pergunta de esclarecimento
  do campo `modelo_produto` é específica para relógios (cartográfico/eletrônico).

Isso foi adequado para o MVP inicial, quando apenas "catraca" e "relogio_ponto"
estavam no catálogo. Hoje a planilha `planilha_catalogo_modelos_v2.csv` já
inclui os tipos "Controle de Acesso", "Cancela", "Leitor Facial", "Câmera",
"Bastão de Ronda", "Software para Controle de Acesso", "Roteador", entre outros,
e a expectativa é adicionar novas categorias sem reescrever regras de conversação.
A planilha `planilha_catalogo_modelos_2026-07.csv` foi descontinuada e não deve
ser usada como fonte. O importador `backend/scripts/importar_catalogo_csv.py`
já aponta para `planilha_catalogo_modelos_v2.csv`.

## Escopo da análise

Avaliar se o custo de manter campos/entidades específicos para cada tipo de
produto justifica a precisão ganha, ou se já é hora de introduzir mecanismos
genéricos baseados nos metadados do catálogo.

## Critérios de avaliação

| Critério | Peso |
|----------|------|
| Facilidade para adicionar novos produtos/modelos sem tocar em código | alto |
| Risco de regressão/falso positivo na extração de entidades | alto |
| Capacidade de manter perguntas contextualizadas por tipo de produto | médio |
| Esforço de implementação e refatoração | médio |
| Clareza para manutenção futura | médio |

## Alternativas

### A — Manter campos específicos (status quo)

Nesta abordagem, cada novo tipo de produto que precise de perguntas especiais
adiciona novos mapeamentos em `classificador.py` e novos `CampoDef` em
`catalogo_campos.py`.

**Vantagens:**
- Controle total sobre sinônimos e regras.
- Fácil de justificar em requisitos formais (`REQ-002.x`).
- Baixo risco de curto prazo enquanto o catálogo tiver poucos tipos.

**Desvantagens:**
- Cada novo produto exige PR em regras de negócio + testes.
- Duplicação: `tipo_leitor_mencionado` e `modelo` acabam competindo pela mesma
  informação (tecnologia de leitura).
- Perguntas escritas à mão rapidamente ficam desalinhadas com a descrição real
  dos modelos no catálogo.
- Quebra o princípio "a fonte da verdade é a planilha/DB".

**Custo estimado (novo tipo):** 1-2 dias de dev entre classificador, catálogo de
perguntas e testes, mais revisitada de REQs.

### B — Generalizar extração e campos via catálogo

Nesta abordagem, o catálogo passa a ser a fonte da verdade também para:

1. **Sinônimos de produto:** tabela `produto_sinonimos` (ou campo JSON em
   `Produto`) com os termos que disparam `tipos_produto`.
2. **Atributos de modelos:** campos genéricos como `Modelo.tecnologia`,
   `Modelo.capacidade`, etc., ou tabela `modelo_atributos` (chave/valor).
3. **Perguntas de qualificação:** tabela `campo_qualificacao` ligada a produto e
   a uma lista de atributos que a pergunta tenta esclarecer.

O `classificador.py` passa a extrair entidades genéricas (`atributos_detectados`)
e o `processador.py` usa esses atributos para filtrar o catálogo dinamicamente.

**Vantagens:**
- Novo produto/modelo entra via importação de planilha, sem mudar código.
- Perguntas e sinônimos versionados junto com o catálogo.
- Desacopla regras linguísticas do processador.

**Desvantagens:**
- Refatoração de médio porte: novas tabelas, migrations, ajuste no importador CSV,
  testes e atualização do LLM prompt.
- Alguns atributos são específicos demais para serem genéricos (ex.: software de
  controle de ponto só faz sentido para relógios; "faixa de funcionários" é
  relevante quase só para relógios de ponto).
- Risco de extrair atributos demais e confundir a resolução de modelo.

**Custo estimado (refatoração única):** 3-5 dias de dev + ajustes no catálogo.

**Custo estimado (novo tipo após refatoração):** 1-2 horas de revisão de
planilha/sinônimos, sem PR de código.

### C — Híbrida recomendada (caminho intermediário)

Aproximar-se da opção B em camadas, sem uma migração "big bang":

1. **Sinônimos de produto vêm do catálogo:** criar `produto_sinonimos` e trocar
   `_TIPOS_PRODUTO_PALAVRAS` por uma leitura em tempo de importação/execução.
   Mantém o repositório como fonte da verdade.
2. **Entidades de "tecnologia de leitura" genérica:** manter
   `tipo_leitor_mencionado` como sinal cru, mas a pergunta de qualificação do
   campo `modelo_produto` passa a ser genérica ("Qual modelo ou tecnologia você
   prefere?"), enquanto o processador usa a descrição dos modelos + atributos
   `marca`/`aplicacao` para filtrar.
3. **Perguntas específicas continuam em `catalogo_campos.py`, mas ampliam
   `produtos_aplicaveis`:** `CAMPO_SOFTWARE_PONTO` e `CAMPO_FAIXA_FUNCIONARIOS`
   permanecem específicos para `relogio_ponto`, mas `CAMPO_MODELO` passa a
   aplicar a todos os produtos.
4. **Introduzir `modelo_atributos` (genérico) apenas quando houver um terceiro
   tipo de produto** que exija atributos não cobertos por `marca`/`aplicacao`.

**Vantagens:**
- Ganha escalabilidade sem refatoração pesada.
- Preserva regras de negócio específicas (software de ponto, funcionários).
- Permite validar o impacto com o terceiro tipo de produto.

**Desvantagens:**
- Ainda há duplicação temporária entre `tipo_leitor_mencionado` e descrição dos
  modelos.
- Necessita migração e importador de sinônimos.

**Custo estimado:** 1-2 dias de dev para sinônimos + generalização do
`CAMPO_MODELO`.

## Análise de custo x benefício

| Alternativa | Curto prazo | Médio prazo | Longo prazo | Risco de regressão | Manutenção |
|-------------|-------------|-------------|-------------|--------------------|------------|
| A — Específico | baixo custo | custo crescente | alto custo | baixo | alta |
| B — Genérico | alto custo | baixo custo | baixo custo | médio | baixa |
| C — Híbrida | médio custo | baixo custo | baixo custo | baixo | média |

A opção A deixa dívidas técnicas crescerem rápido. A opção B é ideal, mas exige
um investimento que pode não valer a pena se o catálogo continuar com apenas três
tipos de produto por um tempo. A opção C oferece o melhor equilíbrio: resolve a
restrição mais incômoda agora (modelo aplicável só a relógios, sinônimos
hardcoded), sem abrir mão das regras específicas que ainda têm sentido de
negócio.

## Recomendação

Adotar a **opção C (híbrida)** como próximo passo:

1. Criar tabela `produto_sinonimos` e importar os sinônimos a partir da
   planilha/DB; substituir `_TIPOS_PRODUTO_PALAVRAS` por leitura dinâmica.
2. Generalizar `CAMPO_MODELO` para todos os produtos e ajustar a pergunta para
   não pressupor relógio de ponto.
3. Manter `CAMPO_SOFTWARE_PONTO` e `CAMPO_FAIXA_FUNCIONARIOS` específicos para
   `relogio_ponto` até que outro tipo de produto precise de campos equivalentes.
4. Criar `modelo_atributos` (genérico) apenas quando `marca`, `aplicacao` e a
   descrição do modelo não forem suficientes para desambiguar um novo tipo.
5. Revisar se `tipo_leitor_mencionado` deve continuar como entidade específica ou
   pode virar um atributo genérico "tecnologia" indexado no catálogo.

## Consequências

- O sistema passa a aceitar novos tipos de produto sem alterar regras de código,
  desde que eles resolvam em `Modelo` por `marca`/`aplicacao`/descrição.
- A refatoração é incremental: não quebra o comportamento atual de relógio de
  ponto.
- O LLM continua sendo o fallback para extração; o prompt já usa `marca` e
  `aplicacao`, então a mudança principal é no repositório de sinônimos e no
  catálogo de perguntas.

## Próximos passos sugeridos

1. ADR complementar detalhando o modelo de dados para `produto_sinonimos` e
   `modelo_atributos`.
2. Criar migration e ajustar `importar_catalogo_csv.py` para popular sinônimos.
3. Refatorar `_TIPOS_PRODUTO_PALAVRAS` para ler do banco.
4. Ajustar `catalogo_campos.py`: `CAMPO_MODELO.produtos_aplicaveis` para todos os
   produtos e pergunta genérica.
5. Validar com o catálogo atual e com a inclusão do tipo "Controle de Acesso".

---

**Registrado em:** 2026-07-23  
**Responsável:** Arquiteto de Sistemas
