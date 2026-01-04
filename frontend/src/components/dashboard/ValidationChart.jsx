import React from 'react';
import { BarChart3 } from 'lucide-react';

const ValidationChart = ({ history }) => {
    if (!history || history.length === 0) {
        return null;
    }

    return (
        <div className="glass-card p-6">
            <div className="flex items-center gap-2 mb-6">
                <BarChart3 size={20} className="text-indigo-400" />
                <h2 className="text-lg font-semibold text-white">Validation History (7 Days)</h2>
            </div>
            <div className="flex items-end gap-2 h-32">
                {history.map((day, i) => {
                    const maxTotal = Math.max(...history.map(d => d.total));
                    const height = maxTotal > 0 ? (day.total / maxTotal) * 100 : 0;
                    const successRate = day.total > 0 ? (day.successful / day.total) : 1;
                    
                    return (
                        <div key={i} className="flex-1 flex flex-col items-center gap-2">
                            <div className="w-full flex flex-col justify-end h-24">
                                <div 
                                    className="w-full bg-gradient-to-t from-indigo-500 to-indigo-400 rounded-t opacity-80 hover:opacity-100 transition-opacity"
                                    style={{ height: `${height}%`, minHeight: day.total > 0 ? '4px' : '0' }}
                                    title={`${day.total} validations, ${Math.round(successRate * 100)}% success`}
                                />
                            </div>
                            <span className="text-xs text-slate-500">
                                {new Date(day.day).toLocaleDateString('en', { weekday: 'short' })}
                            </span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default ValidationChart;
