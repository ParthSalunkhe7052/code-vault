import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

const CopyButton = ({ text, className = '', size = 14 }) => {
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(text);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (error) {
            console.error('Failed to copy:', error);
        }
    };

    return (
        <button
            onClick={handleCopy}
            className={`relative p-2 rounded-lg hover:bg-white/10 transition-all duration-200 ${className}`}
            title={copied ? 'Copied!' : 'Copy to clipboard'}
        >
            <span className={`transition-all duration-200 block ${copied ? 'scale-0' : 'scale-100'}`}>
                <Copy size={size} className="text-slate-400" />
            </span>
            <span className={`absolute inset-0 flex items-center justify-center 
                transition-all duration-200 ${copied ? 'scale-100' : 'scale-0'}`}>
                <Check size={size} className="text-emerald-400" />
            </span>
        </button>
    );
};

export default CopyButton;
