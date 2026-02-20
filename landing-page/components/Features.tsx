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
        <motion.img 
          src="/assets/features/feature-1.png"
          alt="Drop your script"
          animate={{ y: [0, -15, 0] }}
          transition={{ repeat: Infinity, duration: 5, ease: "easeInOut" }}
          className="w-full max-w-lg drop-shadow-[0_0_50px_rgba(99,102,241,0.2)]"
        />
      </div>
    )
  },
  {
    id: 'compile',
    title: 'Nuitka Compilation',
    benefit: 'Your code is yours. Keep it that way.',
    description: 'We translate your Python code into C, then compile it into a native binary. This significantly raises the bar for reverse engineering compared to PyInstaller\'s bytecode shipping.',
    icon: <Cpu className="w-5 h-5" />,
    renderVisual: () => (
      <div className="relative w-full h-full flex items-center justify-center p-8">
        <motion.img 
          src="/assets/features/feature-2.png"
          alt="Nuitka Compilation"
          animate={{ y: [0, -15, 0] }}
          transition={{ repeat: Infinity, duration: 5, ease: "easeInOut", delay: 0.5 }}
          className="w-full max-w-lg drop-shadow-[0_0_50px_rgba(99,102,241,0.2)]"
        />
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
      <div className="relative w-full h-full flex items-center justify-center p-8">
        <motion.img 
          src="/assets/features/feature-3.png"
          alt="Kill Piracy Dead"
          animate={{ y: [0, -15, 0] }}
          transition={{ repeat: Infinity, duration: 5, ease: "easeInOut", delay: 1 }}
          className="w-full max-w-lg drop-shadow-[0_0_50px_rgba(99,102,241,0.2)]"
        />
      </div>
    )
  },
  {
    id: 'profit',
    title: 'Air-Gapped Revenue',
    benefit: 'Sell to enterprise, offline.',
    description: 'Issue cryptographically signed leases that allow applications to run offline for up to 24 hours. Manage everything from a single dashboard.',
    icon: <DollarSign className="w-5 h-5" />,
    renderVisual: () => (
      <div className="relative w-full h-full flex items-center justify-center p-8">
        <motion.img 
          src="/assets/features/feature-4.png"
          alt="Air-Gapped Revenue"
          animate={{ y: [0, -15, 0] }}
          transition={{ repeat: Infinity, duration: 5, ease: "easeInOut", delay: 1.5 }}
          className="w-full max-w-lg drop-shadow-[0_0_50px_rgba(99,102,241,0.2)]"
        />
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