import { useState, useEffect, useCallback } from 'react'
import { HelpCircle, Search, RefreshCw, ChevronDown, ChevronRight } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import DetalheModal from './DetalheModal'
import { obterAjuda } from '../ajuda'
import { api } from '../services/api'

const TITULO_PADRAO = 'Detalhes desta funcionalidade'

/** Markdown com a tipografia do projeto. `max-w-none` porque `prose` limita a
 *  largura a 65ch, o que deixaria o texto mais estreito que o modal. */
function Markdown({ children }) {
  return (
    <div className="prose prose-sm max-w-none">
      <ReactMarkdown>{children}</ReactMarkdown>
    </div>
  )
}

/**
 * Botao de ajuda contextual da tela.
 *
 * Duas camadas de conteudo, complementares:
 *   1. FAQ (`/api/ajuda`) — responde pergunta pontual, editavel na aba Base de Ajuda.
 *   2. `src/ajuda/<contexto>.md` — explicacao completa da tela, versionada em git.
 *
 * O texto completo aparece aberto por padrao (era o comportamento antes do FAQ existir)
 * e se recolhe sozinho quando uma resposta chega, para nao competir com ela. Se a API
 * do FAQ estiver fora, o texto da tela continua funcionando: a busca degrada, a
 * documentacao nao.
 *
 * @param {string} contexto Identificador da tela (ex: 'reports', 'chat').
 * @param {string} [titulo] Titulo do modal e do tooltip.
 * @param {string} [className] Classes do botao — sobrescrever em fundo escuro.
 */
function BotaoAjuda({ contexto, titulo = TITULO_PADRAO, className = 'text-gray-400 hover:text-inforrel-primary transition' }) {
  const [aberto, setAberto] = useState(false)
  const [pergunta, setPergunta] = useState('')
  const [buscando, setBuscando] = useState(false)
  const [resultado, setResultado] = useState(null) // { encontrou, resultados[] }
  const [sugestoes, setSugestoes] = useState([])
  const [erroBusca, setErroBusca] = useState(null)
  const [mostrarTexto, setMostrarTexto] = useState(true)

  const texto = obterAjuda(contexto)

  const limpar = useCallback(() => {
    setPergunta('')
    setResultado(null)
    setErroBusca(null)
    setMostrarTexto(true)
  }, [])

  // Sugestoes ao abrir. Falha aqui e silenciosa: sem sugestoes o modal ainda serve.
  useEffect(() => {
    if (!aberto) return
    let cancelado = false
    api
      .sugestoesAjuda(contexto)
      .then((data) => !cancelado && setSugestoes(data.sugestoes || []))
      .catch(() => !cancelado && setSugestoes([]))
    return () => {
      cancelado = true
    }
  }, [aberto, contexto])

  const fechar = () => {
    setAberto(false)
    limpar()
  }

  const buscar = async (e) => {
    e?.preventDefault()
    const q = pergunta.trim()
    if (!q || buscando) return
    setBuscando(true)
    setErroBusca(null)
    try {
      const data = await api.perguntarAjuda(q, contexto)
      setResultado(data)
      // Achou: o texto completo sai da frente. Nao achou: continua aberto, porque
      // e onde a pessoa tem mais chance de encontrar o que procurava.
      setMostrarTexto(!data.encontrou)
    } catch (error) {
      setErroBusca(error.message)
      setResultado(null)
    } finally {
      setBuscando(false)
    }
  }

  /** Clique numa sugestao responde na hora: a resposta ja veio no payload.
   *  Nao registra consulta de proposito — senao as estatisticas de "mais
   *  perguntado" misturariam clique em atalho com pergunta digitada. */
  const usarSugestao = (s) => {
    setPergunta(s.pergunta)
    setResultado({ encontrou: true, resultados: [s] })
    setMostrarTexto(false)
    setErroBusca(null)
  }

  if (!texto) return null

  return (
    <>
      <button
        type="button"
        onClick={() => setAberto(true)}
        title={titulo}
        aria-label={titulo}
        className={className}
      >
        <HelpCircle size={16} />
      </button>

      {aberto && (
        <DetalheModal titulo={titulo} onClose={fechar}>
          <form onSubmit={buscar} className="flex gap-2">
            <div className="relative flex-1">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={pergunta}
                onChange={(e) => setPergunta(e.target.value)}
                placeholder="Pergunte algo sobre esta tela..."
                className="w-full rounded-lg border border-gray-300 py-2 pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-inforrel-secondary"
              />
            </div>
            <button
              type="submit"
              disabled={!pergunta.trim() || buscando}
              className="btn-primary text-sm disabled:opacity-50"
            >
              {buscando ? <RefreshCw size={16} className="animate-spin" /> : 'Buscar'}
            </button>
          </form>

          {erroBusca && (
            <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
              Busca indisponível ({erroBusca}). A explicação da tela continua abaixo.
            </p>
          )}

          {resultado?.encontrou && (
            <div className="mt-3 space-y-3">
              {resultado.resultados.map((r) => (
                <div
                  key={r.conteudo_id}
                  className="rounded-lg border-l-4 border-inforrel-secondary bg-blue-50/50 px-4 py-3"
                >
                  <p className="mb-1 text-xs font-semibold text-inforrel-primary">{r.pergunta}</p>
                  <Markdown>{r.resposta}</Markdown>
                </div>
              ))}
            </div>
          )}

          {resultado && !resultado.encontrou && (
            <p className="mt-3 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-xs text-gray-600">
              Não encontrei uma resposta para isso. Tente outras palavras, veja as sugestões
              abaixo ou procure na explicação completa da tela. Sua pergunta ficou registrada
              para virar conteúdo de ajuda.
            </p>
          )}

          {sugestoes.length > 0 && (
            <div className="mt-3">
              <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-gray-400">
                Perguntas frequentes
              </p>
              <div className="flex flex-wrap gap-1.5">
                {sugestoes.map((s) => (
                  <button
                    key={s.conteudo_id}
                    type="button"
                    onClick={() => usarSugestao(s)}
                    className="rounded-full border border-gray-200 bg-white px-2.5 py-1 text-xs text-gray-700 transition hover:border-inforrel-secondary hover:text-inforrel-primary"
                  >
                    {s.pergunta}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="mt-4 border-t pt-3">
            <button
              type="button"
              onClick={() => setMostrarTexto((v) => !v)}
              className="flex items-center gap-1 text-xs font-medium text-gray-500 transition hover:text-inforrel-primary"
            >
              {mostrarTexto ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              Explicação completa desta tela
            </button>
            {mostrarTexto && (
              <div className="mt-2">
                <Markdown>{texto}</Markdown>
              </div>
            )}
          </div>
        </DetalheModal>
      )}
    </>
  )
}

export default BotaoAjuda
