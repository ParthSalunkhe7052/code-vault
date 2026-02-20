import { Rocket, Shield, Zap, ArrowRight, Plus } from 'lucide-react';
import { Link } from 'react-router-dom';

const OnboardingHero = () => {
  return (
    <div className="relative overflow-hidden rounded-3xl border border-indigo-500/20 bg-gradient-to-br from-indigo-500/10 via-background to-background p-8 md:p-12 mb-8">
      {/* Background elements */}
      <div className="absolute top-0 right-0 -translate-y-1/2 translate-x-1/2 w-64 h-64 bg-indigo-500/10 rounded-full blur-[80px]" />
      <div className="absolute bottom-0 left-0 translate-y-1/2 -translate-x-1/2 w-64 h-64 bg-emerald-500/10 rounded-full blur-[80px]" />

      <div className="relative z-10 max-w-3xl">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/20 border border-indigo-500/30 mb-6 backdrop-blur-md">
          <Rocket size={14} className="text-indigo-400" />
          <span className="text-[10px] font-bold tracking-widest uppercase text-indigo-300">Welcome to CodeVault</span>
        </div>

        <h2 className="text-4xl md:text-5xl font-bold tracking-tight text-white mb-6 leading-tight">
          Your journey to <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-emerald-400">secure code</span> starts here.
        </h2>

        <p className="text-lg text-slate-400 mb-10 leading-relaxed">
          CodeVault turns your Python and Node.js scripts into native, hardware-locked binaries. 
          Protect your Intellectual Property and manage licenses with enterprise-grade security.
        </p>

        <div className="flex flex-wrap gap-4">
          <Link 
            to="/projects" 
            className="group flex items-center gap-2 bg-white text-black px-6 py-3 rounded-xl font-bold hover:bg-slate-100 transition-all hover:scale-[1.02]"
          >
            <Plus size={18} />
            Create Your First Project
            <ArrowRight size={18} className="transition-transform group-hover:translate-x-1" />
          </Link>
          
          <div className="flex items-center gap-6 px-4">
            <div className="flex flex-col">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">Protection</span>
              <div className="flex items-center gap-1 text-emerald-400 font-mono text-sm">
                <Shield size={14} />
                <span>Nuitka Native</span>
              </div>
            </div>
            <div className="w-px h-8 bg-white/10" />
            <div className="flex flex-col">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">Licensing</span>
              <div className="flex items-center gap-1 text-indigo-400 font-mono text-sm">
                <Zap size={14} />
                <span>HWID Locked</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OnboardingHero;
