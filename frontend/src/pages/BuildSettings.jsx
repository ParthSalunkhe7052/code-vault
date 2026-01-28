import React from 'react';
import { RotateCcw, Package, Clock, Server, Eye, Download } from 'lucide-react';
import { useSettings } from '../contexts/SettingsContext';

/**
 * BuildSettings Page - Build defaults and preferences configuration
 * Separate from Settings.jsx which handles user/API settings
 */
const BuildSettings = () => {
    const { settings, updateSetting, resetSettings } = useSettings();

    const Section = ({ title, icon: Icon, children }) => (
        <div className="bg-white/5 rounded-xl border border-white/10 overflow-hidden mb-6">
            <div className="flex items-center gap-3 p-4 border-b border-white/10 bg-white/5">
                <Icon size={18} className="text-indigo-400" />
                <h3 className="font-semibold text-white">{title}</h3>
            </div>
            <div className="p-4 space-y-4">{children}</div>
        </div>
    );

    const Toggle = ({ label, description, value, onChange }) => (
        <div className="flex items-center justify-between py-2">
            <div>
                <p className="text-white font-medium">{label}</p>
                {description && <p className="text-xs text-slate-400 mt-0.5">{description}</p>}
            </div>
            <button
                onClick={() => onChange(!value)}
                className={`w-12 h-6 rounded-full p-1 transition-colors ${value ? 'bg-emerald-500' : 'bg-slate-600'}`}
            >
                <div className={`w-4 h-4 rounded-full bg-white transition-transform ${value ? 'translate-x-6' : 'translate-x-0'}`} />
            </button>
        </div>
    );

    const Input = ({ label, description, value, onChange, placeholder }) => (
        <div className="py-2">
            <label className="text-white font-medium block mb-1">{label}</label>
            {description && <p className="text-xs text-slate-400 mb-2">{description}</p>}
            <input
                type="text"
                value={value}
                onChange={(e) => onChange(e.target.value)}
                placeholder={placeholder}
                className="input w-full"
            />
        </div>
    );

    const Select = ({ label, description, value, onChange, options }) => (
        <div className="py-2">
            <label className="text-white font-medium block mb-1">{label}</label>
            {description && <p className="text-xs text-slate-400 mb-2">{description}</p>}
            <select value={value} onChange={(e) => onChange(e.target.value)} className="input w-full">
                {options.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
            </select>
        </div>
    );

    return (
        <div className="p-6">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-2xl font-bold text-white mb-2">Build Settings</h1>
                    <p className="text-slate-400">Configure default build options and preferences</p>
                </div>
                <button
                    onClick={resetSettings}
                    className="flex items-center gap-2 px-4 py-2 text-slate-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                >
                    <RotateCcw size={16} />
                    Reset Defaults
                </button>
            </div>

            <div className="max-w-2xl">
                <Section title="Build Defaults" icon={Package}>
                    <Toggle label="Show Console Window" description="Show console by default for new builds" value={settings.defaultShowConsole} onChange={(v) => updateSetting('defaultShowConsole', v)} />
                    <Toggle label="One-File Mode" description="Compile to single executable by default" value={settings.defaultOneFile} onChange={(v) => updateSetting('defaultOneFile', v)} />
                    <Input label="Default Excluded Packages" description="Comma-separated list of packages to exclude" value={settings.defaultExcludePackages?.join(', ') || ''} onChange={(v) => updateSetting('defaultExcludePackages', v.split(',').map(s => s.trim()).filter(Boolean))} placeholder="tkinter, test" />
                </Section>

                <Section title="Distribution Method" icon={Download}>
                    <Select
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
                    <Input
                        label="Default Publisher Name"
                        description="Company/developer name shown in installer and Add/Remove Programs"
                        value={settings.defaultPublisher || ''}
                        onChange={(v) => updateSetting('defaultPublisher', v)}
                        placeholder="Your Company Name"
                    />
                    <Select
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
                    <Select label="Default Demo Duration" description="Default trial period for new builds" value={settings.defaultDemoDuration} onChange={(v) => updateSetting('defaultDemoDuration', Number(v))} options={[
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
                    <Input label="License Server URL" description="URL for license validation" value={settings.defaultServerUrl} onChange={(v) => updateSetting('defaultServerUrl', v)} placeholder="http://localhost:8000" />
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
