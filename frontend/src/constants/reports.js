export const CATEGORIAS = [
  { valor: 'classificacao', label: 'Classificação', descricao: 'Intenção ou entidades erradas' },
  { valor: 'fluxo', label: 'Fluxo', descricao: 'Orquestração/roteamento errado' },
  { valor: 'template', label: 'Template', descricao: 'Texto/tom da resposta' },
  { valor: 'resposta_inadequada', label: 'Resposta Inadequada', descricao: 'Resposta do agente reprovada pelo usuário' },
  { valor: 'dados', label: 'Dados', descricao: 'Dados incorretos (CNPJ, contato, etc.)' },
  { valor: 'llm', label: 'LLM', descricao: 'Problema com a LLM' },
  {
    valor: 'escalonamento_indevido',
    label: 'Escalonamento indevido',
    descricao: 'Escalonamento avaliado como indevido no painel (aberto automaticamente)',
  },
  { valor: 'duvida', label: 'Dúvida', descricao: 'Pergunta sobre o sistema; respondida pela IA ou pela equipe' },
  { valor: 'sugestao', label: 'Sugestão', descricao: 'Ideia de melhoria' },
  { valor: 'outro', label: 'Outro', descricao: 'Outra categoria' },
]

// Categorias que não apontam defeito: aba própria ("Dúvidas e Sugestões") e, com a caixa
// marcada, o Claude só responde (espelha `CATEGORIAS_DUVIDA_SUGESTAO` do backend).
export const CATEGORIAS_DUVIDA_SUGESTAO = ['duvida', 'sugestao']
export const ehDuvidaOuSugestao = (c) => CATEGORIAS_DUVIDA_SUGESTAO.includes(c)

// Quem escreveu uma resposta a um report (`respostas_report.origem` no backend): a IA (goal
// do Claude pela ponte) ou um usuário da equipe, identificado pelo nome.
export const ORIGENS_RESPOSTA = {
  claude: { cor: 'bg-purple-100 text-purple-800' },
  equipe: { cor: 'bg-blue-100 text-blue-800' },
}

// "pela IA" / "por Ana": complemento de "Respondida ..." para uma resposta.
export const quemRespondeu = (r) =>
  r.origem === 'claude' ? 'pela IA' : `por ${r.autor || 'equipe de desenvolvimento'}`

// Etiqueta da lista: "Respondida pela IA", "Respondida por Ana", "Respondida pela IA e por Ana".
export const etiquetaRespondida = (respostas) =>
  `Respondida ${[...new Set((respostas || []).map(quemRespondeu))].join(' e ')}`

export const SEVERIDADES = [
  { valor: 'baixa', label: 'Baixa', cor: 'bg-gray-100 text-gray-700' },
  { valor: 'media', label: 'Média', cor: 'bg-blue-100 text-blue-700' },
  { valor: 'alta', label: 'Alta', cor: 'bg-orange-100 text-orange-700' },
  { valor: 'critica', label: 'Crítica', cor: 'bg-red-100 text-red-700' },
]

export const STATUS = [
  { valor: 'aberto', label: 'Aberto', cor: 'bg-yellow-100 text-yellow-800' },
  { valor: 'em_analise', label: 'Em análise', cor: 'bg-blue-100 text-blue-800' },
  { valor: 'aguardando_fix', label: 'Aguardando fix', cor: 'bg-purple-100 text-purple-800' },
  { valor: 'resolvido', label: 'Resolvido', cor: 'bg-green-100 text-green-800' },
  { valor: 'descartado', label: 'Descartado', cor: 'bg-gray-200 text-gray-600' },
]

export const STATUS_ABERTOS = ['aberto', 'em_analise', 'aguardando_fix']

// Espelha `_TRANSICOES_STATUS_REPORT` do backend (backend/main.py) — usado só
// para restringir as opções do <select> de status na UI; a validação de
// verdade é sempre feita no backend em `PATCH /api/reports/{id}`.
export const TRANSICOES_STATUS = {
  aberto: ['em_analise', 'descartado'],
  em_analise: ['aguardando_fix', 'resolvido', 'descartado'],
  aguardando_fix: ['resolvido', 'em_analise'],
  resolvido: ['em_analise'],
  descartado: ['em_analise'],
}

export const statusPermitidos = (statusAtual) => [
  statusAtual,
  ...(TRANSICOES_STATUS[statusAtual] || []),
]

export const corSeveridade = (sev) =>
  SEVERIDADES.find((s) => s.valor === sev)?.cor || 'bg-gray-100 text-gray-700'

export const corStatus = (st) =>
  STATUS.find((s) => s.valor === st)?.cor || 'bg-gray-100 text-gray-700'

export const labelCategoria = (c) =>
  CATEGORIAS.find((x) => x.valor === c)?.label || c

export const labelStatus = (s) =>
  STATUS.find((x) => x.valor === s)?.label || s

export const labelSeveridade = (s) =>
  SEVERIDADES.find((x) => x.valor === s)?.label || s
