import js from '@eslint/js';
import globals from 'globals';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';

export default [
    { ignores: ['dist', 'node_modules', '**/*.test.js', '**/*.spec.js'] },
    {
        files: ['**/*.{js,jsx}'],
        languageOptions: {
            ecmaVersion: 2020,
            globals: globals.browser,
            parserOptions: {
                ecmaVersion: 'latest',
                ecmaFeatures: { jsx: true },
                sourceType: 'module',
            },
        },
        plugins: {
            'react-hooks': reactHooks,
            'react-refresh': reactRefresh,
        },
        rules: {
            ...js.configs.recommended.rules,
            ...reactHooks.configs.recommended.rules,
            'react-refresh/only-export-components': [
                'warn',
                { allowConstantExport: true },
            ],
            // Relaxed rules for production use - false positives are common in React
            'no-unused-vars': ['warn', {
                'argsIgnorePattern': '^_',
                'varsIgnorePattern': '^_',
                'caughtErrorsIgnorePattern': '^_'
            }],
            'no-console': 'off',
            // Keep as warnings, not errors
            'no-undef': 'warn',
            'no-empty': 'warn',
            'no-constant-condition': 'warn',
            // Security: These should be warnings but not break builds
            'no-prototype-builtins': 'warn',
            'no-async-promise-executor': 'warn',
            'no-misleading-character-class': 'warn',
            'no-regex-spaces': 'warn',
        },
    },
];
