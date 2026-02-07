import React from 'react';
import { Quote, Shield, Clock, Server } from 'lucide-react';

const Testimonials: React.FC = () => {
  return (
    <section className="py-24 bg-surface border-y border-white/5">
      <div className="max-w-7xl mx-auto px-6">
        
        {/* Trust Badges */}
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold mb-4">Built for Developers</h2>
          <p className="text-gray-400">Security, reliability, and control without the guesswork</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-20">
          <div className="flex items-center gap-4 p-6 rounded-xl bg-white/[0.02] border border-white/5">
            <div className="w-12 h-12 rounded-full bg-green-500/10 flex items-center justify-center">
              <Shield className="w-6 h-6 text-green-400" />
            </div>
            <div>
              <div className="text-2xl font-bold text-white">Reliability-first</div>
              <div className="text-sm text-gray-400">Built for production workloads</div>
            </div>
          </div>

          <div className="flex items-center gap-4 p-6 rounded-xl bg-white/[0.02] border border-white/5">
            <div className="w-12 h-12 rounded-full bg-blue-500/10 flex items-center justify-center">
              <Server className="w-6 h-6 text-blue-400" />
            </div>
            <div>
              <div className="text-2xl font-bold text-white">Scale-ready</div>
              <div className="text-sm text-gray-400">From solo makers to teams</div>
            </div>
          </div>

          <div className="flex items-center gap-4 p-6 rounded-xl bg-white/[0.02] border border-white/5">
            <div className="w-12 h-12 rounded-full bg-purple-500/10 flex items-center justify-center">
              <Clock className="w-6 h-6 text-purple-400" />
            </div>
            <div>
              <div className="text-2xl font-bold text-white">Always-on</div>
              <div className="text-sm text-gray-400">License validation that keeps up</div>
            </div>
          </div>
        </div>

        {/* Testimonials */}
        <div className="rounded-2xl bg-white/[0.02] border border-white/5 p-8 text-center text-gray-400">
          <div className="flex items-center justify-center gap-3 mb-4 text-white/60">
            <Quote className="w-5 h-5" />
            <span className="text-sm uppercase tracking-wider">Customer Stories</span>
          </div>
          <p className="text-gray-300">
            We publish testimonials only with explicit customer permission.
          </p>
          <p className="text-sm text-gray-500 mt-2">
            Check back soon for verified quotes.
          </p>
        </div>
      </div>
    </section>
  );
};

export default Testimonials;
