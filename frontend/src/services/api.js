const API_URL = import.meta.env.VITE_API_URL || ''

class ApiError extends Error {
  constructor(message, status, type = 'api') {
    super(message)
    this.status = status
    this.type = type
  }
}

export const api = {
  async listarTelefones() {
    try {
      const response = await fetch(`${API_URL}/api/telefones`)
      if (!response.ok) {
        throw new ApiError('Erro ao listar telefones', response.status, 'server')
      }
      return response.json()
    } catch (error) {
      if (error instanceof ApiError) throw error
      throw new ApiError('Backend não está respondendo', 0, 'network')
    }
  },

  async obterHistorico(telefone) {
    try {
      const response = await fetch(`${API_URL}/api/historico/${encodeURIComponent(telefone)}`)
      if (!response.ok) {
        if (response.status === 500) {
          throw new ApiError('Erro interno do servidor (500)', 500, 'server')
        }
        throw new ApiError('Erro ao obter histórico', response.status, 'server')
      }
      return response.json()
    } catch (error) {
      if (error instanceof ApiError) throw error
      throw new ApiError('Backend não está respondendo', 0, 'network')
    }
  },

  async enviarMensagem(telefone, mensagem) {
    try {
      const response = await fetch(`${API_URL}/api/mensagem`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ telefone, mensagem }),
      })
      if (!response.ok) {
        if (response.status === 500) {
          throw new ApiError('Erro interno do servidor (500)', 500, 'server')
        }
        throw new ApiError('Erro ao enviar mensagem', response.status, 'server')
      }
      return response.json()
    } catch (error) {
      if (error instanceof ApiError) throw error
      throw new ApiError('Backend não está respondendo', 0, 'network')
    }
  },

  async healthCheck() {
    try {
      const response = await fetch(`${API_URL}/health`)
      if (!response.ok) throw new ApiError('API não disponível', response.status, 'server')
      return response.json()
    } catch (error) {
      if (error instanceof ApiError) throw error
      throw new ApiError('Backend não está respondendo', 0, 'network')
    }
  },
}

export { ApiError }
