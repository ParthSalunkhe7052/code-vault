"use client";

import { motion } from "framer-motion";
import { Check, Shield } from "lucide-react";

const PricingCard = ({ tier, price, features, recommended = false }: any) => (
    <motion.div
        whileHover={{ y: -5 }}
        className={`relative p-8 rounded-2xl border ${recommended
                ? "bg-[#0a0a0a] border-[#D4AF37] shadow-[0_0_30px_rgba(212,175,55,0.1)]"
                : "bg-[#050505] border-white/10"
            }`}
    >
        {recommended && (
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 bg-[#D4AF37] text-black text-xs font-bold uppercase tracking-wide rounded-full">
                Most Popular
            </div>
        )}
        <h3 className="text-lg font-mono text-neutral-400 mb-2">{tier}</h3>
        <div className="flex items-baseline gap-1 mb-6">
            <span className="text-4xl font-bold text-white">${price}</span>
            <span className="text-neutral-500">/mo</span>
        </div>
        <ul className="space-y-4 mb-8">
            {features.map((feat: string, i: number) => (
                <li key={i} className="flex items-center gap-3 text-sm text-neutral-300">
                    <Check className="w-4 h-4 text-[#D4AF37]" />
                    {feat}
                </li>
            ))}
        </ul>
        <button
            className={`w-full py-3 rounded-lg font-semibold transition-all ${recommended
                    ? "bg-[#D4AF37] text-black hover:bg-[#b5952f]"
                    : "bg-white/5 text-white hover:bg-white/10"
                }`}
        >
            {recommended ? "Get Started" : "Choose Plan"}
        </button>
    </motion.div>
);

export default function Pricing() {
    const plans = [
        {
            tier: "Hobby",
            price: "0",
            features: ["1 Compiled App", "5 License Keys", "Basic Obfuscation", "Manual Dashboard"],
        },
        {
            tier: "Pro",
            price: "29",
            recommended: true,
            features: ["Unlimited Apps", "Stripe Integration", "HWID Locking", "Advanced PyArmor", "Priority Support"],
        },
        {
            tier: "Studio",
            price: "99",
            features: ["Source Code Access", "Custom Branding", "Dedicated Server", "Audit Logs", "SLA Support"],
        },
    ];

    return (
        <section className="py-24 bg-[#050505] border-t border-white/5">
            <div className="container mx-auto px-4 max-w-6xl">
                <div className="text-center mb-16">
                    <h2 className="text-3xl font-bold text-white mb-4">Simple, Transparent Pricing</h2>
                    <p className="text-neutral-400">Stop paying per-seat. Pay for the platform.</p>
                </div>
                <div className="grid md:grid-cols-3 gap-8">
                    {plans.map((plan, i) => (
                        <PricingCard key={i} {...plan} />
                    ))}
                </div>
            </div>
        </section>
    );
}
