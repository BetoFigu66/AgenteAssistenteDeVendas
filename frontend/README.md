# Frontend - Assistente de Vendas

Frontend React + Vite + TailwindCSS para o Assistente de Vendas Inforrel.

## Tecnologias

- **React 18** - Biblioteca UI
- **Vite** - Build tool
- **TailwindCSS** - Estilização
- **Lucide React** - Ícones

## Estrutura

```
frontend/
├── src/
│   ├── components/     # Componentes React
│   │   ├── Header.jsx
│   │   ├── Footer.jsx
│   │   ├── PhonePanel.jsx
│   │   ├── ChatArea.jsx
│   │   └── Message.jsx
│   ├── services/       # Serviços de API
│   │   └── api.js
│   ├── App.jsx         # Componente principal
│   ├── main.jsx        # Entry point
│   └── index.css       # Estilos globais
├── public/             # Assets estáticos
│   └── images/
├── index.html          # HTML template
├── package.json        # Dependências
├── vite.config.js      # Configuração Vite
├── tailwind.config.js  # Configuração Tailwind
├── Dockerfile          # Build de produção
└── nginx.conf          # Configuração nginx
```

## Desenvolvimento Local

### Pré-requisitos

- Node.js 18+ 
- npm ou yarn

### Instalação

```bash
cd frontend
npm install
```

### Executar em desenvolvimento

```bash
npm run dev
```

Acesse: http://localhost:5173

> O Vite faz proxy automático das requisições `/api/*` para o backend em `localhost:8000`

### Build de produção

```bash
npm run build
```

Os arquivos serão gerados em `dist/`.

## Docker

### Build da imagem

```bash
docker build -t assistente-vendas-frontend .
```

### Executar container

```bash
docker run -p 3000:80 assistente-vendas-frontend
```

## Variáveis de Ambiente

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `VITE_API_URL` | URL base da API | `` (usa proxy) |

## Paleta de Cores (Inforrel)

| Cor | Hex | Uso |
|-----|-----|-----|
| Primary | `#1B4F72` | Títulos, botões principais |
| Secondary | `#2E86AB` | Hover, destaques |
| Accent | `#F39C12` | Badges, alertas |
| Dark | `#1A252F` | Header, footer |
| Light | `#F8F9FA` | Background |

## Scripts

| Comando | Descrição |
|---------|-----------|
| `npm run dev` | Inicia servidor de desenvolvimento |
| `npm run build` | Build de produção |
| `npm run preview` | Preview do build |
| `npm run lint` | Verifica código com ESLint |
