import { useState, useRef, useEffect } from 'react'
import { Send, MessageCircle, AlertTriangle } from 'lucide-react'
import Message from './Message'
import ConversaInfo from './ConversaInfo'
import { api } from '../services/api'

function ChatArea({ telefone, mensagens, dadosConversa, loading, erro, onEnviarMensagem }) {
  const [inputMensagem, setInputMensagem] = useState('')
  const messagesEndRef = useRef(null)
  const [scoreMinimo, setScoreMinimo] = useState(null)
  const [salvandoScore, setSalvandoScore] = useState(false)

  useEffect(() => {
    api.getConfigRag().then(cfg => setScoreMinimo(cfg.rag_score_minimo)).catch(() => {})
  }, [])

  const handleScoreChange = (e) => {
    const val = parseFloat(e.target.value)
    if (!isNaN(val)) setScoreMinimo(val)
  }

  const handleScoreBlur = async (e) => {
    const val = parseFloat(e.target.value)
    if (isNaN(val) || val < 0 || val > 1) return
    setSalvandoScore(true)
    try {
      await api.patchConfigRag({ rag_score_minimo: val })
    } catch (_) {}
    finally { setSalvandoScore(false) }
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [mensagens])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (inputMensagem.trim() && telefone) {
      onEnviarMensagem(inputMensagem.trim())
      setInputMensagem('')
    }
  }

  return (
    <div className="md:col-span-2 bg-white rounded-lg shadow-md flex flex-col" style={{ height: '600px' }}>
      {/* Header do chat */}
      <div className="px-4 py-3 border-b bg-gradient-to-r from-inforrel-primary to-inforrel-secondary rounded-t-lg">
        <div className="flex items-center justify-between text-white">
          <div className="flex items-center gap-2">
            <MessageCircle size={20} />
            <p className="font-medium">
              {telefone || 'Selecione um telefone'}
            </p>
          </div>
          {scoreMinimo !== null && (
            <div className="flex items-center gap-1.5 text-xs">
              <span className="text-white/70">Score RAG</span>
              <input
                type="number"
                min="0"
                max="1"
                step="0.05"
                value={scoreMinimo}
                onChange={handleScoreChange}
                onBlur={handleScoreBlur}
                onKeyDown={e => e.key === 'Enter' && e.target.blur()}
                title="Score mínimo de similaridade para a RAG retornar resultados (0.0 a 1.0)"
                className="w-16 text-center rounded px-1 py-0.5 bg-white/20 text-white border border-white/30 focus:outline-none focus:bg-white/30"
              />
              <span className={`text-xs transition-opacity ${salvandoScore ? 'opacity-100' : 'opacity-0'} text-white/60`}>✓</span>
            </div>
          )}
        </div>
      </div>

      {/* Informações da conversa (empresa, contato, negociação) */}
      {telefone && dadosConversa && <ConversaInfo dados={dadosConversa} />}

      {/* Mensagens */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50">
        {!telefone ? (
          <div className="text-center text-gray-400 text-sm py-8">
            Selecione ou digite um número de telefone para iniciar
          </div>
        ) : erro ? (
          <div className="text-center py-8">
            <div className="inline-flex items-center gap-2 bg-red-50 text-red-600 px-4 py-3 rounded-lg border border-red-200">
              <AlertTriangle size={20} />
              <span className="text-sm">{erro}</span>
            </div>
          </div>
        ) : loading ? (
          <div className="text-center text-gray-400 text-sm py-8">
            Carregando...
          </div>
        ) : mensagens.length === 0 ? (
          <div className="text-center text-gray-400 text-sm py-8">
            Nenhuma mensagem ainda. Envie a primeira!
          </div>
        ) : (
          <>
            {mensagens.map((msg, index) => (
              <Message key={msg.id || index} mensagem={msg} />
            ))}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input de mensagem */}
      <div className="p-4 border-t">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={inputMensagem}
            onChange={(e) => setInputMensagem(e.target.value)}
            placeholder="Digite sua mensagem..."
            disabled={!telefone || loading}
            className="input flex-1 rounded-full"
          />
          <button
            type="submit"
            disabled={!telefone || loading || !inputMensagem.trim()}
            className="btn-primary rounded-full px-6"
          >
            <Send size={20} />
          </button>
        </form>
      </div>
    </div>
  )
}

export default ChatArea
