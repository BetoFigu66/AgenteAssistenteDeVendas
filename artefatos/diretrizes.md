# Diretriz: Paridade entre WSL e PowerShell

## Objetivo
Garantir que toda instrução, script de instalação ou comando de execução documentado para o projeto seja disponibilizado tanto para WSL quanto para PowerShell.

## Regra geral

Sempre que um novo conteúdo técnico for produzido e incluir:

- scripts de shell (`.sh`);
- instruções de instalação ou configuração;
- comandos de execução do projeto;
- exemplos de uso de `git`, `docker`, `python`, `npm`, `venv`, etc.;

ele deve ser acompanhado por uma variante equivalente para PowerShell ou uma indicação clara de compatibilidade.

## Como aplicar

1. Documente dois blocos separados quando houver comandos específicos de plataforma:
   - WSL / Linux / macOS
   - PowerShell / Windows
2. Se um script `.sh` for criado, forneça também o mesmo fluxo em PowerShell ou explique como o comando deve ser adaptado.
3. Se o comando funcionar em ambas as plataformas sem alteração, deixe explícito:
   - `Funciona em WSL e PowerShell`
4. Se houver limitações técnicas ou pré-requisitos distintos, registre-os claramente.

## Exemplo de formato recomendado

### PowerShell
```powershell
cd C:\caminho\para\projeto
.\.venv\Scripts\Activate.ps1
python agentes\scripts\gerente_de_projetos\gera_sprint_report.py ...
```

### WSL / Linux
```bash
cd /mnt/c/caminho/para/projeto
source .venv/bin/activate
python agentes/scripts/gerente_de_projetos/gera_sprint_report.py ...
```

## Exceções

- Quando um recurso só existe em WSL ou só em PowerShell, documente explicitamente essa limitação.
- Se a instrução for estritamente para ambiente Linux e não for aplicável em Windows, inclua um aviso claro.

## Local de referência

Esta diretriz deve ser usada como referência sempre que:

- documentar novos scripts em `agentes/scripts/`;
- atualizar `README.md`, `backend/README.md`, `frontend/README.md`, `docs/comandos_uteis.md` ou artefatos de infraestrutura;
- criar comandos de setup para contêineres, virtualenv ou ferramentas externas.

## Benefício

A regra garante que a equipe e os colaboradores possam reproduzir os procedimentos em cada ambiente de desenvolvimento comum, evitando erros por diferenças entre o terminal WSL e o terminal PowerShell.