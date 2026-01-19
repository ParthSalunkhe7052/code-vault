import Hero from "@/components/landing/Hero";
import BentoGrid from "@/components/landing/BentoGrid";
import ScrollWrapper from "@/components/landing/ScrollWrapper";
import Pricing from "@/components/landing/Pricing";
import FAQ from "@/components/landing/FAQ";

export default function Home() {
  return (
    <main className="min-h-screen bg-[#050505] selection:bg-[#D4AF37] selection:text-black">
      <Hero />
      <BentoGrid />
      <ScrollWrapper />
      <Pricing />
      <FAQ />

      {/* Footer Simple */}
      <footer className="py-8 border-t border-white/5 text-center text-neutral-600 text-sm">
        <p>© 2026 Code Vault Inc. All systems operational.</p>
      </footer>
    </main>
  );
}
