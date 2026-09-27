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

// Para quem vende, não para quem programa: dizem o que aconteceu na conversa. Os números
// (quantidade lida, limite vigente) ficam nas evidências, logo abaixo. Espelhados em
// `LABEL_GATILHO_ESCALONAMENTO` (backend/services/escalonamentos.py), que usa os mesmos
// textos na descrição do report de escalonamento indevido.
const GATILHO_LABELS = {
  intencao_escalar_humano: 'Cliente pediu para falar com uma pessoa',
  intencao_reclamar: 'Cliente reclamou ou demonstrou insatisfação',
  quantidade_minima: 'Cliente pediu muitos equipamentos de uma vez',
  faixa_funcionarios: 'Empresa do cliente tem muitos funcionários',
  leitor_facial: 'Cliente falou em leitor facial',
  baixa_confianca_repetida: 'O sistema não entendeu várias mensagens seguidas',
  base_sem_resposta: 'O sistema não tinha resposta para a pergunta',
  tentativas_esgotadas: 'O sistema não conseguiu identificar o modelo do equipamento',
  assumido_pelo_vendedor: 'Vendedor assumiu a conversa',
}

export function labelGatilhoEscalonamento(gatilho) {
  return GATILHO_LABELS[gatilho] || gatilho
}

const AVALIACAO_LABELS = {
  procedente: 'Procedente',
  indevido: 'Indevido',
  // Valor do histórico do report quando a avaliação é desfeita (services/escalonamentos.py).
  nao_avaliado: 'Não avaliado',
}

export function labelAvaliacaoEscalonamento(avaliacao) {
  if (!avaliacao) return 'Não avaliado'
  return AVALIACAO_LABELS[avaliacao] || avaliacao
}

const ORIGEM_CLASSIFICACAO_LABELS = {
  regra: 'identificada por regra',
  llm: 'identificada pela IA',
}

// "pedir_orcamento" → "Pedir orçamento": fallback para valor sem rótulo.
function capitalizarValor(valor) {
  const texto = String(valor).replace(/_/g, ' ')
  return texto.charAt(0).toUpperCase() + texto.slice(1)
}

// Espelha `Intencao` de backend/services/classificador.py. Intenção nova sem entrada aqui
// sai pelo fallback (`capitalizarValor`), sem acento.
const INTENCAO_LABELS = {
  saudacao: 'Saudação',
  fornecer_cnpj: 'Informar CNPJ',
  fornecer_cpf: 'Informar CPF',
  fornecer_nome: 'Informar nome',
  fornecer_data_nascimento: 'Informar data de nascimento',
  confirmar: 'Confirmar',
  negar: 'Negar',
  pedir_orcamento: 'Pedir orçamento',
  pedir_catalogo: 'Pedir catálogo',
  perguntar_disponibilidade: 'Perguntar disponibilidade',
  perguntar_preco: 'Perguntar preço',
  perguntar_produto: 'Perguntar sobre produto',
  perguntar_prazo: 'Perguntar prazo',
  aprovar_orcamento: 'Aprovar orçamento',
  reprovar_orcamento: 'Recusar orçamento',
  reclamar: 'Reclamação',
  escalar_humano: 'Pedir atendente',
  fora_contexto: 'Fora do assunto',
  desconhecido: 'Não identificada',
}

export function labelIntencao(intencao) {
  if (!intencao) return 'Não identificada'
  return INTENCAO_LABELS[intencao] || capitalizarValor(intencao)
}

// Espelha `NivelConfianca` de backend/services/classificador.py.
const NIVEL_CONFIANCA_LABELS = {
  alta: 'Alta',
  media: 'Média',
  baixa: 'Baixa',
}

export function labelNivelConfianca(nivel) {
  if (!nivel) return ''
  return NIVEL_CONFIANCA_LABELS[nivel] || capitalizarValor(nivel)
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

  // Classificação: "Intenção: Reclamação, confiança 0,90 (Alta), identificada pela IA".
  if (presente(ev, 'intencoes') || presente(ev, 'confianca')) {
    usar('intencoes', 'confianca', 'confianca_nivel', 'origem_classificacao')
    const intencoes = Array.isArray(ev.intencoes) ? ev.intencoes : []
    const partes = [intencoes.length > 0 ? intencoes.map(labelIntencao).join(', ') : 'nenhuma']
    if (typeof ev.confianca === 'number') {
      const nivel = labelNivelConfianca(ev.confianca_nivel)
      partes.push(`confiança ${numeroBR(ev.confianca, 2)}${nivel ? ` (${nivel})` : ''}`)
    }
    if (ev.origem_classificacao) {
      partes.push(ORIGEM_CLASSIFICACAO_LABELS[ev.origem_classificacao] || `identificada por ${ev.origem_classificacao}`)
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
