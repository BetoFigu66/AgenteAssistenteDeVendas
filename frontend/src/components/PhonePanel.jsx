import { useState } from 'react'
import { Phone, Plus } from 'lucide-react'
import { formatDatetimeBRT } from '../utils/datetime'

function PhonePanel({ telefones, telefoneAtual, onSelectTelefone }) {
  const [novoTelefone, setNovoTelefone] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (novoTelefone.trim()) {
      onSelectTelefone(novoTelefone.trim())
      setNovoTelefone('')
    }
  }

  return (
    <div className="card">
      <h2 className="font-semibold text-inforrel-primary mb-4 font-heading flex items-center gap-2">
        <Phone size={20} />
        Telefones
      </h2>

      {/* Novo telefone */}
      <form onSubmit={handleSubmit} className="mb-4">
        <input
          type="text"
          value={novoTelefone}
          onChange={(e) => setNovoTelefone(e.target.value)}
          placeholder="+5511999999999"
          className="input mb-2"
        />
        <button type="submit" className="btn-primary w-full flex items-center justify-center gap-2">
          <Plus size={18} />
          Iniciar Conversa
        </button>
      </form>

      {/* Lista de telefones — ordenada pelo backend por última mensagem
          (mais recente primeiro), a conversa ativa sempre fica no topo. */}
      <div className="border-t pt-4">
        <p className="text-xs text-gray-500 mb-2">Conversas anteriores:</p>
        {telefones.length === 0 ? (
          <p className="text-gray-400 text-sm italic">Nenhuma conversa</p>
        ) : (
          <ul className="space-y-1">
            {telefones.map(({ telefone: tel, ultima_mensagem_em }) => (
              <li key={tel}>
                <button
                  onClick={() => onSelectTelefone(tel)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                    tel === telefoneAtual
                      ? 'bg-inforrel-primary text-white'
                      : 'hover:bg-gray-100 text-gray-700'
                  }`}
                >
                  <div>{tel}</div>
                  {ultima_mensagem_em && (
                    <div className={`text-xs ${tel === telefoneAtual ? 'text-white/70' : 'text-gray-400'}`}>
                      {formatDatetimeBRT(ultima_mensagem_em)}
                    </div>
                  )}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

export default PhonePanel
