import { useState, useEffect, useCallback } from 'react'
import { ListChecks, Plus, Save, Trash2, CheckCircle } from 'lucide-react'
import { api } from '../services/api'
import { formatDatetimeBRT } from '../utils/datetime'
import { rotuloCampo } from '../utils/atendimento'

// Perguntas do roteiro de qualificação com texto por produto
// (backend/services/perguntas_produto.py). Fica dentro da tela de Parâmetros.
function PerguntasProdutoSecao() {
  const [itens, setItens] = useState([])
  const [produtos, setProdutos] = useState([])
  const [campos, setCampos] = useState([])
  const [edicoes, setEdicoes] = useState({})
  const [carregando, setCarregando] = useState(false)
  const [erro, setErro] = useState(null)
  const [salvandoId, setSalvandoId] = useState(null)
  const [salvoId, setSalvoId] = useState(null)
  const [nova, setNova] = useState({ produto_id: '', campo: 'modelo_produto', texto: '' })

  const carregar = useCallback(async () => {
    setCarregando(true)
    setErro(null)
    try {
      const data = await api.listarPerguntasProduto()
      const lista = data.perguntas || []
      setItens(lista)
      setProdutos(data.produtos || [])
      setCampos(data.campos || [])
      const mapa = {}
      lista.forEach((p) => {
        mapa[p.id] = { texto: p.texto, ativo: p.ativo }
      })
      setEdicoes(mapa)
    } catch (e) {
      setErro('Erro ao carregar as perguntas por produto: ' + e.message)
    } finally {
      setCarregando(false)
    }
  }, [])

  useEffect(() => {
    carregar()
  }, [carregar])

  const textoPadrao = (chave) => campos.find((c) => c.chave === chave)?.texto_padrao || ''

  const alterado = (p) => {
    const e = edicoes[p.id]
    return e && (e.texto !== p.texto || e.ativo !== p.ativo)
  }

  const editar = (id, campo, valor) => {
    setEdicoes((prev) => ({ ...prev, [id]: { ...prev[id], [campo]: valor } }))
    setSalvoId((atual) => (atual === id ? null : atual))
  }

  const salvar = async (p) => {
    setSalvandoId(p.id)
    setErro(null)
    try {
      const atualizado = await api.salvarPerguntaProduto(p.id, edicoes[p.id])
      setItens((prev) => prev.map((i) => (i.id === p.id ? atualizado : i)))
      setEdicoes((prev) => ({ ...prev, [p.id]: { texto: atualizado.texto, ativo: atualizado.ativo } }))
      setSalvoId(p.id)
      setTimeout(() => setSalvoId((atual) => (atual === p.id ? null : atual)), 2000)
    } catch (e) {
      setErro(`Erro ao salvar (${p.produto}, ${rotuloCampo(p.campo)}): ${e.message}`)
    } finally {
      setSalvandoId(null)
    }
  }

  const excluir = async (p) => {
    if (!confirm(`Excluir o texto de "${rotuloCampo(p.campo)}" para ${p.produto}? Volta a valer o padrão.`)) return
    setErro(null)
    try {
      await api.excluirPerguntaProduto(p.id)
      await carregar()
    } catch (e) {
      setErro('Erro ao excluir: ' + e.message)
    }
  }

  const adicionar = async (e) => {
    e.preventDefault()
    setErro(null)
    try {
      await api.salvarPerguntaProduto(null, { ...nova, produto_id: Number(nova.produto_id) })
      setNova((n) => ({ ...n, produto_id: '', texto: '' }))
      await carregar()
    } catch (err) {
      setErro('Erro ao adicionar: ' + err.message)
    }
  }

  const campo =
    'w-full px-2 py-1.5 border border-gray-200 rounded text-sm focus:outline-none focus:ring-1 focus:ring-inforrel-primary'

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 mt-6">
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <ListChecks size={20} className="text-inforrel-primary" />
          <h2 className="text-lg font-semibold text-inforrel-primary">Perguntas por produto</h2>
          <span className="text-sm text-gray-500">{itens.length} registro(s)</span>
        </div>
        <p className="mt-2 text-sm text-gray-500">
          Troca, para um produto, o texto de uma pergunta do roteiro de qualificação (ex.: a pergunta do modelo do
          Relógio de Ponto lista cartográfico, cartão, biometria e facial). Sem texto cadastrado, vale o padrão. Uma
          pergunta por texto (no máximo um “?”). Vale na hora, sem reiniciar.
        </p>
      </div>

      {erro && (
        <div className="m-4 px-4 py-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg">{erro}</div>
      )}

      <form onSubmit={adicionar} className="p-4 flex flex-col gap-2 border-b border-gray-100">
        <span className="text-sm font-medium text-gray-700">Novo texto</span>
        <div className="flex flex-wrap md:flex-nowrap gap-2">
          <select
            value={nova.produto_id}
            onChange={(e) => setNova((n) => ({ ...n, produto_id: e.target.value }))}
            className={`${campo} md:w-56`}
            aria-label="Produto"
          >
            <option value="">Produto...</option>
            {produtos.map((p) => (
              <option key={p.id} value={p.id}>
                {p.descricao}
              </option>
            ))}
          </select>
          <select
            value={nova.campo}
            onChange={(e) => setNova((n) => ({ ...n, campo: e.target.value }))}
            className={`${campo} md:w-48`}
            aria-label="Pergunta"
          >
            {campos.map((c) => (
              <option key={c.chave} value={c.chave}>
                {rotuloCampo(c.chave)}
              </option>
            ))}
          </select>
          <input
            value={nova.texto}
            onChange={(e) => setNova((n) => ({ ...n, texto: e.target.value }))}
            placeholder={textoPadrao(nova.campo)}
            className={campo}
            aria-label="Texto da pergunta"
          />
          <button
            type="submit"
            disabled={!nova.produto_id || !nova.texto.trim()}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-sm rounded bg-inforrel-primary text-white hover:bg-inforrel-secondary transition disabled:opacity-40 disabled:cursor-not-allowed whitespace-nowrap"
          >
            <Plus size={14} />
            Adicionar
          </button>
        </div>
        <span className="text-xs text-gray-400">Padrão desta pergunta: {textoPadrao(nova.campo)}</span>
      </form>

      {carregando && itens.length === 0 ? (
        <p className="p-8 text-center text-gray-500 text-sm">Carregando...</p>
      ) : itens.length === 0 ? (
        <p className="p-8 text-center text-gray-500 text-sm">Nenhum texto por produto cadastrado.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200 text-left">
                <th className="px-4 py-3 font-medium text-gray-600 w-44">Produto</th>
                <th className="px-4 py-3 font-medium text-gray-600 w-36">Pergunta</th>
                <th className="px-4 py-3 font-medium text-gray-600">Texto</th>
                <th className="px-4 py-3 font-medium text-gray-600 w-20">Ativo</th>
                <th className="px-4 py-3 font-medium text-gray-600 w-44">Atualizado</th>
                <th className="px-4 py-3 font-medium text-gray-600 w-36" />
              </tr>
            </thead>
            <tbody>
              {itens.map((p) => {
                const e = edicoes[p.id] || {}
                const salvando = salvandoId === p.id
                return (
                  <tr key={p.id} className="border-b border-gray-100 hover:bg-gray-50/50">
                    <td className="px-4 py-2 text-gray-800">{p.produto}</td>
                    <td className="px-4 py-2 text-gray-800" title={textoPadrao(p.campo)}>
                      {rotuloCampo(p.campo)}
                    </td>
                    <td className="px-4 py-2">
                      <textarea
                        value={e.texto ?? ''}
                        onChange={(ev) => editar(p.id, 'texto', ev.target.value)}
                        rows={2}
                        className={campo}
                        aria-label={`Texto de ${rotuloCampo(p.campo)} para ${p.produto}`}
                      />
                    </td>
                    <td className="px-4 py-2">
                      <input
                        type="checkbox"
                        checked={!!e.ativo}
                        onChange={(ev) => editar(p.id, 'ativo', ev.target.checked)}
                        aria-label={`Ativo: ${rotuloCampo(p.campo)} para ${p.produto}`}
                      />
                    </td>
                    <td className="px-4 py-2 text-xs text-gray-500 whitespace-nowrap">
                      {formatDatetimeBRT(p.updated_at)}
                      {p.atualizado_por && <span className="block text-gray-400">{p.atualizado_por}</span>}
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex items-center gap-2">
                        {salvoId === p.id ? (
                          <span className="inline-flex items-center gap-1 text-green-600 text-xs">
                            <CheckCircle size={14} />
                            Salvo
                          </span>
                        ) : (
                          <button
                            type="button"
                            onClick={() => salvar(p)}
                            disabled={!alterado(p) || salvando}
                            className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded bg-inforrel-primary text-white hover:bg-inforrel-secondary transition disabled:opacity-40 disabled:cursor-not-allowed"
                          >
                            <Save size={12} />
                            {salvando ? '...' : 'Salvar'}
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => excluir(p)}
                          className="p-1 text-gray-400 hover:text-red-600 transition"
                          title="Excluir (volta a valer o padrão)"
                          aria-label={`Excluir ${rotuloCampo(p.campo)} para ${p.produto}`}
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

export default PerguntasProdutoSecao
