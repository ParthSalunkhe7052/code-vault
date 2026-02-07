import React from 'react';
import { Quote, Shield, Clock, Server } from 'lucide-react';

const Testimonials: React.FC = () => {
  return (
    <section className="py-24 bg-surface border-y border-white/5">
      <div className="max-w-7xl mx-auto px-6">
        
        {/* Trust Badges */}
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold mb-4">Trusted by Developers</h2>
          <p className="text-gray-400">Join hundreds of developers protecting their software</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-20">
          <div className="flex items-center gap-4 p-6 rounded-xl bg-white/[0.02] border border-white/5">
            <div className="w-12 h-12 rounded-full bg-green-500/10 flex items-center justify-center">
              <Shield className="w-6 h-6 text-green-400" />
            </div>
            <div>
              <div className="text-2xl font-bold text-white">99.9%</div>
              <div className="text-sm text-gray-400">Uptime SLA</div>
            </div>
          </div>

          <div className="flex items-center gap-4 p-6 rounded-xl bg-white/[0.02] border border-white/5">
            <div className="w-12 h-12 rounded-full bg-blue-500/10 flex items-center justify-center">
              <Server className="w-6 h-6 text-blue-400" />
            </div>
            <div>
              <div className="text-2xl font-bold text-white">500+</div>
              <div className="text-sm text-gray-400">Protected Applications</div>
            </div>
          </div>

          <div className="flex items-center gap-4 p-6 rounded-xl bg-white/[0.02] border border-white/5">
            <div className="w-12 h-12 rounded-full bg-purple-500/10 flex items-center justify-center">
              <Clock className="w-6 h-6 text-purple-400" />
            </div>
            <div>
              <div className="text-2xl font-bold text-white">24/7</div>
              <div className="text-sm text-gray-400">License Validation</div>
            </div>
          </div>
        </div>

        {/* Testimonials */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="p-8 rounded-2xl bg-white/[0.02] border border-white/5 relative">
            <Quote className="w-10 h-10 text-white/10 absolute top-6 left-6" />
            <p className="text-gray-300 mb-6 relative z-10 pl-8">
              "CodeVault completely changed how we distribute our Python tools. The hardware locking 
              is solid, and our customers love the seamless license activation process."
            </p>
            <div className="flex items-center gap-4 pl-8">
              <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white font-bold">
                JD
              </div>
              <div>
                <div className="font-medium text-white">John Developer</div>
                <div className="text-sm text-gray-400">Indie Software Vendor</div>
              </div>
            </div>
          </div>

          <div className="p-8 rounded-2xl bg-white/[0.02] border border-white/5 relative">
            <Quote className="w-10 h-10 text-white/10 absolute top-6 left-6" />
            <p className="text-gray-300 mb-6 relative z-10 pl-8">
              "We evaluated several licensing solutions, but CodeVault's native compilation approach 
              and offline lease system were exactly what we needed for our enterprise clients."
            </p>
            <div className="flex items-center gap-4 pl-8">
              <div className="w-12 h-12 rounded-full bg-gradient-to-br from-green-500 to-teal-500 flex items-center justify-center text-white font-bold">
                ST
              </div>
              <div>
                <div className="font-medium text-white">Sarah Tech</div>
                <div className="text-sm text-gray-400">CTO, DataTools Inc</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Testimonials;
