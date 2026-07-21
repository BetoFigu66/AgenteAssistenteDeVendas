import { useState, useEffect, useCallback } from 'react'
import { RefreshCw, CheckCircle, Edit2, Trash2, Plus, Search, Filter, BookOpen, Flame, AlertTriangle } from 'lucide-react'
import { api } from '../services/api'
import DetalheModal from './DetalheModal'
import { CONTEXTOS_QA as CONTEXTOS } from '../constants/qa'

const BADGE_CONTEXTO = {
  catraca: 'bg-blue-100 text-blue-800',
  relogio_ponto: 'bg-purple-100 text-purple-800',
  facial: 'bg-pink-100 text-pink-800',
  controle_acesso: 'bg-indigo-100 text-indigo-800',
  bastao_ronda: 'bg-yellow-100 text-yellow-800',
  geral: 'bg-gray-100 text-gray-700',
}

function QABasePage() {
  const [pares, setPares] = useState([])
  const [total, setTotal] = useState(0)
  const [carregando, setCarregando] = useState(false)
  const [erro, setErro] = useState(null)

  // Filtros
  const [filtroContexto, setFiltroContexto] = useState('')
  const [filtroTag, setFiltroTag] = useState('')
  const [filtroAprovado, setFiltroAprovado] = useState('')
  const [filtroAtivo, setFiltroAtivo] = useState('true')
  const [buscaTexto, setBuscaTexto] = useState('')

  // Estatísticas de uso (REQ-013.7)
  const [statsUso, setStatsUso] = useState([])

  // Modal de edição
  const [parEditando, setParEditando] = useState(null)
  const [editPergunta, setEditPergunta] = useState('')
  const [editResposta, setEditResposta] = useState('')
  const [editContexto, setEditContexto] = useState('')
  const [salvandoEdicao, setSalvandoEdicao] = useState(false)

  // Modal de criação
  const [mostrarModalCriar, setMostrarModalCriar] = useState(false)
  const [novoPergunta, setNovoPergunta] = useState('')
  const [novoResposta, setNovoResposta] = useState('')
  const [novoContexto, setNovoContexto] = useState('')
  const [criando, setCriando] = useState(false)

  // Detecção de duplicatas por similaridade (REQ-013.5) — dispara antes de
  // criar de fato; usuário confirma explicitamente se quiser prosseguir mesmo
  // com candidatos parecidos já existentes.
  const [verificandoSimilares, setVerificandoSimilares] = useState(false)
  const [similaresEncontrados, setSimilaresEncontrados] = useState([])
  const [confirmandoSimilares, setConfirmandoSimilares] = useState(false)

  // Aprovação em andamento
  const [aprovandoId, setAprovandoId] = useState(null)
  const [desativandoId, setDesativandoId] = useState(null)

  const carregarPares = useCallback(async () => {
    setCarregando(true)
    setErro(null)
    try {
      const params = {}
      if (filtroContexto) params.contexto = filtroContexto
      if (filtroTag.trim()) params.tag = filtroTag.trim()
      if (filtroAprovado !== '') params.aprovado = filtroAprovado === 'true'
      if (filtroAtivo !== '') params.ativo = filtroAtivo === 'true'
      params.limit = 100
      const data = await api.listarParesQA(params)
      setPares(data.pares || [])
      setTotal(data.total || 0)
    } catch (e) {
      setErro('Erro ao carregar pares Q&A: ' + e.message)
    } finally {
      setCarregando(false)
    }
  }, [filtroContexto, filtroTag, filtroAprovado, filtroAtivo])

  useEffect(() => {
    carregarPares()
  }, [carregarPares])

  useEffect(() => {
    api.estatisticasUsoQA({ top: 5 })
      .then((data) => setStatsUso(data.estatisticas || []))
      .catch(() => setStatsUso([]))
  }, [])

  const paresVisiveis = pares.filter(p => {
    if (!buscaTexto.trim()) return true
    const termo = buscaTexto.toLowerCase()
    return p.pergunta?.toLowerCase().includes(termo) || p.resposta?.toLowerCase().includes(termo)
  })

  const abrirEdicao = (par) => {
    setParEditando(par)
    setEditPergunta(par.pergunta || '')
    setEditResposta(par.resposta || '')
    setEditContexto(par.contexto || '')
  }

  const fecharEdicao = () => {
    setParEditando(null)
    setEditPergunta('')
    setEditResposta('')
    setEditContexto('')
  }

  const handleSalvarEdicao = async () => {
    if (!editPergunta.trim() || !editResposta.trim()) return
    setSalvandoEdicao(true)
    try {
      await api.atualizarParQA(parEditando.id, {
        pergunta: editPergunta.trim(),
        resposta: editResposta.trim(),
        contexto: editContexto || null,
      })
      fecharEdicao()
      carregarPares()
    } catch (e) {
      alert('Erro ao salvar: ' + e.message)
    } finally {
      setSalvandoEdicao(false)
    }
  }

  const handleAprovar = async (id) => {
    setAprovandoId(id)
    try {
      await api.aprovarParQA(id)
      carregarPares()
    } catch (e) {
      alert('Erro ao aprovar: ' + e.message)
    } finally {
      setAprovandoId(null)
    }
  }

  const handleDesativar = async (id) => {
    if (!confirm('Desativar este par Q&A?')) return
    setDesativandoId(id)
    try {
      await api.desativarParQA(id)
      carregarPares()
    } catch (e) {
      alert('Erro ao desativar: ' + e.message)
    } finally {
      setDesativandoId(null)
    }
  }

  const SIMILARIDADE_ALERTA_MIN = 0.8

  const fecharModalCriar = () => {
    setMostrarModalCriar(false)
    setNovoPergunta('')
    setNovoResposta('')
    setNovoContexto('')
    setSimilaresEncontrados([])
    setConfirmandoSimilares(false)
  }

  const handleCriar = async () => {
    if (!novoPergunta.trim() || !novoResposta.trim() || criando || verificandoSimilares) return

    if (!confirmandoSimilares) {
      setVerificandoSimilares(true)
      try {
        const data = await api.buscarSimilaresQA(novoPergunta.trim(), 5)
        const candidatos = (data.candidatos || []).filter((c) => c.score >= SIMILARIDADE_ALERTA_MIN)
        if (candidatos.length > 0) {
          setSimilaresEncontrados(candidatos)
          setConfirmandoSimilares(true)
          return
        }
      } catch {
        // busca de similares indisponível (ex.: embedding provider fora do ar) —
        // não bloqueia a criação por conta disso, só não alerta de duplicata.
      } finally {
        setVerificandoSimilares(false)
      }
    }

    setCriando(true)
    try {
      await api.criarParQA({
        pergunta: novoPergunta.trim(),
        resposta: novoResposta.trim(),
        contexto: novoContexto || null,
      })
      fecharModalCriar()
      carregarPares()
    } catch (e) {
      alert('Erro ao criar: ' + e.message)
    } finally {
      setCriando(false)
    }
  }

  const pendentesCount = pares.filter(p => p.ativo && !p.aprovado).length

  return (
    <div className="container mx-auto px-4 py-6 max-w-7xl">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <BookOpen size={20} className="text-inforrel-primary" />
            <h2 className="text-lg font-semibold text-inforrel-primary">Base Q&A</h2>
            <span className="text-sm text-gray-500">{total} par(es) total</span>
            {pendentesCount > 0 && (
              <span className="px-2 py-0.5 bg-orange-100 text-orange-800 text-xs font-medium rounded-full">
                {pendentesCount} aguardando aprovação
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={carregarPares}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 hover:text-inforrel-primary transition"
            >
              <RefreshCw size={15} className={carregando ? 'animate-spin' : ''} />
              Atualizar
            </button>
            <button
              onClick={() => setMostrarModalCriar(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-inforrel-primary text-white text-sm rounded-md hover:bg-inforrel-secondary transition"
            >
              <Plus size={15} />
              Novo par
            </button>
          </div>
        </div>

        {/* Filtros */}
        <div className="mt-3 flex flex-wrap gap-2 items-center">
          <Filter size={14} className="text-gray-400" />
          <select
            value={filtroContexto}
            onChange={(e) => setFiltroContexto(e.target.value)}
            className="px-2 py-1.5 border border-gray-200 rounded text-sm focus:outline-none focus:ring-1 focus:ring-inforrel-primary"
          >
            {CONTEXTOS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
          <select
            value={filtroAprovado}
            onChange={(e) => setFiltroAprovado(e.target.value)}
            className="px-2 py-1.5 border border-gray-200 rounded text-sm focus:outline-none focus:ring-1 focus:ring-inforrel-primary"
          >
            <option value="">Todos (aprovado)</option>
            <option value="true">Aprovados</option>
            <option value="false">Pendentes</option>
          </select>
          <select
            value={filtroAtivo}
            onChange={(e) => setFiltroAtivo(e.target.value)}
            className="px-2 py-1.5 border border-gray-200 rounded text-sm focus:outline-none focus:ring-1 focus:ring-inforrel-primary"
          >
            <option value="true">Ativos</option>
            <option value="false">Inativos</option>
            <option value="">Todos</option>
          </select>
          <input
            type="text"
            value={filtroTag}
            onChange={(e) => setFiltroTag(e.target.value)}
            placeholder="Filtrar por tag..."
            className="px-2 py-1.5 border border-gray-200 rounded text-sm w-36 focus:outline-none focus:ring-1 focus:ring-inforrel-primary"
          />
          <div className="flex items-center gap-1 flex-1 min-w-[180px] max-w-xs">
            <Search size={14} className="text-gray-400 ml-1 absolute pointer-events-none" />
            <input
              type="text"
              value={buscaTexto}
              onChange={(e) => setBuscaTexto(e.target.value)}
              placeholder="Buscar por texto..."
              className="w-full pl-6 pr-3 py-1.5 border border-gray-200 rounded text-sm focus:outline-none focus:ring-1 focus:ring-inforrel-primary relative"
            />
          </div>
          {buscaTexto && (
            <span className="text-xs text-gray-500">{paresVisiveis.length} resultado(s)</span>
          )}
        </div>
      </div>

      {/* Pares mais usados (REQ-013.7) */}
      {statsUso.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-3 mb-4">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <Flame size={13} className="text-orange-500" /> Pares mais usados (últimos 90 dias)
          </h3>
          <div className="flex flex-wrap gap-2">
            {statsUso.map((s) => (
              <span
                key={s.id_externo}
                title={s.par?.pergunta || s.id_externo}
                className="text-xs bg-gray-50 border border-gray-200 rounded-full px-2.5 py-1 flex items-center gap-1.5 max-w-xs"
              >
                <span className="font-semibold text-inforrel-primary">{s.usos}×</span>
                <span className="truncate">{s.par?.pergunta || s.id_externo}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Erro */}
      {erro && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-700">{erro}</div>
      )}

      {/* Tabela */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        {carregando ? (
          <div className="p-12 text-center text-gray-500">
            <RefreshCw size={24} className="animate-spin mx-auto mb-2" />
            Carregando pares Q&A...
          </div>
        ) : paresVisiveis.length === 0 ? (
          <div className="p-12 text-center text-gray-400">
            <BookOpen size={32} className="mx-auto mb-2 opacity-40" />
            <p>Nenhum par encontrado com os filtros selecionados.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase w-12">#</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase w-32">Contexto</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Pergunta</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Resposta</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase w-28">Status</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase w-32">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {paresVisiveis.map(par => (
                  <tr key={par.id} className={`hover:bg-gray-50 transition ${!par.ativo ? 'opacity-50' : ''}`}>
                    <td className="px-4 py-3 text-gray-400 text-xs">{par.id}</td>
                    <td className="px-4 py-3">
                      {par.contexto ? (
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${BADGE_CONTEXTO[par.contexto] || 'bg-gray-100 text-gray-700'}`}>
                          {par.contexto}
                        </span>
                      ) : (
                        <span className="text-gray-400 text-xs">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-800 max-w-xs">
                      <p className="line-clamp-2 leading-snug">{par.pergunta}</p>
                      <p className="text-xs text-gray-400 mt-0.5 flex items-center gap-1.5 flex-wrap">
                        {par.criado_por && <span>por: {par.criado_por}</span>}
                        <span
                          title="id_externo — origem/rastreabilidade do par"
                          className="font-mono bg-gray-100 rounded px-1"
                        >
                          {par.id_externo}
                        </span>
                      </p>
                    </td>
                    <td className="px-4 py-3 text-gray-600 max-w-sm">
                      <p className="line-clamp-2 leading-snug text-xs">{par.resposta}</p>
                    </td>
                    <td className="px-4 py-3">
                      {par.aprovado ? (
                        <span className="flex items-center gap-1 text-xs text-green-700 font-medium">
                          <CheckCircle size={13} />
                          Aprovado
                        </span>
                      ) : (
                        <span className="text-xs text-orange-600 font-medium">⏳ Pendente</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        {!par.aprovado && par.ativo && (
                          <button
                            onClick={() => handleAprovar(par.id)}
                            disabled={aprovandoId === par.id}
                            title="Aprovar (gera embedding)"
                            className="p-1.5 rounded text-green-600 hover:bg-green-50 transition disabled:opacity-50"
                          >
                            {aprovandoId === par.id
                              ? <RefreshCw size={14} className="animate-spin" />
                              : <CheckCircle size={14} />
                            }
                          </button>
                        )}
                        <button
                          onClick={() => abrirEdicao(par)}
                          title="Editar"
                          className="p-1.5 rounded text-gray-500 hover:bg-gray-100 transition"
                        >
                          <Edit2 size={14} />
                        </button>
                        {par.ativo && (
                          <button
                            onClick={() => handleDesativar(par.id)}
                            disabled={desativandoId === par.id}
                            title="Desativar"
                            className="p-1.5 rounded text-red-400 hover:bg-red-50 transition disabled:opacity-50"
                          >
                            {desativandoId === par.id
                              ? <RefreshCw size={14} className="animate-spin" />
                              : <Trash2 size={14} />
                            }
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal de edição */}
      {parEditando && (
        <DetalheModal
          titulo={`Editar Par Q&A #${parEditando.id}`}
          onClose={fecharEdicao}
        >
          <div className="p-4 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Pergunta</label>
              <textarea
                value={editPergunta}
                onChange={(e) => setEditPergunta(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-inforrel-primary resize-none text-sm"
                rows={3}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Resposta</label>
              <textarea
                value={editResposta}
                onChange={(e) => setEditResposta(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-inforrel-primary resize-none text-sm"
                rows={5}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Contexto</label>
              <select
                value={editContexto}
                onChange={(e) => setEditContexto(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-inforrel-primary text-sm"
              >
                {CONTEXTOS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </div>
            {parEditando.aprovado && (
              <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded p-2">
                ⚠️ Este par já está aprovado. Editar a pergunta irá re-gerar o embedding na próxima aprovação.
              </p>
            )}
            <div className="flex justify-end gap-2">
              <button onClick={fecharEdicao} className="px-4 py-2 text-gray-600 hover:text-gray-800 transition">
                Cancelar
              </button>
              <button
                onClick={handleSalvarEdicao}
                disabled={!editPergunta.trim() || !editResposta.trim() || salvandoEdicao}
                className="px-4 py-2 bg-inforrel-primary text-white rounded-md hover:bg-inforrel-secondary transition disabled:opacity-50 flex items-center gap-2"
              >
                {salvandoEdicao ? <><RefreshCw size={15} className="animate-spin" />Salvando...</> : 'Salvar'}
              </button>
            </div>
          </div>
        </DetalheModal>
      )}

      {/* Modal de criação */}
      {mostrarModalCriar && (
        <DetalheModal
          titulo="Novo Par Q&A"
          onClose={fecharModalCriar}
        >
          <div className="p-4 space-y-4">
            <p className="text-xs text-gray-500 bg-blue-50 border border-blue-100 rounded p-2">
              O par será salvo como rascunho (ativo, não aprovado). O embedding será gerado na aprovação.
            </p>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Pergunta <span className="text-red-500">*</span>
              </label>
              <textarea
                value={novoPergunta}
                onChange={(e) => {
                  setNovoPergunta(e.target.value)
                  setConfirmandoSimilares(false)
                  setSimilaresEncontrados([])
                }}
                placeholder="Como o cliente costuma perguntar..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-inforrel-primary resize-none text-sm"
                rows={3}
                autoFocus
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Resposta <span className="text-red-500">*</span>
              </label>
              <textarea
                value={novoResposta}
                onChange={(e) => setNovoResposta(e.target.value)}
                placeholder="Resposta ideal para esta pergunta..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-inforrel-primary resize-none text-sm"
                rows={5}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Contexto</label>
              <select
                value={novoContexto}
                onChange={(e) => setNovoContexto(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-inforrel-primary text-sm"
              >
                {CONTEXTOS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </div>

            {confirmandoSimilares && similaresEncontrados.length > 0 && (
              <div className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded p-2.5 space-y-1.5">
                <p className="flex items-center gap-1 font-medium">
                  <AlertTriangle size={13} /> Já existem par(es) parecido(s) na base:
                </p>
                <ul className="space-y-1 pl-1">
                  {similaresEncontrados.map((c) => (
                    <li key={c.id} className="border-l-2 border-amber-300 pl-2">
                      <span className="font-mono text-amber-600">{Math.round(c.score * 100)}%</span>{' '}
                      <span className="italic">"{c.pergunta}"</span>
                      {!c.aprovado && <span className="text-amber-500"> (rascunho)</span>}
                    </li>
                  ))}
                </ul>
                <p>Clique em "Criar mesmo assim" para prosseguir ou ajuste a pergunta acima.</p>
              </div>
            )}

            <div className="flex justify-end gap-2">
              <button
                onClick={fecharModalCriar}
                className="px-4 py-2 text-gray-600 hover:text-gray-800 transition"
              >
                Cancelar
              </button>
              <button
                onClick={handleCriar}
                disabled={!novoPergunta.trim() || !novoResposta.trim() || criando || verificandoSimilares}
                className="px-4 py-2 bg-inforrel-primary text-white rounded-md hover:bg-inforrel-secondary transition disabled:opacity-50 flex items-center gap-2"
              >
                {verificandoSimilares ? (
                  <><RefreshCw size={15} className="animate-spin" />Verificando duplicatas...</>
                ) : criando ? (
                  <><RefreshCw size={15} className="animate-spin" />Salvando...</>
                ) : confirmandoSimilares ? (
                  'Criar mesmo assim'
                ) : (
                  'Salvar rascunho'
                )}
              </button>
            </div>
          </div>
        </DetalheModal>
      )}
    </div>
  )
}

export default QABasePage
