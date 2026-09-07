import { useState, useEffect } from 'react'
import { Flag, Monitor, BookOpen, Settings } from 'lucide-react'
import Header from './components/Header'
import Footer from './components/Footer'
import PhonePanel from './components/PhonePanel'
import ChatArea from './components/ChatArea'
import ReportsPage from './components/ReportsPage'
import AcompanhamentoPage from './components/AcompanhamentoPage'
import QABasePage from './components/QABasePage'
import ParametrosPage from './components/ParametrosPage'
import LoginPage from './components/LoginPage'
import { AuthProvider, useAuth } from './context/AuthContext'
import { api } from './services/api'

function App() {
  const { usuario, carregando } = useAuth()

  if (carregando) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-500">
        Carregando...
      </div>
    )
  }

  if (!usuario) {
    return <LoginPage />
  }

  return <AppLogado />
}

function AppLogado() {
  const [pagina, setPagina] = useState('chat') // 'chat' | 'reports' | 'acompanhamento' | 'qa-base' | 'parametros'
  const [atendimentoIdAlvo, setAtendimentoIdAlvo] = useState(null)
  const [telefoneAtual, setTelefoneAtual] = useState(null)
  const [telefones, setTelefones] = useState([])
  const [mensagens, setMensagens] = useState([])
  const [dadosConversa, setDadosConversa] = useState(null)
  const [loading, setLoading] = useState(false)
  const [erro, setErro] = useState(null)

  useEffect(() => {
    carregarTelefones()
  }, [])

  useEffect(() => {
    if (telefoneAtual) {
      carregarDadosConversa(telefoneAtual)
      carregarHistorico(telefoneAtual)
    } else {
      setDadosConversa(null)
    }
  }, [telefoneAtual])

  const carregarTelefones = async () => {
    try {
      const data = await api.listarTelefones()
      setTelefones(data.telefones || [])
    } catch (error) {
      console.error('Erro ao carregar telefones:', error)
    }
  }

  const carregarHistorico = async (telefone) => {
    setLoading(true)
    setErro(null)
    
    try {
      const data = await api.obterHistorico(telefone)
      setMensagens(data.mensagens || [])
    } catch (error) {
      setMensagens([])
      setErro(error.message || 'Erro ao carregar histórico. Tente novamente.')
    } finally {
      setLoading(false)
    }
  }

  const carregarDadosConversa = async (telefone) => {
    try {
      const data = await api.obterDadosConversa(telefone)
      setDadosConversa(data)
    } catch (error) {
      console.error('Erro ao carregar dados da conversa:', error)
      setDadosConversa(null)
    }
  }

  const abrirAtendimento = (atendimentoId) => {
    setAtendimentoIdAlvo(atendimentoId)
    setPagina('acompanhamento')
  }

  const selecionarTelefone = (telefone) => {
    setTelefoneAtual(telefone)
    if (!telefones.some(t => t.telefone === telefone)) {
      setTelefones(prev => [{ telefone, ultima_mensagem_em: null }, ...prev])
    }
  }

  const enviarMensagem = async (mensagem) => {
    if (!telefoneAtual || !mensagem.trim()) return

    try {
      setLoading(true)
      setErro(null)
      await api.enviarMensagem(telefoneAtual, mensagem)
      await carregarHistorico(telefoneAtual)
      await carregarDadosConversa(telefoneAtual)
      // Reordena pelo backend (última mensagem desc) — a conversa que acabou
      // de receber mensagem sobe pro topo, sem precisar rolar a lista pra achar.
      await carregarTelefones()
    } catch (error) {
      console.error('Erro ao enviar mensagem:', error)
      setErro(error.message || 'Erro ao enviar mensagem. Tente novamente.')
    } finally {
      setLoading(false)
    }
  }

  const apagarConversa = async () => {
    if (!telefoneAtual) return
    const confirmado = window.confirm(
      `Apagar toda a conversa de ${telefoneAtual}? Remove contato, atendimentos e mensagens — não dá pra desfazer.`,
    )
    if (!confirmado) return

    try {
      setLoading(true)
      setErro(null)
      await api.apagarConversa(telefoneAtual)
      setTelefones(prev => prev.filter(t => t.telefone !== telefoneAtual))
      setMensagens([])
      setDadosConversa(null)
      setTelefoneAtual(null)
    } catch (error) {
      console.error('Erro ao apagar conversa:', error)
      setErro(error.message || 'Erro ao apagar conversa. Tente novamente.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      {/* Navegação */}
      <nav className="bg-white border-b border-gray-200">
        <div className="container mx-auto px-4 max-w-7xl flex gap-1">
          <button
            onClick={() => setPagina('chat')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
              pagina === 'chat'
                ? 'border-inforrel-primary text-inforrel-primary'
                : 'border-transparent text-gray-600 hover:text-inforrel-primary'
            }`}
          >
            💬 Chat
          </button>
          <button
            onClick={() => setPagina('acompanhamento')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition flex items-center gap-1.5 ${
              pagina === 'acompanhamento'
                ? 'border-inforrel-primary text-inforrel-primary'
                : 'border-transparent text-gray-600 hover:text-inforrel-primary'
            }`}
          >
            <Monitor size={14} /> Acompanhamento
          </button>
          <button
            onClick={() => setPagina('reports')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition flex items-center gap-1.5 ${
              pagina === 'reports'
                ? 'border-inforrel-primary text-inforrel-primary'
                : 'border-transparent text-gray-600 hover:text-inforrel-primary'
            }`}
          >
            <Flag size={14} /> Triagem de Reports
          </button>
          <button
            onClick={() => setPagina('qa-base')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition flex items-center gap-1.5 ${
              pagina === 'qa-base'
                ? 'border-inforrel-primary text-inforrel-primary'
                : 'border-transparent text-gray-600 hover:text-inforrel-primary'
            }`}
          >
            <BookOpen size={14} /> Base Q&A
          </button>
          <button
            onClick={() => setPagina('parametros')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition flex items-center gap-1.5 ${
              pagina === 'parametros'
                ? 'border-inforrel-primary text-inforrel-primary'
                : 'border-transparent text-gray-600 hover:text-inforrel-primary'
            }`}
          >
            <Settings size={14} /> Parâmetros
          </button>
        </div>
      </nav>

      <main className="flex-1">
        {pagina === 'chat' && (
          <div className="container mx-auto px-4 py-8 max-w-5xl">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <PhonePanel
                telefones={telefones}
                telefoneAtual={telefoneAtual}
                onSelectTelefone={selecionarTelefone}
              />
              <ChatArea
                telefone={telefoneAtual}
                mensagens={mensagens}
                dadosConversa={dadosConversa}
                loading={loading}
                erro={erro}
                onEnviarMensagem={enviarMensagem}
                onApagarConversa={apagarConversa}
              />
            </div>
          </div>
        )}
        {pagina === 'acompanhamento' && (
          <AcompanhamentoPage
            atendimentoIdInicial={atendimentoIdAlvo}
            onAtendimentoIdInicialConsumido={() => setAtendimentoIdAlvo(null)}
          />
        )}
        {pagina === 'reports' && (
          <ReportsPage onVoltar={() => setPagina('chat')} onAbrirAtendimento={abrirAtendimento} />
        )}
        {pagina === 'qa-base' && <QABasePage />}
        {pagina === 'parametros' && <ParametrosPage />}
      </main>

      <Footer />
    </div>
  )
}

function AppComAuth() {
  return (
    <AuthProvider>
      <App />
    </AuthProvider>
  )
}

export default AppComAuth
