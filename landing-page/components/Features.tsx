import React from 'react';
import { Lock, Cloud, Zap, Cpu, Box, Clock, ShieldCheck, Terminal, Server } from 'lucide-react';

const FeatureCard: React.FC<{
  title: string;
  description: string;
  icon: React.ReactNode;
  className?: string;
  children?: React.ReactNode;
  fullWidthDesc?: boolean;
}> = ({ title, description, icon, className = "", children, fullWidthDesc = false }) => (
  <div 
    className={`relative overflow-hidden rounded-3xl border border-white/10 bg-white/[0.02] p-8 hover:bg-white/[0.04] transition-colors duration-300 flex flex-col group ${className}`}
  >
    <div className="relative z-10 flex flex-col h-full pointer-events-none">
      <div className="w-12 h-12 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-white mb-6 backdrop-blur-sm">
        {icon}
      </div>
      
      <h3 className="text-xl font-semibold text-white mb-3">{title}</h3>
      <p className={`text-slate-400 text-sm leading-relaxed mb-6 ${fullWidthDesc ? 'max-w-full' : 'max-w-[90%] md:max-w-[60%]'}`}>
        {description}
      </p>
      
      {/* Visual Container - Positioned absolutely or normally depending on layout */}
      <div className="flex-grow relative pointer-events-auto">
         {children}
      </div>
    </div>

    {/* Decorative Gradients */}
    <div className="absolute top-0 right-0 -mr-20 -mt-20 w-64 h-64 bg-blue-500/5 rounded-full blur-3xl pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
    <div className="absolute bottom-0 left-0 -ml-20 -mb-20 w-64 h-64 bg-purple-500/5 rounded-full blur-3xl pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
  </div>
);

const Features: React.FC = () => {
  return (
    <section id="features" className="py-32 bg-background relative">
      <div className="max-w-7xl mx-auto px-6">
        
        <div className="mb-24 md:text-center max-w-3xl mx-auto">
           <h2 className="text-4xl md:text-5xl font-bold mb-6 tracking-tight">
             Engineered for <span className="text-gradient-primary">unbreakable security.</span>
           </h2>
           <p className="text-slate-400 text-lg">
             Stop relying on simple wrappers. We provide a complete toolchain to compile, protect, and manage your software distribution.
           </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 auto-rows-[minmax(250px,auto)]">
           
           {/* Card 1: Native Nuitka - Large Span */}
           <FeatureCard 
             className="md:col-span-2 min-h-[320px]"
             title="True Native Compilation"
             description="We leverage Nuitka to translate your Python code into C, which is then compiled into a true native binary. No interpreter is bundled, making decompilation exponentially harder than PyInstaller."
             icon={<Cpu className="w-6 h-6 text-blue-400" />}
             fullWidthDesc={true}
           />

           {/* Card 2: Cloud Build */}
           <FeatureCard 
             className="md:col-span-1"
             title="Cloud Build Matrix"
             description="Target Windows and Linux from a single dashboard. macOS cloud builds are currently unavailable."
             icon={<Cloud className="w-6 h-6 text-purple-400" />}
             fullWidthDesc={true}
           >
             <div className="mt-8 flex flex-col gap-3 opacity-80">
                {/* Windows Bar */}
                <div className="group/bar">
                  <div className="flex justify-between text-[10px] text-gray-400 mb-1">
                    <span>Windows (x64)</span>
                    <span className="text-blue-400">Ready</span>
                  </div>
                  <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                    <div className="h-full w-[85%] bg-blue-500 rounded-full"></div>
                  </div>
                </div>
                
                {/* Linux Bar */}
                <div className="group/bar">
                  <div className="flex justify-between text-[10px] text-gray-400 mb-1">
                    <span>Linux (x64)</span>
                    <span className="text-emerald-400">Ready</span>
                  </div>
                  <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                     <div className="h-full w-[80%] bg-emerald-500 rounded-full"></div>
                  </div>
                </div>
             </div>
           </FeatureCard>

           {/* Card 3: HWID - Standard Span */}
           <FeatureCard 
             className="md:col-span-1"
             title="Hardware Locking"
             description="Bind licenses to unique hardware signatures (CPU, Disk, Mobo)."
             icon={<Lock className="w-6 h-6 text-green-400" />}
             fullWidthDesc={true}
           >
             <div className="mt-6 border border-white/5 bg-black/20 rounded-lg p-3 font-mono text-[10px] text-slate-500 space-y-2 relative overflow-hidden">
               <div className="absolute top-0 left-0 w-1 h-full bg-green-500/50"></div>
               <div className="flex justify-between items-center">
                 <span className="text-gray-400">CPU_ID</span> 
                 <span className="text-green-500/80">MATCH</span>
               </div>
               <div className="flex justify-between items-center">
                 <span className="text-gray-400">DISK_SN</span> 
                 <span className="text-green-500/80">MATCH</span>
               </div>
               <div className="flex justify-between items-center">
                 <span className="text-gray-400">MOBO_ID</span> 
                 <span className="text-red-500/80">MISMATCH</span>
               </div>
             </div>
           </FeatureCard>

            {/* Card 4: Offline Leases - Large Span */}
            <FeatureCard 
             className="md:col-span-2 min-h-[280px]"
             title="Offline Crypto Leases"
             description="Your apps don't need constant internet. We issue cryptographically signed leases that allow applications to run offline for a configurable grace period (e.g., 7 days) while maintaining full control."
             icon={<Clock className="w-6 h-6 text-orange-400" />}
           >
               <div className="absolute bottom-6 right-6 flex items-center gap-3 bg-surface p-3 rounded-xl border border-white/10 shadow-xl">
                 <div className="px-3 py-1.5 rounded-full bg-green-500/10 border border-green-500/20 flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></div>
                    <span className="text-xs font-medium text-green-400">Valid Lease</span>
                 </div>
                 <div className="text-xs text-slate-500 font-mono border-l border-white/10 pl-3">
                    Exp: 12h 45m
                 </div>
              </div>
           </FeatureCard>

           {/* Card 5: Node.js Support */}
           <FeatureCard 
             title="Node.js Support"
             description="Full support for packaging Node.js applications using V8 bytecode snapshots."
             icon={<Box className="w-6 h-6 text-yellow-400" />}
             className="md:col-span-1"
             fullWidthDesc={true}
           />

           {/* Card 6: Webhooks */}
           <FeatureCard 
             title="Webhooks & Events"
             description="Push license and subscription events to your systems in real time."
             icon={<ShieldCheck className="w-6 h-6 text-red-400" />}
             className="md:col-span-1"
             fullWidthDesc={true}
           />

           {/* Card 7: Fast Mode */}
           <FeatureCard 
             title="Fast Dev Mode"
             description="Skip the heavy compilation steps during development."
             icon={<Zap className="w-6 h-6 text-blue-300" />}
             className="md:col-span-1"
             fullWidthDesc={true}
           />

        </div>
      </div>
    </section>
  );
};

export default Features;
