import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Code2, Cpu, Lock, DollarSign, CheckCircle2, ShieldCheck, Activity, Globe } from 'lucide-react';

interface FeatureStep {
  id: string;
  title: string;
  benefit: string;
  description: string;
  icon: React.ReactNode;
  renderVisual: () => React.ReactNode;
}

const steps: FeatureStep[] = [
  {
    id: 'develop',
    title: 'Drop your Script',
    benefit: 'Zero proprietary syntax.',
    description: 'Develop your Python or Node.js application as you normally would. No weird SDKs or mandatory imports. We handle the complexity, you handle the logic.',
    icon: <Code2 className="w-5 h-5" />,
    renderVisual: () => (
      <div className="relative w-full h-full flex items-center justify-center p-8">
        <motion.div 
          animate={{ y: [0, -10, 0] }}
          transition={{ repeat: Infinity, duration: 4, ease: "easeInOut" }}
          className="w-64 h-80 rounded-3xl bg-[#111827] border-2 border-dashed border-indigo-500/30 flex flex-col items-center justify-center shadow-2xl"
        >
           <div className="w-16 h-16 rounded-2xl bg-indigo-500/20 flex items-center justify-center mb-6">
              <Code2 className="text-indigo-400" size={32} />
           </div>
           <div className="text-xs font-mono text-slate-500 mb-2">main.py</div>
           <div className="w-32 h-1 bg-white/5 rounded-full mb-2" />
           <div className="w-24 h-1 bg-white/5 rounded-full mb-2" />
           <div className="w-28 h-1 bg-white/5 rounded-full" />
           
           <div className="mt-8 px-4 py-2 rounded-full bg-indigo-500 text-[10px] font-bold text-white shadow-lg">
              DRAG & DROP
           </div>
        </motion.div>
      </div>
    )
  },
  {
    id: 'compile',
    title: 'Nuitka Compilation',
    benefit: 'Your code is yours. Keep it that way.',
    description: 'We translate your Python code into C, then compile it into a true native binary. No bytecode is shipped, making decompilation exponentially harder than PyInstaller.',
    icon: <Cpu className="w-5 h-5" />,
    renderVisual: () => (
      <div className="w-full max-w-md mx-auto aspect-square bg-[#0a0f1a] rounded-3xl border border-white/5 overflow-hidden flex flex-col shadow-2xl">
         <div className="flex items-center px-4 py-3 bg-white/5 border-b border-white/5 gap-2">
            <div className="w-2 h-2 rounded-full bg-red-500/20" />
            <div className="w-2 h-2 rounded-full bg-yellow-500/20" />
            <div className="w-2 h-2 rounded-full bg-green-500/20" />
            <span className="ml-2 text-[10px] font-mono text-slate-500 uppercase tracking-widest">Nuitka Optimizer</span>
         </div>
         <div className="p-6 font-mono text-[10px] text-indigo-400/80 leading-relaxed overflow-hidden">
            <motion.div animate={{ y: [0, -200] }} transition={{ repeat: Infinity, duration: 10, ease: "linear" }}>
               {[...Array(20)].map((_, i) => (
                 <div key={i} className="mb-1">
                    <span className="text-slate-600">[{i}]</span> #include &lt;nuitka/prelude.h&gt;<br />
                    void compiled_function(void) &#123;<br />
                    &nbsp;&nbsp;CHECK_OBJECT(code_obj);<br />
                    &nbsp;&nbsp;PyObject *result = CALL_FUNCTION(obj, args);<br />
                    &#125;
                 </div>
               ))}
            </motion.div>
         </div>
         <div className="mt-auto p-4 bg-emerald-500/10 border-t border-emerald-500/20 flex items-center justify-between">
            <span className="text-[10px] font-bold text-emerald-400">OPTIMIZING C SOURCE</span>
            <div className="flex gap-1">
               <motion.div animate={{ opacity: [0, 1, 0] }} transition={{ repeat: Infinity, duration: 1 }} className="w-1 h-3 bg-emerald-500" />
               <motion.div animate={{ opacity: [0, 1, 0] }} transition={{ repeat: Infinity, duration: 1, delay: 0.2 }} className="w-1 h-3 bg-emerald-500" />
               <motion.div animate={{ opacity: [0, 1, 0] }} transition={{ repeat: Infinity, duration: 1, delay: 0.4 }} className="w-1 h-3 bg-emerald-500" />
            </div>
         </div>
      </div>
    )
  },
  {
    id: 'protect',
    title: 'Kill Piracy Dead',
    benefit: 'Lock it to the motherboard.',
    description: 'Inject HWID validation directly into your binary. Bind licenses to unique hardware signatures (CPU, Disk, Mobo). If they share the .exe, it bricks.',
    icon: <Lock className="w-5 h-5" />,
    renderVisual: () => (
      <div className="relative w-full h-full flex flex-col items-center justify-center p-12">
         <div className="w-full max-w-xs space-y-3">
            {[
              { label: 'CPU_SIGNATURE', status: 'VERIFIED', color: 'emerald' },
              { label: 'DISK_SERIAL_ID', status: 'VERIFIED', color: 'emerald' },
              { label: 'BIOS_UUID_HASH', status: 'VERIFIED', color: 'emerald' },
              { label: 'MAC_ADDRESS', status: 'MISMATCH', color: 'red' },
            ].map((item, i) => (
              <motion.div 
                key={i}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 }}
                className="flex items-center justify-between p-4 rounded-xl bg-white/[0.02] border border-white/5"
              >
                 <span className="text-[10px] font-mono text-slate-500">{item.label}</span>
                 <div className={`flex items-center gap-2 text-[10px] font-bold text-${item.color}-400`}>
                    <div className={`w-1 h-1 rounded-full bg-${item.color}-400 animate-pulse`} />
                    {item.status}
                 </div>
              </motion.div>
            ))}
         </div>
         <motion.div 
           animate={{ rotate: 360 }}
           transition={{ repeat: Infinity, duration: 20, ease: "linear" }}
           className="absolute inset-0 border-[40px] border-indigo-500/5 rounded-full scale-110 pointer-events-none" 
         />
      </div>
    )
  },
  {
    id: 'profit',
    title: 'Air-Gapped Revenue',
    benefit: 'Sell to enterprise, offline.',
    description: 'Issue cryptographically signed leases that allow applications to run offline for up to 365 days. Manage everything from a single dashboard.',
    icon: <DollarSign className="w-5 h-5" />,
    renderVisual: () => (
      <div className="relative w-full h-full flex items-center justify-center">
         <motion.div 
           whileHover={{ scale: 1.05 }}
           className="w-72 p-6 rounded-3xl bg-gradient-to-br from-indigo-600 to-purple-700 border border-indigo-400 shadow-2xl shadow-indigo-500/20"
         >
            <div className="flex justify-between items-start mb-10">
               <div className="p-2 rounded-xl bg-white/10">
                  <ShieldCheck className="text-white" size={24} />
               </div>
               <div className="px-2 py-1 rounded-md bg-white/10 text-[8px] font-bold text-white uppercase tracking-widest">Enterprise Lease</div>
            </div>
            <div className="mb-8">
               <div className="text-[10px] text-indigo-200 mb-1">LICENSE KEY</div>
               <div className="text-sm font-mono text-white font-bold tracking-wider">CV-9921-XP02-L991</div>
            </div>
            <div className="flex justify-between items-end">
               <div>
                  <div className="text-[10px] text-indigo-200 mb-1">STATUS</div>
                  <div className="text-xs text-white font-bold flex items-center gap-1">
                     <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                     OFFLINE READY
                  </div>
               </div>
               <div className="text-right">
                  <div className="text-[10px] text-indigo-200 mb-1">EXPIRES</div>
                  <div className="text-xs text-white font-bold">364 DAYS</div>
               </div>
            </div>
         </motion.div>
         
         {/* Abstract background stats */}
         <div className="absolute top-10 right-10 p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-xl -z-10 opacity-50 rotate-12">
            <Activity className="text-indigo-400" size={20} />
         </div>
         <div className="absolute bottom-10 left-10 p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-xl -z-10 opacity-50 -rotate-12">
            <Globe className="text-purple-400" size={20} />
         </div>
      </div>
    )
  },
];

const Features: React.FC = () => {
  const [activeStep, setActiveStep] = useState(0);

  return (
    <section id="features" className="py-32 bg-background relative overflow-hidden">
      {/* Background Ambience */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full pointer-events-none">
        <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-indigo-600/5 rounded-full blur-[150px]" />
      </div>

      <div className="max-w-7xl mx-auto px-6">
        <div className="mb-24 flex flex-col md:flex-row md:items-end justify-between gap-8">
          <div className="max-w-2xl">
            <h2 className="text-5xl md:text-7xl font-bold tracking-tighter text-white mb-8">
              The <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-400">Protocol.</span>
            </h2>
            <p className="text-xl text-slate-400 leading-relaxed font-medium">
              A high-performance pipeline designed to protect your intellectual property and maximize distribution control.
            </p>
          </div>
          <div className="hidden md:block pb-2">
             <div className="flex gap-1">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="w-12 h-1 bg-white/5 rounded-full overflow-hidden">
                     <motion.div 
                       animate={{ x: ['-100%', '100%'] }} 
                       transition={{ repeat: Infinity, duration: 2, delay: i * 0.4 }} 
                       className="w-full h-full bg-indigo-500/20" 
                     />
                  </div>
                ))}
             </div>
          </div>
        </div>

        <div className="grid lg:grid-cols-12 gap-20 items-start">
          
          {/* Left: Step Selection */}
          <div className="lg:col-span-5 space-y-2">
            {steps.map((step, index) => (
              <button
                key={step.id}
                onMouseEnter={() => setActiveStep(index)}
                onClick={() => setActiveStep(index)}
                className={`w-full text-left p-8 rounded-3xl transition-all duration-500 group relative ${
                  activeStep === index
                    ? 'bg-white/[0.03] shadow-2xl'
                    : 'hover:bg-white/[0.01]'
                }`}
              >
                {/* Active Indicator Line */}
                {activeStep === index && (
                  <motion.div 
                    layoutId="active-line"
                    className="absolute left-0 top-8 bottom-8 w-1 bg-indigo-500 rounded-full shadow-[0_0_15px_rgba(99,102,241,0.5)]" 
                  />
                )}

                <div className="flex items-start gap-6">
                  <div className={`mt-1.5 p-2 rounded-xl transition-all duration-500 ${
                    activeStep === index ? 'bg-indigo-500 text-white scale-110 shadow-lg shadow-indigo-500/20' : 'bg-white/5 text-slate-600 group-hover:text-slate-400'
                  }`}>
                    {step.icon}
                  </div>
                  <div>
                    <h3 className={`text-2xl font-bold mb-2 transition-colors duration-500 ${
                      activeStep === index ? 'text-white' : 'text-slate-500 group-hover:text-slate-300'
                    }`}>
                      {step.title}
                    </h3>
                    <p className={`text-xs font-black tracking-[0.2em] uppercase mb-4 transition-colors duration-500 ${
                      activeStep === index ? 'text-indigo-400' : 'text-slate-700'
                    }`}>
                      {step.benefit}
                    </p>
                    <AnimatePresence>
                      {activeStep === index && (
                        <motion.p
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                          className="text-slate-400 text-sm leading-relaxed"
                        >
                          {step.description}
                        </motion.p>
                      )}
                    </AnimatePresence>
                  </div>
                </div>
              </button>
            ))}
          </div>

          {/* Right: Visual Display (Removed restrictive pill border) */}
          <div className="lg:col-span-7 relative flex justify-center items-center min-h-[600px]">
            {/* Spotlight Effect */}
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 via-transparent to-transparent rounded-[4rem] blur-3xl" />
            
            <AnimatePresence mode="wait">
              <motion.div
                key={activeStep}
                initial={{ opacity: 0, scale: 0.95, filter: 'blur(10px)' }}
                animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
                exit={{ opacity: 0, scale: 1.05, filter: 'blur(10px)' }}
                transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
                className="relative z-10 w-full h-full flex justify-center items-center"
              >
                {steps[activeStep].renderVisual()}
              </motion.div>
            </AnimatePresence>
          </div>

        </div>
      </div>
    </section>
  );
};

export default Features;