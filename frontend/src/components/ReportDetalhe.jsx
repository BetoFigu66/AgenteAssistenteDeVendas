import { useEffect, useState } from 'react'
import { Loader2, Save, AlertTriangle, CheckCircle2, MessageCircle } from 'lucide-react'
import { api } from '../services/api'
import DetalheModal from './DetalheModal'
import { formatDatetimeBRT, formatTimeBRT } from '../utils/datetime'
import {
  CATEGORIAS,
  SEVERIDADES,
  STATUS,
  corStatus,
  corSeveridade,
  labelCategoria,
  labelStatus,
  labelSeveridade,
} from '../constants/reports'

function ReportDetalhe({ reportId, onClose, onAtualizado }) {
  const [ctx, setCtx] = useState(null)
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState(null)

  // Form
  const [status, setStatus] = useState('aberto')
  const [categoria, setCategoria] = useState('outro')
  const [severidade, setSeveridade] = useState('media')
  const [resolucao, setResolucao] = useState('')
  const [resolvidoPor, setResolvidoPor] = useState('')
  const [salvando, setSalvando] = useState(false)
  const [erroSave, setErroSave] = useState(null)
  const [sucessoSave, setSucessoSave] = useState(false)

  useEffect(() => {
    let cancelado = false
    setLoading(true)
    api
      .obterContextoReport(reportId)
      .then((data) => {
        if (cancelado) return
        setCtx(data)
        const r = data.report
        setStatus(r.status || 'aberto')
        setCategoria(r.categoria || 'outro')
        setSeveridade(r.severidade || 'media')
        setResolucao(r.resolucao || '')
        setResolvidoPor(r.resolvido_por || '')
      })
      .catch((e) => !cancelado && setErro(e.message))
      .finally(() => !cancelado && setLoading(false))
    return () => {
      cancelado = true
    }
  }, [reportId])

  const salvar = async () => {
    setSalvando(true)
    setErroSave(null)
    setSucessoSave(false)
    try {
      const atualizado = await api.atualizarReport(reportId, {
        status,
        categoria,
        severidade,
        resolucao: resolucao.trim() || null,
        resolvido_por: resolvidoPor.trim() || null,
      })
      setCtx((prev) => (prev ? { ...prev, report: atualizado } : prev))
      setSucessoSave(true)
      setTimeout(() => setSucessoSave(false), 2500)
      onAtualizado?.(atualizado)
    } catch (e) {
      setErroSave(e.message || 'Falha ao salvar')
    } finally {
      setSalvando(false)
    }
  }

  const report = ctx?.report
  const proc = ctx?.processamento
  const msgs = ctx?.contexto_mensagens || []
  const msgReportadaId = proc?.id ? msgs.find((m) => m.processamento_id === proc.id)?.id : null

  return (
    <DetalheModal
      titulo={`Report #${reportId}${report?.status ? ` — ${labelStatus(report.status)}` : ''}`}
      onClose={onClose}
    >
      {loading ? (
        <div className="text-center py-8 text-gray-500">
          <Loader2 size={24} className="animate-spin mx-auto mb-2" /> Carregando...
        </div>
      ) : erro ? (
        <p className="text-red-600 text-sm">{erro}</p>
      ) : !report ? null : (
        <div className="space-y-5">
          {/* Descrição original */}
          <div>
            <h3 className="text-sm font-semibold text-inforrel-primary mb-1">Descrição</h3>
            <p className="text-sm text-gray-800 whitespace-pre-wrap bg-yellow-50 border-l-4 border-inforrel-accent rounded p-2.5">
              {report.descricao}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Criado em {formatDatetimeBRT(report.created_at)}
              {report.autor && ` — por ${report.autor}`}
            </p>
          </div>

          {/* Contexto da conversa */}
          {msgs.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-inforrel-primary mb-2 flex items-center gap-1.5">
                <MessageCircle size={14} /> Contexto da conversa
              </h3>
              <div className="space-y-1.5 bg-gray-50 rounded p-2.5 max-h-72 overflow-y-auto">
                {msgs.map((m) => {
                  const isReportada = m.id === msgReportadaId
                  const isUser = m.origem === 'user'
                  return (
                    <div
                      key={m.id}
                      className={`text-sm px-2 py-1.5 rounded ${
                        isReportada
                          ? 'bg-inforrel-accent bg-opacity-20 border-2 border-inforrel-accent'
                          : isUser
                            ? 'bg-blue-50 border-l-2 border-inforrel-secondary'
                            : 'bg-white border-l-2 border-inforrel-primary'
                      }`}
                    >
                      <div className="flex justify-between items-start">
                        <span className="text-xs font-medium text-gray-600">
                          {isUser ? '👤 Cliente' : '🤖 Assistente'}
                          {isReportada && ' 🚩 (mensagem reportada)'}
                        </span>
                        <span className="text-xs text-gray-400">
                          {m.timestamp &&
                            formatTimeBRT(m.timestamp)}
                        </span>
                      </div>
                      <p className="text-gray-800 mt-0.5">{m.conteudo}</p>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Processamento — resumo */}
          {proc && (
            <div>
              <h3 className="text-sm font-semibold text-inforrel-primary mb-2">
                Processamento #{proc.id}
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-sm bg-gray-50 rounded p-2.5">
                <div>
                  <span className="text-xs text-gray-500">Intenção</span>
                  <div className="font-mono">{proc.intencao || '—'}</div>
                </div>
                <div>
                  <span className="text-xs text-gray-500">Confiança</span>
                  <div>
                    {proc.confianca !== null && proc.confianca !== undefined
                      ? `${Math.round(proc.confianca * 100)}%`
                      : '—'}
                  </div>
                </div>
                <div>
                  <span className="text-xs text-gray-500">Origem</span>
                  <div>{proc.origem_classificacao || '—'}</div>
                </div>
                <div>
                  <span className="text-xs text-gray-500">Template</span>
                  <div className="font-mono text-xs">{proc.template_usado || '—'}</div>
                </div>
                <div>
                  <span className="text-xs text-gray-500">Status identif.</span>
                  <div>{proc.status_identificacao || '—'}</div>
                </div>
                <div>
                  <span className="text-xs text-gray-500">Duração</span>
                  <div>{proc.duracao_ms ? `${proc.duracao_ms}ms` : '—'}</div>
                </div>
              </div>
            </div>
          )}

          {/* Triagem / Resolução */}
          <div className="border-t pt-4">
            <h3 className="text-sm font-semibold text-inforrel-primary mb-2">Triagem</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-3">
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wide">Status</label>
                <select
                  value={status}
                  onChange={(e) => setStatus(e.target.value)}
                  className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm mt-0.5"
                >
                  {STATUS.map((s) => (
                    <option key={s.valor} value={s.valor}>{s.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wide">Categoria</label>
                <select
                  value={categoria}
                  onChange={(e) => setCategoria(e.target.value)}
                  className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm mt-0.5"
                >
                  {CATEGORIAS.map((c) => (
                    <option key={c.valor} value={c.valor}>{c.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wide">Severidade</label>
                <select
                  value={severidade}
                  onChange={(e) => setSeveridade(e.target.value)}
                  className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm mt-0.5"
                >
                  {SEVERIDADES.map((s) => (
                    <option key={s.valor} value={s.valor}>{s.label}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="mb-2">
              <label className="text-xs text-gray-500 uppercase tracking-wide">
                Resolução (o que foi feito)
              </label>
              <textarea
                value={resolucao}
                onChange={(e) => setResolucao(e.target.value)}
                rows={3}
                placeholder="Ex: adicionada regra para 'catracão' no classificador; ajustado template X..."
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm mt-0.5"
              />
            </div>
            <div className="mb-3">
              <label className="text-xs text-gray-500 uppercase tracking-wide">
                Resolvido por
              </label>
              <input
                type="text"
                value={resolvidoPor}
                onChange={(e) => setResolvidoPor(e.target.value)}
                placeholder="Seu nome"
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm mt-0.5"
              />
            </div>

            {erroSave && (
              <div className="text-xs text-red-600 flex items-center gap-1 mb-2">
                <AlertTriangle size={12} /> {erroSave}
              </div>
            )}
            {sucessoSave && (
              <div className="text-xs text-green-600 flex items-center gap-1 mb-2">
                <CheckCircle2 size={12} /> Salvo com sucesso
              </div>
            )}

            <div className="flex justify-end">
              <button
                onClick={salvar}
                disabled={salvando}
                className="btn-primary text-sm px-4 py-1.5 rounded flex items-center gap-1.5 disabled:opacity-50"
              >
                {salvando ? (
                  <>
                    <Loader2 size={14} className="animate-spin" /> Salvando...
                  </>
                ) : (
                  <>
                    <Save size={14} /> Salvar alterações
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </DetalheModal>
  )
}

export default ReportDetalhe
