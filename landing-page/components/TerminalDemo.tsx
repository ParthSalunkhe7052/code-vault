import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const TerminalDemo: React.FC = () => {
  const [step, setStep] = useState(0);
  const [lines, setLines] = useState<string[]>([]);

  const sequence = [
    { text: '$ codevault build ./server.js --target node20-win-x64 --lock=hwid', delay: 800 },
    { text: '> [1/4] Analyzing dependency tree...', delay: 1500 },
    { text: '> [2/4] Encrypting bytecode snapshot...', delay: 2200 },
    { text: '> [3/4] Injecting HWID verification module...', delay: 3000 },
    { text: '> [4/4] Signing binary with CodeVault cert...', delay: 3800 },
    { text: '✔ Build complete: ./dist/server.exe (35 MB)', delay: 4500, color: 'text-emerald-400' },
  ];

  useEffect(() => {
    let timeout: NodeJS.Timeout;

    const runSequence = async () => {
      for (let i = 0; i < sequence.length; i++) {
        await new Promise(resolve => {
          timeout = setTimeout(() => {
            setLines(prev => [...prev, sequence[i].text]);
            setStep(i);
            resolve(true);
          }, i === 0 ? 0 : sequence[i].delay - sequence[i-1].delay);
        });
      }
    };

    runSequence();

    return () => clearTimeout(timeout);
  }, []);

  return (
    <div className="w-full max-w-lg mx-auto bg-[#0a0f1a] rounded-xl overflow-hidden border border-white/10 shadow-2xl shadow-purple-900/20 font-mono text-sm">
      {/* Window Controls */}
      <div className="flex items-center px-4 py-3 bg-[#111827] border-b border-white/5">
        <div className="flex gap-2">
          <div className="w-3 h-3 rounded-full bg-red-500/20 border border-red-500/50" />
          <div className="w-3 h-3 rounded-full bg-yellow-500/20 border border-yellow-500/50" />
          <div className="w-3 h-3 rounded-full bg-green-500/20 border border-green-500/50" />
        </div>
        <div className="ml-4 text-xs text-slate-500">terminal — zsh</div>
      </div>

      {/* Terminal Body */}
      <div className="p-6 h-[240px] overflow-y-auto flex flex-col justify-end">
        {lines.map((line, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            className={`mb-2 ${sequence[index]?.color || 'text-slate-300'}`}
          >
            {line.startsWith('$') ? (
              <>
                <span className="text-purple-400 mr-2">➜</span>
                <span className="text-blue-400 mr-2">~</span>
                {line.substring(2)}
              </>
            ) : (
              line
            )}
          </motion.div>
        ))}
        <motion.div
          animate={{ opacity: [0, 1, 0] }}
          transition={{ repeat: Infinity, duration: 0.8 }}
          className="w-2 h-4 bg-slate-500 inline-block"
        />
      </div>
    </div>
  );
};

export default TerminalDemo;
