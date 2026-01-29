import React from 'react';
import { Code2, Globe, DollarSign, Rocket } from 'lucide-react';

const Step: React.FC<{
  icon: React.ReactNode;
  title: string;
  description: string;
  stepNumber: string;
}> = ({ icon, title, description, stepNumber }) => (
  <div className="relative flex flex-col items-center text-center p-6 z-10">
    <div className="absolute top-0 right-1/2 translate-x-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-[#0B0C10] border border-white/10 flex items-center justify-center text-xs text-gray-400 font-mono z-10 shadow-lg">
      {stepNumber}
    </div>
    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-[#1c1e26] to-[#0B0C10] border border-white/10 flex items-center justify-center text-blue-400 mb-6 shadow-2xl ring-1 ring-white/5">
      {icon}
    </div>
    <h3 className="text-lg font-semibold text-white mb-2">{title}</h3>
    <p className="text-sm text-gray-400 leading-relaxed max-w-[200px]">{description}</p>
  </div>
);

const HowItWorks: React.FC = () => {
  return (
    <section id="how-it-works" className="py-24 bg-[#0F1115] border-y border-white/5 overflow-hidden">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
           <h2 className="text-3xl md:text-4xl font-bold mb-4">From Script to Revenue</h2>
           <p className="text-gray-400">The easiest way to monetize your desktop software.</p>
        </div>

        <div className="relative grid grid-cols-1 md:grid-cols-4 gap-8">
          
          {/* Connector Line (Desktop) */}
          <div className="hidden md:block absolute top-[3.5rem] left-[10%] right-[10%] h-[2px] bg-gradient-to-r from-transparent via-blue-500/20 to-transparent" />

          <Step 
            stepNumber="01"
            icon={<Code2 className="w-8 h-8" />}
            title="Build"
            description="Write your tool in Python or Node.js. No complex SDKs required."
          />
          
          <Step 
            stepNumber="02"
            icon={<Rocket className="w-8 h-8" />}
            title="Publish"
            description="Upload to CodeVault. We compile it to a secure, protected binary automatically."
          />

          <Step 
            stepNumber="03"
            icon={<Globe className="w-8 h-8" />}
            title="Sell"
            description="Your tool gets a dedicated store page. Buyers pay, we deliver the license & binary."
          />

          <Step 
            stepNumber="04"
            icon={<DollarSign className="w-8 h-8" />}
            title="Earn"
            description="Track sales in real-time. Receive automated payouts directly to your bank."
          />

        </div>
      </div>
    </section>
  );
};

export default HowItWorks;