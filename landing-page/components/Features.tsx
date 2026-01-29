import React from 'react';
import { Lock, Globe, Wallet, Zap, ShieldCheck, Download, LayoutDashboard, BadgeCheck } from 'lucide-react';

const FeatureCard: React.FC<{
  title: string;
  description: string;
  icon: React.ReactNode;
  className?: string;
  children?: React.ReactNode;
  fullWidthDesc?: boolean;
}> = ({ title, description, icon, className = "", children, fullWidthDesc = false }) => (
  <div 
    className={`relative overflow-hidden rounded-3xl border border-white/10 bg-white/[0.02] p-8 hover:bg-white/[0.04] transition-colors duration-300 flex flex-col group ${className}`}
  >
    <div className="relative z-10 flex flex-col h-full pointer-events-none">
      <div className="w-12 h-12 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-white mb-6 backdrop-blur-sm">
        {icon}
      </div>
      
      <h3 className="text-xl font-semibold text-white mb-3">{title}</h3>
      <p className={`text-slate-400 text-sm leading-relaxed mb-6 ${fullWidthDesc ? 'max-w-full' : 'max-w-[90%] md:max-w-[60%]'}`}>
        {description}
      </p>
      
      {/* Visual Container */}
      <div className="flex-grow relative pointer-events-auto">
         {children}
      </div>
    </div>

    {/* Decorative Gradients */}
    <div className="absolute top-0 right-0 -mr-20 -mt-20 w-64 h-64 bg-blue-500/5 rounded-full blur-3xl pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
    <div className="absolute bottom-0 left-0 -ml-20 -mb-20 w-64 h-64 bg-purple-500/5 rounded-full blur-3xl pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
  </div>
);

const Features: React.FC = () => {
  return (
    <section id="features" className="py-32 bg-[#0B0C10] relative">
      <div className="max-w-7xl mx-auto px-6">
        
        <div className="mb-24 md:text-center max-w-3xl mx-auto">
           <h2 className="text-4xl md:text-5xl font-bold mb-6 tracking-tight">
             Everything you need to <span className="text-gradient-primary">sell software.</span>
           </h2>
           <p className="text-slate-400 text-lg">
             We combine military-grade code protection with a modern e-commerce platform.
           </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 auto-rows-[minmax(250px,auto)]">
           
           {/* Card 1: Global Marketplace - Large Span */}
           <FeatureCard 
             className="md:col-span-2 min-h-[320px]"
             title="Global Marketplace"
             description="Reach customers in 45+ countries. We act as the Merchant of Record, handling VAT, GST, and compliance so you don't have to."
             icon={<Globe className="w-6 h-6 text-blue-400" />}
             fullWidthDesc={true}
           >
             <div className="absolute bottom-6 right-6 flex gap-4">
                <div className="bg-[#0F1115] border border-white/10 p-3 rounded-lg flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center">
                    <span className="text-xs">🇺🇸</span>
                  </div>
                  <div className="text-xs">
                    <div className="text-gray-400">USA Sales</div>
                    <div className="text-white font-mono">$1,204.00</div>
                  </div>
                </div>
                 <div className="hidden sm:flex bg-[#0F1115] border border-white/10 p-3 rounded-lg items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-purple-500/20 flex items-center justify-center">
                    <span className="text-xs">🇩🇪</span>
                  </div>
                  <div className="text-xs">
                    <div className="text-gray-400">EU Sales</div>
                    <div className="text-white font-mono">€840.00</div>
                  </div>
                </div>
             </div>
           </FeatureCard>

           {/* Card 2: Seller Dashboard */}
           <FeatureCard 
             className="md:col-span-1"
             title="Seller Dashboard"
             description="Track views, conversion rates, and revenue in real-time."
             icon={<LayoutDashboard className="w-6 h-6 text-purple-400" />}
             fullWidthDesc={true}
           >
             <div className="mt-8 p-4 bg-[#0F1115] rounded-xl border border-white/5 opacity-80">
                <div className="flex justify-between items-end mb-2">
                   <div className="text-2xl font-bold text-white">$4,290</div>
                   <div className="text-xs text-green-400">+12%</div>
                </div>
                <div className="flex gap-1 h-8 items-end">
                   <div className="w-1/5 h-[40%] bg-blue-500/30 rounded-t"></div>
                   <div className="w-1/5 h-[60%] bg-blue-500/30 rounded-t"></div>
                   <div className="w-1/5 h-[30%] bg-blue-500/30 rounded-t"></div>
                   <div className="w-1/5 h-[80%] bg-blue-500/30 rounded-t"></div>
                   <div className="w-1/5 h-[100%] bg-blue-500 rounded-t"></div>
                </div>
             </div>
           </FeatureCard>

           {/* Card 3: Auto Fulfillment */}
           <FeatureCard 
             className="md:col-span-1"
             title="Auto License Fulfillment"
             description="Instant delivery. Buyers get a download link + license key immediately after payment."
             icon={<Zap className="w-6 h-6 text-yellow-400" />}
             fullWidthDesc={true}
           >
              <div className="mt-6 flex items-center gap-3 text-xs text-gray-400 bg-black/20 p-3 rounded-lg border border-white/5">
                 <BadgeCheck className="w-4 h-4 text-green-500" />
                 <span>License Key sent to buyer@email.com</span>
              </div>
           </FeatureCard>

            {/* Card 4: Protected Binary - Large Span */}
            <FeatureCard 
             className="md:col-span-2 min-h-[280px]"
             title="Piracy-Proof Distribution"
             description="Buyers don't get your source code. They get a compiled, HWID-locked binary that only runs on their machine."
             icon={<ShieldCheck className="w-6 h-6 text-green-400" />}
           >
              <div className="absolute bottom-6 right-6 flex items-center gap-3 bg-[#0F1115] p-3 rounded-xl border border-white/10 shadow-xl">
                 <div className="px-3 py-1.5 rounded-full bg-red-500/10 border border-red-500/20 flex items-center gap-2">
                    <Lock className="w-3 h-3 text-red-400" />
                    <span className="text-xs font-medium text-red-400">Source Code Hidden</span>
                 </div>
                 <div className="px-3 py-1.5 rounded-full bg-green-500/10 border border-green-500/20 flex items-center gap-2">
                    <Download className="w-3 h-3 text-green-400" />
                    <span className="text-xs font-medium text-green-400">Binary Only</span>
                 </div>
              </div>
           </FeatureCard>

           {/* Card 5: Wallet/Payouts */}
           <FeatureCard 
             title="Instant Payouts"
             description="Withdraw earnings via Bank Transfer or UPI. Transparent fee structure."
             icon={<Wallet className="w-6 h-6 text-orange-400" />}
             className="md:col-span-1"
             fullWidthDesc={true}
           />

           {/* Card 6: Native Compilation */}
           <FeatureCard 
             title="Native Compilation"
             description="Powered by Nuitka for true C-level compilation and performance."
             icon={<Lock className="w-6 h-6 text-blue-300" />}
             className="md:col-span-1"
             fullWidthDesc={true}
           />

        </div>
      </div>
    </section>
  );
};

export default Features;