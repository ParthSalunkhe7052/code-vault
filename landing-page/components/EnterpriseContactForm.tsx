import React, { useState } from 'react';
import { Send, CheckCircle } from 'lucide-react';

export const EnterpriseContactForm: React.FC = () => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    company: '',
    message: ''
  });
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    
    // For now, just open email client - can be upgraded to API call later
    const subject = `Enterprise Inquiry from ${formData.company}`;
    const body = `Name: ${formData.name}\nEmail: ${formData.email}\nCompany: ${formData.company}\n\nMessage:\n${formData.message}`;
    window.location.href = `mailto:parth.ajit7052@gmail.com?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    
    setSubmitted(true);
    setLoading(false);
  };

  if (submitted) {
    return (
      <div className="text-center p-8 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl">
        <CheckCircle size={48} className="text-emerald-400 mx-auto mb-4" />
        <h3 className="text-xl font-bold text-white mb-2">Thank You!</h3>
        <p className="text-slate-300">We'll be in touch within 24 hours.</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 max-w-md mx-auto">
      <input
        type="text"
        placeholder="Your Name"
        required
        value={formData.name}
        onChange={(e) => setFormData({...formData, name: e.target.value})}
        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
      />
      <input
        type="email"
        placeholder="Work Email"
        required
        value={formData.email}
        onChange={(e) => setFormData({...formData, email: e.target.value})}
        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
      />
      <input
        type="text"
        placeholder="Company Name"
        required
        value={formData.company}
        onChange={(e) => setFormData({...formData, company: e.target.value})}
        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
      />
      <textarea
        placeholder="Tell us about your needs..."
        rows={4}
        value={formData.message}
        onChange={(e) => setFormData({...formData, message: e.target.value})}
        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors resize-none"
      />
      <button
        type="submit"
        disabled={loading}
        className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800 text-white font-bold rounded-lg transition-colors flex items-center justify-center gap-2"
      >
        {loading ? (
          <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
        ) : (
          <>
            <Send size={18} />
            Request Enterprise Demo
          </>
        )}
      </button>
    </form>
  );
};
