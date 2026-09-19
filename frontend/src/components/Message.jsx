import { useState } from 'react'
import { User, Bot, Brain, Reply, AlertTriangle } from 'lucide-react'
import DetalheModal from './DetalheModal'
import ProcessamentoDetalhes from './ProcessamentoDetalhes'
import { formatDatetimeBRT } from '../utils/datetime'

const LIMITE_CITACAO = 90

function trecho(texto) {
  if (!texto) return 'mensagem citada'
  return texto.length > LIMITE_CITACAO ? `${texto.slice(0, LIMITE_CITACAO)}…` : texto
}

/**
 * Um balão da conversa.
 *
 * `mensagemCitada` é a mensagem que esta responde, já resolvida pelo ChatArea a partir
 * de `resposta_a_mensagem_id` — o backend manda só o id, porque a conversa inteira já
 * está carregada aqui e um SELECT por balão não se justificaria. Pode vir `undefined`
 * se a citada ficou fora da página carregada, e o balão então mostra a citação genérica.
 */
function Message({ mensagem, mensagemCitada, onResponder }) {
  const isUser = mensagem.origem === 'user'
  const [mostrarDebug, setMostrarDebug] = useState(false)
  const temProcessamento = !!mensagem.processamento_id
  const temCitacao = !!mensagem.resposta_a_mensagem_id
  // Só faz sentido citar uma mensagem do assistente: quem digita aqui simula o cliente,
  // e o que interessa registrar é a qual pergunta do sistema ele está respondendo.
  const podeResponder = !isUser && !!onResponder

  const formatarData = (timestamp) => formatDatetimeBRT(timestamp)

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`group max-w-[80%] rounded-lg px-4 py-2 ${
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
            {formatarData(mensagem.timestamp)}
          </span>
          <div className="ml-auto flex items-center gap-1">
            {podeResponder && (
              <button
                onClick={() => onResponder(mensagem)}
                className="text-gray-400 hover:text-inforrel-primary transition opacity-0 group-hover:opacity-100 focus:opacity-100"
                title="Responder citando esta mensagem"
                aria-label="Responder citando esta mensagem"
              >
                <Reply size={14} />
              </button>
            )}
            {temProcessamento && (
              <button
                onClick={() => setMostrarDebug(true)}
                className="text-gray-400 hover:text-inforrel-primary transition"
                title="Ver raciocínio do cérebro"
                aria-label="Ver raciocínio do cérebro"
              >
                <Brain size={14} />
              </button>
            )}
          </div>
        </div>

        {temCitacao && (
          <div className="mb-2 border-l-2 border-inforrel-accent bg-gray-50 px-2 py-1 rounded-r">
            <p className="text-[11px] font-medium text-gray-500">
              {mensagemCitada
                ? (mensagemCitada.origem === 'user' ? 'Você' : 'Assistente')
                : 'Em resposta a'}
            </p>
            <p className="text-xs text-gray-600 italic">{trecho(mensagemCitada?.conteudo)}</p>
          </div>
        )}

        <p className="text-gray-800 text-sm">{mensagem.conteudo}</p>

        {mensagem.erro_envio && (
          <div className="mt-2 flex items-start gap-1 text-xs text-red-600">
            <AlertTriangle size={12} className="mt-0.5 shrink-0" />
            <span>Não entregue: {mensagem.erro_envio}</span>
          </div>
        )}
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
