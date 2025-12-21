import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import LicenseRow from './LicenseRow';

const LicenseTable = ({
    licenses,
    loading,
    selectedLicenses,
    onSelectAll,
    onSelectLicense,
    onViewBindings,
    onRevoke,
    onDelete,
    getProjectName,
    copyToClipboard,
    // Pagination
    currentPage,
    totalPages,
    itemsPerPage,
    totalItems,
    onPageChange
}) => {
    return (
        <div className="glass-card overflow-hidden">
            <div className="table-container border-0 bg-transparent">
                <table>
                    <thead>
                        <tr>
                            <th className="w-12">
                                <input
                                    type="checkbox"
                                    checked={selectedLicenses.size === licenses.length && licenses.length > 0}
                                    onChange={onSelectAll}
                                    className="rounded border-slate-600 bg-slate-800 text-indigo-500 focus:ring-indigo-500"
                                />
                            </th>
                            <th>License Key</th>
                            <th>Project</th>
                            <th>Client Details</th>
                            <th>Status</th>
                            <th>Expires</th>
                            <th>Usage</th>
                            <th>Features</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {licenses.length === 0 ? (
                            <tr>
                                <td colSpan="9" className="text-center py-12 text-slate-500">
                                    {loading ? 'Loading...' : 'No licenses found.'}
                                </td>
                            </tr>
                        ) : (
                            licenses.map((license, index) => (
                                <LicenseRow
                                    key={license.id}
                                    license={license}
                                    isSelected={selectedLicenses.has(license.id)}
                                    onSelect={onSelectLicense}
                                    onViewBindings={onViewBindings}
                                    onRevoke={onRevoke}
                                    onDelete={onDelete}
                                    getProjectName={getProjectName}
                                    copyToClipboard={copyToClipboard}
                                    animationDelay={index * 50}
                                />
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
                <div className="flex items-center justify-between px-6 py-4 border-t border-white/10">
                    <span className="text-sm text-slate-400">
                        Showing {((currentPage - 1) * itemsPerPage) + 1} to {Math.min(currentPage * itemsPerPage, totalItems)} of {totalItems} licenses
                    </span>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => onPageChange(currentPage - 1)}
                            disabled={currentPage === 1}
                            className="p-2 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            <ChevronLeft size={18} />
                        </button>
                        {[...Array(totalPages)].map((_, i) => (
                            <button
                                key={i + 1}
                                onClick={() => onPageChange(i + 1)}
                                className={`w-8 h-8 rounded-lg text-sm font-medium transition-colors ${
                                    currentPage === i + 1
                                        ? 'bg-indigo-500 text-white'
                                        : 'hover:bg-white/10 text-slate-400'
                                }`}
                            >
                                {i + 1}
                            </button>
                        )).slice(
                            Math.max(0, currentPage - 3),
                            Math.min(totalPages, currentPage + 2)
                        )}
                        <button
                            onClick={() => onPageChange(currentPage + 1)}
                            disabled={currentPage === totalPages}
                            className="p-2 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            <ChevronRight size={18} />
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default LicenseTable;
