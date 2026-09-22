/**
 * Resolvedor dos textos de ajuda por tela.
 *
 * Cada tela do painel tem um arquivo Markdown neste diretorio (ex: `reports.md`),
 * carregado em tempo de build pelo `import.meta.glob` do Vite. Para adicionar ajuda
 * a uma tela nova basta criar o `.md` e montar `<BotaoAjuda contexto="..." />` nela:
 * nao e preciso registrar o arquivo em lugar nenhum.
 *
 * Ver `README.md` neste diretorio para a convencao completa.
 */

const arquivos = import.meta.glob('./*.md', {
  query: '?raw',
  import: 'default',
  eager: true,
})

const CHAVE_FALLBACK = 'geral'

/**
 * Retorna o texto de ajuda de um contexto, subindo a hierarquia ate achar um arquivo.
 *
 * O contexto usa pontos para indicar especificidade crescente, entao
 * 'reports.detalhe' tenta `reports.detalhe.md`, depois `reports.md` e por fim
 * `geral.md`. Isso permite criar ajuda especifica de uma subarea sem precisar
 * duplicar o texto da tela inteira.
 *
 * @param {string} contexto Identificador da tela/subarea (ex: 'reports').
 * @returns {string|null} Conteudo Markdown, ou null se nem o fallback existir.
 */
export function obterAjuda(contexto) {
  const partes = String(contexto || '').split('.').filter(Boolean)

  while (partes.length > 0) {
    const texto = arquivos[`./${partes.join('.')}.md`]
    if (texto) return texto
    partes.pop()
  }

  return arquivos[`./${CHAVE_FALLBACK}.md`] ?? null
}
