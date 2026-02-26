
import { Cpu, Globe } from 'lucide-react';

const MachinesList = ({ machines }) => {
    return (
        <div className="glass-card p-6">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <Cpu size={20} className="text-emerald-400" />
                    <h2 className="text-lg font-semibold text-white">Active Machines</h2>
                </div>
            </div>
            {machines && machines.length > 0 ? (
                <div className="space-y-3">
                    {machines.map((machine, i) => (
                        <MachineItem key={i} machine={machine} />
                    ))}
                </div>
            ) : (
                <div className="p-4 text-center">
                    <p className="text-slate-500 text-sm">No active machines.</p>
                    <p className="text-slate-600 text-xs mt-1">Machines will appear here when clients validate licenses.</p>
                </div>
            )}
        </div>
    );
};

const MachineItem = ({ machine }) => (
    <div className="flex items-center gap-4 p-3 bg-white/5 rounded-lg">
        <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
            <Cpu size={16} />
        </div>
        <div className="flex-1 min-w-0">
            <p className="text-sm text-white font-medium truncate">
                {machine.machine_name || 'Unknown Machine'}
            </p>
            <div className="flex items-center gap-3 text-xs text-slate-500 mt-0.5">
                <span className="font-mono">{machine.hwid?.substring(0, 12)}...</span>
                {machine.ip_address && (
                    <span className="flex items-center gap-1">
                        <Globe size={10} />
                        {machine.ip_address}
                    </span>
                )}
            </div>
        </div>
        <div className="text-right">
            <p className="text-xs text-slate-400">{machine.client_name}</p>
            <p className="text-xs text-slate-500 font-mono truncate max-w-[100px]">
                {machine.license_key?.substring(0, 12)}...
            </p>
        </div>
    </div>
);

export default MachinesList;
