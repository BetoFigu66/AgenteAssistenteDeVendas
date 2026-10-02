import { useState, useEffect, useCallback } from 'react'
import {
  RefreshCw, Edit2, Trash2, Plus, Search, Filter, LifeBuoy, AlertTriangle, Wand2,
} from 'lucide-react'
import { api } from '../services/api'
import DetalheModal from './DetalheModal'
import BotaoAjuda from './BotaoAjuda'
import { formatDatetimeBRT } from '../utils/datetime'

const CHAVE_GLOBAL = '__global__'

/**
 * Administracao do conteudo de ajuda do painel (aba "Base de Ajuda").
 *
 * Base separada da Base Q&A de proposito: aqui e a ajuda que o *operador* le nas telas;
 * la sao as respostas que o *cliente* recebe no WhatsApp. Misturar as duas arriscaria
 * mandar instrucao de painel para um cliente.
 */
function AjudaBasePage() {
  const [conteudos, setConteudos] = useState([])
  const [total, setTotal] = useState(0)
  const [contextos, setContextos] = useState([])
  const [carregando, setCarregando] = useState(false)
  const [erro, setErro] = useState(null)

  const [filtroContexto, setFiltroContexto] = useState('')
  const [filtroAtivo, setFiltroAtivo] = useState('true')
  const [busca, setBusca] = useState('')
  const [buscaAplicada, setBuscaAplicada] = useState('')

  const [editando, setEditando] = useState(null)
  const [criando, setCriando] = useState(false)
  const [form, setForm] = useState({ pergunta: '', resposta: '', contexto_chave: '', prioridade: 0 })
  const [salvando, setSalvando] = useState(false)

  const [reindexando, setReindexando] = useState(false)
  const [lacunas, setLacunas] = useState([])

  const carregar = useCallback(async () => {
    setCarregando(true)
    setErro(null)
    try {
      const data = await api.listarConteudosAjuda({
        contexto: filtroContexto,
        ativo: filtroAtivo === '' ? null : filtroAtivo === 'true',
        q: buscaAplicada,
        limit: 200,
      })
      setConteudos(data.conteudos || [])
      setTotal(data.total || 0)
    } catch (e) {
      setErro('Erro ao carregar conteúdos de ajuda: ' + e.message)
    } finally {
      setCarregando(false)
    }
  }, [filtroContexto, filtroAtivo, buscaAplicada])

  useEffect(() => {
    carregar()
  }, [carregar])

  useEffect(() => {
    api.listarContextosAjuda()
      .then((d) => setContextos(d.contextos || []))
      .catch(() => setContextos([]))
    // Lacunas: o que os usuários perguntaram e a base não soube responder.
    // É a pauta de conteúdo desta tela, por isso fica visível o tempo todo.
    api.listarConsultasAjuda({ encontrou: false, limit: 200 })
      .then((d) => setLacunas(d.agrupadas || []))
      .catch(() => setLacunas([]))
  }, [])

  const recarregarLacunas = () => {
    api.listarConsultasAjuda({ encontrou: false, limit: 200 })
      .then((d) => setLacunas(d.agrupadas || []))
      .catch(() => {})
  }

  const abrirCriacao = (perguntaInicial = '', contextoInicial = '') => {
    setForm({
      pergunta: perguntaInicial,
      resposta: '',
      contexto_chave: contextoInicial,
      prioridade: 0,
    })
    setCriando(true)
  }

  const abrirEdicao = (item) => {
    setForm({
      pergunta: item.pergunta || '',
      resposta: item.resposta || '',
      contexto_chave: item.contexto_chave || '',
      prioridade: item.prioridade ?? 0,
    })
    setEditando(item)
  }

  const fecharModal = () => {
    setCriando(false)
    setEditando(null)
    setForm({ pergunta: '', resposta: '', contexto_chave: '', prioridade: 0 })
  }

  const salvar = async () => {
    if (!form.pergunta.trim() || !form.resposta.trim() || salvando) return
    setSalvando(true)
    try {
      const payload = {
        pergunta: form.pergunta.trim(),
        resposta: form.resposta.trim(),
        contexto_chave: form.contexto_chave || null,
        prioridade: Number(form.prioridade) || 0,
      }
      if (editando) {
        await api.atualizarConteudoAjuda(editando.id, payload)
      } else {
        await api.criarConteudoAjuda(payload)
      }
      fecharModal()
      carregar()
      recarregarLacunas()
    } catch (e) {
      alert('Erro ao salvar: ' + e.message)
    } finally {
      setSalvando(false)
    }
  }

  const desativar = async (item) => {
    if (!confirm(`Desativar "${item.pergunta.slice(0, 60)}"?`)) return
    try {
      await api.desativarConteudoAjuda(item.id)
      carregar()
    } catch (e) {
      alert('Erro ao desativar: ' + e.message)
    }
  }

  const reindexar = async () => {
    setReindexando(true)
    try {
      const r = await api.reindexarConteudosAjuda()
      alert(
        `Reindexação: ${r.indexados} conteúdo(s) com busca semântica gerada` +
        (r.falhas ? `, ${r.falhas} falha(s).` : '.'),
      )
      carregar()
    } catch (e) {
      alert('Erro ao reindexar: ' + e.message)
    } finally {
      setReindexando(false)
    }
  }

  const semEmbedding = conteudos.filter((c) => c.ativo && !c.tem_embedding).length

  return (
    <div className="container mx-auto max-w-7xl px-4 py-6">
      <div className="mb-4 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <LifeBuoy size={20} className="text-inforrel-primary" />
            <h2 className="text-lg font-semibold text-inforrel-primary">Base de Ajuda</h2>
            <BotaoAjuda contexto="ajuda-base" />
            <span className="text-sm text-gray-500">{total} conteúdo(s)</span>
            {semEmbedding > 0 && (
              <span
                title="Sem busca semântica: só são encontrados por palavra-chave"
                className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800"
              >
                {semEmbedding} sem índice semântico
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {semEmbedding > 0 && (
              <button
                onClick={reindexar}
                disabled={reindexando}
                title="Gera a busca semântica dos conteúdos que ficaram sem"
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 transition hover:text-inforrel-primary disabled:opacity-50"
              >
                <Wand2 size={15} className={reindexando ? 'animate-pulse' : ''} />
                Reindexar
              </button>
            )}
            <button
              onClick={carregar}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 transition hover:text-inforrel-primary"
            >
              <RefreshCw size={15} className={carregando ? 'animate-spin' : ''} />
              Atualizar
            </button>
            <button
              onClick={() => abrirCriacao()}
              className="flex items-center gap-1.5 rounded-md bg-inforrel-primary px-3 py-1.5 text-sm text-white transition hover:bg-inforrel-secondary"
            >
              <Plus size={15} />
              Novo conteúdo
            </button>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Filter size={14} className="text-gray-400" />
          <select
            value={filtroContexto}
            onChange={(e) => setFiltroContexto(e.target.value)}
            className="rounded border border-gray-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-inforrel-primary"
          >
            <option value="">Todas as telas</option>
            <option value={CHAVE_GLOBAL}>Ajuda global (toda tela)</option>
            {contextos.map((c) => (
              <option key={c.chave} value={c.chave}>
                {c.rotulo} ({c.total_conteudos})
              </option>
            ))}
          </select>
          <select
            value={filtroAtivo}
            onChange={(e) => setFiltroAtivo(e.target.value)}
            className="rounded border border-gray-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-inforrel-primary"
          >
            <option value="true">Ativos</option>
            <option value="false">Inativos</option>
            <option value="">Todos</option>
          </select>
          <div className="relative">
            <Search size={14} className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && setBuscaAplicada(busca)}
              onBlur={() => setBuscaAplicada(busca)}
              placeholder="Buscar no texto..."
              className="w-52 rounded border border-gray-200 py-1.5 pl-7 pr-3 text-sm focus:outline-none focus:ring-1 focus:ring-inforrel-primary"
            />
          </div>
        </div>
      </div>

      {/* Lacunas: pauta de conteúdo vinda do uso real */}
      {lacunas.length > 0 && (
        <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-3">
          <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-amber-800">
            <AlertTriangle size={13} />
            Perguntas sem resposta ({lacunas.length})
          </h3>
          <p className="mb-2 text-xs text-amber-700">
            O que os usuários procuraram e a base não soube responder. Clique para criar o conteúdo.
          </p>
          <div className="flex flex-wrap gap-1.5">
            {lacunas.slice(0, 12).map((l, i) => (
              <button
                key={`${l.pergunta}-${l.contexto}-${i}`}
                onClick={() => abrirCriacao(l.pergunta, l.contexto || '')}
                title={`Criar conteúdo para esta pergunta${l.contexto ? ` (tela: ${l.contexto})` : ''}`}
                className="rounded-full border border-amber-300 bg-white px-2.5 py-1 text-xs text-amber-900 transition hover:border-amber-500"
              >
                {l.pergunta}
                {l.vezes > 1 && <span className="ml-1 font-semibold">{l.vezes}×</span>}
              </button>
            ))}
          </div>
        </div>
      )}

      {erro && (
        <div className="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{erro}</div>
      )}

      <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
        {carregando ? (
          <div className="p-12 text-center text-gray-500">
            <RefreshCw size={24} className="mx-auto mb-2 animate-spin" />
            Carregando...
          </div>
        ) : conteudos.length === 0 ? (
          <div className="p-12 text-center text-gray-400">
            <LifeBuoy size={32} className="mx-auto mb-2 opacity-40" />
            <p>Nenhum conteúdo de ajuda com os filtros selecionados.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-gray-200 bg-gray-50">
                <tr>
                  <th className="w-12 px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">#</th>
                  <th className="w-40 px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Tela</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Pergunta</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Resposta</th>
                  <th className="w-20 px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Prior.</th>
                  <th className="w-32 px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Atualizado</th>
                  <th className="w-20 px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {conteudos.map((c) => (
                  <tr key={c.id} className={`transition hover:bg-gray-50 ${!c.ativo ? 'opacity-50' : ''}`}>
                    <td className="px-4 py-3 text-xs text-gray-400">{c.id}</td>
                    <td className="px-4 py-3">
                      {c.contexto_chave ? (
                        <span className="rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">
                          {c.contexto_chave}
                        </span>
                      ) : (
                        <span className="rounded bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                          global
                        </span>
                      )}
                    </td>
                    <td className="max-w-xs px-4 py-3 text-gray-800">
                      <p className="line-clamp-2 leading-snug">{c.pergunta}</p>
                      {!c.tem_embedding && c.ativo && (
                        <span
                          title="Sem busca semântica: só é encontrado por palavra-chave"
                          className="text-xs text-amber-600"
                        >
                          sem índice semântico
                        </span>
                      )}
                    </td>
                    <td className="max-w-sm px-4 py-3 text-gray-600">
                      <p className="line-clamp-2 text-xs leading-snug">{c.resposta}</p>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">{c.prioridade}</td>
                    <td className="whitespace-nowrap px-4 py-3 text-xs text-gray-500">
                      {formatDatetimeBRT(c.updated_at)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => abrirEdicao(c)}
                          title="Editar"
                          className="rounded p-1.5 text-gray-500 transition hover:bg-gray-100"
                        >
                          <Edit2 size={14} />
                        </button>
                        {c.ativo && (
                          <button
                            onClick={() => desativar(c)}
                            title="Desativar"
                            className="rounded p-1.5 text-red-400 transition hover:bg-red-50"
                          >
                            <Trash2 size={14} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {(criando || editando) && (
        <DetalheModal
          titulo={editando ? `Editar conteúdo #${editando.id}` : 'Novo conteúdo de ajuda'}
          onClose={fecharModal}
        >
          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Pergunta, como o usuário faria
              </label>
              <textarea
                value={form.pergunta}
                onChange={(e) => setForm({ ...form, pergunta: e.target.value })}
                rows={2}
                placeholder="Como aprovo uma mensagem pendente?"
                className="w-full resize-none rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-inforrel-primary"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Resposta <span className="font-normal text-gray-400">(aceita Markdown)</span>
              </label>
              <textarea
                value={form.resposta}
                onChange={(e) => setForm({ ...form, resposta: e.target.value })}
                rows={6}
                placeholder="Clique em **Aprovar** no cartão da mensagem..."
                className="w-full resize-none rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-inforrel-primary"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Tela</label>
                <select
                  value={form.contexto_chave}
                  onChange={(e) => setForm({ ...form, contexto_chave: e.target.value })}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-inforrel-primary"
                >
                  <option value="">Global — vale em toda tela</option>
                  {contextos.map((c) => (
                    <option key={c.chave} value={c.chave}>{c.rotulo}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Prioridade <span className="font-normal text-gray-400">(ordem nas sugestões)</span>
                </label>
                <input
                  type="number"
                  value={form.prioridade}
                  onChange={(e) => setForm({ ...form, prioridade: e.target.value })}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-inforrel-primary"
                />
              </div>
            </div>
            <p className="rounded border border-gray-200 bg-gray-50 p-2 text-xs text-gray-500">
              Conteúdo desta base aparece só para a equipe, no botão de ajuda das telas.
              Nunca é enviado a clientes — para isso existe a <strong>Base Q&A</strong>.
            </p>
            <div className="flex justify-end gap-2">
              <button onClick={fecharModal} className="px-4 py-2 text-gray-600 transition hover:text-gray-800">
                Cancelar
              </button>
              <button
                onClick={salvar}
                disabled={!form.pergunta.trim() || !form.resposta.trim() || salvando}
                className="flex items-center gap-2 rounded-md bg-inforrel-primary px-4 py-2 text-white transition hover:bg-inforrel-secondary disabled:opacity-50"
              >
                {salvando ? <><RefreshCw size={15} className="animate-spin" />Salvando...</> : 'Salvar'}
              </button>
            </div>
          </div>
        </DetalheModal>
      )}
    </div>
  )
}

export default AjudaBasePage
