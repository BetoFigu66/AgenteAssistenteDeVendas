import { useState } from 'react'
import { Building2, User, Briefcase } from 'lucide-react'
import DetalheModal from './DetalheModal'
import EmpresaDetalhes from './EmpresaDetalhes'
import NegociacaoDetalhes from './NegociacaoDetalhes'

function ConversaInfo({ dados }) {
  const [modal, setModal] = useState(null) // 'empresa' | 'negociacao' | null

  const empresa = dados?.empresa
  const contato = dados?.contato
  const atendimento = dados?.atendimento ?? dados?.negociacao

  return (
    <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 text-sm">
      <div className="flex flex-wrap gap-x-6 gap-y-1">
        {/* Empresa */}
        <div className="flex items-center gap-1.5">
          <Building2 size={14} className="text-inforrel-primary" />
          {empresa ? (
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
          ) : (
            <span className="text-gray-500 italic">Empresa não identificada</span>
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

        {/* Negociação */}
        <div className="flex items-center gap-1.5">
          <Briefcase size={14} className="text-inforrel-primary" />
          {atendimento ? (
            <button
              onClick={() => setModal('negociacao')}
              className="text-inforrel-primary hover:underline font-medium"
              title="Ver detalhes da negociação"
            >
              Negociação #{atendimento.id}
              <span className="text-gray-600 font-normal"> ({atendimento.status})</span>
            </button>
          ) : (
            <span className="text-gray-500 italic">Negociação não identificada</span>
          )}
        </div>
      </div>

      {modal === 'empresa' && empresa && (
        <DetalheModal titulo={`Empresa: ${empresa.nome}`} onClose={() => setModal(null)}>
          <EmpresaDetalhes empresaId={empresa.id} />
        </DetalheModal>
      )}

      {modal === 'negociacao' && atendimento && (
        <DetalheModal titulo={`Negociação #${atendimento.id}`} onClose={() => setModal(null)}>
          <NegociacaoDetalhes negociacaoId={atendimento.id} />
        </DetalheModal>
      )}
    </div>
  )
}

export default ConversaInfo
