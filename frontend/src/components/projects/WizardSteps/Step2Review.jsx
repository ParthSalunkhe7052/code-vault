import React from 'react';
import { FolderTree, FileCode, Package, CheckCircle, AlertCircle } from 'lucide-react';

/**
 * Step2Review - Review the project structure after upload
 * Shows file tree, detected entry point, and dependencies
 */
const Step2Review = ({ fileTree, files = [], entryPoint, entryPointConfidence, onEntryPointChange }) => {
    const hasFileTree = fileTree && fileTree.files && fileTree.files.length > 0;

    const getConfidenceColor = (confidence) => {
        switch (confidence) {
            case 'high': return 'text-emerald-400';
            case 'medium': return 'text-amber-400';
            default: return 'text-red-400';
        }
    };

    const getConfidenceIcon = (confidence) => {
        return confidence === 'high' || confidence === 'medium'
            ? <CheckCircle size={16} className={getConfidenceColor(confidence)} />
            : <AlertCircle size={16} className={getConfidenceColor(confidence)} />;
    };

    // Build folder structure for display
    const buildFolderStructure = () => {
        if (!hasFileTree) return null;

        const folders = {};
        const rootFiles = [];

        fileTree.files.forEach(file => {
            if (file.includes('/')) {
                const parts = file.split('/');
                const fileName = parts.pop();
                const folderPath = parts.join('/');

                if (!folders[folderPath]) {
                    folders[folderPath] = [];
                }
                folders[folderPath].push(fileName);
            } else {
                rootFiles.push(file);
            }
        });

        return { folders, rootFiles };
    };

    const structure = buildFolderStructure();

    return (
        <div className="space-y-6">
            <div className="text-center mb-6">
                <h2 className="text-xl font-bold text-white mb-2">Review Project Structure</h2>
                <p className="text-slate-400 text-sm">
                    Verify your project files and detected entry point
                </p>
            </div>

            {/* File Tree Display */}
            {hasFileTree && (
                <div className="bg-white/5 rounded-xl border border-white/10 p-4">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-2">
                            <FolderTree size={20} className="text-indigo-400" />
                            <h3 className="font-semibold text-white">Project Structure</h3>
                        </div>
                        <span className="text-xs text-slate-400 bg-white/10 px-2 py-1 rounded">
                            {fileTree.total_files} files
                        </span>
                    </div>

                    <div className="font-mono text-sm max-h-64 overflow-y-auto space-y-1">
                        {/* Root files first */}
                        {structure?.rootFiles.map((file, i) => (
                            <div
                                key={`root-${i}`}
                                className={`flex items-center gap-2 pl-2 py-1 rounded ${file === entryPoint ? 'bg-emerald-500/20 text-emerald-400' : 'text-slate-300'
                                    }`}
                            >
                                <FileCode size={14} />
                                <span>{file}</span>
                                {file === entryPoint && (
                                    <span className="text-xs bg-emerald-500/30 px-2 py-0.5 rounded ml-2">
                                        Entry Point
                                    </span>
                                )}
                            </div>
                        ))}

                        {/* Folders */}
                        {structure && Object.entries(structure.folders).map(([folder, folderFiles]) => (
                            <div key={folder} className="mt-2">
                                <div className="flex items-center gap-2 text-amber-400 pl-2">
                                    <Package size={14} />
                                    <span>{folder}/</span>
                                </div>
                                {folderFiles.slice(0, 5).map((file, i) => (
                                    <div
                                        key={`${folder}-${i}`}
                                        className={`flex items-center gap-2 pl-6 py-0.5 ${`${folder}/${file}` === entryPoint
                                                ? 'text-emerald-400'
                                                : 'text-slate-400'
                                            }`}
                                    >
                                        <FileCode size={12} />
                                        <span>{file}</span>
                                    </div>
                                ))}
                                {folderFiles.length > 5 && (
                                    <div className="text-slate-500 pl-6 text-xs">
                                        ... and {folderFiles.length - 5} more
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Entry Point Detection */}
            <div className="bg-gradient-to-br from-indigo-500/10 to-purple-500/10 rounded-xl border border-indigo-500/20 p-5">
                <div className="flex items-center gap-3 mb-4">
                    {getConfidenceIcon(entryPointConfidence)}
                    <div>
                        <h3 className="font-semibold text-white">Detected Entry Point</h3>
                        <p className="text-xs text-slate-400">
                            Confidence: <span className={getConfidenceColor(entryPointConfidence)}>{entryPointConfidence || 'low'}</span>
                        </p>
                    </div>
                </div>

                <div className="bg-white/5 rounded-lg p-3 font-mono text-emerald-400">
                    {entryPoint || 'No entry point detected'}
                </div>

                {entryPointConfidence !== 'high' && (
                    <p className="text-xs text-amber-400 mt-3">
                        ⚠️ Detection confidence is not high. You can change this in the next step.
                    </p>
                )}
            </div>

            {/* Dependencies */}
            {fileTree?.dependencies?.has_requirements && (
                <div className="bg-white/5 rounded-xl border border-white/10 p-4">
                    <div className="flex items-center gap-2 mb-3">
                        <Package size={18} className="text-blue-400" />
                        <h3 className="font-semibold text-white">Dependencies Found</h3>
                        <span className="text-xs text-slate-400">
                            ({fileTree.dependencies.python.length} packages)
                        </span>
                    </div>

                    <div className="flex flex-wrap gap-2">
                        {fileTree.dependencies.python.slice(0, 10).map((dep, i) => (
                            <span
                                key={i}
                                className="px-3 py-1.5 bg-blue-500/20 text-blue-400 rounded-lg text-sm"
                            >
                                {dep}
                            </span>
                        ))}
                        {fileTree.dependencies.python.length > 10 && (
                            <span className="px-3 py-1.5 bg-slate-500/20 text-slate-400 rounded-lg text-sm">
                                +{fileTree.dependencies.python.length - 10} more
                            </span>
                        )}
                    </div>
                </div>
            )}

            {/* No files warning */}
            {!hasFileTree && files.length === 0 && (
                <div className="text-center py-12 text-slate-400">
                    <AlertCircle size={48} className="mx-auto mb-4 opacity-50" />
                    <p>No files to review. Please go back and upload your project.</p>
                </div>
            )}
        </div>
    );
};

export default Step2Review;
