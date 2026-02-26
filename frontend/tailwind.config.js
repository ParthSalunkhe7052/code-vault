/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                cv: {
                    bg: 'var(--cv-bg)',
                    'bg-secondary': 'var(--cv-bg-secondary)',
                    'bg-elevated': 'var(--cv-bg-elevated)',
                    card: 'var(--cv-card)',
                    'card-solid': 'var(--cv-card-solid)',
                    text: 'var(--cv-text)',
                    'text-muted': 'var(--cv-text-muted)',
                    'text-dim': 'var(--cv-text-dim)',
                    primary: 'var(--cv-primary)',
                    'primary-hover': 'var(--cv-primary-hover)',
                    'primary-glow': 'var(--cv-primary-glow)',
                    secondary: 'var(--cv-secondary)',
                    'secondary-glow': 'var(--cv-secondary-glow)',
                    accent: 'var(--cv-accent)',
                    'accent-glow': 'var(--cv-accent-glow)',
                    border: 'var(--cv-border)',
                    'border-muted': 'var(--cv-border-muted)',
                    'border-subtle': 'var(--cv-border-subtle)',
                    muted: 'var(--cv-muted)',
                },
                background: {
                    DEFAULT: '#0a0f1a', // Slightly lighter for better contrast
                    secondary: '#111827',
                    card: 'rgba(17, 24, 39, 0.92)',
                    elevated: 'rgba(30, 41, 59, 0.95)',
                },
                primary: {
                    DEFAULT: '#6366f1',
                    light: '#818cf8',
                    dark: '#4f46e5',
                    glow: 'rgba(99, 102, 241, 0.4)',
                },
                secondary: {
                    DEFAULT: '#10b981',
                    light: '#34d399',
                    dark: '#059669',
                    glow: 'rgba(16, 185, 129, 0.3)',
                },
                accent: {
                    DEFAULT: '#06b6d4',
                    blue: '#3b82f6',
                    cyan: '#06b6d4',
                    amber: '#f59e0b',
                    rose: '#f43f5e',
                    glow: 'rgba(6, 182, 212, 0.3)',
                },
                surface: {
                    100: 'rgba(255, 255, 255, 0.03)',
                    200: 'rgba(255, 255, 255, 0.06)',
                    300: 'rgba(255, 255, 255, 0.09)',
                    border: 'rgba(255, 255, 255, 0.12)',
                }
            },
            fontFamily: {
                sans: ['Outfit', 'Inter', 'sans-serif'],
            },
            boxShadow: {
                'cv-primary-glow': '0 4px 14px -3px var(--cv-primary-glow)',
                'cv-primary-active': '0 0 15px -5px var(--cv-primary-glow)',
                'cv-primary-glow-strong': '0 0 6px var(--cv-primary-glow)',
                'cv-secondary-glow': '0 0 12px -2px var(--cv-secondary-glow)',
                'cv-accent-glow': '0 0 12px -2px var(--cv-accent-glow)',
                'cv-amber-active': '0 0 8px -3px rgba(245,158,11,0.3)',
                'cv-amber-strong': '0 0 6px rgba(245,158,11,0.6)',
                'cv-purple-active': '0 0 8px -3px rgba(168,85,247,0.3)',
                'cv-purple-strong': '0 0 6px rgba(168,85,247,0.6)',
                'cv-emerald-pulse': '0 0 10px rgba(16,185,129,0.5)',
            },
            backgroundImage: {
                'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
                'cv-primary-gradient': 'linear-gradient(135deg, var(--cv-primary), var(--cv-primary-hover))',
                'cv-card-gradient': 'linear-gradient(135deg, var(--cv-card), var(--cv-bg-secondary))',
                'cv-glow-gradient': 'linear-gradient(135deg, var(--cv-primary-glow), transparent)',
                'cv-hover-glow': 'linear-gradient(to right, var(--cv-primary-glow), var(--cv-secondary-glow))',
                'cv-bottom-fade': 'linear-gradient(to bottom, transparent, var(--cv-bg) 80%, var(--cv-bg))',
            },
            animation: {
                // Note: fadeIn, slideUp, scaleIn keyframes are defined in index.css to
                // avoid duplication. Only non-CSS-defined animations go here.
                'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
            },
        },
    },
    plugins: [],
}
