import { useEffect, useState } from 'react'
import { Phone, Mail } from 'lucide-react'
import { api } from '../services/api'

const ROTULO_MODO = {
  simulacao: 'Simulação',
  conversa_controlada: 'Conversa Controlada',
  execucao_normal: 'Execução Normal',
}

const CLASSES_MODO = {
  simulacao: 'bg-purple-100 text-purple-700 border-purple-300',
  conversa_controlada: 'bg-amber-100 text-amber-700 border-amber-300',
  execucao_normal: 'bg-green-100 text-green-700 border-green-300',
}

function ModoExecucaoBadge() {
  const [modo, setModo] = useState(null)
  const [alterando, setAlterando] = useState(false)
  const [erro, setErro] = useState(null)

  const carregar = async () => {
    try {
      const dados = await api.getConfigExecucao()
      setModo(dados.modo_execucao)
      setErro(null)
    } catch (error) {
      setErro(error.message)
    }
  }

  useEffect(() => {
    carregar()
  }, [])

  const handleChange = async (e) => {
    const novoModo = e.target.value
    if (novoModo === modo) return
    setAlterando(true)
    try {
      await api.patchConfigExecucao(novoModo, 'vendedor')
      setModo(novoModo)
      setErro(null)
    } catch (error) {
      setErro(error.message)
    } finally {
      setAlterando(false)
    }
  }

  if (!modo) {
    return erro ? <span className="text-xs text-red-500">Modo de execução indisponível</span> : null
  }

  return (
    <div className="flex items-center gap-2" title="Modo de execução vigente (REQ-011)">
      <span
        className={`text-xs px-2 py-1 rounded-full border font-medium ${CLASSES_MODO[modo] || 'bg-gray-100 text-gray-700 border-gray-300'}`}
      >
        {ROTULO_MODO[modo] || modo}
      </span>
      <select
        value={modo}
        onChange={handleChange}
        disabled={alterando}
        className="text-xs border border-gray-300 rounded px-1.5 py-1 focus:outline-none focus:ring-2 focus:ring-inforrel-primary"
      >
        {Object.keys(ROTULO_MODO).map((valor) => (
          <option key={valor} value={valor}>
            {ROTULO_MODO[valor]}
          </option>
        ))}
      </select>
    </div>
  )
}

function Header() {
  return (
    <>
      {/* Top Bar */}
      <div className="bg-inforrel-dark text-white text-sm py-2">
        <div className="container mx-auto px-4 max-w-5xl flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Phone size={14} />
            <span>(19) 3772-5050</span>
          </div>
          <div className="flex items-center gap-2">
            <Mail size={14} />
            <span>contato@inforrel.com.br</span>
          </div>
        </div>
      </div>

      {/* Header */}
      <header className="bg-white shadow-md">
        <div className="container mx-auto px-4 py-4 max-w-5xl flex items-center justify-between">
          <div className="flex items-center gap-4">
            <img
              src="/images/inforrel01.jpg"
              alt="Inforrel"
              className="h-14 w-auto"
              onError={(e) => {
                e.target.style.display = 'none'
              }}
            />
            <div className="hidden md:block">
              <h1 className="text-xl font-bold text-inforrel-primary font-heading">
                Assistente de Vendas
              </h1>
              <p className="text-sm text-gray-500">Controle de Ponto e Acesso</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="hidden sm:inline text-sm text-gray-600">
              Simulador de Atendimento
            </span>
            <span className="bg-inforrel-accent text-white text-xs px-3 py-1 rounded-full font-medium">
              POC
            </span>
            <ModoExecucaoBadge />
          </div>
        </div>
      </header>
    </>
  )
}

export default Header
