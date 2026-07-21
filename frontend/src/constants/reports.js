export const CATEGORIAS = [
  { valor: 'classificacao', label: 'Classificação', descricao: 'Intenção ou entidades erradas' },
  { valor: 'fluxo', label: 'Fluxo', descricao: 'Orquestração/roteamento errado' },
  { valor: 'template', label: 'Template', descricao: 'Texto/tom da resposta' },
  { valor: 'resposta_inadequada', label: 'Resposta Inadequada', descricao: 'Resposta do agente reprovada pelo usuário' },
  { valor: 'dados', label: 'Dados', descricao: 'Dados incorretos (CNPJ, contato, etc.)' },
  { valor: 'llm', label: 'LLM', descricao: 'Problema com a LLM' },
  { valor: 'outro', label: 'Outro', descricao: 'Outra categoria' },
]

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
  aberto: ['em_analise', 'aguardando_fix', 'descartado'],
  em_analise: ['aguardando_fix', 'resolvido', 'descartado', 'aberto'],
  aguardando_fix: ['resolvido', 'descartado', 'em_analise'],
  resolvido: ['aberto'],
  descartado: ['aberto'],
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
