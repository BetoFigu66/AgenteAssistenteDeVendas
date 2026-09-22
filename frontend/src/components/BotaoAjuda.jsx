import { useState } from 'react'
import { HelpCircle } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import DetalheModal from './DetalheModal'
import { obterAjuda } from '../ajuda'

const TITULO_PADRAO = 'Detalhes desta funcionalidade'

/**
 * Botao de ajuda contextual: abre um modal com a explicacao da tela atual.
 *
 * O texto vem de `src/ajuda/<contexto>.md` (ver `src/ajuda/README.md`). Se nao
 * houver conteudo para o contexto nem fallback, o botao nao e renderizado.
 *
 * @param {string} contexto Identificador da tela (ex: 'reports', 'chat').
 * @param {string} [titulo] Titulo do modal e do tooltip.
 * @param {string} [className] Classes do botao — sobrescrever em fundo escuro.
 */
function BotaoAjuda({ contexto, titulo = TITULO_PADRAO, className = 'text-gray-400 hover:text-inforrel-primary transition' }) {
  const [aberto, setAberto] = useState(false)
  const texto = obterAjuda(contexto)

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
        <DetalheModal titulo={titulo} onClose={() => setAberto(false)}>
          {/* `max-w-none` e necessario: `prose` limita a largura a 65ch, o que
              deixaria o texto mais estreito que o modal. */}
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown>{texto}</ReactMarkdown>
          </div>
        </DetalheModal>
      )}
    </>
  )
}

export default BotaoAjuda
