import React from 'react';
import { APP_URL } from '../lib/config';

const Footer: React.FC = () => {

  return (
    <footer className="border-t border-white/5 bg-background pt-20 pb-10">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-10 mb-16">
          <div className="col-span-2 md:col-span-1">
            <h4 className="font-bold text-white mb-4 flex items-center gap-2">
              CodeVault
            </h4>
            <p className="text-sm text-gray-400">
              Protecting intellectual property for developers worldwide.
            </p>
          </div>
          
          <div>
            <h5 className="font-semibold text-white mb-4">Product</h5>
            <ul className="space-y-2 text-sm text-gray-400">
              <li><a href="#features" className="hover:text-white transition-colors">Features</a></li>
              <li><a href="#pricing" className="hover:text-white transition-colors">Pricing</a></li>
              <li><a href="#how-it-works" className="hover:text-white transition-colors">How It Works</a></li>
            </ul>
          </div>

          <div>
            <h5 className="font-semibold text-white mb-4">Get Started</h5>
            <ul className="space-y-2 text-sm text-gray-400">
              <li><a href={`${APP_URL}/signup`} className="hover:text-white transition-colors">Sign Up</a></li>
              <li><a href={`${APP_URL}/login`} className="hover:text-white transition-colors">Log In</a></li>
            </ul>
          </div>

          <div>
            <h5 className="font-semibold text-white mb-4">Legal</h5>
            <ul className="space-y-2 text-sm text-gray-400">
              <li><a href={`${APP_URL}/privacy`} className="hover:text-white transition-colors">Privacy Policy</a></li>
              <li><a href={`${APP_URL}/terms`} className="hover:text-white transition-colors">Terms of Service</a></li>
              <li><a href={`${APP_URL}/gdpr`} className="hover:text-white transition-colors">GDPR Compliance</a></li>
              <li><a href={`${APP_URL}/sla`} className="hover:text-white transition-colors">SLA / Uptime</a></li>
            </ul>
          </div>

          <div>
            <h5 className="font-semibold text-white mb-4">Social</h5>
<ul className="space-y-2 text-sm text-gray-400">
              <li><a href="https://github.com/ParthSalunkhe7052/code-vault" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors">GitHub</a></li>
            </ul>
          </div>
        </div>
        
        <div className="pt-8 border-t border-white/5 flex flex-col md:flex-row justify-between items-center gap-4 text-xs text-gray-500">
          <p>&copy; {new Date().getFullYear()} CodeVault Inc. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
