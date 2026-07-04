import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  // Type-checked linting (le « clippy » du front) sur le code source uniquement :
  // no-floating-promises / no-misused-promises = l'équivalent #[must_use] pour l'async.
  {
    files: ['src/**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommendedTypeChecked,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
      parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname },
    },
    rules: {
      // Convention : un argument préfixé `_` est intentionnellement inutilisé
      // (ex. mocks qui doivent respecter la signature de l'API réelle).
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
      // Les handlers d'événements async sur des attributs JSX (onClick={async …})
      // sont sûrs (React ignore la valeur de retour) — pas de `void` cosmétique.
      // Les promesses flottantes dans du code impératif restent, elles, une erreur.
      '@typescript-eslint/no-misused-promises': [
        'error',
        { checksVoidReturn: { attributes: false } },
      ],
    },
  },
  {
    // shadcn-style primitives export their cva variant maps alongside the
    // component; that's intentional and doesn't break Fast Refresh in practice.
    files: ['src/components/ui/**/*.{ts,tsx}'],
    rules: {
      'react-refresh/only-export-components': 'off',
    },
  },
  // Fichiers de config (hors projet TS) : pas de linting typé.
  {
    files: ['**/*.{js,mjs,cjs}'],
    extends: [tseslint.configs.disableTypeChecked],
  },
])
