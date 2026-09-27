import { useEffect, useState } from 'react'
import { ThumbsUp, ThumbsDown, Undo2, MessageSquare, Brain, Flag, Save } from 'lucide-react'
import { api } from '../services/api'
import ReportDetalhe from './ReportDetalhe'
import { labelStatus } from '../constants/reports'
import { formatDatetimeBRT } from '../utils/datetime'
import { labelMotivoEscalonamento } from '../utils/atendimento'
import {
  labelGatilhoEscalonamento,
  labelAvaliacaoEscalonamento,
  linhasEvidencias,
} from '../utils/escalonamento'

const CLASSES_AVALIACAO = {
  procedente: 'bg-green-100 text-green-700',
  indevido: 'bg-red-100 text-red-700',
}

// "dd/MM HH:mm": o ano do formato padrão sobra para uma avaliação recente.
function dataCurta(iso) {
  return formatDatetimeBRT(iso, { year: undefined })
}

function EstadoAvaliacao({ escalonamento }) {
  const { avaliacao, avaliado_por: por, avaliado_em: em } = escalonamento
  if (!avaliacao) {
    return <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-600">Não avaliado</span>
  }
  return (
    <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${CLASSES_AVALIACAO[avaliacao] || 'bg-gray-100 text-gray-600'}`}>
      {labelAvaliacaoEscalonamento(avaliacao)}
      {por && ` por ${por}`}
      {em && ` em ${dataCurta(em)}`}
    </span>
  )
}

/** Avaliação humana de um escalonamento (REQ-004.5C): vale a última, `null` desfaz. */
function AvaliacaoEscalonamento({ escalonamento, onAtualizado }) {
  const [comentario, setComentario] = useState(escalonamento.avaliacao_comentario || '')
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState(null)

  useEffect(() => {
    setComentario(escalonamento.avaliacao_comentario || '')
  }, [escalonamento.avaliacao_comentario])

  const salvar = async (avaliacao) => {
    setSalvando(true)
    setErro(null)
    try {
      const atualizado = await api.avaliarEscalonamento(
        escalonamento.id,
        avaliacao,
        avaliacao ? comentario.trim() : null,
      )
      onAtualizado(atualizado)
    } catch (e) {
      console.error('Erro ao avaliar escalonamento:', e)
      setErro(e.message)
    } finally {
      setSalvando(false)
    }
  }

  // Trocar só o comentário reusa o PATCH com a avaliação atual. O backend grava o
  // comentário sem espaços nas pontas, então a comparação também.
  const comentarioMudou = comentario.trim() !== (escalonamento.avaliacao_comentario || '')
  const podeSalvarComentario = Boolean(escalonamento.avaliacao) && comentarioMudou && !salvando

  const botao = (valor, rotulo, Icone, classesAtivo) => {
    const ativo = escalonamento.avaliacao === valor
    return (
      <button
        type="button"
        onClick={() => salvar(valor)}
        disabled={salvando}
        aria-pressed={ativo}
        className={`flex items-center gap-1.5 px-2.5 py-1 text-xs rounded transition disabled:opacity-50 ${
          ativo ? classesAtivo : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
        }`}
      >
        <Icone size={12} />
        {rotulo}
      </button>
    )
  }

  return (
    <div className="mt-2 pt-2 border-t border-gray-100 space-y-2">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs font-medium text-gray-600">Avaliação:</span>
        <EstadoAvaliacao escalonamento={escalonamento} />
      </div>
      <textarea
        value={comentario}
        onChange={(e) => setComentario(e.target.value)}
        placeholder="Comentário opcional (ex.: o que o sistema leu errado)"
        aria-label="Comentário da avaliação"
        rows={2}
        className="w-full px-2 py-1.5 border border-gray-300 rounded-md text-xs focus:outline-none focus:ring-2 focus:ring-inforrel-primary resize-none"
      />
      <div className="flex items-center gap-2 flex-wrap">
        {botao('procedente', 'Procedente', ThumbsUp, 'bg-green-100 text-green-700 border border-green-200')}
        {botao('indevido', 'Indevido', ThumbsDown, 'bg-red-100 text-red-700 border border-red-200')}
        {escalonamento.avaliacao && (
          <button
            type="button"
            onClick={() => salvar(escalonamento.avaliacao)}
            disabled={!podeSalvarComentario}
            className="flex items-center gap-1 px-2.5 py-1 text-xs rounded bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 transition disabled:opacity-50 disabled:cursor-not-allowed"
            title={comentarioMudou ? 'Grava o comentário sem mudar a avaliação' : 'Edite o comentário para salvar'}
          >
            <Save size={12} />
            Salvar comentário
          </button>
        )}
        {escalonamento.avaliacao && (
          <button
            type="button"
            onClick={() => salvar(null)}
            disabled={salvando}
            className="flex items-center gap-1 px-2 py-1 text-xs text-gray-500 hover:text-inforrel-primary transition disabled:opacity-50"
            title="Volta para não avaliado (apaga também o comentário)"
          >
            <Undo2 size={12} />
            Desfazer avaliação
          </button>
        )}
        {salvando && <span className="text-xs text-gray-400">Salvando...</span>}
      </div>
      {!escalonamento.avaliacao && (escalonamento.mensagem_id || escalonamento.processamento_id) && (
        <p className="text-[11px] text-gray-400">
          Indevido abre um report na fila de Reports para corrigir a regra.
        </p>
      )}
      {erro && <p className="text-xs text-red-600">{erro}</p>}
    </div>
  )
}

/**
 * Report aberto quando o escalonamento foi avaliado como indevido. Continua aparecendo se a
 * avaliação mudar depois: o report é histórico de triagem e não é apagado.
 */
function ReportDoEscalonamento({ escalonamento, onAtualizado }) {
  const [aberto, setAberto] = useState(false)
  const reportId = escalonamento.report_id

  if (!reportId) {
    // Takeover manual não tem mensagem nem processamento, e todo report precisa de um dos dois.
    const semOrigem = !escalonamento.mensagem_id && !escalonamento.processamento_id
    if (escalonamento.avaliacao !== 'indevido' || !semOrigem) return null
    return (
      <p className="mt-1.5 text-[11px] text-gray-400">
        Sem report: o vendedor assumiu pelo painel e não há mensagem do cliente para analisar.
      </p>
    )
  }

  const status = escalonamento.report_status
  const rotulo = !status || status === 'aberto' ? `Report #${reportId} aberto` : `Report #${reportId} (${labelStatus(status)})`
  return (
    <>
      <button
        type="button"
        onClick={() => setAberto(true)}
        className="mt-1.5 flex items-center gap-1 text-xs text-inforrel-secondary hover:text-inforrel-primary hover:underline"
        title="Abrir o report na fila de triagem"
      >
        <Flag size={12} />
        {rotulo}
      </button>
      {aberto && (
        <ReportDetalhe
          reportId={reportId}
          onClose={() => setAberto(false)}
          onAtualizado={(r) => r?.status && onAtualizado({ ...escalonamento, report_status: r.status })}
        />
      )}
    </>
  )
}

function ItemEscalonamento({ escalonamento, onAtualizado, onIrParaMensagem, mensagemVisivel, onAbrirProcessamento }) {
  const evidencias = linhasEvidencias(escalonamento.evidencias)
  const gatilhos = escalonamento.gatilhos || []
  const idMsg = escalonamento.mensagem_id
  const idProc = escalonamento.processamento_id
  const linkMensagem = idMsg && onIrParaMensagem && (!mensagemVisivel || mensagemVisivel(idMsg))

  return (
    <li className="p-3 bg-white border border-gray-200 rounded-md">
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <span className="text-sm font-medium text-gray-800">
          {labelMotivoEscalonamento(escalonamento.motivo)}
        </span>
        <span className="text-xs text-gray-500">
          {formatDatetimeBRT(escalonamento.timestamp)}
          {escalonamento.ator && ` · por ${escalonamento.ator}`}
        </span>
      </div>

      <div className="mt-1.5 flex flex-wrap gap-1">
        {gatilhos.length > 0 ? (
          gatilhos.map((g) => (
            <span
              key={g}
              className="px-2 py-0.5 text-xs rounded-full bg-inforrel-accent/10 text-inforrel-accent font-medium"
              title={g}
            >
              {labelGatilhoEscalonamento(g)}
            </span>
          ))
        ) : (
          <span className="text-xs text-gray-500 italic">Gatilho não registrado</span>
        )}
      </div>

      {evidencias.length > 0 && (
        <ul className="mt-2 space-y-0.5 text-xs text-gray-700 list-disc list-inside">
          {evidencias.map((linha, i) => (
            <li key={i}>{linha}</li>
          ))}
        </ul>
      )}

      {(idMsg || idProc) && (
        <div className="mt-2 flex items-center gap-3 flex-wrap text-xs">
          {idMsg &&
            (linkMensagem ? (
              <button
                type="button"
                onClick={() => onIrParaMensagem(idMsg)}
                className="flex items-center gap-1 text-inforrel-secondary hover:text-inforrel-primary hover:underline"
                title="Rolar a conversa até a mensagem que causou o escalonamento"
              >
                <MessageSquare size={12} />
                Ver mensagem de origem (#{idMsg})
              </button>
            ) : (
              <span className="text-gray-400">mensagem #{idMsg}</span>
            ))}
          {idProc &&
            (onAbrirProcessamento ? (
              <button
                type="button"
                onClick={() => onAbrirProcessamento(idProc)}
                className="flex items-center gap-1 text-inforrel-secondary hover:text-inforrel-primary hover:underline"
                title="Ver raciocínio do cérebro"
              >
                <Brain size={12} />
                Ver raciocínio (#{idProc})
              </button>
            ) : (
              <span className="text-gray-400">processamento #{idProc}</span>
            ))}
        </div>
      )}

      <AvaliacaoEscalonamento escalonamento={escalonamento} onAtualizado={onAtualizado} />
      <ReportDoEscalonamento escalonamento={escalonamento} onAtualizado={onAtualizado} />
    </li>
  )
}

/**
 * "Por que escalou" (REQ-004.5B/5C): um item por escalonamento, do mais recente ao mais
 * antigo, com motivo, gatilhos, evidências e a avaliação humana.
 *
 * Com `escalonamentos` (já vindos do detalhe do atendimento) não busca nada; sem, busca
 * em `GET /api/atendimentos/{id}/escalonamentos`, de novo sempre que `recarregarChave`
 * mudar (ex.: depois de o vendedor assumir o atendimento, que cria um registro novo).
 *
 * `onIrParaMensagem`/`mensagemVisivel` só fazem sentido onde a conversa está na tela;
 * sem eles, a mensagem de origem aparece só como número.
 */
function EscalonamentosAtendimento({
  atendimentoId,
  escalonamentos: iniciais,
  recarregarChave,
  onIrParaMensagem,
  mensagemVisivel,
  onAbrirProcessamento,
  onCarregados,
}) {
  const [itens, setItens] = useState(iniciais || [])
  const [loading, setLoading] = useState(!iniciais)
  const [erro, setErro] = useState(null)

  useEffect(() => {
    if (iniciais) {
      setItens(iniciais)
      return
    }
    let cancelado = false
    setLoading(true)
    setErro(null)
    api
      .obterEscalonamentosAtendimento(atendimentoId)
      .then((data) => {
        if (!cancelado) setItens(data.escalonamentos || [])
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
  }, [atendimentoId, iniciais, recarregarChave])

  useEffect(() => {
    onCarregados?.(itens)
    // Só reage à lista: incluir o callback recarregaria a cada render do pai.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [itens])

  const substituir = (atualizado) => {
    setItens((atual) => atual.map((e) => (e.id === atualizado.id ? atualizado : e)))
  }

  if (loading) return <p className="text-xs text-gray-500">Carregando escalonamentos...</p>
  if (erro) return <p className="text-xs text-red-600">{erro}</p>
  if (itens.length === 0) {
    return (
      <p className="text-xs text-gray-500 italic">
        Sem registro detalhado. Escalonamentos anteriores a 26/09/2026 guardam só o motivo.
      </p>
    )
  }

  return (
    <ul className="space-y-2">
      {itens.map((esc) => (
        <ItemEscalonamento
          key={esc.id}
          escalonamento={esc}
          onAtualizado={substituir}
          onIrParaMensagem={onIrParaMensagem}
          mensagemVisivel={mensagemVisivel}
          onAbrirProcessamento={onAbrirProcessamento}
        />
      ))}
    </ul>
  )
}

export default EscalonamentosAtendimento
