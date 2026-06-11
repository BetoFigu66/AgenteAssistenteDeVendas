import { useEffect, useState } from 'react'
import { api } from '../services/api'

function Campo({ label, valor }) {
  if (valor === null || valor === undefined || valor === '') return null
  return (
    <div className="flex flex-col">
      <span className="text-xs text-gray-500 uppercase tracking-wide">{label}</span>
      <span className="text-sm text-gray-800">{String(valor)}</span>
    </div>
  )
}

function NegociacaoDetalhes({ negociacaoId }) {
  const [negociacao, setNegociacao] = useState(null)
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState(null)

  useEffect(() => {
    let cancelado = false
    setLoading(true)
    api
      .obterNegociacao(negociacaoId)
      .then((data) => {
        if (!cancelado) setNegociacao(data)
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
  }, [negociacaoId])

  if (loading) return <p className="text-gray-500 text-sm">Carregando...</p>
  if (erro) return <p className="text-red-600 text-sm">{erro}</p>
  if (!negociacao) return null

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <Campo label="ID" valor={negociacao.id} />
        <Campo label="Status" valor={negociacao.status} />
        <Campo label="Título" valor={negociacao.titulo} />
        <Campo label="Valor Estimado" valor={negociacao.valor_estimado} />
        <Campo label="Criada em" valor={negociacao.created_at} />
      </div>

      {negociacao.empresa && (
        <div>
          <h3 className="text-sm font-semibold text-inforrel-primary mb-1">Empresa</h3>
          <p className="text-sm text-gray-800">
            {negociacao.empresa.nome} <span className="text-gray-500">({negociacao.empresa.cnpj})</span>
          </p>
        </div>
      )}

      {negociacao.contato && (
        <div>
          <h3 className="text-sm font-semibold text-inforrel-primary mb-1">Contato</h3>
          <p className="text-sm text-gray-800">
            {negociacao.contato.nome || '—'} <span className="text-gray-500">{negociacao.contato.telefone}</span>
          </p>
        </div>
      )}

      {negociacao.itens?.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-inforrel-primary mb-2">Itens</h3>
          <ul className="space-y-1 text-sm">
            {negociacao.itens.map((item) => (
              <li key={item.id} className="text-gray-800">
                Tipo #{item.tipo_produto_id} - Qtd: {item.quantidade}
                {item.produto_id && <span> (Produto #{item.produto_id})</span>}
                {item.observacoes && <span className="text-gray-500"> — {item.observacoes}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {negociacao.informacoes?.length > 0 && (
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
              {negociacao.informacoes.map((info) => (
                <tr key={info.id} className="border-b last:border-0">
                  <td className="py-1 pr-2 font-mono text-xs">{info.chave}</td>
                  <td className="py-1 pr-2">{info.valor || '—'}</td>
                  <td className="py-1 pr-2">{info.origem || '—'}</td>
                  <td className="py-1">{info.pendente ? 'sim' : 'não'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {negociacao.orcamentos?.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-inforrel-primary mb-2">Orçamentos</h3>
          <ul className="space-y-1 text-sm">
            {negociacao.orcamentos.map((o) => (
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

export default NegociacaoDetalhes
