"use client";

import { motion } from "framer-motion";
import { ShieldCheck, Box, CreditCard, Terminal, Zap } from "lucide-react";

const BentoCard = ({
    children,
    className = "",
    delay = 0
}: {
    children: React.ReactNode;
    className?: string;
    delay?: number
}) => (
    <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5, delay }}
        className={`relative bg-[#0a0a0a] border border-white/5 rounded-2xl overflow-hidden hover:border-[#D4AF37]/30 transition-colors group ${className}`}
    >
        <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
        {children}
    </motion.div>
);

export default function BentoGrid() {
    return (
        <section className="py-32 bg-[#050505] relative overflow-hidden">
            <div className="container mx-auto px-4 max-w-6xl">
                <div className="text-center mb-16 space-y-4">
                    <h2 className="text-3xl md:text-5xl font-bold text-white tracking-tight">
                        The <span className="text-[#D4AF37]">All-in-One</span> Platform
                    </h2>
                    <p className="text-neutral-400 max-w-2xl mx-auto">
                        Replace your fragmented stack. No more PyArmor scripts, hacked-together licenses, or manual Gumroad links.
                    </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 md:grid-rows-2 gap-6 h-auto md:h-[600px]">

                    {/* Card 1: Native Compilation (Large Top Left) */}
                    <BentoCard className="md:col-span-2 relative p-8 flex flex-col justify-between" delay={0.1}>
                        <div className="absolute top-0 right-0 h-full w-1/2 opacity-20 group-hover:opacity-40 transition-opacity mask-linear-gradient">
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img
                                src="/assets/terminal-cube.jpg"
                                alt="Native Compilation"
                                className="object-cover w-full h-full mix-blend-lighten grayscale hover:grayscale-0 transition-all duration-500"
                            />
                        </div>
                        <div className="relative z-10 max-w-sm">
                            <div className="w-12 h-12 rounded-lg bg-[#D4AF37]/10 flex items-center justify-center mb-6 text-[#D4AF37]">
                                <Zap className="w-6 h-6" />
                            </div>
                            <h3 className="text-2xl font-bold text-white mb-2">Native Compilation</h3>
                            <p className="text-neutral-400">
                                Powered by Nuitka. We don't just bundle Python; we compile it to C.
                                Enjoy <span className="text-white">300% faster startup times</span> and true native performance.
                            </p>
                        </div>
                    </BentoCard>

                    {/* Card 2: Protection (Tall Right) */}
                    <BentoCard className="md:row-span-2 relative p-0 flex flex-col overflow-hidden" delay={0.2}>
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                            src="/assets/shield-lock.jpg"
                            alt="Security"
                            className="absolute inset-0 w-full h-full object-cover opacity-40 group-hover:opacity-60 group-hover:scale-105 transition-all duration-700"
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-[#050505] via-[#050505]/80 to-transparent" />

                        <div className="relative z-10 p-8 mt-auto">
                            <div className="w-12 h-12 rounded-lg bg-white/5 flex items-center justify-center mb-6 text-white backdrop-blur-sm border border-white/10">
                                <ShieldCheck className="w-6 h-6" />
                            </div>
                            <h3 className="text-2xl font-bold text-white mb-2">Military-Grade Defense</h3>
                            <p className="text-neutral-400 text-sm">
                                Hardware-ID Locking (HWID), Anti-Debug traps, and VM detection. Your code runs ONLY where you say it runs.
                            </p>
                        </div>
                    </BentoCard>

                    {/* Card 3: Monetization (Bottom Left) */}
                    <BentoCard className="p-8 flex flex-row items-center gap-6" delay={0.3}>
                        <div className="flex-1">
                            <div className="w-12 h-12 rounded-lg bg-white/5 flex items-center justify-center mb-4 text-white">
                                <CreditCard className="w-6 h-6" />
                            </div>
                            <h3 className="text-xl font-bold text-white mb-2">Instant Monetization</h3>
                            <p className="text-neutral-400 text-sm">
                                Creation keys, subscriptions, and trials instantly via Stripe.
                            </p>
                        </div>
                        <div className="w-1/3 h-full relative rounded-lg overflow-hidden border border-white/10">
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img
                                src="/assets/revenue-graph.jpg"
                                alt="Revenue"
                                className="object-cover w-full h-full opacity-80"
                            />
                        </div>
                    </BentoCard>

                    {/* Card 4: CLI (Bottom Center) */}
                    <BentoCard className="p-8 flex flex-col justify-between group overflow-hidden" delay={0.4}>
                        <div className="absolute inset-0 bg-[url('/assets/noise.jpg')] opacity-10 mix-blend-overlay" />
                        <div className="relative z-10">
                            <div className="w-12 h-12 rounded-lg bg-white/5 flex items-center justify-center mb-4 text-white">
                                <Terminal className="w-6 h-6" />
                            </div>
                            <h3 className="text-xl font-bold text-white mb-2">CLI First</h3>

                            <div className="relative mt-2">
                                <div className="absolute -left-2 top-1/2 -translate-y-1/2 w-1 h-8 bg-[#D4AF37] rounded-r" />
                                <code className="block bg-black/50 p-3 rounded border border-white/10 text-xs text-green-500 font-mono pl-4">
                                    $ codevault build .
                                </code>
                            </div>
                        </div>
                    </BentoCard>

                </div>
            </div>
        </section>
    );
}
