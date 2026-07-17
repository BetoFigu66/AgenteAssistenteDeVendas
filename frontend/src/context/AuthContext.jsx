import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api } from '../services/api'

const AuthContext = createContext(null)

/**
 * REQ-010 (Fase 4): único Context do projeto — só existe para evitar
 * prop-drilling do usuário logado por Header/AcompanhamentoPage/ReportDetalhe,
 * que hoje pediam "quem fez a ação" auto-declarado.
 */
export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null)
  const [carregando, setCarregando] = useState(true)

  const carregarUsuario = useCallback(async () => {
    try {
      const dados = await api.obterUsuarioAtual()
      setUsuario(dados)
    } catch {
      setUsuario(null)
    } finally {
      setCarregando(false)
    }
  }, [])

  useEffect(() => {
    carregarUsuario()
  }, [carregarUsuario])

  const login = useCallback(async (loginValor, senha) => {
    const dados = await api.login(loginValor, senha)
    setUsuario(dados)
    return dados
  }, [])

  const logout = useCallback(async () => {
    await api.logout()
    setUsuario(null)
  }, [])

  return (
    <AuthContext.Provider value={{ usuario, carregando, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth precisa ser usado dentro de <AuthProvider>')
  return ctx
}
