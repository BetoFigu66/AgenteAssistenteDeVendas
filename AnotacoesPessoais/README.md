# AnotacoesPessoais

Área pessoal para **cada colaborador** guardar arquivos de uso durante o trabalho no projeto.

## Propósito

Um lugar comum, dentro do repositório local, para:

- Rascunhos, anotações e checklists pessoais
- Mensagens de teste manual (ex: roteiros para o WhatsApp)
- Planilhas de apoio (ex: `RT.xlsx`)
- Capturas de tela e imagens de referência
- Scripts/comandos pessoais que ainda não viraram documentação oficial
- Logs e saídas de testes ad-hoc

## Regras

1. **Nada aqui é commitado no Git.** A pasta está no `.gitignore` (apenas este `README.md` é versionado).
2. **Não colocar dados reais de clientes** (LGPD). Use apenas dados fictícios/sanitizados.
3. **Não colocar segredos** (API keys, senhas, tokens). Esses vão no `.env` local.
4. Se uma anotação aqui virar algo útil para o time, **mover/promover** para o lugar apropriado:
   - Comandos/dicas reutilizáveis → `docs/comandos_uteis.md`
   - Decisões arquiteturais → `artefatos/arquiteto_de_sistemas/`
   - Requisitos → `artefatos/analista_de_requisitos/`
   - Código produtivo → `backend/` ou `frontend/`

## Organização sugerida

Cada colaborador pode criar uma subpasta com seu nome para evitar misturar arquivos:

```
AnotacoesPessoais/
├── README.md          (versionado)
├── Beto/              (ignorado pelo git)
├── Kika/              (ignorado pelo git)
└── imagens/           (ignorado pelo git)
```

## Como verificar que algo não vai subir

```powershell
git status
git check-ignore -v AnotacoesPessoais/meu_arquivo.txt
```

Se `git check-ignore` retornar a regra do `.gitignore`, está protegido.
