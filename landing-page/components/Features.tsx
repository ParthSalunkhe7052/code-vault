import React, { useRef, useState } from 'react';
import { Lock, Cloud, Zap, Cpu, Box, Server } from 'lucide-react';

// Mouse-tracking card component
const BentoCard: React.FC<{
  title: string;
  description: string;
  icon: React.ReactNode;
  className?: string;
  children?: React.ReactNode;
}> = ({ title, description, icon, className = "", children }) => {
  const divRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [opacity, setOpacity] = useState(0);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!divRef.current) return;
    const rect = divRef.current.getBoundingClientRect();
    setPosition({ x: e.clientX - rect.left, y: e.clientY - rect.top });
  };

  const handleMouseEnter = () => setOpacity(1);
  const handleMouseLeave = () => setOpacity(0);

  return (
    <div
      ref={divRef}
      onMouseMove={handleMouseMove}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className={`relative overflow-hidden rounded-2xl bg-[#0f1219] border border-white/5 p-8 flex flex-col group ${className}`}
    >
      {/* Mouse Follower Gradient */}
      <div
        className="pointer-events-none absolute -inset-px transition-opacity duration-300"
        style={{
          opacity,
          background: `radial-gradient(600px circle at ${position.x}px ${position.y}px, rgba(255,255,255,0.06), transparent 40%)`,
        }}
      />
      
      {/* Content */}
      <div className="relative z-10 flex flex-col h-full">
        <div className="w-10 h-10 rounded-lg bg-white/5 flex items-center justify-center text-white mb-4 border border-white/10">
          {icon}
        </div>
        
        <h3 className="text-xl font-semibold text-white mb-2">{title}</h3>
        <p className="text-slate-400 text-sm leading-relaxed mb-6">
          {description}
        </p>
        
        {/* Visual Slot */}
        <div className="flex-grow mt-auto">
           {children}
        </div>
      </div>
    </div>
  );
};

const Features: React.FC = () => {
  return (
    <section id="features" className="py-32 bg-background relative overflow-hidden">
      <div className="max-w-7xl mx-auto px-6">
        
        <div className="mb-20 max-w-3xl">
           <h2 className="text-4xl md:text-5xl font-bold mb-6 tracking-tight">
             <span className="text-transparent bg-clip-text bg-gradient-to-r from-white to-slate-500">
               Everything you need to ship
             </span>
             <br />
             <span className="text-white">secure binaries.</span>
           </h2>
           <p className="text-slate-400 text-lg">
             A complete toolchain for Python & Node.js distribution.
           </p>
        </div>

        {/* Bento Grid Layout */}
        <div className="grid grid-cols-1 md:grid-cols-6 gap-4 min-h-[800px]">
           
           {/* Card 1: Native Compilation (Large, Top Left) */}
           <BentoCard 
             className="md:col-span-4 md:row-span-2"
             title="Native Compilation"
             description="We translate your Python code into C, then compile it into a true native binary. No interpreter bundled."
             icon={<Cpu size={20} />}
           >
             <div className="relative w-full h-full min-h-[200px] bg-[#0a0c10] rounded-xl border border-white/5 overflow-hidden flex items-center justify-center group-hover:border-white/10 transition-colors">
                {/* Visual Placeholder: Binary Transformation */}
                <div className="flex items-center gap-8 opacity-80">
                   <div className="w-20 h-24 border border-blue-500/30 bg-blue-500/10 rounded-lg flex items-center justify-center">
                      <span className="font-mono text-blue-400 text-xs">.py</span>
                   </div>
                   <div className="h-0.5 w-16 bg-gradient-to-r from-blue-500 to-purple-500 relative">
                      <div className="absolute top-1/2 left-0 -translate-y-1/2 w-full h-4 bg-blue-500/20 blur-lg"></div>
                   </div>
                   <div className="w-20 h-24 border border-purple-500/30 bg-purple-500/10 rounded-lg flex items-center justify-center">
                      <span className="font-mono text-purple-400 text-xs">.exe</span>
                   </div>
                </div>
             </div>
           </BentoCard>

           {/* Card 2: Cloud Build (Tall, Right) */}
           <BentoCard 
             className="md:col-span-2 md:row-span-2"
             title="Cloud Build Matrix"
             description="Target Windows and Linux x64 from a single CLI command."
             icon={<Cloud size={20} />}
           >
             <div className="mt-4 space-y-3 font-mono text-xs">
                <div className="flex justify-between items-center p-3 rounded-lg bg-white/5 border border-white/5">
                   <span className="text-slate-300">win-x64</span>
                   <span className="text-emerald-400">Ready</span>
                </div>
                <div className="flex justify-between items-center p-3 rounded-lg bg-white/5 border border-white/5">
                   <span className="text-slate-300">linux-x64</span>
                   <span className="text-emerald-400">Ready</span>
                </div>
                <div className="flex justify-between items-center p-3 rounded-lg bg-white/5 border border-white/5 opacity-50">
                   <span className="text-slate-500">macos-arm64</span>
                   <span className="text-slate-500">Coming Soon</span>
                </div>
             </div>
           </BentoCard>

           {/* Card 3: HWID Locking (Medium, Bottom Left) */}
           <BentoCard 
             className="md:col-span-2 md:row-span-1"
             title="Hardware Locking"
             description="Bind licenses to CPU, Disk, and Motherboard serials."
             icon={<Lock size={20} />}
           />

           {/* Card 4: Offline Leases (Medium, Bottom Center) */}
           <BentoCard 
             className="md:col-span-2 md:row-span-1"
             title="Offline Leases"
             description="Allow apps to run offline for up to 365 days."
             icon={<Zap size={20} />}
           />

           {/* Card 5: Webhooks (Medium, Bottom Right) */}
           <BentoCard 
             className="md:col-span-2 md:row-span-1"
             title="Webhooks"
             description="Real-time events for builds and validations."
             icon={<Server size={20} />}
           />

        </div>
      </div>
    </section>
  );
};

export default Features;