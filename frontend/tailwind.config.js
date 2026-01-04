/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
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
            backgroundImage: {
                'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
            },
            animation: {
                'fade-in': 'fadeIn 0.3s ease-out',
                'scale-in': 'scaleIn 0.2s ease-out',
                'slide-up': 'slideUp 0.3s ease-out',
                'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
            },
            keyframes: {
                fadeIn: {
                    '0%': { opacity: '0', transform: 'translateY(8px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
                scaleIn: {
                    '0%': { opacity: '0', transform: 'scale(0.95)' },
                    '100%': { opacity: '1', transform: 'scale(1)' },
                },
                slideUp: {
                    '0%': { opacity: '0', transform: 'translateY(100%)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
            },
        },
    },
    plugins: [],
}
