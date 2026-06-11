"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTournament } from "../context/TournamentContext";
import { getApiBaseUrl } from "../lib/config";
import { 
  Trophy, 
  User, 
  LogOut, 
  LayoutDashboard, 
  Swords, 
  Grid, 
  Activity, 
  Brain, 
  Loader2,
  Sparkles
} from "lucide-react";

export default function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const { pipelineStatus } = useTournament();
  
  // Auth state
  const [username, setUsername] = useState<string | null>(null);

  useEffect(() => {
    // Check local storage for auth details
    const storedUsername = localStorage.getItem("username");
    setUsername(storedUsername);

    // Listen for custom login event or storage updates
    const handleAuthChange = () => {
      setUsername(localStorage.getItem("username"));
    };

    window.addEventListener("storage", handleAuthChange);
    window.addEventListener("auth-change", handleAuthChange);
    
    return () => {
      window.removeEventListener("storage", handleAuthChange);
      window.removeEventListener("auth-change", handleAuthChange);
    };
  }, []);

  const handleLogout = async () => {
    const API_BASE = getApiBaseUrl();
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        }
      });
    } catch (err) {
      console.warn("Logout endpoint failed:", err);
    }
    
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    setUsername(null);
    
    // Dispatch auth change event
    window.dispatchEvent(new Event("auth-change"));
    router.push("/");
  };

  const navItems = [
    { name: "Home", href: "/", icon: LayoutDashboard },
    { name: "Predictor", href: "/predictions", icon: Swords },
    { name: "Bracket", href: "/bracket", icon: Grid },
    { name: "Injury Lab", href: "/injury-lab", icon: Activity },
    { name: "Explainability", href: "/explainability", icon: Brain },
    { name: "Fan League", href: "/competition", icon: Trophy },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-white/10 bg-[#030308]/60 backdrop-blur-md transition-all duration-300">
      <div className="mx-auto flex max-w-7xl h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
        
        {/* Logo and Brand */}
        <Link href="/" className="flex items-center gap-3 group">
          <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-cyan-500 shadow-lg shadow-violet-500/20 group-hover:scale-105 transition-transform duration-300 overflow-hidden p-1 bg-zinc-950/40">
            <img src="/images/logos/tournai.png" alt="TournAI" className="h-full w-full object-contain filter brightness-110" />
            <div className="absolute inset-0 rounded-xl bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
          </div>
          <div className="flex flex-col">
            <span className="text-lg font-bold tracking-wider text-white flex items-center gap-1.5 leading-none">
              TournAI <span className="text-xs px-1.5 py-0.5 rounded-full bg-cyan-500/15 text-cyan-400 font-mono">ATLAS</span>
            </span>
            <span className="text-[10px] text-gray-400 font-medium">World Cup 2026</span>
          </div>
        </Link>

        {/* Desktop Navigation Link Items */}
        <nav className="hidden md:flex items-center gap-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${
                  isActive 
                    ? "bg-white/5 text-cyan-400 shadow-sm border border-cyan-500/20" 
                    : "text-gray-300 hover:text-white hover:bg-white/5 border border-transparent"
                }`}
              >
                <Icon className={`h-4 w-4 ${isActive ? "text-cyan-400 animate-pulse-slow" : "text-gray-400"}`} />
                {item.name}
              </Link>
            );
          })}
        </nav>

        {/* Live Status and User Authentication */}
        <div className="flex items-center gap-4">
          
          {/* Pulse LIVE Connection Indicator */}
          <div className="flex items-center gap-2 rounded-full bg-white/5 border border-white/10 px-3 py-1.5">
            <span className="relative flex h-2 w-2">
              {pipelineStatus?.status === "running" ? (
                <>
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-violet-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-violet-500"></span>
                </>
              ) : (
                <>
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </>
              )}
            </span>
            <span className="text-[11px] font-mono text-gray-300 font-medium select-none uppercase">
              {pipelineStatus?.status === "running" ? "Updating" : "Live"}
            </span>
            {pipelineStatus?.status === "running" && (
              <Loader2 className="h-3 w-3 animate-spin text-violet-400" />
            )}
          </div>

          {/* User Auth Profile Dropdown */}
          {username ? (
            <div className="flex items-center gap-3">
              <div className="hidden sm:flex items-center gap-2 text-xs font-mono font-medium text-cyan-400 bg-cyan-950/20 border border-cyan-500/20 rounded-xl px-3 py-1.5">
                <User className="h-3.5 w-3.5" />
                {username}
              </div>
              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-rose-400 hover:text-white bg-rose-950/20 hover:bg-rose-600/20 border border-rose-500/20 hover:border-rose-500/50 transition-all duration-200 cursor-pointer"
                title="Logout"
              >
                <LogOut className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          ) : (
            <Link
              href="/auth"
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-violet-600 to-cyan-600 hover:from-violet-500 hover:to-cyan-500 shadow-md shadow-violet-500/10 hover:shadow-violet-500/20 transition-all duration-200 border border-white/10"
            >
              <Sparkles className="h-3.5 w-3.5" />
              Join League
            </Link>
          )}

        </div>

      </div>

      {/* Mobile Fixture Navigation Link Row */}
      <div className="flex md:hidden items-center justify-around border-t border-white/5 bg-[#030308]/40 h-11 px-2 overflow-x-auto whitespace-nowrap">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`text-xs font-semibold px-2.5 py-1.5 rounded-lg transition-colors ${
                isActive ? "text-cyan-400 bg-white/5" : "text-gray-400 hover:text-white"
              }`}
            >
              {item.name}
            </Link>
          );
        })}
      </div>
    </header>
  );
}
