import React from 'react';
import { motion } from 'framer-motion';
import { APP_URL } from '../../lib/config';

const Terms: React.FC = () => {
  return (
    <div className="min-h-screen bg-background pt-20 pb-20">
      <div className="max-w-4xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="prose prose-invert prose-slate max-w-none"
        >
          <h1 className="text-4xl font-bold text-white mb-8">Terms of Service</h1>
          
          <p className="text-slate-400">Last updated: February 2026</p>

          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">1. Acceptance of Terms</h2>
          <p className="text-slate-300">
            By accessing or using CodeVault services, you agree to be bound by these Terms of Service. 
            If you do not agree to these terms, please do not use our services.
          </p>

          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">2. Description of Service</h2>
          <p className="text-slate-300">
            CodeVault provides software licensing, protection, and compilation services. We offer tools 
            for license management, hardware binding, and native binary compilation for Python and Node.js applications.
          </p>

          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">3. Account Registration</h2>
          <p className="text-slate-300">
            To use our services, you must create an account. You are responsible for maintaining the 
            confidentiality of your account credentials and for all activities under your account.
          </p>

          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">4. Subscription Plans</h2>
          <p className="text-slate-300">
            CodeVault offers Free, Pro, Business, and Enterprise plans. Features and limits vary by plan:
          </p>
          <ul className="text-slate-300 list-disc pl-6 space-y-2">
            <li>Free: 1 project, 50 licenses, local builds only</li>
            <li>Pro: Unlimited projects, 500 licenses, 25 cloud builds/month</li>
            <li>Business: 5,000 licenses, 100 cloud builds/month, team features</li>
            <li>Enterprise: Custom limits and dedicated support</li>
          </ul>

          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">5. Acceptable Use</h2>
          <p className="text-slate-300">
            You agree not to use CodeVault to:
          </p>
          <ul className="text-slate-300 list-disc pl-6 space-y-2">
            <li>Violate any applicable laws or regulations</li>
            <li>Infringe on intellectual property rights</li>
            <li>Distribute malware or malicious software</li>
            <li>Attempt to reverse engineer our protection systems</li>
            <li>Engage in fraudulent or deceptive practices</li>
          </ul>

          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">6. Intellectual Property</h2>
          <p className="text-slate-300">
            You retain ownership of your code and compiled binaries. CodeVault retains ownership of 
            our platform, protection technology, and related intellectual property.
          </p>

          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">7. Limitation of Liability</h2>
          <p className="text-slate-300">
            CodeVault is provided &quot;as is&quot; without warranties of any kind. We are not liable for any 
            indirect, incidental, or consequential damages arising from your use of our services.
          </p>

          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">8. Termination</h2>
          <p className="text-slate-300">
            We reserve the right to terminate or suspend your account for violations of these terms. 
            You may cancel your subscription at any time.
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

export default Terms;