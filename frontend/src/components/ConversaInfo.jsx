import { useEffect, useState } from 'react'
import { Building2, Contact, User, Briefcase, ListChecks } from 'lucide-react'
import DetalheModal from './DetalheModal'
import EmpresaDetalhes from './EmpresaDetalhes'
import AtendimentoDetalhes from './AtendimentoDetalhes'
import { api } from '../services/api'

import { numeroAtendimentoExibicao, rotuloAtendimento, rotuloFase, classesFase } from '../utils/atendimento'

function CamposPendentesBadge({ atendimentoId }) {
  const [campos, setCampos] = useState([])

  useEffect(() => {
    let cancelado = false
    if (!atendimentoId) {
      setCampos([])
      return
    }
    api
      .obterCamposPendentes(atendimentoId)
      .then((data) => !cancelado && setCampos(data.campos_pendentes || []))
      .catch(() => !cancelado && setCampos([]))
    return () => {
      cancelado = true
    }
  }, [atendimentoId])

  if (campos.length === 0) return null

  return (
    <span
      className="flex items-center gap-1 px-2 py-0.5 text-xs rounded-full font-medium bg-amber-100 text-amber-700 cursor-help"
      title={`Faltam: ${campos.map((c) => c.pergunta).join(' · ')}`}
    >
      <ListChecks size={12} />
      {campos.length} pendente{campos.length > 1 ? 's' : ''}
    </span>
  )
}

function ConversaInfo({ dados }) {
  const [modal, setModal] = useState(null) // 'empresa' | 'atendimento' | null

  const empresa = dados?.empresa
  const pessoa = dados?.pessoa
  const contato = dados?.contato
  const atendimento = dados?.atendimento

  return (
    <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 text-sm">
      <div className="flex flex-wrap gap-x-6 gap-y-1">
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
          {atendimento && <CamposPendentesBadge atendimentoId={atendimento.id} />}
        </div>
      </div>

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
