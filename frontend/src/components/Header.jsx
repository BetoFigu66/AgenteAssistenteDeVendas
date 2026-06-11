import { Phone, Mail } from 'lucide-react'

function Header() {
  return (
    <>
      {/* Top Bar */}
      <div className="bg-inforrel-dark text-white text-sm py-2">
        <div className="container mx-auto px-4 max-w-5xl flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Phone size={14} />
            <span>(19) 3772-5050</span>
          </div>
          <div className="flex items-center gap-2">
            <Mail size={14} />
            <span>contato@inforrel.com.br</span>
          </div>
        </div>
      </div>

      {/* Header */}
      <header className="bg-white shadow-md">
        <div className="container mx-auto px-4 py-4 max-w-5xl flex items-center justify-between">
          <div className="flex items-center gap-4">
            <img 
              src="/images/inforrel01.jpg" 
              alt="Inforrel" 
              className="h-14 w-auto"
              onError={(e) => {
                e.target.style.display = 'none'
              }}
            />
            <div className="hidden md:block">
              <h1 className="text-xl font-bold text-inforrel-primary font-heading">
                Assistente de Vendas
              </h1>
              <p className="text-sm text-gray-500">Controle de Ponto e Acesso</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="hidden sm:inline text-sm text-gray-600">
              Simulador de Atendimento
            </span>
            <span className="bg-inforrel-accent text-white text-xs px-3 py-1 rounded-full font-medium">
              POC
            </span>
          </div>
        </div>
      </header>
    </>
  )
}

export default Header
