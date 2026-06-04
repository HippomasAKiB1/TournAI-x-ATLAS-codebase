import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "TournAI × ATLAS | World Cup 2026 Intelligence System",
  description: "Adaptive Tournament Learning and Analytics System (ATLAS). Explore predictions, Monte Carlo tournament simulations, player intelligence grades, injury what-if labs, and SHAP explainability summaries.",
  keywords: ["World Cup 2026", "TournAI", "ATLAS", "Sports Analytics", "Machine Learning Predictions", "Tournament Simulation", "Monte Carlo Simulator", "SHAP Explainability"],
  authors: [{ name: "Antigravity AI Engine" }],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased dark`}
    >
      <body className="min-h-full flex flex-col bg-[#030308] text-[#f4f4f7] selection:bg-cyan-500/30 selection:text-cyan-200">
        {children}
      </body>
    </html>
  );
}
