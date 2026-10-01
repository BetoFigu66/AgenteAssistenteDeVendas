import { useEffect, useState } from 'react'
import { api } from '../services/api'

// Injetada pelo Vite no build (vite.config.js, lida de frontend/VERSAO).
const VERSAO_FRONT = __VERSAO_FRONT__

function Footer() {
  const [versaoBack, setVersaoBack] = useState('...')

  useEffect(() => {
    api.obterVersaoBackend()
      .then(setVersaoBack)
      .catch(() => setVersaoBack('indisponível'))
  }, [])

  return (
    <footer className="bg-inforrel-dark text-white py-6 mt-auto">
      <div className="container mx-auto px-4 max-w-5xl">
        <div className="flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="text-center md:text-left">
            <p className="font-semibold font-heading">Inforrel</p>
            <p className="text-sm text-gray-400">
              Controle de Ponto e Acesso em Campinas
            </p>
          </div>
          <div className="text-center md:text-right text-sm text-gray-400">
            <p>POC - Assistente de Vendas</p>
            <p title="Data e hora da última mudança de cada lado">
              Front {VERSAO_FRONT} · Back {versaoBack}
            </p>
            <p>© {new Date().getFullYear()} Todos os direitos reservados</p>
          </div>
        </div>
      </div>
    </footer>
  )
}

export default Footer
