import React from 'react';
import { Check, Upload, FolderTree, Settings, Key, Hammer } from 'lucide-react';

/**
 * WizardStepIndicator - Visual progress indicator for the project wizard
 * Shows 5 steps: Upload, Review, Configure, License, Build
 */
const WizardStepIndicator = ({ currentStep, completedSteps = [] }) => {
    const steps = [
        { id: 1, name: 'Upload', icon: Upload },
        { id: 2, name: 'Review', icon: FolderTree },
        { id: 3, name: 'Configure', icon: Settings },
        { id: 4, name: 'License', icon: Key },
        { id: 5, name: 'Build', icon: Hammer },
    ];

    const getStepStatus = (stepId) => {
        if (completedSteps.includes(stepId)) return 'completed';
        if (stepId === currentStep) return 'current';
        return 'upcoming';
    };

    return (
        <div className="w-full px-4 py-6">
            <div className="flex items-center justify-between">
                {steps.map((step, index) => {
                    const status = getStepStatus(step.id);
                    const Icon = step.icon;

                    return (
                        <React.Fragment key={step.id}>
                            {/* Step Circle */}
                            <div className="flex flex-col items-center">
                                <div
                                    className={`
                                        w-12 h-12 rounded-full flex items-center justify-center
                                        transition-all duration-300 border-2
                                        ${status === 'completed'
                                            ? 'bg-emerald-500 border-emerald-500 text-white'
                                            : status === 'current'
                                                ? 'bg-indigo-500 border-indigo-500 text-white shadow-lg shadow-indigo-500/30'
                                                : 'bg-white/5 border-white/20 text-slate-400'
                                        }
                                    `}
                                >
                                    {status === 'completed' ? (
                                        <Check size={20} className="stroke-[3]" />
                                    ) : (
                                        <Icon size={20} />
                                    )}
                                </div>
                                <span className={`
                                    mt-2 text-xs font-medium
                                    ${status === 'current' ? 'text-indigo-400' :
                                        status === 'completed' ? 'text-emerald-400' : 'text-slate-500'}
                                `}>
                                    {step.name}
                                </span>
                            </div>

                            {/* Connector Line */}
                            {index < steps.length - 1 && (
                                <div className="flex-1 mx-3 h-0.5 relative">
                                    <div className="absolute inset-0 bg-white/10 rounded-full" />
                                    <div
                                        className={`
                                            absolute inset-y-0 left-0 rounded-full transition-all duration-500
                                            ${completedSteps.includes(step.id)
                                                ? 'bg-emerald-500 w-full'
                                                : status === 'current'
                                                    ? 'bg-indigo-500 w-1/2'
                                                    : 'w-0'
                                            }
                                        `}
                                    />
                                </div>
                            )}
                        </React.Fragment>
                    );
                })}
            </div>
        </div>
    );
};

export default WizardStepIndicator;
