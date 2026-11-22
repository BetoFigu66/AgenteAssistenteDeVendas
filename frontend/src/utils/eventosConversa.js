// Eventos do atendimento (mudança de fase, escalonamento, modo de operação...) intercalados na
// conversa do Acompanhamento. Um evento com `mensagem_id` de uma mensagem da lista entra logo
// depois dela: é a mensagem que o provocou. Os demais (ação manual no painel, mensagem fora da
// lista) entram na posição do horário.

import { labelMotivoEncerramento, labelMotivoEscalonamento, rotuloFase } from './atendimento'

const MODO = { agente: 'Agente (IA)', humano: 'Humano' }

/** Texto curto do evento para o marcador na conversa: { titulo, detalhe }. */
export function descreverEvento(ev) {
  switch (ev.tipo) {
    case 'fase_alterada':
      return { titulo: `Fase: ${rotuloFase(ev.estado_anterior)} → ${rotuloFase(ev.estado_novo)}`, detalhe: ev.motivo }
    case 'escalado':
      return { titulo: 'Escalado para humano', detalhe: labelMotivoEscalonamento(ev.motivo) }
    case 'modo_operacao_alterado':
      return {
        titulo: `Modo: ${MODO[ev.estado_anterior] || ev.estado_anterior || '—'} → ${MODO[ev.estado_novo] || ev.estado_novo || '—'}`,
        detalhe: ev.motivo,
      }
    case 'criado':
      return { titulo: 'Atendimento criado', detalhe: null }
    case 'encerrado':
      return { titulo: 'Atendimento encerrado', detalhe: labelMotivoEncerramento(ev.motivo) || ev.motivo }
    case 'reaberto':
      return { titulo: 'Atendimento reaberto', detalhe: ev.motivo }
    default:
      return { titulo: ev.tipo, detalhe: ev.motivo }
  }
}

const instante = (t) => (t ? new Date(t).getTime() : 0)

/**
 * Lista única para renderizar: { tipo: 'mensagem', msg, eventos } e { tipo: 'evento', ev }.
 * `mensagens` vem em ordem cronológica; a ordem dela é preservada.
 */
export function intercalarEventos(mensagens, eventos) {
  const ids = new Set(mensagens.map((m) => m.id))
  const porMensagem = new Map()
  const soltos = []
  for (const ev of [...(eventos || [])].sort((a, b) => instante(a.timestamp) - instante(b.timestamp))) {
    if (ev.mensagem_id && ids.has(ev.mensagem_id)) {
      if (!porMensagem.has(ev.mensagem_id)) porMensagem.set(ev.mensagem_id, [])
      porMensagem.get(ev.mensagem_id).push(ev)
    } else {
      soltos.push(ev)
    }
  }
  const itens = []
  let i = 0
  for (const msg of mensagens) {
    while (i < soltos.length && instante(soltos[i].timestamp) < instante(msg.timestamp)) {
      itens.push({ tipo: 'evento', ev: soltos[i++] })
    }
    itens.push({ tipo: 'mensagem', msg, eventos: porMensagem.get(msg.id) || [] })
  }
  while (i < soltos.length) itens.push({ tipo: 'evento', ev: soltos[i++] })
  return itens
}
