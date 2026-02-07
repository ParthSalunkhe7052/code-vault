import React from 'react';
import { Quote } from 'lucide-react';

const TechLogo: React.FC<{ name: string; className?: string }> = ({ name, className = "" }) => (
  <div className={`flex items-center gap-2 px-6 py-3 rounded-lg border border-white/5 bg-white/[0.02] hover:bg-white/[0.05] transition-colors cursor-default group ${className}`}>
    <span className="font-mono text-sm font-semibold text-slate-400 group-hover:text-white transition-colors">
      {name}
    </span>
  </div>
);

const Testimonials: React.FC = () => {
  return (
    <section className="py-24 bg-[#0a0f1a] relative">
      <div className="max-w-7xl mx-auto px-6">
        
        {/* Ecosystem / Trust Bar */}
        <div className="text-center mb-20">
          <p className="text-sm font-mono text-slate-500 mb-8 uppercase tracking-widest">
            Seamlessly integrated with your stack
          </p>
          
          <div className="flex flex-wrap justify-center gap-4 opacity-80">
             <TechLogo name="PYTHON 3.11+" />
             <TechLogo name="NODE.JS 18+" />
             <TechLogo name="ELECTRON" />
             <TechLogo name="DOCKER" />
             <TechLogo name="GITHUB ACTIONS" />
             <TechLogo name="STRIPE" />
          </div>
        </div>

        {/* The "Indie Hacker" Featured Quote */}
        <div className="max-w-4xl mx-auto">
           <div className="relative rounded-3xl border border-white/10 bg-gradient-to-b from-white/5 to-transparent p-10 md:p-14 text-center overflow-hidden">
              
              {/* Decorative Quote Icon */}
              <div className="absolute top-6 left-8 opacity-10">
                 <Quote size={120} className="text-white" />
              </div>

              <blockquote className="relative z-10">
                 <p className="text-2xl md:text-3xl font-medium text-slate-200 leading-relaxed mb-8">
                   "Finally, I can distribute my algorithmic trading bot without finding it on BlackHatWorld the next day. <span className="text-white font-bold decoration-purple-500 decoration-2 underline underline-offset-4">CodeVault is the Stripe for Licensing.</span>"
                 </p>
                 
                 <footer className="flex flex-col items-center justify-center gap-2">
                    <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center text-white font-bold text-lg mb-2 shadow-lg shadow-blue-500/20">
                       A
                    </div>
                    <div className="text-white font-semibold">Alex V.</div>
                    <div className="text-sm text-slate-500">Indie Developer & Algo Trader</div>
                 </footer>
              </blockquote>

              {/* Bottom Gradient Fade */}
              <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-[#0a0f1a] to-transparent pointer-events-none opacity-50" />
           </div>
        </div>

      </div>
    </section>
  );
};

export default Testimonials;