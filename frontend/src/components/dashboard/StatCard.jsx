import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

const TrendIndicator = ({ value }) => {
    const isPositive = value >= 0;
    const Icon = isPositive ? TrendingUp : TrendingDown;

    return (
        <div className={`flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full ${isPositive
                ? 'text-emerald-400 bg-emerald-500/10'
                : 'text-red-400 bg-red-500/10'
            }`}>
            <Icon size={12} />
            <span>{Math.abs(value)}%</span>
        </div>
    );
};

const StatCard = ({ title, value, icon: Icon, color, subtitle, trend }) => (
    <div
        className="relative overflow-hidden rounded-2xl p-6 group transition-all duration-300
            shadow-lg shadow-black/20 hover:shadow-xl hover:shadow-black/30"
        style={{
            background: 'linear-gradient(135deg, var(--cv-card), var(--cv-bg-secondary))',
            border: '1px solid var(--cv-border)'
        }}
    >
        {/* Subtle gradient overlay */}
        <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500"
            style={{ background: 'linear-gradient(135deg, var(--cv-primary-glow), transparent)' }} />

        {/* Glow effect on hover */}
        <div className="absolute -inset-1 rounded-2xl blur opacity-0 group-hover:opacity-30 transition-opacity duration-500"
            style={{ background: 'linear-gradient(to right, var(--cv-primary-glow), var(--cv-secondary-glow))' }} />

        <div className="relative z-10">
            <div className="flex items-start justify-between mb-4">
                <div
                    className={`p-3 rounded-xl ${color} group-hover:scale-110 transition-transform duration-300`}
                    style={{
                        backgroundColor: 'var(--cv-bg-elevated)',
                        border: '1px solid var(--cv-border)'
                    }}
                >
                    <Icon size={22} />
                </div>
                {trend !== undefined && (
                    <TrendIndicator value={trend} />
                )}
            </div>
            <div>
                <h3 className="text-4xl font-bold mb-1 tabular-nums" style={{ color: 'var(--cv-text)' }}>{value}</h3>
                <p className="text-sm font-medium" style={{ color: 'var(--cv-text-muted)' }}>{title}</p>
                {subtitle && (
                    <p className="text-xs mt-2 flex items-center gap-1" style={{ color: 'var(--cv-text-dim)' }}>
                        <span className="w-1 h-1 rounded-full" style={{ backgroundColor: 'var(--cv-text-dim)' }} />
                        {subtitle}
                    </p>
                )}
            </div>
        </div>
    </div>
);

export default StatCard;
