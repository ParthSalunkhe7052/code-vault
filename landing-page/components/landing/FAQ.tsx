"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown } from "lucide-react";

const faqs = [
    {
        q: "How does the compilation working?",
        a: "We use Nuitka to translate your Python code into C, then compile it into a machine-native binary. It's not just a wrapper – it's a true executable.",
    },
    {
        q: "Is this secure against decompilation?",
        a: "Much more than standard tools. Since it's compiled C code with additional obfuscation layers and HWID checks, reverse engineering becomes exponentially harder.",
    },
    {
        q: "Can I sell my software on Gumroad?",
        a: "Yes! Code Vault integrates with Stripe directly, but you can also generate license keys manually to sell on any platform you choose.",
    },
];

const FAQItem = ({ q, a }: { q: string; a: string }) => {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <div className="border-b border-white/5">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full py-6 flex items-center justify-between text-left hover:text-[#D4AF37] transition-colors"
            >
                <span className="text-lg text-white font-medium">{q}</span>
                <ChevronDown
                    className={`w-5 h-5 text-neutral-500 transition-transform ${isOpen ? "rotate-180" : ""
                        }`}
                />
            </button>
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="overflow-hidden"
                    >
                        <p className="pb-6 text-neutral-400 leading-relaxed">{a}</p>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default function FAQ() {
    return (
        <section className="py-24 bg-[#050505]">
            <div className="container mx-auto px-4 max-w-3xl">
                <h2 className="text-3xl font-bold text-white mb-12 text-center">Frequently Asked Questions</h2>
                <div className="space-y-2">
                    {faqs.map((faq, i) => (
                        <FAQItem key={i} {...faq} />
                    ))}
                </div>
            </div>
        </section>
    );
}
