import React from 'react';
import { motion } from 'framer-motion';
import { APP_URL } from '../../lib/config';

const GDPR: React.FC = () => {
  return (
    <div className="min-h-screen bg-background pt-20 pb-20">
      <div className="max-w-4xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="prose prose-invert prose-slate max-w-none"
        >
          <h1 className="text-4xl font-bold text-white mb-8">GDPR Compliance</h1>
          
          <p className="text-slate-400">Last updated: February 2026</p>

          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">1. Data Controller</h2>
          <p className="text-slate-300">
            CodeVault operates as the data controller for personal information collected through our platform. 
            For inquiries regarding data protection, contact us at contact@codevault.com.
          </p>

          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">2. Legal Basis for Processing</h2>
          <p className="text-slate-300">
            We process personal data based on the following legal grounds:
          </p>
          <ul className="text-slate-300 list-disc pl-6 space-y-2">
            <li><strong>Contract:</strong> Processing necessary to provide our services</li>
            <li><strong>Legitimate Interest:</strong> Fraud prevention and service improvement</li>
            <li><strong>Consent:</strong> Marketing communications (optional)</li>
            <li><strong>Legal Obligation:</strong> Tax and regulatory compliance</li>
          </ul>

          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">3. Your GDPR Rights</h2>
          <p className="text-slate-300">
            Under GDPR, you have the following rights:
          </p>
          <ul className="text-slate-300 list-disc pl-6 space-y-2">
            <li><strong>Right to Access:</strong> Request a copy of your personal data</li>
            <li><strong>Right to Rectification:</strong> Correct inaccurate or incomplete data</li>
            <li><strong>Right to Erasure:</strong> Request deletion of your personal data</li>
            <li><strong>Right to Restrict Processing:</strong> Limit how we use your data</li>
            <li><strong>Right to Data Portability:</strong> Receive data in a machine-readable format</li>
            <li><strong>Right to Object:</strong> Opt-out of certain data processing</li>
          </ul>

          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">4. Data Retention</h2>
          <p className="text-slate-300">
            We retain personal data only as long as necessary:
          </p>
          <ul className="text-slate-300 list-disc pl-6 space-y-2">
            <li>Account data: Until account deletion</li>
            <li>Build logs: 30 days</li>
            <li>License validation logs: 1 year</li>
            <li>Payment records: 7 years (legal requirement)</li>
          </ul>

          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">5. International Transfers</h2>
          <p className="text-slate-300">
            We primarily store data within the EU. When data is transferred outside the EEA, 
            we ensure appropriate safeguards are in place, including Standard Contractual Clauses.
          </p>

          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">6. Data Protection Officer</h2>
          <p className="text-slate-300">
            For GDPR-related inquiries, contact our data protection team:
            <br />
            Email: contact@codevault.com
          </p>

          <h2 className="text-2xl font-semibold text-white mt-8 mb-4">7. Complaints</h2>
          <p className="text-slate-300">
            If you believe we have not handled your data correctly, you have the right to lodge 
            a complaint with your local supervisory authority.
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

export default GDPR;