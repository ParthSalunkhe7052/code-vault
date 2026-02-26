import React, { useRef } from 'react';
import { motion, useScroll, useTransform, useSpring } from 'framer-motion';
import { AnalysisSymbol, CompilationSymbol, HWIDSymbol, AuthSymbol } from './Symbols';

const STAGES = [
  {
    id: 'stage-1',
    phase: '01',
    title: 'Input Analysis',
    description: 'Drop your Python or Node.js entry point. Our engine performs a deep-trace analysis of your dependency tree, automatically packaging your local modules and environment variables.',
    color: '#6366f1',
    symbol: AnalysisSymbol,
    hud: 'SCANNING SOURCE'
  },
  {
    id: 'stage-2',
    phase: '02',
    title: 'Native Compilation',
    description: 'We transpile your high-level code into optimized C++ and compile it using Nuitka. This isn\'t "bundling"—it is true native compilation for decompiler resistance.',
    color: '#a855f7',
    symbol: CompilationSymbol,
    hud: 'OPTIMIZING NATIVE'
  },
  {
    id: 'stage-3',
    phase: '03',
    title: 'HWID Synthesis',
    description: 'We bind your binary to unique silicon signatures. By verifying Motherboard UUID, CPU Signature, and Disk Serial ID at launch, we ensure total hardware-locked security.',
    color: '#06b6d4',
    symbol: HWIDSymbol,
    hud: 'SILICON LOCK: TRUE'
  },
  {
    id: 'stage-4',
    phase: '04',
    title: 'Air-Gapped Auth',
    description: 'Monetize high-security enterprise environments without "phoning home." Our protocol issues cryptographically signed offline leases for total control.',
    color: '#10b981',
    symbol: AuthSymbol,
    hud: 'SIGNATURE VALID'
  }
];

const SPACING = 900; 

const Node = ({ stage, index, scrollProgress }: { stage: any, index: number, scrollProgress: any }) => {
  const start = index * 0.25;
  const mid = start + 0.125;
  const end = (index + 1) * 0.25;
  
  // "Tunnel" Scaling: Stages grow from 0.8x (distant) to 1.0x (focus) to 1.2x (flying past camera)
  const scale = useTransform(scrollProgress, 
    [start - 0.05, start + 0.05, end - 0.05, end + 0.05], 
    [0.8, 1, 1, 1.2]
  );
  
  const opacity = useTransform(scrollProgress, 
    [start - 0.05, start + 0.05, end - 0.05, end + 0.05], 
    [0, 1, 1, 0]
  );

  const blur = useTransform(scrollProgress,
    [start - 0.05, start, end - 0.05, end],
    ["blur(10px)", "blur(0px)", "blur(0px)", "blur(10px)"]
  );

  const Symbol = stage.symbol;

  return (
    <motion.div
      style={{ 
        position: 'absolute',
        top: index * SPACING,
        left: '50%',
        x: '-50%',
        y: '-50%',
        opacity,
        scale,
        filter: blur
      }}
      className="w-[580px] h-[420px] z-20"
    >
      {/* Dynamic Aura Glow */}
      <motion.div 
        style={{ 
          backgroundColor: stage.color,
          opacity: useTransform(scrollProgress, [start, start + 0.1], [0, 0.2])
        }}
        className="absolute inset-0 blur-[120px] rounded-full scale-90"
      />

      {/* The Simulator Window */}
      <div className="w-full h-full relative z-10">
        <Symbol color={stage.color} />
      </div>

      {/* Process HUD Overlay */}
      <motion.div
        style={{ 
          opacity: useTransform(scrollProgress, [start, start + 0.05], [0, 1]),
          y: useTransform(scrollProgress, [start, start + 0.05], [20, 0])
        }}
        className="absolute -top-6 -right-6 px-5 py-2.5 rounded-xl bg-black/80 border border-white/10 backdrop-blur-xl shadow-2xl z-30 flex items-center gap-3"
      >
        <div className="w-2.5 h-2.5 rounded-full animate-pulse shadow-[0_0_10px_rgba(255,255,255,0.5)]" style={{ backgroundColor: stage.color }} />
        <span className="text-xs font-black font-mono text-white uppercase tracking-[0.2em]">{stage.hud}</span>
      </motion.div>
    </motion.div>
  );
};

const Features: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"]
  });

  const smoothProgress = useSpring(scrollYProgress, { stiffness: 90, damping: 40, restDelta: 0.001 });
  
  const elevatorY = useTransform(smoothProgress, [0, 1], ["0px", `-${(STAGES.length - 1) * SPACING}px`]);

  // Parallax Background Grid Logic
  const gridY = useTransform(smoothProgress, [0, 1], ["0%", "-10%"]);

  // Global Section Fade (to blend with preceding/following sections)
  const sectionFade = useTransform(smoothProgress, [0, 0.05, 0.95, 1], [0, 1, 1, 0]);

  return (
    <section ref={containerRef} className="relative h-[400vh] bg-transparent">
      
      <div className="sticky top-0 h-screen w-full flex items-center justify-center overflow-hidden bg-background">
        
        {/* Transition Masks (Feathers the entrance and exit) */}
        <div className="absolute top-0 left-0 right-0 h-40 bg-gradient-to-b from-background to-transparent z-[50] pointer-events-none" />
        <div className="absolute bottom-0 left-0 right-0 h-40 bg-gradient-to-t from-background to-transparent z-[50] pointer-events-none" />

        {/* Cinematic Background Layer */}
        <motion.div style={{ opacity: sectionFade }} className="absolute inset-0 z-0">
          {/* Parallax Grid */}
          <motion.div 
            style={{ y: gridY }}
            className="absolute inset-0 opacity-[0.1]"
            side-grid="true"
          >
            <div className="absolute inset-0" style={{ 
              backgroundImage: `radial-gradient(circle at 2px 2px, #3f3f46 1px, transparent 0)`,
              backgroundSize: '48px 48px'
            }} />
          </motion.div>

          {/* Large Area Atmosphere */}
          {STAGES.map((stage, i) => (
            <motion.div 
              key={`bg-${i}`}
              style={{ 
                opacity: useTransform(smoothProgress, [i*0.25 - 0.1, i*0.25, (i+1)*0.25 - 0.1, (i+1)*0.25], [0, 0.25, 0.25, 0]),
                backgroundColor: stage.color 
              }}
              className="absolute inset-0 blur-[350px] scale-150"
            />
          ))}
        </motion.div>

        <div className="w-full h-full max-w-7xl mx-auto flex items-center relative z-10 px-6">
          
          {/* Left Side: Cinematic Copy */}
          <div className="w-[42%] h-full relative flex items-center">
            {STAGES.map((stage, i) => {
              const start = i * 0.25;
              const end = (i + 1) * 0.25;
              
              const opacity = useTransform(smoothProgress, [start - 0.02, start, end - 0.02, end], [0, 1, 1, 0]);
              const scale = useTransform(smoothProgress, [start - 0.02, start, end - 0.02, end], [0.95, 1, 1, 1.05]);
              const y = useTransform(smoothProgress, [start - 0.02, start, end - 0.02, end], [30, 0, 0, -30]);

              return (
                <motion.div key={stage.id} style={{ opacity, scale, y }} className="absolute flex flex-col justify-center">
                  <div className="flex items-center gap-5 mb-8">
                    <span className="text-[10px] font-black tracking-[0.6em] uppercase text-zinc-500">PHASE {stage.phase}</span>
                    <div className="h-px w-12 bg-zinc-800" />
                  </div>
                  <h2 className="text-8xl font-bold text-white tracking-tighter leading-[0.85] mb-10">
                    {stage.title.split(' ').map((word, wi) => (
                      <span key={wi} className="block">{word}</span>
                    ))}
                  </h2>
                  <p className="text-xl text-zinc-400 font-medium leading-relaxed max-w-sm">
                    {stage.description}
                  </p>
                  
                  {/* Phase Specific Metric/Detail */}
                  <motion.div 
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="mt-12 flex items-center gap-4 text-xs font-mono"
                    style={{ color: stage.color }}
                  >
                    <span className="w-2 h-2 rounded-full animate-ping" style={{ backgroundColor: 'currentColor' }} />
                    {stage.hud} ACTIVATED
                  </motion.div>
                </motion.div>
              );
            })}
          </div>

          {/* Right Side: Tunnel Vision Simulator */}
          <div className="w-[58%] h-full relative flex items-center justify-center">
            
            {/* Focal Vignette */}
            <div className="absolute inset-0 pointer-events-none z-30">
               <div className="h-1/3 w-full bg-gradient-to-b from-zinc-950 via-zinc-950/60 to-transparent" />
               <div className="h-1/3 w-full absolute bottom-0 bg-gradient-to-t from-zinc-950 via-zinc-950/60 to-transparent" />
            </div>

            {/* The Cinematic Track */}
            <motion.div 
              style={{ y: elevatorY }}
              className="absolute top-1/2 left-0 w-full"
            >
              {/* The Data Spine (Continuity Thread) */}
              <div className="absolute left-1/2 -translate-x-1/2 top-0 w-[2px] h-[3000px] bg-zinc-900/50 z-0">
                <motion.div 
                  style={{ 
                    height: useTransform(smoothProgress, [0, 1], ["0%", "100%"]),
                    background: useTransform(smoothProgress, STAGES.map((_, i) => i * 0.25), STAGES.map(s => `linear-gradient(to bottom, transparent, ${s.color}, transparent)`))
                  }}
                  className="w-full shadow-[0_0_30px_rgba(255,255,255,0.1)]"
                />
              </div>

              <div className="relative w-full">
                {STAGES.map((stage, i) => (
                  <Node key={stage.id} stage={stage} index={i} scrollProgress={smoothProgress} />
                ))}
              </div>
            </motion.div>

          </div>

        </div>
      </div>
    </section>
  );
};

export default Features;
