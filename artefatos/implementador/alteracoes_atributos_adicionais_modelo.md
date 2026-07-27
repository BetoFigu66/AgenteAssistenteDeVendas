# Handoff: Atributos Adicionais do Modelo

## Contexto

Criada a tabela `atributos_adicionais_modelo` para armazenar atributos específicos de cada modelo de produto, mantendo a tabela `modelos` apenas com os campos comuns a todos os modelos. Isso evita duplicação de informação e facilita a inclusão de novos tipos de produto sem alterar o schema da tabela `modelos`.

## Schema

- Tabela: `atributos_adicionais_modelo`
- Colunas: `id`, `modelo_id` (FK `modelos.id` ON DELETE CASCADE), `chave`, `valor`, `ativo`, `created_at`, `updated_at`.
- Índices: `modelo_id`, `chave`, `valor`.
- Constraint única: `(modelo_id, chave, valor)`.

## Pontos alterados

### 1. Banco de dados

Migration:
- `backend/alembic/versions/2026072301_adiciona_atributos_adicionais_modelo.py`
  - Cria tabela e índices.
  - `down_revision` aponta para `2026072216`.

### 2. ORM

- `backend/models.py`
  - Adicionado `AtributoAdicionalModelo` com relacionamento `modelo`.
  - `Modelo` recebeu relacionamento `atributos` com `cascade="all, delete-orphan"`.
  - `Modelo.to_dict()` agora inclui `"atributos"`.

### 3. Importador de catálogo

- `backend/scripts/importar_catalogo_csv.py`
  - Importa `AtributoAdicionalModelo`.
  - Adicionado mapeamento `_ATRIBUTOS_POR_PALAVRA` que detecta na coluna `modelo` atributos de `tecnologia_leitura` (biometria, facial, cartao, cartografico, barras, qr_code).
  - `LinhaCatalogo` agora carrega `atributos: frozenset[tuple[str, str]]`.
  - Função `_extrair_atributos(descricao)` gera os pares chave/valor.
  - Deduplicação de modelos leva em conta os atributos.
  - Importação sincroniza atributos existentes (inativa os removidos, adiciona os novos).
  - Planilha ativa continua sendo `artefatos/implementador/planilha_catalogo_modelos_v2.csv`.

### 4. Classificador de intenções

- `backend/services/classificador.py`
  - `EntidadesExtraidas` ganhou campo `atributos: Dict[str, str]`.
  - Adicionado `_ATRIBUTOS_MENSAGEM_PALAVRAS` para extrair `tecnologia_leitura` da mensagem do cliente.
  - `extrair_entidades()` popula `atributos` mantendo `tipo_leitor_mencionado` para compatibilidade.
  - Prompt do LLM atualizado para retornar `entidades.atributos`.
  - Parsing do LLM inclui `atributos`.
  - Classificador híbrido combina atributos de regras e LLM (regras têm prioridade).

### 5. Processador / resolução de modelo

- `backend/services/processador.py`
  - Importa `AtributoAdicionalModelo` e `and_`.
  - `_atualizar_infos_atendimento()` persiste atributos genéricos em `AtendimentoInfo` usando a mesma chave da tabela `atributos_adicionais_modelo`.
  - `_tentar_resolver_modelo()`:
    - Mescla atributos salvos em `AtendimentoInfo` com os extraídos na mensagem.
    - Mapeia `tipo_leitor_mencionado` legado para `tecnologia_leitura`.
    - Filtra modelos exigindo que possuam todos os atributos extraídos.
  - `_gerar_resumo_finalizando()` inclui `atributos` no contexto.
  - `_montar_resumo_escalonamento()` lista atributos do modelo resolvido.

### 6. Catálogo de campos da conversação

- `backend/services/conversacao/catalogo_campos.py`
  - `CAMPO_MODELO.produtos_aplicaveis` expandido para produtos além de `relogio_ponto`: catraca, cancela, leitor facial/biometria, camera, controle de acesso, controle por cartão, bastão de ronda, roteador.
  - Pergunta tornada genérica, mencionando tecnologias comuns a vários produtos.

### 7. Sinônimos de produtos

- `backend/services/classificador.py` (`_TIPOS_PRODUTO_PALAVRAS`)
  - Adicionados sinônimos para cancela, leitor facial, leitor biométrico, câmera, controle de acesso, controle por cartão, bastão de ronda e roteador.

### 8. Respostas / resumos

- `backend/services/respostas/transformers.py`
  - `montar_resumo_finalizando()` lista atributos do modelo quando presentes.

### 9. Testes

- `backend/tests/test_extracao_entidades_fase_d.py`
  - Testes de extração de atributos genéricos (`tecnologia_leitura`) e compatibilidade com `tipo_leitor_mencionado`.
- `backend/tests/test_importar_catalogo_atributos.py` (novo)
  - Testa importação de atributos a partir da descrição do modelo.
- `backend/tests/test_processador_resolucao_atributos.py` (novo)
  - Testa resolução de modelo com atributos e ausência de match.

## Como reimportar o catálogo

```powershell
# Aplica a migration (se ainda não estiver em head)
& venv\Scripts\Activate.ps1
alembic upgrade head

# Reimporta o catálogo com os atributos
python scripts/importar_catalogo_csv.py --aplicar
```

## Compatibilidade

- `tipo_leitor_mencionado` continua sendo extraído e mapeado para `tecnologia_leitura` para não quebrar lógicas existentes que o consumam diretamente.
- Atributos são persistidos em `AtendimentoInfo.chave` usando a chave do atributo (ex.: `tecnologia_leitura`).

## Próximos passos sugeridos

1. Avaliar se outros atributos do catálogo devem migrar para `atributos_adicionais_modelo` (ex.: conectividade, alimentação, certificações).
2. Criar interface no painel administrativo para editar atributos por modelo sem depender da planilha.
3. Adicionar validação de atributos conhecidos em `AtendimentoInfo` para evitar chaves livres indesejadas.
