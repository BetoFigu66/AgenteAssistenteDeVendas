import { useEffect, useState } from 'react'
import { Building2, Contact, User, Briefcase, ListChecks, CheckCircle2 } from 'lucide-react'
import DetalheModal from './DetalheModal'
import EmpresaDetalhes from './EmpresaDetalhes'
import AtendimentoDetalhes from './AtendimentoDetalhes'
import { api } from '../services/api'

import { rotuloAtendimento, rotuloFase, classesFase } from '../utils/atendimento'

// Rótulos curtos dos campos do catálogo de qualificação
// (backend/services/conversacao/catalogo_campos.py). O catálogo só tem a pergunta
// inteira, longa demais para um pill; a pergunta vai no title. Chave sem entrada aqui
// cai na própria chave técnica, que é feio mas não esconde informação.
const ROTULO_CAMPO = {
  modelo_produto: 'Modelo',
  software_controle_ponto: 'Software de ponto',
  software_controle_acesso: 'Software de acesso',
  interesse_sistema_nuvem: 'Sistema na nuvem',
  faixa_funcionarios: 'Faixa de pessoas',
  quantidade: 'Quantidade',
  homologado_software: 'Homologação verificada',
}

function rotuloCampo(chave) {
  return ROTULO_CAMPO[chave] || chave
}

function CamposPendentesBadge({ atendimentoId, temCapturados }) {
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

  // REQ-010.7B: nada pendente com algo já coletado é "coleta completa". Sem nenhum
  // campo capturado não há o que comemorar — é só uma conversa que ainda nem começou
  // a qualificar.
  if (campos.length === 0) {
    if (!temCapturados) return null
    return (
      <span className="flex items-center gap-1 px-2 py-0.5 text-xs rounded-full font-medium bg-green-100 text-green-700">
        <CheckCircle2 size={12} />
        Pronto para orçamento
      </span>
    )
  }

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
