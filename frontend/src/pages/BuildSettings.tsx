import React from 'react';
import { RotateCcw, Package, Clock, Server, Eye, Download, LucideIcon } from 'lucide-react';
import { useSettings } from '../contexts/SettingsContext';

/**
 * BuildSettings Page - Build defaults and preferences configuration
 */

interface SectionProps {
    title: string;
    icon: LucideIcon;
    children: React.ReactNode;
}

const Section: React.FC<SectionProps> = ({ title, icon: Icon, children }) => (
    <div className="bg-cv-border-subtle rounded-xl border border-cv-border overflow-hidden mb-6">
        <div className="flex items-center gap-3 p-4 border-b border-cv-border bg-cv-bg-elevated">
            <Icon size={18} className="text-cv-primary" />
            <h3 className="font-semibold text-cv-text">{title}</h3>
        </div>
        <div className="p-4 space-y-4">{children}</div>
    </div>
);

interface ToggleProps {
    label: string;
    description?: string;
    value: boolean;
    onChange: (value: boolean) => void;
}

const Toggle: React.FC<ToggleProps> = ({ label, description, value, onChange }) => (
    <div className="flex items-center justify-between py-2">
        <div>
            <p className="text-cv-text font-medium">{label}</p>
            {description && <p className="text-xs text-cv-text-muted mt-0.5">{description}</p>}
        </div>
        <button
            onClick={() => onChange(!value)}
            aria-pressed={value}
            className={`w-12 h-6 rounded-full p-1 transition-colors ${value ? 'bg-emerald-500' : 'bg-cv-muted'}`}
        >
            <div className={`w-4 h-4 rounded-full bg-white transition-transform ${value ? 'translate-x-6' : 'translate-x-0'}`} />
        </button>
    </div>
);

interface SettingsInputProps {
    label: string;
    description?: string;
    value: string;
    onChange: (value: string) => void;
    placeholder?: string;
}

const SettingsInput: React.FC<SettingsInputProps> = ({ label, description, value, onChange, placeholder }) => (
    <div className="py-2">
        <label className="text-cv-text font-medium block mb-1">{label}</label>
        {description && <p className="text-xs text-cv-text-muted mb-2">{description}</p>}
        <input
            type="text"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            className="input w-full"
        />
    </div>
);

interface SettingsSelectProps {
    label: string;
    description?: string;
    value: string | number;
    onChange: (value: string) => void;
    options: { value: string | number; label: string }[];
}

const SettingsSelect: React.FC<SettingsSelectProps> = ({ label, description, value, onChange, options }) => (
    <div className="py-2">
        <label className="text-cv-text font-medium block mb-1">{label}</label>
        {description && <p className="text-xs text-cv-text-muted mb-2">{description}</p>}
        <select value={value} onChange={(e) => onChange(e.target.value)} className="input w-full">
            {options.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
        </select>
    </div>
);

const BuildSettings: React.FC = () => {
    const { settings, updateSetting, resetSettings } = useSettings();

    return (
        <div className="p-6">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-2xl font-bold text-cv-text mb-2">Build Settings</h1>
                    <p className="text-cv-text-muted">Configure default build options and preferences</p>
                </div>
                <button
                    onClick={resetSettings}
                    className="flex items-center gap-2 px-4 py-2 text-cv-text-muted hover:text-cv-text hover:bg-cv-border-subtle rounded-lg transition-colors"
                >
                    <RotateCcw size={16} />
                    Reset Defaults
                </button>
            </div>

            <div className="max-w-2xl">
                <Section title="Build Defaults" icon={Package}>
                    <Toggle label="Show Console Window" description="Show console by default for new builds" value={settings.defaultShowConsole} onChange={(v) => updateSetting('defaultShowConsole', v)} />
                    <Toggle label="One-File Mode" description="Compile to single executable by default" value={settings.defaultOneFile} onChange={(v) => updateSetting('defaultOneFile', v)} />
                    <SettingsInput label="Default Excluded Packages" description="Comma-separated list of packages to exclude" value={settings.defaultExcludePackages?.join(', ') || ''} onChange={(v) => updateSetting('defaultExcludePackages', v.split(',').map(s => s.trim()).filter(Boolean))} placeholder="tkinter, test" />
                </Section>

                <Section title="Distribution Method" icon={Download}>
                    <SettingsSelect
                        label="Output Type"
                        description="How the final build should be packaged"
                        value={settings.defaultDistributionType || 'installer'}
                        onChange={(v) => updateSetting('defaultDistributionType', v)}
                        options={[
                            { value: 'portable', label: 'Portable Executable (no installer)' },
                            { value: 'installer', label: 'Windows Installer (NSIS)' },
                        ]}
                    />
                    <Toggle
                        label="Create Desktop Shortcut"
                        description="Add shortcut to user's desktop during installation"
                        value={settings.defaultCreateDesktopShortcut !== false}
                        onChange={(v) => updateSetting('defaultCreateDesktopShortcut', v)}
                    />
                    <Toggle
                        label="Create Start Menu Entry"
                        description="Add entry to Windows Start Menu during installation"
                        value={settings.defaultCreateStartMenu !== false}
                        onChange={(v) => updateSetting('defaultCreateStartMenu', v)}
                    />
                    <SettingsInput
                        label="Default Publisher Name"
                        description="Company/developer name shown in installer and Add/Remove Programs"
                        value={settings.defaultPublisher || ''}
                        onChange={(v) => updateSetting('defaultPublisher', v)}
                        placeholder="Your Company Name"
                    />
                    <SettingsSelect
                        label="License Activation UI"
                        description="How users enter their license key on first run"
                        value={settings.defaultLicenseUI || 'gui'}
                        onChange={(v) => updateSetting('defaultLicenseUI', v)}
                        options={[
                            { value: 'gui', label: 'GUI Popup Dialog (Recommended)' },
                            { value: 'console', label: 'Console Prompt' },
                            { value: 'web', label: 'Web Browser (Node.js only)' },
                        ]}
                    />
                </Section>

                <Section title="Demo Mode Defaults" icon={Clock}>
                    <Toggle label="Enable Demo Mode by Default" description="New builds will have demo mode enabled" value={settings.defaultDemoEnabled} onChange={(v) => updateSetting('defaultDemoEnabled', v)} />
                    <SettingsSelect label="Default Demo Duration" description="Default trial period for new builds" value={settings.defaultDemoDuration} onChange={(v) => updateSetting('defaultDemoDuration', Number(v))} options={[
                        { value: 30, label: '30 minutes' },
                        { value: 60, label: '1 hour' },
                        { value: 120, label: '2 hours' },
                        { value: 240, label: '4 hours' },
                        { value: 1440, label: '24 hours (1 day)' },
                        { value: 4320, label: '3 days' },
                        { value: 10080, label: '7 days' },
                        { value: 20160, label: '14 days' },
                        { value: 43200, label: '30 days' },
                    ]} />
                </Section>

                <Section title="Server Settings" icon={Server}>
                    <SettingsInput label="License Server URL" description="URL for license validation" value={settings.defaultServerUrl} onChange={(v) => updateSetting('defaultServerUrl', v)} placeholder={import.meta.env.VITE_API_URL || 'https://api.codevault.com'} />
                </Section>

                <Section title="UI Preferences" icon={Eye}>
                    <Toggle label="Show Advanced Options by Default" description="Expand advanced options in build wizard" value={settings.showAdvancedByDefault} onChange={(v) => updateSetting('showAdvancedByDefault', v)} />
                    <Toggle label="Auto-Check Updates" description="Check for app updates on startup" value={settings.autoUpdate} onChange={(v) => updateSetting('autoUpdate', v)} />
                </Section>
            </div>
        </div>
    );
};

export default BuildSettings;
