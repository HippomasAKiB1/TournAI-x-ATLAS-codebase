"use client";

import React from "react";
import { Globe, Mail, Shield } from "lucide-react";

export default function Footer() {
  return (
    <footer className="w-full bg-[#05050c]/80 backdrop-blur-md border-t border-white/5 py-8 mt-auto select-none">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          
          {/* Credit Intro */}
          <div className="flex flex-col items-center md:items-start text-center md:text-left gap-1">
            <span className="text-[10px] font-mono text-cyan-400 font-extrabold uppercase tracking-widest flex items-center gap-1">
              <Shield className="h-3 w-3 text-cyan-400" /> System Architect & Model Engineering
            </span>
            <p className="text-xs text-zinc-400 font-medium max-w-md mt-1 leading-relaxed">
              Experimented, trained ELO/ATLAS ML models, and developed the predictive analytics pipeline by{" "}
              <span className="text-white font-semibold">Akib Hasan</span>.
            </p>
            <span className="text-[10px] text-zinc-600 font-mono mt-1">
              © {new Date().getFullYear()} TournAI × ATLAS. All rights reserved.
            </span>
          </div>

          {/* Socials & Contacts Grid */}
          <div className="flex flex-wrap items-center justify-center gap-4">
            
            {/* Website Link */}
            <a
              href="https://akibhasan.me"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-zinc-800/80 bg-zinc-950/45 hover:border-cyan-500/40 hover:bg-cyan-500/5 text-zinc-300 hover:text-white text-xs font-semibold font-mono tracking-tight transition duration-200"
            >
              <Globe className="h-3.5 w-3.5 text-cyan-400" /> akibhasan.me
            </a>

            {/* Email Link */}
            <a
              href="mailto:mail@akibhasan.me"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-zinc-800/80 bg-zinc-950/45 hover:border-cyan-500/40 hover:bg-cyan-500/5 text-zinc-300 hover:text-white text-xs font-semibold font-mono tracking-tight transition duration-200"
            >
              <Mail className="h-3.5 w-3.5 text-purple-400" /> mail@akibhasan.me
            </a>

            {/* LinkedIn */}
            <a
              href="https://www.linkedin.com/in/akib-hasan-pyil/"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center p-2 rounded-lg border border-zinc-800/80 bg-zinc-950/45 hover:border-blue-500/40 hover:bg-blue-500/5 text-zinc-400 hover:text-[#0077b5] transition duration-200"
              title="LinkedIn Profile"
            >
              <svg className="h-4 w-4 fill-current" viewBox="0 0 24 24">
                <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.779-1.75-1.75s.784-1.75 1.75-1.75 1.75.779 1.75 1.75-.784 1.75-1.75 1.75zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/>
              </svg>
            </a>

            {/* Facebook */}
            <a
              href="https://www.facebook.com/HippomasAKiB"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center p-2 rounded-lg border border-zinc-800/80 bg-zinc-950/45 hover:border-blue-600/40 hover:bg-blue-600/5 text-zinc-400 hover:text-[#1877f2] transition duration-200"
              title="Facebook Profile"
            >
              <svg className="h-4 w-4 fill-current" viewBox="0 0 24 24">
                <path d="M9 8h-3v4h3v12h5v-12h3.642l.358-4h-4v-1.667c0-.955.192-1.333 1.115-1.333h2.885v-5h-3.808c-3.596 0-5.192 1.583-5.192 4.615v3.385z"/>
              </svg>
            </a>

          </div>

        </div>
      </div>
    </footer>
  );
}
