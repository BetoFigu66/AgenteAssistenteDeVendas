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

function EmpresaDetalhes({ empresaId }) {
  const [empresa, setEmpresa] = useState(null)
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState(null)

  useEffect(() => {
    let cancelado = false
    setLoading(true)
    api
      .obterEmpresa(empresaId)
      .then((data) => {
        if (!cancelado) setEmpresa(data)
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
  }, [empresaId])

  if (loading) return <p className="text-gray-500 text-sm">Carregando...</p>
  if (erro) return <p className="text-red-600 text-sm">{erro}</p>
  if (!empresa) return null

  const endereco = [
    empresa.logradouro,
    empresa.numero,
    empresa.complemento,
    empresa.bairro,
    empresa.municipio && empresa.uf ? `${empresa.municipio}/${empresa.uf}` : empresa.municipio,
    empresa.cep,
  ]
    .filter(Boolean)
    .join(', ')

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <Campo label="Razão Social" valor={empresa.nome} />
        <Campo label="Nome Fantasia" valor={empresa.fantasia} />
        <Campo label="CNPJ" valor={empresa.cnpj} />
        <Campo label="Tipo" valor={empresa.tipo} />
        <Campo label="Porte" valor={empresa.porte} />
        <Campo label="Natureza Jurídica" valor={empresa.natureza_juridica} />
        <Campo label="Capital Social" valor={empresa.capital_social} />
        <Campo label="Abertura" valor={empresa.abertura} />
        <Campo label="Situação" valor={empresa.situacao} />
        <Campo label="Data Situação" valor={empresa.data_situacao} />
        <Campo label="Email" valor={empresa.email} />
        <Campo label="Telefone" valor={empresa.telefone} />
      </div>

      {endereco && (
        <div>
          <h3 className="text-sm font-semibold text-inforrel-primary mb-1">Endereço</h3>
          <p className="text-sm text-gray-800">{endereco}</p>
        </div>
      )}

      {empresa.atividades?.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-inforrel-primary mb-2">Atividades (CNAE)</h3>
          <ul className="space-y-1 text-sm">
            {empresa.atividades.map((a, i) => (
              <li key={i} className="text-gray-800">
                <span className="font-mono text-xs text-gray-600">{a.codigo}</span>
                {a.is_principal && (
                  <span className="ml-2 text-xs bg-inforrel-accent text-white px-1.5 py-0.5 rounded">
                    principal
                  </span>
                )}
                <div className="text-gray-700">{a.descricao}</div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {empresa.socios?.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-inforrel-primary mb-2">Sócios</h3>
          <ul className="space-y-1 text-sm">
            {empresa.socios.map((s, i) => (
              <li key={i} className="text-gray-800">
                <span className="font-medium">{s.nome}</span>
                {s.qualificacao && (
                  <span className="text-gray-500 ml-2">({s.qualificacao})</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

export default EmpresaDetalhes
