import React from 'react';
import { motion } from 'framer-motion';
import { APP_URL } from '../../lib/config';

const SLA: React.FC = () => {
  return (
    <div className="min-h-screen bg-background pt-20 pb-20">
      <div className="max-w-4xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="prose prose-invert prose-slate max-w-none"
        >
          <h1 className="text-4xl font-bold text-white mb-8">Service Level Agreement</h1>
          
          <p className="text-slate-400">Last updated: February 2026</p>

          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">1. Service Availability</h2>
          <p className="text-slate-300">
            CodeVault commits to the following uptime guarantees:
          </p>
          <ul className="text-slate-300 list-disc pl-6 space-y-2">
            <li><strong>Free & Pro:</strong> 99.0% monthly uptime</li>
            <li><strong>Business:</strong> 99.5% monthly uptime</li>
            <li><strong>Enterprise:</strong> 99.9% monthly uptime</li>
          </ul>

          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">2. Exclusions</h2>
          <p className="text-slate-300">
            The following are excluded from uptime calculations:
          </p>
          <ul className="text-slate-300 list-disc pl-6 space-y-2">
            <li>Scheduled maintenance windows (with 24-hour notice)</li>
            <li>Force majeure events</li>
            <li>Third-party service failures (GitHub, Cloudflare)</li>
            <li>Client-side network issues</li>
            <li>DDoS attacks exceeding our mitigation capacity</li>
          </ul>

          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">3. Service Credits</h2>
          <p className="text-slate-300">
            If uptime falls below the guaranteed level, credits are applied as follows:
          </p>
          <ul className="text-slate-300 list-disc pl-6 space-y-2">
            <li>&lt; 99.9% but ≥ 99.0%: 5% credit</li>
            <li>&lt; 99.0% but ≥ 95.0%: 15% credit</li>
            <li>&lt; 95.0%: 50% credit</li>
          </ul>
          <p className="text-slate-300 mt-4">
            Credits are applied to the next billing cycle and do not exceed one month&apos;s fees.
          </p>

          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">4. Support Response Times</h2>
          <p className="text-slate-300">
            Target response times for support requests:
          </p>
          <ul className="text-slate-300 list-disc pl-6 space-y-2">
            <li><strong>Free:</strong> Community support only</li>
            <li><strong>Pro:</strong> 48 hours</li>
            <li><strong>Business:</strong> 24 hours</li>
            <li><strong>Enterprise:</strong> 4 hours (business hours)</li>
          </ul>

          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">5. Cloud Build SLAs</h2>
          <p className="text-slate-300">
            For cloud compilation services:
          </p>
          <ul className="text-slate-300 list-disc pl-6 space-y-2">
            <li>Build queue time: &lt; 5 minutes for standard builds</li>
            <li>Build completion notification: Real-time via WebSocket</li>
            <li>Artifact availability: 7 days after build completion</li>
            <li>Failed build retry: Automatic retry for infrastructure failures</li>
          </ul>

          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">6. License Validation SLAs</h2>
          <p className="text-slate-300">
            For license validation API:
          </p>
          <ul className="text-slate-300 list-disc pl-6 space-y-2">
            <li>API response time: &lt; 500ms (95th percentile)</li>
            <li>Validation endpoint availability: 99.99%</li>
            <li>Offline lease support: Available for Pro+ plans</li>
          </ul>

          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">7. Maintenance Windows</h2>
          <p className="text-slate-300">
            Scheduled maintenance occurs during low-traffic periods (UTC 02:00-06:00 on Sundays). 
            Emergency maintenance may be required with minimum notice.
          </p>

          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">8. Custom SLAs</h2>
          <p className="text-slate-300">
            Enterprise customers may negotiate custom SLAs with dedicated support channels, 
            faster response times, and enhanced uptime guarantees.
          </p>

          <div className="mt-12 pt-8 border-t border-white/10">
            <a href={APP_URL} className="text-indigo-400 hover:text-indigo-300">
              ← Back to Dashboard
            </a>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default SLA;