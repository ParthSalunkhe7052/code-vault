import React from 'react';
import { ArrowRight, Terminal } from 'lucide-react';

const Hero: React.FC = () => {
  const APP_URL = import.meta.env.VITE_APP_URL || "http://localhost:5173";

  return (
    <div className="relative min-h-screen flex flex-col justify-center items-center pt-24 overflow-hidden bg-[#0B0C10]">
      
      {/* Optimized Background - CSS Radial Gradients (Cheap on GPU) */}
      <div className="absolute inset-0 z-0 pointer-events-none">
        <div className="absolute top-[-10%] left-1/2 -translate-x-1/2 w-[80%] h-[60%] bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-blue-900/20 via-[#0B0C10]/0 to-[#0B0C10]/0 opacity-70"></div>
        <div className="absolute bottom-[-10%] left-1/2 -translate-x-1/2 w-[60%] h-[40%] bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-purple-900/20 via-[#0B0C10]/0 to-[#0B0C10]/0 opacity-50"></div>
        {/* Grid Pattern Overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)]"></div>
      </div>

      <div className="relative z-10 max-w-5xl mx-auto px-6 text-center">
        
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 mb-8 backdrop-blur-sm animate-fade-in">
          <span className="flex h-2 w-2 rounded-full bg-green-400"></span>
          <span className="text-xs font-medium text-green-200">New: Full Node.js & Pkg Support</span>
        </div>

        {/* Heading */}
        <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-8 animate-slide-up">
          Secure your Python &<br />
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">Node.js Applications.</span>
        </h1>

        {/* Subheading */}
        <p className="text-lg md:text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed animate-slide-up [animation-delay:100ms]">
          Transform your scripts into native machine code via Nuitka. 
          Implement bank-grade security, HWID locking, and offline leases in minutes.
        </p>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16 animate-slide-up [animation-delay:200ms]">
          <a href={`${APP_URL}/signup`} className="group relative inline-flex h-12 items-center justify-center overflow-hidden rounded-full bg-white px-8 font-medium text-black transition-all duration-300 hover:bg-gray-200 hover:scale-105 focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-gray-900">
            <span className="mr-2">Start Building Free</span>
            <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
          </a>
          
          <button className="group inline-flex h-12 items-center justify-center rounded-full border border-white/10 bg-white/5 px-8 font-medium text-white transition-all hover:bg-white/10 backdrop-blur-sm">
            <Terminal className="mr-2 w-4 h-4 text-gray-400" />
            <span>Read Documentation</span>
          </button>
        </div>

        {/* Code/Terminal Preview */}
        <div className="relative w-full max-w-4xl mx-auto mt-10 rounded-xl overflow-hidden border border-white/10 shadow-2xl bg-[#0F1115] animate-slide-up [animation-delay:300ms]">
           <div className="flex items-center px-4 py-3 bg-[#16181D] border-b border-white/5">
              <div className="flex gap-2">
                 <div className="w-3 h-3 rounded-full bg-red-500/20 border border-red-500/50"></div>
                 <div className="w-3 h-3 rounded-full bg-yellow-500/20 border border-yellow-500/50"></div>
                 <div className="w-3 h-3 rounded-full bg-green-500/20 border border-green-500/50"></div>
              </div>
              <div className="ml-4 text-xs text-gray-500 font-mono">codevault-cli — bash</div>
           </div>
           <div className="p-6 text-left font-mono text-sm md:text-base leading-relaxed overflow-x-auto">
              <div className="flex">
                  <span className="text-green-400 mr-2">➜</span>
                  <span className="text-blue-400">~</span>
                  <span className="text-gray-400 ml-2">codevault build ./server.js --target node18-win-x64</span>
              </div>
              <div className="mt-2 text-slate-400">
                  <span className="text-blue-500">ℹ</span> Detecting runtime... <span className="text-green-500">Node.js v18.16.0</span><br/>
                  <span className="text-blue-500">ℹ</span> Encrypting bytecode (snapshot)... <span className="text-green-500">Done</span><br/>
                  <span className="text-blue-500">ℹ</span> Injecting HWID validation module... <span className="text-green-500">Done</span><br/>
                  <span className="text-blue-500">ℹ</span> Packaging native binary with pkg... <span className="text-green-500">Done</span><br/>
                  <br/>
                  <span className="text-green-400">✔ Build complete!</span> <span className="text-slate-500">./dist/server.exe (35 MB)</span>
              </div>
              <div className="mt-4 flex animate-pulse">
                  <span className="text-green-400 mr-2">➜</span>
                  <span className="text-blue-400">~</span>
                  <span className="w-2 h-5 bg-gray-500 ml-2"></span>
              </div>
           </div>
           
           {/* Overlay Gradient for Fade */}
           <div className="absolute inset-0 pointer-events-none bg-gradient-to-t from-[#0B0C10]/20 to-transparent"></div>
        </div>

      </div>
    </div>
  );
};

export default Hero;