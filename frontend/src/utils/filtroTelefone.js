// Filtro da lista de telefones da aba Chat, com curinga `*` (qualquer sequência, inclusive vazia):
//   *73*    contém 73
//   *73     termina com 73
//   +5519*  começa com +5519
// Sem `*`, um texto com menos de 10 caracteres vale como *X* (busca parcial) e um com 10 ou
// mais, como número exato. Espaços digitados são ignorados.

const TAMANHO_PARCIAL = 10

function escaparRegex(texto) {
  return texto.replace(/[.+?^${}()|[\]\\]/g, '\\$&')
}

// Função (telefone) => boolean para o padrão digitado; padrão vazio aceita tudo.
export function criarFiltroTelefone(padrao) {
  let p = (padrao || '').replace(/\s+/g, '')
  if (!p) return () => true
  if (!p.includes('*') && p.length < TAMANHO_PARCIAL) p = `*${p}*`
  const regex = new RegExp(`^${p.split('*').map(escaparRegex).join('.*')}$`)
  return (telefone) => regex.test(telefone || '')
}
