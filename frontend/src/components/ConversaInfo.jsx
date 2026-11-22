import { useEffect, useRef, useState } from 'react'
import { Building2, Contact, User, UserCircle, Briefcase, ListChecks, CheckCircle2, Copy, Check, Send, Clock, XCircle, CircleDashed } from 'lucide-react'
import DetalheModal from './DetalheModal'
import EmpresaDetalhes from './EmpresaDetalhes'
import AtendimentoDetalhes from './AtendimentoDetalhes'
import { api } from '../services/api'

import { rotuloAtendimento, rotuloFase, classesFase, rotuloCampo } from '../utils/atendimento'

// Situação de cada pergunta pendente (backend: campos_pendentes.perguntas_para_painel).
const SITUACAO_PERGUNTA = {
  enviada: { rotulo: 'Enviada', icone: Send, classes: 'text-green-700' },
  aguardando_aprovacao: { rotulo: 'Aguardando aprovação', icone: Clock, classes: 'text-amber-700' },
  reprovada: { rotulo: 'Reprovada', icone: XCircle, classes: 'text-red-600' },
  nao_enviada: { rotulo: 'Não enviada', icone: CircleDashed, classes: 'text-gray-500' },
}

function CamposPendentesBadge({ atendimentoId, temCapturados }) {
  const [perguntas, setPerguntas] = useState([])
  const [aberto, setAberto] = useState(false)
  const [copiado, setCopiado] = useState(false)
  const caixa = useRef(null)

  useEffect(() => {
    let cancelado = false
    setAberto(false)
    if (!atendimentoId) {
      setPerguntas([])
      return
    }
    api
      .obterCamposPendentes(atendimentoId)
      .then((data) => !cancelado && setPerguntas(data.perguntas || []))
      .catch(() => !cancelado && setPerguntas([]))
    return () => {
      cancelado = true
    }
  }, [atendimentoId])

  // Fecha a lista ao clicar fora dela.
  useEffect(() => {
    if (!aberto) return
    const fora = (e) => caixa.current && !caixa.current.contains(e.target) && setAberto(false)
    document.addEventListener('mousedown', fora)
    return () => document.removeEventListener('mousedown', fora)
  }, [aberto])

  // REQ-010.7B: nada pendente com algo já coletado é "coleta completa". Sem nenhum
  // campo capturado não há o que comemorar — é só uma conversa que ainda nem começou
  // a qualificar.
  if (perguntas.length === 0) {
    if (!temCapturados) return null
    return (
      <span className="flex items-center gap-1 px-2 py-0.5 text-xs rounded-full font-medium bg-green-100 text-green-700">
        <CheckCircle2 size={12} />
        Pronto para orçamento
      </span>
    )
  }

  // Uma pergunta por linha, com a situação entre colchetes, para colar em report ou nota.
  const copiar = async () => {
    const texto = perguntas.map((p) => `[${SITUACAO_PERGUNTA[p.situacao]?.rotulo || p.situacao}] ${p.pergunta}`).join('\n')
    try {
      await navigator.clipboard.writeText(texto)
      setCopiado(true)
      setTimeout(() => setCopiado(false), 2000)
    } catch (e) {
      alert('Falha ao copiar: ' + e.message)
    }
  }

  const enviadas = perguntas.filter((p) => p.situacao === 'enviada').length

  return (
    <span ref={caixa} className="relative">
      <button
        type="button"
        onClick={() => setAberto((a) => !a)}
        className="flex items-center gap-1 px-2 py-0.5 text-xs rounded-full font-medium bg-amber-100 text-amber-700 hover:bg-amber-200"
        title="Ver as perguntas pendentes"
        aria-expanded={aberto}
      >
        <ListChecks size={12} />
        {perguntas.length} pendente{perguntas.length > 1 ? 's' : ''}
        <span className="font-normal">({enviadas} enviada{enviadas === 1 ? '' : 's'})</span>
      </button>
      {aberto && (
        <div className="absolute left-0 top-full mt-1 z-20 w-96 max-w-[90vw] bg-white border border-gray-200 rounded-lg shadow-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-gray-700">Perguntas pendentes</span>
            <button
              type="button"
              onClick={copiar}
              className="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded border border-inforrel-primary text-inforrel-primary hover:bg-inforrel-primary hover:text-white transition"
            >
              {copiado ? <Check size={12} /> : <Copy size={12} />}
              {copiado ? 'Copiado' : 'Copiar'}
            </button>
          </div>
          <ul className="space-y-1.5 select-text">
            {perguntas.map((p) => {
              const s = SITUACAO_PERGUNTA[p.situacao] || SITUACAO_PERGUNTA.nao_enviada
              const Icone = s.icone
              return (
                <li key={p.chave} className="flex gap-2 text-xs text-gray-800">
                  <span className={`flex items-center gap-1 shrink-0 w-36 ${s.classes}`}>
                    <Icone size={12} />
                    {s.rotulo}
                  </span>
                  <span>{p.pergunta}</span>
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </span>
  )
}

/**
 * REQ-010.7B: o que já foi coletado, visível sem abrir modal, para o atendente não
 * repetir pergunta que o cliente já respondeu. A lista vem filtrada pelo catálogo de
 * campos no backend — chave de controle interno do motor não chega aqui.
 */
function CamposCapturados({ campos }) {
  if (!campos || campos.length === 0) return null

  return (
    <div className="flex flex-wrap items-center gap-1.5 mt-1">
      <span className="text-xs text-gray-500">Já coletado:</span>
      {campos.map((campo) => (
        <span
          key={campo.chave}
          className="px-2 py-0.5 text-xs rounded-full bg-inforrel-secondary/10 text-inforrel-secondary cursor-help"
          title={campo.pergunta}
        >
          {rotuloCampo(campo.chave)}: <strong className="font-medium">{campo.valor}</strong>
        </span>
      ))}
    </div>
  )
}

function ConversaInfo({ dados, nomePerfil, onNomePerfilChange }) {
  const [modal, setModal] = useState(null) // 'empresa' | 'atendimento' | null

  const empresa = dados?.empresa
  const pessoa = dados?.pessoa
  const contato = dados?.contato
  const atendimento = dados?.atendimento

  return (
    <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 text-sm">
      <div className="flex flex-wrap gap-x-6 gap-y-1">
        {/* Simula o `ProfileName` do WhatsApp: vai em toda mensagem enquanto preenchido. */}
        {onNomePerfilChange && (
          <label className="flex items-center gap-1.5 text-xs text-gray-500">
            <UserCircle size={14} className="shrink-0 text-inforrel-primary" />
            <span className="shrink-0">Nome do perfil (WhatsApp):</span>
            <input
              type="text"
              value={nomePerfil || ''}
              onChange={(e) => onNomePerfilChange(e.target.value)}
              placeholder="vazio = sem nome"
              maxLength={100}
              className="input w-36 py-0.5 px-2 text-xs"
            />
          </label>
        )}

        {/* Empresa (PJ) ou Pessoa (PF) — REQ-010, Fase 4 */}
        <div className="flex items-center gap-1.5">
          {empresa ? (
            <>
              <Building2 size={14} className="text-inforrel-primary" />
              <button
                onClick={() => setModal('empresa')}
                className="text-inforrel-primary hover:underline font-medium"
                title="Ver detalhes da empresa"
              >
                {empresa.cnpj}
                {empresa.fantasia && (
                  <span className="text-gray-600 font-normal"> — {empresa.fantasia}</span>
                )}
              </button>
            </>
          ) : pessoa ? (
            <>
              <Contact size={14} className="text-inforrel-primary" />
              <span className="text-gray-800 font-medium" title="Pessoa física (CPF mascarado)">
                {pessoa.nome || 'Pessoa física'}
                <span className="text-gray-600 font-normal"> — {pessoa.cpf_mascarado}</span>
              </span>
            </>
          ) : (
            <>
              <Building2 size={14} className="text-inforrel-primary" />
              <span className="text-gray-500 italic">Empresa/Pessoa não identificada</span>
            </>
          )}
        </div>

        {/* Contato */}
        <div className="flex items-center gap-1.5">
          <User size={14} className="text-inforrel-primary" />
          {contato?.nome ? (
            <span className="text-gray-800 font-medium">{contato.nome}</span>
          ) : (
            <span className="text-gray-500 italic">Contato não identificado</span>
          )}
        </div>

        {/* Atendimento */}
        <div className="flex items-center gap-1.5">
          <Briefcase size={14} className="text-inforrel-primary" />
          {atendimento ? (
            <button
              onClick={() => setModal('atendimento')}
              className="text-inforrel-primary hover:underline font-medium"
              title="Ver detalhes do atendimento"
            >
              {rotuloAtendimento(atendimento)}
              <span className="text-gray-600 font-normal"> ({atendimento.status})</span>
            </button>
          ) : (
            <span className="text-gray-500 italic">Atendimento não identificado</span>
          )}
          {atendimento?.fase && (
            <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${classesFase(atendimento.fase)}`}>
              {rotuloFase(atendimento.fase)}
            </span>
          )}
          {atendimento && (
            <CamposPendentesBadge
              atendimentoId={atendimento.id}
              temCapturados={(atendimento.campos_capturados || []).length > 0}
            />
          )}
        </div>
      </div>

      {atendimento && <CamposCapturados campos={atendimento.campos_capturados} />}

      {modal === 'empresa' && empresa && (
        <DetalheModal titulo={`Empresa: ${empresa.nome}`} onClose={() => setModal(null)}>
          <EmpresaDetalhes empresaId={empresa.id} />
        </DetalheModal>
      )}

      {modal === 'atendimento' && atendimento && (
        <DetalheModal titulo={rotuloAtendimento(atendimento)} onClose={() => setModal(null)}>
          <AtendimentoDetalhes atendimentoId={atendimento.id} />
        </DetalheModal>
      )}
    </div>
  )
}

export default ConversaInfo
