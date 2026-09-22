import typography from '@tailwindcss/typography'

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        inforrel: {
          primary: '#1B4F72',
          secondary: '#2E86AB',
          accent: '#F39C12',
          dark: '#1A252F',
          light: '#F8F9FA',
        }
      },
      fontFamily: {
        sans: ['Open Sans', 'sans-serif'],
        heading: ['Montserrat', 'sans-serif'],
      },
      // Usado pelos textos de ajuda por tela (src/ajuda/*.md) renderizados
      // com `prose`: alinha titulos e links as cores da identidade Inforrel.
      typography: {
        DEFAULT: {
          css: {
            '--tw-prose-headings': '#1B4F72',
            '--tw-prose-links': '#2E86AB',
          },
        },
      },
    },
  },
  plugins: [typography],
}
