import React from 'react';
import { Check, X } from 'lucide-react';

const PricingCard: React.FC<{
  tier: string;
  price: string;
  period: string;
  features: { text: string; included: boolean }[];
  recommended?: boolean;
  ctaLink: string;
  ctaLabel: string;
}> = ({ tier, price, period, features, recommended = false, ctaLink, ctaLabel }) => (
  <div className={`relative p-8 rounded-2xl border mt-4 ${recommended ? 'border-indigo-500/50 bg-indigo-500/[0.03]' : 'border-white/10 bg-white/[0.02]'} flex flex-col h-full transform transition-all duration-300 hover:scale-[1.02]`}>
    {recommended && (
      <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-indigo-500 text-white text-xs font-bold rounded-full uppercase tracking-wider shadow-lg shadow-indigo-500/20">
        Most Popular
      </div>
    )}
    <div className="mb-8">
      <h3 className="text-lg font-medium text-gray-300 mb-2">{tier}</h3>
      <div className="flex items-baseline gap-1">
        <span className="text-4xl font-bold text-white">${price}</span>
        <span className="text-sm text-gray-500">{period}</span>
      </div>
    </div>
    
    <ul className="space-y-4 mb-8 flex-1">
      {features.map((feature, idx) => (
        <li key={idx} className="flex items-start gap-3 text-sm">
          {feature.included ? (
            <Check className="w-5 h-5 text-indigo-400 shrink-0" />
          ) : (
            <X className="w-5 h-5 text-gray-600 shrink-0" />
          )}
          <span className={feature.included ? 'text-gray-300' : 'text-gray-600'}>{feature.text}</span>
        </li>
      ))}
    </ul>

    <a href={ctaLink} className={`w-full py-3 rounded-lg font-medium transition-all text-center inline-block ${
      recommended 
        ? 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/25' 
        : 'bg-white/10 hover:bg-white/20 text-white'
    }`}>
      {ctaLabel}
    </a>
  </div>
);

const Pricing: React.FC = () => {
  const APP_URL = import.meta.env.VITE_APP_URL || "https://app.codevault.parth7.me";

  return (
    <section id="pricing" className="py-32 relative bg-background">
      {/* Background decoration */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-indigo-900/10 rounded-full blur-[100px] pointer-events-none mix-blend-screen" />

      <div className="relative z-10 max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-5xl font-bold mb-6 tracking-tight">Simple pricing.</h2>
          <p className="text-slate-400 text-lg">
            Start for free, scale as you grow. Build once, distribute unlimited times.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          <PricingCard 
            tier="Free"
            price="0"
            period="/forever"
            ctaLink={`${APP_URL}/signup`}
            ctaLabel="Get Started"
            features={[
              { text: "1 Project", included: true },
              { text: "50 Licenses", included: true },
              { text: "Local Builds Only", included: true },
              { text: "Basic Obfuscation", included: true },
              { text: "Cloud Builds", included: false },
              { text: "Node.js Support", included: false },
              { text: "Analytics", included: false },
              { text: "Webhooks", included: false },
            ]}
          />
          <PricingCard 
            tier="Pro"
            price="15"
            period="/month"
            recommended={true}
            ctaLink={`${APP_URL}/signup`}
            ctaLabel="Subscribe"
            features={[
              { text: "Unlimited Projects", included: true },
              { text: "500 Licenses", included: true },
              { text: "25 Cloud Builds/mo", included: true },
              { text: "Node.js Support", included: true },
              { text: "Offline Crypto Leases", included: true },
              { text: "Advanced Nuitka Compilation", included: true },
              { text: "Analytics & Webhooks", included: true },
              { text: "Priority Support", included: true },
            ]}
          />
          <PricingCard 
            tier="Business"
            price="39"
            period="/month"
            ctaLink={`${APP_URL}/signup`}
            ctaLabel="Subscribe"
            features={[
              { text: "Everything in Pro", included: true },
              { text: "5,000 Licenses", included: true },
              { text: "100 Cloud Builds/mo", included: true },
              { text: "10 Team Seats", included: true },
              { text: "White-labeling (Custom Splash)", included: true },
              { text: "Dedicated Build Runners", included: true },
              { text: "SLA Agreement", included: true },
              { text: "Priority Support", included: true },
            ]}
          />
        </div>

        {/* FAQ */}
        <div className="mt-24 max-w-3xl mx-auto">
          <h3 className="text-2xl font-bold text-center mb-12">Frequently Asked Questions</h3>
          <div className="space-y-8">
            <div>
              <h4 className="text-white font-medium mb-2">What are cloud builds?</h4>
              <p className="text-sm text-gray-400 leading-relaxed">
                Cloud builds let you compile your application for Windows, macOS, and Linux from the dashboard without needing each OS locally. Each compilation counts as one build credit.
              </p>
            </div>
            <div>
              <h4 className="text-white font-medium mb-2">What does "build once, distribute unlimited" mean?</h4>
              <p className="text-sm text-gray-400 leading-relaxed">
                Once you compile your application, you can distribute the same binary to unlimited end-users. Each user gets a unique license key, but the build itself is reusable. You only use build credits when you compile, not when you distribute.
              </p>
            </div>
            <div>
              <h4 className="text-white font-medium mb-2">Can I cancel anytime?</h4>
              <p className="text-sm text-gray-400 leading-relaxed">
                Yes. You can cancel your subscription at any time. Your plan will remain active until the end of the current billing period, then downgrade to Free.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Pricing;
