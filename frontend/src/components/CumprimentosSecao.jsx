import { useState, useEffect, useCallback } from 'react'
import { MessageCircle, Plus, Save, Trash2, CheckCircle, Search } from 'lucide-react'
import { api } from '../services/api'
import { formatDatetimeBRT } from '../utils/datetime'

// Cumprimentos: o que conta como início de conversa e com que frase o assistente responde
// (backend/services/cumprimentos.py). Fica dentro da tela de Parâmetros.
function CumprimentosSecao() {
  const [itens, setItens] = useState([])
  const [edicoes, setEdicoes] = useState({})
  const [carregando, setCarregando] = useState(false)
  const [erro, setErro] = useState(null)
  const [salvandoId, setSalvandoId] = useState(null)
  const [salvoId, setSalvoId] = useState(null)
  const [nova, setNova] = useState({ expressao: '', resposta: '' })
  const [textoTeste, setTextoTeste] = useState('')
  const [resultadoTeste, setResultadoTeste] = useState(null)

  const carregar = useCallback(async () => {
    setCarregando(true)
    setErro(null)
    try {
      const data = await api.listarCumprimentos()
      const lista = data.cumprimentos || []
      setItens(lista)
      const mapa = {}
      lista.forEach((c) => {
        mapa[c.id] = { expressao: c.expressao, resposta: c.resposta, ativo: c.ativo }
      })
      setEdicoes(mapa)
    } catch (e) {
      setErro('Erro ao carregar cumprimentos: ' + e.message)
    } finally {
      setCarregando(false)
    }
  }, [])

  useEffect(() => {
    carregar()
  }, [carregar])

  const alterado = (c) => {
    const e = edicoes[c.id]
    return e && (e.expressao !== c.expressao || e.resposta !== c.resposta || e.ativo !== c.ativo)
  }

  const editar = (id, campo, valor) => {
    setEdicoes((prev) => ({ ...prev, [id]: { ...prev[id], [campo]: valor } }))
    setSalvoId((atual) => (atual === id ? null : atual))
  }

  const salvar = async (c) => {
    setSalvandoId(c.id)
    setErro(null)
    try {
      const atualizado = await api.salvarCumprimento(c.id, edicoes[c.id])
      setItens((prev) => prev.map((i) => (i.id === c.id ? atualizado : i)))
      setEdicoes((prev) => ({
        ...prev,
        [c.id]: { expressao: atualizado.expressao, resposta: atualizado.resposta, ativo: atualizado.ativo },
      }))
      setSalvoId(c.id)
      setTimeout(() => setSalvoId((atual) => (atual === c.id ? null : atual)), 2000)
    } catch (e) {
      setErro(`Erro ao salvar "${c.expressao}": ${e.message}`)
    } finally {
      setSalvandoId(null)
    }
  }

  const excluir = async (c) => {
    if (!confirm(`Excluir o cumprimento "${c.expressao}"?`)) return
    setErro(null)
    try {
      await api.excluirCumprimento(c.id)
      await carregar()
    } catch (e) {
      setErro(`Erro ao excluir "${c.expressao}": ${e.message}`)
    }
  }

  const adicionar = async (e) => {
    e.preventDefault()
    setErro(null)
    try {
      await api.salvarCumprimento(null, nova)
      setNova({ expressao: '', resposta: '' })
      await carregar()
    } catch (err) {
      setErro('Erro ao adicionar: ' + err.message)
    }
  }

  const testar = async (e) => {
    e.preventDefault()
    if (!textoTeste.trim()) return
    try {
      setResultadoTeste(await api.testarCumprimento(textoTeste))
    } catch (err) {
      setErro(err.message)
    }
  }

  const campo =
    'w-full px-2 py-1.5 border border-gray-200 rounded text-sm focus:outline-none focus:ring-1 focus:ring-inforrel-primary'

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 mt-6">
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <MessageCircle size={20} className="text-inforrel-primary" />
          <h2 className="text-lg font-semibold text-inforrel-primary">Cumprimentos</h2>
          <span className="text-sm text-gray-500">{itens.length} registro(s)</span>
        </div>
        <p className="mt-2 text-sm text-gray-500">
          Mensagem com uma destas expressões conta como início de conversa, e o assistente abre a resposta com a
          frase cadastrada (ex.: “Bom dia” recebe “Bom dia!”). Sem expressão reconhecida, ele responde “Olá!”.
          Resposta em branco: conta como cumprimento, mas não escolhe a frase. Vale na hora, sem reiniciar.
        </p>
      </div>

      {erro && (
        <div className="m-4 px-4 py-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg">{erro}</div>
      )}

      <div className="p-4 grid gap-4 md:grid-cols-2 border-b border-gray-100">
        <form onSubmit={adicionar} className="flex flex-col gap-2">
          <span className="text-sm font-medium text-gray-700">Novo cumprimento</span>
          <div className="flex gap-2">
            <input
              value={nova.expressao}
              onChange={(e) => setNova((n) => ({ ...n, expressao: e.target.value }))}
              placeholder="Expressão (ex.: E aí Bro)"
              className={campo}
              aria-label="Expressão do novo cumprimento"
            />
            <input
              value={nova.resposta}
              onChange={(e) => setNova((n) => ({ ...n, resposta: e.target.value }))}
              placeholder="Resposta (ex.: E aí?)"
              className={campo}
              aria-label="Resposta do novo cumprimento"
            />
            <button
              type="submit"
              disabled={!nova.expressao.trim()}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-sm rounded bg-inforrel-primary text-white hover:bg-inforrel-secondary transition disabled:opacity-40 disabled:cursor-not-allowed whitespace-nowrap"
            >
              <Plus size={14} />
              Adicionar
            </button>
          </div>
        </form>

        <form onSubmit={testar} className="flex flex-col gap-2">
          <span className="text-sm font-medium text-gray-700">Testar uma mensagem</span>
          <div className="flex gap-2">
            <input
              value={textoTeste}
              onChange={(e) => {
                setTextoTeste(e.target.value)
                setResultadoTeste(null)
              }}
              placeholder="Ex.: Boa tarde, tudo bem?"
              className={campo}
              aria-label="Mensagem para testar"
            />
            <button
              type="submit"
              className="inline-flex items-center gap-1 px-3 py-1.5 text-sm rounded border border-inforrel-primary text-inforrel-primary hover:bg-inforrel-primary hover:text-white transition whitespace-nowrap"
            >
              <Search size={14} />
              Testar
            </button>
          </div>
          {resultadoTeste && (
            <p className="text-sm text-gray-600">
              {resultadoTeste.e_cumprimento ? 'Reconhecido como cumprimento' : 'Não é cumprimento'}. O assistente
              abriria com <strong>{resultadoTeste.resposta}</strong>
              {resultadoTeste.expressoes.length > 0 && (
                <span className="text-gray-400"> (expressões: {resultadoTeste.expressoes.join(', ')})</span>
              )}
            </p>
          )}
        </form>
      </div>

      {carregando && itens.length === 0 ? (
        <p className="p-8 text-center text-gray-500 text-sm">Carregando cumprimentos...</p>
      ) : itens.length === 0 ? (
        <p className="p-8 text-center text-gray-500 text-sm">Nenhum cumprimento cadastrado.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200 text-left">
                <th className="px-4 py-3 font-medium text-gray-600">Expressão</th>
                <th className="px-4 py-3 font-medium text-gray-600">Resposta</th>
                <th className="px-4 py-3 font-medium text-gray-600 w-20">Ativo</th>
                <th className="px-4 py-3 font-medium text-gray-600 w-44">Atualizado</th>
                <th className="px-4 py-3 font-medium text-gray-600 w-36" />
              </tr>
            </thead>
            <tbody>
              {itens.map((c) => {
                const e = edicoes[c.id] || {}
                const salvando = salvandoId === c.id
                return (
                  <tr key={c.id} className="border-b border-gray-100 hover:bg-gray-50/50">
                    <td className="px-4 py-2">
                      <input
                        value={e.expressao ?? ''}
                        onChange={(ev) => editar(c.id, 'expressao', ev.target.value)}
                        className={campo}
                        aria-label={`Expressão de ${c.expressao}`}
                      />
                    </td>
                    <td className="px-4 py-2">
                      <input
                        value={e.resposta ?? ''}
                        onChange={(ev) => editar(c.id, 'resposta', ev.target.value)}
                        placeholder="(em branco)"
                        className={campo}
                        aria-label={`Resposta de ${c.expressao}`}
                      />
                    </td>
                    <td className="px-4 py-2">
                      <input
                        type="checkbox"
                        checked={!!e.ativo}
                        onChange={(ev) => editar(c.id, 'ativo', ev.target.checked)}
                        aria-label={`Ativo: ${c.expressao}`}
                      />
                    </td>
                    <td className="px-4 py-2 text-xs text-gray-500 whitespace-nowrap">
                      {formatDatetimeBRT(c.updated_at)}
                      {c.atualizado_por && <span className="block text-gray-400">{c.atualizado_por}</span>}
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex items-center gap-2">
                        {salvoId === c.id ? (
                          <span className="inline-flex items-center gap-1 text-green-600 text-xs">
                            <CheckCircle size={14} />
                            Salvo
                          </span>
                        ) : (
                          <button
                            type="button"
                            onClick={() => salvar(c)}
                            disabled={!alterado(c) || salvando}
                            className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded bg-inforrel-primary text-white hover:bg-inforrel-secondary transition disabled:opacity-40 disabled:cursor-not-allowed"
                          >
                            <Save size={12} />
                            {salvando ? '...' : 'Salvar'}
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => excluir(c)}
                          className="p-1 text-gray-400 hover:text-red-600 transition"
                          title="Excluir"
                          aria-label={`Excluir ${c.expressao}`}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default CumprimentosSecao
