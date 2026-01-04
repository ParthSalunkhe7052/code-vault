import React from 'react';
import { Inbox, Plus } from 'lucide-react';

const EmptyState = ({
    icon: Icon = Inbox,
    title,
    description,
    action,
    actionLabel,
    actionIcon: ActionIcon = Plus
}) => (
    <div className="flex flex-col items-center justify-center py-16 px-8 text-center">
        <div className="w-20 h-20 rounded-full bg-slate-800/50 flex items-center justify-center 
            mb-6 text-slate-500 border border-white/10">
            <Icon size={32} />
        </div>
        <h3 className="text-xl font-semibold text-white mb-2">{title}</h3>
        <p className="text-slate-400 text-sm max-w-sm mb-6">{description}</p>
        {action && (
            <button
                onClick={action}
                className="btn-primary flex items-center gap-2"
            >
                <ActionIcon size={18} />
                {actionLabel}
            </button>
        )}
    </div>
);

export default EmptyState;
