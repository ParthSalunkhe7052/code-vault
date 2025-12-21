import React, { createContext, useState, useContext, useEffect } from 'react';

/**
 * Settings Context - Global and per-project settings management
 * Stores build defaults, UI preferences, and other configurable options
 */

const defaultSettings = {
    // Global Settings
    theme: 'dark',
    autoUpdate: true,

    // Default Build Options
    defaultShowConsole: true,
    defaultOneFile: true,
    defaultDemoEnabled: false,
    defaultDemoDuration: 60, // minutes

    // Package Defaults
    defaultIncludePackages: [],
    defaultExcludePackages: ['tkinter', 'test', 'unittest'],

    // Server Settings
    defaultServerUrl: 'http://localhost:8000',

    // Distribution Defaults (NSIS Installer System)
    defaultDistributionType: 'installer', // 'portable' or 'installer'
    defaultCreateDesktopShortcut: true,
    defaultCreateStartMenu: true,
    defaultPublisher: '',
    defaultLicenseUI: 'gui', // 'gui', 'console', or 'web'

    // UI Preferences
    showAdvancedByDefault: false,
    rememberLastProject: true,
    lastProjectId: null,
};

const SettingsContext = createContext({
    settings: defaultSettings,
    updateSetting: () => { },
    updateSettings: () => { },
    resetSettings: () => { },
});

export const useSettings = () => useContext(SettingsContext);

export const SettingsProvider = ({ children }) => {
    const [settings, setSettings] = useState(defaultSettings);
    const [loaded, setLoaded] = useState(false);

    // Load settings from localStorage on mount
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

    // Save settings to localStorage whenever they change
    useEffect(() => {
        if (loaded) {
            try {
                localStorage.setItem('codevault_settings', JSON.stringify(settings));
            } catch (error) {
                console.error('Failed to save settings:', error);
            }
        }
    }, [settings, loaded]);

    const updateSetting = (key, value) => {
        setSettings(prev => ({ ...prev, [key]: value }));
    };

    const updateSettings = (newSettings) => {
        setSettings(prev => ({ ...prev, ...newSettings }));
    };

    const resetSettings = () => {
        setSettings(defaultSettings);
        localStorage.removeItem('codevault_settings');
    };

    return (
        <SettingsContext.Provider value={{ settings, updateSetting, updateSettings, resetSettings }}>
            {children}
        </SettingsContext.Provider>
    );
};

export default SettingsContext;
