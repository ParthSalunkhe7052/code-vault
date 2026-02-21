import React, { useState } from 'react';
import { Check, X, Zap, XIcon } from 'lucide-react';
import { APP_URL } from '../lib/config';
import { motion } from 'framer-motion';
import { EnterpriseContactForm } from './EnterpriseContactForm';

const PricingCard: React.FC<{
  tier: string;
  price: string;
  period: string;
  features: { text: string; included: boolean }[];
  recommended?: boolean;
  ctaLink: string;
  ctaLabel: string;
  delay?: number;
}> = ({ tier, price, period, features, recommended = false, ctaLink, ctaLabel, delay = 0 }) => (
  <motion.div 
    initial={{ opacity: 0, y: 20 }}
    whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true }}
    transition={{ delay, duration: 0.5 }}
    className={`relative p-8 rounded-3xl border mt-4 flex flex-col h-full transform transition-all duration-300 hover:scale-[1.02] ${
      recommended 
        ? 'border-indigo-500/50 bg-indigo-500/[0.03] shadow-2xl shadow-indigo-500/10 z-10 scale-105' 
        : 'border-white/10 bg-surface hover:bg-surface/80 z-0'
    }`}
  >
    {recommended && (
      <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1.5 bg-indigo-500 text-white text-xs font-bold rounded-full uppercase tracking-wider shadow-lg shadow-indigo-500/40 flex items-center gap-2">
        <Zap size={12} fill="currentColor" />
        Most Popular
      </div>
    )}
    
    <div className="mb-8">
      <h3 className={`text-lg font-medium mb-2 ${recommended ? 'text-indigo-300' : 'text-slate-400'}`}>{tier}</h3>
      <div className="flex items-baseline gap-1">
        <span className="text-4xl font-bold text-white tracking-tight">
          {typeof price === 'string' && price.toLowerCase() === 'custom' ? price : `$${price}`}
        </span>
        {period && <span className="text-sm text-slate-500 font-medium">{period}</span>}
      </div>
    </div>
    
    <ul className="space-y-4 mb-8 flex-1">
      {features.map((feature, idx) => (
        <li key={idx} className="flex items-start gap-3 text-sm group">
          {feature.included ? (
            <div className={`mt-0.5 w-4 h-4 rounded-full flex items-center justify-center shrink-0 ${recommended ? 'bg-indigo-500/20 text-indigo-400' : 'bg-white/10 text-slate-300'}`}>
               <Check size={10} strokeWidth={3} />
            </div>
          ) : (
            <div className="mt-0.5 w-4 h-4 rounded-full flex items-center justify-center shrink-0 bg-transparent">
               <X size={12} className="text-slate-700" />
            </div>
          )}
          <span className={`${feature.included ? 'text-slate-300' : 'text-slate-600 line-through decoration-slate-700'}`}>
            {feature.text}
          </span>
        </li>
      ))}
    </ul>

    <a href={ctaLink} className={`w-full py-3.5 rounded-xl font-bold transition-all text-center inline-block ${
      recommended 
        ? 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/25 hover:shadow-indigo-500/40' 
        : 'bg-white/5 hover:bg-white/10 text-white border border-white/5'
    }`}>
      {ctaLabel}
    </a>
  </motion.div>
);

const Pricing: React.FC = () => {
  const [showEnterpriseForm, setShowEnterpriseForm] = useState(false);

  return (
    <section id="pricing" className="py-32 relative bg-background overflow-hidden">
      {/* Background decoration */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-indigo-900/10 rounded-full blur-[120px] pointer-events-none mix-blend-screen" />

      <div className="relative z-10 max-w-7xl mx-auto px-6">
        <div className="text-center mb-20 max-w-3xl mx-auto">
          <h2 className="text-4xl md:text-5xl font-bold mb-6 tracking-tight">
            Simple, transparent <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-400">pricing.</span>
          </h2>
          <p className="text-slate-400 text-lg">
            Start for free. Scale when you're profitable. No hidden fees or royalties.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 max-w-7xl mx-auto items-center">
          <PricingCard 
            tier="Free"
            price="0"
            period="/forever"
            ctaLink={`${APP_URL}/signup`}
            ctaLabel="Start Building"
            delay={0}
            features={[
              { text: "1 Project", included: true },
              { text: "50 Licenses Total", included: true },
              { text: "Local Builds Only", included: true },
              { text: "5 Trial Builds/mo", included: true },
              { text: "Community Support", included: true },
              { text: "Cloud Builds", included: false },
              { text: "Node.js Support", included: false },
            ]}
          />
          <PricingCard 
            tier="Pro"
            price="15"
            period="/month"
            recommended={true}
            ctaLink={`${APP_URL}/signup`}
            ctaLabel="Start 14-Day Trial"
            delay={0.1}
            features={[
              { text: "Unlimited Projects", included: true },
              { text: "500 Licenses", included: true },
              { text: "25 Cloud Builds/mo", included: true },
              { text: "Node.js Support", included: true },
              { text: "Offline Leases", included: true },
              { text: "No Branding / Splash", included: true },
              { text: "White Label Branding", included: false },
            ]}
          />
          <PricingCard 
            tier="Business"
            price="39"
            period="/month"
            ctaLink={`${APP_URL}/signup`}
            ctaLabel="Subscribe"
            delay={0.2}
            features={[
              { text: "Unlimited Projects", included: true },
              { text: "5,000 Licenses", included: true },
              { text: "100 Cloud Builds/mo", included: true },
              { text: "Priority Queue Access", included: true },
              { text: "Advanced Nuitka Config", included: true },
              { text: "White Label Branding", included: true },
              { text: "Priority Support", included: true },
            ]}
          />
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3, duration: 0.5 }}
            className="relative p-8 rounded-3xl border mt-4 flex flex-col h-full transform transition-all duration-300 hover:scale-[1.02] border-white/10 bg-surface hover:bg-surface/80 z-0"
          >
            <div className="mb-8">
              <h3 className="text-lg font-medium mb-2 text-slate-400">Enterprise</h3>
              <div className="flex items-baseline gap-1">
                <span className="text-4xl font-bold text-white tracking-tight">Custom</span>
              </div>
            </div>
            
             <ul className="space-y-4 mb-8 flex-1">
              {[
                { text: "Unlimited Licenses", included: true },
                { text: "Unlimited Cloud Builds", included: true },
                { text: "Unlimited Team Seats", included: true },
                { text: "Priority Queue Access", included: true },
                { text: "Custom SLAs", included: true },
                { text: "Security Audits", included: true },
                { text: "24/7 Phone Support", included: true },
              ].map((feature, idx) => (
                <li key={idx} className="flex items-start gap-3 text-sm group">
                  {feature.included ? (
                    <div className="mt-0.5 w-4 h-4 rounded-full flex items-center justify-center shrink-0 bg-white/10 text-slate-300">
                       <Check size={10} strokeWidth={3} />
                    </div>
                  ) : (
                    <div className="mt-0.5 w-4 h-4 rounded-full flex items-center justify-center shrink-0 bg-transparent">
                       <X size={12} className="text-slate-700" />
                    </div>
                  )}
                  <span className={feature.included ? 'text-slate-300' : 'text-slate-600 line-through decoration-slate-700'}>
                    {feature.text}
                  </span>
                </li>
              ))}
            </ul>

            <button 
              onClick={() => setShowEnterpriseForm(true)}
              className="w-full py-3.5 rounded-xl font-bold transition-all text-center inline-block bg-white/5 hover:bg-white/10 text-white border border-white/5"
            >
              Contact Sales
            </button>
          </motion.div>

          {/* Enterprise Contact Form Modal */}
          {showEnterpriseForm && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
              <div className="relative w-full max-w-lg bg-surface border border-white/10 rounded-2xl p-8">
                <button
                  onClick={() => setShowEnterpriseForm(false)}
                  className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors"
                >
                  <XIcon size={24} />
                </button>
                <h3 className="text-2xl font-bold text-white mb-2 text-center">Enterprise Plan</h3>
                <p className="text-slate-400 text-center mb-6">Get in touch for custom pricing and dedicated support.</p>
                <EnterpriseContactForm />
              </div>
            </div>
          )}
        </div>

        {/* FAQ Section */}
        <div className="mt-32 max-w-3xl mx-auto">
          <h3 className="text-2xl font-bold text-center mb-12">Common Questions</h3>
          <div className="space-y-1">
              <div className="p-6 rounded-2xl bg-surface border border-white/5 hover:border-white/10 transition-colors">
                 <h4 className="font-semibold text-white mb-2">What is a "Cloud Build"?</h4>
                 <p className="text-sm text-slate-400 leading-relaxed">
                    A Cloud Build is a remote compilation job. We spin up a fresh VM, install your dependencies, run Nuitka, and return a signed binary. 
                    You get 25/mo on Pro. Local builds (on your own machine) are always unlimited and free.
                 </p>
                  <p className="text-sm text-slate-500 leading-relaxed mt-2">
                    <span className="text-amber-400">Note:</span> Cloud Builds support Windows and Linux. macOS users can build locally using the CLI for native macOS executables.
                  </p>
              </div>
             <div className="p-6 rounded-2xl bg-[#0f1219] border border-white/5 hover:border-white/10 transition-colors">
                <h4 className="font-semibold text-white mb-2">Can I sell my software?</h4>
                <p className="text-sm text-slate-400 leading-relaxed">
                   Yes! You own 100% of the binaries you build. We don't take royalties. You just pay for the platform to manage the licenses.
                </p>
             </div>
             <div className="p-6 rounded-2xl bg-[#0f1219] border border-white/5 hover:border-white/10 transition-colors">
                <h4 className="font-semibold text-white mb-2">How secure is "Hardware Locking"?</h4>
                <p className="text-sm text-slate-400 leading-relaxed">
                   Very. We bind the license to the CPU ID, Motherboard Serial, and Disk Serial. If a user copies the .exe to another PC, 
                   it will detect the hardware mismatch and refuse to run (or request a new activation, depending on your settings).
                </p>
             </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Pricing;