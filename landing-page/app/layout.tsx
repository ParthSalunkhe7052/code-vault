import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Code Vault | Protect. Compile. Monetize.",
  description: "The all-in-one platform to turn Python scripts into secure, commercial software.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable} antialiased dark`}>
      <body
        className="bg-[#050505] text-white selection:bg-[#D4AF37] selection:text-black font-sans"
      >
        {children}
      </body>
    </html>
  );
}
