import React from 'react';
import { Shield, Menu, X, ArrowRight } from 'lucide-react';
import { APP_URL } from '../lib/config';

const Navbar: React.FC = () => {
  const [isOpen, setIsOpen] = React.useState(false);
  const menuId = 'mobile-nav-menu';

  // Close mobile menu on Escape key
  React.useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsOpen(false);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  return (
    <nav aria-label="Main navigation" className="fixed top-0 left-0 right-0 z-50 border-b border-white/5 bg-[#0a0f1a]/60 backdrop-blur-xl transition-all duration-300">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-1.5 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg shadow-lg shadow-indigo-500/20">
            <Shield className="w-5 h-5 text-white" aria-hidden="true" />
          </div>
          <span className="font-bold text-lg tracking-tight text-white">CodeVault</span>
          
          {/* Operational Badge */}
          <div className="hidden sm:flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 ml-2">
             <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
             <span className="text-[10px] font-medium text-emerald-400">OPERATIONAL</span>
          </div>
        </div>

        {/* Desktop Menu */}
        <div className="hidden md:flex items-center gap-8">
          <a href="#features" className="text-sm font-medium text-slate-400 hover:text-white transition-colors">Features</a>
          <a href="#how-it-works" className="text-sm font-medium text-slate-400 hover:text-white transition-colors">How it works</a>
          <a href="#pricing" className="text-sm font-medium text-slate-400 hover:text-white transition-colors">Pricing</a>
          
          <div className="flex items-center gap-3 ml-2">
            <a href={`${APP_URL}/login`} className="text-sm font-medium text-white hover:text-indigo-300 transition-colors">
              Log in
            </a>
            <a href={`${APP_URL}/signup`} className="group flex items-center gap-2 text-sm font-bold bg-white text-black px-4 py-2 rounded-lg hover:bg-indigo-50 transition-all hover:scale-105 hover:shadow-lg hover:shadow-indigo-500/20">
              Get API Keys
              <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
            </a>
          </div>
        </div>

        {/* Mobile Menu Button */}
        <button
          className="md:hidden text-gray-400 p-2 hover:bg-white/5 rounded-lg transition-colors"
          onClick={() => setIsOpen(!isOpen)}
          aria-label={isOpen ? 'Close navigation menu' : 'Open navigation menu'}
          aria-expanded={isOpen}
          aria-controls={menuId}
        >
          {isOpen ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
        </button>
      </div>

      {/* Mobile Menu */}
      {isOpen && (
        <div
          id={menuId}
          role="navigation"
          aria-label="Mobile navigation"
          className="md:hidden absolute top-16 left-0 right-0 bg-[#0a0f1a] border-b border-white/10 p-6 flex flex-col gap-4 animate-fade-in shadow-2xl"
        >
          <a href="#features" className="text-gray-400 hover:text-white font-medium" onClick={() => setIsOpen(false)}>Features</a>
          <a href="#how-it-works" className="text-gray-400 hover:text-white font-medium" onClick={() => setIsOpen(false)}>How it works</a>
          <a href="#pricing" className="text-gray-400 hover:text-white font-medium" onClick={() => setIsOpen(false)}>Pricing</a>
          <hr className="border-white/10 my-2" />
          <a href={`${APP_URL}/login`} className="text-white font-medium">Log in</a>
          <a href={`${APP_URL}/signup`} className="bg-white text-black text-center py-3 rounded-lg font-bold">Get API Keys</a>
        </div>
      )}
    </nav>
  );
};

export default Navbar;