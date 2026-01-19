"use client";

import { useRef } from "react";
import { motion, useScroll, useTransform } from "framer-motion";
import { FileCode, Lock, Shield, Zap } from "lucide-react";

export default function ScrollWrapper() {
    const containerRef = useRef<HTMLDivElement>(null);
    const { scrollYProgress } = useScroll({
        target: containerRef,
        offset: ["start end", "end start"],
    });

    // Transform stages
    const rawCodeOpacity = useTransform(scrollYProgress, [0, 0.3], [1, 0]);
    const shieldScale = useTransform(scrollYProgress, [0.2, 0.5], [0.5, 1]);
    const shieldOpacity = useTransform(scrollYProgress, [0.2, 0.4], [0, 1]);

    const lockY = useTransform(scrollYProgress, [0.4, 0.6], [-50, 0]);
    const lockOpacity = useTransform(scrollYProgress, [0.4, 0.5], [0, 1]);

    const goldGlimmer = useTransform(scrollYProgress, [0.6, 0.8], ["#333", "#D4AF37"]);
    const finalScale = useTransform(scrollYProgress, [0.8, 1], [1, 1.2]);

    return (
        <section ref={containerRef} className="h-[200vh] relative bg-[#050505] flex items-center justify-center overflow-hidden">

            {/* Sticky Container */}
            <div className="sticky top-0 h-screen w-full flex flex-col items-center justify-center">
                <h2 className="text-3xl font-bold text-white mb-12 opacity-80">
                    The <span className="text-[#D4AF37]">Wrapping</span> Process
                </h2>

                <div className="relative w-64 h-64 flex items-center justify-center">

                    {/* Stage 1: Raw Code */}
                    <motion.div
                        style={{ opacity: rawCodeOpacity }}
                        className="absolute inset-0 flex items-center justify-center bg-neutral-900 rounded-xl border border-white/10"
                    >
                        <FileCode className="w-24 h-24 text-neutral-500" />
                        <div className="absolute font-mono text-xs text-green-500 bottom-4">script.py</div>
                    </motion.div>

                    {/* Stage 2: Armor/Shield */}
                    <motion.div
                        style={{ scale: shieldScale, opacity: shieldOpacity }}
                        className="absolute inset-0 flex items-center justify-center bg-neutral-800 rounded-xl border-2 border-neutral-600 z-10 shadow-2xl"
                    >
                        <Shield className="w-32 h-32 text-neutral-400" strokeWidth={1} />
                    </motion.div>

                    {/* Stage 3: Lock Injection */}
                    <motion.div
                        style={{ y: lockY, opacity: lockOpacity }}
                        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-20"
                    >
                        <div className="bg-[#050505] p-4 rounded-full border border-[#D4AF37]">
                            <Lock className="w-12 h-12 text-[#D4AF37]" />
                        </div>
                    </motion.div>

                    {/* Stage 4: Final Gold Transformation */}
                    <motion.div
                        style={{
                            borderColor: goldGlimmer,
                            scale: finalScale,
                            boxShadow: "0 0 50px rgba(212, 175, 55, 0.2)"
                        }}
                        className="absolute inset-0 rounded-xl border-2 z-30 pointer-events-none transition-colors duration-500"
                    />

                </div>

                {/* Status Text based on Scroll */}
                <div className="mt-12 font-mono text-sm space-y-2 text-center h-24">
                    {/* We can use opacity transforms for text lines too if needed, but keeping it simple for now */}
                    <motion.div style={{ opacity: rawCodeOpacity }} className="text-neutral-500">
                        Reading Source Code...
                    </motion.div>
                    <motion.div style={{ opacity: shieldOpacity }} className="text-blue-400">
                        Compiling to Native C...
                    </motion.div>
                    <motion.div style={{ opacity: lockOpacity }} className="text-[#D4AF37]">
                        Injecting HWID Protection...
                    </motion.div>
                </div>

            </div>
        </section>
    );
}
