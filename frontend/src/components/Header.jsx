import { useEffect, useState } from 'react'
import { Phone, Mail, LogOut, User, AlertTriangle } from 'lucide-react'
import { api } from '../services/api'
import { useAuth } from '../context/AuthContext'
import DetalheModal from './DetalheModal'

const ROTULO_MODO = {
  simulacao: 'Simulação',
  conversa_controlada: 'Conversa Controlada',
  execucao_normal: 'Execução Normal',
}

const CLASSES_MODO = {
  simulacao: 'bg-purple-100 text-purple-700 border-purple-300',
  conversa_controlada: 'bg-amber-100 text-amber-700 border-amber-300',
  execucao_normal: 'bg-green-100 text-green-700 border-green-300',
}

// REQ-011.18: janela dos indicadores apresentados na confirmação. Mesmo padrão do
// backend (`INDICADORES_EXECUCAO_DIAS_PADRAO`).
const DIAS_INDICADORES = 7

function formatarTaxa(taxa) {
  if (taxa === null || taxa === undefined) return null
  return `${Math.round(taxa * 100)}%`
}

function Indicador({ rotulo, valor, observacao }) {
  return (
    <div className="border border-gray-200 rounded p-2">
      <p className="text-xs text-gray-500">{rotulo}</p>
      <p className="text-lg font-semibold text-inforrel-primary">{valor}</p>
      {observacao && <p className="text-xs text-gray-500 mt-0.5">{observacao}</p>}
    </div>
  )
}

/**
 * REQ-011.18: promover para `execucao_normal` é o único sentido da troca de modo em
 * que o sistema passa a responder ao cliente sem decisão humana. Por isso a mudança
 * nessa direção pede confirmação explícita e mostra o histórico recente de
 * aprovações/reprovações. Voltar para um modo mais conservador não pede nada: é a
 * direção segura, e o próprio requisito só fala em confirmar a promoção.
 */
function ConfirmacaoExecucaoNormal({ indicadores, erro, canal, onCancelar, onConfirmar, aplicando }) {
  const taxa = indicadores ? formatarTaxa(indicadores.taxa_aprovacao_humana) : null

  return (
    <DetalheModal titulo="Ativar Execução Normal?" onClose={onCancelar}>
      <div className="space-y-4 text-sm">
        <div className="flex gap-2 items-start">
          <AlertTriangle size={18} className="text-inforrel-accent shrink-0 mt-0.5" />
          <p className="text-gray-700">
            Em <strong>Execução Normal</strong> o sistema responde ao cliente sem passar por
            aprovação humana. Toda resposta gerada vai direto, sem ninguém revisar antes.
          </p>
        </div>

        {canal && !canal.entrega_real && (
          <p className="text-gray-600 border border-gray-200 rounded p-2">
            O canal de saída está em <strong>{canal.canal_saida}</strong>, então nada é entregue de
            fato ainda. Essa é a segunda trava (definida no <code>.env</code>), não a primeira: se
            ela for liberada, este modo já estará valendo.
          </p>
        )}

        {erro && <p className="text-red-600">Não foi possível carregar os indicadores: {erro}</p>}

        {!erro && !indicadores && <p className="text-gray-500">Carregando indicadores...</p>}

        {indicadores && (
          <div className="space-y-2">
            <p className="text-gray-700 font-medium">
              Decisões humanas nos últimos {indicadores.dias} dias
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <Indicador rotulo="Aprovadas" valor={indicadores.aprovadas_por_humano} />
              <Indicador rotulo="Reprovadas" valor={indicadores.reprovadas_por_humano} />
              <Indicador
                rotulo="Taxa de aprovação"
                valor={taxa || '—'}
                observacao={taxa ? null : 'sem decisões no período'}
              />
              <Indicador rotulo="Aguardando decisão" valor={indicadores.pendentes} />
            </div>
            <p className="text-xs text-gray-500">
              As {indicadores.auto_aprovadas_pelo_sistema} mensagens já auto-aprovadas pelo próprio
              sistema (quando ele rodou em Execução Normal) ficam fora dos números acima: são
              carimbo automático, não julgamento de ninguém, e somá-las inflaria justo o indicador
              usado para tomar esta decisão.
            </p>
            {indicadores.decididas_por_humano === 0 && (
              <p className="text-gray-700">
                Ninguém aprovou nem reprovou nada no período. Não há evidência de que o agente
                esteja maduro o bastante para responder sozinho.
              </p>
            )}
          </div>
        )}

        <div className="flex justify-end gap-2 pt-2 border-t border-gray-200">
          <button
            onClick={onCancelar}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded text-gray-700 hover:bg-gray-50 transition"
          >
            Cancelar
          </button>
          <button
            onClick={onConfirmar}
            disabled={aplicando}
            className="px-3 py-1.5 text-sm rounded bg-inforrel-accent text-white font-medium hover:opacity-90 transition disabled:opacity-50"
          >
            {aplicando ? 'Ativando...' : 'Ativar Execução Normal'}
          </button>
        </div>
      </div>
    </DetalheModal>
  )
}

function ModoExecucaoBadge() {
  const [modo, setModo] = useState(null)
  const [canal, setCanal] = useState(null)
  const [alterando, setAlterando] = useState(false)
  const [erro, setErro] = useState(null)
  const [confirmando, setConfirmando] = useState(false)
  const [indicadores, setIndicadores] = useState(null)
  const [erroIndicadores, setErroIndicadores] = useState(null)

  const carregar = async () => {
    try {
      const dados = await api.getConfigExecucao()
      setModo(dados.modo_execucao)
      setCanal({ canal_saida: dados.canal_saida, entrega_real: dados.entrega_real })
      setErro(null)
    } catch (error) {
      setErro(error.message)
    }
  }

  useEffect(() => {
    carregar()
  }, [])

  const aplicar = async (novoModo) => {
    setAlterando(true)
    try {
      await api.patchConfigExecucao(novoModo)
      setModo(novoModo)
      setErro(null)
      setConfirmando(false)
    } catch (error) {
      setErro(error.message)
    } finally {
      setAlterando(false)
    }
  }

  const handleChange = async (e) => {
    const novoModo = e.target.value
    if (novoModo === modo) return

    // Só a promoção pede confirmação. O select continua controlado por `modo`, então
    // enquanto a pessoa não confirmar ele volta sozinho para o modo vigente.
    if (novoModo === 'execucao_normal') {
      setIndicadores(null)
      setErroIndicadores(null)
      setConfirmando(true)
      try {
        setIndicadores(await api.getIndicadoresExecucao(DIAS_INDICADORES))
      } catch (error) {
        setErroIndicadores(error.message)
      }
      return
    }

    await aplicar(novoModo)
  }

  if (!modo) {
    return erro ? <span className="text-xs text-red-500">Modo de execução indisponível</span> : null
  }

  return (
    <div className="flex items-center gap-2" title="Modo de execução vigente (REQ-011)">
      <span
        className={`text-xs px-2 py-1 rounded-full border font-medium ${CLASSES_MODO[modo] || 'bg-gray-100 text-gray-700 border-gray-300'}`}
      >
        {ROTULO_MODO[modo] || modo}
      </span>
      <select
        value={modo}
        onChange={handleChange}
        disabled={alterando}
        className="text-xs border border-gray-300 rounded px-1.5 py-1 focus:outline-none focus:ring-2 focus:ring-inforrel-primary"
      >
        {Object.keys(ROTULO_MODO).map((valor) => (
          <option key={valor} value={valor}>
            {ROTULO_MODO[valor]}
          </option>
        ))}
      </select>
      {confirmando && (
        <ConfirmacaoExecucaoNormal
          indicadores={indicadores}
          erro={erroIndicadores}
          canal={canal}
          aplicando={alterando}
          onCancelar={() => setConfirmando(false)}
          onConfirmar={() => aplicar('execucao_normal')}
        />
      )}
    </div>
  )
}

function UsuarioLogado() {
  const { usuario, logout } = useAuth()
  if (!usuario) return null
  return (
    <div className="flex items-center gap-2">
      <User size={14} />
      <span>{usuario.nome}</span>
      <button
        onClick={logout}
        title="Sair"
        className="flex items-center gap-1 hover:text-inforrel-accent transition"
      >
        <LogOut size={14} />
      </button>
    </div>
  )
}

function Header() {
  return (
    <>
      {/* Top Bar */}
      <div className="bg-inforrel-dark text-white text-sm py-2">
        <div className="container mx-auto px-4 max-w-5xl flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Phone size={14} />
            <span>(19) 3772-5050</span>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Mail size={14} />
              <span>contato@inforrel.com.br</span>
            </div>
            <UsuarioLogado />
          </div>
        </div>
      </div>

      {/* Header */}
      <header className="bg-white shadow-md">
        <div className="container mx-auto px-4 py-4 max-w-5xl flex items-center justify-between">
          <div className="flex items-center gap-4">
            <img
              src="/images/inforrel01.jpg"
              alt="Inforrel"
              className="h-14 w-auto"
              onError={(e) => {
                e.target.style.display = 'none'
              }}
            />
            <div className="hidden md:block">
              <h1 className="text-xl font-bold text-inforrel-primary font-heading">
                Assistente de Vendas
              </h1>
              <p className="text-sm text-gray-500">Controle de Ponto e Acesso</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="hidden sm:inline text-sm text-gray-600">
              Simulador de Atendimento
            </span>
            <span className="bg-inforrel-accent text-white text-xs px-3 py-1 rounded-full font-medium">
              POC
            </span>
            <ModoExecucaoBadge />
          </div>
        </div>
      </header>
    </>
  )
}

export default Header
