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

// Reduced spacing for snappier feel — proportional to 250vh total
const SPACING = 600;

const Node = ({ stage, index, scrollProgress }: { stage: typeof STAGES[0], index: number, scrollProgress: ReturnType<typeof useSpring> }) => {
  const start = index * 0.25;
  const end = (index + 1) * 0.25;

  // Snap-in: tight entrance band (0.08) so the stage "clicks" into place quickly
  const scale = useTransform(scrollProgress,
    [start - 0.04, start + 0.08, end - 0.08, end + 0.04],
    [0.88, 1, 1, 1.12]
  );

  const opacity = useTransform(scrollProgress,
    [start - 0.04, start + 0.08, end - 0.08, end + 0.04],
    [0, 1, 1, 0]
  );

  // Removed filter:blur — it forces GPU rasterization of a new layer on every frame
  // and is the single most expensive effect in the original implementation.

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
        // GPU promotion: composited transform+opacity only — no layout/paint triggers
        willChange: 'transform, opacity',
      }}
      className="w-[580px] h-[420px] z-20"
    >
      {/* Dynamic Aura Glow */}
      <motion.div
        style={{
          backgroundColor: stage.color,
          opacity: useTransform(scrollProgress, [start, start + 0.1], [0, 0.18])
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
          opacity: useTransform(scrollProgress, [start, start + 0.06], [0, 1]),
          y: useTransform(scrollProgress, [start, start + 0.06], [16, 0])
        }}
        className="absolute -top-6 -right-6 px-5 py-2.5 rounded-xl bg-black/80 border border-white/10 backdrop-blur-xl shadow-2xl z-30 flex items-center gap-3"
      >
        <div className="w-2.5 h-2.5 rounded-full animate-pulse shadow-[0_0_10px_rgba(255,255,255,0.5)]" style={{ backgroundColor: stage.color }} />
        <span className="text-xs font-black font-mono text-white uppercase tracking-[0.2em]">{stage.hud}</span>
      </motion.div>
    </motion.div>
  );
};

// ─── Mobile: simple stacked cards, no scroll-tunnel ─────────────────────────
const MobileFeatures: React.FC = () => (
  <div className="lg:hidden py-24 px-6 space-y-8 max-w-lg mx-auto">
    <div className="text-center mb-16">
      <span className="text-[10px] font-black tracking-[0.5em] uppercase text-zinc-500">The Pipeline</span>
      <h2 className="text-4xl font-bold text-white tracking-tighter mt-3">How we protect your code</h2>
    </div>
    {STAGES.map((stage, i) => {
      const Symbol = stage.symbol;
      return (
        <motion.div
          key={stage.id}
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-60px' }}
          transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
          className="rounded-3xl border border-white/8 bg-white/[0.02] overflow-hidden"
        >
          {/* Stage symbol — contained, no overflow */}
          <div className="relative h-56 flex items-center justify-center overflow-hidden">
            <div
              className="absolute inset-0 blur-[80px] opacity-20 scale-90"
              style={{ backgroundColor: stage.color }}
            />
            <div className="relative z-10 w-[260px] h-[190px]">
              <Symbol color={stage.color} />
            </div>
          </div>

          <div className="p-6 border-t border-white/5">
            <div className="flex items-center gap-4 mb-4">
              <span className="text-[10px] font-black tracking-[0.5em] uppercase text-zinc-500">PHASE {stage.phase}</span>
              <div
                className="h-px flex-1"
                style={{ backgroundColor: `${stage.color}30` }}
              />
              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: stage.color }} />
            </div>
            <h3 className="text-2xl font-bold text-white tracking-tight mb-3">{stage.title}</h3>
            <p className="text-sm text-zinc-400 leading-relaxed">{stage.description}</p>
            <div className="mt-4 flex items-center gap-2 text-[11px] font-mono" style={{ color: stage.color }}>
              <span className="w-1.5 h-1.5 rounded-full animate-ping" style={{ backgroundColor: 'currentColor' }} />
              {stage.hud}
            </div>
          </div>
        </motion.div>
      );
    })}
  </div>
);

// ─── Desktop: sticky scroll-tunnel ──────────────────────────────────────────
const DesktopFeatures: React.FC<{
  smoothProgress: ReturnType<typeof useSpring>;
}> = ({ smoothProgress }) => {
  const elevatorY = useTransform(smoothProgress, [0, 1], ['0px', `-${(STAGES.length - 1) * SPACING}px`]);
  const gridY = useTransform(smoothProgress, [0, 1], ['0%', '-10%']);
  const sectionFade = useTransform(smoothProgress, [0, 0.05, 0.95, 1], [0, 1, 1, 0]);

  return (
    <div className="hidden lg:block sticky top-0 h-screen w-full flex items-center justify-center overflow-hidden bg-background">

      {/* Transition Masks */}
      <div className="absolute top-0 left-0 right-0 h-40 bg-gradient-to-b from-background to-transparent z-[50] pointer-events-none" />
      <div className="absolute bottom-0 left-0 right-0 h-40 bg-gradient-to-t from-background to-transparent z-[50] pointer-events-none" />

      {/* Cinematic Background */}
      <motion.div style={{ opacity: sectionFade }} className="absolute inset-0 z-0">
        <motion.div
          style={{ y: gridY }}
          className="absolute inset-0 opacity-[0.08]"
        >
          <div className="absolute inset-0" style={{
            backgroundImage: `radial-gradient(circle at 2px 2px, #3f3f46 1px, transparent 0)`,
            backgroundSize: '48px 48px'
          }} />
        </motion.div>

        {STAGES.map((stage, i) => (
          <motion.div
            key={`bg-${i}`}
            style={{
              opacity: useTransform(smoothProgress, [i * 0.25 - 0.1, i * 0.25, (i + 1) * 0.25 - 0.1, (i + 1) * 0.25], [0, 0.22, 0.22, 0]),
              backgroundColor: stage.color
            }}
            className="absolute inset-0 blur-[350px] scale-150"
          />
        ))}
      </motion.div>

      <div className="w-full h-full max-w-7xl mx-auto flex items-center relative z-10 px-6">

        {/* Left: Copy */}
        <div className="w-[42%] h-full relative flex items-center">
          {STAGES.map((stage, i) => {
            const start = i * 0.25;
            const end = (i + 1) * 0.25;
            const opacity = useTransform(smoothProgress, [start - 0.02, start + 0.08, end - 0.08, end], [0, 1, 1, 0]);
            const scale = useTransform(smoothProgress, [start - 0.02, start + 0.08, end - 0.08, end], [0.96, 1, 1, 1.04]);
            const y = useTransform(smoothProgress, [start - 0.02, start + 0.08, end - 0.08, end], [24, 0, 0, -24]);

            return (
              <motion.div
                key={stage.id}
                style={{ opacity, scale, y, willChange: 'transform, opacity' }}
                className="absolute flex flex-col justify-center"
              >
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

        {/* Right: Tunnel Simulator */}
        <div className="w-[58%] h-full relative flex items-center justify-center">

          {/* Focal Vignette */}
          <div className="absolute inset-0 pointer-events-none z-30">
            <div className="h-1/3 w-full bg-gradient-to-b from-zinc-950 via-zinc-950/60 to-transparent" />
            <div className="h-1/3 w-full absolute bottom-0 bg-gradient-to-t from-zinc-950 via-zinc-950/60 to-transparent" />
          </div>

          {/* Cinematic Track */}
          <motion.div
            style={{ y: elevatorY }}
            className="absolute top-1/2 left-0 w-full"
          >
            {/* Data Spine */}
            <div className="absolute left-1/2 -translate-x-1/2 top-0 w-[2px] h-[2400px] bg-zinc-900/50 z-0">
              <motion.div
                style={{
                  height: useTransform(smoothProgress, [0, 1], ['0%', '100%']),
                  background: useTransform(
                    smoothProgress,
                    STAGES.map((_, i) => i * 0.25),
                    STAGES.map(s => `linear-gradient(to bottom, transparent, ${s.color}, transparent)`)
                  )
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
  );
};

// ─── Main component ──────────────────────────────────────────────────────────
const Features: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ['start start', 'end end']
  });

  // Snappier spring: higher stiffness snaps stages into place quickly,
  // lower damping allows a brief overshoot that feels tactile.
  const smoothProgress = useSpring(scrollYProgress, {
    stiffness: 250,
    damping: 28,
    restDelta: 0.001
  });

  return (
    // id="features" — fixes the broken #features anchor from the navbar
    <section id="features" ref={containerRef} className="relative h-[250vh] bg-transparent">
      {/* Desktop sticky tunnel */}
      <DesktopFeatures smoothProgress={smoothProgress} />

      {/* Mobile stacked cards — rendered outside the sticky wrapper so it
          flows naturally in the document and doesn't fight the 250vh height */}
      <MobileFeatures />
    </section>
  );
};

export default Features;
