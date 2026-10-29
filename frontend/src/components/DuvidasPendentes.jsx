import { useEffect, useState } from 'react'
import { HelpCircle } from 'lucide-react'
import { api } from '../services/api'
import { formatDatetimeBRT } from '../utils/datetime'

/**
 * Dúvidas do cliente que o agente não respondeu: a mensagem trazia uma pergunta, mas caiu
 * numa ação exclusiva (pedido de atendente, reclamação, projeto complexo...). O operador
 * responde pela resposta manual e marca como respondida.
 *
 * Busca em `GET /api/atendimentos/{id}/duvidas-pendentes`, de novo sempre que
 * `recarregarChave` mudar (ex.: chegou mensagem nova). Sem dúvida pendente, não aparece.
 */
function DuvidasPendentes({ atendimentoId, recarregarChave, onIrParaMensagem, mensagemVisivel }) {
  const [duvidas, setDuvidas] = useState([])
  const [resolvendoId, setResolvendoId] = useState(null)

  useEffect(() => {
    let cancelado = false
    api
      .obterDuvidasPendentes(atendimentoId)
      .then((data) => {
        if (!cancelado) setDuvidas(data.duvidas_pendentes || [])
      })
      .catch(() => {
        if (!cancelado) setDuvidas([])
      })
    return () => {
      cancelado = true
    }
  }, [atendimentoId, recarregarChave])

  const resolver = async (duvida) => {
    setResolvendoId(duvida.id)
    try {
      await api.resolverDuvidaPendente(duvida.id)
      setDuvidas((atual) => atual.filter((d) => d.id !== duvida.id))
    } catch (error) {
      alert(error.message)
    } finally {
      setResolvendoId(null)
    }
  }

  if (duvidas.length === 0) return null

  return (
    <div className="mx-4 mt-3 p-3 bg-blue-50 border border-blue-200 rounded-md">
      <div className="flex items-center gap-1.5 text-sm font-medium text-inforrel-primary">
        <HelpCircle size={14} />
        {duvidas.length === 1 ? 'Dúvida do cliente sem resposta do agente' : `${duvidas.length} dúvidas do cliente sem resposta do agente`}
      </div>
      <ul className="mt-2 space-y-2">
        {duvidas.map((duvida) => (
          <li key={duvida.id} className="text-sm bg-white border border-blue-100 rounded p-2">
            <p className="text-gray-800 whitespace-pre-wrap">{duvida.texto}</p>
            <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-gray-500">
              <span>{formatDatetimeBRT(duvida.criado_em)}</span>
              {duvida.mensagem_id && onIrParaMensagem && mensagemVisivel?.(duvida.mensagem_id) && (
                <button
                  type="button"
                  onClick={() => onIrParaMensagem(duvida.mensagem_id)}
                  className="text-inforrel-secondary hover:underline"
                >
                  Ir para a mensagem
                </button>
              )}
              <button
                type="button"
                onClick={() => resolver(duvida)}
                disabled={resolvendoId === duvida.id}
                className="ml-auto px-2 py-0.5 rounded bg-inforrel-primary text-white hover:opacity-90 disabled:opacity-50"
              >
                Marcar como respondida
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default DuvidasPendentes
