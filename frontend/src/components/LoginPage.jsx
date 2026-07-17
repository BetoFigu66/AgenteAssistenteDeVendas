import { useState } from 'react'
import { LogIn } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

function LoginPage() {
  const { login } = useAuth()
  const [loginValor, setLoginValor] = useState('')
  const [senha, setSenha] = useState('')
  const [entrando, setEntrando] = useState(false)
  const [erro, setErro] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!loginValor.trim() || !senha || entrando) return
    setEntrando(true)
    setErro(null)
    try {
      await login(loginValor.trim(), senha)
    } catch (err) {
      setErro(err.message || 'Login ou senha inválidos')
    } finally {
      setEntrando(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-inforrel-light px-4">
      <form
        onSubmit={handleSubmit}
        className="bg-white rounded-lg shadow-md p-8 w-full max-w-sm space-y-4"
      >
        <div className="text-center mb-2">
          <h1 className="text-xl font-heading font-bold text-inforrel-primary">Inforrel</h1>
          <p className="text-sm text-gray-500">Painel do Assistente de Vendas</p>
        </div>

        <div>
          <label className="block text-xs text-gray-500 uppercase tracking-wide mb-1">Login</label>
          <input
            type="text"
            value={loginValor}
            onChange={(e) => setLoginValor(e.target.value)}
            autoFocus
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-inforrel-primary"
          />
        </div>

        <div>
          <label className="block text-xs text-gray-500 uppercase tracking-wide mb-1">Senha</label>
          <input
            type="password"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-inforrel-primary"
          />
        </div>

        {erro && <p className="text-sm text-red-600">{erro}</p>}

        <button
          type="submit"
          disabled={!loginValor.trim() || !senha || entrando}
          className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-50"
        >
          <LogIn size={16} />
          {entrando ? 'Entrando...' : 'Entrar'}
        </button>
      </form>
    </div>
  )
}

export default LoginPage
