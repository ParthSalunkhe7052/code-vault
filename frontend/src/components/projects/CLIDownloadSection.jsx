import { useState } from 'react';
import { Loader, Package, Terminal, Copy, Check } from 'lucide-react';
import api from '../../services/api';

const CLIDownloadSection = ({ project, licenses = [] }) => {
    const [selectedLicense, setSelectedLicense] = useState('');
    const [downloading, setDownloading] = useState(false);
    const [copied, setCopied] = useState(false);

    const activeLicenses = licenses.filter(l => l.status === 'active');

    const handleDownloadBundle = async () => {
        if (!project?.id) return;

        setDownloading(true);
        try {
            // Call the build-bundle endpoint
            const params = selectedLicense ? `?license_id=${selectedLicense}` : '';
            const response = await api.get(`/projects/${project.id}/build-bundle${params}`, {
                responseType: 'blob'
            });

            // Create download link
            const blob = new Blob([response.data], { type: 'application/zip' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${project.name?.replace(/\s+/g, '_').toLowerCase() || 'project'}_bundle.zip`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } catch (err) {
            if (import.meta.env.DEV) {
                console.error('Failed to download build bundle:', err);
            }
            const errorMessage = err.response?.data?.detail || 'Failed to download build bundle. Please try again.';
            alert(errorMessage);
        } finally {
            setDownloading(false);
        }
    };

    const cliCommand = `codevault project build ${project?.id || '<project-id>'}${selectedLicense ? ` --license ${selectedLicense}` : ''}`;
    const cliCommandFast = `codevault project build ${project?.id || '<project-id>'} --fast${selectedLicense ? ` --license ${selectedLicense}` : ''}`;

    const handleCopyCommand = async () => {
        try {
            await navigator.clipboard.writeText(cliCommand);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            if (import.meta.env.DEV) {
                console.error('Failed to copy:', err);
            }
        }
    };

    return (
        <div className="space-y-5">
            {/* License Selection */}
            <div className="bg-gradient-to-br from-purple-500/10 to-pink-500/10 rounded-xl p-5 border border-purple-500/20">
                <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center">
                        <span className="text-lg font-bold text-purple-400">1</span>
                    </div>
                    <div>
                        <h3 className="font-semibold text-white">Select License (Optional)</h3>
                        <p className="text-xs text-slate-400">Embed license protection in your build</p>
                    </div>
                </div>

                {activeLicenses.length > 0 ? (
                    <select
                        value={selectedLicense}
                        onChange={(e) => setSelectedLicense(e.target.value)}
                        className="input w-full text-base py-3"
                    >
                        <option value="">Generic Build (runtime license prompt)</option>
                        {activeLicenses.map(lic => (
                            <option key={lic.id} value={lic.id}>
                                {lic.license_key} {lic.client_name ? `- ${lic.client_name}` : ''}
                            </option>
                        ))}
                    </select>
                ) : (
                    <div className="text-sm text-slate-400 p-3 bg-white/5 rounded-lg border border-white/10">
                        No licenses created yet. Build will use generic mode (license prompt at runtime).{' '}
                        <a href="/licenses" className="text-indigo-400 hover:underline">
                            Create a license →
                        </a>
                    </div>
                )}
            </div>

            {/* CLI Command */}
            <div className="bg-gradient-to-br from-cyan-500/10 to-blue-500/10 rounded-xl p-5 border border-cyan-500/20">
                <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-full bg-cyan-500/20 flex items-center justify-center">
                        <span className="text-lg font-bold text-cyan-400">2</span>
                    </div>
                    <div>
                        <h3 className="font-semibold text-white">Run Build Command</h3>
                        <p className="text-xs text-slate-400">Execute this in your terminal to compile locally</p>
                    </div>
                </div>

                <div className="relative mb-2">
                    <div className="bg-black/40 rounded-lg p-4 font-mono text-sm text-emerald-400 pr-12 break-all">
                        {cliCommand}
                    </div>
                    <button
                        onClick={handleCopyCommand}
                        className="absolute right-2 top-1/2 -translate-y-1/2 p-2 hover:bg-white/10 rounded-lg transition-colors"
                        title="Copy command"
                    >
                        {copied ? (
                            <Check size={18} className="text-emerald-400" />
                        ) : (
                            <Copy size={18} className="text-slate-400" />
                        )}
                    </button>
                </div>

                <div className="relative mb-3">
                    <div className="bg-black/40 rounded-lg p-3 font-mono text-sm text-indigo-400 pr-12 break-all">
                        {cliCommandFast}
                    </div>
                    <button
                        onClick={async () => {
                            await navigator.clipboard.writeText(cliCommandFast);
                            setCopied(true);
                            setTimeout(() => setCopied(false), 2000);
                        }}
                        className="absolute right-2 top-1/2 -translate-y-1/2 p-2 hover:bg-white/10 rounded-lg transition-colors"
                        title="Copy command"
                    >
                        <Copy size={18} className="text-slate-400" />
                    </button>
                </div>

                <div className="flex flex-wrap gap-2 text-xs mb-3">
                    <span className="px-2 py-1 bg-emerald-500/20 text-emerald-400 rounded">Python: Free</span>
                    <span className="px-2 py-1 bg-purple-500/20 text-purple-400 rounded">Windows only</span>
                    <span className="px-2 py-1 bg-amber-500/20 text-amber-400 rounded">--fast for 3-4x faster</span>
                </div>

                <div className="mt-2 text-xs text-slate-500">
                    First install: <code className="bg-white/10 px-1.5 py-0.5 rounded">pip install codevault-cli</code>
                </div>
            </div>

            {/* Alternative: Download Build Bundle */}
            <div className="bg-gradient-to-br from-emerald-500/10 to-cyan-500/10 rounded-xl p-5 border border-emerald-500/20">
                <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-full bg-emerald-500/20 flex items-center justify-center">
                        <Terminal size={20} className="text-emerald-400" />
                    </div>
                    <div>
                        <h3 className="font-semibold text-white">Alternative: Download Bundle</h3>
                        <p className="text-xs text-slate-400">Manual download if CLI isn&apos;t working</p>
                    </div>
                </div>

                <button
                    onClick={handleDownloadBundle}
                    disabled={downloading}
                    className="w-full flex items-center justify-center gap-3 px-6 py-3 rounded-xl bg-white/10 hover:bg-white/20 text-white font-medium transition-all border border-white/10 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {downloading ? (
                        <>
                            <Loader size={18} className="animate-spin" />
                            Preparing Bundle...
                        </>
                    ) : (
                        <>
                            <Package size={18} />
                            Download Build Bundle (.zip)
                        </>
                    )}
                </button>

                <div className="mt-3 text-center text-xs text-slate-500">
                    Extract the ZIP, then run: <code className="bg-white/10 px-1.5 py-0.5 rounded">python -m codevault_cli build .</code>
                </div>
            </div>
        </div>
    );
};

export default CLIDownloadSection;

