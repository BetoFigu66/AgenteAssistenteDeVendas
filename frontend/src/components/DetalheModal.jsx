import { useRef, useState } from 'react'
import { GripHorizontal, X } from 'lucide-react'

// Parte do cabecalho que precisa continuar visivel ao arrastar a janela flutuante,
// para que ela nunca fique perdida fora da tela.
const MARGEM_VISIVEL = 80

/**
 * Janela de detalhe.
 *
 * Padrao: modal com fundo escuro, clicar fora fecha.
 * `flutuante`: sem fundo, arrastavel pelo cabecalho e sem bloquear a tela por tras,
 * que continua visivel e clicavel (ex.: ler o raciocinio do cerebro enquanto preenche
 * o "Reportar problema"). Fica em z-40, abaixo dos modais comuns (z-50), para que um
 * modal aberto a partir da tela principal apareca por cima dela.
 */
function DetalheModal({ titulo, onClose, children, flutuante = false }) {
  const [deslocamento, setDeslocamento] = useState({ x: 0, y: 0 })
  const arrasto = useRef(null)
  const painelRef = useRef(null)

  const iniciarArrasto = (e) => {
    if (!flutuante || e.button !== 0 || e.target.closest('button')) return
    const rect = painelRef.current.getBoundingClientRect()
    arrasto.current = { inicioX: e.clientX, inicioY: e.clientY, base: deslocamento, rect }
    e.currentTarget.setPointerCapture(e.pointerId)
    e.preventDefault()
  }

  const arrastar = (e) => {
    const a = arrasto.current
    if (!a) return
    let dx = e.clientX - a.inicioX
    let dy = e.clientY - a.inicioY
    // limita para o cabecalho continuar alcancavel
    dx = Math.min(Math.max(dx, MARGEM_VISIVEL - a.rect.right), window.innerWidth - MARGEM_VISIVEL - a.rect.left)
    dy = Math.min(Math.max(dy, -a.rect.top), window.innerHeight - 48 - a.rect.top)
    setDeslocamento({ x: a.base.x + dx, y: a.base.y + dy })
  }

  const encerrarArrasto = () => {
    arrasto.current = null
  }

  const painel = (
    <div
      ref={painelRef}
      className={`bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[85vh] overflow-hidden flex flex-col ${
        flutuante ? 'pointer-events-auto ring-1 ring-black/10 shadow-2xl' : ''
      }`}
      style={flutuante ? { transform: `translate(${deslocamento.x}px, ${deslocamento.y}px)` } : undefined}
      onClick={(e) => e.stopPropagation()}
    >
      <div
        className={`px-5 py-3 border-b bg-gradient-to-r from-inforrel-primary to-inforrel-secondary text-white flex items-center justify-between ${
          flutuante ? 'cursor-move select-none touch-none' : ''
        }`}
        onPointerDown={iniciarArrasto}
        onPointerMove={arrastar}
        onPointerUp={encerrarArrasto}
        onPointerCancel={encerrarArrasto}
        title={flutuante ? 'Arraste para mover' : undefined}
      >
        <h2 className="font-semibold text-lg flex items-center gap-2">
          {flutuante && <GripHorizontal size={18} className="opacity-70 shrink-0" />}
          {titulo}
        </h2>
        <button
          onClick={onClose}
          className="hover:bg-white/20 rounded p-1 transition"
          aria-label="Fechar"
        >
          <X size={20} />
        </button>
      </div>
      {/* text-gray-800 explicito: o modal nao usa portal e herda `color` do ponto
          onde foi montado (ex.: botao dentro de cabecalho escuro com text-white
          deixaria inputs e textos sem cor propria invisiveis no fundo branco) */}
      <div className="p-5 overflow-y-auto flex-1 text-gray-800">{children}</div>
    </div>
  )

  if (flutuante) {
    return (
      <div className="fixed inset-0 flex items-center justify-center z-40 p-4 pointer-events-none">
        {painel}
      </div>
    )
  }

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      {painel}
    </div>
  )
}

export default DetalheModal
