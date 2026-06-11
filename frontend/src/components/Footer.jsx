function Footer() {
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
            <p>POC - Assistente de Vendas v0.1.0</p>
            <p>© {new Date().getFullYear()} Todos os direitos reservados</p>
          </div>
        </div>
      </div>
    </footer>
  )
}

export default Footer
