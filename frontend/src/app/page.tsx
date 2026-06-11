"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTournament } from "../context/TournamentContext";
import { resetDatabase } from "../lib/api";
import { getApiBaseUrl } from "../lib/config";
import { 
  Trophy, 
  Activity, 
  ChevronRight, 
  Calendar, 
  Swords, 
  Info, 
  Sparkles,
  Users,
  Search,
  Loader2,
  TrendingUp,
  X,
  RefreshCw
} from "lucide-react";
import PlayerImage from "../components/PlayerImage";

const FLAG_MAP: Record<string, string> = {
  "Algeria": "/images/country-logos/ALG.png",
  "Argentina": "/images/country-logos/ARG.png",
  "Australia": "/images/country-logos/AUS.png",
  "Austria": "/images/country-logos/AUT.png",
  "Belgium": "/images/country-logos/BEL.png",
  "Bosnia and Herzegovina": "/images/country-logos/BIH.png",
  "Brazil": "/images/country-logos/BRA.png",
  "Canada": "/images/country-logos/CAN.png",
  "Cape Verde": "/images/country-logos/CPV.png",
  "Colombia": "/images/country-logos/COL.png",
  "Croatia": "/images/country-logos/CRO.png",
  "Curaçao": "/images/country-logos/CUW.png",
  "Curacao": "/images/country-logos/CUW.png",
  "Czech Republic": "/images/country-logos/CZE.png",
  "DR Congo": "/images/country-logos/COD.png",
  "Ecuador": "/images/country-logos/ECU.png",
  "Egypt": "/images/country-logos/EGY.png",
  "England": "/images/country-logos/ENG.png",
  "France": "/images/country-logos/FRA.png",
  "Germany": "/images/country-logos/GER.png",
  "Ghana": "/images/country-logos/GHA.png",
  "Haiti": "/images/country-logos/HAI.png",
  "Iran": "/images/country-logos/IRN.png",
  "Iraq": "/images/country-logos/IRQ.png",
  "Ivory Coast": "/images/country-logos/CIV.png",
  "Japan": "/images/country-logos/JPN.png",
  "Jordan": "/images/country-logos/JOR.png",
  "Mexico": "/images/country-logos/MEX.png",
  "Morocco": "/images/country-logos/MAR.png",
  "Netherlands": "/images/country-logos/NED.png",
  "New Zealand": "/images/country-logos/NZL.png",
  "Norway": "/images/country-logos/NOR.png",
  "Panama": "/images/country-logos/PAN.png",
  "Paraguay": "/images/country-logos/PAR.png",
  "Portugal": "/images/country-logos/POR.png",
  "Qatar": "/images/country-logos/QAT.png",
  "Saudi Arabia": "/images/country-logos/KSA.png",
  "Scotland": "/images/country-logos/SCO.png",
  "Senegal": "/images/country-logos/SEN.png",
  "South Africa": "/images/country-logos/RSA.png",
  "South Africa ": "/images/country-logos/RSA.png",
  "South Korea": "/images/country-logos/KOR.png",
  "Spain": "/images/country-logos/ESP.png",
  "Sweden": "/images/country-logos/SWE.png",
  "Switzerland": "/images/country-logos/SUI.png",
  "Tunisia": "/images/country-logos/TUN.png",
  "Turkey": "/images/country-logos/TUR.png",
  "USA": "/images/country-logos/USA.png",
  "Uruguay": "/images/country-logos/URU.png",
  "Uzbekistan": "/images/country-logos/UZB.png"
};

interface LiveMatchData {
  id: number;
  home_team: string;
  away_team: string;
  home_score: number;
  away_score: number;
  minute: number;
  status: string;
  possession_home: number;
  possession_away: number;
  stage: string;
  home_win_prob: number;
  draw_prob: number;
  away_win_prob: number;
}

interface FixtureData {
  id: number;
  home_team: string;
  away_team: string;
  home_score: number | null;
  away_score: number | null;
  stage: string;
  status: string;
  date: string;
  kickoff_utc: string | null;
  home_win_prob: number;
  draw_prob: number;
  away_win_prob: number;
}

export default function HomePage() {
  const router = useRouter();
  const { 
    loading: contextLoading, 
    groupStandings, 
    latestShift, 
    predictions,
    refreshData
  } = useTournament();

  const [liveMatch, setLiveMatch] = useState<LiveMatchData | null>(null);
  const [fixtures, setFixtures] = useState<FixtureData[]>([]);
  const [featuredPlayers, setFeaturedPlayers] = useState<any[]>([]);
  const [activePlayerIndex, setActivePlayerIndex] = useState(0);
  
  // Group standings expansions states
  const [expandedGroup, setExpandedGroup] = useState<string | null>(null);

  // Team explorer states
  const [selectedExplorerTeam, setSelectedExplorerTeam] = useState<string | null>(null);
  const [explorerSquad, setExplorerSquad] = useState<any[]>([]);
  const [explorerStartingXI, setExplorerStartingXI] = useState<any[]>([]);
  const [explorerLoading, setExplorerLoading] = useState(false);

  const API_BASE = getApiBaseUrl();

  const handleResetSandbox = async () => {
    const confirmReset = window.confirm("Are you sure you want to reset the sandbox database back to pre-tournament baseline? This will clear all ingested match scores.");
    if (!confirmReset) return;
    
    try {
      const res = await resetDatabase();
      if (res) {
        // Refresh context (narrative shifts, simulations, group standings, bracket ELOs)
        await refreshData();
        // Re-fetch home page state
        const liveRes = await fetch(`${API_BASE}/live`);
        if (liveRes.ok) setLiveMatch(await liveRes.json());
        
        const fixturesRes = await fetch(`${API_BASE}/fixtures`);
        if (fixturesRes.ok) setFixtures(await fixturesRes.json());
      }
    } catch (e) {
      console.error("Failed to reset sandbox:", e);
    }
  };

  const TEAM_GROUP_MAP = React.useMemo(() => {
    const map: Record<string, string> = {};
    if (!groupStandings) return map;
    Object.entries(groupStandings).forEach(([groupName, teams]) => {
      if (Array.isArray(teams)) {
        teams.forEach(t => {
          map[t.Team] = groupName.replace("Group ", "");
        });
      }
    });
    return map;
  }, [groupStandings]);


  // Load Home widgets from API
  useEffect(() => {
    const fetchHomeData = async () => {
      try {
        const liveRes = await fetch(`${API_BASE}/live`);
        if (liveRes.ok) {
          const liveData = await liveRes.json();
          setLiveMatch(liveData);
        }

        const fixturesRes = await fetch(`${API_BASE}/fixtures`);
        if (fixturesRes.ok) {
          const fixturesData = await fixturesRes.json();
          setFixtures(fixturesData);
        }

        const featuredRes = await fetch(`${API_BASE}/players/featured`);
        if (featuredRes.ok) {
          const featuredData = await featuredRes.json();
          setFeaturedPlayers(featuredData);
        }
      } catch (err) {
        console.error("Error loading home page components:", err);
      }
    };
    
    fetchHomeData();
    const interval = setInterval(fetchHomeData, 15000); 
    return () => clearInterval(interval);
  }, []);

  // Cycle featured player profiles
  useEffect(() => {
    if (featuredPlayers.length <= 1) return;
    const playerTimer = setInterval(() => {
      setActivePlayerIndex((prev) => (prev + 1) % featuredPlayers.length);
    }, 8000);
    return () => clearInterval(playerTimer);
  }, [featuredPlayers]);

  // Load team explorer drawer data
  const handleOpenTeamExplorer = async (teamName: string) => {
    setSelectedExplorerTeam(teamName);
    setExplorerLoading(true);
    try {
      const res = await fetch(`${API_BASE}/squads/${encodeURIComponent(teamName)}`);
      if (res.ok) {
        const data = await res.json();
        setExplorerSquad(data.squad || []);
        setExplorerStartingXI(data.projected_xi || []);
      }
    } catch (err) {
      console.error("Failed to load explorer squad:", err);
    } finally {
      setExplorerLoading(false);
    }
  };

  // SVG Pitch Redesign
  const renderSoccerPitch = () => {
    const gks = explorerStartingXI.filter(p => p.position === "GK");
    const defs = explorerStartingXI.filter(p => p.position === "DEF");
    const mids = explorerStartingXI.filter(p => p.position === "MID");
    const fwds = explorerStartingXI.filter(p => p.position === "FWD");

    // Coordinates layout mapping (percentages of soccer field box width/height)
    const positionsConfig = [
      { player: gks[0], x: 50, y: 88, label: "GK" },
      { player: defs[0], x: 15, y: 70, label: "LB" },
      { player: defs[1], x: 38, y: 72, label: "LCB" },
      { player: defs[2], x: 62, y: 72, label: "RCB" },
      { player: defs[3], x: 85, y: 70, label: "RB" },
      { player: mids[0], x: 25, y: 48, label: "LM" },
      { player: mids[1], x: 50, y: 52, label: "CM" },
      { player: mids[2], x: 75, y: 48, label: "RM" },
      { player: fwds[0], x: 20, y: 22, label: "LW" },
      { player: fwds[1], x: 50, y: 18, label: "ST" },
      { player: fwds[2], x: 80, y: 22, label: "RW" },
    ];

    return (
      <div className="relative w-full h-[380px] bg-gradient-to-b from-[#0e301d] via-[#071f11] to-[#040f09] rounded-2xl border border-emerald-500/30 overflow-hidden shadow-[inset_0_4px_20px_rgba(0,0,0,0.6)] flex flex-col justify-end p-2 select-none">
        
        {/* Alternate grass stripes */}
        <div className="absolute inset-0 flex flex-col pointer-events-none opacity-25">
          {[...Array(6)].map((_, i) => (
            <div key={i} className={`flex-1 w-full ${i % 2 === 0 ? "bg-[#104025]" : "bg-transparent"}`} />
          ))}
        </div>

        {/* Soccer Pitch markings */}
        <div className="absolute inset-4 border border-white/10 pointer-events-none rounded">
          {/* Center Circle */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-24 h-24 rounded-full border border-white/10" />
          {/* Halfway line */}
          <div className="absolute top-1/2 left-0 w-full h-px bg-white/10" />
          {/* Penalty boxes */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-48 h-18 border-b border-x border-white/10" />
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-48 h-18 border-t border-x border-white/10" />
          {/* Penalty Spots */}
          <div className="absolute top-12 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full bg-white/30" />
          <div className="absolute bottom-12 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full bg-white/30" />
          {/* Goal boxes */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-24 h-6 border-b border-x border-white/5" />
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-24 h-6 border-t border-x border-white/5" />
        </div>

        {/* Dynamic Jerseys mapping */}
        {positionsConfig.map((pos, idx) => {
          if (!pos.player) return null;
          const initials = pos.player.player_name.split(" ").map((n: string) => n[0]).join("").substring(0, 2).toUpperCase();
          
          return (
            <div 
              key={idx}
              style={{ left: `${pos.x}%`, top: `${pos.y}%` }}
              className="absolute -translate-x-1/2 -translate-y-1/2 group cursor-pointer z-10"
            >
              {/* Node jersey */}
              <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-teal-400 border border-emerald-300/30 text-[10px] font-extrabold text-white shadow-lg shadow-emerald-950/50 group-hover:scale-115 group-hover:from-purple-500 group-hover:to-indigo-500 group-hover:border-purple-300/40 transition-all duration-300">
                <svg className="w-5 h-5 absolute opacity-25 text-white pointer-events-none" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M13 2v3h3v9H8V5h3V2L5 4v4h3v12h8V8h3V4l-6-2z"/>
                </svg>
                <span className="relative font-mono z-1">{initials}</span>
                
                {/* Role indicator badge */}
                <span className="absolute -bottom-2 px-1 bg-zinc-950 border border-zinc-800 text-[7px] text-cyan-400 rounded-md font-mono scale-90 tracking-tighter">
                  {pos.label}
                </span>
              </div>
              
              {/* Floating Tooltip */}
              <div className="absolute bottom-13 left-1/2 -translate-x-1/2 w-52 bg-zinc-950/95 border border-cyan-500/30 p-3 rounded-2xl text-left shadow-2xl pointer-events-none opacity-0 group-hover:opacity-100 transition-all duration-300 z-20 backdrop-blur-md translate-y-2 group-hover:translate-y-0">
                <div className="flex justify-between items-center border-b border-zinc-900 pb-1.5 mb-2.5">
                  <span className="text-[9px] font-mono text-cyan-400 font-extrabold uppercase tracking-wider">{pos.label}</span>
                  <span className="text-[8px] font-mono text-zinc-500 bg-zinc-900 px-1.5 py-0.5 rounded">Squad Player</span>
                </div>
                <div className="flex items-center gap-2 mb-2">
                  <PlayerImage playerName={pos.player.player_name} className="h-8 w-8 shrink-0 border border-cyan-500/20" fallbackSize={14} />
                  <span className="text-xs font-bold text-white block truncate leading-tight">{pos.player.player_name}</span>
                </div>
                <div className="flex justify-between items-center mt-2 pt-1.5 border-t border-zinc-900/50 text-[9px] text-zinc-400 font-mono">
                  <span>Age: {pos.player.age}</span>
                  <span className="text-glow-purple text-purple-400 font-extrabold">Impact: {pos.player.impact_score?.toFixed(1)}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  if (contextLoading || !groupStandings) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center py-20 bg-[#030308]">
        <Loader2 className="h-10 w-10 animate-spin text-cyan-400 mb-4" />
        <p className="text-sm text-zinc-400 font-medium">Booting TournAI World Cup Hub...</p>
      </div>
    );
  }

  const uniqueTeamsList = Object.values(groupStandings)
    .flatMap(group => group.map(row => row.Team))
    .sort();

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 space-y-8 pb-20">

      {/* 0. FIFA WORLD CUP 2026 HERO BANNER */}
      <section className="relative overflow-hidden rounded-3xl border border-amber-500/20 p-6 sm:p-10 text-center shadow-[0_0_80px_rgba(245,158,11,0.07)] stadium-glow">
        {/* Background wallpaper image with overlay to keep text readable */}
        <div 
          className="absolute inset-0 bg-cover bg-center bg-no-repeat opacity-35 pointer-events-none scale-105 transition-transform duration-700 hover:scale-100"
          style={{ backgroundImage: "url('/images/wallpaper/fifa_wallapaper.jpg')" }}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-[#0d0a00]/50 via-[#0c0c1a]/70 to-[#04040e]/95 pointer-events-none" />
        
        {/* Background stadium spotlight rings */}
        <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full bg-amber-500/5 blur-3xl pointer-events-none" />
        <div className="absolute -top-20 left-1/4 w-[300px] h-[300px] rounded-full bg-violet-500/5 blur-3xl pointer-events-none" />
        <div className="absolute -top-20 right-1/4 w-[300px] h-[300px] rounded-full bg-cyan-500/5 blur-3xl pointer-events-none" />
        <div className="absolute inset-0 cyber-grid opacity-5 pointer-events-none" />

        <div className="relative z-10 flex flex-col items-center gap-4">
          {/* Tournament chip */}
          <div className="flex items-center gap-2 px-4 py-1.5 rounded-full border border-amber-500/30 bg-amber-500/5 text-amber-400 text-[10px] font-mono font-extrabold uppercase tracking-widest select-none">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
            Official AI Intelligence System — FIFA World Cup 2026™
          </div>

          {/* Trophy + Title */}
          <div className="flex flex-col items-center gap-2">
            <img 
              src="/images/logos/WC26_Logo.png" 
              alt="FIFA World Cup 2026 Logo" 
              className="h-24 sm:h-28 object-contain select-none animate-float filter drop-shadow-[0_0_20px_rgba(255,255,255,0.15)]"
            />
            <h1 className="text-3xl sm:text-5xl font-black tracking-tight text-shimmer leading-none">
              World Cup 2026
            </h1>
            <p className="text-xs sm:text-sm text-zinc-400 font-medium max-w-lg mt-1.5 leading-relaxed">
              ATLAS-powered predictions · Monte Carlo simulations · Live ELO tracking
            </p>
          </div>

          {/* Host Nations Row */}
          <div className="flex flex-wrap items-center justify-center gap-3 mt-2">
            <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest select-none mr-1">Hosted by</span>
            {[
              { flag: "🇺🇸", name: "USA", city: "New York / LA" },
              { flag: "🇨🇦", name: "Canada", city: "Toronto / Vancouver" },
              { flag: "🇲🇽", name: "Mexico", city: "Mexico City" },
            ].map((host) => (
              <div key={host.name} className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-zinc-800/80 bg-zinc-950/60 hover:border-amber-500/30 transition duration-200 select-none">
                {FLAG_MAP[host.name] ? (
                  <img src={FLAG_MAP[host.name]} alt={host.name} className="h-5 w-7 object-contain rounded-sm shrink-0" />
                ) : (
                  <span className="text-xl select-none">🏳️</span>
                )}
                <div className="text-left">
                  <span className="text-xs font-extrabold text-zinc-200 block leading-none">{host.name}</span>
                  <span className="text-[9px] font-mono text-zinc-500 block">{host.city}</span>
                </div>
              </div>
            ))}
          </div>

          {/* Stats pill row */}
          <div className="flex flex-wrap items-center justify-center gap-4 mt-1 text-[10px] font-mono text-zinc-500 select-none">
            <span className="flex items-center gap-1"><span className="text-amber-400 font-bold">48</span> Teams</span>
            <span className="w-px h-3 bg-zinc-700" />
            <span className="flex items-center gap-1"><span className="text-cyan-400 font-bold">104</span> Matches</span>
            <span className="w-px h-3 bg-zinc-700" />
            <span className="flex items-center gap-1"><span className="text-violet-400 font-bold">16</span> Host Cities</span>
            <span className="w-px h-3 bg-zinc-700" />
            <span className="flex items-center gap-1"><span className="text-emerald-400 font-bold">Jun–Jul</span> 2026</span>
          </div>
        </div>
      </section>

      {/* 1. HERO WIDGET: Match Right Now */}
      {liveMatch && (
        <section className="relative overflow-hidden rounded-3xl border border-cyan-500/15 bg-gradient-to-br from-indigo-950/40 via-[#090915] to-[#040914] p-6 sm:p-8 shadow-[0_0_30px_rgba(139,92,246,0.08)]">
          <div className="absolute inset-0 cyber-grid opacity-10 pointer-events-none" />
          
          <div className="relative flex flex-col md:flex-row items-center justify-between gap-6 z-10">
            
            <div className="flex flex-col items-center md:items-start text-center md:text-left gap-2">
              <div className="flex flex-wrap items-center gap-2 justify-center md:justify-start">
                <div className="flex items-center gap-2 px-3 py-1 bg-rose-500/10 border border-rose-500/30 text-rose-400 text-[10px] uppercase font-mono font-extrabold rounded-full select-none shadow-[0_0_10px_rgba(244,63,94,0.1)]">
                  <span className="flex h-2 w-2 relative">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
                  </span>
                  Live Match
                </div>
                {liveMatch.id === 9999 && (
                  <span className="flex items-center gap-1 px-2.5 py-1 bg-amber-500/10 border border-amber-500/30 text-amber-400 text-[9px] uppercase font-mono font-extrabold rounded-full select-none shadow-[0_0_10px_rgba(245,158,11,0.1)]">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
                    Sandbox Preview
                  </span>
                )}
              </div>
              <span className="text-[10px] font-mono text-cyan-400/80 tracking-widest uppercase mt-1 select-none">{liveMatch.stage}</span>
              <span className="text-zinc-500 font-mono text-xs">{liveMatch.minute}' Played</span>
            </div>

            {/* Scoreboard display */}
            <div className="flex items-center justify-center gap-3 sm:gap-6 md:gap-10 flex-1 w-full min-w-0">
              <div className="flex flex-col items-center w-20 sm:w-28 group shrink-0">
                <div className="relative flex h-12 w-12 sm:h-16 sm:w-16 items-center justify-center rounded-full bg-zinc-950/60 border border-zinc-800 shadow-inner group-hover:scale-105 group-hover:border-cyan-500/40 transition duration-300 overflow-hidden">
                  {FLAG_MAP[liveMatch.home_team] ? (
                    <img src={FLAG_MAP[liveMatch.home_team]} alt={liveMatch.home_team} className="h-8 w-10 sm:h-10 sm:w-12 object-contain filter drop-shadow-md" />
                  ) : (
                    <span className="text-2xl sm:text-4xl select-none">🏳️</span>
                  )}
                </div>
                <span className="text-[10px] sm:text-xs font-extrabold text-zinc-300 text-center truncate w-full mt-2.5 tracking-wide uppercase">{liveMatch.home_team}</span>
              </div>
              
              <div className="text-3xl sm:text-4xl md:text-5xl font-black font-mono text-white flex items-center gap-2 sm:gap-4 text-glow-purple shrink-0">
                <span>{liveMatch.home_score}</span>
                <span className="text-cyan-500 font-black animate-pulse">:</span>
                <span>{liveMatch.away_score}</span>
              </div>
              
              <div className="flex flex-col items-center w-20 sm:w-28 group shrink-0">
                <div className="relative flex h-12 w-12 sm:h-16 sm:w-16 items-center justify-center rounded-full bg-zinc-950/60 border border-zinc-800 shadow-inner group-hover:scale-105 group-hover:border-cyan-500/40 transition duration-300 overflow-hidden">
                  {FLAG_MAP[liveMatch.away_team] ? (
                    <img src={FLAG_MAP[liveMatch.away_team]} alt={liveMatch.away_team} className="h-8 w-10 sm:h-10 sm:w-12 object-contain filter drop-shadow-md" />
                  ) : (
                    <span className="text-2xl sm:text-4xl select-none">🏳️</span>
                  )}
                </div>
                <span className="text-[10px] sm:text-xs font-extrabold text-zinc-300 text-center truncate w-full mt-2.5 tracking-wide uppercase">{liveMatch.away_team}</span>
              </div>
            </div>

            {/* Possession swaying bar */}
            <div className="flex flex-col items-center md:items-end w-full md:w-64 gap-2">
              <div className="flex justify-between w-full text-[10px] font-mono text-zinc-400">
                <span>POSSESSION ({liveMatch.possession_home}%)</span>
                <span>({liveMatch.possession_away}%)</span>
              </div>
              <div className="w-full h-2 rounded-full overflow-hidden bg-zinc-900 flex shadow-inner">
                <div style={{ width: `${liveMatch.possession_home}%` }} className="bg-gradient-to-r from-purple-500 to-indigo-500 transition-all duration-1000" />
                <div style={{ width: `${liveMatch.possession_away}%` }} className="bg-gradient-to-r from-cyan-500 to-emerald-500 transition-all duration-1000" />
              </div>
              <button 
                onClick={() => router.push("/predictions")}
                className="mt-3.5 w-full flex items-center justify-center gap-1.5 px-4 py-2 bg-gradient-to-r from-cyan-500/10 to-indigo-500/10 hover:from-cyan-500/15 hover:to-indigo-500/15 border border-cyan-500/20 hover:border-cyan-500/45 text-cyan-400 font-extrabold text-xs rounded-xl cursor-pointer transition-all duration-300 shadow-sm"
              >
                Match Centre <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>

          </div>

          {/* Simulated Match Stats Sub-Grid */}
          <div className="w-full max-w-xl grid grid-cols-3 gap-3 mx-auto mt-6 pt-5 border-t border-zinc-800/80 text-[10px] font-mono text-zinc-400 text-center select-none">
            <div className="bg-[#0b0c16]/50 border border-zinc-800/60 p-2.5 rounded-xl hover:border-cyan-500/20 transition duration-300">
              <div className="font-extrabold text-white text-xs mb-0.5">{liveMatch.id === 9999 ? "12 (5)" : "15 (8)"}</div>
              <div className="text-[9px] text-zinc-500">Shots (On Target)</div>
            </div>
            <div className="bg-[#0b0c16]/50 border border-zinc-800/60 p-2.5 rounded-xl hover:border-cyan-500/20 transition duration-300">
              <div className="font-extrabold text-white text-xs mb-0.5">{liveMatch.id === 9999 ? "88%" : "91%"}</div>
              <div className="text-[9px] text-zinc-500">Pass Accuracy</div>
            </div>
            <div className="bg-[#0b0c16]/50 border border-zinc-800/60 p-2.5 rounded-xl hover:border-cyan-500/20 transition duration-300">
              <div className="font-extrabold text-white text-xs mb-0.5">{liveMatch.id === 9999 ? "4" : "6"}</div>
              <div className="text-[9px] text-zinc-500">Corners</div>
            </div>
          </div>
        </section>
      )}

      {/* 2. LATEST TOURNAMENT PROBABILITY SHIFT */}
      {latestShift && (
        <section className="p-4 rounded-2xl bg-gradient-to-r from-violet-950/20 to-zinc-950/50 border border-violet-500/20 shadow-md flex flex-col sm:flex-row items-start gap-4 relative overflow-hidden group">
          <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-violet-500 to-cyan-500" />
          <div className="flex items-start gap-3 flex-1">
            <TrendingUp className="h-5 w-5 text-violet-400 shrink-0 mt-0.5 animate-pulse" />
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono text-violet-400 font-bold uppercase tracking-wider">Latest Simulation Shift</span>
                {fixtures.some(f => f.status === "completed") && (
                  <span className="px-1.5 py-0.2 bg-rose-500/10 border border-rose-500/35 text-rose-400 text-[8px] uppercase font-mono font-bold rounded">
                    Sandbox Active
                  </span>
                )}
              </div>
              <p className="text-xs sm:text-sm text-zinc-300 font-medium leading-relaxed mt-1.5 pr-4">
                {fixtures.some(f => f.status === "completed") 
                  ? latestShift.shift_narrative 
                  : "No match results have been completed in the database yet. Operating on baseline simulations. Ingest finished match scores to track real-time probability shifts!"
                }
              </p>
              
              {fixtures.some(f => f.status === "completed") && (
                <button
                  onClick={handleResetSandbox}
                  className="mt-3.5 flex items-center gap-1.5 px-3 py-1.5 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 hover:border-rose-500/40 text-rose-400 font-extrabold text-[10px] font-mono rounded-xl cursor-pointer select-none transition-all duration-200"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  Reset Sandbox Data
                </button>
              )}
            </div>
          </div>
          <Link 
            href="/predictions"
            className="self-end sm:self-center shrink-0 flex items-center gap-0.5 text-xs text-violet-400 font-bold hover:text-violet-300 font-mono transition mt-2 sm:mt-0"
          >
            Explore Predictions <ChevronRight className="h-4 w-4" />
          </Link>
        </section>
      )}


      {/* 3. FIXTURE STRIP */}
      <section className="space-y-3">
        <div className="flex justify-between items-center px-1">
          <h3 className="text-sm font-bold uppercase tracking-wider text-zinc-400 flex items-center gap-1.5 select-none">
            <Calendar className="h-4.5 w-4.5 text-zinc-400" /> Fixtures & Scheduled Matches
          </h3>
          <span className="text-[10px] font-mono text-zinc-500 bg-zinc-900 border border-zinc-800/80 px-2.5 py-1 rounded-full uppercase select-none">
            WC 2026 Grid
          </span>
        </div>

        <div className="w-full overflow-x-auto pb-4 scrollbar-thin scrollbar-thumb-zinc-800">
          <div className="flex gap-4 p-1 min-w-max">
            {fixtures.slice(0, 12).map((match) => {
              const isCompleted = match.status === "completed";
              return (
                <div 
                  key={match.id}
                  onClick={() => router.push("/predictions")}
                  className="w-56 glass-card p-4 rounded-xl flex flex-col justify-between shrink-0 shadow border border-zinc-800/80 bg-[#090912]/40 hover:border-cyan-500/30 hover:shadow-cyan-500/5 cursor-pointer select-none transition-all duration-200"
                >
                  <div className="flex justify-between text-[9px] font-mono text-zinc-500 mb-2.5">
                    <span>Match {match.id}</span>
                    {isCompleted ? (
                      <span className="text-emerald-400 font-bold tracking-wider uppercase">Finished</span>
                    ) : (
                      <span className="text-zinc-500 font-semibold">{match.date}</span>
                    )}
                  </div>
                  
                  <div className="space-y-1.5 my-2">
                    <div className="flex justify-between items-center text-xs font-semibold text-zinc-200">
                      <span className="flex items-center gap-1.5 truncate max-w-[130px]">
                        {FLAG_MAP[match.home_team] ? (
                          <img src={FLAG_MAP[match.home_team]} alt={match.home_team} className="h-4.5 w-6 object-contain rounded-sm shrink-0" />
                        ) : (
                          <span className="text-sm">🏳️</span>
                        )}
                        <span className="truncate">{match.home_team}</span>
                      </span>
                      {isCompleted && <span className="font-mono text-white font-bold">{match.home_score}</span>}
                    </div>
                    <div className="flex justify-between items-center text-xs font-semibold text-zinc-200">
                      <span className="flex items-center gap-1.5 truncate max-w-[130px]">
                        {FLAG_MAP[match.away_team] ? (
                          <img src={FLAG_MAP[match.away_team]} alt={match.away_team} className="h-4.5 w-6 object-contain rounded-sm shrink-0" />
                        ) : (
                          <span className="text-sm">🏳️</span>
                        )}
                        <span className="truncate">{match.away_team}</span>
                      </span>
                      {isCompleted && <span className="font-mono text-white font-bold">{match.away_score}</span>}
                    </div>
                  </div>

                  {!isCompleted && (
                    <div className="border-t border-zinc-800/60 mt-2.5 pt-2 flex justify-between text-[9px] font-mono text-cyan-400/80">
                      <span>Adv. {match.home_team.substring(0,3).toUpperCase()}: {(match.home_win_prob * 100).toFixed(0)}%</span>
                      <span>{match.away_team.substring(0,3).toUpperCase()}: {(match.away_win_prob * 100).toFixed(0)}%</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* 4. MAIN COLUMN GRID: Standings & Featured Player */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Compact Group Standings List */}
        <div className="lg:col-span-2 glass-card p-6 rounded-2xl flex flex-col justify-between border-white/5 bg-[#090910]/40">
          <div>
            <h3 className="text-lg font-bold text-white flex items-center gap-2 select-none">
              <Trophy className="h-5 w-5 text-amber-400" /> Group Standings (Top 2)
            </h3>
            <p className="text-xs text-zinc-400 mt-1 mb-6 select-none">Top 2 advancing spots shown. Tap any group to view full standings.</p>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.keys(groupStandings).sort().map((groupName) => {
                const teams = groupStandings[groupName] || [];
                const topTwo = teams.slice(0, 2);
                const isExpanded = expandedGroup === groupName;
                
                return (
                  <div 
                    key={groupName}
                    className="p-4 rounded-xl border border-zinc-850/80 bg-zinc-950/45 hover:border-cyan-500/20 transition-all duration-200"
                  >
                    <div className="flex justify-between items-center border-b border-zinc-800/60 pb-2 mb-2">
                      <span className="text-xs font-bold text-white font-mono">{groupName}</span>
                      <button 
                        onClick={() => setExpandedGroup(isExpanded ? null : groupName)}
                        className="text-[10px] font-mono font-bold text-cyan-400 hover:text-cyan-300 cursor-pointer"
                      >
                        {isExpanded ? "Close" : "Expand"}
                      </button>
                    </div>

                    {!isExpanded ? (
                      <div className="space-y-1.5">
                        {topTwo.map((t) => (
                          <div key={t.Team} className="flex justify-between items-center text-xs text-zinc-300">
                            <span className="flex items-center gap-1.5 font-medium truncate max-w-[170px]">
                              {FLAG_MAP[t.Team] ? (
                                <img src={FLAG_MAP[t.Team]} alt={t.Team} className="h-4.5 w-6 object-contain rounded-sm shrink-0" />
                              ) : (
                                <span className="text-sm select-none">🏳️</span>
                              )}
                              <span className="truncate">{t.Team}</span>
                            </span>
                            <span className="font-mono font-bold text-zinc-400 bg-zinc-900 px-2 py-0.5 rounded">{t.Pts} Pts</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="space-y-2.5">
                        {teams.map((t) => (
                          <div key={t.Team} className="flex justify-between items-center text-xs text-zinc-300 border-b border-zinc-900/50 pb-1.5 last:border-0 last:pb-0">
                            <span className="flex items-center gap-1.5 font-bold text-white truncate max-w-[150px]">
                              <span className="text-[10px] text-zinc-500 font-mono w-4">{t.Position}</span>
                              {FLAG_MAP[t.Team] ? (
                                <img src={FLAG_MAP[t.Team]} alt={t.Team} className="h-4.5 w-6 object-contain rounded-sm shrink-0" />
                              ) : (
                                <span className="text-sm select-none">🏳️</span>
                              )}
                              <span className="truncate">{t.Team}</span>
                            </span>
                            <div className="flex gap-2 text-[10px] font-mono font-medium text-zinc-400">
                              <span>GD: {t.GD > 0 ? `+${t.GD}` : t.GD}</span>
                              <span className="text-zinc-200">{t.Pts} Pts</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Featured Player Card Carousel */}
        <div className="glass-card p-6 rounded-2xl relative overflow-hidden flex flex-col justify-between border-white/5 bg-[#090910]/40">
          <div>
            <span className="text-[10px] font-mono text-purple-400 font-bold uppercase tracking-wider">Featured Performer</span>
            
            {featuredPlayers.length > 0 ? (
              (() => {
                const player = featuredPlayers[activePlayerIndex];
                return (
                  <div className="mt-6 flex flex-col items-center text-center">
                    <PlayerImage playerName={player.player_name} className="h-20 w-20 mb-4 shadow-lg shadow-purple-500/25 border-2 border-purple-500/40" fallbackSize={36} />
                    
                    <h4 className="text-xl font-extrabold text-white leading-none tracking-tight">{player.player_name}</h4>
                    <span className="text-xs text-purple-400 font-mono mt-2 flex items-center gap-2">
                      {FLAG_MAP[player.team] ? (
                        <img src={FLAG_MAP[player.team]} alt={player.team} className="h-4.5 w-6 object-contain rounded-sm inline-block align-middle" />
                      ) : (
                        <span>🏳️</span>
                      )}
                      <span>{player.team} Star</span>
                    </span>

                    {/* Circular Impact grade display */}
                    <div className="mt-6 p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 w-full text-left space-y-2">
                      <div className="flex justify-between items-center text-xs text-zinc-400 py-1.5 border-b border-zinc-900/60">
                        <span>ATLAS Impact Grade</span>
                        <span className="font-mono text-purple-400 font-extrabold">{player.impact_score?.toFixed(1)} / 100</span>
                      </div>
                      <div className="flex justify-between items-center text-xs text-zinc-400 py-1.5 border-b border-zinc-900/60">
                        <span>Expected Goals / 90</span>
                        <span className="font-mono text-white font-bold">{player.xg_p90?.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between items-center text-xs text-zinc-400 py-1.5">
                        <span>Key passes / 90</span>
                        <span className="font-mono text-white font-bold">{player.key_passes_p90?.toFixed(2)}</span>
                      </div>
                    </div>
                  </div>
                );
              })()
            ) : (
              <div className="flex items-center justify-center h-48">
                <Loader2 className="h-6 w-6 animate-spin text-purple-400" />
              </div>
            )}
          </div>
          
          {/* Cycle Indicators */}
          <div className="flex justify-center gap-2 mt-6 pt-4 border-t border-zinc-900">
            {featuredPlayers.map((_, idx) => (
              <button 
                key={idx}
                onClick={() => setActivePlayerIndex(idx)}
                className={`w-1.5 h-1.5 rounded-full cursor-pointer transition-all ${
                  idx === activePlayerIndex ? "bg-purple-400 w-3" : "bg-zinc-800"
                }`}
              />
            ))}
          </div>

        </div>

      </section>

      {/* 5. TEAM EXPLORER FLAGS STRIP */}
      <section className="space-y-3">
        <div className="flex items-center gap-1.5 px-1">
          <Users className="h-4.5 w-4.5 text-zinc-400" />
          <h3 className="text-sm font-bold uppercase tracking-wider text-zinc-400 select-none">
            Team Explorer Squads & Start XIs
          </h3>
        </div>

        <div className="w-full overflow-x-auto pb-4 scrollbar-thin scrollbar-thumb-zinc-800">
          <div className="flex gap-3 p-1 min-w-max">
            {uniqueTeamsList.map((teamName) => (
              <button
                key={teamName}
                onClick={() => handleOpenTeamExplorer(teamName)}
                className="flex items-center gap-2.5 px-4 py-2.5 rounded-xl border border-zinc-850 bg-[#0a0a14]/60 hover:bg-cyan-500/5 hover:border-cyan-500/40 hover:shadow-[0_0_15px_rgba(6,182,212,0.1)] cursor-pointer select-none transition-all duration-300 group"
              >
                {FLAG_MAP[teamName] ? (
                  <img src={FLAG_MAP[teamName]} alt={teamName} className="h-5 w-6 object-contain rounded-sm group-hover:scale-110 transition duration-300 shrink-0" />
                ) : (
                  <span className="text-xl">🏳️</span>
                )}
                <div className="text-left">
                  <span className="text-xs font-bold text-zinc-300 block">{teamName}</span>
                  <span className="text-[8px] font-mono text-zinc-500 block">Group {TEAM_GROUP_MAP[teamName] || "-"}</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* 6. TEAM EXPLORER SQUAD DRAWER MODAL OVERLAY */}
      {selectedExplorerTeam && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#030308]/85 backdrop-blur-sm p-4 animate-fade-in">
          <div className="relative w-full max-w-4xl max-h-[90vh] sm:max-h-[85vh] overflow-y-auto glass-card rounded-3xl border border-white/10 bg-[#07070d] p-4 sm:p-6 shadow-2xl flex flex-col justify-between">
            
            <button 
              onClick={() => { setSelectedExplorerTeam(null); setExplorerSquad([]); setExplorerStartingXI([]); }}
              className="absolute top-4 right-4 p-2 rounded-xl text-zinc-400 hover:text-white bg-white/5 border border-white/5 hover:border-white/10 transition cursor-pointer"
            >
              <X className="h-4 w-4" />
            </button>

            {explorerLoading ? (
              <div className="flex flex-col items-center justify-center py-20 min-h-[300px]">
                <Loader2 className="h-8 w-8 animate-spin text-cyan-400 mb-2" />
                <p className="text-xs text-zinc-400 font-mono">Assembling projected rosters...</p>
              </div>
            ) : (
              <div className="space-y-6">
                
                {/* Header */}
                <div className="flex items-center gap-3 pb-4 border-b border-zinc-900">
                  {FLAG_MAP[selectedExplorerTeam] ? (
                    <img src={FLAG_MAP[selectedExplorerTeam]} alt={selectedExplorerTeam} className="h-10 w-12 object-contain rounded-md" />
                  ) : (
                    <span className="text-4xl select-none">🏳️</span>
                  )}
                  <div>
                    <h3 className="text-2xl font-extrabold text-white leading-none tracking-tight">{selectedExplorerTeam} Squad Explorer</h3>
                    <span className="text-xs text-cyan-400 font-mono mt-1 block">ATLAS Projected Roster Profile</span>
                  </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  
                  {/* Squad List */}
                  <div className="space-y-3">
                    <span className="text-[10px] font-mono text-zinc-400 font-bold uppercase tracking-wider block">Full Squad Roster</span>
                    <div className="max-h-[360px] overflow-y-auto border border-zinc-800/80 rounded-2xl divide-y divide-zinc-900 bg-zinc-950/20">
                      {explorerSquad.map((player) => (
                        <div key={player.player_name} className="flex justify-between items-center p-3 text-xs hover:bg-zinc-900/10 transition gap-3">
                          <div className="flex items-center gap-2.5">
                            <PlayerImage playerName={player.player_name} className="h-8 w-8 shrink-0" fallbackSize={14} />
                            <div>
                              <span className="font-semibold text-white block">{player.player_name}</span>
                              <span className="text-[10px] font-mono text-zinc-500 uppercase">{player.position} • {player.age} Years Old</span>
                            </div>
                          </div>
                          <div className="text-right">
                            <span className="font-mono font-bold text-glow-purple text-purple-400 block">{player.impact_score?.toFixed(1)}</span>
                            <span className="text-[9px] font-mono text-zinc-600 block">MV: {player.market_value_m}M</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Projected Starting XI Interactive Pitch */}
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-[10px] font-mono text-cyan-400 font-bold uppercase tracking-wider">Projected Starting XI (4-3-3 Pitch)</span>
                      <span className="px-2 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 font-mono text-[9px] uppercase font-bold animate-pulse">ATLAS Pick</span>
                    </div>

                    {renderSoccerPitch()}
                  </div>

                </div>

              </div>
            )}
          </div>
        </div>
      )}

    </div>
  );
}
