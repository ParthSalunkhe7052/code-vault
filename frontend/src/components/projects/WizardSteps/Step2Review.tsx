import React, { useMemo, memo } from 'react';
import { FolderTree, FileCode, Package, CheckCircle, AlertCircle, FileText, Layers, GitBranch } from 'lucide-react';
import { ProjectFile } from '../../../types/api';

interface Step2ReviewProps {
    fileTree: any;
    files?: ProjectFile[];
    entryPoint: string | null;
    entryPointConfidence?: string;
    onEntryPointChange?: (file: string) => void;
}

const Step2Review: React.FC<Step2ReviewProps> = memo(({ fileTree, files = [], entryPoint, entryPointConfidence }) => {
    const hasFileTree = useMemo(() => fileTree && fileTree.files && fileTree.files.length > 0, [fileTree]);

    const getConfidenceColor = (confidence?: string) => {
        switch (confidence) {
            case 'high': return 'text-emerald-400';
            case 'medium': return 'text-amber-400';
            default: return 'text-red-400';
        }
    };

    const getConfidenceBg = (confidence?: string) => {
        switch (confidence) {
            case 'high': return 'bg-emerald-500/10 border-emerald-500/20';
            case 'medium': return 'bg-amber-500/10 border-amber-500/20';
            default: return 'bg-red-500/10 border-red-500/20';
        }
    };

    const structure = useMemo(() => {
        if (!hasFileTree) return null;

        const folders: Record<string, string[]> = {};
        const rootFiles: string[] = [];

        fileTree.files.forEach((file: string) => {
            if (file.includes('/')) {
                const parts = file.split('/');
                const fileName = parts.pop()!;
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
    }, [fileTree, hasFileTree]);

    const renderData = useMemo(() => {
        if (!structure) return null;

        const rootFiles = structure.rootFiles.map((file, i) => ({
            key: `root-${i}`,
            file,
            isEntry: file === entryPoint
        }));

        const folders = Object.entries(structure.folders).map(([folder, folderFiles]) => ({
            key: folder,
            folder,
            files: folderFiles.slice(0, 5),
            hasMore: folderFiles.length > 5,
            moreCount: folderFiles.length - 5
        }));

        return { rootFiles, folders };
    }, [structure, entryPoint]);

    return (
        <div className="space-y-8 animate-in fade-in duration-500 h-full flex flex-col">
            <div className="text-left shrink-0">
                <h2 className="text-2xl font-bold text-white mb-2 tracking-tight">Structure Review</h2>
                <p className="text-slate-400">
                    We&apos;ve analyzed your project. Please confirm the structure and entry point detection.
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 flex-1 min-h-0">
                <div className="lg:col-span-2 bg-white/5 rounded-2xl border border-white/10 flex flex-col overflow-hidden h-[500px] lg:h-auto">
                    <div className="p-4 border-b border-white/10 bg-white/5 flex items-center justify-between">
                         <div className="flex items-center gap-3">
                            <FolderTree size={18} className="text-indigo-400" />
                            <h3 className="font-bold text-white">Project Files</h3>
                        </div>
                        <span className="text-xs font-mono text-slate-400 bg-black/20 px-2 py-1 rounded">
                            {fileTree?.total_files || files.length} files
                        </span>
                    </div>

                    {hasFileTree ? (
                        <div className="flex-1 overflow-y-auto p-4 custom-scrollbar bg-black/20">
                            <div className="space-y-1 font-mono text-sm">
                                {renderData?.rootFiles.map(({ key, file, isEntry }) => (
                                    <div
                                        key={key}
                                        className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${isEntry
                                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/10'
                                            : 'text-slate-300 hover:bg-white/5'
                                            }`}
                                    >
                                        <FileCode size={14} className={isEntry ? 'text-emerald-400' : 'text-slate-500'} />
                                        <span>{file}</span>
                                        {isEntry && (
                                            <span className="ml-auto text-[10px] uppercase font-bold tracking-wider bg-emerald-500/20 px-2 py-0.5 rounded text-emerald-300">
                                                Entry Point
                                            </span>
                                        )}
                                    </div>
                                ))}

                                {renderData?.folders.map(({ key, folder, files, hasMore, moreCount }) => (
                                    <div key={key} className="mt-4">
                                        <div className="flex items-center gap-2 text-amber-400 px-3 mb-2 font-bold opacity-80">
                                            <Package size={14} />
                                            <span>{folder}/</span>
                                        </div>
                                        <div className="pl-4 border-l border-white/10 ml-4 space-y-1">
                                            {files.map((file, i) => {
                                                const fullPath = `${folder}/${file}`;
                                                const isEntry = fullPath === entryPoint;
                                                return (
                                                    <div
                                                        key={`${key}-${i}`}
                                                        className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${isEntry
                                                            ? 'bg-emerald-500/20 text-emerald-400'
                                                            : 'text-slate-400 hover:text-slate-300'
                                                            }`}
                                                    >
                                                        <FileText size={12} />
                                                        <span>{file}</span>
                                                    </div>
                                                );
                                            })}
                                            {hasMore && (
                                                <div className="text-slate-600 px-3 text-xs italic">
                                                    + {moreCount} more files...
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : (
                         files.length > 0 ? (
                            <div className="flex-1 p-4 overflow-y-auto space-y-2">
                                {files.map((file) => (
                                    <div key={file.id} className="flex items-center gap-3 p-3 bg-white/5 rounded-lg border border-white/5">
                                        <FileCode size={18} className="text-slate-400" />
                                        <span className="text-slate-300 text-sm font-mono">{file.filename}</span>
                                    </div>
                                ))}
                            </div>
                         ) : (
                            <div className="flex-1 flex flex-col items-center justify-center text-slate-500 gap-4">
                                <AlertCircle size={48} className="opacity-20" />
                                <p>No files loaded</p>
                            </div>
                         )
                    )}
                </div>

                <div className="space-y-6 flex flex-col">
                    <div className={`rounded-2xl border p-6 ${getConfidenceBg(entryPointConfidence)}`}>
                        <div className="flex items-center gap-3 mb-4">
                            <GitBranch size={20} className={getConfidenceColor(entryPointConfidence)} />
                            <h3 className="font-bold text-white">Entry Detection</h3>
                        </div>
                        
                        <div className="mb-4">
                            <p className="text-xs text-slate-400 mb-1 uppercase tracking-wider font-semibold">Detected Main File</p>
                            <div className="bg-black/30 rounded-xl p-3 font-mono text-sm text-white border border-white/10 flex items-center justify-between">
                                {entryPoint || 'None detected'}
                                {entryPointConfidence === 'high' && <CheckCircle size={16} className="text-emerald-500" />}
                            </div>
                        </div>

                        <div className="flex items-center justify-between text-xs">
                             <span className="text-slate-400">Confidence Score</span>
                             <span className={`font-bold px-2 py-1 rounded bg-black/20 ${getConfidenceColor(entryPointConfidence)} uppercase`}>
                                {entryPointConfidence || 'N/A'}
                             </span>
                        </div>
                    </div>

                    {fileTree?.dependencies?.has_requirements && (
                        <div className="bg-white/5 rounded-2xl border border-white/10 p-6 flex-1">
                            <div className="flex items-center gap-3 mb-4">
                                <Layers size={20} className="text-blue-400" />
                                <div>
                                    <h3 className="font-bold text-white">Dependencies</h3>
                                    <p className="text-xs text-slate-400">{fileTree.dependencies.python?.length || 0} packages identified</p>
                                </div>
                            </div>

                            <div className="flex flex-wrap gap-2 content-start h-full max-h-60 overflow-y-auto custom-scrollbar">
                                {fileTree.dependencies.python?.slice(0, 15).map((dep: string, i: number) => (
                                    <span
                                        key={i}
                                        className="px-3 py-1.5 bg-blue-500/10 text-blue-300 border border-blue-500/20 rounded-lg text-xs font-mono"
                                    >
                                        {dep}
                                    </span>
                                ))}
                                {fileTree.dependencies.python?.length > 15 && (
                                    <span className="px-3 py-1.5 bg-white/5 text-slate-400 border border-white/10 rounded-lg text-xs">
                                        +{fileTree.dependencies.python.length - 15} more
                                    </span>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
});

Step2Review.displayName = 'Step2Review';

export default Step2Review;
