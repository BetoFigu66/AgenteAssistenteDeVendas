# WebScrapping - Inforrel

Script para fazer scraping recursivo do site `https://inforrel.com.br/` e salvar o conteúdo de cada página em arquivos `.txt`.

## Como funciona

- Inicia pela URL base (`https://inforrel.com.br/`)
- Extrai o texto visível (sem `<script>`, `<style>` etc.) e salva em `result/<slug-da-url>.txt`
- Encontra todos os links internos da página e visita recursivamente (BFS)
- Mantém um conjunto de URLs já visitadas em memória para não acessar a mesma página mais de uma vez
- Ignora links externos, `mailto:`, `tel:` e arquivos binários (PDF, imagens, etc.)

## Instalação

```bash
cd WebScrapping
pip install -r requirements.txt
```

## Execução

```bash
python scraper.py
```

Os arquivos serão gerados em `WebScrapping/result/`.

## Configurações

Edite as constantes no topo de `scraper.py`:

- `BASE_URL`: URL inicial
- `REQUEST_DELAY`: delay entre requisições (segundos)
- `REQUEST_TIMEOUT`: timeout de cada requisição

## Nomes de arquivo

Derivados do caminho (path) da URL:

| URL | Arquivo |
|-----|---------|
| `https://inforrel.com.br/` | `index.txt` |
| `https://inforrel.com.br/produtos` | `produtos.txt` |
| `https://inforrel.com.br/cat/relogios/` | `cat_relogios.txt` |
