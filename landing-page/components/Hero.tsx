import React from 'react';
import { ArrowRight } from 'lucide-react';
import { APP_URL } from '../lib/config';
import TerminalDemo from './TerminalDemo';
import { motion } from 'framer-motion';

const Hero: React.FC = () => {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden bg-background pt-20">
      
      {/* Background Ambience */}
      <div className="absolute inset-0 z-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-purple-600/10 rounded-full blur-[120px] animate-pulse-slow" />
        <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-blue-600/10 rounded-full blur-[120px] animate-pulse-slow [animation-delay:2s]" />
        {/* Grid */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:40px_40px] [mask-image:radial-gradient(ellipse_80%_80%_at_50%_50%,black,transparent)]" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-6 grid lg:grid-cols-2 gap-12 items-center">
        
        {/* Left Column: Copy */}
        <div className="text-left">
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 mb-6 backdrop-blur-md"
          >
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs font-mono text-emerald-200">v2.0: Node.js Support Live</span>
          </motion.div>

          <motion.h1 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-5xl md:text-7xl font-bold tracking-tight mb-6 leading-tight"
          >
            Ship <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-purple-400 to-emerald-400">
              Uncrackable Apps.
            </span>
          </motion.h1>

          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="text-lg text-slate-400 mb-8 max-w-lg leading-relaxed"
          >
            Turn your Python & Node.js scripts into hardware-locked, native executables. 
            No interpreters. No leaks. Just revenue.
          </motion.p>

          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="flex flex-wrap gap-4"
          >
            <a href={`${APP_URL}/signup`} className="group relative inline-flex h-12 items-center justify-center overflow-hidden rounded-lg bg-white px-8 font-medium text-black transition-all hover:bg-gray-200 hover:scale-[1.02]">
              <span>Get API Keys</span>
              <ArrowRight className="ml-2 w-4 h-4 transition-transform group-hover:translate-x-1" />
            </a>
            <a href="#features" className="inline-flex h-12 items-center justify-center rounded-lg border border-white/10 bg-white/5 px-8 font-medium text-white transition-all hover:bg-white/10 backdrop-blur-sm">
              View Documentation
            </a>
          </motion.div>

          {/* Social Proof / Ecosystem */}
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="mt-12 pt-8 border-t border-white/5"
          >
            <p className="text-xs text-slate-500 font-mono mb-4">WORKS SEAMLESSLY WITH</p>
            <div className="flex gap-6 opacity-50 grayscale hover:grayscale-0 transition-all duration-500">
               {/* Simple SVG Placeholders for logos to save GPU/Bandwidth */}
               <div className="text-xs font-bold text-white flex gap-6">
                  <span>PYTHON</span>
                  <span>NODE.JS</span>
                  <span>ELECTRON</span>
                  <span>DOCKER</span>
               </div>
            </div>
          </motion.div>
        </div>

        {/* Right Column: Visuals */}
        <div className="relative">
          {/* Floating Element - Placeholder for Nano Banana Asset */}
          <motion.div
            animate={{ y: [0, -20, 0] }}
            transition={{ repeat: Infinity, duration: 6, ease: "easeInOut" }}
            className="absolute -top-20 -right-20 w-64 h-64 bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-3xl blur-3xl z-0"
          />
          
          <div className="relative z-10">
             <TerminalDemo />
          </div>

          {/* Decorative Cube (CSS-only replacement for 3D asset if generation fails) */}
          <div className="absolute -bottom-10 -right-10 w-32 h-32 border border-white/10 rounded-xl bg-white/5 backdrop-blur-md z-20 flex items-center justify-center shadow-2xl animate-float">
             <div className="text-center">
                <div className="text-2xl font-bold text-emerald-400">100%</div>
                <div className="text-xs text-slate-400">Secure</div>
             </div>
          </div>
        </div>

      </div>
    </section>
  );
};

export default Hero;
