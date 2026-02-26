import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// --- Shared Components ---

const GlassWindow = ({ title, children, color }: { title: string, children: React.ReactNode, color: string }) => (
  <div className="w-full h-full rounded-xl border border-white/10 bg-zinc-950/50 backdrop-blur-xl overflow-hidden flex flex-col shadow-2xl">
    {/* Title Bar */}
    <div className="h-8 border-b border-white/5 bg-white/5 flex items-center px-4 justify-between">
      <div className="flex gap-1.5">
        <div className="w-2.5 h-2.5 rounded-full bg-red-500/20 border border-red-500/40" />
        <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/20 border border-yellow-500/40" />
        <div className="w-2.5 h-2.5 rounded-full bg-green-500/20 border border-green-500/40" />
      </div>
      <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest">{title}</span>
      <div className="w-10" />
    </div>
    {/* Content */}
    <div className="flex-1 relative overflow-hidden">
      {children}
    </div>
  </div>
);

// --- Stage 01: Analysis (Code Editor) ---

export const AnalysisSymbol = ({ color }: { color: string }) => {
  const codeLines = [
    "import os",
    "import sys",
    "from codevault import secure",
    "",
    "@secure.license_lock",
    "def main():",
    "    print('Initializing...')",
    "    data = load_env_vars()",
    "    return process(data)",
    "",
    "if __name__ == '__main__':",
    "    main()"
  ];

  return (
    <GlassWindow title="main.py" color={color}>
      <div className="p-6 font-mono text-xs text-zinc-400 space-y-1 relative h-full">
        {codeLines.map((line, i) => (
          <div key={i} className="flex gap-4">
            <span className="text-zinc-700 w-4 text-right">{i + 1}</span>
            <span style={{ color: line.includes('import') || line.includes('from') ? color : undefined }}>
              {line}
            </span>
          </div>
        ))}
        
        {/* Scanning Beam */}
        <motion.div 
          animate={{ top: ['0%', '100%', '0%'] }}
          transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
          className="absolute left-0 right-0 h-1/3 bg-gradient-to-b from-transparent via-white/5 to-transparent z-10 pointer-events-none"
          style={{ borderBottom: `1px solid ${color}44` }}
        />

        {/* Floating Dependency Chips */}
        <div className="absolute bottom-4 right-4 flex flex-col gap-2 items-end">
          {['os', 'sys', 'crypto'].map((dep, i) => (
            <motion.div 
              key={dep}
              initial={{ x: 20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ delay: i * 0.5 }}
              className="px-2 py-1 rounded border border-white/5 bg-zinc-900 text-[9px] text-zinc-400"
            >
              + {dep}
            </motion.div>
          ))}
        </div>
      </div>
    </GlassWindow>
  );
};

// --- Stage 02: Compilation (Build Terminal) ---

export const CompilationSymbol = ({ color }: { color: string }) => {
  const logs = [
    "[Nuitka] Starting compilation...",
    "[Nuitka] Analyzing dependency tree...",
    "[Nuitka] Compiling main.py to C++...",
    "[GCC] Generating object files...",
    "[GCC] Linking shared libraries...",
    "[Nuitka] Optimizing performance...",
    "[CodeVault] Injecting security headers...",
    "[SUCCESS] Build finished: ./dist/app.exe"
  ];

  return (
    <GlassWindow title="build-terminal" color={color}>
      <div className="p-4 font-mono text-[10px] space-y-2 h-full bg-black/40">
        <div className="flex flex-col gap-1">
          {logs.map((log, i) => (
            <motion.div 
              key={i}
              initial={{ opacity: 0, x: -5 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.3 }}
              className={log.includes('SUCCESS') ? 'text-emerald-400' : 'text-zinc-500'}
            >
              <span className="mr-2 opacity-30 text-zinc-200">$&gt;</span>
              {log}
            </motion.div>
          ))}
        </div>

        {/* Progress Bar */}
        <div className="absolute bottom-4 left-4 right-4 space-y-2">
          <div className="flex justify-between text-[9px] text-zinc-600 uppercase font-bold tracking-tighter">
            <span>Progress</span>
            <span style={{ color }}>98%</span>
          </div>
          <div className="h-1 w-full bg-zinc-900 rounded-full overflow-hidden">
            <motion.div 
              animate={{ width: ['0%', '100%'] }}
              transition={{ duration: 5, repeat: Infinity }}
              className="h-full"
              style={{ backgroundColor: color }}
            />
          </div>
        </div>
      </div>
    </GlassWindow>
  );
};

// --- Stage 03: HWID (Hardware Lock) ---

export const HWIDSymbol = ({ color }: { color: string }) => {
  return (
    <GlassWindow title="silicon-auth" color={color}>
      <div className="p-6 h-full flex flex-col gap-6">
        {/* Hardware Visual Grid */}
        <div className="relative flex-1 rounded-lg border border-white/5 bg-zinc-950 overflow-hidden">
          <div className="absolute inset-0 grid grid-cols-8 grid-rows-8 opacity-20">
            {[...Array(64)].map((_, i) => (
              <div key={i} className="border-[0.5px] border-zinc-800" />
            ))}
          </div>
          
          <div className="absolute inset-0 flex items-center justify-center">
            {/* Pulsing Chip Core */}
            <motion.div 
              animate={{ 
                scale: [1, 1.05, 1],
                boxShadow: [`0 0 20px ${color}22`, `0 0 40px ${color}44`, `0 0 20px ${color}22`]
              }}
              transition={{ duration: 2, repeat: Infinity }}
              className="w-16 h-16 rounded-xl border-2 flex items-center justify-center relative bg-black"
              style={{ borderColor: color }}
            >
              <div className="w-8 h-8 rounded-full border border-dashed animate-spin-slow opacity-40" style={{ borderColor: color }} />
              <div className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-emerald-500 blur-sm" />
            </motion.div>
          </div>
        </div>

        {/* ID Metrics */}
        <div className="grid grid-cols-2 gap-3">
          {[
            { label: 'Motherboard', value: '0x7F2A-B91C', icon: 'MB' },
            { label: 'CPU Signature', value: 'INTEL-7392-X', icon: 'CPU' },
          ].map((item, i) => (
            <div key={i} className="p-2 rounded border border-white/5 bg-white/5 space-y-1">
              <div className="flex justify-between text-[8px] text-zinc-600 uppercase font-black">
                <span>{item.label}</span>
                <span className="text-emerald-500">Verified</span>
              </div>
              <div className="text-[10px] font-mono text-zinc-300">{item.value}</div>
            </div>
          ))}
        </div>
      </div>
    </GlassWindow>
  );
};

// --- Stage 04: Auth (License Card) ---

export const AuthSymbol = ({ color }: { color: string }) => {
  return (
    <GlassWindow title="license-vault" color={color}>
      <div className="p-8 h-full flex flex-col items-center justify-center gap-8">
        {/* The Premium License Card */}
        <motion.div 
          initial={{ rotateY: 20, rotateX: 10 }}
          animate={{ rotateY: -20, rotateX: -10 }}
          transition={{ duration: 6, repeat: Infinity, repeatType: "mirror", ease: "easeInOut" }}
          className="w-full aspect-[1.6/1] rounded-2xl relative overflow-hidden group perspective-1000"
        >
          {/* Card Surface */}
          <div className="absolute inset-0 bg-gradient-to-br from-zinc-800 to-zinc-950 border border-white/10 p-6 flex flex-col justify-between shadow-2xl">
            <div className="flex justify-between items-start">
              <div className="w-10 h-10 rounded-full border border-white/20 bg-white/5 flex items-center justify-center">
                <div className="w-5 h-5 rounded-full" style={{ backgroundColor: color, boxShadow: `0 0 20px ${color}` }} />
              </div>
              <div className="text-[8px] font-mono text-zinc-500 uppercase tracking-widest text-right">
                CodeVault Secure<br/>Enterprise Lease
              </div>
            </div>

            <div className="space-y-4">
              <div className="font-mono text-lg tracking-[0.2em] text-white/90">
                XXXX XXXX XXXX 7429
              </div>
              <div className="flex justify-between items-end">
                <div className="space-y-1">
                  <div className="text-[7px] text-zinc-500 uppercase font-bold">Holder</div>
                  <div className="text-[10px] text-zinc-300 font-mono">ID: SECURE_INSTANCE_01</div>
                </div>
                <div className="px-3 py-1 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 text-[9px] font-black uppercase">
                  Verified Offline
                </div>
              </div>
            </div>
          </div>

          {/* Shimmer Effect */}
          <motion.div 
            animate={{ left: ['-100%', '200%'] }}
            transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
            className="absolute inset-0 w-1/2 bg-gradient-to-r from-transparent via-white/5 to-transparent skew-x-12"
          />
        </motion.div>

        <div className="text-center space-y-2">
          <div className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest">Signed Protocol v2.4</div>
          <div className="flex gap-2 justify-center">
            <div className="w-2 h-2 rounded-full animate-pulse" style={{ backgroundColor: color }} />
            <div className="w-2 h-2 rounded-full animate-pulse delay-75" style={{ backgroundColor: color }} />
            <div className="w-2 h-2 rounded-full animate-pulse delay-150" style={{ backgroundColor: color }} />
          </div>
        </div>
      </div>
    </GlassWindow>
  );
};
