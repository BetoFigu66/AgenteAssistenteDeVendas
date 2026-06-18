/** Número exibido ao usuário (sequencial por contato quando existir; senão id interno). */
export function numeroAtendimentoExibicao(atendimento) {
  if (!atendimento) return null
  const n = atendimento.numero_atendimento_cliente
  if (n !== null && n !== undefined) return n
  return atendimento.id
}

export function rotuloAtendimento(atendimento) {
  const n = numeroAtendimentoExibicao(atendimento)
  return n != null ? `Atendimento #${n}` : 'Atendimento'
}
