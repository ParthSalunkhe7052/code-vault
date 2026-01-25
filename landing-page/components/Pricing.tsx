import React from 'react';
import { Check } from 'lucide-react';

const PricingCard: React.FC<{
  tier: string;
  price: string;
  features: string[];
  recommended?: boolean;
  ctaLink: string;
}> = ({ tier, price, features, recommended = false, ctaLink }) => (
  <div className={`relative p-8 rounded-2xl border ${recommended ? 'border-blue-500/50 bg-blue-500/[0.03]' : 'border-white/10 bg-white/[0.02]'} flex flex-col h-full transform transition-all duration-300 hover:scale-[1.02]`}>
    {recommended && (
      <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded-full uppercase tracking-wider shadow-lg shadow-blue-500/20">
        Most Popular
      </div>
    )}
    <div className="mb-8">
      <h3 className="text-lg font-medium text-gray-300 mb-2">{tier}</h3>
      <div className="flex items-baseline gap-1">
        <span className="text-4xl font-bold text-white">${price}</span>
        <span className="text-sm text-gray-500">/month</span>
      </div>
    </div>
    
    <ul className="space-y-4 mb-8 flex-1">
      {features.map((feature, idx) => (
        <li key={idx} className="flex items-start gap-3 text-sm text-gray-300">
          <Check className="w-5 h-5 text-blue-400 shrink-0" />
          <span>{feature}</span>
        </li>
      ))}
    </ul>

    <a href={ctaLink} className={`w-full py-3 rounded-lg font-medium transition-all text-center inline-block ${
      recommended 
        ? 'bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-500/25' 
        : 'bg-white/10 hover:bg-white/20 text-white'
    }`}>
      {price === '0' ? 'Get Started' : 'Subscribe'}
    </a>
  </div>
);

const Pricing: React.FC = () => {
  const APP_URL = import.meta.env.VITE_APP_URL || "http://localhost:5173";

  return (
    <section id="pricing" className="py-32 relative bg-[#0B0C10]">
      {/* Background decoration */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-blue-900/10 rounded-full blur-[100px] pointer-events-none mix-blend-screen" />

      <div className="relative z-10 max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-5xl font-bold mb-6 tracking-tight">Simple pricing.</h2>
          <p className="text-slate-400 text-lg">
            Start for free, scale as you grow.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          <PricingCard 
            tier="Hobby"
            price="0"
            ctaLink={`${APP_URL}/signup`}
            features={[
              "1 Project",
              "Local Builds Only",
              "5 Licenses",
              "Basic Obfuscation",
              "Community Support"
            ]}
          />
          <PricingCard 
            tier="Pro"
            price="20"
            recommended={true}
            ctaLink={`${APP_URL}/signup`}
            features={[
              "Unlimited Projects",
              "Cloud Builds (Win/Mac/Linux)",
              "Unlimited Licenses",
              "Offline Crypto Leases",
              "Stripe Integration",
              "Advanced Nuitka Compilation"
            ]}
          />
          <PricingCard 
            tier="Enterprise"
            price="50"
            ctaLink={`${APP_URL}/signup`}
            features={[
              "Everything in Pro",
              "White-labeling (Custom Splash)",
              "Source Code Access",
              "Dedicated Build Runners",
              "Priority Support",
              "SLA Agreement"
            ]}
          />
        </div>
      </div>
    </section>
  );
};

export default Pricing;