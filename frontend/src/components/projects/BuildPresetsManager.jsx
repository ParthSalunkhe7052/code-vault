import React, { useState, useEffect } from 'react';
import { Save, Trash2, FileText, ChevronDown, ChevronUp, Plus } from 'lucide-react';

/**
 * BuildPresetsManager - Save and load build configuration presets
 * Can be used standalone or embedded in the wizard
 */
const BuildPresetsManager = ({
    currentConfig = {},
    onLoadPreset,
    compact = false
}) => {
    const [presets, setPresets] = useState([]);
    const [newPresetName, setNewPresetName] = useState('');
    const [showPresets, setShowPresets] = useState(!compact);
    const [saving, setSaving] = useState(false);

    // Load presets from localStorage
    useEffect(() => {
        const saved = localStorage.getItem('codevault_build_presets');
        if (saved) {
            try {
                setPresets(JSON.parse(saved));
            } catch (e) {
                console.error('Failed to load presets:', e);
            }
        }
    }, []);

    // Save presets to localStorage
    const savePresets = (newPresets) => {
        setPresets(newPresets);
        localStorage.setItem('codevault_build_presets', JSON.stringify(newPresets));
    };

    const handleSavePreset = () => {
        if (!newPresetName.trim()) return;

        setSaving(true);

        const preset = {
            id: Date.now().toString(),
            name: newPresetName.trim(),
            createdAt: new Date().toISOString(),
            config: {
                showConsole: currentConfig.showConsole,
                includePackages: currentConfig.includePackages,
                excludePackages: currentConfig.excludePackages,
                selectedDataFolders: currentConfig.selectedDataFolders,
                demoMode: currentConfig.demoMode,
                demoDuration: currentConfig.demoDuration,
                iconPath: currentConfig.iconPath,
            }
        };

        savePresets([...presets, preset]);
        setNewPresetName('');
        setSaving(false);
    };

    const handleDeletePreset = (id) => {
        savePresets(presets.filter(p => p.id !== id));
    };

    const handleLoadPreset = (preset) => {
        if (onLoadPreset) {
            onLoadPreset(preset.config);
        }
    };

    if (compact && presets.length === 0) {
        return null;
    }

    return (
        <div className={`bg-white/5 rounded-xl border border-white/10 overflow-hidden ${compact ? 'text-sm' : ''}`}>
            {/* Header */}
            <button
                onClick={() => setShowPresets(!showPresets)}
                className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
            >
                <div className="flex items-center gap-3">
                    <FileText size={compact ? 16 : 18} className="text-purple-400" />
                    <span className="font-medium text-white">Build Presets</span>
                    {presets.length > 0 && (
                        <span className="text-xs bg-purple-500/30 text-purple-300 px-2 py-0.5 rounded-full">
                            {presets.length}
                        </span>
                    )}
                </div>
                {showPresets ? <ChevronUp size={18} className="text-slate-400" /> : <ChevronDown size={18} className="text-slate-400" />}
            </button>

            {showPresets && (
                <div className="p-4 border-t border-white/10 space-y-4">
                    {/* Save New Preset */}
                    <div className="flex gap-2">
                        <input
                            type="text"
                            value={newPresetName}
                            onChange={(e) => setNewPresetName(e.target.value)}
                            placeholder="Preset name..."
                            className="input flex-1"
                            onKeyDown={(e) => e.key === 'Enter' && handleSavePreset()}
                        />
                        <button
                            onClick={handleSavePreset}
                            disabled={!newPresetName.trim() || saving}
                            className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg transition-colors disabled:opacity-50"
                        >
                            <Save size={16} />
                            Save
                        </button>
                    </div>

                    {/* Presets List */}
                    {presets.length > 0 ? (
                        <div className="space-y-2 max-h-48 overflow-y-auto custom-scrollbar">
                            {presets.map(preset => (
                                <div
                                    key={preset.id}
                                    className="flex items-center justify-between p-3 bg-white/5 rounded-lg hover:bg-white/10 transition-colors group"
                                >
                                    <div className="flex-1" onClick={() => handleLoadPreset(preset)}>
                                        <p className="text-white font-medium cursor-pointer">{preset.name}</p>
                                        <p className="text-xs text-slate-500">
                                            {new Date(preset.createdAt).toLocaleDateString()}
                                        </p>
                                    </div>
                                    <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <button
                                            onClick={() => handleLoadPreset(preset)}
                                            className="p-1.5 text-slate-400 hover:text-emerald-400 hover:bg-emerald-500/10 rounded transition-colors"
                                            title="Load preset"
                                        >
                                            <Plus size={16} />
                                        </button>
                                        <button
                                            onClick={() => handleDeletePreset(preset.id)}
                                            className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
                                            title="Delete preset"
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="text-slate-500 text-sm text-center py-4">
                            No presets saved yet. Save your current configuration as a preset for quick reuse.
                        </p>
                    )}
                </div>
            )}
        </div>
    );
};

export default BuildPresetsManager;
