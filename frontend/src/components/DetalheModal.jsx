import { X } from 'lucide-react'

function DetalheModal({ titulo, onClose, children }) {
  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[85vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-5 py-3 border-b bg-gradient-to-r from-inforrel-primary to-inforrel-secondary text-white flex items-center justify-between">
          <h2 className="font-semibold text-lg">{titulo}</h2>
          <button
            onClick={onClose}
            className="hover:bg-white/20 rounded p-1 transition"
            aria-label="Fechar"
          >
            <X size={20} />
          </button>
        </div>
        <div className="p-5 overflow-y-auto flex-1">{children}</div>
      </div>
    </div>
  )
}

export default DetalheModal
