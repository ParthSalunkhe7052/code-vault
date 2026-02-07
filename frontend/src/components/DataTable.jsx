import { useState, useMemo } from 'react';
import { ChevronDown, ChevronUp, Search, ChevronLeft, ChevronRight } from 'lucide-react';

const DataTable = ({
    data = [],
    columns = [],
    searchable = true,
    searchPlaceholder = "Search...",
    pageSize = 10,
    sortable = true,
    emptyMessage = "No data found",
    className = "",
}) => {
    const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
    const [searchTerm, setSearchTerm] = useState('');
    const [currentPage, setCurrentPage] = useState(1);

    // Handle sorting
    const handleSort = (key) => {
        if (!sortable) return;
        
        setSortConfig(current => ({
            key,
            direction: current.key === key && current.direction === 'asc' ? 'desc' : 'asc'
        }));
    };

    // Filter and sort data
    const processedData = useMemo(() => {
        let result = [...data];

        // Filter
        if (searchable && searchTerm) {
            const lowerSearch = searchTerm.toLowerCase();
            result = result.filter(row =>
                columns.some(col => {
                    const value = col.accessor ? row[col.accessor] : row[col.key];
                    if (value === null || value === undefined) return false;
                    return String(value).toLowerCase().includes(lowerSearch);
                })
            );
        }

        // Sort
        if (sortConfig.key) {
            result.sort((a, b) => {
                const aVal = columns.find(col => col.key === sortConfig.key)?.accessor 
                    ? a[columns.find(col => col.key === sortConfig.key).accessor] 
                    : a[sortConfig.key];
                const bVal = columns.find(col => col.key === sortConfig.key)?.accessor 
                    ? b[columns.find(col => col.key === sortConfig.key).accessor] 
                    : b[sortConfig.key];

                if (aVal === null || aVal === undefined) return 1;
                if (bVal === null || bVal === undefined) return -1;

                if (typeof aVal === 'string') {
                    return sortConfig.direction === 'asc' 
                        ? aVal.localeCompare(bVal)
                        : bVal.localeCompare(aVal);
                }

                return sortConfig.direction === 'asc' 
                    ? (aVal > bVal ? 1 : -1)
                    : (aVal < bVal ? 1 : -1);
            });
        }

        return result;
    }, [data, columns, searchTerm, sortConfig, searchable]);

    // Pagination
    const totalPages = Math.ceil(processedData.length / pageSize);
    const paginatedData = processedData.slice(
        (currentPage - 1) * pageSize,
        currentPage * pageSize
    );

    const goToPage = (page) => {
        setCurrentPage(Math.max(1, Math.min(page, totalPages)));
    };

    return (
        <div className={`w-full ${className}`}>
            {/* Search */}
            {searchable && (
                <div className="mb-4 relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input
                        type="text"
                        placeholder={searchPlaceholder}
                        value={searchTerm}
                        onChange={(e) => {
                            setSearchTerm(e.target.value);
                            setCurrentPage(1);
                        }}
                        className="w-full max-w-md pl-10 pr-4 py-2 bg-surface border border-white/10 rounded-lg 
                                   text-white placeholder-slate-400 focus:outline-none focus:border-white/20
                                   transition-colors"
                    />
                </div>
            )}

            {/* Table */}
            <div className="overflow-x-auto border border-white/10 rounded-lg">
                <table className="w-full">
                    <thead className="bg-white/[0.02] border-b border-white/10">
                        <tr>
                            {columns.map((col) => (
                                <th
                                    key={col.key}
                                    onClick={() => handleSort(col.key)}
                                    className={`px-4 py-3 text-left text-sm font-medium text-slate-300 
                                               ${sortable ? 'cursor-pointer hover:text-white' : ''} 
                                               ${col.className || ''}`}
                                >
                                    <div className="flex items-center gap-1">
                                        {col.label}
                                        {sortable && sortConfig.key === col.key && (
                                            sortConfig.direction === 'asc' 
                                                ? <ChevronUp className="w-4 h-4" />
                                                : <ChevronDown className="w-4 h-4" />
                                        )}
                                    </div>
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                        {paginatedData.length === 0 ? (
                            <tr>
                                <td 
                                    colSpan={columns.length} 
                                    className="px-4 py-8 text-center text-slate-400"
                                >
                                    {searchTerm ? 'No results found' : emptyMessage}
                                </td>
                            </tr>
                        ) : (
                            paginatedData.map((row, idx) => (
                                <tr 
                                    key={row.id || idx}
                                    className="hover:bg-white/[0.02] transition-colors"
                                >
                                    {columns.map((col) => (
                                        <td 
                                            key={col.key} 
                                            className={`px-4 py-3 text-sm text-slate-300 ${col.cellClassName || ''}`}
                                        >
                                            {col.render 
                                                ? col.render(row)
                                                : col.accessor 
                                                    ? row[col.accessor]
                                                    : row[col.key]
                                            }
                                        </td>
                                    ))}
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4 px-2">
                    <div className="text-sm text-slate-400">
                        Showing {((currentPage - 1) * pageSize) + 1} to {Math.min(currentPage * pageSize, processedData.length)} of {processedData.length} results
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => goToPage(currentPage - 1)}
                            disabled={currentPage === 1}
                            className="p-2 rounded-lg border border-white/10 text-slate-300 
                                       hover:bg-white/5 disabled:opacity-50 disabled:cursor-not-allowed
                                       transition-colors"
                        >
                            <ChevronLeft className="w-4 h-4" />
                        </button>
                        
                        {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                            let pageNum;
                            if (totalPages <= 5) {
                                pageNum = i + 1;
                            } else if (currentPage <= 3) {
                                pageNum = i + 1;
                            } else if (currentPage >= totalPages - 2) {
                                pageNum = totalPages - 4 + i;
                            } else {
                                pageNum = currentPage - 2 + i;
                            }
                            
                            return (
                                <button
                                    key={pageNum}
                                    onClick={() => goToPage(pageNum)}
                                    className={`w-8 h-8 rounded-lg text-sm font-medium transition-colors
                                               ${currentPage === pageNum 
                                                   ? 'bg-indigo-500 text-white' 
                                                   : 'border border-white/10 text-slate-300 hover:bg-white/5'
                                               }`}
                                >
                                    {pageNum}
                                </button>
                            );
                        })}
                        
                        <button
                            onClick={() => goToPage(currentPage + 1)}
                            disabled={currentPage === totalPages}
                            className="p-2 rounded-lg border border-white/10 text-slate-300 
                                       hover:bg-white/5 disabled:opacity-50 disabled:cursor-not-allowed
                                       transition-colors"
                        >
                            <ChevronRight className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default DataTable;
