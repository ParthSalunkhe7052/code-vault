import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

const TrendIndicator = ({ value }) => {
    const isPositive = value >= 0;
    const Icon = isPositive ? TrendingUp : TrendingDown;
    
    return (
        <div className={`flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full ${
            isPositive 
                ? 'text-emerald-400 bg-emerald-500/10' 
                : 'text-red-400 bg-red-500/10'
        }`}>
            <Icon size={12} />
            <span>{Math.abs(value)}%</span>
        </div>
    );
};

const StatCard = ({ title, value, icon: Icon, color, subtitle, trend }) => (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-gray-900/95 to-gray-800/90 
        border border-white/15 p-6 group hover:border-primary/40 transition-all duration-300
        shadow-lg shadow-black/20 hover:shadow-xl hover:shadow-black/30">
        
        {/* Subtle gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent 
            opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
        
        {/* Glow effect on hover */}
        <div className="absolute -inset-1 bg-gradient-to-r from-primary/20 to-secondary/20 
            rounded-2xl blur opacity-0 group-hover:opacity-30 transition-opacity duration-500" />
        
        <div className="relative z-10">
            <div className="flex items-start justify-between mb-4">
                <div className={`p-3 rounded-xl bg-gray-800/80 border border-white/10 ${color}
                    group-hover:scale-110 transition-transform duration-300`}>
                    <Icon size={22} />
                </div>
                {trend !== undefined && (
                    <TrendIndicator value={trend} />
                )}
            </div>
            <div>
                <h3 className="text-4xl font-bold text-white mb-1 tabular-nums">{value}</h3>
                <p className="text-slate-400 text-sm font-medium">{title}</p>
                {subtitle && (
                    <p className="text-xs text-slate-500 mt-2 flex items-center gap-1">
                        <span className="w-1 h-1 rounded-full bg-slate-500" />
                        {subtitle}
                    </p>
                )}
            </div>
        </div>
    </div>
);

export default StatCard;
