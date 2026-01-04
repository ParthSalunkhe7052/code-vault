import React, { useRef } from 'react';
import { Upload, Package, Loader, FileCode, X } from 'lucide-react';

/**
 * Step1Upload - First step of the wizard
 * Handles single file or ZIP upload with drag-and-drop support
 */
const Step1Upload = ({
    onFileUpload,
    onZipUpload,
    uploadProgress,
    files = [],
    fileTree,
    onDeleteFile,
    project
}) => {
    const isNodeJS = project?.language === 'nodejs';
    const langName = isNodeJS ? 'Node.js' : 'Python';
    const fileTypes = isNodeJS ? '.js, .ts, .mjs' : '.py';
    const depFile = isNodeJS ? 'package.json' : 'requirements.txt';

    const [uploadType, setUploadType] = React.useState('zip');
    const fileInputRef = useRef(null);
    const zipInputRef = useRef(null);

    const formatFileSize = (bytes) => {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        e.stopPropagation();
    };

    const handleDrop = (e) => {
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
    };

    const hasFiles = files.length > 0 || fileTree;

    return (
        <div className="space-y-6">
            <div className="text-center mb-6">
                <h2 className="text-xl font-bold text-white mb-2">Upload Your Project</h2>
                <p className="text-slate-400 text-sm">
                    Upload your {langName} project as a ZIP file or individual files
                </p>
            </div>

            {/* Upload Type Selector */}
            <div className="flex gap-3 mb-6">
                <button
                    type="button"
                    onClick={() => setUploadType('zip')}
                    className={`flex-1 px-4 py-3 rounded-xl border transition-all ${uploadType === 'zip'
                        ? 'bg-indigo-600 border-indigo-500 text-white'
                        : 'bg-white/5 border-white/10 text-slate-400 hover:border-indigo-500/50'
                        }`}
                >
                    <Package size={20} className="inline mr-2" />
                    📁 Entire Project (ZIP)
                </button>
                <button
                    type="button"
                    onClick={() => setUploadType('single')}
                    className={`flex-1 px-4 py-3 rounded-xl border transition-all ${uploadType === 'single'
                        ? 'bg-indigo-600 border-indigo-500 text-white'
                        : 'bg-white/5 border-white/10 text-slate-400 hover:border-indigo-500/50'
                        }`}
                >
                    <FileCode size={20} className="inline mr-2" />
                    Single Files
                </button>
            </div>

            {/* Upload Zone */}
            {uploadType === 'zip' ? (
                <div>
                    <input
                        ref={zipInputRef}
                        type="file"
                        accept=".zip"
                        onChange={onZipUpload}
                        className="hidden"
                    />
                    <div
                        onClick={() => zipInputRef.current?.click()}
                        onDragOver={handleDragOver}
                        onDrop={handleDrop}
                        className="border-2 border-dashed border-white/20 rounded-2xl p-12 flex flex-col items-center justify-center text-center hover:border-indigo-500/50 hover:bg-indigo-500/5 transition-all cursor-pointer group"
                    >
                        {uploadProgress ? (
                            <div className="flex items-center gap-3 text-indigo-400">
                                <Loader size={32} className="animate-spin" />
                                <span className="text-lg">Uploading & extracting ZIP...</span>
                            </div>
                        ) : (
                            <>
                                <div className="w-20 h-20 rounded-full bg-white/5 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                                    <Package size={40} className="text-slate-400 group-hover:text-indigo-400" />
                                </div>
                                <p className="text-lg text-slate-300 font-medium mb-2">
                                    Drop your ZIP file here
                                </p>
                                <p className="text-sm text-slate-500 mb-4">
                                    or click to browse
                                </p>
                                <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4 text-left max-w-sm">
                                    <p className="text-xs font-semibold text-blue-400 mb-2">📝 How to prepare:</p>
                                    <ol className="text-xs text-slate-400 space-y-1 list-decimal list-inside">
                                        <li>Put all project files in one folder</li>
                                        <li>Include <code className="bg-white/10 px-1 rounded">{depFile}</code> if needed</li>
                                        <li>Right-click → Send to → Compressed folder</li>
                                    </ol>
                                </div>
                            </>
                        )}
                    </div>
                </div>
            ) : (
                <div>
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
                    <div
                        onClick={() => fileInputRef.current?.click()}
                        onDragOver={handleDragOver}
                        onDrop={handleDrop}
                        className="border-2 border-dashed border-white/20 rounded-2xl p-12 flex flex-col items-center justify-center text-center hover:border-indigo-500/50 hover:bg-indigo-500/5 transition-all cursor-pointer group"
                    >
                        {uploadProgress ? (
                            <div className="flex items-center gap-3 text-indigo-400">
                                <Loader size={32} className="animate-spin" />
                                <span className="text-lg">Uploading files...</span>
                            </div>
                        ) : (
                            <>
                                <div className="w-20 h-20 rounded-full bg-white/5 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                                    <Upload size={40} className="text-slate-400 group-hover:text-indigo-400" />
                                </div>
                                <p className="text-lg text-slate-300 font-medium mb-2">
                                    Drop {langName} files here
                                </p>
                                <p className="text-sm text-slate-500">
                                    or click to browse ({fileTypes})
                                </p>
                            </>
                        )}
                    </div>
                </div>
            )}

            {/* Uploaded Files Display */}
            {files.length > 0 && !fileTree && (
                <div className="space-y-2 mt-6">
                    <label className="text-sm font-medium text-slate-400">
                        Uploaded Files ({files.length})
                    </label>
                    <div className="max-h-48 overflow-y-auto space-y-2">
                        {files.map((file) => (
                            <div
                                key={file.id}
                                className="flex items-center justify-between bg-white/5 rounded-lg p-3 border border-white/10"
                            >
                                <div className="flex items-center gap-3">
                                    <FileCode size={18} className="text-indigo-400" />
                                    <div>
                                        <p className="text-sm text-white font-medium">{file.original_filename}</p>
                                        <p className="text-xs text-slate-500">{formatFileSize(file.file_size)}</p>
                                    </div>
                                </div>
                                <button
                                    type="button"
                                    onClick={() => onDeleteFile(file.id)}
                                    className="p-1.5 rounded hover:bg-red-500/20 text-slate-400 hover:text-red-400 transition-colors"
                                >
                                    <X size={16} />
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Success indicator */}
            {hasFiles && (
                <div className="mt-6 p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-center">
                    <p className="text-emerald-400 font-medium">
                        ✓ {fileTree ? `${fileTree.total_files} files ready` : `${files.length} files uploaded`}
                    </p>
                    <p className="text-sm text-slate-400 mt-1">
                        Click "Next" to review your project structure
                    </p>
                </div>
            )}
        </div>
    );
};

export default Step1Upload;
