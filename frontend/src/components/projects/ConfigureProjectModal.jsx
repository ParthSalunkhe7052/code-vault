import React, { useState } from 'react';
import { Upload, FileCode, Loader, X, CheckCircle, XCircle, Package, Terminal } from 'lucide-react';
import Modal from '../Modal';
import DirectBuildSection from './DirectBuildSection';
import CompilationModal from '../CompilationModal';

const ConfigureProjectModal = ({
    isOpen,
    onClose,
    project,
    configLoading,
    configData,
    setConfigData,
    saveMessage,
    uploadProgress,
    fileInputRef,
    onFileUpload,
    onZipUpload,
    onDeleteFile,
    onConfigSave,
    licenses = []
}) => {
    const [uploadType, setUploadType] = useState('single'); // 'single' or 'zip'
    const [showCompilationModal, setShowCompilationModal] = useState(false);
    const [buildConfig, setBuildConfig] = useState(null);

    const formatFileSize = (bytes) => {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={`Configure Project: ${project?.name || ''}`}
            size="full"
        >
            {configLoading ? (
                <div className="flex items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-indigo-500"></div>
                </div>
            ) : (
                <div className="flex flex-col gap-6">
                    {/* Toast Message */}
                    {saveMessage && (
                        <div className={`p-3 rounded-lg flex items-center gap-2 ${saveMessage.type === 'success'
                            ? 'bg-emerald-500/20 border border-emerald-500/30 text-emerald-400'
                            : 'bg-red-500/20 border border-red-500/30 text-red-400'
                            }`}>
                            {saveMessage.type === 'success' ? <CheckCircle size={16} /> : <XCircle size={16} />}
                            <span className="text-sm">{saveMessage.text}</span>
                        </div>
                    )}

                    {/* Two Column Layout */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* Left Column: Files & Config */}
                        <div className="space-y-6">
                            {/* Uploaded Files Section */}
                            <FileUploadSection
                                files={configData.files}
                                uploadProgress={uploadProgress}
                                uploadType={uploadType}
                                setUploadType={setUploadType}
                                fileInputRef={fileInputRef}
                                onFileUpload={onFileUpload}
                                onZipUpload={onZipUpload}
                                onDeleteFile={onDeleteFile}
                                formatFileSize={formatFileSize}
                                fileTree={configData.file_tree}
                            />

                            {/* Configuration Options */}
                            <div>
                                <label className="block text-sm font-medium text-slate-400 mb-2">
                                    Entry File
                                </label>
                                <select
                                    value={configData.entry_file}
                                    onChange={(e) => setConfigData({ ...configData, entry_file: e.target.value })}
                                    className="input w-full text-base py-3"
                                >
                                    <option value="">Select entry file...</option>
                                    {/* Show files from file_tree if ZIP uploaded, otherwise from files array */}
                                    {(() => {
                                        const isNodeJS = project?.language === 'nodejs';
                                        const isSourceFile = (f) => isNodeJS
                                            ? /\.(js|mjs|cjs|ts|tsx|jsx)$/.test(f)
                                            : f.endsWith('.py');

                                        return configData.file_tree ? (
                                            configData.file_tree.files.filter(isSourceFile).map((file, idx) => (
                                                <option key={idx} value={file}>
                                                    {file}
                                                </option>
                                            ))
                                        ) : (
                                            configData.files.filter(f => isSourceFile(f.original_filename)).map(file => (
                                                <option key={file.id} value={file.original_filename}>
                                                    {file.original_filename}
                                                </option>
                                            ))
                                        );
                                    })()}
                                </select>
                            </div>
                        </div>

                        {/* Right Column: Build Options */}
                        <div className="space-y-4">
                            <h3 className="text-sm font-medium text-slate-400">Build Options</h3>

                            {/* Native Build Section */}
                            <div className="min-h-[280px]">
                                <DirectBuildSection
                                    project={project}
                                    licenses={licenses}
                                    entryFile={configData.entry_file}
                                    hasUploadedFiles={(configData.files?.length > 0) || configData.file_tree}
                                    onBuildStart={(config) => {
                                        setBuildConfig(config);
                                        setShowCompilationModal(true);
                                    }}
                                />
                            </div>
                        </div>
                    </div>

                    {/* Actions */}
                    <div className="flex justify-end gap-3 pt-4 border-t border-white/10">
                        <button
                            type="button"
                            onClick={onClose}
                            className="btn btn-secondary"
                        >
                            Close
                        </button>
                        <button
                            type="button"
                            onClick={onConfigSave}
                            className="btn btn-primary"
                        >
                            Save Config
                        </button>
                    </div>
                </div>
            )}

            {/* Compilation Modal */}
            <CompilationModal
                isOpen={showCompilationModal}
                onClose={() => {
                    setShowCompilationModal(false);
                    setBuildConfig(null);
                }}
                projectPath={buildConfig?.projectPath || ''}
                entryFile={buildConfig?.entryFile || configData.entry_file}
                outputName={configData.entry_file?.replace(/\.(py|js|ts|mjs|cjs)$/, '') || 'output'}
                outputDir={buildConfig?.outputDir}
                licenseKey={buildConfig?.licenseKey}
                showConsole={buildConfig?.showConsole ?? true}
                // New enhanced options
                bundleRequirements={buildConfig?.bundleRequirements ?? false}
                envValues={buildConfig?.envValues}
                buildFrontend={buildConfig?.buildFrontend ?? false}
                splitFrontend={buildConfig?.splitFrontend ?? false}
                createLauncher={buildConfig?.createLauncher ?? true}
                frontendDir={buildConfig?.frontendDir}
                onComplete={() => {
                    setShowCompilationModal(false);
                    setBuildConfig(null);
                }}
            />
        </Modal>
    );
};

const FileUploadSection = ({
    files,
    uploadProgress,
    uploadType,
    setUploadType,
    fileInputRef,
    onFileUpload,
    onZipUpload,
    onDeleteFile,
    formatFileSize,
    fileTree
}) => {
    const zipInputRef = React.useRef(null);

    return (
        <div>
            <label className="block text-sm font-medium text-slate-400 mb-3">
                Project Files ({fileTree ? fileTree.total_files : files.length})
            </label>

            {/* Upload Type Selector */}
            <div className="flex gap-3 mb-4">
                <button
                    type="button"
                    onClick={() => setUploadType('single')}
                    className={`flex-1 px-4 py-2 rounded-lg border transition-all ${uploadType === 'single'
                        ? 'bg-indigo-600 border-indigo-500 text-white'
                        : 'bg-white/5 border-white/10 text-slate-400 hover:border-indigo-500/50'
                        }`}
                >
                    <FileCode size={16} className="inline mr-2" />
                    Single Files
                </button>
                <button
                    type="button"
                    onClick={() => setUploadType('zip')}
                    className={`flex-1 px-4 py-2 rounded-lg border transition-all ${uploadType === 'zip'
                        ? 'bg-indigo-600 border-indigo-500 text-white'
                        : 'bg-white/5 border-white/10 text-slate-400 hover:border-indigo-500/50'
                        }`}
                >
                    <Package size={16} className="inline mr-2" />
                    📁 Entire Project (ZIP)
                </button>
            </div>

            {/* File Tree Display (if ZIP uploaded) */}
            {fileTree && (
                <div className="mb-4 p-4 bg-white/5 rounded-lg border border-white/10">
                    <div className="flex items-center justify-between mb-3">
                        <h4 className="text-sm font-semibold text-white">Project Structure</h4>
                        <span className="text-xs text-slate-400">{fileTree.total_files} files</span>
                    </div>
                    <div className="space-y-1 max-h-32 overflow-y-auto text-xs font-mono">
                        <div className="text-green-400">📁 {fileTree.entry_point} (entry point)</div>
                        {fileTree.files.slice(0, 10).map((file, i) => (
                            file !== fileTree.entry_point && (
                                <div key={i} className="text-slate-400 pl-4">📄 {file}</div>
                            )
                        ))}
                        {fileTree.files.length > 10 && (
                            <div className="text-slate-500 pl-4">... and {fileTree.files.length - 10} more</div>
                        )}
                    </div>
                    {fileTree.dependencies?.has_requirements && (
                        <div className="mt-3 pt-3 border-t border-white/10">
                            <div className="text-xs font-semibold text-slate-400 mb-2">
                                📦 Dependencies ({fileTree.dependencies.python.length})
                            </div>
                            <div className="flex flex-wrap gap-1">
                                {fileTree.dependencies.python.slice(0, 5).map((dep, i) => (
                                    <span key={i} className="px-2 py-1 bg-blue-500/20 text-blue-400 rounded text-xs">
                                        {dep}
                                    </span>
                                ))}
                                {fileTree.dependencies.python.length > 5 && (
                                    <span className="px-2 py-1 bg-slate-500/20 text-slate-400 rounded text-xs">
                                        +{fileTree.dependencies.python.length - 5} more
                                    </span>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Regular Files Display */}
            {!fileTree && files.length > 0 && (
                <div className="space-y-2 mb-4 max-h-48 overflow-y-auto">
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
            )}

            {/* Upload Area */}
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
                        className="border-2 border-dashed border-white/10 rounded-xl p-8 flex flex-col items-center justify-center text-center hover:border-indigo-500/50 hover:bg-indigo-500/5 transition-all cursor-pointer group/upload"
                    >
                        {uploadProgress ? (
                            <div className="flex items-center gap-2 text-indigo-400">
                                <Loader size={24} className="animate-spin" />
                                <span>Uploading ZIP...</span>
                            </div>
                        ) : (
                            <>
                                <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-3 group-hover/upload:scale-110 transition-transform">
                                    <Package size={32} className="text-slate-400 group-hover/upload:text-indigo-400" />
                                </div>
                                <p className="text-sm text-slate-300 font-medium">Upload ZIP File</p>
                                <p className="text-xs text-slate-500 mt-1">Entire project with folder structure</p>
                                <div className="mt-4 bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 text-left">
                                    <p className="text-xs font-semibold text-blue-400 mb-1">📝 How to prepare:</p>
                                    <ol className="text-xs text-slate-400 space-y-1 list-decimal list-inside">
                                        <li>Put all project files in one folder</li>
                                        <li>Right-click → Send to → Compressed folder</li>
                                        <li>Upload the .zip here</li>
                                    </ol>
                                </div>
                            </>
                        )}
                    </div>
                </div>
            ) : (
                <div
                    onClick={() => fileInputRef.current?.click()}
                    className="border-2 border-dashed border-white/10 rounded-xl p-6 flex flex-col items-center justify-center text-center hover:border-indigo-500/50 hover:bg-indigo-500/5 transition-all cursor-pointer group/upload"
                >
                    {uploadProgress ? (
                        <div className="flex items-center gap-2 text-indigo-400">
                            <Loader size={24} className="animate-spin" />
                            <span>Uploading...</span>
                        </div>
                    ) : (
                        <>
                            <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center mb-3 group-hover/upload:scale-110 transition-transform">
                                <Upload size={24} className="text-slate-400 group-hover/upload:text-indigo-400" />
                            </div>
                            <p className="text-sm text-slate-300 font-medium">Click to upload files</p>
                            <p className="text-xs text-slate-500 mt-1">Source files</p>
                        </>
                    )}
                    <input
                        ref={fileInputRef}
                        type="file"
                        multiple
                        accept=".py,.pyw,.js,.mjs,.cjs,.ts,.tsx,.jsx,.txt,.json,.yaml,.yml,.toml,.ini,.cfg"
                        className="hidden"
                        onChange={onFileUpload}
                    />
                </div>
            )}
        </div>
    );
};

const CompileStatusSection = ({ status, onDownload }) => (
    <div className={`rounded-xl p-4 border ${status.status === 'completed' ? 'bg-emerald-500/10 border-emerald-500/20' :
        status.status === 'failed' ? 'bg-red-500/10 border-red-500/20' :
            'bg-indigo-500/10 border-indigo-500/20'
        }`}>
        <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
                {status.status === 'completed' ? (
                    <CheckCircle size={18} className="text-emerald-400" />
                ) : status.status === 'failed' ? (
                    <XCircle size={18} className="text-red-400" />
                ) : (
                    <Loader size={18} className="text-indigo-400 animate-spin" />
                )}
                <span className="font-medium text-white capitalize">{status.status}</span>
            </div>
            <span className="text-sm text-slate-400">{status.progress}%</span>
        </div>
        <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
            <div
                className={`h-full rounded-full transition-all duration-500 ${status.status === 'completed' ? 'bg-emerald-500' :
                    status.status === 'failed' ? 'bg-red-500' :
                        'bg-indigo-500'
                    }`}
                style={{ width: `${status.progress}%` }}
            />
        </div>
        {status.logs && status.logs.length > 0 && (
            <div className="mt-3 text-xs text-slate-400 font-mono max-h-24 overflow-y-auto">
                {status.logs.slice(-5).map((log, i) => (
                    <div key={i}>{log}</div>
                ))}
            </div>
        )}
        {status.error_message && (
            <p className="mt-2 text-sm text-red-400">{status.error_message}</p>
        )}
        {status.status === 'completed' && status.output_filename && (
            <div className="mt-4 flex items-center justify-between p-3 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
                <div className="flex items-center gap-2">
                    <FileCode size={18} className="text-emerald-400" />
                    <span className="text-sm text-white font-medium">{status.output_filename}</span>
                </div>
                <button
                    onClick={() => onDownload(status.id, status.output_filename)}
                    className="btn btn-primary text-sm py-1.5 px-3"
                >
                    <Download size={16} />
                    Download
                </button>
            </div>
        )}
    </div>
);

export default ConfigureProjectModal;
