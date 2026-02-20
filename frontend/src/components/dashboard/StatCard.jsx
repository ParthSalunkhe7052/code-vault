
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

const StatCard = ({ title, value, icon: Icon, subtitle, trend }) => (
    <div
        className="relative overflow-hidden rounded-2xl p-6 group transition-all duration-300
            shadow-lg shadow-black/20 hover:shadow-xl hover:shadow-black/30 border border-cv-border bg-cv-card-gradient"
    >
        {/* Subtle gradient overlay */}
        <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 bg-cv-glow-gradient" />

        {/* Glow effect on hover */}
        <div className="absolute -inset-1 rounded-2xl blur opacity-0 group-hover:opacity-30 transition-opacity duration-500 bg-cv-hover-glow" />

        <div className="relative z-10">
            <div className="flex items-start justify-between mb-4">
                <div
                    className="p-3 rounded-xl group-hover:scale-110 transition-transform duration-300 bg-cv-bg-elevated border border-cv-border"
                >
                    <Icon size={22} />
                </div>
                {trend !== undefined && (
                    <TrendIndicator value={trend} />
                )}
            </div>
            <div>
                <h3 className="text-4xl font-bold mb-1 tabular-nums text-cv-text">{value}</h3>
                <p className="text-sm font-medium text-cv-text-muted">{title}</p>
                {subtitle && (
                    <p className="text-xs mt-2 flex items-center gap-1 text-cv-text-dim">
                        <span className="w-1 h-1 rounded-full bg-cv-text-dim" />
                        {subtitle}
                    </p>
                )}
            </div>
        </div>
    </div>
);

export default StatCard;
