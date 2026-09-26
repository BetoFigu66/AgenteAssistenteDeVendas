/**
 * Rótulos e formatação do registro de escalonamento (REQ-004.5B/5C).
 *
 * Espelha `GatilhoEscalonamento` e `AvaliacaoEscalonamento` de
 * backend/models/atendimento.py, e as chaves de `Escalonamento.evidencias` gravadas em
 * services/processador.py, services/conversacao/regras_globais.py,
 * services/conversacao/estados/finalizando.py e no takeover manual (main.py). Chave ou
 * gatilho sem entrada aqui cai no fallback genérico (o próprio valor técnico), para um
 * gatilho novo no backend aparecer na tela mesmo antes de ganhar rótulo.
 */

const GATILHO_LABELS = {
  intencao_escalar_humano: 'Cliente pediu para falar com uma pessoa',
  intencao_reclamar: 'Cliente reclamou ou demonstrou insatisfação',
  quantidade_minima: 'Quantidade de equipamentos acima do mínimo',
  faixa_funcionarios: 'Número de funcionários acima do limiar',
  leitor_facial: 'Leitor facial mencionado',
  baixa_confianca_repetida: 'Confiança baixa em mensagens seguidas',
  base_sem_resposta: 'Base de conhecimento sem resposta',
  tentativas_esgotadas: 'Tentativas de identificar o modelo esgotadas',
  assumido_pelo_vendedor: 'Assumido pelo vendedor no painel',
}

export function labelGatilhoEscalonamento(gatilho) {
  return GATILHO_LABELS[gatilho] || gatilho
}

const AVALIACAO_LABELS = {
  procedente: 'Procedente',
  indevido: 'Indevido',
}

export function labelAvaliacaoEscalonamento(avaliacao) {
  if (!avaliacao) return 'Não avaliado'
  return AVALIACAO_LABELS[avaliacao] || avaliacao
}

const ORIGEM_CLASSIFICACAO_LABELS = {
  regra: 'por regra',
  llm: 'por LLM',
}

// Rótulos das chaves do fallback genérico e de `sinais_extraidos`.
const CHAVE_LABELS = {
  marca: 'marca',
  aplicacao: 'aplicação',
  tipo_leitor: 'tipo de leitor',
  origem_acao: 'Origem da ação',
  ator: 'Quem assumiu',
}

function rotuloChave(chave) {
  return CHAVE_LABELS[chave] || chave
}

function numeroBR(valor, casas) {
  if (typeof valor !== 'number') return String(valor)
  if (casas === undefined) return valor.toLocaleString('pt-BR')
  return valor.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas })
}

function simNao(valor) {
  return valor ? 'sim' : 'não'
}

function presente(evidencias, chave) {
  return Object.prototype.hasOwnProperty.call(evidencias, chave)
}

/** Valor qualquer em texto legível (fallback genérico). */
export function formatarValorEvidencia(valor) {
  if (valor === null || valor === undefined || valor === '') return 'não informado'
  if (typeof valor === 'boolean') return simNao(valor)
  if (typeof valor === 'number') return numeroBR(valor)
  if (Array.isArray(valor)) {
    return valor.length === 0 ? 'nenhum' : valor.map(formatarValorEvidencia).join(', ')
  }
  if (typeof valor === 'object') {
    const partes = Object.entries(valor).map(([k, v]) => `${rotuloChave(k)}: ${formatarValorEvidencia(v)}`)
    return partes.length === 0 ? 'nenhum' : partes.join('; ')
  }
  return String(valor)
}

/**
 * Converte `evidencias` em linhas legíveis. As chaves conhecidas viram frases (algumas
 * agrupadas: valor lido + limiar numa linha só); as demais saem como "chave: valor".
 *
 * @param {Record<string, unknown>|null|undefined} evidencias
 * @returns {string[]}
 */
export function linhasEvidencias(evidencias) {
  if (!evidencias || typeof evidencias !== 'object') return []
  const ev = evidencias
  const usadas = new Set()
  const linhas = []
  const usar = (...chaves) => chaves.forEach((c) => usadas.add(c))

  // Classificação: "Intenção: reclamar, confiança 0,90 (alta), por LLM".
  if (presente(ev, 'intencoes') || presente(ev, 'confianca')) {
    usar('intencoes', 'confianca', 'confianca_nivel', 'origem_classificacao')
    const intencoes = Array.isArray(ev.intencoes) ? ev.intencoes : []
    const partes = [
      intencoes.length > 0 ? intencoes.map((i) => String(i).replace(/_/g, ' ')).join(', ') : 'nenhuma',
    ]
    if (typeof ev.confianca === 'number') {
      partes.push(`confiança ${numeroBR(ev.confianca, 2)}${ev.confianca_nivel ? ` (${ev.confianca_nivel})` : ''}`)
    }
    if (ev.origem_classificacao) {
      partes.push(ORIGEM_CLASSIFICACAO_LABELS[ev.origem_classificacao] || `por ${ev.origem_classificacao}`)
    }
    linhas.push(`${intencoes.length > 1 ? 'Intenções' : 'Intenção'}: ${partes.join(', ')}`)
  }

  // Projeto complexo: as três condições, disparadas ou não, com o limiar vigente.
  if (presente(ev, 'quantidades')) {
    usar('quantidades', 'quantidade_minima')
    const qtds = Array.isArray(ev.quantidades) ? ev.quantidades : []
    const lidas = qtds.length > 0 ? qtds.map((q) => numeroBR(q)).join(', ') : 'nenhuma'
    const minimo = ev.quantidade_minima != null ? ` (mínimo ${numeroBR(ev.quantidade_minima)})` : ''
    linhas.push(`Quantidades lidas: ${lidas}${minimo}`)
  }
  if (presente(ev, 'faixa_funcionarios')) {
    usar('faixa_funcionarios', 'limiar_funcionarios')
    const faixa = ev.faixa_funcionarios != null ? numeroBR(ev.faixa_funcionarios) : 'não informada'
    const limiar = ev.limiar_funcionarios != null ? ` (limiar ${numeroBR(ev.limiar_funcionarios)})` : ''
    linhas.push(`Faixa de funcionários: ${faixa}${limiar}`)
  }
  if (presente(ev, 'tipo_leitor_mencionado')) {
    usar('tipo_leitor_mencionado')
    linhas.push(`Leitor: ${ev.tipo_leitor_mencionado || 'não mencionado'}`)
  }

  // Baixa confiança repetida.
  if (presente(ev, 'ocorrencias_consecutivas')) {
    usar('ocorrencias_consecutivas', 'limiar_confianca_baixa')
    const limiar =
      typeof ev.limiar_confianca_baixa === 'number'
        ? ` (confiança baixa é até ${numeroBR(ev.limiar_confianca_baixa, 2)})`
        : ''
    linhas.push(`Mensagens seguidas com confiança baixa: ${numeroBR(ev.ocorrencias_consecutivas)}${limiar}`)
  }

  // Base insuficiente.
  if (presente(ev, 'qa_encontrado')) {
    usar('qa_encontrado')
    linhas.push(`Resposta na base Q&A: ${ev.qa_encontrado ? 'encontrada' : 'não encontrada'}`)
  }
  if (presente(ev, 'trechos_rag')) {
    usar('trechos_rag', 'rag_score_minimo', 'rag_habilitado')
    const score =
      typeof ev.rag_score_minimo === 'number' ? ` (score mínimo ${numeroBR(ev.rag_score_minimo, 2)})` : ''
    const habilitada = presente(ev, 'rag_habilitado') ? `, RAG habilitada: ${simNao(ev.rag_habilitado)}` : ''
    linhas.push(`Trechos da base de documentos acima do score: ${numeroBR(ev.trechos_rag)}${score}${habilitada}`)
  }
  if (presente(ev, 'clarificacoes_pedidas')) {
    usar('clarificacoes_pedidas')
    linhas.push(`Pedidos de esclarecimento antes de escalar: ${numeroBR(ev.clarificacoes_pedidas)}`)
  }

  // Modelo não reconhecido.
  if (presente(ev, 'tentativas')) {
    usar('tentativas', 'tentativas_maximas')
    const max = ev.tentativas_maximas != null ? ` de ${numeroBR(ev.tentativas_maximas)}` : ''
    linhas.push(`Tentativas de identificar o modelo: ${numeroBR(ev.tentativas)}${max}`)
  }
  if (presente(ev, 'sinais_extraidos')) {
    usar('sinais_extraidos')
    linhas.push(`Sinais extraídos da mensagem: ${formatarValorEvidencia(ev.sinais_extraidos)}`)
  }

  // Takeover manual: `ator` repete o do registro; só a origem da ação é informação nova.
  if (presente(ev, 'origem_acao')) {
    usar('origem_acao', 'ator')
    linhas.push(`Origem da ação: ${ev.origem_acao}`)
  }

  for (const [chave, valor] of Object.entries(ev)) {
    if (usadas.has(chave)) continue
    linhas.push(`${rotuloChave(chave)}: ${formatarValorEvidencia(valor)}`)
  }
  return linhas
}
