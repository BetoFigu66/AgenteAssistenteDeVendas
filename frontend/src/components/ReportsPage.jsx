import { useEffect, useState } from 'react'
import { Flag, RefreshCw, AlertTriangle, Loader2 } from 'lucide-react'
import { api } from '../services/api'
import { formatDatetimeBRT } from '../utils/datetime'
import {
  CATEGORIAS,
  SEVERIDADES,
  STATUS,
  corSeveridade,
  corStatus,
  labelCategoria,
  labelSeveridade,
  labelStatus,
} from '../constants/reports'
import ReportDetalhe from './ReportDetalhe'

function StatCard({ label, valor, valorFiltrado, temFiltro, cor = 'bg-gray-100 text-gray-700' }) {
  const display = temFiltro ? `${valorFiltrado ?? 0}/${valor ?? 0}` : (valor ?? 0)
  return (
    <div className={`rounded-lg px-3 py-2 ${cor}`}>
      <div className="text-xs font-medium uppercase tracking-wide opacity-80">{label}</div>
      <div className="text-xl font-bold">{display}</div>
    </div>
  )
}

function ReportsPage({ onVoltar }) {
  const [reports, setReports] = useState([])
  const [stats, setStats] = useState(null)
  const [statsFiltrados, setStatsFiltrados] = useState(null)
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState(null)
  const [selecionado, setSelecionado] = useState(null)

  // Filtros
  const [filtroStatus, setFiltroStatus] = useState('')
  const [filtroCategoria, setFiltroCategoria] = useState('')
  const [filtroSeveridade, setFiltroSeveridade] = useState('')
  const [apenasAbertos, setApenasAbertos] = useState(true)

  const montarFiltrosApi = () => ({
    status: filtroStatus,
    categoria: filtroCategoria,
    severidade: filtroSeveridade,
    apenas_abertos: !filtroStatus && apenasAbertos ? 'true' : '',
  })

  const temFiltroAtivo =
    !!filtroStatus || !!filtroCategoria || !!filtroSeveridade || (!filtroStatus && apenasAbertos)

  const carregar = async () => {
    setLoading(true)
    setErro(null)
    try {
      const filtros = montarFiltrosApi()
      const [data, s, sFiltrado] = await Promise.all([
        api.listarReports(filtros),
        api.statsReports(),
        temFiltroAtivo ? api.statsReports(filtros) : Promise.resolve(null),
      ])
      setReports(data.reports || [])
      setStats(s)
      setStatsFiltrados(sFiltrado)
    } catch (e) {
      setErro(e.message || 'Erro ao carregar reports')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    carregar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtroStatus, filtroCategoria, filtroSeveridade, apenasAbertos])

  const onReportAtualizado = (reportAtualizado) => {
    setReports((prev) =>
      prev.map((r) => (r.id === reportAtualizado.id ? { ...r, ...reportAtualizado } : r)),
    )
    const filtros = montarFiltrosApi()
    Promise.all([
      api.statsReports(),
      temFiltroAtivo ? api.statsReports(filtros) : Promise.resolve(null),
    ])
      .then(([s, sFiltrado]) => {
        setStats(s)
        setStatsFiltrados(sFiltrado)
      })
      .catch(() => {})
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Flag className="text-inforrel-primary" size={22} />
          <h1 className="text-xl font-semibold text-inforrel-primary">
            Triagem de Reports
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={carregar}
            className="text-sm text-gray-600 hover:text-inforrel-primary flex items-center gap-1"
          >
            <RefreshCw size={14} /> Atualizar
          </button>
          {onVoltar && (
            <button
              onClick={onVoltar}
              className="text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-1.5 rounded"
            >
              ← Voltar ao chat
            </button>
          )}
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 mb-4">
          <StatCard
            label="Total"
            valor={stats.total}
            valorFiltrado={statsFiltrados?.total}
            temFiltro={temFiltroAtivo}
            cor="bg-inforrel-primary text-white"
          />
          <StatCard
            label="Abertos"
            valor={stats.por_status?.aberto}
            valorFiltrado={statsFiltrados?.por_status?.aberto}
            temFiltro={temFiltroAtivo}
            cor="bg-yellow-100 text-yellow-800"
          />
          <StatCard
            label="Em análise"
            valor={stats.por_status?.em_analise}
            valorFiltrado={statsFiltrados?.por_status?.em_analise}
            temFiltro={temFiltroAtivo}
            cor="bg-blue-100 text-blue-800"
          />
          <StatCard
            label="Aguardando fix"
            valor={stats.por_status?.aguardando_fix}
            valorFiltrado={statsFiltrados?.por_status?.aguardando_fix}
            temFiltro={temFiltroAtivo}
            cor="bg-purple-100 text-purple-800"
          />
          <StatCard
            label="Resolvidos"
            valor={stats.por_status?.resolvido}
            valorFiltrado={statsFiltrados?.por_status?.resolvido}
            temFiltro={temFiltroAtivo}
            cor="bg-green-100 text-green-800"
          />
          <StatCard
            label="Descartados"
            valor={stats.por_status?.descartado}
            valorFiltrado={statsFiltrados?.por_status?.descartado}
            temFiltro={temFiltroAtivo}
            cor="bg-gray-200 text-gray-600"
          />
        </div>
      )}

      {/* Filtros */}
      <div className="bg-white rounded-lg border border-gray-200 p-3 mb-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
          <div>
            <label className="text-xs text-gray-500 uppercase tracking-wide">Status</label>
            <select
              value={filtroStatus}
              onChange={(e) => setFiltroStatus(e.target.value)}
              className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm mt-0.5"
            >
              <option value="">Todos</option>
              {STATUS.map((s) => (
                <option key={s.valor} value={s.valor}>{s.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 uppercase tracking-wide">Categoria</label>
            <select
              value={filtroCategoria}
              onChange={(e) => setFiltroCategoria(e.target.value)}
              className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm mt-0.5"
            >
              <option value="">Todas</option>
              {CATEGORIAS.map((c) => (
                <option key={c.valor} value={c.valor}>{c.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 uppercase tracking-wide">Severidade</label>
            <select
              value={filtroSeveridade}
              onChange={(e) => setFiltroSeveridade(e.target.value)}
              className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm mt-0.5"
            >
              <option value="">Todas</option>
              {SEVERIDADES.map((s) => (
                <option key={s.valor} value={s.valor}>{s.label}</option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
              <input
                type="checkbox"
                checked={apenasAbertos}
                onChange={(e) => setApenasAbertos(e.target.checked)}
                disabled={!!filtroStatus}
              />
              Apenas não-finalizados
            </label>
          </div>
        </div>
      </div>

      {/* Erro */}
      {erro && (
        <div className="mb-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded p-3 flex items-center gap-2">
          <AlertTriangle size={16} /> {erro}
        </div>
      )}

      {/* Lista */}
      {loading ? (
        <div className="text-center py-12 text-gray-500">
          <Loader2 size={24} className="animate-spin mx-auto mb-2" />
          Carregando reports...
        </div>
      ) : reports.length === 0 ? (
        <div className="text-center py-12 text-gray-500 bg-white rounded-lg border border-gray-200">
          Nenhum report encontrado com os filtros atuais.
        </div>
      ) : (
        <div className="space-y-2">
          {reports.map((r) => (
            <button
              key={r.id}
              onClick={() => setSelecionado(r)}
              className="w-full text-left bg-white hover:bg-gray-50 border border-gray-200 rounded-lg p-3 transition"
            >
              <div className="flex items-center justify-between mb-1 flex-wrap gap-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-semibold text-inforrel-primary">
                    #{r.id}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${corStatus(r.status)}`}>
                    {labelStatus(r.status)}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${corSeveridade(r.severidade)}`}>
                    {labelSeveridade(r.severidade)}
                  </span>
                  <span className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded-full">
                    {labelCategoria(r.categoria)}
                  </span>
                </div>
                <span className="text-xs text-gray-500">
                  {formatDatetimeBRT(r.created_at)}
                </span>
              </div>
              <p className="text-sm text-gray-800 line-clamp-2 mb-1.5">{r.descricao}</p>
              {r.mensagem && (
                <div className="text-xs text-gray-600 bg-gray-50 rounded px-2 py-1 border-l-2 border-inforrel-secondary">
                  <span className="text-gray-500">💬 {r.mensagem.telefone}:</span>{' '}
                  <span className="italic">"{r.mensagem.conteudo}"</span>
                </div>
              )}
              {r.processamento && (
                <div className="flex gap-3 mt-1 text-xs text-gray-500">
                  {r.processamento.intencao && (
                    <span>
                      intenção: <code className="font-mono">{r.processamento.intencao}</code>
                    </span>
                  )}
                  {r.processamento.template_usado && (
                    <span>
                      template: <code className="font-mono">{r.processamento.template_usado}</code>
                    </span>
                  )}
                </div>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Modal de detalhe */}
      {selecionado && (
        <ReportDetalhe
          reportId={selecionado.id}
          onClose={() => setSelecionado(null)}
          onAtualizado={onReportAtualizado}
        />
      )}
    </div>
  )
}

export default ReportsPage
