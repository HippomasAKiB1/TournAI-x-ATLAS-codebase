"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTournament } from "../context/TournamentContext";
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
  X
} from "lucide-react";

const FLAG_MAP: Record<string, string> = {
  "Morocco": "🇲🇦", "Portugal": "🇵🇹", "Argentina": "🇦🇷", "Brazil": "🇧🇷", "Spain": "🇪🇸", 
  "France": "🇫🇷", "Germany": "🇩🇪", "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Netherlands": "🇳🇱", "Belgium": "🇧🇪",
  "Uruguay": "🇺🇾", "Croatia": "🇭🇷", "Italy": "🇮🇹", "USA": "🇺🇸", "Mexico": "🇲🇽", 
  "Canada": "🇨🇦", "Senegal": "🇸🇳", "Egypt": "🇪🇬", "Nigeria": "🇳🇬", "Cameroon": "🇨🇲", 
  "Ghana": "🇬🇭", "Ivory Coast": "🇨🇮", "Algeria": "🇩🇿", "Tunisia": "🇹🇳", "South Africa": "🇿🇦",
  "Japan": "🇯🇵", "South Korea": "🇰🇷", "Australia": "🇦🇺", "Saudi Arabia": "🇸🇦", "Iran": "🇮🇷",
  "Colombia": "🇨🇴", "Ecuador": "🇪🇨", "Chile": "🇨🇱", "Peru": "🇵🇪", "Venezuela": "🇻🇪",
  "Paraguay": "🇵🇾", "Bolivia": "🇧🇴", "Jamaica": "🇯🇲", "Costa Rica": "🇨🇷", "Panama": "🇵🇦",
  "Honduras": "🇭🇳", "Switzerland": "🇨🇭", "Austria": "🇦🇹", "Denmark": "🇩🇰", "Sweden": "🇸🇪",
  "Norway": "🇳🇴", "Poland": "🇵🇱", "Ukraine": "🇺🇦", "Turkey": "🇹🇷", "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
  "Wales": "🏴󠁧󠁢󠁷󠁬󠁳󠁿", "Czech Republic": "🇨🇿", "Hungary": "🇭🇺", "Slovakia": "🇸🇰", "Romania": "🇷🇴",
  "Georgia": "🇬🇪", "Albania": "🇦🇱", "South Africa ": "🇿🇦", "DR Congo": "🇨🇩"
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
    predictions 
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

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

  // Load Home widgets from API
  useEffect(() => {
    const fetchHomeData = async () => {
      try {
        // 1. Fetch live match
        const liveRes = await fetch(`${API_BASE}/live`);
        if (liveRes.ok) {
          const liveData = await liveRes.json();
          setLiveMatch(liveData);
        }

        // 2. Fetch fixtures list
        const fixturesRes = await fetch(`${API_BASE}/fixtures`);
        if (fixturesRes.ok) {
          const fixturesData = await fixturesRes.json();
          setFixtures(fixturesData);
        }

        // 3. Fetch featured players
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
    const interval = setInterval(fetchHomeData, 10000); // Fast live score update interval
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
      
      {/* 1. HERO WIDGET: Match Right Now */}
      {liveMatch && (
        <section className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-indigo-950/40 via-zinc-950/60 to-cyan-950/40 p-6 sm:p-8 shadow-2xl">
          {/* Cyber grid background */}
          <div className="absolute inset-0 cyber-grid opacity-15 pointer-events-none" />
          
          <div className="relative flex flex-col md:flex-row items-center justify-between gap-6">
            
            {/* Live Indicator Header */}
            <div className="flex flex-col items-center md:items-start text-center md:text-left gap-1">
              <div className="flex items-center gap-2 px-3 py-1 bg-rose-500/15 border border-rose-500/30 text-rose-400 text-[10px] uppercase font-mono font-extrabold rounded-full select-none animate-pulse">
                <span className="w-1.5 h-1.5 rounded-full bg-rose-500" /> Live Match
              </div>
              <span className="text-[10px] font-mono text-zinc-400 tracking-wider uppercase mt-1.5">{liveMatch.stage}</span>
              <span className="text-zinc-500 font-mono text-xs">{liveMatch.minute}' Played</span>
            </div>

            {/* Scoreboard display */}
            <div className="flex items-center justify-center gap-6 sm:gap-8 flex-1">
              <div className="flex flex-col items-center w-28">
                <span className="text-4xl sm:text-5xl select-none mb-2">{FLAG_MAP[liveMatch.home_team] || "🏳️"}</span>
                <span className="text-sm font-bold text-white text-center truncate w-full">{liveMatch.home_team}</span>
              </div>
              <div className="text-3xl sm:text-4xl font-extrabold font-mono text-white flex items-center gap-3">
                <span>{liveMatch.home_score}</span>
                <span className="text-zinc-600">:</span>
                <span>{liveMatch.away_score}</span>
              </div>
              <div className="flex flex-col items-center w-28">
                <span className="text-4xl sm:text-5xl select-none mb-2">{FLAG_MAP[liveMatch.away_team] || "🏳️"}</span>
                <span className="text-sm font-bold text-white text-center truncate w-full">{liveMatch.away_team}</span>
              </div>
            </div>

            {/* Possession swaying bar */}
            <div className="flex flex-col items-center md:items-end w-full md:w-64 gap-2">
              <div className="flex justify-between w-full text-[10px] font-mono text-zinc-400">
                <span>POSSESSION ({liveMatch.possession_home}%)</span>
                <span>({liveMatch.possession_away}%)</span>
              </div>
              <div className="w-full h-2 rounded-full overflow-hidden bg-zinc-800 flex shadow">
                <div style={{ width: `${liveMatch.possession_home}%` }} className="bg-gradient-to-r from-purple-500 to-indigo-500 transition-all duration-1000" />
                <div style={{ width: `${liveMatch.possession_away}%` }} className="bg-gradient-to-r from-cyan-500 to-emerald-500 transition-all duration-1000" />
              </div>
              <button 
                onClick={() => router.push("/predictions")}
                className="mt-3 w-full flex items-center justify-center gap-1 px-4 py-2 bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-500/20 text-cyan-400 font-bold text-xs rounded-xl cursor-pointer transition-all duration-200"
              >
                Match Centre <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>

          </div>
        </section>
      )}

      {/* 2. LATEST TOURNAMENT PROBABILITY SHIFT */}
      {latestShift && (
        <section className="p-4 rounded-2xl bg-gradient-to-r from-violet-950/20 to-zinc-950 border border-violet-500/20 shadow flex items-start gap-3 relative overflow-hidden group">
          <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-violet-500 to-cyan-500" />
          <TrendingUp className="h-5 w-5 text-violet-400 shrink-0 mt-0.5 animate-pulse" />
          <div className="flex-1">
            <span className="text-[10px] font-mono text-violet-400 font-bold uppercase tracking-wider">Latest Simulation Shift</span>
            <p className="text-xs sm:text-sm text-zinc-300 font-medium leading-relaxed leading-normal mt-1 pr-16">{latestShift.shift_narrative}</p>
          </div>
          <Link 
            href="/predictions"
            className="absolute right-4 bottom-4 shrink-0 flex items-center gap-0.5 text-xs text-violet-400 font-bold hover:text-violet-300 font-mono"
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
            Today's fixtures
          </span>
        </div>

        <div className="w-full overflow-x-auto pb-4 scrollbar-thin scrollbar-thumb-zinc-800">
          <div className="flex gap-4 p-1 min-w-max">
            {fixtures.slice(0, 8).map((match) => {
              const isCompleted = match.status === "completed";
              return (
                <div 
                  key={match.id}
                  onClick={() => router.push("/predictions")}
                  className="w-56 glass-card p-4 rounded-xl flex flex-col justify-between shrink-0 shadow border border-zinc-800/80 bg-zinc-950/40 hover:border-cyan-500/20 hover:bg-zinc-900/10 cursor-pointer select-none transition-all duration-200"
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
                        <span>{FLAG_MAP[match.home_team] || "🏳️"}</span>
                        <span className="truncate">{match.home_team}</span>
                      </span>
                      {isCompleted && <span className="font-mono text-white font-bold">{match.home_score}</span>}
                    </div>
                    <div className="flex justify-between items-center text-xs font-semibold text-zinc-200">
                      <span className="flex items-center gap-1.5 truncate max-w-[130px]">
                        <span>{FLAG_MAP[match.away_team] || "🏳️"}</span>
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
        <div className="lg:col-span-2 glass-card p-6 rounded-2xl flex flex-col justify-between">
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
                    className="p-4 rounded-xl border border-zinc-800/80 bg-zinc-950/30 hover:border-cyan-500/20 transition-all duration-200"
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
                              <span className="text-sm select-none">{FLAG_MAP[t.Team] || "🏳️"}</span>
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
                              <span className="text-sm select-none">{FLAG_MAP[t.Team] || "🏳️"}</span>
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
        <div className="glass-card p-6 rounded-2xl relative overflow-hidden flex flex-col justify-between">
          <div>
            <span className="text-[10px] font-mono text-purple-400 font-bold uppercase tracking-wider">Featured Tournament Performer</span>
            
            {featuredPlayers.length > 0 ? (
              (() => {
                const player = featuredPlayers[activePlayerIndex];
                return (
                  <div className="mt-6 flex flex-col items-center text-center">
                    <div className="relative flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-purple-600 to-indigo-500 text-3xl select-none mb-4 shadow shadow-purple-500/20">
                      ⚽
                    </div>
                    
                    <h4 className="text-xl font-extrabold text-white leading-none tracking-tight">{player.player_name}</h4>
                    <span className="text-xs text-purple-400 font-mono mt-2 flex items-center gap-1">
                      {FLAG_MAP[player.team] || "🏳️"} {player.team} Star
                    </span>

                    {/* Circular Impact grade display */}
                    <div className="mt-6 p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 w-full text-left space-y-2">
                      <div className="flex justify-between items-center text-xs text-zinc-400 py-1.5 border-b border-zinc-900">
                        <span>ATLAS Impact Grade</span>
                        <span className="font-mono text-purple-400 font-bold">{player.impact_score?.toFixed(1)} / 100</span>
                      </div>
                      <div className="flex justify-between items-center text-xs text-zinc-400 py-1.5 border-b border-zinc-900">
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
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-zinc-800/80 bg-zinc-950/40 hover:border-cyan-500/30 hover:bg-zinc-900/10 cursor-pointer select-none transition-all duration-200"
              >
                <span className="text-lg leading-none">{FLAG_MAP[teamName] || "🏳️"}</span>
                <span className="text-xs font-semibold text-zinc-300">{teamName}</span>
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* 6. TEAM EXPLORER SQUAD DRAWER MODAL OVERLAY */}
      {selectedExplorerTeam && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#030308]/85 backdrop-blur-sm p-4 animate-fade-in">
          <div className="relative w-full max-w-4xl max-h-[85vh] overflow-y-auto glass-card rounded-3xl border border-white/10 bg-[#07070d] p-6 shadow-2xl flex flex-col justify-between">
            
            {/* Close Button */}
            <button 
              onClick={() => { setSelectedExplorerTeam(null); setExplorerSquad([]); setExplorerStartingXI([]); }}
              className="absolute top-4 right-4 p-2 rounded-xl text-zinc-400 hover:text-white bg-white/5 border border-white/5 hover:border-white/10 transition cursor-pointer"
            >
              <X className="h-4 w-4" />
            </button>

            {/* Modal Body */}
            {explorerLoading ? (
              <div className="flex flex-col items-center justify-center py-20 min-h-[300px]">
                <Loader2 className="h-8 w-8 animate-spin text-cyan-400 mb-2" />
                <p className="text-xs text-zinc-400 font-mono">Assembling projected rosters...</p>
              </div>
            ) : (
              <div className="space-y-6">
                
                {/* Header */}
                <div className="flex items-center gap-3 pb-4 border-b border-zinc-900">
                  <span className="text-4xl select-none">{FLAG_MAP[selectedExplorerTeam] || "🏳️"}</span>
                  <div>
                    <h3 className="text-2xl font-extrabold text-white leading-none tracking-tight">{selectedExplorerTeam} Squad Explorer</h3>
                    <span className="text-xs text-cyan-400 font-mono mt-1 block">ATLAS Projected Roster Profile</span>
                  </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  
                  {/* Squad List */}
                  <div className="space-y-3">
                    <span className="text-[10px] font-mono text-zinc-400 font-bold uppercase tracking-wider block">Full Squad Roster</span>
                    <div className="max-h-[350px] overflow-y-auto border border-zinc-800/80 rounded-2xl divide-y divide-zinc-900 bg-zinc-950/20">
                      {explorerSquad.map((player) => (
                        <div key={player.player_name} className="flex justify-between items-center p-3 text-xs hover:bg-zinc-900/10 transition">
                          <div>
                            <span className="font-semibold text-white block">{player.player_name}</span>
                            <span className="text-[10px] font-mono text-zinc-500 uppercase">{player.position} • {player.age} Years Old</span>
                          </div>
                          <div className="text-right">
                            <span className="font-mono font-bold text-glow-purple text-purple-400 block">{player.impact_score?.toFixed(1)}</span>
                            <span className="text-[9px] font-mono text-zinc-600 block">MV: {player.market_value_m}M</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Projected Starting XI */}
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-[10px] font-mono text-cyan-400 font-bold uppercase tracking-wider">Projected Starting XI (4-3-3)</span>
                      <span className="px-2 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 font-mono text-[9px] uppercase font-bold animate-pulse">ATLAS Pick</span>
                    </div>

                    <div className="border border-zinc-800/80 rounded-2xl bg-zinc-950/20 max-h-[350px] overflow-y-auto divide-y divide-zinc-900">
                      {explorerStartingXI.map((player) => (
                        <div key={player.player_name} className="flex justify-between items-center p-3 text-xs">
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] font-mono text-cyan-400 px-1.5 py-0.5 rounded bg-cyan-950/45 border border-cyan-800/30 font-bold uppercase">{player.position}</span>
                            <span className="font-semibold text-white">{player.player_name}</span>
                          </div>
                          <span className="font-mono text-zinc-400 font-bold">{player.impact_score?.toFixed(1)}</span>
                        </div>
                      ))}
                    </div>
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
