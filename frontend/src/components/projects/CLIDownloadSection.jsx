import React, { useState } from 'react';
import { Download, Loader, Package } from 'lucide-react';
import api from '../../services/api';

const CLIDownloadSection = ({ project, licenses = [] }) => {
    const [selectedLicense, setSelectedLicense] = useState('');
    const [downloading, setDownloading] = useState(false);

    const activeLicenses = licenses.filter(l => l.status === 'active');

    const handleDownloadPackage = async () => {
        if (!project?.id) return;

        setDownloading(true);
        try {
            // Call the build-package endpoint
            const params = selectedLicense ? `?license_key=${selectedLicense}` : '';
            const response = await api.get(`/projects/${project.id}/build-package${params}`, {
                responseType: 'blob'
            });

            // Create download link
            const blob = new Blob([response.data], { type: 'application/zip' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `build_${project.name?.replace(/\s+/g, '_').toLowerCase() || 'project'}.zip`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } catch (err) {
            console.error('Failed to download build package:', err);
            alert('Failed to download build package. Please try again.');
        } finally {
            setDownloading(false);
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
                        <h3 className="font-semibold text-white">Select License</h3>
                        <p className="text-xs text-slate-400">Embed license protection in your build</p>
                    </div>
                </div>

                {activeLicenses.length > 0 ? (
                    <select
                        value={selectedLicense}
                        onChange={(e) => setSelectedLicense(e.target.value)}
                        className="input w-full text-base py-3"
                    >
                        <option value="">No license (Demo mode)</option>
                        {activeLicenses.map(lic => (
                            <option key={lic.id} value={lic.license_key}>
                                {lic.license_key} {lic.client_name ? `- ${lic.client_name}` : ''}
                            </option>
                        ))}
                    </select>
                ) : (
                    <div className="text-sm text-slate-400 p-3 bg-white/5 rounded-lg border border-white/10">
                        No licenses created yet.{' '}
                        <a href="/licenses" className="text-indigo-400 hover:underline">
                            Create one →
                        </a>
                    </div>
                )}
            </div>

            {/* Download Build Package */}
            <div className="bg-gradient-to-br from-emerald-500/10 to-cyan-500/10 rounded-xl p-5 border border-emerald-500/20">
                <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-full bg-emerald-500/20 flex items-center justify-center">
                        <span className="text-lg font-bold text-emerald-400">2</span>
                    </div>
                    <div>
                        <h3 className="font-semibold text-white">Download Build Package</h3>
                        <p className="text-xs text-slate-400">Extract, run build.bat, get your .exe</p>
                    </div>
                </div>

                <button
                    onClick={handleDownloadPackage}
                    disabled={downloading}
                    className="w-full flex items-center justify-center gap-3 px-6 py-4 rounded-xl bg-gradient-to-r from-emerald-600 to-cyan-600 text-white font-semibold text-lg hover:from-emerald-500 hover:to-cyan-500 transition-all shadow-lg shadow-emerald-500/25 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {downloading ? (
                        <>
                            <Loader size={22} className="animate-spin" />
                            Preparing Package...
                        </>
                    ) : (
                        <>
                            <Package size={22} />
                            Download Build Package
                        </>
                    )}
                </button>

                <div className="mt-4 text-center text-xs text-slate-500">
                    Requires Python 3.8+ • Windows only
                </div>
            </div>
        </div>
    );
};

export default CLIDownloadSection;
