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

        {/* Beta Testimonial CTA */}
        <div className="max-w-4xl mx-auto">
           <div className="relative rounded-3xl border border-white/10 bg-gradient-to-b from-white/5 to-transparent p-10 md:p-14 text-center overflow-hidden">
              
              {/* Decorative Quote Icon */}
              <div className="absolute top-6 left-8 opacity-10">
                 <Quote size={120} className="text-white" />
              </div>

              <blockquote className="relative z-10">
                 <p className="text-2xl md:text-3xl font-medium text-slate-200 leading-relaxed mb-8">
                   "We're currently collecting testimonials from our beta users. Join our early access program to be featured here."
                 </p>
                 
                 <footer className="flex flex-col items-center justify-center gap-2">
                    <div className="text-white font-semibold">Your Company Here</div>
                    <div className="text-sm text-slate-500">Early Access Partner</div>
                    <a href="mailto:parth.ajit7052@gmail.com" className="mt-4 px-6 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-semibold transition-colors">
                      Apply for Beta
                    </a>
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