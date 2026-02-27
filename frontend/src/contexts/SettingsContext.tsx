import React, { createContext, useState, useContext, useEffect, useCallback, useMemo } from 'react';

/**
 * Settings Context - Global and per-project settings management
 */

export interface Settings {
    theme: string;
    autoUpdate: boolean;
    defaultShowConsole: boolean;
    defaultOneFile: boolean;
    defaultDemoEnabled: boolean;
    defaultDemoDuration: number;
    defaultIncludePackages: string[];
    defaultExcludePackages: string[];
    defaultServerUrl: string;
    defaultDistributionType: string;
    defaultCreateDesktopShortcut: boolean;
    defaultCreateStartMenu: boolean;
    defaultPublisher: string;
    defaultLicenseUI: string;
    showAdvancedByDefault: boolean;
    rememberLastProject: boolean;
    lastProjectId: string | null;
}

const defaultSettings: Settings = {
    theme: 'dark',
    autoUpdate: true,
    defaultShowConsole: true,
    defaultOneFile: true,
    defaultDemoEnabled: false,
    defaultDemoDuration: 60,
    defaultIncludePackages: [],
    defaultExcludePackages: ['tkinter', 'test', 'unittest'],
    defaultServerUrl: import.meta.env.VITE_API_URL || 'http://localhost:8000',
    defaultDistributionType: 'installer',
    defaultCreateDesktopShortcut: true,
    defaultCreateStartMenu: true,
    defaultPublisher: '',
    defaultLicenseUI: 'gui',
    showAdvancedByDefault: false,
    rememberLastProject: true,
    lastProjectId: null,
};

interface SettingsContextType {
    settings: Settings;
    updateSetting: (key: keyof Settings, value: any) => void;
    updateSettings: (newSettings: Partial<Settings>) => void;
    resetSettings: () => void;
    toggleTheme: () => void;
}

const SettingsContext = createContext<SettingsContextType>({
    settings: defaultSettings,
    updateSetting: () => { },
    updateSettings: () => { },
    resetSettings: () => { },
    toggleTheme: () => { },
});

export const useSettings = () => useContext(SettingsContext);

export const SettingsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [settings, setSettings] = useState<Settings>(defaultSettings);
    const [loaded, setLoaded] = useState(false);

    useEffect(() => {
        try {
            const saved = localStorage.getItem('codevault_settings');
            if (saved) {
                const parsed = JSON.parse(saved);
                setSettings({ ...defaultSettings, ...parsed });
            }
        } catch (error) {
            console.error('Failed to load settings:', error);
        }
        setLoaded(true);
    }, []);

    useEffect(() => {
        if (loaded) {
            const html = document.documentElement;
            html.classList.remove('light', 'dark', 'dark-matter');

            if (settings.theme === 'dark-matter') {
                html.classList.add('dark-matter');
            } else if (settings.theme === 'dark') {
                html.classList.add('dark');
            } else if (settings.theme === 'light') {
                html.classList.add('light');
            }

            html.setAttribute('data-theme', settings.theme);
        }
    }, [settings.theme, loaded]);

    useEffect(() => {
        if (loaded) {
            try {
                localStorage.setItem('codevault_settings', JSON.stringify(settings));
            } catch (error) {
                console.error('Failed to save settings:', error);
            }
        }
    }, [settings, loaded]);

    const updateSetting = useCallback((key: keyof Settings, value: any) => {
        setSettings(prev => ({ ...prev, [key]: value }));
    }, []);

    const updateSettings = useCallback((newSettings: Partial<Settings>) => {
        setSettings(prev => ({ ...prev, ...newSettings }));
    }, []);

    const resetSettings = useCallback(() => {
        setSettings(defaultSettings);
        localStorage.removeItem('codevault_settings');
    }, []);

    const toggleTheme = useCallback(() => {
        setSettings(prev => ({
            ...prev,
            theme: prev.theme === 'dark' ? 'dark-matter' : 'dark'
        }));
    }, []);

    const value = useMemo(() => ({
        settings,
        updateSetting,
        updateSettings,
        resetSettings,
        toggleTheme
    }), [settings, updateSetting, updateSettings, resetSettings, toggleTheme]);

    return (
        <SettingsContext.Provider value={value}>
            {children}
        </SettingsContext.Provider>
    );
};

export default SettingsContext;