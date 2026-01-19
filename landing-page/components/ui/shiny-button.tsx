"use client";

import { motion } from "framer-motion";

interface ShinyButtonProps {
    children: React.ReactNode;
    onClick?: () => void;
    className?: string;
}

export const ShinyButton = ({ children, onClick, className = "" }: ShinyButtonProps) => {
    return (
        <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className={`relative px-8 py-3 bg-[#D4AF37] text-black font-bold uppercase tracking-wider rounded text-sm md:text-base overflow-hidden group ${className}`}
            onClick={onClick}
        >
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent translate-x-[-150%] group-hover:translate-x-[150%] transition-transform duration-700 ease-in-out skew-x-[-20deg]" />
            <span className="relative z-10 flex items-center justify-center gap-2">
                {children}
            </span>
        </motion.button>
    );
};
