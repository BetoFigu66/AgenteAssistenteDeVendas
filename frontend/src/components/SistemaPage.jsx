import { useState, useEffect, useCallback } from 'react'
import { RefreshCw, Server, Lock, AlertTriangle, Zap } from 'lucide-react'
import { api } from '../services/api'
import BotaoAjuda from './BotaoAjuda'
import { formatDatetimeBRT } from '../utils/datetime'

// Situação geral do LLM (`services/diagnostico_sistema.py::status_llm`).
const ESTILO_SITUACAO = {
  funcional: { rotulo: 'Funcional', classe: 'bg-green-100 text-green-800 border-green-300' },
  erro: { rotulo: 'Com erro', classe: 'bg-red-100 text-red-800 border-red-300' },
  desligado: { rotulo: 'Desligado', classe: 'bg-gray-100 text-gray-700 border-gray-300' },
}

// Situação de cada ponto registrado em `comparacoes_llm`.
const ROTULO_USO = {
  ok: { rotulo: 'LLM respondeu', classe: 'text-green-700' },
  erro: { rotulo: 'LLM com erro', classe: 'text-red-700' },
  vazio: { rotulo: 'LLM vazio', classe: 'text-amber-700' },
  indisponivel: { rotulo: 'Sem LLM', classe: 'text-gray-600' },
}

const ROTULO_ETAPA = {
  classificacao: 'Classificação',
  resposta_rag: 'Resposta da base',
  personalizacao: 'Personalização',
}

function StatusLLM({ status, testando, onTestar }) {
  if (!status) return null
  const estilo = ESTILO_SITUACAO[status.situacao] || ESTILO_SITUACAO.desligado
  const { teste, uso_recente: uso } = status
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-4">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div className="flex items-center gap-3">
          <Zap size={18} className="text-inforrel-primary" />
          <h3 className="font-semibold text-inforrel-primary">LLM</h3>
          <span className={`px-2 py-0.5 text-xs font-medium rounded border ${estilo.classe}`}>{estilo.rotulo}</span>
        </div>
        <button
          onClick={onTestar}
          disabled={testando}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-inforrel-primary text-inforrel-primary rounded hover:bg-inforrel-primary hover:text-white transition disabled:opacity-50"
        >
          <RefreshCw size={14} className={testando ? 'animate-spin' : ''} /> Testar agora
        </button>
      </div>
      <p className="text-sm text-gray-700 mb-3">{status.resumo}</p>

      <dl className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-x-6 gap-y-2 text-sm">
        <div><dt className="text-gray-500">Provedor</dt><dd className="font-mono">{status.provedor}</dd></div>
        <div><dt className="text-gray-500">Modelo</dt><dd className="font-mono break-all">{status.modelo}</dd></div>
        {status.endereco && (
          <div><dt className="text-gray-500">Endereço</dt><dd className="font-mono break-all">{status.endereco}</dd></div>
        )}
        <div><dt className="text-gray-500">Chave</dt><dd>{status.chave_definida ? 'definida' : 'não definida'}</dd></div>
        <div>
          <dt className="text-gray-500">Carregado no processador</dt>
          <dd>{status.carregado_no_processador ? 'sim' : 'não'}</dd>
        </div>
      </dl>

      {teste && (
        <div className={`mt-3 p-3 rounded text-sm ${teste.ok ? 'bg-green-50' : 'bg-red-50'}`}>
          <div className="font-medium">
            Teste ao vivo: {teste.ok ? 'respondeu' : 'falhou'}
            {teste.latencia_ms != null && <span className="font-normal text-gray-600"> · {teste.latencia_ms} ms</span>}
            {teste.testado_em && (
              <span className="font-normal text-gray-600">
                {' '}· {formatDatetimeBRT(teste.testado_em)}{teste.em_cache ? ' (resultado guardado, até 1 min)' : ''}
              </span>
            )}
          </div>
          {teste.erro && <div className="mt-1 font-mono text-xs text-red-800 break-all">{teste.erro}</div>}
        </div>
      )}

      {uso && (
        <div className="mt-3 text-sm text-gray-700">
          <span className="text-gray-500">Uso real nas últimas {uso.horas}h: </span>
          {Object.keys(uso.por_situacao).length === 0
            ? 'nenhum ponto registrado'
            : Object.entries(uso.por_situacao)
                .map(([situacao, n]) => `${n} ${(ROTULO_USO[situacao]?.rotulo || situacao).toLowerCase()}`)
                .join(' · ')}
          <span className="text-gray-500">. Última resposta do LLM: </span>
          {uso.ultimo_ok_em ? formatDatetimeBRT(uso.ultimo_ok_em) : 'nenhuma registrada'}
        </div>
      )}
    </div>
  )
}

function Comparacoes({ itens, situacao, onSituacao }) {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-4">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <h3 className="font-semibold text-inforrel-primary">Sem LLM × com LLM (últimos registros)</h3>
        <select
          value={situacao}
          onChange={(e) => onSituacao(e.target.value)}
          className="text-sm border border-gray-300 rounded px-2 py-1"
        >
          <option value="">Todas as situações</option>
          {Object.entries(ROTULO_USO).map(([valor, { rotulo }]) => (
            <option key={valor} value={valor}>{rotulo}</option>
          ))}
        </select>
      </div>
      {itens.length === 0 ? (
        <p className="text-sm text-gray-500">Nenhum registro ainda. Cada mensagem em que o LLM foi (ou seria) usado aparece aqui.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b">
                <th className="py-2 pr-3 font-medium">Quando</th>
                <th className="py-2 pr-3 font-medium">Etapa</th>
                <th className="py-2 pr-3 font-medium">Mensagem do cliente</th>
                <th className="py-2 pr-3 font-medium">Sem LLM</th>
                <th className="py-2 pr-3 font-medium">Com LLM</th>
              </tr>
            </thead>
            <tbody>
              {itens.map((c) => {
                const uso = ROTULO_USO[c.situacao] || { rotulo: c.situacao, classe: '' }
                return (
                  <tr key={c.id} className="border-b last:border-0 align-top">
                    <td className="py-2 pr-3 whitespace-nowrap text-gray-600">
                      {formatDatetimeBRT(c.created_at)}
                      {c.atendimento_id && <div className="text-xs text-gray-400">Atendimento #{c.atendimento_id}</div>}
                    </td>
                    <td className="py-2 pr-3 whitespace-nowrap">
                      {ROTULO_ETAPA[c.etapa] || c.etapa}
                      <div className={`text-xs ${uso.classe}`}>{uso.rotulo}</div>
                    </td>
                    <td className="py-2 pr-3 max-w-xs whitespace-pre-wrap break-words">{c.mensagem_cliente}</td>
                    <td className="py-2 pr-3 max-w-xs whitespace-pre-wrap break-words">{c.sem_llm}</td>
                    <td className="py-2 pr-3 max-w-xs whitespace-pre-wrap break-words">
                      {c.com_llm || (c.erro ? (
                        <span className="font-mono text-xs text-red-700 break-all">{c.erro}</span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      ))}
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

function Configuracoes({ itens }) {
  const grupos = []
  itens.forEach((item) => {
    let grupo = grupos.find((g) => g.nome === item.grupo)
    if (!grupo) {
      grupo = { nome: item.grupo, itens: [] }
      grupos.push(grupo)
    }
    grupo.itens.push(item)
  })
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      <h3 className="font-semibold text-inforrel-primary mb-1">Configurações do servidor (.env)</h3>
      <p className="text-sm text-gray-500 mb-3">
        Só leitura. Chaves, tokens, usuários e senhas aparecem apenas como “definido” ou “não definido”.
      </p>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {grupos.map((grupo) => (
          <div key={grupo.nome}>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">{grupo.nome}</h4>
            <table className="w-full text-sm">
              <tbody>
                {grupo.itens.map((item) => (
                  <tr key={item.nome} className="border-b last:border-0 align-top">
                    <td className="py-1 pr-3 font-mono text-xs text-gray-700 break-all">{item.nome}</td>
                    <td className="py-1 pr-3 font-mono text-xs break-all">
                      <span className="inline-flex items-center gap-1">
                        {item.sensivel && <Lock size={12} className="text-gray-400" />}
                        {item.valor === null || item.valor === undefined ? <span className="text-gray-400">vazio</span> : String(item.valor)}
                      </span>
                      {item.aviso && (
                        <div className="flex items-center gap-1 text-amber-700 font-sans">
                          <AlertTriangle size={12} /> {item.aviso}
                        </div>
                      )}
                    </td>
                    <td className="py-1 text-xs text-gray-400 whitespace-nowrap">{item.origem}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>
    </div>
  )
}

function SistemaPage() {
  const [status, setStatus] = useState(null)
  const [configuracoes, setConfiguracoes] = useState([])
  const [comparacoes, setComparacoes] = useState([])
  const [situacao, setSituacao] = useState('')
  const [carregando, setCarregando] = useState(false)
  const [testando, setTestando] = useState(false)
  const [erro, setErro] = useState(null)

  const carregar = useCallback(async () => {
    setCarregando(true)
    setErro(null)
    try {
      const [cfg, st, comp] = await Promise.all([
        api.obterConfigSistema(),
        api.obterStatusLLM(),
        api.listarComparacoesLLM({ situacao }),
      ])
      setConfiguracoes(cfg.configuracoes || [])
      setStatus(st)
      setComparacoes(comp.comparacoes || [])
    } catch (e) {
      setErro('Erro ao carregar: ' + e.message)
    } finally {
      setCarregando(false)
    }
  }, [situacao])

  useEffect(() => {
    carregar()
  }, [carregar])

  const testar = async () => {
    setTestando(true)
    setErro(null)
    try {
      setStatus(await api.obterStatusLLM({ forcar: true }))
    } catch (e) {
      setErro('Erro ao testar o LLM: ' + e.message)
    } finally {
      setTestando(false)
    }
  }

  return (
    <div className="container mx-auto px-4 py-6 max-w-7xl">
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Server size={20} className="text-inforrel-primary" />
            <h2 className="text-lg font-semibold text-inforrel-primary">Sistema</h2>
            <BotaoAjuda contexto="sistema" />
          </div>
          <button
            onClick={carregar}
            disabled={carregando}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 hover:text-inforrel-primary transition disabled:opacity-50"
          >
            <RefreshCw size={14} className={carregando ? 'animate-spin' : ''} /> Atualizar
          </button>
        </div>
        {erro && <p className="mt-2 text-sm text-red-700">{erro}</p>}
      </div>

      <StatusLLM status={status} testando={testando} onTestar={testar} />
      <Comparacoes itens={comparacoes} situacao={situacao} onSituacao={setSituacao} />
      <Configuracoes itens={configuracoes} />
    </div>
  )
}

export default SistemaPage
