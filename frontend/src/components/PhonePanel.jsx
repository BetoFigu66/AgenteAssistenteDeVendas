import { useMemo, useState } from 'react'
import { Phone, Plus, Search, X } from 'lucide-react'
import { formatDatetimeBRT } from '../utils/datetime'
import { criarFiltroTelefone } from '../utils/filtroTelefone'
import DetalheModal from './DetalheModal'

function PhonePanel({ telefones, telefoneAtual, onSelectTelefone }) {
  const [novoTelefone, setNovoTelefone] = useState('')
  const [modalNovo, setModalNovo] = useState(false)
  const [filtro, setFiltro] = useState('')
  const filtrados = useMemo(() => {
    const aceita = criarFiltroTelefone(filtro)
    return telefones.filter(({ telefone }) => aceita(telefone))
  }, [telefones, filtro])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (novoTelefone.trim()) {
      onSelectTelefone(novoTelefone.trim())
      setNovoTelefone('')
      setModalNovo(false)
    }
  }

  return (
    // Mesma altura do ChatArea (600px) no desktop; só a lista de conversas rola, para a página
    // não crescer com o número de telefones e o rodapé continuar visível.
    <div className="card flex flex-col md:h-[600px]">
      <h2 className="font-semibold text-inforrel-primary mb-4 font-heading flex items-center gap-2">
        <Phone size={20} />
        Telefones
      </h2>

      {/* O número do telefone novo é digitado num modal; o botão divide a linha com o filtro */}
      <div className="flex items-end gap-2 mb-3">
        <button
          type="button"
          onClick={() => setModalNovo(true)}
          className="btn-primary shrink-0 h-9 px-3 text-sm whitespace-nowrap flex items-center gap-1.5"
        >
          <Plus size={16} />
          Iniciar Conversa
        </button>
        {telefones.length > 0 && (
          <div className="flex-1 min-w-0">
            <label htmlFor="filtro-telefones" className="block text-xs text-gray-500 mb-0.5 truncate">
              Filtrar telefones:
              {filtro.trim() && ` ${filtrados.length} de ${telefones.length}`}
            </label>
            <div className="relative">
              <Search size={14} className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                id="filtro-telefones"
                type="text"
                value={filtro}
                onChange={(e) => setFiltro(e.target.value)}
                placeholder="ex.: *73*"
                title="* vale qualquer sequência: *73* contém 73, *73 termina com 73, +5519* começa com +5519. Sem *, menos de 10 caracteres é busca parcial; 10 ou mais, número exato."
                className="input h-9 text-sm py-1 pl-7 pr-7"
              />
              {filtro && (
                <button
                  type="button"
                  onClick={() => setFiltro('')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  aria-label="Limpar filtro"
                >
                  <X size={14} />
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Lista de telefones — ordenada pelo backend por última mensagem
          (mais recente primeiro), a conversa ativa sempre fica no topo. */}
      <div className="border-t pt-3 flex flex-col flex-1 min-h-0">
        {telefones.length === 0 ? (
          <p className="text-gray-400 text-sm italic">Nenhuma conversa</p>
        ) : filtrados.length === 0 ? (
          <p className="text-gray-400 text-sm italic">Nenhum telefone corresponde ao filtro</p>
        ) : (
          <ul className="space-y-1 overflow-y-auto flex-1 min-h-0 max-h-80 md:max-h-none pr-1">
            {filtrados.map(({ telefone: tel, ultima_mensagem_em }) => (
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
      {modalNovo && (
        <DetalheModal titulo="Iniciar conversa" onClose={() => setModalNovo(false)}>
          <form onSubmit={handleSubmit} className="space-y-3">
            <label htmlFor="novo-telefone" className="block text-sm text-gray-600">
              Número do telefone (com DDI e DDD)
            </label>
            <input
              id="novo-telefone"
              type="text"
              value={novoTelefone}
              onChange={(e) => setNovoTelefone(e.target.value)}
              onKeyDown={(e) => e.key === 'Escape' && setModalNovo(false)}
              placeholder="+5511999999999"
              autoFocus
              className="input"
            />
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setModalNovo(false)}
                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={!novoTelefone.trim()}
                className="btn-primary text-sm flex items-center gap-1.5"
              >
                <Plus size={16} />
                Iniciar
              </button>
            </div>
          </form>
        </DetalheModal>
      )}
    </div>
  )
}

export default PhonePanel
