import { useEffect, useState } from 'react'
import { AlertTriangle, CheckCircle2, Flag, Loader2 } from 'lucide-react'
import { api } from '../services/api'
import {
  CATEGORIAS,
  SEVERIDADES,
  corSeveridade,
  corStatus,
  labelCategoria,
  labelStatus,
  labelSeveridade,
} from '../constants/reports'

function Campo({ label, valor, mono }) {
  if (valor === null || valor === undefined || valor === '') return null
  return (
    <div className="flex flex-col">
      <span className="text-xs text-gray-500 uppercase tracking-wide">{label}</span>
      <span className={`text-sm text-gray-800 ${mono ? 'font-mono' : ''}`}>
        {String(valor)}
      </span>
    </div>
  )
}

function Secao({ titulo, children }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-inforrel-primary mb-2">{titulo}</h3>
      {children}
    </div>
  )
}

function ConfiancaBadge({ valor }) {
  if (valor === null || valor === undefined) return null
  const pct = Math.round(valor * 100)
  let cor = 'bg-red-100 text-red-700'
  if (pct >= 70) cor = 'bg-green-100 text-green-700'
  else if (pct >= 40) cor = 'bg-yellow-100 text-yellow-700'
  return (
    <span className={`inline-block text-xs px-2 py-0.5 rounded-full ${cor}`}>
      {pct}%
    </span>
  )
}

function EntidadesView({ entidades }) {
  if (!entidades) return <p className="text-sm text-gray-500 italic">Nenhuma entidade extraída</p>
  const grupos = [
    ['CNPJs', entidades.cnpjs],
    ['Nomes', entidades.nomes],
    ['Tipos de produto', entidades.tipos_produto],
    ['Quantidades', entidades.quantidades],
    ['Emails', entidades.emails],
  ]
  const temAlgo = grupos.some(([, v]) => v && v.length > 0)
  if (!temAlgo) return <p className="text-sm text-gray-500 italic">Nenhuma entidade extraída</p>
  return (
    <div className="space-y-1">
      {grupos.map(([titulo, valores]) =>
        valores && valores.length > 0 ? (
          <div key={titulo} className="flex gap-2 text-sm">
            <span className="text-gray-500 min-w-[110px]">{titulo}:</span>
            <span className="text-gray-800 font-mono">{JSON.stringify(valores)}</span>
          </div>
        ) : null,
      )}
    </div>
  )
}

function ReportsSection({ processamentoId, reportsIniciais }) {
  const [reports, setReports] = useState(reportsIniciais || [])
  const [descricao, setDescricao] = useState('')
  const [categoria, setCategoria] = useState('outro')
  const [severidade, setSeveridade] = useState('media')
  const [enviando, setEnviando] = useState(false)
  const [erroEnvio, setErroEnvio] = useState(null)
  const [sucesso, setSucesso] = useState(false)

  const handleEnviar = async (e) => {
    e.preventDefault()
    if (!descricao.trim() || enviando) return
    setEnviando(true)
    setErroEnvio(null)
    setSucesso(false)
    try {
      const novo = await api.criarReportProblema(processamentoId, {
        descricao: descricao.trim(),
        categoria,
        severidade,
      })
      setReports([novo, ...reports])
      setDescricao('')
      setCategoria('outro')
      setSeveridade('media')
      setSucesso(true)
      setTimeout(() => setSucesso(false), 2500)
    } catch (err) {
      setErroEnvio(err.message || 'Falha ao registrar report')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div>
      <h3 className="text-sm font-semibold text-inforrel-primary mb-2 flex items-center gap-1.5">
        <Flag size={14} /> Reportar problema
      </h3>

      <form onSubmit={handleEnviar} className="space-y-2 mb-4">
        <textarea
          value={descricao}
          onChange={(e) => setDescricao(e.target.value)}
          placeholder="Descreva o que deu errado neste processamento (intenção incorreta, resposta inadequada, CNPJ não reconhecido, etc.)"
          rows={3}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:border-inforrel-primary"
          disabled={enviando}
        />
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs text-gray-500 uppercase tracking-wide">Categoria</label>
            <select
              value={categoria}
              onChange={(e) => setCategoria(e.target.value)}
              disabled={enviando}
              className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm mt-0.5"
            >
              {CATEGORIAS.map((c) => (
                <option key={c.valor} value={c.valor}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 uppercase tracking-wide">Severidade</label>
            <select
              value={severidade}
              onChange={(e) => setSeveridade(e.target.value)}
              disabled={enviando}
              className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm mt-0.5"
            >
              {SEVERIDADES.map((s) => (
                <option key={s.valor} value={s.valor}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        {erroEnvio && (
          <div className="text-xs text-red-600 flex items-center gap-1">
            <AlertTriangle size={12} /> {erroEnvio}
          </div>
        )}
        {sucesso && (
          <div className="text-xs text-green-600 flex items-center gap-1">
            <CheckCircle2 size={12} /> Report registrado com sucesso
          </div>
        )}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={!descricao.trim() || enviando}
            className="btn-primary text-sm px-4 py-1.5 rounded flex items-center gap-1.5 disabled:opacity-50"
          >
            {enviando ? (
              <>
                <Loader2 size={14} className="animate-spin" /> Enviando...
              </>
            ) : (
              <>
                <Flag size={14} /> Registrar report
              </>
            )}
          </button>
        </div>
      </form>

      {reports.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">
            Histórico de reports ({reports.length})
          </h4>
          <ul className="space-y-2">
            {reports.map((r) => (
              <li
                key={r.id}
                className="border-l-4 border-inforrel-accent bg-yellow-50 rounded p-2.5 text-sm"
              >
                <div className="flex items-center justify-between mb-1 flex-wrap gap-1">
                  <span className="text-xs text-gray-500">
                    #{r.id} — {new Date(r.created_at).toLocaleString('pt-BR')}
                  </span>
                  <div className="flex gap-1 flex-wrap">
                    {r.categoria && (
                      <span className="text-xs bg-white border border-gray-300 text-gray-700 px-2 py-0.5 rounded-full">
                        {labelCategoria(r.categoria)}
                      </span>
                    )}
                    {r.severidade && (
                      <span className={`text-xs px-2 py-0.5 rounded-full ${corSeveridade(r.severidade)}`}>
                        {labelSeveridade(r.severidade)}
                      </span>
                    )}
                    {r.status && (
                      <span className={`text-xs px-2 py-0.5 rounded-full ${corStatus(r.status)}`}>
                        {labelStatus(r.status)}
                      </span>
                    )}
                  </div>
                </div>
                <p className="text-gray-800 whitespace-pre-wrap">{r.descricao}</p>
                {r.resolucao && (
                  <p className="mt-1.5 text-xs text-gray-600 border-t border-yellow-200 pt-1.5">
                    <strong>Resolução:</strong> {r.resolucao}
                    {r.resolvido_por && ` — por ${r.resolvido_por}`}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}


function ProcessamentoDetalhes({ processamentoId }) {
  const [proc, setProc] = useState(null)
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState(null)
  const [mostrarRaw, setMostrarRaw] = useState(false)

  useEffect(() => {
    let cancelado = false
    setLoading(true)
    api
      .obterProcessamento(processamentoId)
      .then((data) => {
        if (!cancelado) setProc(data)
      })
      .catch((e) => {
        if (!cancelado) setErro(e.message)
      })
      .finally(() => {
        if (!cancelado) setLoading(false)
      })
    return () => {
      cancelado = true
    }
  }, [processamentoId])

  if (loading) return <p className="text-gray-500 text-sm">Carregando...</p>
  if (erro) return <p className="text-red-600 text-sm">{erro}</p>
  if (!proc) return null

  return (
    <div className="space-y-5">
      {/* Classificação */}
      <Secao titulo="Classificação">
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col">
            <span className="text-xs text-gray-500 uppercase tracking-wide">Intenção</span>
            <span className="text-sm text-gray-800 font-mono flex items-center gap-2">
              {proc.intencao}
              <ConfiancaBadge valor={proc.confianca} />
            </span>
          </div>
          <Campo label="Origem" valor={proc.origem_classificacao} />
        </div>
      </Secao>

      {/* Entidades */}
      <Secao titulo="Entidades extraídas">
        <EntidadesView entidades={proc.entidades} />
      </Secao>

      {/* Identificação */}
      <Secao titulo="Identificação no momento">
        <div className="grid grid-cols-2 gap-3">
          <Campo label="Status" valor={proc.status_identificacao} />
          <Campo label="Contato ID" valor={proc.contato_id_identificado} />
          <Campo label="Empresa ID" valor={proc.empresa_id_identificada} />
          <Campo label="Atendimento ativo" valor={proc.atendimento_id_ativa ?? proc.negociacao_id_ativa} />
        </div>
      </Secao>

      {/* Resposta */}
      <Secao titulo="Decisão de resposta">
        <div className="grid grid-cols-2 gap-3">
          <Campo label="Template usado" valor={proc.template_usado} mono />
          <Campo
            label="Personalizado via LLM"
            valor={proc.personalizado_via_llm ? 'sim' : 'não'}
          />
        </div>
      </Secao>

      {/* LLM */}
      {(proc.llm_provider || proc.llm_latencia_ms || proc.llm_tokens_input) && (
        <Secao titulo="LLM">
          <div className="grid grid-cols-2 gap-3">
            <Campo label="Provider" valor={proc.llm_provider} />
            <Campo label="Modelo" valor={proc.llm_modelo} mono />
            <Campo label="Latência (ms)" valor={proc.llm_latencia_ms} />
            <Campo label="Tokens entrada" valor={proc.llm_tokens_input} />
            <Campo label="Tokens saída" valor={proc.llm_tokens_output} />
          </div>
        </Secao>
      )}

      {/* Controle */}
      <Secao titulo="Controle">
        <div className="grid grid-cols-2 gap-3">
          <Campo label="Duração total (ms)" valor={proc.duracao_ms} />
          <Campo label="Registrado em" valor={proc.created_at} />
        </div>
        {proc.erro && (
          <div className="mt-2 bg-red-50 border border-red-200 text-red-700 text-sm rounded p-2">
            <strong>Erro:</strong> {proc.erro}
          </div>
        )}
      </Secao>

      {/* Raw LLM */}
      {proc.llm_raw_resposta && (
        <Secao titulo="Resposta bruta da LLM">
          <button
            onClick={() => setMostrarRaw(!mostrarRaw)}
            className="text-xs text-inforrel-secondary hover:underline mb-1"
          >
            {mostrarRaw ? 'Ocultar' : 'Mostrar'} JSON bruto
          </button>
          {mostrarRaw && (
            <pre className="bg-gray-900 text-green-200 text-xs p-3 rounded overflow-x-auto">
              {JSON.stringify(proc.llm_raw_resposta, null, 2)}
            </pre>
          )}
        </Secao>
      )}

      {/* Reports de problema */}
      <div className="pt-4 border-t border-gray-200">
        <ReportsSection
          processamentoId={processamentoId}
          reportsIniciais={proc.reports || []}
        />
      </div>
    </div>
  )
}

export default ProcessamentoDetalhes
