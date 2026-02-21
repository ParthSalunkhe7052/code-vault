import React, { useRef } from 'react';
import { motion, useScroll, useTransform, useSpring } from 'framer-motion';
import { Code2, Cpu, Lock, DollarSign } from 'lucide-react';

const STAGES = [
  {
    id: 'stage-1',
    title: 'Drop your Script',
    description: 'Zero proprietary syntax. Develop as you normally would.',
    color: '#6366f1', // Indigo
    icon: Code2
  },
  {
    id: 'stage-2',
    title: 'Nuitka Forge',
    description: 'Code-to-C translation for native hardware performance.',
    color: '#a855f7', // Purple
    icon: Cpu
  },
  {
    id: 'stage-3',
    title: 'Hardware Lock',
    description: 'Binding your binary to unique motherboard signatures.',
    color: '#06b6d4', // Cyan
    icon: Lock
  },
  {
    id: 'stage-4',
    title: 'The Vault',
    description: 'Air-gapped revenue. Secure, offline distribution.',
    color: '#10b981', // Emerald
    icon: DollarSign
  }
];

const Node = ({ index, scrollProgress, color, icon: Icon }: { index: number, scrollProgress: any, color: string, icon: any }) => {
  const start = index * 0.25;
  const end = (index + 1) * 0.25;
  
  const opacity = useTransform(scrollProgress, [start - 0.1, start, end - 0.05, end], [0.2, 1, 1, 0.2]);
  const scale = useTransform(scrollProgress, [start - 0.1, start, end - 0.05, end], [0.8, 1.1, 1, 0.8]);
  const glow = useTransform(scrollProgress, [start - 0.1, start, end - 0.05, end], [0, 20, 15, 0]);
  const iconOpacity = useTransform(scrollProgress, [start - 0.05, start, end - 0.05, end], [0.3, 1, 1, 0.3]);

  return (
    <motion.div
      style={{ 
        opacity, 
        scale,
        boxShadow: `0 0 ${glow}px ${color}44`
      }}
      className="relative w-32 h-32 rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl flex items-center justify-center overflow-hidden"
    >
      <div className="absolute inset-0 bg-gradient-to-br from-white/10 to-transparent" />
      <motion.div style={{ opacity: iconOpacity, color }}>
        <Icon size={40} strokeWidth={1.5} />
      </motion.div>
      <motion.div 
        animate={{ scale: [1, 1.5], opacity: [0.5, 0] }}
        transition={{ repeat: Infinity, duration: 2 }}
        className="absolute inset-0 rounded-3xl border border-white/20 pointer-events-none"
      />
    </motion.div>
  );
};

const Path = ({ index, scrollProgress }: { index: number, scrollProgress: any }) => {
  const start = index * 0.25 + 0.125;
  const end = (index + 1) * 0.25 + 0.125;
  const pathLength = useTransform(scrollProgress, [start, end], [0, 1]);
  const opacity = useTransform(scrollProgress, [start, end], [0.2, 1]);

  if (index === STAGES.length - 1) return null;

  return (
    <div className="absolute left-1/2 -translate-x-1/2 w-1 h-32 top-full overflow-hidden">
      <div className="w-full h-full bg-white/5 rounded-full" />
      <motion.div 
        style={{ scaleY: pathLength, opacity, originY: 0 }}
        className="absolute inset-0 bg-gradient-to-b from-indigo-500 to-emerald-500 rounded-full"
      />
    </div>
  );
};

const Features: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start 0.8", "end 0.2"]
  });

  const smoothProgress = useSpring(scrollYProgress, { stiffness: 50, damping: 20 });

  return (
    <section ref={containerRef} className="relative h-[400vh] bg-transparent overflow-visible">
      <div className="sticky top-0 h-screen w-full flex items-center justify-center overflow-hidden">
        <div className="max-w-7xl w-full px-6 grid grid-cols-1 md:grid-cols-12 gap-12 items-center relative h-full">
          
          {/* Left Side: Fixed text block that changes opacity based on scroll */}
          <div className="md:col-span-6 relative h-[400px] flex items-center">
            {STAGES.map((stage, i) => {
              const start = i * 0.25;
              const end = (i + 1) * 0.25;
              const opacity = useTransform(smoothProgress, [start - 0.05, start, end - 0.05, end], [0, 1, 1, 0]);
              const translateY = useTransform(smoothProgress, [start - 0.05, start, end - 0.05, end], [20, 0, 0, -20]);

              return (
                <motion.div 
                  key={stage.id}
                  style={{ opacity, y: translateY }}
                  className="absolute inset-0 flex flex-col justify-center"
                >
                  <div className="flex items-center gap-3 mb-6">
                    <div className="w-1 h-8 rounded-full bg-indigo-500" />
                    <span className="text-xs font-black tracking-widest text-indigo-400 uppercase">Phase {i + 1}</span>
                  </div>
                  <h2 className="text-5xl md:text-7xl font-bold text-white tracking-tighter leading-tight mb-6">
                    {stage.title}
                  </h2>
                  <p className="text-xl text-slate-400 font-medium leading-relaxed max-w-lg">
                    {stage.description}
                  </p>
                </motion.div>
              );
            })}
          </div>

          {/* Right Side: Centered Neural Nodes */}
          <div className="md:col-span-6 flex flex-col items-center gap-32 relative py-20">
            {STAGES.map((stage, i) => (
              <div key={stage.id} className="relative">
                <Node index={i} scrollProgress={smoothProgress} color={stage.color} icon={stage.icon} />
                <Path index={i} scrollProgress={smoothProgress} />
              </div>
            ))}
          </div>

        </div>
      </div>
    </section>
  );
};

export default Features;
