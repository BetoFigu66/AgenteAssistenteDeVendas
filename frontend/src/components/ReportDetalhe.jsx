import { useEffect, useState } from 'react'
import {
  Loader2,
  Save,
  AlertTriangle,
  CheckCircle2,
  MessageCircle,
  Download,
  Brain,
  ExternalLink,
  BookOpen,
} from 'lucide-react'
import { api } from '../services/api'
import DetalheModal from './DetalheModal'
import ProcessamentoDetalhes, { RagTrechosView, ScoreBadge } from './ProcessamentoDetalhes'
import { formatDatetimeBRT, formatTimeBRT } from '../utils/datetime'
import { useAuth } from '../context/AuthContext'
import { CONTEXTOS_QA } from '../constants/qa'
import {
  CATEGORIAS,
  SEVERIDADES,
  STATUS,
  corStatus,
  corSeveridade,
  labelCategoria,
  labelStatus,
  labelSeveridade,
  statusPermitidos,
} from '../constants/reports'

function ReportDetalhe({ reportId, onClose, onAtualizado, onAbrirAtendimento }) {
  const { usuario } = useAuth()
  const [ctx, setCtx] = useState(null)
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState(null)

  // Criar par Q&A a partir deste report (REQ-013.7, Fase 9)
  const [mostrarCriarQA, setMostrarCriarQA] = useState(false)
  const [qaPergunta, setQaPergunta] = useState('')
  const [qaResposta, setQaResposta] = useState('')
  const [qaContexto, setQaContexto] = useState('')
  const [criandoQA, setCriandoQA] = useState(false)
  const [erroQA, setErroQA] = useState(null)
  const [sucessoQA, setSucessoQA] = useState(false)

  // Form
  const [status, setStatus] = useState('aberto')
  const [categoria, setCategoria] = useState('outro')
  const [severidade, setSeveridade] = useState('media')
  const [resolucao, setResolucao] = useState('')
  const [salvando, setSalvando] = useState(false)
  const [erroSave, setErroSave] = useState(null)
  const [sucessoSave, setSucessoSave] = useState(false)
  const [baixandoYaml, setBaixandoYaml] = useState(false)
  const [erroYaml, setErroYaml] = useState(null)
  const [mostrarProcessamento, setMostrarProcessamento] = useState(false)

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

  const baixarYaml = async () => {
    setBaixandoYaml(true)
    setErroYaml(null)
    try {
      await api.baixarPacoteAnaliseReport(reportId)
    } catch (e) {
      setErroYaml(e.message || 'Falha ao baixar YAML')
    } finally {
      setBaixandoYaml(false)
    }
  }

  const report = ctx?.report
  const proc = ctx?.processamento
  const msgs = ctx?.contexto_mensagens || []
  const telefone =
    ctx?.telefone || msgs.find((m) => m.telefone)?.telefone || null
  const msgReportadaId = proc?.id ? msgs.find((m) => m.processamento_id === proc.id)?.id : null

  const abrirCriarQA = () => {
    const idx = msgReportadaId ? msgs.findIndex((m) => m.id === msgReportadaId) : -1
    const perguntaCliente =
      idx >= 0
        ? msgs.slice(0, idx).reverse().find((m) => m.origem === 'user')?.conteudo
        : msgs.find((m) => m.origem === 'user')?.conteudo
    setQaPergunta(perguntaCliente || '')
    setQaResposta('')
    setQaContexto('')
    setErroQA(null)
    setSucessoQA(false)
    setMostrarCriarQA(true)
  }

  const criarParQADoReport = async () => {
    if (!qaPergunta.trim() || !qaResposta.trim() || criandoQA) return
    setCriandoQA(true)
    setErroQA(null)
    try {
      await api.criarParQA({
        // REQ-013.3/013.7 (Fase 9): id_externo rastreável até o report de origem.
        id_externo: `report:${reportId}`,
        pergunta: qaPergunta.trim(),
        resposta: qaResposta.trim(),
        contexto: qaContexto || null,
        criado_por: usuario?.nome || null,
      })
      setSucessoQA(true)
      setMostrarCriarQA(false)
    } catch (e) {
      setErroQA(e.message || 'Falha ao criar par Q&A')
    } finally {
      setCriandoQA(false)
    }
  }

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

          {/* Navegação real report → atendimento/processamento */}
          {(proc || ctx?.atendimento_id) && (
            <div className="flex flex-wrap gap-2">
              {proc && (
                <button
                  type="button"
                  onClick={() => setMostrarProcessamento(true)}
                  className="text-xs bg-white border border-gray-300 hover:border-inforrel-primary text-gray-700 hover:text-inforrel-primary px-2.5 py-1 rounded-full flex items-center gap-1"
                >
                  <Brain size={12} /> Ver processamento completo
                </button>
              )}
              {ctx?.atendimento_id && onAbrirAtendimento && (
                <button
                  type="button"
                  onClick={() => {
                    onAbrirAtendimento(ctx.atendimento_id)
                    onClose?.()
                  }}
                  className="text-xs bg-white border border-gray-300 hover:border-inforrel-primary text-gray-700 hover:text-inforrel-primary px-2.5 py-1 rounded-full flex items-center gap-1"
                >
                  <ExternalLink size={12} /> Ver atendimento #{ctx.atendimento_id}
                </button>
              )}
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

          {/* RAG/Q&A — trechos recuperados na resposta reportada (REQ-003.5/003.14) */}
          {proc?.rag_utilizada && (
            <div>
              <h3 className="text-sm font-semibold text-inforrel-primary mb-2 flex items-center gap-2">
                Base de conhecimento (RAG/Q&A)
                <ScoreBadge valor={proc.rag_score_maximo} />
              </h3>
              <RagTrechosView trechos={proc.rag_trechos} />
            </div>
          )}

          {/* Criar par Q&A a partir deste report (REQ-013.7) */}
          <div className="border rounded-lg p-3 bg-slate-50">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
              <div>
                <h3 className="text-sm font-semibold text-inforrel-primary flex items-center gap-1.5">
                  <BookOpen size={14} /> Criar par Q&A a partir deste report
                </h3>
                <p className="text-xs text-gray-600 mt-0.5">
                  Salva um rascunho na Base Q&A (sem embedding ainda) rastreável até este report.
                </p>
              </div>
              {!mostrarCriarQA && (
                <button
                  type="button"
                  onClick={abrirCriarQA}
                  className="btn-secondary text-sm px-4 py-1.5 rounded flex items-center gap-1.5 shrink-0"
                >
                  <BookOpen size={14} /> Criar par Q&A
                </button>
              )}
            </div>

            {sucessoQA && !mostrarCriarQA && (
              <div className="text-xs text-green-600 flex items-center gap-1 mt-2">
                <CheckCircle2 size={12} /> Rascunho Q&A criado — revise na Base Q&A.
              </div>
            )}

            {mostrarCriarQA && (
              <div className="mt-3 space-y-2">
                <div>
                  <label className="text-xs text-gray-500 uppercase tracking-wide">Pergunta</label>
                  <textarea
                    value={qaPergunta}
                    onChange={(e) => setQaPergunta(e.target.value)}
                    rows={2}
                    placeholder="Como o cliente costuma perguntar..."
                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm mt-0.5"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500 uppercase tracking-wide">Resposta</label>
                  <textarea
                    value={qaResposta}
                    onChange={(e) => setQaResposta(e.target.value)}
                    rows={3}
                    placeholder="Resposta ideal para esta pergunta..."
                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm mt-0.5"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500 uppercase tracking-wide">Contexto</label>
                  <select
                    value={qaContexto}
                    onChange={(e) => setQaContexto(e.target.value)}
                    className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm mt-0.5"
                  >
                    {CONTEXTOS_QA.map((c) => (
                      <option key={c.value} value={c.value}>{c.label}</option>
                    ))}
                  </select>
                </div>
                {erroQA && (
                  <div className="text-xs text-red-600 flex items-center gap-1">
                    <AlertTriangle size={12} /> {erroQA}
                  </div>
                )}
                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setMostrarCriarQA(false)}
                    className="text-sm text-gray-600 hover:text-gray-800 px-3 py-1.5"
                  >
                    Cancelar
                  </button>
                  <button
                    type="button"
                    onClick={criarParQADoReport}
                    disabled={!qaPergunta.trim() || !qaResposta.trim() || criandoQA}
                    className="btn-primary text-sm px-4 py-1.5 rounded flex items-center gap-1.5 disabled:opacity-50"
                  >
                    {criandoQA ? (
                      <><Loader2 size={14} className="animate-spin" /> Salvando...</>
                    ) : (
                      <><BookOpen size={14} /> Salvar rascunho</>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="border rounded-lg p-3 bg-slate-50">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
              <div>
                <h3 className="text-sm font-semibold text-inforrel-primary">
                  Pacote para curador
                </h3>
                <p className="text-xs text-gray-600 mt-0.5">
                  Gera YAML com re-busca Q&A/RAG e sugestão de documentos para o{' '}
                  <span className="font-mono">[curador_conhecimento]</span>.
                </p>
                {telefone && (
                  <p className="text-xs text-gray-600 mt-1">
                    Telefone:{' '}
                    <span className="font-mono text-gray-800">{telefone}</span>
                  </p>
                )}
              </div>
              <button
                type="button"
                onClick={baixarYaml}
                disabled={baixandoYaml}
                className="btn-secondary text-sm px-4 py-1.5 rounded flex items-center gap-1.5 disabled:opacity-50 shrink-0"
              >
                {baixandoYaml ? (
                  <>
                    <Loader2 size={14} className="animate-spin" /> Gerando...
                  </>
                ) : (
                  <>
                    <Download size={14} /> Download YAML
                  </>
                )}
              </button>
            </div>
            {erroYaml && (
              <div className="text-xs text-red-600 flex items-center gap-1 mt-2">
                <AlertTriangle size={12} /> {erroYaml}
              </div>
            )}
          </div>

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
                  {STATUS.filter((s) => statusPermitidos(report.status).includes(s.valor)).map((s) => (
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
            {ctx?.report?.resolvido_por && (
              <p className="text-xs text-gray-500 mb-3">
                Resolvido por <span className="font-medium">{ctx.report.resolvido_por}</span>
                {ctx.report.resolvido_em && ` em ${formatDatetimeBRT(ctx.report.resolvido_em)}`}
              </p>
            )}

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

      {mostrarProcessamento && proc && (
        <DetalheModal
          titulo={`Raciocínio do cérebro — processamento #${proc.id}`}
          onClose={() => setMostrarProcessamento(false)}
        >
          <ProcessamentoDetalhes processamentoId={proc.id} />
        </DetalheModal>
      )}
    </DetalheModal>
  )
}

export default ReportDetalhe
