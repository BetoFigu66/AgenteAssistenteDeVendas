import { useState, useEffect, useCallback } from 'react'
import { RefreshCw, Settings, Save, CheckCircle } from 'lucide-react'
import { api } from '../services/api'
import { formatDatetimeBRT } from '../utils/datetime'

function ParametrosPage() {
  const [parametros, setParametros] = useState([])
  const [valoresEditados, setValoresEditados] = useState({})
  const [carregando, setCarregando] = useState(false)
  const [erro, setErro] = useState(null)
  const [salvandoNome, setSalvandoNome] = useState(null)
  const [salvoNome, setSalvoNome] = useState(null)

  const carregarParametros = useCallback(async () => {
    setCarregando(true)
    setErro(null)
    try {
      const data = await api.listarParametros()
      const lista = data.parametros || []
      setParametros(lista)
      const mapa = {}
      lista.forEach((p) => {
        mapa[p.nome] = p.valor ?? ''
      })
      setValoresEditados(mapa)
    } catch (e) {
      setErro('Erro ao carregar parâmetros: ' + e.message)
    } finally {
      setCarregando(false)
    }
  }, [])

  useEffect(() => {
    carregarParametros()
  }, [carregarParametros])

  const valorAlterado = (nome) => {
    const original = parametros.find((p) => p.nome === nome)?.valor ?? ''
    return (valoresEditados[nome] ?? '') !== original
  }

  const handleValorChange = (nome, valor) => {
    setValoresEditados((prev) => ({ ...prev, [nome]: valor }))
    setSalvoNome((atual) => (atual === nome ? null : atual))
  }

  const handleSalvar = async (nome) => {
    setSalvandoNome(nome)
    setErro(null)
    try {
      const atualizado = await api.atualizarParametro(nome, valoresEditados[nome])
      setParametros((prev) =>
        prev.map((p) => (p.nome === nome ? { ...p, ...atualizado } : p)),
      )
      setValoresEditados((prev) => ({ ...prev, [nome]: atualizado.valor }))
      setSalvoNome(nome)
      setTimeout(() => setSalvoNome((atual) => (atual === nome ? null : atual)), 2000)
    } catch (e) {
      setErro(`Erro ao salvar "${nome}": ${e.message}`)
    } finally {
      setSalvandoNome(null)
    }
  }

  return (
    <div className="container mx-auto px-4 py-6 max-w-7xl">
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Settings size={20} className="text-inforrel-primary" />
            <h2 className="text-lg font-semibold text-inforrel-primary">Parâmetros</h2>
            <span className="text-sm text-gray-500">{parametros.length} registro(s)</span>
          </div>
          <button
            onClick={carregarParametros}
            disabled={carregando}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 hover:text-inforrel-primary transition disabled:opacity-50"
          >
            <RefreshCw size={15} className={carregando ? 'animate-spin' : ''} />
            Atualizar
          </button>
        </div>
        <p className="mt-2 text-sm text-gray-500">
          Nome e descrição são somente leitura. Alterações no valor entram em vigor conforme REQ-014
          (sem reiniciar o servidor).
        </p>
      </div>

      {erro && (
        <div className="mb-4 px-4 py-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg">
          {erro}
        </div>
      )}

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        {carregando && parametros.length === 0 ? (
          <p className="p-8 text-center text-gray-500 text-sm">Carregando parâmetros...</p>
        ) : parametros.length === 0 ? (
          <p className="p-8 text-center text-gray-500 text-sm">Nenhum parâmetro cadastrado.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200 text-left">
                  <th className="px-4 py-3 font-medium text-gray-600 w-64">Nome</th>
                  <th className="px-4 py-3 font-medium text-gray-600">Descrição</th>
                  <th className="px-4 py-3 font-medium text-gray-600 w-48">Valor</th>
                  <th className="px-4 py-3 font-medium text-gray-600 w-36">Atualizado</th>
                  <th className="px-4 py-3 font-medium text-gray-600 w-24" />
                </tr>
              </thead>
              <tbody>
                {parametros.map((p) => {
                  const dirty = valorAlterado(p.nome)
                  const salvando = salvandoNome === p.nome
                  const salvo = salvoNome === p.nome
                  return (
                    <tr key={p.nome} className="border-b border-gray-100 hover:bg-gray-50/50">
                      <td className="px-4 py-3 align-top">
                        <code className="text-xs bg-gray-100 text-gray-800 px-1.5 py-0.5 rounded break-all">
                          {p.nome}
                        </code>
                      </td>
                      <td className="px-4 py-3 align-top text-gray-600">
                        {p.descricao || <span className="italic text-gray-400">—</span>}
                      </td>
                      <td className="px-4 py-3 align-top">
                        <input
                          type="text"
                          value={valoresEditados[p.nome] ?? ''}
                          onChange={(e) => handleValorChange(p.nome, e.target.value)}
                          className="w-full px-2 py-1.5 border border-gray-200 rounded text-sm font-mono focus:outline-none focus:ring-1 focus:ring-inforrel-primary"
                          aria-label={`Valor de ${p.nome}`}
                        />
                      </td>
                      <td className="px-4 py-3 align-top text-xs text-gray-500 whitespace-nowrap">
                        {formatDatetimeBRT(p.updated_at)}
                      </td>
                      <td className="px-4 py-3 align-top">
                        {salvo ? (
                          <span className="inline-flex items-center gap-1 text-green-600 text-xs">
                            <CheckCircle size={14} />
                            Salvo
                          </span>
                        ) : (
                          <button
                            type="button"
                            onClick={() => handleSalvar(p.nome)}
                            disabled={!dirty || salvando}
                            className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded bg-inforrel-primary text-white hover:bg-inforrel-secondary transition disabled:opacity-40 disabled:cursor-not-allowed"
                          >
                            <Save size={12} />
                            {salvando ? '...' : 'Salvar'}
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

export default ParametrosPage
