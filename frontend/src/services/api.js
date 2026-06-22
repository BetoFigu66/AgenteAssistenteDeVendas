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

  async obterDadosConversa(telefone) {
    try {
      const response = await fetch(`${API_URL}/api/conversa/${encodeURIComponent(telefone)}`)
      if (!response.ok) {
        throw new ApiError('Erro ao obter dados da conversa', response.status, 'server')
      }
      return response.json()
    } catch (error) {
      if (error instanceof ApiError) throw error
      throw new ApiError('Backend não está respondendo', 0, 'network')
    }
  },

  async obterEmpresa(empresaId) {
    try {
      const response = await fetch(`${API_URL}/api/empresas/${empresaId}`)
      if (!response.ok) {
        throw new ApiError('Erro ao obter empresa', response.status, 'server')
      }
      return response.json()
    } catch (error) {
      if (error instanceof ApiError) throw error
      throw new ApiError('Backend não está respondendo', 0, 'network')
    }
  },

  async obterAtendimento(atendimentoId) {
    try {
      const response = await fetch(`${API_URL}/api/atendimentos/${atendimentoId}`)
      if (!response.ok) {
        throw new ApiError('Erro ao obter atendimento', response.status, 'server')
      }
      return response.json()
    } catch (error) {
      if (error instanceof ApiError) throw error
      throw new ApiError('Backend não está respondendo', 0, 'network')
    }
  },

  async obterProcessamento(processamentoId) {
    try {
      const response = await fetch(`${API_URL}/api/processamentos/${processamentoId}`)
      if (!response.ok) {
        throw new ApiError('Erro ao obter processamento', response.status, 'server')
      }
      return response.json()
    } catch (error) {
      if (error instanceof ApiError) throw error
      throw new ApiError('Backend não está respondendo', 0, 'network')
    }
  },

  async criarReportProblema(processamentoId, payload = {}) {
    try {
      const response = await fetch(
        `${API_URL}/api/processamentos/${processamentoId}/reports`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        },
      )
      if (!response.ok) {
        const detail = await response.json().catch(() => null)
        throw new ApiError(
          detail?.detail || 'Erro ao registrar report',
          response.status,
          'server',
        )
      }
      return response.json()
    } catch (error) {
      if (error instanceof ApiError) throw error
      throw new ApiError('Backend não está respondendo', 0, 'network')
    }
  },

  async listarReports(filtros = {}) {
    const params = new URLSearchParams()
    Object.entries(filtros).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') params.append(k, v)
    })
    const qs = params.toString()
    const response = await fetch(`${API_URL}/api/reports${qs ? `?${qs}` : ''}`)
    if (!response.ok) throw new ApiError('Erro ao listar reports', response.status, 'server')
    return response.json()
  },

  async statsReports() {
    const response = await fetch(`${API_URL}/api/reports/stats`)
    if (!response.ok) throw new ApiError('Erro ao obter estatísticas', response.status, 'server')
    return response.json()
  },

  async obterContextoReport(reportId, { antes = 3, depois = 3 } = {}) {
    const response = await fetch(
      `${API_URL}/api/reports/${reportId}/contexto?antes=${antes}&depois=${depois}`,
    )
    if (!response.ok) throw new ApiError('Erro ao obter contexto', response.status, 'server')
    return response.json()
  },

  async baixarPacoteAnaliseReport(reportId, { antes = 5, depois = 3 } = {}) {
    try {
      const params = new URLSearchParams({
        formato: 'yaml',
        antes: String(antes),
        depois: String(depois),
      })
      const response = await fetch(
        `${API_URL}/api/reports/${reportId}/pacote-analise?${params}`,
      )
      if (!response.ok) {
        const detail = await response.json().catch(() => null)
        const msg = detail?.detail || 'Erro ao gerar pacote de análise'
        throw new ApiError(
          typeof msg === 'string' && msg === 'Not Found'
            ? 'Endpoint não encontrado no backend — reinicie o backend (Docker: docker compose up -d backend)'
            : msg,
          response.status,
          'server',
        )
      }
      const yaml = await response.text()
      const blob = new Blob([yaml], { type: 'text/yaml;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `report_${String(reportId).padStart(3, '0')}_pacote_analise.yaml`
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
    } catch (error) {
      if (error instanceof ApiError) throw error
      throw new ApiError('Backend não está respondendo', 0, 'network')
    }
  },

  async atualizarReport(reportId, payload) {
    const response = await fetch(`${API_URL}/api/reports/${reportId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!response.ok) {
      const detail = await response.json().catch(() => null)
      throw new ApiError(detail?.detail || 'Erro ao atualizar report', response.status, 'server')
    }
    return response.json()
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

  // Users
  async listarUsers() {
    const response = await fetch(`${API_URL}/api/users`)
    if (!response.ok) throw new ApiError('Erro ao listar usuários', response.status, 'server')
    return response.json()
  },

  async criarUser(nome) {
    const response = await fetch(`${API_URL}/api/users`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nome }),
    })
    if (!response.ok) {
      const detail = await response.json().catch(() => null)
      throw new ApiError(detail?.detail || 'Erro ao criar usuário', response.status, 'server')
    }
    return response.json()
  },

  // Atendimentos ativos
  async listarAtendimentosAtivos() {
    const response = await fetch(`${API_URL}/api/atendimentos/ativas`)
    if (!response.ok) throw new ApiError('Erro ao listar atendimentos', response.status, 'server')
    return response.json()
  },

  async alterarModoOperacao(atendimentoId, modoOperacao) {
    const response = await fetch(`${API_URL}/api/atendimentos/${atendimentoId}/modo-operacao`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ modo_operacao: modoOperacao }),
    })
    if (!response.ok) {
      const detail = await response.json().catch(() => null)
      throw new ApiError(detail?.detail || 'Erro ao alterar modo', response.status, 'server')
    }
    return response.json()
  },

  async enviarMensagemManual(atendimentoId, conteudo, aprovadorId = null) {
    const response = await fetch(`${API_URL}/api/atendimentos/${atendimentoId}/mensagens-manuais`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conteudo, aprovador_id: aprovadorId }),
    })
    if (!response.ok) {
      const detail = await response.json().catch(() => null)
      throw new ApiError(detail?.detail || 'Erro ao enviar mensagem', response.status, 'server')
    }
    return response.json()
  },

  // Aprovação de mensagens
  async aprovarMensagem(mensagemId, aprovadorId) {
    const response = await fetch(`${API_URL}/api/mensagens/${mensagemId}/aprovar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ aprovador_id: aprovadorId }),
    })
    if (!response.ok) {
      const detail = await response.json().catch(() => null)
      throw new ApiError(detail?.detail || 'Erro ao aprovar mensagem', response.status, 'server')
    }
    return response.json()
  },

  async reprovarMensagem(mensagemId, justificativa, reprovadorId) {
    const response = await fetch(`${API_URL}/api/mensagens/${mensagemId}/reprovar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ justificativa, reprovador_id: reprovadorId }),
    })
    if (!response.ok) {
      const detail = await response.json().catch(() => null)
      throw new ApiError(detail?.detail || 'Erro ao reprovar mensagem', response.status, 'server')
    }
    return response.json()
  },

  async listarMensagensPendentes() {
    const response = await fetch(`${API_URL}/api/mensagens/pendentes`)
    if (!response.ok) throw new ApiError('Erro ao listar mensagens pendentes', response.status, 'server')
    return response.json()
  },

  // Pares Q&A
  async listarParesQA({ contexto, ativo, aprovado, page = 1, limit = 50 } = {}) {
    const params = new URLSearchParams()
    if (contexto !== undefined && contexto !== null && contexto !== '') params.append('contexto', contexto)
    if (ativo !== undefined && ativo !== null) params.append('ativo', ativo)
    if (aprovado !== undefined && aprovado !== null) params.append('aprovado', aprovado)
    params.append('page', page)
    params.append('limit', limit)
    const response = await fetch(`${API_URL}/api/pares-qa?${params}`)
    if (!response.ok) throw new ApiError('Erro ao listar pares Q&A', response.status, 'server')
    return response.json()
  },

  async listarPendentesAprovacaoQA(contexto) {
    const params = new URLSearchParams()
    if (contexto) params.append('contexto', contexto)
    const response = await fetch(`${API_URL}/api/pares-qa/pendentes-aprovacao?${params}`)
    if (!response.ok) throw new ApiError('Erro ao listar pendentes Q&A', response.status, 'server')
    return response.json()
  },

  async criarParQA(dados) {
    const response = await fetch(`${API_URL}/api/pares-qa`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(dados),
    })
    if (!response.ok) {
      const detail = await response.json().catch(() => null)
      throw new ApiError(detail?.detail || 'Erro ao criar par Q&A', response.status, 'server')
    }
    return response.json()
  },

  async atualizarParQA(id, dados) {
    const response = await fetch(`${API_URL}/api/pares-qa/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(dados),
    })
    if (!response.ok) {
      const detail = await response.json().catch(() => null)
      throw new ApiError(detail?.detail || 'Erro ao atualizar par Q&A', response.status, 'server')
    }
    return response.json()
  },

  async aprovarParQA(id) {
    const response = await fetch(`${API_URL}/api/pares-qa/${id}/aprovar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })
    if (!response.ok) {
      const detail = await response.json().catch(() => null)
      throw new ApiError(detail?.detail || 'Erro ao aprovar par Q&A', response.status, 'server')
    }
    return response.json()
  },

  async desativarParQA(id) {
    const response = await fetch(`${API_URL}/api/pares-qa/${id}`, { method: 'DELETE' })
    if (!response.ok) {
      const detail = await response.json().catch(() => null)
      throw new ApiError(detail?.detail || 'Erro ao desativar par Q&A', response.status, 'server')
    }
    return response.json()
  },

  async getConfigRag() {
    try {
      const response = await fetch(`${API_URL}/api/config/rag`)
      if (!response.ok) throw new ApiError('Erro ao buscar config RAG', response.status, 'server')
      return response.json()
    } catch (error) {
      if (error instanceof ApiError) throw error
      throw new ApiError('Backend não está respondendo', 0, 'network')
    }
  },

  async patchConfigRag(dados) {
    try {
      const response = await fetch(`${API_URL}/api/config/rag`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dados),
      })
      if (!response.ok) {
        const detail = await response.json().catch(() => null)
        throw new ApiError(detail?.detail || 'Erro ao atualizar config RAG', response.status, 'server')
      }
      return response.json()
    } catch (error) {
      if (error instanceof ApiError) throw error
      throw new ApiError('Backend não está respondendo', 0, 'network')
    }
  },

  async listarParametros() {
    const response = await fetch(`${API_URL}/api/parametros`)
    if (!response.ok) throw new ApiError('Erro ao listar parâmetros', response.status, 'server')
    return response.json()
  },

  async atualizarParametro(nome, valor) {
    const response = await fetch(`${API_URL}/api/parametros/${encodeURIComponent(nome)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ valor }),
    })
    if (!response.ok) {
      const detail = await response.json().catch(() => null)
      throw new ApiError(detail?.detail || 'Erro ao atualizar parâmetro', response.status, 'server')
    }
    return response.json()
  },
}

export { ApiError }
