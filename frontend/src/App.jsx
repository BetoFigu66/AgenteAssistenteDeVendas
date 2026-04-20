import { useState, useEffect } from 'react'
import Header from './components/Header'
import Footer from './components/Footer'
import PhonePanel from './components/PhonePanel'
import ChatArea from './components/ChatArea'
import { api } from './services/api'

function App() {
  const [telefoneAtual, setTelefoneAtual] = useState(null)
  const [telefones, setTelefones] = useState([])
  const [mensagens, setMensagens] = useState([])
  const [loading, setLoading] = useState(false)
  const [erro, setErro] = useState(null)

  useEffect(() => {
    carregarTelefones()
  }, [])

  useEffect(() => {
    if (telefoneAtual) {
      carregarHistorico(telefoneAtual)
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

  const selecionarTelefone = (telefone) => {
    setTelefoneAtual(telefone)
    if (!telefones.includes(telefone)) {
      setTelefones(prev => [...prev, telefone])
    }
  }

  const enviarMensagem = async (mensagem) => {
    if (!telefoneAtual || !mensagem.trim()) return

    try {
      setLoading(true)
      setErro(null)
      await api.enviarMensagem(telefoneAtual, mensagem)
      await carregarHistorico(telefoneAtual)
    } catch (error) {
      console.error('Erro ao enviar mensagem:', error)
      setErro(error.message || 'Erro ao enviar mensagem. Tente novamente.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      
      <main className="flex-1 container mx-auto px-4 py-8 max-w-5xl">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <PhonePanel
            telefones={telefones}
            telefoneAtual={telefoneAtual}
            onSelectTelefone={selecionarTelefone}
          />
          
          <ChatArea
            telefone={telefoneAtual}
            mensagens={mensagens}
            loading={loading}
            erro={erro}
            onEnviarMensagem={enviarMensagem}
          />
        </div>
      </main>
      
      <Footer />
    </div>
  )
}

export default App
