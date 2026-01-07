import { useSettings } from '../contexts/SettingsContext';
import { Moon, Sparkles } from 'lucide-react';

/**
 * Theme Toggle Switch - Completely Redesigned
 *
 * Changes from old version:
 * - Removed weird pulsing glow on hover
 * - Cleaner visual design
 * - Better accessibility with clear labels
 * - Desktop-only hover enhancements (no mobile glow issues)
 * - Theme-aware styling that works for both modes
 */
const ThemeToggle = () => {
    const { settings, toggleTheme } = useSettings();
    const isDarkMatter = settings.theme === 'dark-matter';

    return (
        <div className="flex items-center gap-3 select-none">
            {/* Theme Label - Shows current theme */}
            <div className="flex items-center gap-2 text-xs font-medium">
                <div className={`flex items-center gap-1 px-2 py-1 rounded-full border transition-all ${!isDarkMatter
                    ? 'bg-[var(--cv-primary)]/15 text-[var(--cv-primary)] border-[var(--cv-primary)]/30'
                    : 'bg-[var(--cv-bg-elevated)] text-[var(--cv-text-muted)] border-transparent opacity-60'}`}>
                    <Moon size={12} />
                    <span className="hidden sm:inline">Default</span>
                </div>
            </div>

            {/* Toggle Switch */}
            <button
                onClick={toggleTheme}
                className={`
                    relative inline-flex items-center rounded-full
                    transition-all duration-200
                    focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[var(--cv-primary)]
                    h-8 w-16 p-1
                    ${isDarkMatter
                        ? 'bg-gradient-to-r from-purple-600/80 via-indigo-600/80 to-[var(--cv-primary)] border border-purple-500/30'
                        : 'bg-[var(--cv-bg-elevated)] border border-[var(--cv-border)] hover:border-[var(--cv-primary)]/50'}
                `}
                title={isDarkMatter ? 'Switch to Default Theme' : 'Switch to Dark Matter'}
                aria-label="Toggle theme"
                role="switch"
                aria-checked={isDarkMatter}
            >
                {/* Sliding indicator */}
                <span
                    className={`
                        inline-flex items-center justify-center
                        w-6 h-6 rounded-full bg-white
                        transition-transform duration-200 ease-out
                        shadow-lg
                        ${isDarkMatter ? 'translate-x-8' : 'translate-x-0'}
                    `}
                >
                    {isDarkMatter ? (
                        <Sparkles size={14} className="text-purple-600" />
                    ) : (
                        <Moon size={14} className="text-slate-700" />
                    )}
                </span>
            </button>

            {/* Theme Label - Shows current theme */}
            <div className="flex items-center gap-2 text-xs font-medium">
                <div className={`flex items-center gap-1 px-2 py-1 rounded-full border transition-all ${isDarkMatter
                    ? 'bg-[var(--cv-primary)]/15 text-[var(--cv-primary)] border-[var(--cv-primary)]/30'
                    : 'bg-[var(--cv-bg-elevated)] text-[var(--cv-text-muted)] border-transparent opacity-60'}`}>
                    <Sparkles size={12} />
                    <span className="hidden sm:inline">Matter</span>
                </div>
            </div>
        </div>
    );
};

export default ThemeToggle;
