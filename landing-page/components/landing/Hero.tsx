"use client";

import { motion } from "framer-motion";
import { ShinyButton } from "@/components/ui/shiny-button";
import { TextReveal } from "@/components/ui/text-reveal";
import { ArrowRight, ShieldCheck, Terminal } from "lucide-react";

export default function Hero() {
    return (
        <section className="relative min-h-screen flex items-center justify-center overflow-hidden bg-[#050505]">
            {/* Background Gradients */}
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[500px] bg-[#D4AF37] opacity-[0.03] blur-[120px] rounded-full pointer-events-none" />
            <div className="absolute inset-0 bg-[url('/assets/noise.jpg')] opacity-[0.02] mix-blend-overlay pointer-events-none" />

            <div className="container mx-auto px-4 grid lg:grid-cols-2 gap-12 items-center relative z-10">

                {/* Text Content */}
                <div className="text-left space-y-6">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5 }}
                        className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/10 bg-white/5 text-xs text-[#D4AF37] font-mono mb-2"
                    >
                        <span className="w-2 h-2 rounded-full bg-[#D4AF37] animate-pulse" />
                        V1.0 NOW AVAILABLE
                    </motion.div>

                    <div className="space-y-2">
                        <TextReveal
                            text="The Standard for"
                            className="text-5xl md:text-7xl font-bold tracking-tighter text-white leading-[1.1]"
                            delay={0}
                        />
                        <TextReveal
                            text="Python Licensing."
                            className="text-5xl md:text-7xl font-bold tracking-tighter text-white/50 leading-[1.1]"
                            delay={0.2}
                        />
                    </div>

                    <motion.p
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5, delay: 0.2 }}
                        className="text-lg md:text-xl text-neutral-400 max-w-lg leading-relaxed"
                    >
                        Turn your Python scripts into secure, monetized commercial software in one command. Native compilation, HWID locking, and instant licensing.
                    </motion.p>

                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5, delay: 0.3 }}
                        className="flex flex-col sm:flex-row gap-4 pt-4"
                    >
                        <ShinyButton onClick={() => console.log("Monetize")}>
                            Start Monetizing
                            <ArrowRight className="w-4 h-4" />
                        </ShinyButton>

                        <button className="px-8 py-3 rounded border border-white/10 text-neutral-400 hover:text-white hover:border-white/30 transition-colors flex items-center justify-center gap-2 cursor-pointer">
                            <Terminal className="w-4 h-4" />
                            View Documentation
                        </button>
                    </motion.div>

                    <div className="pt-8 flex items-center gap-6 text-neutral-500 text-sm">
                        <div className="flex items-center gap-2">
                            <ShieldCheck className="w-4 h-4 text-[#D4AF37]" />
                            <span>Bank-Grade Security</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-4 h-4 rounded-full border border-neutral-600 flex items-center justify-center text-[10px]">C</div>
                            <span>Native Compilation</span>
                        </div>
                    </div>
                </div>

                {/* Visual Content */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.95, rotateX: 10, rotateY: -10 }}
                    animate={{ opacity: 1, scale: 1, rotateX: 0, rotateY: 0 }}
                    transition={{ duration: 1.2, ease: "easeOut" }}
                    className="relative w-full flex items-center justify-center perspective-1000"
                >
                    {/* Main Card */}
                    <div className="relative w-full max-w-xl aspect-[4/3] bg-[#0a0a0a] rounded-xl border border-white/10 border-glow shadow-2xl p-2 transform rotate-y-12 rotate-x-6 hover:rotate-0 transition-transform duration-700 ease-out preserve-3d group">

                        {/* Image Container */}
                        <div className="relative w-full h-full rounded-lg overflow-hidden bg-black/50">
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img
                                src="/assets/hero-ui.png"
                                alt="CodeVault Dashboard"
                                className="object-cover w-full h-full opacity-90 group-hover:opacity-100 transition-opacity"
                            />

                            {/* Overlay Reflection */}
                            <div className="absolute inset-0 bg-gradient-to-tr from-white/5 to-transparent pointer-events-none" />
                        </div>

                        {/* Glowing Border FX */}
                        <div className="absolute inset-0 rounded-xl border-2 border-[#D4AF37]/10 pointer-events-none group-hover:border-[#D4AF37]/30 transition-colors" />
                    </div>

                    {/* Background Elements */}
                    <div className="absolute -z-10 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[120%] h-[120%] bg-radial-gradient from-[#D4AF37]/10 to-transparent blur-3xl opacity-50" />
                </motion.div>

            </div>
        </section>
    );
}
