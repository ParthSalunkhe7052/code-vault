import React, { memo } from 'react';
import { Upload, FolderTree, Settings, Shield, Hammer, CheckCircle, Circle } from 'lucide-react';

const WizardSidebar = memo(({ currentStep, completedSteps = [] }) => {
    const steps = [
        { 
            id: 1, 
            name: 'Upload', 
            description: 'Source files',
            icon: Upload 
        },
        { 
            id: 2, 
            name: 'Review', 
            description: 'Verify structure',
            icon: FolderTree 
        },
        { 
            id: 3, 
            name: 'Configure', 
            description: 'Build settings',
            icon: Settings 
        },
        { 
            id: 4, 
            name: 'Protection', 
            description: 'License & Security',
            icon: Shield 
        },
        { 
            id: 5, 
            name: 'Build', 
            description: 'Compile & Output',
            icon: Hammer 
        },
    ];

    return (
        <div className="w-full bg-slate-900/50 border-r border-white/10 h-full flex flex-col shrink-0 backdrop-blur-sm">
            <div className="p-6 border-b border-white/10">
                <h3 className="text-lg font-bold text-white tracking-tight">Setup Project</h3>
                <p className="text-xs text-slate-500 mt-1">Follow the steps below</p>
            </div>

            <div className="flex-1 py-6 px-4 space-y-1 overflow-y-auto custom-scrollbar">
                {steps.map((step, index) => {
                    const isCompleted = completedSteps.includes(step.id);
                    const isCurrent = currentStep === step.id;
                    const Icon = step.icon;

                    return (
                        <div key={step.id} className="relative group">
                            {/* Connector Line */}
                            {index < steps.length - 1 && (
                                <div className={`
                                    absolute left-5 top-10 bottom-0 w-0.5 -ml-px
                                    ${isCompleted ? 'bg-emerald-500/30' : 'bg-slate-800'}
                                    group-hover:bg-slate-700 transition-colors
                                `} style={{ height: 'calc(100% + 8px)' }} />
                            )}

                            <div 
                                className={`
                                    flex items-start gap-4 p-3 rounded-xl transition-all duration-300
                                    ${isCurrent 
                                        ? 'bg-indigo-500/10 border border-indigo-500/20 translate-x-1' 
                                        : 'hover:bg-white/5 border border-transparent'}
                                `}
                            >
                                {/* Icon Bubble */}
                                <div className={`
                                    relative z-10 w-10 h-10 rounded-full flex items-center justify-center shrink-0 border-2 transition-colors
                                    ${isCompleted
                                        ? 'bg-emerald-500 border-emerald-500 text-white'
                                        : isCurrent
                                            ? 'bg-indigo-600 border-indigo-500 text-white shadow-lg shadow-indigo-500/20'
                                            : 'bg-slate-800 border-slate-700 text-slate-400 group-hover:border-slate-600'
                                    }
                                `}>
                                    {isCompleted ? (
                                        <CheckCircle size={18} />
                                    ) : (
                                        <Icon size={18} />
                                    )}
                                </div>

                                {/* Text Info */}
                                <div className="flex flex-col pt-0.5">
                                    <span className={`
                                        text-sm font-semibold transition-colors
                                        ${isCurrent ? 'text-indigo-400' : isCompleted ? 'text-emerald-400' : 'text-slate-400 group-hover:text-slate-300'}
                                    `}>
                                        {step.name}
                                    </span>
                                    <span className="text-xs text-slate-500 font-medium">
                                        {step.description}
                                    </span>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
            
            {/* Bottom Info */}
            <div className="p-4 border-t border-white/10 bg-white/5">
                <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="text-xs text-emerald-400 font-medium">System Ready</span>
                </div>
            </div>
        </div>
    );
});

WizardSidebar.displayName = 'WizardSidebar';

export default WizardSidebar;
