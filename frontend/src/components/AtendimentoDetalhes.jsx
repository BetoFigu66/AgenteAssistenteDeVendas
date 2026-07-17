import { useEffect, useState } from 'react'
import { AlertTriangle } from 'lucide-react'
import { api } from '../services/api'
import { formatDatetimeBRT } from '../utils/datetime'
import {
  rotuloAtendimento,
  numeroAtendimentoExibicao,
  rotuloFase,
  classesFase,
  labelMotivoEscalonamento,
} from '../utils/atendimento'

function Campo({ label, valor }) {
  if (valor === null || valor === undefined || valor === '') return null
  return (
    <div className="flex flex-col">
      <span className="text-xs text-gray-500 uppercase tracking-wide">{label}</span>
      <span className="text-sm text-gray-800">{String(valor)}</span>
    </div>
  )
}

// Rótulos amigáveis para as chaves técnicas mais comuns de AtendimentoInfo (H2) —
// chaves sem entrada aqui caem no fallback (a própria chave técnica).
const LABELS_INFO = {
  nome_contato: 'Nome',
  email_contato: 'E-mail',
  tipos_produto: 'Tipo de produto',
  quantidades: 'Quantidades',
  modelo_produto: 'Modelo',
  software_controle_ponto: 'Software de ponto',
  tipo_leitor_mencionado: 'Tipo de leitor mencionado',
  faixa_funcionarios: 'Faixa de funcionários',
  resumo_finalizando_apresentado: 'Resumo apresentado',
  modelo_tentativas_falhas: 'Tentativas de modelo sem sucesso',
}

function rotuloInfo(chave) {
  return LABELS_INFO[chave] || chave
}

function AtendimentoDetalhes({ atendimentoId }) {
  const [atendimento, setAtendimento] = useState(null)
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState(null)

  useEffect(() => {
    let cancelado = false
    setLoading(true)
    api
      .obterAtendimento(atendimentoId)
      .then((data) => {
        if (!cancelado) setAtendimento(data)
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
  }, [atendimentoId])

  if (loading) return <p className="text-gray-500 text-sm">Carregando...</p>
  if (erro) return <p className="text-red-600 text-sm">{erro}</p>
  if (!atendimento) return null

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <Campo label="Atendimento" valor={rotuloAtendimento(atendimento)} />
        <Campo label="ID interno" valor={atendimento.id} />
        <Campo label="Nº cliente" valor={numeroAtendimentoExibicao(atendimento)} />
        <Campo label="Status" valor={atendimento.status} />
        {atendimento.fase && (
          <div className="flex flex-col">
            <span className="text-xs text-gray-500 uppercase tracking-wide">Fase</span>
            <span
              className={`w-fit px-2 py-0.5 text-xs rounded-full font-semibold ${classesFase(atendimento.fase)}`}
            >
              {rotuloFase(atendimento.fase)}
            </span>
          </div>
        )}
        <Campo label="Título" valor={atendimento.titulo} />
        <Campo label="Valor Estimado" valor={atendimento.valor_estimado} />
        <Campo label="Criado em" valor={formatDatetimeBRT(atendimento.created_at)} />
        <Campo label="Última mensagem" valor={formatDatetimeBRT(atendimento.ultima_mensagem_at)} />
      </div>

      {atendimento.empresa && (
        <div>
          <h3 className="text-sm font-semibold text-inforrel-primary mb-1">Empresa</h3>
          <p className="text-sm text-gray-800">
            {atendimento.empresa.nome}{' '}
            <span className="text-gray-500">({atendimento.empresa.cnpj})</span>
          </p>
        </div>
      )}

      {atendimento.contato && (
        <div>
          <h3 className="text-sm font-semibold text-inforrel-primary mb-1">Contato</h3>
          <p className="text-sm text-gray-800">
            {atendimento.contato.nome || '—'}{' '}
            <span className="text-gray-500">{atendimento.contato.telefone}</span>
          </p>
        </div>
      )}

      {atendimento.motivo_escalonamento && (
        <div className="p-3 bg-orange-50 border border-orange-200 rounded-md">
          <h3 className="text-sm font-semibold text-orange-800 mb-1 flex items-center gap-1.5">
            <AlertTriangle size={14} /> Escalonamento (REQ-004)
          </h3>
          <p className="text-sm text-gray-800">
            {labelMotivoEscalonamento(atendimento.motivo_escalonamento)}
          </p>
          <p className="text-xs text-gray-500 mt-1">
            {formatDatetimeBRT(atendimento.escalado_em)}
            {atendimento.escalado_por && ` · por ${atendimento.escalado_por}`}
          </p>
          {atendimento.resumo_escalonamento && (
            <pre className="text-xs text-gray-700 bg-white border border-orange-100 rounded p-2 mt-2 whitespace-pre-wrap font-sans">
              {atendimento.resumo_escalonamento}
            </pre>
          )}
        </div>
      )}

      {atendimento.itens?.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-inforrel-primary mb-2">Itens</h3>
          <ul className="space-y-1 text-sm">
            {atendimento.itens.map((item) => (
              <li key={item.id} className="text-gray-800">
                Produto #{item.produto_id} - Qtd: {item.quantidade}
                {item.modelo_id && <span> (Modelo #{item.modelo_id})</span>}
                {item.observacoes && <span className="text-gray-500"> — {item.observacoes}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {atendimento.informacoes?.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-inforrel-primary mb-2">Informações coletadas</h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b">
                <th className="py-1 pr-2">Chave</th>
                <th className="py-1 pr-2">Valor</th>
                <th className="py-1 pr-2">Origem</th>
                <th className="py-1">Pendente</th>
              </tr>
            </thead>
            <tbody>
              {atendimento.informacoes.map((info) => (
                <tr key={info.id} className="border-b last:border-0">
                  <td className="py-1 pr-2">{rotuloInfo(info.chave)}</td>
                  <td className="py-1 pr-2">{info.valor || '—'}</td>
                  <td className="py-1 pr-2">{info.origem || '—'}</td>
                  <td className="py-1">
                    <span
                      className={`px-1.5 py-0.5 text-xs rounded ${
                        info.pendente ? 'bg-yellow-200 text-yellow-800' : 'bg-green-200 text-green-800'
                      }`}
                    >
                      {info.pendente ? 'Pendente' : 'Capturado'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {atendimento.orcamentos?.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-inforrel-primary mb-2">Orçamentos</h3>
          <ul className="space-y-1 text-sm">
            {atendimento.orcamentos.map((o) => (
              <li key={o.id} className="text-gray-800">
                #{o.id} - {o.status} - Total: {o.valor_total || '—'}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

export default AtendimentoDetalhes
