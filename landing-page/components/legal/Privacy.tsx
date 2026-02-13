import React from 'react';
import { motion } from 'framer-motion';
import { APP_URL } from '../../lib/config';

const Privacy: React.FC = () => {
  return (
    <div className="min-h-screen bg-background pt-20 pb-20">
      <div className="max-w-4xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="prose prose-invert prose-slate max-w-none"
        >
          <h1 className="text-4xl font-bold text-white mb-8">Privacy Policy</h1>
          
          <p className="text-slate-400">Last updated: February 2026</p>
          
          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">1. Information We Collect</h2>
          <p className="text-slate-300">
            CodeVault collects information necessary to provide our software licensing and protection services. This includes:
          </p>
          <ul className="text-slate-300 list-disc pl-6 space-y-2">
            <li>Account information (email, name)</li>
            <li>Project metadata and configuration</li>
            <li>License keys and usage data</li>
            <li>Hardware identifiers (HWID) for license validation</li>
            <li>Build logs and compilation artifacts</li>
          </ul>

          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">2. How We Use Your Information</h2>
          <p className="text-slate-300">
            We use collected information to:
          </p>
          <ul className="text-slate-300 list-disc pl-6 space-y-2">
            <li>Provide and maintain our services</li>
            <li>Process license validations and hardware binding</li>
            <li>Generate compilation reports and analytics</li>
            <li>Send service notifications and updates</li>
            <li>Prevent fraud and abuse</li>
          </ul>

          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">3. Data Storage & Security</h2>
          <p className="text-slate-300">
            Your data is stored securely using industry-standard encryption. We use PostgreSQL for database storage 
            and Cloudflare R2 for file storage. All data is encrypted in transit using TLS 1.3.
          </p>

          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">4. Third-Party Services</h2>
          <p className="text-slate-300">
            We use the following third-party services:
          </p>
          <ul className="text-slate-300 list-disc pl-6 space-y-2">
            <li>Polar.sh for payment processing</li>
            <li>GitHub Actions for cloud builds</li>
            <li>Cloudflare for CDN and security</li>
            <li>Upstash for rate limiting</li>
          </ul>

          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">5. Your Rights</h2>
          <p className="text-slate-300">
            You have the right to access, correct, or delete your personal data. Contact us at contact@codevault.com 
            for data-related requests.
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

export default Privacy;