import { useRef, useState, useMemo, useCallback, memo } from 'react';
import { Upload, Package, Loader, FileCode, X, Cloud, ArrowUpCircle } from 'lucide-react';

/**
 * Step1Upload - Redesigned for Mission Control
 * "Hero" style upload area
 */
const Step1Upload = memo(({
    onFileUpload,
    onZipUpload,
    uploadProgress,
    files = [],
    fileTree,
    onDeleteFile,
    project
}) => {
    // Memoized language-specific values
    const isNodeJS = useMemo(() => project?.language === 'nodejs', [project?.language]);
    const langName = useMemo(() => isNodeJS ? 'Node.js' : 'Python', [isNodeJS]);
    const fileTypes = useMemo(() => isNodeJS ? '.js, .ts, .mjs' : '.py', [isNodeJS]);
    const depFile = useMemo(() => isNodeJS ? 'package.json' : 'requirements.txt', [isNodeJS]);

    const [uploadType, setUploadType] = useState('zip');
    const fileInputRef = useRef(null);
    const zipInputRef = useRef(null);

    // Memoized formatFileSize
    const formatFileSize = useCallback((bytes) => {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }, []);

    // Memoized drag/drop handlers
    const handleDragOver = useCallback((e) => {
        e.preventDefault();
        e.stopPropagation();
    }, []);

    const handleDrop = useCallback((e) => {
        e.preventDefault();
        e.stopPropagation();

        const droppedFiles = e.dataTransfer.files;
        if (droppedFiles.length === 0) return;

        const file = droppedFiles[0];
        if (file.name.endsWith('.zip')) {
            onZipUpload({ target: { files: [file] } });
        } else {
            onFileUpload({ target: { files: droppedFiles } });
        }
    }, [onZipUpload, onFileUpload]);

    // Memoized click handlers
    const handleZipClick = useCallback(() => {
        zipInputRef.current?.click();
    }, []);

    const handleFileClick = useCallback(() => {
        fileInputRef.current?.click();
    }, []);

    const handleDeleteFile = useCallback((fileId) => {
        onDeleteFile(fileId);
    }, [onDeleteFile]);

    // Memoized upload type toggles
    const toggleToZip = useCallback(() => setUploadType('zip'), []);
    const toggleToSingle = useCallback(() => setUploadType('single'), []);

    const hasFiles = useMemo(() => files.length > 0 || fileTree, [files, fileTree]);

    return (
        <div className="space-y-8 animate-in fade-in duration-500 max-w-5xl mx-auto">
            <div className="text-left">
                <h2 className="text-2xl font-bold text-white mb-2 tracking-tight">Project Source</h2>
                <p className="text-slate-400">
                    Import your {langName} codebase. We support ZIP archives or direct file uploads.
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Left Column: Controls & Instructions */}
                <div className="space-y-6">
                    <div className="bg-white/5 rounded-2xl p-1 border border-white/10 flex">
                        <button
                            type="button"
                            onClick={toggleToZip}
                            className={`flex-1 px-4 py-3 rounded-xl transition-all font-medium text-sm flex items-center justify-center gap-2 ${uploadType === 'zip'
                                ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20'
                                : 'text-slate-400 hover:text-white hover:bg-white/5'
                                }`}
                        >
                            <Package size={18} />
                            ZIP Archive
                        </button>
                        <button
                            type="button"
                            onClick={toggleToSingle}
                            className={`flex-1 px-4 py-3 rounded-xl transition-all font-medium text-sm flex items-center justify-center gap-2 ${uploadType === 'single'
                                ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20'
                                : 'text-slate-400 hover:text-white hover:bg-white/5'
                                }`}
                        >
                            <FileCode size={18} />
                            Files
                        </button>
                    </div>

                    <div className="bg-blue-500/5 border border-blue-500/10 rounded-2xl p-6">
                        <h3 className="text-blue-400 font-semibold mb-3 flex items-center gap-2">
                            <Cloud size={18} />
                            Preparation Guide
                        </h3>
                        <ul className="space-y-3 text-sm text-slate-300">
                            <li className="flex items-start gap-3">
                                <span className="w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center text-xs font-bold mt-0.5">1</span>
                                <span>Ensure all source files are in the root or structured folders.</span>
                            </li>
                            <li className="flex items-start gap-3">
                                <span className="w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center text-xs font-bold mt-0.5">2</span>
                                <span>Include <code className="bg-blue-500/20 px-1.5 py-0.5 rounded text-blue-300">{depFile}</code> for auto-dependency detection.</span>
                            </li>
                            <li className="flex items-start gap-3">
                                <span className="w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center text-xs font-bold mt-0.5">3</span>
                                <span>Remove build artifacts (node_modules, venv, __pycache__) to save time.</span>
                            </li>
                        </ul>
                    </div>
                </div>

                {/* Right Column: Upload Zone (Spans 2 cols) */}
                <div className="lg:col-span-2">
                    {uploadType === 'zip' ? (
                        <div className="h-full">
                            <input
                                ref={zipInputRef}
                                type="file"
                                accept=".zip"
                                onChange={onZipUpload}
                                className="hidden"
                            />
                            <div
                                onClick={handleZipClick}
                                onDragOver={handleDragOver}
                                onDrop={handleDrop}
                                className={`
                                    h-80 border-2 border-dashed rounded-3xl flex flex-col items-center justify-center text-center transition-all cursor-pointer group relative overflow-hidden
                                    ${uploadProgress 
                                        ? 'border-indigo-500/50 bg-indigo-500/5' 
                                        : 'border-white/10 hover:border-indigo-500/50 hover:bg-indigo-500/5 bg-white/5'
                                    }
                                `}
                            >
                                {/* Background decoration */}
                                <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

                                {uploadProgress ? (
                                    <div className="relative z-10 flex flex-col items-center gap-4">
                                        <div className="relative">
                                            <div className="w-20 h-20 rounded-full border-4 border-indigo-500/30 border-t-indigo-500 animate-spin" />
                                            <div className="absolute inset-0 flex items-center justify-center">
                                                <Cloud size={24} className="text-indigo-400" />
                                            </div>
                                        </div>
                                        <div>
                                            <h3 className="text-xl font-bold text-white mb-1">Uploading...</h3>
                                            <p className="text-slate-400">Extracting project files</p>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="relative z-10 flex flex-col items-center gap-6 p-8">
                                        <div className="w-24 h-24 rounded-full bg-indigo-500/10 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                                            <ArrowUpCircle size={48} className="text-indigo-400" />
                                        </div>
                                        <div>
                                            <h3 className="text-2xl font-bold text-white mb-2">Drop Project ZIP</h3>
                                            <p className="text-slate-400">or click to browse</p>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    ) : (
                        <div className="h-full flex flex-col">
                            <input
                                ref={fileInputRef}
                                type="file"
                                multiple
                                accept={isNodeJS
                                    ? ".js,.mjs,.cjs,.ts,.tsx,.jsx,.json,.yaml,.yml"
                                    : ".py,.pyw,.txt,.json,.yaml,.yml,.toml,.ini,.cfg"}
                                onChange={onFileUpload}
                                className="hidden"
                            />
                            
                            {!hasFiles && (
                                <div
                                    onClick={handleFileClick}
                                    onDragOver={handleDragOver}
                                    onDrop={handleDrop}
                                    className="flex-1 h-80 border-2 border-dashed border-white/10 hover:border-indigo-500/50 hover:bg-indigo-500/5 bg-white/5 rounded-3xl flex flex-col items-center justify-center text-center transition-all cursor-pointer group"
                                >
                                    <div className="w-20 h-20 rounded-full bg-indigo-500/10 flex items-center justify-center group-hover:scale-110 transition-transform mb-4">
                                        <FileCode size={40} className="text-indigo-400" />
                                    </div>
                                    <h3 className="text-xl font-bold text-white mb-2">Select Source Files</h3>
                                    <p className="text-slate-400">Drag & drop {fileTypes}</p>
                                </div>
                            )}

                            {hasFiles && (
                                <div className="bg-white/5 rounded-2xl border border-white/10 overflow-hidden flex flex-col h-80">
                                    <div className="p-4 border-b border-white/10 flex items-center justify-between bg-white/5">
                                        <span className="font-semibold text-white">Files Ready ({files.length})</span>
                                        <button 
                                            onClick={handleFileClick}
                                            className="text-xs bg-indigo-500/20 text-indigo-300 px-3 py-1.5 rounded-lg hover:bg-indigo-500/30 transition-colors"
                                        >
                                            + Add More
                                        </button>
                                    </div>
                                    <div className="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar">
                                        {files.map((file) => (
                                            <div
                                                key={file.id}
                                                className="flex items-center justify-between p-3 rounded-xl hover:bg-white/5 group transition-colors"
                                            >
                                                <div className="flex items-center gap-3">
                                                    <div className="w-8 h-8 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400">
                                                        <FileCode size={16} />
                                                    </div>
                                                    <div>
                                                        <p className="text-sm font-medium text-white">{file.original_filename}</p>
                                                        <p className="text-xs text-slate-500">{formatFileSize(file.file_size)}</p>
                                                    </div>
                                                </div>
                                                <button
                                                    onClick={() => handleDeleteFile(file.id)}
                                                    className="p-2 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg opacity-0 group-hover:opacity-100 transition-all"
                                                >
                                                    <X size={16} />
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* Success indicator */}
            {hasFiles && (
                <div className="flex items-center justify-between p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl animate-in slide-in-from-bottom-2">
                    <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-full bg-emerald-500/20 flex items-center justify-center text-emerald-400">
                            <Package size={20} />
                        </div>
                        <div>
                            <h4 className="font-bold text-white">Project Uploaded</h4>
                            <p className="text-sm text-emerald-400/70">
                                {fileTree ? `${fileTree.total_files} files processed successfully` : `${files.length} files staged`}
                            </p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
});

Step1Upload.displayName = 'Step1Upload';

export default Step1Upload;
