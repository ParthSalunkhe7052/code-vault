import React from 'react';

// Base Skeleton Component
const Skeleton = ({ className = '' }) => (
    <div className={`animate-pulse bg-white/5 rounded ${className}`} />
);

// Skeleton for Stat Cards
export const SkeletonCard = () => (
    <div className="rounded-2xl bg-gray-900/90 border border-white/15 p-6 space-y-4">
        <div className="flex items-start justify-between">
            <Skeleton className="h-12 w-12 rounded-xl" />
            <Skeleton className="h-6 w-16 rounded-full" />
        </div>
        <div className="space-y-2">
            <Skeleton className="h-10 w-24" />
            <Skeleton className="h-4 w-32" />
        </div>
    </div>
);

// Skeleton for Table Rows
export const SkeletonTable = ({ rows = 5, columns = 5 }) => (
    <div className="glass-card overflow-hidden">
        <div className="p-4 border-b border-white/15">
            <Skeleton className="h-6 w-48" />
        </div>
        <div className="divide-y divide-white/10">
            {[...Array(rows)].map((_, i) => (
                <div key={i} className="flex items-center gap-4 p-4">
                    <Skeleton className="h-5 w-5 rounded" />
                    {[...Array(columns)].map((_, j) => (
                        <Skeleton 
                            key={j} 
                            className={`h-4 ${j === 0 ? 'w-32' : j === columns - 1 ? 'w-16' : 'w-24'}`} 
                        />
                    ))}
                </div>
            ))}
        </div>
    </div>
);

// Skeleton for List Items
export const SkeletonList = ({ items = 5 }) => (
    <div className="space-y-3">
        {[...Array(items)].map((_, i) => (
            <div key={i} className="flex items-center gap-4 p-3 bg-white/[0.02] rounded-xl">
                <Skeleton className="h-10 w-10 rounded-lg" />
                <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-32" />
                    <Skeleton className="h-3 w-24" />
                </div>
                <Skeleton className="h-6 w-16 rounded-full" />
            </div>
        ))}
    </div>
);

// Skeleton for Profile/User Card
export const SkeletonProfile = () => (
    <div className="glass-card p-6 space-y-4">
        <div className="flex items-center gap-4">
            <Skeleton className="h-16 w-16 rounded-full" />
            <div className="space-y-2">
                <Skeleton className="h-5 w-32" />
                <Skeleton className="h-4 w-48" />
            </div>
        </div>
        <div className="grid grid-cols-2 gap-4 pt-4 border-t border-white/10">
            <div className="space-y-1">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-4 w-24" />
            </div>
            <div className="space-y-1">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-4 w-24" />
            </div>
        </div>
    </div>
);

// Skeleton for Chart
export const SkeletonChart = () => (
    <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-6">
            <Skeleton className="h-6 w-40" />
            <Skeleton className="h-8 w-24 rounded-lg" />
        </div>
        <div className="h-64 flex items-end gap-2">
            {[...Array(12)].map((_, i) => (
                <Skeleton 
                    key={i} 
                    className="flex-1 rounded-t"
                    style={{ height: `${Math.random() * 60 + 20}%` }}
                />
            ))}
        </div>
    </div>
);

// Inline Skeleton for text replacement
export const SkeletonText = ({ width = 'w-24', height = 'h-4' }) => (
    <Skeleton className={`${width} ${height} inline-block`} />
);

export default Skeleton;
