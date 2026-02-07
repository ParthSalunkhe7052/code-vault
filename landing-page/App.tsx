import React from 'react';
import Navbar from './components/Navbar';
import Hero from './components/Hero';
import Features from './components/Features';
import HowItWorks from './components/HowItWorks';
import Testimonials from './components/Testimonials';
import Pricing from './components/Pricing';
import Footer from './components/Footer';
import { APP_URL } from './lib/config';

const App: React.FC = () => {
  return (
    <div className="bg-background min-h-screen text-white selection:bg-indigo-500/30">
      <Navbar />
      <main>
        <Hero />
        <Features />
        <HowItWorks />
        <Testimonials />
        <Pricing />
        
        {/* Simple CTA Section before footer */}
        <section className="py-24 border-t border-white/5 relative overflow-hidden">
           <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-blue-600/10 rounded-[100%] blur-[80px] pointer-events-none" />
           
           <div className="relative z-10 max-w-4xl mx-auto px-6 text-center">
             <h2 className="text-4xl font-bold mb-6">Ready to ship confidently?</h2>
              <p className="text-gray-400 mb-10 text-lg">
                Join developers who trust CodeVault to protect their revenue streams.
              </p>
             <a href={`${APP_URL}/signup`} className="bg-white text-black px-8 py-3 rounded-full font-medium hover:bg-gray-200 transition-all hover:scale-105 inline-block">
               Start Building Free
             </a>
           </div>
        </section>
      </main>
      <Footer />
    </div>
  );
};

export default App;