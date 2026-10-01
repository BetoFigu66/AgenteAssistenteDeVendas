/**
 * Configuração do ESLint 8 (formato legado `.eslintrc`, que é o padrão desta versão).
 * Usa apenas plugins já presentes em devDependencies: react, react-hooks e react-refresh.
 */
module.exports = {
  root: true,
  env: { browser: true, es2021: true },
  // Constante injetada pelo Vite no build (vite.config.js, `define`).
  globals: { __VERSAO_FRONT__: 'readonly' },
  extends: [
    'eslint:recommended',
    'plugin:react/recommended',
    'plugin:react/jsx-runtime',
    'plugin:react-hooks/recommended',
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    ecmaFeatures: { jsx: true },
  },
  settings: { react: { version: 'detect' } },
  plugins: ['react-refresh'],
  rules: {
    // Vite HMR: um módulo deve exportar só componentes para o fast refresh funcionar.
    'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
    // O projeto nunca usou PropTypes (nem TypeScript); manter a regra ligada geraria
    // ~78 erros só por essa convenção. Reavaliar se um dia adotarmos tipagem.
    'react/prop-types': 'off',
  },
  overrides: [
    {
      // Arquivos de configuração rodam no Node, não no browser.
      files: ['*.cjs', '*.config.js'],
      env: { node: true, browser: false },
    },
  ],
}
