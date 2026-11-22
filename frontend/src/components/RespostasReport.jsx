import { Bot, UserRound } from 'lucide-react'
import { ORIGENS_RESPOSTA } from '../constants/reports'
import { formatDatetimeBRT } from '../utils/datetime'

/** Respostas de um report (Dúvida), com a indicação de quem respondeu: Claude ou equipe. */
function RespostasReport({ respostas, compacto = false }) {
  if (!respostas?.length) return null
  return (
    <ul className="space-y-2">
      {respostas.map((r) => {
        const origem = ORIGENS_RESPOSTA[r.origem] || { label: r.origem, cor: 'bg-gray-100 text-gray-700' }
        const Icone = r.origem === 'claude' ? Bot : UserRound
        return (
          <li
            key={r.id}
            className={`bg-white border border-gray-200 rounded ${compacto ? 'p-2' : 'p-2.5'} text-sm`}
          >
            <div className="flex items-center justify-between flex-wrap gap-1 mb-1">
              <span className={`text-xs px-2 py-0.5 rounded-full flex items-center gap-1 ${origem.cor}`}>
                <Icone size={12} /> Respondido por {origem.label}
              </span>
              <span className="text-xs text-gray-500">
                {r.autor && r.autor !== origem.label && `${r.autor} · `}
                {formatDatetimeBRT(r.created_at)}
              </span>
            </div>
            <p className="text-gray-800 whitespace-pre-wrap">{r.texto}</p>
          </li>
        )
      })}
    </ul>
  )
}

export default RespostasReport
