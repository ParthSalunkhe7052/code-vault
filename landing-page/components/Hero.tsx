import React, { useState } from 'react';
import { ArrowRight, Sparkles, Terminal } from 'lucide-react';
import { generateHeroVisual } from '../services/geminiService';

const Hero: React.FC = () => {
  const [bgImage, setBgImage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerateBg = async () => {
    setLoading(true);
    setError(null);
    try {
      const img = await generateHeroVisual();
      setBgImage(img);
    } catch (e) {
      console.error(e);
      // Fallback: Set a slight variation to the default gradient or just show error text
      setError("AI Generation unavailable (Check API Key/Quota)");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen flex flex-col justify-center items-center pt-24 overflow-hidden">
      
      {/* Dynamic Background */}
      <div className="absolute inset-0 z-0">
        {bgImage ? (
           <div 
             className="absolute inset-0 bg-cover bg-center opacity-40 transition-opacity duration-1000"
             style={{ backgroundImage: `url(${bgImage})` }}
           />
        ) : (
          <>
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[500px] bg-blue-600/20 rounded-[100%] blur-[120px] pointer-events-none mix-blend-screen" />
            <div className="absolute top-[20%] left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-purple-600/10 rounded-[100%] blur-[100px] pointer-events-none mix-blend-screen" />
          </>
        )}
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#0B0C10]/80 to-[#0B0C10]" />
      </div>

      <div className="relative z-10 max-w-5xl mx-auto px-6 text-center">
        
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 mb-8 backdrop-blur-sm animate-float">
          <span className="flex h-2 w-2 rounded-full bg-green-400"></span>
          <span className="text-xs font-medium text-green-200">New: Full Node.js & Pkg Support</span>
        </div>

        {/* Heading */}
        <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-8">
          Secure your Python &<br />
          <span className="text-gradient-primary">Node.js Applications.</span>
        </h1>

        {/* Subheading */}
        <p className="text-lg md:text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed">
          Transform your scripts into native machine code via Nuitka. 
          Implement bank-grade security, HWID locking, and offline leases in minutes.
        </p>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
          <a href="https://app.codevault.parth7.me/login" className="group relative inline-flex h-12 items-center justify-center overflow-hidden rounded-full bg-white px-8 font-medium text-black transition-all duration-300 hover:bg-gray-200 hover:scale-105 focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-gray-900">
            <span className="mr-2">Start Building Free</span>
            <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
          </a>
          
          <button className="group inline-flex h-12 items-center justify-center rounded-full border border-white/10 bg-white/5 px-8 font-medium text-white transition-all hover:bg-white/10 backdrop-blur-sm">
            <Terminal className="mr-2 w-4 h-4 text-gray-400" />
            <span>Read Documentation</span>
          </button>
        </div>

        {/* AI Background Generator Trigger */}
        <div className="flex flex-col items-center gap-2 mb-8">
          <button 
              onClick={handleGenerateBg}
              disabled={loading}
              className={`text-xs transition-colors flex items-center justify-center mx-auto gap-1 ${error ? 'text-red-400' : 'text-slate-600 hover:text-slate-400'}`}
          >
              <Sparkles className="w-3 h-3" />
              {loading ? "Generating Visuals..." : "Generate Abstract Theme (AI)"}
          </button>
          {error && <span className="text-[10px] text-red-500/80">{error}</span>}
        </div>

        {/* Code/Terminal Preview */}
        <div className="relative w-full max-w-4xl mx-auto mt-10 rounded-xl overflow-hidden border border-white/10 shadow-2xl bg-[#0F1115]">
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