import React from 'react';
import { Shield, Menu, X } from 'lucide-react';

const Navbar: React.FC = () => {
  const [isOpen, setIsOpen] = React.useState(false);
  const APP_URL = import.meta.env.VITE_APP_URL || "https://app.codevault.parth7.me";

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-white/5 bg-[#0B0C10]/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <span className="font-semibold text-lg tracking-tight text-white">CodeVault</span>
        </div>

        {/* Desktop Menu */}
        <div className="hidden md:flex items-center gap-8">
          <a href={`${APP_URL}/store`} className="text-sm font-medium text-cyan-400 hover:text-cyan-300 transition-colors flex items-center gap-1">
            Store
          </a>
          <a href="#features" className="text-sm text-gray-400 hover:text-white transition-colors">Features</a>
          <a href="#how-it-works" className="text-sm text-gray-400 hover:text-white transition-colors">How it works</a>
          <a href="#pricing" className="text-sm text-gray-400 hover:text-white transition-colors">Pricing</a>
          <div className="flex items-center gap-4 ml-4">
            <a href={`${APP_URL}/login`} className="text-sm font-medium text-white hover:text-gray-200">Log in</a>
            <a href={`${APP_URL}/signup`} className="text-sm font-medium bg-white text-black px-4 py-2 rounded-full hover:bg-gray-200 transition-colors">
              Sign up
            </a>
          </div>
        </div>

        {/* Mobile Menu Button */}
        <button className="md:hidden text-gray-400" onClick={() => setIsOpen(!isOpen)}>
          {isOpen ? <X /> : <Menu />}
        </button>
      </div>

      {/* Mobile Menu */}
      {isOpen && (
        <div className="md:hidden absolute top-16 left-0 right-0 bg-[#0B0C10] border-b border-white/10 p-6 flex flex-col gap-4">
          <a href="#features" className="text-gray-400 hover:text-white">Features</a>
          <a href="#how-it-works" className="text-gray-400 hover:text-white">How it works</a>
          <a href="#pricing" className="text-gray-400 hover:text-white">Pricing</a>
          <hr className="border-white/10" />
          <a href={`${APP_URL}/login`} className="text-white">Log in</a>
          <a href={`${APP_URL}/signup`} className="bg-white text-black text-center py-2 rounded-full">Sign up</a>
        </div>
      )}
    </nav>
  );
};

export default Navbar;