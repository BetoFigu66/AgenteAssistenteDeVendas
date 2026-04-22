import { useState } from 'react'
import { User, Bot, Brain } from 'lucide-react'
import DetalheModal from './DetalheModal'
import ProcessamentoDetalhes from './ProcessamentoDetalhes'

function Message({ mensagem }) {
  const isUser = mensagem.origem === 'user'
  const [mostrarDebug, setMostrarDebug] = useState(false)
  const temProcessamento = !!mensagem.processamento_id

  const formatTime = (timestamp) => {
    if (!timestamp) return ''
    const date = new Date(timestamp)
    return date.toLocaleTimeString('pt-BR', {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-2 ${
          isUser
            ? 'bg-blue-50 border-l-4 border-inforrel-secondary'
            : 'bg-white border-l-4 border-inforrel-primary shadow-sm'
        }`}
      >
        <div className="flex items-center gap-2 mb-1">
          {isUser ? (
            <User size={14} className="text-inforrel-secondary" />
          ) : (
            <Bot size={14} className="text-inforrel-primary" />
          )}
          <span className="text-xs font-medium text-gray-500">
            {isUser ? 'Você' : 'Assistente'}
          </span>
          <span className="text-xs text-gray-400">
            {formatTime(mensagem.timestamp)}
          </span>
          {temProcessamento && (
            <button
              onClick={() => setMostrarDebug(true)}
              className="ml-auto text-gray-400 hover:text-inforrel-primary transition"
              title="Ver raciocínio do cérebro"
              aria-label="Ver raciocínio do cérebro"
            >
              <Brain size={14} />
            </button>
          )}
        </div>
        <p className="text-gray-800 text-sm">{mensagem.conteudo}</p>
      </div>

      {mostrarDebug && temProcessamento && (
        <DetalheModal
          titulo={`Raciocínio do cérebro — msg #${mensagem.id}`}
          onClose={() => setMostrarDebug(false)}
        >
          <ProcessamentoDetalhes processamentoId={mensagem.processamento_id} />
        </DetalheModal>
      )}
    </div>
  )
}

export default Message
