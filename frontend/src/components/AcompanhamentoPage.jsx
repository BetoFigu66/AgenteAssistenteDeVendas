import { useState, useEffect } from 'react'
import { Eye, CheckCircle, XCircle, Send, UserPlus, Users, RefreshCw, Bot, User, Brain, Flag, Clipboard } from 'lucide-react'
import { api } from '../services/api'
import DetalheModal from './DetalheModal'
import ProcessamentoDetalhes from './ProcessamentoDetalhes'
import { formatDatetimeBRT } from '../utils/datetime'
import { numeroAtendimentoExibicao, rotuloAtendimento, rotuloFase, classesFase } from '../utils/atendimento'

function AcompanhamentoPage() {
  const [atendimentos, setAtendimentos] = useState([])
  const [atendimentoSelecionado, setAtendimentoSelecionado] = useState(null)
  const [mensagensAtendimento, setMensagensAtendimento] = useState([])
  const [carregandoAtendimentos, setCarregandoAtendimentos] = useState(false)
  const [carregandoMensagens, setCarregandoMensagens] = useState(false)
  const [erro, setErro] = useState(null)

  const [users, setUsers] = useState([])
  const [userSelecionado, setUserSelecionado] = useState(null)
  const [mostrarModalCriarUser, setMostrarModalCriarUser] = useState(false)
  const [novoUserNome, setNovoUserNome] = useState('')

  const [modoOperacao, setModoOperacao] = useState('agente')
  const [mensagemManual, setMensagemManual] = useState('')
  const [enviandoMensagem, setEnviandoMensagem] = useState(false)

  const [processamentoSelecionado, setProcessamentoSelecionado] = useState(null)

  const [mensagemReprovando, setMensagemReprovando] = useState(null)
  const [justificativaReprovacao, setJustificativaReprovacao] = useState('')
  const [enviandoReprovacao, setEnviandoReprovacao] = useState(false)

  const [slaAprovacaoMinutos, setSlaAprovacaoMinutos] = useState(10)

  const [perguntaQA, setPerguntaQA] = useState('')
  const [contextoQA, setContextoQA] = useState('')
  const [respostaQA, setRespostaQA] = useState('')
  const [pendentesQA, setPendentesQA] = useState([])
  const [carregandoPendentesQA, setCarregandoPendentesQA] = useState(false)
  const [confirmandoPendentesQA, setConfirmandoPendentesQA] = useState(false)

  useEffect(() => {
    carregarAtendimentos()
    carregarUsers()
    carregarConfigExecucao()
  }, [])

  useEffect(() => {
    if (atendimentoSelecionado) {
      carregarMensagensAtendimento(atendimentoSelecionado.telefone)
      setModoOperacao(atendimentoSelecionado.modo_operacao || 'agente')
    } else {
      setMensagensAtendimento([])
    }
  }, [atendimentoSelecionado])

  useEffect(() => {
    if (mensagemReprovando) {
      const idx = mensagensAtendimento.findIndex(m => m.id === mensagemReprovando.id)
      const msgCliente = mensagensAtendimento.slice(0, idx).reverse().find(m => m.origem === 'user')
      setPerguntaQA(msgCliente?.conteudo || '')
      setContextoQA('')
      setRespostaQA('')
      setPendentesQA([])
      setConfirmandoPendentesQA(false)
    }
  }, [mensagemReprovando])

  const fecharModalReprovacao = () => {
    setMensagemReprovando(null)
    setJustificativaReprovacao('')
    setPerguntaQA('')
    setContextoQA('')
    setRespostaQA('')
    setPendentesQA([])
    setConfirmandoPendentesQA(false)
  }

  const carregarAtendimentos = async () => {
    setCarregandoAtendimentos(true)
    setErro(null)
    try {
      const data = await api.listarAtendimentosAtivos()
      setAtendimentos(data.atendimentos || [])
    } catch (error) {
      console.error('Erro ao carregar atendimentos:', error)
      setErro('Erro ao carregar atendimentos ativos')
    } finally {
      setCarregandoAtendimentos(false)
    }
  }

  const carregarUsers = async () => {
    try {
      const data = await api.listarUsers()
      setUsers(data.users || [])
      if (data.users && data.users.length > 0 && !userSelecionado) {
        setUserSelecionado(data.users[0].id)
      }
    } catch (error) {
      console.error('Erro ao carregar usuários:', error)
    }
  }

  const carregarConfigExecucao = async () => {
    try {
      const data = await api.getConfigExecucao()
      setSlaAprovacaoMinutos(data.sla_aprovacao_minutos || 10)
    } catch (error) {
      console.error('Erro ao carregar config de execução:', error)
    }
  }

  const carregarMensagensAtendimento = async (telefone) => {
    setCarregandoMensagens(true)
    try {
      const data = await api.obterHistorico(telefone)
      setMensagensAtendimento(data.mensagens || [])
    } catch (error) {
      console.error('Erro ao carregar mensagens:', error)
      setMensagensAtendimento([])
    } finally {
      setCarregandoMensagens(false)
    }
  }

  const handleCriarUser = async () => {
    if (!novoUserNome.trim()) return
    try {
      const user = await api.criarUser(novoUserNome.trim())
      setUsers([...users, user])
      setUserSelecionado(user.id)
      setMostrarModalCriarUser(false)
      setNovoUserNome('')
    } catch (error) {
      console.error('Erro ao criar usuário:', error)
      alert('Erro ao criar usuário: ' + error.message)
    }
  }

  const handleAlterarModo = async (novoModo) => {
    if (!atendimentoSelecionado) return
    try {
      await api.alterarModoOperacao(atendimentoSelecionado.id, novoModo)
      setModoOperacao(novoModo)
      carregarAtendimentos()
    } catch (error) {
      console.error('Erro ao alterar modo:', error)
      alert('Erro ao alterar modo de operação: ' + error.message)
    }
  }

  const handleCopiarContextoQA = async (msg) => {
    try {
      const idx = mensagensAtendimento.findIndex(m => m.id === msg.id)
      let perguntaCliente = null
      let respostaSistema = null
      if (msg.origem === 'system') {
        respostaSistema = msg
        perguntaCliente = mensagensAtendimento
          .slice(0, idx)
          .reverse()
          .find(m => m.origem === 'user') || null
      } else {
        perguntaCliente = msg
        respostaSistema = mensagensAtendimento
          .slice(idx + 1)
          .find(m => m.origem === 'system') || null
      }
      const contexto = {
        fonte: 'AcompanhamentoPage',
        telefone: atendimentoSelecionado?.telefone || null,
        atendimento_id: atendimentoSelecionado?.id || null,
        atendimento_numero: numeroAtendimentoExibicao(atendimentoSelecionado),
        modo_operacao: modoOperacao || null,
        capturado_em: new Date().toISOString(),
        pergunta_cliente: perguntaCliente ? {
          mensagem_id: perguntaCliente.id,
          timestamp: perguntaCliente.timestamp,
          conteudo: perguntaCliente.conteudo,
        } : null,
        resposta_sistema: respostaSistema ? {
          mensagem_id: respostaSistema.id,
          timestamp: respostaSistema.timestamp,
          conteudo: respostaSistema.conteudo,
          pendente_aprovacao: !!respostaSistema.pendente_aprovacao,
          processamento_id: respostaSistema.processamento_id || null,
        } : null,
      }
      const texto = JSON.stringify(contexto, null, 2)
      await navigator.clipboard.writeText(texto)
      alert('Contexto copiado. Cole no QA Runner ao reportar um bug.')
    } catch (error) {
      console.error('Erro ao copiar contexto QA:', error)
      alert('Falha ao copiar contexto: ' + error.message)
    }
  }

  const handleAprovarMensagem = async (mensagemId) => {
    if (!userSelecionado) {
      alert('Selecione um usuário para aprovar a mensagem')
      return
    }
    // REQ-011.6: feedback opcional na aprovação — "correto, mas..." (Cancelar/vazio pula).
    const feedback = window.prompt(
      'Feedback opcional sobre esta resposta (deixe em branco para pular):',
      ''
    )
    try {
      await api.aprovarMensagem(mensagemId, userSelecionado, feedback || null)
      if (atendimentoSelecionado) {
        carregarMensagensAtendimento(atendimentoSelecionado.telefone)
      }
      carregarAtendimentos()
    } catch (error) {
      console.error('Erro ao aprovar mensagem:', error)
      alert('Erro ao aprovar mensagem: ' + error.message)
    }
  }

  const handleReprovarMensagem = async () => {
    if (!mensagemReprovando || !justificativaReprovacao.trim()) return
    if (!userSelecionado) {
      alert('Selecione um usuário para reprovar a mensagem')
      return
    }

    if (respostaQA.trim() && !confirmandoPendentesQA) {
      setCarregandoPendentesQA(true)
      try {
        const data = await api.listarPendentesAprovacaoQA(contextoQA || undefined)
        if (data.total > 0) {
          setPendentesQA(data.pares)
          setConfirmandoPendentesQA(true)
          return
        }
      } catch {
        // falha silenciosa — prossegue sem verificação
      } finally {
        setCarregandoPendentesQA(false)
      }
    }

    setEnviandoReprovacao(true)
    try {
      await api.reprovarMensagem(mensagemReprovando.id, justificativaReprovacao.trim(), userSelecionado)

      let mensagemAlerta = 'Mensagem reprovada com sucesso'
      if (respostaQA.trim() && perguntaQA.trim()) {
        try {
          await api.criarParQA({
            pergunta: perguntaQA.trim(),
            resposta: respostaQA.trim(),
            contexto: contextoQA || null,
            criado_por: String(userSelecionado),
          })
          mensagemAlerta = 'Mensagem reprovada · Rascunho Q&A salvo para revisão'
        } catch (errQA) {
          mensagemAlerta = `Mensagem reprovada · Falha ao salvar rascunho Q&A: ${errQA.message}`
        }
      }

      fecharModalReprovacao()
      if (atendimentoSelecionado) {
        carregarMensagensAtendimento(atendimentoSelecionado.telefone)
      }
      carregarAtendimentos()
      alert(mensagemAlerta)
    } catch (error) {
      console.error('Erro ao reprovar mensagem:', error)
      alert('Erro ao reprovar mensagem: ' + error.message)
    } finally {
      setEnviandoReprovacao(false)
    }
  }

  const handleEnviarMensagemManual = async () => {
    if (!mensagemManual.trim() || !atendimentoSelecionado) return
    setEnviandoMensagem(true)
    try {
      await api.enviarMensagemManual(
        atendimentoSelecionado.id,
        mensagemManual.trim(),
        userSelecionado
      )
      setMensagemManual('')
      carregarMensagensAtendimento(atendimentoSelecionado.telefone)
    } catch (error) {
      console.error('Erro ao enviar mensagem manual:', error)
      alert('Erro ao enviar mensagem: ' + error.message)
    } finally {
      setEnviandoMensagem(false)
    }
  }

  const formatarData = (timestamp) => formatDatetimeBRT(timestamp)

  const tituloListaAtendimento = (atendimento) => {
    const rotulo = rotuloAtendimento(atendimento)
    if (atendimento.empresa_nome) {
      return `${rotulo} — ${atendimento.empresa_nome}`
    }
    return rotulo
  }

  return (
    <div className="container mx-auto px-4 py-6 max-w-7xl">
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <h2 className="text-lg font-semibold text-inforrel-primary">
              Acompanhamento de Atendimentos
            </h2>
            <button
              onClick={carregarAtendimentos}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 hover:text-inforrel-primary transition"
              title="Atualizar lista"
            >
              <RefreshCw size={16} className={carregandoAtendimentos ? 'animate-spin' : ''} />
              Atualizar
            </button>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Users size={18} className="text-gray-500" />
              <select
                value={userSelecionado || ''}
                onChange={(e) => setUserSelecionado(Number(e.target.value))}
                className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-inforrel-primary"
              >
                <option value="">Selecione um usuário</option>
                {users.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.nome}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={() => setMostrarModalCriarUser(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-inforrel-primary text-white rounded-md text-sm hover:bg-inforrel-secondary transition"
            >
              <UserPlus size={16} />
              Novo Usuário
            </button>
          </div>
        </div>

        {erro && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
            {erro}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
            <h3 className="font-medium text-gray-700">
              Atendimentos Ativos ({atendimentos.length})
            </h3>
            <p className="text-xs text-gray-500 mt-1">
              Ordenados por mensagens pendentes de aprovação
            </p>
          </div>

          <div className="max-h-[calc(100vh-280px)] overflow-y-auto">
            {carregandoAtendimentos ? (
              <div className="p-8 text-center text-gray-500">
                <RefreshCw size={24} className="animate-spin mx-auto mb-2" />
                Carregando...
              </div>
            ) : atendimentos.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                Nenhum atendimento ativo encontrado
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {atendimentos.map((atendimento) => (
                  <div
                    key={atendimento.id}
                    onClick={() => setAtendimentoSelecionado(atendimento)}
                    className={`p-4 cursor-pointer transition hover:bg-gray-50 ${
                      atendimentoSelecionado?.id === atendimento.id ? 'bg-blue-50 border-l-4 border-inforrel-primary' : 'border-l-4 border-transparent'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <span className="px-2 py-0.5 text-xs rounded-full bg-inforrel-primary/10 text-inforrel-primary font-semibold">
                            {rotuloAtendimento(atendimento)}
                          </span>
                          {atendimento.empresa_nome && (
                            <span className="font-medium text-gray-900 truncate">
                              {atendimento.empresa_nome}
                            </span>
                          )}
                          <span
                            className={`px-2 py-0.5 text-xs rounded-full ${
                              atendimento.modo_operacao === 'humano'
                                ? 'bg-orange-100 text-orange-700'
                                : 'bg-green-100 text-green-700'
                            }`}
                          >
                            {atendimento.modo_operacao === 'humano' ? 'HUMANO' : 'AGENTE'}
                          </span>
                          {atendimento.fase && (
                            <span
                              className={`px-2 py-0.5 text-xs rounded-full font-medium ${classesFase(atendimento.fase)}`}
                            >
                              {rotuloFase(atendimento.fase)}
                            </span>
                          )}
                        </div>
                        <div className="text-sm text-gray-600">
                          {atendimento.nome_contato || 'Sem nome'} • {atendimento.telefone}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          Status: {atendimento.status} • Última msg:{' '}
                          {formatarData(atendimento.ultima_mensagem_at || atendimento.updated_at)}
                        </div>
                      </div>

                      <div className="flex flex-col items-end gap-1 ml-3">
                        {atendimento.mensagens_pendentes > 0 && (
                          <span className="px-2 py-1 bg-red-100 text-red-700 text-xs font-medium rounded-full">
                            {atendimento.mensagens_pendentes} pendente{atendimento.mensagens_pendentes > 1 ? 's' : ''}
                          </span>
                        )}
                        <Eye size={16} className="text-gray-400" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          {!atendimentoSelecionado ? (
            <div className="p-8 text-center text-gray-500">
              <Eye size={48} className="mx-auto mb-4 text-gray-300" />
              <p>Selecione um atendimento para visualizar os detalhes</p>
            </div>
          ) : (
            <>
              <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="px-2 py-0.5 text-xs rounded-full bg-inforrel-primary/10 text-inforrel-primary font-semibold">
                        {rotuloAtendimento(atendimentoSelecionado)}
                      </span>
                      {atendimentoSelecionado.fase && (
                        <span
                          className={`px-2 py-0.5 text-xs rounded-full font-medium ${classesFase(atendimentoSelecionado.fase)}`}
                        >
                          {rotuloFase(atendimentoSelecionado.fase)}
                        </span>
                      )}
                    </div>
                    <h3 className="font-medium text-gray-900">
                      {tituloListaAtendimento(atendimentoSelecionado)}
                    </h3>
                    <p className="text-sm text-gray-600">
                      {atendimentoSelecionado.nome_contato || 'Sem nome'} • {atendimentoSelecionado.telefone}
                    </p>
                  </div>
                </div>

                <div className="mt-3 p-3 bg-white rounded-md border border-gray-200">
                  <label className="text-sm font-medium text-gray-700 block mb-2">
                    Modo de Operação
                  </label>
                  <div className="flex gap-4">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="modoOperacao"
                        value="agente"
                        checked={modoOperacao === 'agente'}
                        onChange={() => handleAlterarModo('agente')}
                        className="w-4 h-4 text-inforrel-primary focus:ring-inforrel-primary"
                      />
                      <span className="flex items-center gap-1.5 text-sm">
                        <Bot size={16} className="text-green-600" />
                        Agente (automático)
                      </span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="modoOperacao"
                        value="humano"
                        checked={modoOperacao === 'humano'}
                        onChange={() => handleAlterarModo('humano')}
                        className="w-4 h-4 text-inforrel-primary focus:ring-inforrel-primary"
                      />
                      <span className="flex items-center gap-1.5 text-sm">
                        <User size={16} className="text-orange-600" />
                        Humano (manual)
                      </span>
                    </label>
                  </div>
                </div>
              </div>

              {mensagensAtendimento.filter(m => m.origem === 'system' && m.pendente_aprovacao).length > 0 && (
                <div className="mx-4 mt-3 p-3 bg-yellow-50 border border-yellow-300 rounded-md">
                  <div className="flex items-center gap-2 text-yellow-800">
                    <CheckCircle size={18} />
                    <span className="font-medium text-sm">
                      {mensagensAtendimento.filter(m => m.origem === 'system' && m.pendente_aprovacao).length} mensagen(s) pendente(s) de aprovação
                    </span>
                  </div>
                  {!userSelecionado && (
                    <p className="text-xs text-yellow-700 mt-1">
                      Selecione um usuário no topo da página para aprovar as mensagens.
                    </p>
                  )}
                </div>
              )}

              <div className="max-h-[calc(100vh-450px)] overflow-y-auto p-4 space-y-3">
                {carregandoMensagens ? (
                  <div className="text-center text-gray-500 py-8">
                    <RefreshCw size={20} className="animate-spin mx-auto mb-2" />
                    Carregando mensagens...
                  </div>
                ) : mensagensAtendimento.length === 0 ? (
                  <div className="text-center text-gray-500 py-8">
                    Nenhuma mensagem encontrada
                  </div>
                ) : (
                  mensagensAtendimento.map((msg) => (
                    <div
                      key={msg.id}
                      className={`flex ${
                        msg.origem === 'user' ? 'justify-end' : 'justify-start'
                      }`}
                    >
                      <div
                        className={`max-w-[85%] rounded-lg px-4 py-2.5 ${
                          msg.origem === 'user'
                            ? 'bg-blue-50 border-l-4 border-inforrel-secondary'
                            : msg.pendente_aprovacao
                            ? 'bg-yellow-50 border-l-4 border-yellow-400'
                            : 'bg-white border-l-4 border-inforrel-primary shadow-sm'
                        }`}
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-medium text-gray-500">
                            {msg.origem === 'user' ? 'Cliente' : 'Assistente'}
                          </span>
                          <span className="text-xs text-gray-400">
                            {formatarData(msg.timestamp)}
                          </span>
                          {msg.origem === 'system' && (
                            <>
                              {msg.pendente_aprovacao ? (
                                <>
                                  <span className="px-1.5 py-0.5 bg-yellow-200 text-yellow-800 text-xs rounded">
                                    Pendente
                                  </span>
                                  {msg.segundos_pendente != null && (
                                    <span
                                      className={`px-1.5 py-0.5 text-xs rounded ${
                                        msg.segundos_pendente >= slaAprovacaoMinutos * 60
                                          ? 'bg-red-200 text-red-800 font-medium'
                                          : 'bg-gray-100 text-gray-500'
                                      }`}
                                      title={`SLA de aprovação: ${slaAprovacaoMinutos} min`}
                                    >
                                      há {Math.max(1, Math.floor(msg.segundos_pendente / 60))} min
                                    </span>
                                  )}
                                </>
                              ) : (
                                <span className="px-1.5 py-0.5 bg-green-200 text-green-800 text-xs rounded">
                                  Aprovada
                                </span>
                              )}
                            </>
                          )}
                          {msg.processamento_id && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                setProcessamentoSelecionado(msg.processamento_id)
                              }}
                              className={`${msg.processamento_id ? 'ml-auto' : ''} text-gray-400 hover:text-inforrel-primary transition`}
                              title="Ver raciocínio do cérebro"
                              type="button"
                            >
                              <Brain size={14} />
                            </button>
                          )}
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleCopiarContextoQA(msg)
                            }}
                            className={`${msg.processamento_id ? '' : 'ml-auto'} text-gray-400 hover:text-inforrel-primary transition`}
                            title="Copiar contexto desta mensagem para reportar bug no QA Runner"
                            type="button"
                          >
                            <Clipboard size={14} />
                          </button>
                        </div>
                        <p className="text-gray-800 text-sm">{msg.conteudo}</p>

                        {msg.origem === 'system' && (
                          <div className="mt-2 flex items-center gap-2">
                            {msg.pendente_aprovacao && (
                              <>
                                <button
                                  onClick={() => handleAprovarMensagem(msg.id)}
                                  disabled={!userSelecionado}
                                  className={`flex items-center gap-1.5 px-2.5 py-1 text-xs rounded transition ${
                                    userSelecionado
                                      ? 'bg-inforrel-primary text-white hover:bg-inforrel-secondary'
                                      : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                  }`}
                                  title={userSelecionado ? 'Aprovar mensagem' : 'Selecione um usuário para aprovar'}
                                >
                                  <CheckCircle size={12} />
                                  Aprovar
                                  {!userSelecionado && ' (selecione usuário)'}
                                </button>
                                <button
                                  onClick={() => setMensagemReprovando(msg)}
                                  disabled={!userSelecionado}
                                  className={`flex items-center gap-1.5 px-2.5 py-1 text-xs rounded transition ${
                                    userSelecionado
                                      ? 'bg-red-100 text-red-700 hover:bg-red-200'
                                      : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                  }`}
                                  title={userSelecionado ? 'Reprovar mensagem' : 'Selecione um usuário para reprovar'}
                                >
                                  <XCircle size={12} />
                                  Reprovar
                                  {!userSelecionado && ' (selecione usuário)'}
                                </button>
                              </>
                            )}
                            {msg.processamento_id && (
                              <button
                                onClick={() => setProcessamentoSelecionado(msg.processamento_id)}
                                className="flex items-center gap-1.5 px-2.5 py-1 text-xs rounded bg-orange-100 text-orange-700 hover:bg-orange-200 transition"
                                title="Reportar problema com esta mensagem"
                              >
                                <Flag size={12} />
                                Reportar
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>

              {modoOperacao === 'humano' && (
                <div className="p-4 bg-gray-50 border-t border-gray-200">
                  <div className="flex gap-2">
                    <textarea
                      value={mensagemManual}
                      onChange={(e) => setMensagemManual(e.target.value)}
                      placeholder="Digite a mensagem para enviar ao cliente..."
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-inforrel-primary resize-none"
                      rows={2}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault()
                          handleEnviarMensagemManual()
                        }
                      }}
                    />
                    <button
                      onClick={handleEnviarMensagemManual}
                      disabled={!mensagemManual.trim() || enviandoMensagem}
                      className="px-4 py-2 bg-inforrel-primary text-white rounded-md hover:bg-inforrel-secondary transition disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {enviandoMensagem ? (
                        <RefreshCw size={18} className="animate-spin" />
                      ) : (
                        <Send size={18} />
                      )}
                    </button>
                  </div>
                  <p className="text-xs text-gray-500 mt-2">
                    Pressione Enter para enviar, Shift+Enter para nova linha
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {mostrarModalCriarUser && (
        <DetalheModal
          titulo="Criar Novo Usuário"
          onClose={() => {
            setMostrarModalCriarUser(false)
            setNovoUserNome('')
          }}
        >
          <div className="p-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Nome do usuário
            </label>
            <input
              type="text"
              value={novoUserNome}
              onChange={(e) => setNovoUserNome(e.target.value)}
              placeholder="Ex: Rita, Beto, João..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-inforrel-primary"
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleCriarUser()
              }}
              autoFocus
            />
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => {
                  setMostrarModalCriarUser(false)
                  setNovoUserNome('')
                }}
                className="px-4 py-2 text-gray-600 hover:text-gray-800 transition"
              >
                Cancelar
              </button>
              <button
                onClick={handleCriarUser}
                disabled={!novoUserNome.trim()}
                className="px-4 py-2 bg-inforrel-primary text-white rounded-md hover:bg-inforrel-secondary transition disabled:opacity-50"
              >
                Criar Usuário
              </button>
            </div>
          </div>
        </DetalheModal>
      )}

      {mensagemReprovando && (
        <DetalheModal
          titulo="Reprovar Mensagem"
          onClose={fecharModalReprovacao}
        >
          <div className="p-4 space-y-4">
            <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-md">
              <p className="text-sm text-yellow-800 font-medium mb-1">Mensagem a ser reprovada:</p>
              <p className="text-sm text-gray-700">{mensagemReprovando.conteudo}</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Justificativa da reprovação <span className="text-red-500">*</span>
              </label>
              <textarea
                value={justificativaReprovacao}
                onChange={(e) => setJustificativaReprovacao(e.target.value)}
                placeholder="Descreva o problema com esta mensagem..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-inforrel-primary resize-none"
                rows={3}
              />
              <p className="text-xs text-gray-500 mt-1">
                Esta justificativa será registrada como um report de problema vinculado à mensagem.
              </p>
            </div>

            <div className="border border-gray-200 rounded-md">
              <div className="px-3 py-2 bg-gray-50 border-b border-gray-200 rounded-t-md">
                <p className="text-sm font-medium text-gray-700">Registrar nova resposta (opcional)</p>
                <p className="text-xs text-gray-500">Se preenchida, será salva como rascunho para revisão na Base Q&A.</p>
              </div>
              <div className="p-3 space-y-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Pergunta do cliente (pré-preenchida, editável)
                  </label>
                  <textarea
                    value={perguntaQA}
                    onChange={(e) => { setPerguntaQA(e.target.value); setConfirmandoPendentesQA(false); setPendentesQA([]) }}
                    placeholder="Pergunta que gerou esta resposta inadequada..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-inforrel-primary resize-none text-sm"
                    rows={2}
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Contexto</label>
                  <select
                    value={contextoQA}
                    onChange={(e) => { setContextoQA(e.target.value); setConfirmandoPendentesQA(false); setPendentesQA([]) }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-inforrel-primary text-sm"
                  >
                    <option value="">— geral —</option>
                    <option value="catraca">Catraca</option>
                    <option value="relogio_ponto">Relógio de Ponto</option>
                    <option value="facial">Leitor Facial</option>
                    <option value="controle_acesso">Controle de Acesso</option>
                    <option value="bastao_ronda">Bastão de Ronda</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Resposta correta <span className="text-gray-400">(obrigatória para salvar)</span>
                  </label>
                  <textarea
                    value={respostaQA}
                    onChange={(e) => { setRespostaQA(e.target.value); setConfirmandoPendentesQA(false); setPendentesQA([]) }}
                    placeholder="Como o assistente deveria ter respondido..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-inforrel-primary resize-none text-sm"
                    rows={3}
                  />
                </div>
                {confirmandoPendentesQA && pendentesQA.length > 0 && (
                  <div className="p-3 bg-orange-50 border border-orange-300 rounded-md">
                    <p className="text-sm font-medium text-orange-800 mb-2">
                      ⚠️ Já existem {pendentesQA.length} rascunho(s) aguardando aprovação{contextoQA ? ` no contexto "${contextoQA}"` : ''}:
                    </p>
                    <ul className="space-y-1 max-h-32 overflow-y-auto">
                      {pendentesQA.map(p => (
                        <li key={p.id} className="text-xs text-orange-700 bg-white border border-orange-200 rounded px-2 py-1">
                          <span className="font-medium">#{p.id}</span> — {p.pergunta?.slice(0, 80)}{p.pergunta?.length > 80 ? '...' : ''}
                        </li>
                      ))}
                    </ul>
                    <p className="text-xs text-orange-700 mt-2">Clique em "Reprovar" novamente para confirmar mesmo assim.</p>
                  </div>
                )}
              </div>
            </div>

            <div className="flex justify-end gap-2">
              <button
                onClick={fecharModalReprovacao}
                className="px-4 py-2 text-gray-600 hover:text-gray-800 transition"
              >
                Cancelar
              </button>
              <button
                onClick={handleReprovarMensagem}
                disabled={!justificativaReprovacao.trim() || enviandoReprovacao || carregandoPendentesQA}
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition disabled:opacity-50 flex items-center gap-2"
              >
                {(enviandoReprovacao || carregandoPendentesQA) ? (
                  <>
                    <RefreshCw size={16} className="animate-spin" />
                    {carregandoPendentesQA ? 'Verificando...' : 'Enviando...'}
                  </>
                ) : (
                  <>
                    <XCircle size={16} />
                    {confirmandoPendentesQA ? 'Reprovar mesmo assim' : 'Reprovar Mensagem'}
                    {respostaQA.trim() ? ' + Salvar rascunho' : ''}
                  </>
                )}
              </button>
            </div>
          </div>
        </DetalheModal>
      )}

      {processamentoSelecionado && (
        <DetalheModal
          titulo={`Raciocínio do cérebro — processamento #${processamentoSelecionado}`}
          onClose={() => setProcessamentoSelecionado(null)}
        >
          <ProcessamentoDetalhes processamentoId={processamentoSelecionado} />
        </DetalheModal>
      )}
    </div>
  )
}

export default AcompanhamentoPage
