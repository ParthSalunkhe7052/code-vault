import React from 'react';
import { Code2, Cloud, FileCode, Users } from 'lucide-react';

const Step: React.FC<{
  icon: React.ReactNode;
  title: string;
  description: string;
  stepNumber: string;
}> = ({ icon, title, description, stepNumber }) => (
  <div className="relative flex flex-col items-center text-center z-10 group">
    
    {/* Icon Container */}
    <div className="w-20 h-20 rounded-3xl bg-[#0f1219] border border-white/10 flex items-center justify-center text-slate-300 mb-8 shadow-2xl relative transition-transform duration-500 group-hover:scale-110 group-hover:border-white/20">
       
       {/* Inner Glow */}
       <div className="absolute inset-0 rounded-3xl bg-blue-500/5 blur-xl group-hover:bg-blue-500/10 transition-colors" />
       
       {/* Step Badge */}
       <div className="absolute -top-3 -right-3 w-8 h-8 rounded-full bg-[#0a0f1a] border border-white/10 flex items-center justify-center text-xs font-mono text-slate-500 shadow-lg">
         {stepNumber}
       </div>

       {icon}
    </div>

    <h3 className="text-xl font-bold text-white mb-3">{title}</h3>
    <p className="text-sm text-slate-400 leading-relaxed max-w-[240px] group-hover:text-slate-300 transition-colors">
      {description}
    </p>
  </div>
);

const HowItWorks: React.FC = () => {
  return (
    <section id="how-it-works" className="py-32 bg-background relative overflow-hidden">
      <div className="max-w-7xl mx-auto px-6">
        
        <div className="text-center mb-24">
           <h2 className="text-4xl md:text-5xl font-bold mb-6 tracking-tight">The Pipeline</h2>
           <p className="text-slate-400 text-lg">Build once. Sell forever.</p>
        </div>

        <div className="relative grid grid-cols-1 md:grid-cols-4 gap-12 md:gap-4">
          
          {/* Animated Connector Line (Desktop) */}
          <div className="hidden md:block absolute top-10 left-[12%] right-[12%] h-[2px] bg-white/5 overflow-hidden rounded-full">
             <div className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-blue-500/50 to-transparent w-[50%] animate-loading-bar" />
          </div>

          <Step 
            stepNumber="01"
            icon={<Code2 className="w-8 h-8 text-blue-400" />}
            title="Develop"
            description="Write your Python or Node.js code. No weird proprietary syntax required."
          />
          
          <Step 
            stepNumber="02"
            icon={<Cloud className="w-8 h-8 text-purple-400" />}
            title="Cloud Build"
            description="Push to CodeVault. We inject HWID locks and compile to native code."
          />

          <Step 
            stepNumber="03"
            icon={<FileCode className="w-8 h-8 text-emerald-400" />}
            title="Sign"
            description="We cryptographically sign license responses to prevent tampering."
          />

          <Step 
            stepNumber="04"
            icon={<Users className="w-8 h-8 text-amber-400" />}
            title="Profit"
            description="Distribute the .exe. Manage licenses via our dashboard or API."
          />

        </div>
      </div>
    </section>
  );
};

export default HowItWorks;
