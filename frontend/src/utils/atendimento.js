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

const FASE_LABELS = {
  esclarecendo: 'Esclarecendo',
  finalizando: 'Finalizando',
  em_orcamentacao: 'Em orçamentação',
}

const FASE_CLASSES = {
  esclarecendo: 'bg-gray-100 text-gray-600',
  finalizando: 'bg-inforrel-secondary/10 text-inforrel-secondary',
  em_orcamentacao: 'bg-inforrel-accent/10 text-inforrel-accent',
}

/** Rótulo legível da fase do atendimento (REQ-010). */
export function rotuloFase(fase) {
  return FASE_LABELS[fase] || fase || '—'
}

/** Classes Tailwind do badge de fase — uma cor por fase (esclarecendo/finalizando/em_orcamentacao). */
export function classesFase(fase) {
  return FASE_CLASSES[fase] || 'bg-gray-100 text-gray-600'
}

const MOTIVO_ESCALONAMENTO_LABELS = {
  solicitado_cliente: 'Cliente pediu para falar com atendente',
  reclamacao: 'Reclamação/insatisfação do cliente',
  projeto_complexo: 'Projeto complexo (quantidade/porte/leitor facial)',
  baixa_confianca: 'Baixa confiança do classificador (mensagens repetidamente ambíguas)',
  base_insuficiente: 'Base de conhecimento sem conteúdo suficiente',
  manual_vendedor: 'Assumido manualmente pelo vendedor',
}

/** Rótulo legível do motivo de escalonamento (REQ-004, Fase 5). */
export function labelMotivoEscalonamento(motivo) {
  if (!motivo) return 'Em modo humano'
  return MOTIVO_ESCALONAMENTO_LABELS[motivo] || motivo
}
