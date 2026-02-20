import React from 'react';
import { ArrowRight, Terminal } from 'lucide-react';
import { APP_URL } from '../lib/config';
import TerminalDemo from './TerminalDemo';
import { motion } from 'framer-motion';

const Hero: React.FC = () => {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden bg-background pt-20">
      
      {/* Background Ambience - High Zazz, Optimized GPU */}
      <div className="absolute inset-0 z-0 pointer-events-none">
        <div className="absolute top-[-10%] left-1/2 -translate-x-1/2 w-[1000px] h-[600px] bg-indigo-600/10 rounded-[100%] blur-[80px]" />
        <div className="absolute bottom-[-10%] left-1/4 w-[600px] h-[400px] bg-purple-600/5 rounded-[100%] blur-[60px]" />
        
        {/* Subtle Grid with Radial Fade */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:64px_64px] [mask-image:radial-gradient(ellipse_60%_60%_at_50%_50%,#000_70%,transparent_100%)]" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-6 grid lg:grid-cols-2 gap-16 items-center">
        
        {/* Left Column: Copy */}
        <div className="text-left">
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 mb-8 backdrop-blur-md"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
            <span className="text-[10px] font-bold tracking-widest uppercase text-indigo-300">Enterprise Grade Protection</span>
          </motion.div>

          <motion.h1 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-6xl md:text-8xl font-bold tracking-tighter mb-8 leading-[0.9] text-white"
          >
            Ship <br />
            <span className="text-transparent bg-clip-text bg-[linear-gradient(to_top_right,var(--tw-gradient-stops))] from-cyan-400 via-indigo-500 to-white">
              Protected.
            </span>
          </motion.h1>

          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="text-xl text-slate-400 mb-10 max-w-lg leading-relaxed font-medium"
          >
            The first compiler-as-a-service that turns Python & Node.js scripts into native, hardware-locked binaries.
          </motion.p>

          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="flex flex-wrap gap-4"
          >
            <a href={`${APP_URL}/signup`} className="group relative inline-flex h-14 items-center justify-center overflow-hidden rounded-xl bg-white px-10 font-bold text-black transition-all hover:bg-slate-100 hover:scale-[1.02] shadow-2xl shadow-white/10">
              <span>Get Started</span>
              <ArrowRight className="ml-2 w-5 h-5 transition-transform group-hover:translate-x-1" />
            </a>
<a href="#how-it-works" className="inline-flex h-14 items-center justify-center rounded-xl border border-white/10 bg-white/5 px-10 font-bold text-white transition-all hover:bg-white/10 backdrop-blur-sm">
              <Terminal className="w-5 h-5 mr-2 text-slate-500" />
              How It Works
            </a>
          </motion.div>

          {/* Integration Bar */}
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="mt-16 pt-10 border-t border-white/5"
          >
            <div className="flex gap-10 items-center opacity-30 grayscale contrast-200">
               <span className="text-sm font-black tracking-tighter">PYTHON</span>
               <span className="text-sm font-black tracking-tighter">NODE.JS</span>
               <span className="text-sm font-black tracking-tighter">DOCKER</span>
               <span className="text-sm font-black tracking-tighter">GITHUB</span>
            </div>
          </motion.div>
        </div>

        {/* Right Column: Interactive UI Visual */}
        <div className="relative group">
          {/* Main Terminal */}
          <div className="relative z-10 scale-110 lg:translate-x-10 transition-transform duration-700 group-hover:scale-[1.12]">
             <TerminalDemo />
          </div>

          {/* Abstract Floating UI Elements (UI-Only run) */}
          <motion.div 
            animate={{ y: [0, -15, 0] }}
            transition={{ repeat: Infinity, duration: 5, ease: "easeInOut" }}
            className="absolute -top-12 -left-12 w-48 p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-xl z-20 shadow-2xl hidden xl:block"
          >
             <div className="flex items-center gap-3 mb-3">
                <div className="w-2 h-2 rounded-full bg-emerald-500" />
                <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Build Verified</div>
             </div>
             <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                <div className="h-full w-[100%] bg-emerald-500 rounded-full" />
             </div>
          </motion.div>

          <motion.div 
            animate={{ y: [0, 15, 0] }}
            transition={{ repeat: Infinity, duration: 6, ease: "easeInOut", delay: 1 }}
            className="absolute -bottom-12 -right-4 w-56 p-5 rounded-2xl bg-indigo-600 border border-indigo-400/50 z-20 shadow-2xl hidden xl:block"
          >
             <div className="text-xs font-bold text-white mb-1">HWID Hash</div>
             <div className="text-[10px] font-mono text-indigo-200 break-all opacity-80">
                0x7F2A...B91C
             </div>
          </motion.div>
        </div>

      </div>
    </section>
  );
};

export default Hero;
