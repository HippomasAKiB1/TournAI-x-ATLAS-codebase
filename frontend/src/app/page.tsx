"use client";

import React, { useState, useEffect } from "react";
import {
  LayoutDashboard,
  Grid,
  Swords,
  Users,
  Activity,
  Brain,
  Search,
  ChevronRight,
  Info,
  Calendar,
  AlertTriangle,
  ArrowRightLeft,
  Loader2,
  TrendingUp,
  Cpu,
  Trophy,
  Sparkles,
  AlertCircle,
  Play
} from "lucide-react";
import {
  getPredictions,
  getSimulations,
  getPlayers,
  getExplanations,
  getModelComparison,
  getGroupStandings,
  getInjuries,
  getBracketProbabilities,
  getQualificationProbabilities,
  getLatestShift,
  getPipelineStatus,
  getDbMatches,
  ingestMatch,
  runWhatIfSimulation
} from "../lib/api";
import {
  PredictionsResponse,
  SimulationsResponse,
  PlayersResponse,
  ExplanationsResponse,
  ModelComparisonResponse,
  GroupStandingsResponse,
  InjuryScenario,
  Prediction,
  GroupStandingRow,
  TeamStrength,
  Player
} from "../types";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
  Cell
} from "recharts";

export default function Home() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Data States
  const [predictions, setPredictions] = useState<PredictionsResponse | null>(null);
  const [simulations, setSimulations] = useState<SimulationsResponse | null>(null);
  const [players, setPlayers] = useState<PlayersResponse | null>(null);
  const [explanations, setExplanations] = useState<ExplanationsResponse | null>(null);
  const [modelComparison, setModelComparison] = useState<ModelComparisonResponse | null>(null);
  const [groupStandings, setGroupStandings] = useState<GroupStandingsResponse | null>(null);
  const [injuries, setInjuries] = useState<InjuryScenario[]>([]);
  const [bracket, setBracket] = useState<any>(null);
  const [qualification, setQualification] = useState<any>(null);
  const [dbMatches, setDbMatches] = useState<any[]>([]);
  const [latestShift, setLatestShift] = useState<any>(null);
  const [pipelineStatus, setPipelineStatus] = useState<any>({ status: "idle" });

  // Navigation State
  const [activeTab, setActiveTab] = useState<'dashboard' | 'standings' | 'predictor' | 'players' | 'whatif' | 'explain'>('dashboard');

  // Shared active injury star state (propagates to H2H predictor alert)
  const [activeInjuryPlayer, setActiveInjuryPlayer] = useState<string | null>(null);

  const loadData = async () => {
    try {
      const [
        predData,
        simData,
        playerData,
        expData,
        modelData,
        standingsData,
        injuryData,
        bracketData,
        qualData,
        dbMatchesData,
        shiftData,
        statusData
      ] = await Promise.all([
        getPredictions(),
        getSimulations(),
        getPlayers(),
        getExplanations(),
        getModelComparison(),
        getGroupStandings(),
        getInjuries(),
        getBracketProbabilities(),
        getQualificationProbabilities(),
        getDbMatches(),
        getLatestShift(),
        getPipelineStatus()
      ]);

      setPredictions(predData);
      setSimulations(simData);
      setPlayers(playerData);
      setExplanations(expData);
      setModelComparison(modelData);
      setGroupStandings(standingsData);
      setInjuries(injuryData);
      setBracket(bracketData);
      setQualification(qualData);
      setDbMatches(dbMatchesData);
      setLatestShift(shiftData);
      setPipelineStatus(statusData);
      setLoading(false);
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : 'Unknown error loading static assets.');
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    
    // Connect to Server-Sent Events (SSE) updates to automatically refresh data
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
    const sseUrl = `${API_BASE.replace(/\/api$/, '')}/api/sse/pipeline`;
    
    let eventSource: EventSource | null = null;
    try {
      eventSource = new EventSource(sseUrl);
      eventSource.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          if (parsed.event === 'pipeline_complete') {
            console.log("ATLAS Pipeline Update Detected. Reloading data...", parsed.generated_at);
            loadData();
          }
        } catch (err) {
          console.warn("Failed to parse SSE event data:", err);
        }
      };
      
      eventSource.onerror = (err) => {
        console.warn("SSE connection error. Reconnecting...", err);
      };
    } catch (err) {
      console.warn("SSE connection failed to initialize:", err);
    }
    
    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col flex-1 items-center justify-center min-h-screen bg-[#030308]">
        <div className="relative flex flex-col items-center">
          <Loader2 className="w-12 h-12 text-cyan-400 animate-spin mb-4" />
          <div className="absolute top-1 animate-ping w-10 h-10 rounded-full border-2 border-cyan-500/20"></div>
          <h2 className="text-xl font-semibold text-zinc-300 tracking-wider">ATLAS Engine Booting...</h2>
          <p className="text-sm text-zinc-500 mt-2">Loading Monte Carlo Simulations & SHAP models...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col flex-1 items-center justify-center min-h-screen bg-[#030308] p-6 text-center">
        <AlertTriangle className="w-16 h-16 text-rose-500 mb-4 animate-bounce" />
        <h2 className="text-2xl font-bold text-zinc-100 mb-2">Initialization Failed</h2>
        <p className="text-zinc-400 max-w-md mb-6">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="px-5 py-2.5 rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-200 hover:bg-zinc-700 transition"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  const bestModelName = modelComparison?.best_model || "Voting Ensemble";
  const testAccuracy = predictions?.accuracy_on_test ? (predictions.accuracy_on_test * 100).toFixed(2) : "60.16";

  return (
    <div className="min-h-screen flex flex-col lg:flex-row bg-[#030308] cyber-grid">
      {/* Sidebar Navigation */}
      <aside className="w-full lg:w-72 bg-zinc-950/80 border-b lg:border-b-0 lg:border-r border-zinc-800/80 backdrop-blur-xl flex flex-col z-10">
        <div className="p-6 border-b border-zinc-800/80 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-purple-600 to-cyan-400 flex items-center justify-center font-bold text-white shadow-lg shadow-purple-500/20">
                A
              </div>
              <div className="absolute -bottom-1 -right-1 w-3.5 h-3.5 bg-emerald-500 rounded-full border-2 border-zinc-950 animate-pulse"></div>
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight bg-gradient-to-r from-white to-zinc-400 bg-clip-text text-transparent">
                ATLAS ENGINE
              </h1>
              <span className="text-xs text-cyan-400/80 font-mono tracking-widest block uppercase">
                TournAI v1.2
              </span>
            </div>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 p-4 space-y-1.5 overflow-y-auto">
          {[
            { id: 'dashboard', label: 'Simulation Overview', icon: LayoutDashboard },
            { id: 'standings', label: 'Standings & Bracket', icon: Grid },
            { id: 'predictor', label: 'H2H Predictor', icon: Swords },
            { id: 'players', label: 'Player Intelligence', icon: Users },
            { id: 'whatif', label: 'Injury What-If Lab', icon: Activity },
            { id: 'explain', label: 'Explainability Hub', icon: Brain },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? "bg-gradient-to-r from-purple-900/40 to-cyan-900/40 text-cyan-300 border border-cyan-500/30 text-glow-cyan shadow-sm shadow-cyan-500/5"
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/50 border border-transparent"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-zinc-400'}`} />
                {tab.label}
              </button>
            );
          })}
        </nav>

        {/* Divider */}
        <div className="h-px bg-zinc-800/80 my-2 mx-4"></div>

        {/* Fan Prediction Link */}
        <div className="px-4 py-1.5">
          <button
            onClick={() => {
              const token = localStorage.getItem("token");
              if (token) {
                window.location.href = "/competition";
              } else {
                window.location.href = "/auth";
              }
            }}
            className="w-full flex items-center justify-between gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all duration-300 bg-gradient-to-r from-purple-900/30 to-cyan-900/30 hover:from-purple-900/50 hover:to-cyan-900/50 border border-cyan-500/20 hover:border-cyan-400/40 text-cyan-300 shadow-md shadow-cyan-500/5 cursor-pointer group"
          >
            <div className="flex items-center gap-3">
              <Trophy className="w-4 h-4 text-cyan-400 group-hover:scale-110 transition-transform" />
              <span>Fan Prediction League</span>
            </div>
            <ChevronRight className="w-4 h-4 text-cyan-400 group-hover:translate-x-1 transition-transform" />
          </button>
        </div>

        {/* Sidebar Footer */}
        <div className="p-5 border-t border-zinc-800/80 bg-zinc-950/40">
          <div className="flex items-center gap-3 p-3 rounded-lg bg-zinc-900/50 border border-zinc-800">
            <Cpu className="w-5 h-5 text-purple-400 animate-pulse-slow" />
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold text-zinc-300 truncate">Model: {bestModelName}</p>
              <p className="text-[10px] text-zinc-500 font-mono">Test Acc: {testAccuracy}%</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 p-4 lg:p-8 overflow-y-auto max-h-screen">
        {activeTab === 'dashboard' && simulations && (
          <DashboardView
            simulations={simulations}
            players={players}
            latestShift={latestShift}
            dbMatches={dbMatches}
            pipelineStatus={pipelineStatus}
            predictions={predictions}
            onRefresh={loadData}
          />
        )}
        {activeTab === 'standings' && groupStandings && bracket && simulations && (
          <StandingsView
            standings={groupStandings}
            bracket={bracket}
            qualification={qualification}
            simulations={simulations}
          />
        )}
        {activeTab === 'predictor' && predictions && explanations && players && injuries && (
          <PredictorView
            predictions={predictions}
            explanations={explanations}
            players={players}
            injuries={injuries}
            activeInjuryPlayer={activeInjuryPlayer}
          />
        )}
        {activeTab === 'players' && players && (
          <PlayersView players={players} />
        )}
        {activeTab === 'whatif' && injuries && players && simulations && (
          <WhatIfView
            injuries={injuries}
            players={players}
            simulations={simulations}
            activeInjuryPlayer={activeInjuryPlayer}
            setActiveInjuryPlayer={setActiveInjuryPlayer}
          />
        )}
        {activeTab === 'explain' && explanations && modelComparison && (
          <ExplainabilityView
            explanations={explanations}
            modelComparison={modelComparison}
          />
        )}
      </main>
    </div>
  );
}

/* ============================================================================
   VIEW 1: DASHBOARD / SIMULATION OVERVIEW
   ============================================================================ */
function DashboardView({
  simulations,
  players,
  latestShift,
  dbMatches,
  pipelineStatus,
  predictions,
  onRefresh
}: {
  simulations: SimulationsResponse;
  players: PlayersResponse | null;
  latestShift: any;
  dbMatches: any[];
  pipelineStatus: any;
  predictions: PredictionsResponse | null;
  onRefresh: () => Promise<void>;
}) {
  const simResults = simulations.results || [];
  
  // Extract Stats
  const topCandidate = simResults[0] || { Team: "N/A", "Champion %": 0 };
  const secondCandidate = simResults[1] || { Team: "N/A", "Champion %": 0 };
  const bestPlayer = players?.top50?.[0] || { player_name: "N/A", team: "N/A", impact_score: 0 };

  // Prepare chart data (Top 12 teams)
  const chartData = simResults.slice(0, 12).map(team => ({
    name: team.Team,
    "Champion %": team["Champion %"],
    "Finalist %": team["Finalist %"],
  }));

  const colors = ["#a855f7", "#ec4899", "#3b82f6", "#06b6d4", "#10b981", "#f59e0b", "#ef4444", "#6366f1", "#8b5cf6", "#14b8a6", "#84cc16", "#06b6d4"];

  // Ingestion State
  const completedMatchIds = new Set(dbMatches.filter(m => m.status === 'completed').map(m => m.id));
  const upcomingMatches = (predictions?.predictions || []).filter(p => !completedMatchIds.has(p.fixture_id));

  const [selectedFixtureId, setSelectedFixtureId] = useState<number>(1);
  const [homeScore, setHomeScore] = useState<number>(0);
  const [awayScore, setAwayScore] = useState<number>(0);
  const [adminKey, setAdminKey] = useState<string>("atlas-admin-secret-key-2026");
  const [isIngesting, setIsIngesting] = useState<boolean>(false);
  const [ingestError, setIngestError] = useState<string | null>(null);
  const [ingestLog, setIngestLog] = useState<string>("");

  useEffect(() => {
    if (upcomingMatches.length > 0 && !upcomingMatches.some(m => m.fixture_id === selectedFixtureId)) {
      setSelectedFixtureId(upcomingMatches[0].fixture_id);
    }
  }, [upcomingMatches, selectedFixtureId]);

  const handleIngest = async () => {
    const match = predictions?.predictions.find(p => p.fixture_id === selectedFixtureId);
    if (!match) return;
    setIsIngesting(true);
    setIngestError(null);
    setIngestLog("Submitting match result to ingestion queue...");
    try {
      await ingestMatch(
        match.home_team,
        match.away_team,
        homeScore,
        awayScore,
        "Group Stage",
        adminKey
      );
      
      setIngestLog("Adaptive update queued. Retraining Voting Ensemble & running Monte Carlo paths...");
      
      // Poll pipeline status
      const interval = setInterval(async () => {
        try {
          const status = await getPipelineStatus();
          if (status.status === 'idle') {
            clearInterval(interval);
            setIsIngesting(false);
            setIngestLog("");
            await onRefresh();
          } else {
            setIngestLog("Simulation running... (updating Elo ratings and bracket configurations)");
          }
        } catch (e) {
          console.warn("Error checking pipeline status", e);
        }
      }, 2000);
      
      // Timeout safety after 40 seconds
      setTimeout(() => {
        clearInterval(interval);
        setIsIngesting(false);
        setIngestLog("");
        onRefresh();
      }, 40000);
      
    } catch (err: any) {
      setIngestError(err.message || 'Pipeline ingestion execution failed.');
      setIsIngesting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Trophy className="w-6 h-6 text-amber-400" /> Tournament Simulation Hub
          </h2>
          <p className="text-sm text-zinc-400">
            Based on {simulations.n_simulations.toLocaleString()} Monte Carlo pipeline simulations.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {(isIngesting || pipelineStatus.status === 'running') && (
            <div className="flex items-center gap-2 text-xs text-cyan-400 font-semibold bg-cyan-950/20 border border-cyan-800/30 px-3 py-1.5 rounded-xl animate-pulse">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span>ATLAS Pipeline Processing...</span>
            </div>
          )}
          <div className="px-4 py-2 bg-purple-950/30 border border-purple-800/40 rounded-xl text-xs text-purple-300 font-semibold flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-purple-400" /> Global Predictions Active
          </div>
        </div>
      </div>

      {/* Narrative Callout banner */}
      {latestShift && latestShift.shift_narrative && (
        <div className="glass-card p-6 rounded-2xl border border-purple-500/20 bg-gradient-to-r from-purple-950/20 to-cyan-950/20 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-3 text-[9px] font-mono text-purple-400 uppercase tracking-widest flex items-center gap-1.5">
            <Sparkles className="w-3 h-3 text-purple-400" /> ATLAS Live Insight
          </div>
          <h4 className="text-xs font-bold text-purple-300 mb-2 font-mono uppercase tracking-wider">Tournament Probability Shift</h4>
          <p className="text-sm text-zinc-300 leading-relaxed font-sans">{latestShift.shift_narrative}</p>
        </div>
      )}

      {/* Highlights Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Card 1 */}
        <div className="glass-card p-6 rounded-2xl relative overflow-hidden group">
          <div className="absolute right-0 bottom-0 translate-x-4 translate-y-4 opacity-5 group-hover:scale-110 transition duration-300">
            <Trophy className="w-36 h-36 text-white" />
          </div>
          <span className="text-xs text-zinc-500 font-medium uppercase tracking-wider block">AI Chosen Favorite</span>
          <h3 className="text-3xl font-extrabold text-white mt-2 flex items-baseline gap-2">
            {topCandidate.Team}
            <span className="text-sm font-mono text-cyan-400 font-semibold">({topCandidate["Champion %"]?.toFixed(1)}%)</span>
          </h3>
          <p className="text-xs text-zinc-400 mt-2">Highest computed probability of lifting the 2026 World Cup.</p>
        </div>

        {/* Card 2 */}
        <div className="glass-card p-6 rounded-2xl relative overflow-hidden group">
          <div className="absolute right-0 bottom-0 translate-x-4 translate-y-4 opacity-5 group-hover:scale-110 transition duration-300">
            <TrendingUp className="w-36 h-36 text-white" />
          </div>
          <span className="text-xs text-zinc-500 font-medium uppercase tracking-wider block">Primary Challenger</span>
          <h3 className="text-3xl font-extrabold text-zinc-100 mt-2 flex items-baseline gap-2">
            {secondCandidate.Team}
            <span className="text-sm font-mono text-purple-400 font-semibold">({secondCandidate["Champion %"]?.toFixed(1)}%)</span>
          </h3>
          <p className="text-xs text-zinc-400 mt-2">Ranked 2nd globally with strong historical squad data indicators.</p>
        </div>

        {/* Card 3 */}
        <div className="glass-card p-6 rounded-2xl relative overflow-hidden group">
          <div className="absolute right-0 bottom-0 translate-x-4 translate-y-4 opacity-5 group-hover:scale-110 transition duration-300">
            <Users className="w-36 h-36 text-white" />
          </div>
          <span className="text-xs text-zinc-500 font-medium uppercase tracking-wider block">Top Graded Intelligence Player</span>
          <h3 className="text-2xl font-bold text-white mt-2 truncate">
            {bestPlayer.player_name}
          </h3>
          <p className="text-xs text-cyan-400 font-mono mt-1">
            {bestPlayer.team} • Impact Score: {bestPlayer.impact_score?.toFixed(1)}
          </p>
        </div>
      </div>

      {/* Main Charts & Table Area */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Championship odds bar chart */}
        <div className="xl:col-span-2 glass-card p-6 rounded-2xl">
          <div className="mb-4">
            <h4 className="text-base font-bold text-white">Championship Odds Comparison</h4>
            <p className="text-xs text-zinc-400">Comparing champion and finalist probabilities for the Top 12 contenders.</p>
          </div>
          <div className="h-96 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                layout="vertical"
                margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
              >
                <XAxis type="number" stroke="#71717a" fontSize={11} unit="%" />
                <YAxis dataKey="name" type="category" stroke="#71717a" fontSize={11} width={80} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#09090b",
                    borderColor: "#27272a",
                    color: "#f4f4f7",
                    borderRadius: "8px",
                    fontSize: "12px",
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '11px', color: '#a1a1aa' }} />
                <Bar dataKey="Champion %" fill="#8b5cf6" radius={[0, 4, 4, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
                  ))}
                </Bar>
                <Bar dataKey="Finalist %" fill="#06b6d4" opacity={0.4} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Top 15 probabilities list */}
        <div className="glass-card p-6 rounded-2xl flex flex-col">
          <div className="mb-4">
            <h4 className="text-base font-bold text-white">Stage-by-Stage Probabilities</h4>
            <p className="text-xs text-zinc-400">Survival and progression probabilities at each major milestone.</p>
          </div>
          <div className="flex-1 overflow-y-auto space-y-4 max-h-[384px] pr-2">
            {simResults.slice(0, 15).map((team, idx) => (
              <div key={team.Team} className="p-3 bg-zinc-900/40 border border-zinc-800/40 rounded-xl flex items-center justify-between text-sm group hover:border-zinc-700/60 transition">
                <div className="flex items-center gap-3">
                  <span className="text-xs font-mono text-zinc-500 font-semibold">{idx + 1}</span>
                  <div>
                    <p className="font-semibold text-zinc-200 group-hover:text-white transition">{team.Team}</p>
                    <p className="text-[10px] text-zinc-500">Group Exit: {team["Group Exit %"]?.toFixed(1)}%</p>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-xs text-zinc-400 block font-mono">Champion</span>
                  <span className="font-extrabold text-glow-cyan text-cyan-400 font-mono">
                    {team["Champion %"]?.toFixed(1)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Live Match Ingestion Control Panel (Admin Tool for testing adaptiveness) */}
      <div className="glass-card p-6 rounded-2xl border border-zinc-800 bg-gradient-to-tr from-zinc-950 to-zinc-900/40">
        <div className="flex items-center justify-between border-b border-zinc-800 pb-4 mb-4">
          <div>
            <h4 className="text-base font-bold text-white flex items-center gap-2">
              <Cpu className="w-5 h-5 text-cyan-400" /> Ingestion Control Panel (Live Testing Admin)
            </h4>
            <p className="text-xs text-zinc-400">Simulate a match completion to trigger ELO shifts, model retraining, and simulations.</p>
          </div>
          <span className="px-2 py-0.5 text-[9px] font-bold text-cyan-300 bg-cyan-950/20 border border-cyan-800/40 rounded uppercase font-mono tracking-widest">
            Dev Mode
          </span>
        </div>

        {isIngesting ? (
          <div className="flex flex-col items-center justify-center py-6 text-center">
            <Loader2 className="w-10 h-10 text-cyan-400 animate-spin mb-3" />
            <p className="text-sm font-semibold text-zinc-200">{ingestLog}</p>
            <p className="text-xs text-zinc-500 mt-1">This takes about 5-10 seconds to retrain models & simulate 10k bracket paths.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {ingestError && (
              <div className="p-3 bg-rose-950/20 border border-rose-900/30 text-rose-400 rounded-xl text-xs flex items-center gap-2">
                <AlertCircle className="w-4.5 h-4.5 text-rose-500 shrink-0" />
                <span>{ingestError}</span>
              </div>
            )}

            {upcomingMatches.length === 0 ? (
              <div className="text-zinc-500 text-xs py-2 text-center font-mono">
                All 72 scheduled group stage fixtures have been ingested. Adaptive model is fully loaded!
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-end">
                <div className="lg:col-span-4">
                  <label className="block text-[10px] font-mono uppercase text-zinc-500 mb-1">Select Fixture</label>
                  <select
                    value={selectedFixtureId}
                    onChange={(e) => setSelectedFixtureId(Number(e.target.value))}
                    className="w-full bg-zinc-900 border border-zinc-800 text-zinc-200 rounded-xl px-4 py-2.5 text-xs focus:outline-none focus:border-cyan-500"
                  >
                    {upcomingMatches.map(m => (
                      <option key={m.fixture_id} value={m.fixture_id}>
                        Match {m.fixture_id}: {m.home_team} vs. {m.away_team}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="lg:col-span-2">
                  <label className="block text-[10px] font-mono uppercase text-zinc-500 mb-1">
                    {predictions?.predictions.find(p => p.fixture_id === selectedFixtureId)?.home_team} Score
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={homeScore}
                    onChange={(e) => setHomeScore(Math.max(0, parseInt(e.target.value) || 0))}
                    className="w-full bg-zinc-900 border border-zinc-800 text-zinc-200 rounded-xl px-4 py-2 text-center text-sm font-bold focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div className="lg:col-span-2">
                  <label className="block text-[10px] font-mono uppercase text-zinc-500 mb-1">
                    {predictions?.predictions.find(p => p.fixture_id === selectedFixtureId)?.away_team} Score
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={awayScore}
                    onChange={(e) => setAwayScore(Math.max(0, parseInt(e.target.value) || 0))}
                    className="w-full bg-zinc-900 border border-zinc-800 text-zinc-200 rounded-xl px-4 py-2 text-center text-sm font-bold focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div className="lg:col-span-3">
                  <label className="block text-[10px] font-mono uppercase text-zinc-500 mb-1 flex items-center gap-1.5">
                    Pipeline Secret Key
                    <span title="X-ATLAS-KEY validation string"><Info className="w-3 h-3 text-zinc-500 cursor-help" /></span>
                  </label>
                  <input
                    type="password"
                    value={adminKey}
                    onChange={(e) => setAdminKey(e.target.value)}
                    placeholder="Auth key"
                    className="w-full bg-zinc-900 border border-zinc-800 text-zinc-200 rounded-xl px-4 py-2 text-xs focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div className="lg:col-span-1">
                  <button
                    onClick={handleIngest}
                    disabled={isIngesting || pipelineStatus.status === 'running'}
                    className="w-full bg-cyan-600 hover:bg-cyan-500 disabled:bg-zinc-800 text-white disabled:text-zinc-500 px-4 py-2.5 rounded-xl text-xs font-bold transition flex items-center justify-center gap-1.5 cursor-pointer"
                  >
                    <Play className="w-3.5 h-3.5" />
                    Run
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Full Monte Carlo stage statistics */}
      <div className="glass-card rounded-2xl overflow-hidden">
        <div className="p-6 border-b border-zinc-800">
          <h4 className="text-base font-bold text-white">Full Tournament Path Simulation Rates</h4>
          <p className="text-xs text-zinc-400">Likelihood of each country reaching specific rounds based on simulation models.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-zinc-950/60 border-b border-zinc-800 text-zinc-400 uppercase tracking-wider font-mono">
                <th className="py-3 px-6">Team</th>
                <th className="py-3 px-4 text-center">Champion %</th>
                <th className="py-3 px-4 text-center">Finalist %</th>
                <th className="py-3 px-4 text-center">Semi-Final %</th>
                <th className="py-3 px-4 text-center">Quarter-Final %</th>
                <th className="py-3 px-4 text-center">Round of 16 %</th>
                <th className="py-3 px-4 text-center">Round of 32 %</th>
                <th className="py-3 px-4 text-center">Group Exit %</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-900">
              {simResults.slice(0, 20).map((team) => (
                <tr key={team.Team} className="hover:bg-zinc-900/30 transition text-zinc-300">
                  <td className="py-3 px-6 font-semibold text-white">{team.Team}</td>
                  <td className="py-3 px-4 text-center font-bold text-cyan-400 font-mono">{team["Champion %"]?.toFixed(1)}%</td>
                  <td className="py-3 px-4 text-center font-mono">{team["Finalist %"]?.toFixed(1)}%</td>
                  <td className="py-3 px-4 text-center font-mono">{team["Semi-Final %"]?.toFixed(1)}%</td>
                  <td className="py-3 px-4 text-center font-mono">{team["Quarter-Final %"]?.toFixed(1)}%</td>
                  <td className="py-3 px-4 text-center font-mono">{team["Round of 16 %"]?.toFixed(1)}%</td>
                  <td className="py-3 px-4 text-center font-mono">{team["Round of 32 %"]?.toFixed(1)}%</td>
                  <td className="py-3 px-4 text-center text-zinc-500 font-mono">{team["Group Exit %"]?.toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* ============================================================================
   VIEW 2: STANDINGS & KNOCKOUT BRACKET
   ============================================================================ */
function StandingsView({
  standings,
  bracket,
  qualification,
  simulations
}: {
  standings: GroupStandingsResponse;
  bracket: any;
  qualification: any;
  simulations: SimulationsResponse;
}) {
  const [subTab, setSubTab] = useState<'groups' | 'bracket'>('groups');
  const groupsList = Object.keys(standings).sort((a, b) => a.localeCompare(b));
  const [selectedGroup, setSelectedGroup] = useState<string>(groupsList[0] || "Group A");

  const currentGroupData = standings[selectedGroup] || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Grid className="w-6 h-6 text-cyan-400" /> Tournament Standings & Bracket Tracker
          </h2>
          <p className="text-sm text-zinc-400">
            Monitor real-time simulated standings rankings and knockout bracket progress.
          </p>
        </div>

        {/* View Toggle */}
        <div className="flex bg-zinc-950/60 p-1 border border-zinc-800 rounded-xl max-w-sm shrink-0">
          <button
            onClick={() => setSubTab('groups')}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition ${
              subTab === 'groups'
                ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            Group Standings
          </button>
          <button
            onClick={() => setSubTab('bracket')}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition ${
              subTab === 'bracket'
                ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            Knockout Bracket
          </button>
        </div>
      </div>

      {subTab === 'groups' ? (
        <>
          {/* Tab grid for all 12 groups */}
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-12 gap-2">
            {groupsList.map((group) => {
              const letter = group.replace("Group ", "");
              const isSelected = selectedGroup === group;
              return (
                <button
                  key={group}
                  onClick={() => setSelectedGroup(group)}
                  className={`py-2 px-1 text-center font-mono font-bold text-xs rounded-lg transition-all ${
                    isSelected
                      ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 text-glow-cyan"
                      : "bg-zinc-900/40 text-zinc-500 hover:text-zinc-300 border border-zinc-800/60"
                  }`}
                >
                  {letter}
                </button>
              );
            })}
          </div>

          {/* Selected Group Standing Card */}
          <div className="glass-card rounded-2xl overflow-hidden">
            <div className="p-6 border-b border-zinc-800 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-white">{selectedGroup} Standings</h3>
                <p className="text-xs text-zinc-400">Simulation details and qualification chances for {selectedGroup}.</p>
              </div>
              <span className="px-3 py-1 bg-zinc-900 border border-zinc-800 text-zinc-500 font-mono text-[10px] uppercase rounded-full">
                Predicted Standing
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-sm">
                <thead>
                  <tr className="bg-zinc-950/40 border-b border-zinc-800 text-zinc-500 font-mono uppercase text-xs">
                    <th className="py-3.5 px-6 text-center w-16">Rank</th>
                    <th className="py-3.5 px-4">Team</th>
                    <th className="py-3.5 px-4 text-center">MP</th>
                    <th className="py-3.5 px-4 text-center">W</th>
                    <th className="py-3.5 px-4 text-center">D</th>
                    <th className="py-3.5 px-4 text-center">L</th>
                    <th className="py-3.5 px-4 text-center">GF</th>
                    <th className="py-3.5 px-4 text-center">GA</th>
                    <th className="py-3.5 px-4 text-center">GD</th>
                    <th className="py-3.5 px-4 text-center">Pts</th>
                    <th className="py-3.5 px-4 text-center">Group Odds (Monte Carlo)</th>
                    <th className="py-3.5 px-6 text-center">Advancement Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-900 text-zinc-300">
                  {currentGroupData.map((team) => {
                    const gdSign = team.GD > 0 ? `+${team.GD}` : team.GD;
                    
                    // Look up MC probabilities
                    const simRow = simulations.results.find(r => r.Team.toLowerCase() === team.Team.toLowerCase());
                    const r32Pct = simRow ? simRow["Round of 32 %"] : 0.0;
                    
                    const qualRow = qualification ? qualification[team.Team] : null;
                    const pFirst = qualRow?.first_place ?? 0.0;
                    const pSecond = qualRow?.second_place ?? 0.0;

                    // Color badges for qualifies status
                    let qualBadge = null;
                    if (team.Qualifies === "Yes") {
                      qualBadge = (
                        <span className="px-2.5 py-1 text-[10px] font-bold rounded-full bg-emerald-950/30 text-emerald-400 border border-emerald-800/40">
                          Qualified
                        </span>
                      );
                    } else if (team.Qualifies?.includes("Maybe")) {
                      qualBadge = (
                        <span className="px-2.5 py-1 text-[10px] font-bold rounded-full bg-amber-950/30 text-amber-400 border border-amber-800/40">
                          3rd Place Playoff
                        </span>
                      );
                    } else {
                      qualBadge = (
                        <span className="px-2.5 py-1 text-[10px] font-bold rounded-full bg-rose-950/30 text-rose-400 border border-rose-800/40">
                          Eliminated
                        </span>
                      );
                    }

                    return (
                      <tr key={team.Team} className="hover:bg-zinc-900/10 transition">
                        <td className="py-4 px-6 text-center font-mono font-extrabold text-zinc-400">{team.Position}</td>
                        <td className="py-4 px-4 font-semibold text-white">{team.Team}</td>
                        <td className="py-4 px-4 text-center font-mono">{team.MP}</td>
                        <td className="py-4 px-4 text-center font-mono">{team.W}</td>
                        <td className="py-4 px-4 text-center font-mono">{team.D}</td>
                        <td className="py-4 px-4 text-center font-mono">{team.L}</td>
                        <td className="py-4 px-4 text-center font-mono">{team.GF}</td>
                        <td className="py-4 px-4 text-center font-mono">{team.GA}</td>
                        <td className="py-4 px-4 text-center font-mono font-semibold">{gdSign}</td>
                        <td className="py-4 px-4 text-center font-bold text-white font-mono">{team.Pts}</td>
                        <td className="py-4 px-4">
                          <div className="flex gap-2 justify-center text-[10px] font-mono">
                            <span className="px-2 py-0.5 rounded bg-cyan-950/45 border border-cyan-800/30 text-cyan-400">1st: {pFirst.toFixed(0)}%</span>
                            <span className="px-2 py-0.5 rounded bg-indigo-950/45 border border-indigo-800/30 text-indigo-400">2nd: {pSecond.toFixed(0)}%</span>
                            <span className={`px-2 py-0.5 rounded border font-bold ${
                              r32Pct > 70 
                                ? 'bg-emerald-950/45 border-emerald-800/30 text-emerald-400' 
                                : r32Pct > 30 
                                  ? 'bg-amber-950/45 border-amber-800/30 text-amber-400' 
                                  : 'bg-rose-950/45 border-rose-800/30 text-rose-400'
                            }`}>
                              Adv: {r32Pct.toFixed(0)}%
                            </span>
                          </div>
                        </td>
                        <td className="py-4 px-6 text-center">{qualBadge}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : (
        /* Knockout Bracket View */
        <div className="glass-card p-6 rounded-2xl">
          <div className="mb-6 flex justify-between items-center">
            <div>
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Trophy className="w-5 h-5 text-amber-400" /> Projected Knockout Paths & Advancement Odds
              </h3>
              <p className="text-xs text-zinc-400">Projected bracket populated dynamically by Monte Carlo simulation likelihoods.</p>
            </div>
            <div className="text-xs font-mono text-zinc-500 bg-zinc-900/60 px-3 py-1 border border-zinc-800 rounded-full">
              Scroll horizontally →
            </div>
          </div>
          
          <div className="w-full overflow-x-auto pb-6 scrollbar-thin scrollbar-thumb-zinc-800">
            <div className="flex gap-8 p-2 min-w-[1400px] justify-between items-stretch">
              {/* Round of 32 Column */}
              <div className="flex flex-col justify-around py-2 space-y-4 w-64">
                <h4 className="text-xs font-bold font-mono tracking-widest text-zinc-500 text-center uppercase border-b border-zinc-900 pb-2 mb-2">Round of 32</h4>
                {bracket.r32.map((match: any) => (
                  <BracketMatchCard key={match.match_id} match={match} />
                ))}
              </div>
              
              {/* Round of 16 Column */}
              <div className="flex flex-col justify-around py-2 space-y-4 w-64">
                <h4 className="text-xs font-bold font-mono tracking-widest text-zinc-500 text-center uppercase border-b border-zinc-900 pb-2 mb-2">Round of 16</h4>
                {bracket.r16.map((match: any) => (
                  <BracketMatchCard key={match.match_id} match={match} />
                ))}
              </div>
              
              {/* Quarter-Final Column */}
              <div className="flex flex-col justify-around py-2 space-y-4 w-64">
                <h4 className="text-xs font-bold font-mono tracking-widest text-zinc-500 text-center uppercase border-b border-zinc-900 pb-2 mb-2">Quarter-Finals</h4>
                {bracket.qf.map((match: any) => (
                  <BracketMatchCard key={match.match_id} match={match} />
                ))}
              </div>
              
              {/* Semi-Final Column */}
              <div className="flex flex-col justify-around py-2 space-y-4 w-64">
                <h4 className="text-xs font-bold font-mono tracking-widest text-zinc-500 text-center uppercase border-b border-zinc-900 pb-2 mb-2">Semi-Finals</h4>
                {bracket.sf.map((match: any) => (
                  <BracketMatchCard key={match.match_id} match={match} />
                ))}
              </div>
              
              {/* Final Column */}
              <div className="flex flex-col justify-around py-2 space-y-4 w-64">
                <h4 className="text-xs font-bold font-mono tracking-widest text-zinc-500 text-center uppercase border-b border-zinc-900 pb-2 mb-2">Final</h4>
                {bracket.final.map((match: any) => (
                  <BracketMatchCard key={match.match_id} match={match} />
                ))}
              </div>
              
              {/* Champion Column */}
              <div className="flex flex-col justify-center py-2 w-64">
                <h4 className="text-xs font-bold font-mono tracking-widest text-zinc-500 text-center uppercase border-b border-zinc-900 pb-2 mb-2">Projected Champion</h4>
                {bracket.final[0] && (() => {
                  const fMatch = bracket.final[0];
                  const homeBetter = fMatch.home_adv_prob >= fMatch.away_adv_prob;
                  const champName = homeBetter ? fMatch.home_team : fMatch.away_team;
                  const champProb = homeBetter ? fMatch.home_adv_prob : fMatch.away_adv_prob;
                  return (
                    <div className="glass-card p-6 rounded-2xl border-2 border-amber-500/40 bg-gradient-to-br from-amber-950/20 to-yellow-950/10 text-center shadow-lg relative overflow-hidden group py-10">
                      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-amber-500 to-yellow-300"></div>
                      <Trophy className="w-12 h-12 text-amber-400 mx-auto mb-4 animate-bounce-slow" />
                      <h5 className="text-lg font-extrabold text-white tracking-tight uppercase">{champName}</h5>
                      <span className="text-[10px] text-zinc-500 font-mono tracking-widest uppercase block mt-1">Projected Winner</span>
                      <div className="mt-4 px-4 py-1.5 bg-amber-500/20 border border-amber-500/30 text-amber-300 rounded-full inline-block font-mono text-xs font-bold">
                        {champProb?.toFixed(1)}% Championship Odds
                      </div>
                    </div>
                  );
                })()}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Rules Notice */}
      <div className="flex gap-3 p-4 bg-zinc-900/30 border border-zinc-800/60 rounded-2xl text-xs text-zinc-400 items-start">
        <Info className="w-4.5 h-4.5 text-cyan-400 shrink-0 mt-0.5" />
        <div>
          <p className="font-semibold text-zinc-300 mb-0.5">WC 2026 Format Rules Applied</p>
          <p>
            The standing simulator evaluates the new 48-team format: 12 groups of 4 teams each. The top 2 teams of each group qualify automatically (24 teams), alongside the 8 best 3-ranked teams (creating 32 qualifying teams for the Round of 32 knockout bracket).
          </p>
        </div>
      </div>
    </div>
  );
}

function BracketMatchCard({ match }: { match: any }) {
  const homeBetter = match.home_adv_prob >= match.away_adv_prob;
  const isCompleted = match.home_score !== null && match.home_score !== undefined && match.away_score !== null && match.away_score !== undefined;
  
  return (
    <div className="glass-card p-3 rounded-xl border border-zinc-800/80 bg-zinc-950/40 w-64 shadow-lg hover:border-cyan-500/30 transition-all duration-200">
      <div className="text-[9px] font-mono text-zinc-500 mb-1.5 flex justify-between">
        <span>Match {match.match_id}</span>
        {isCompleted ? (
          <span className="text-emerald-400 font-bold uppercase tracking-wider text-[8px] bg-emerald-950/20 border border-emerald-900/40 px-1.5 py-0.5 rounded">FT Result</span>
        ) : (
          <span className="text-cyan-400/80">Slot Adv %</span>
        )}
      </div>
      <div className="space-y-1.5 text-xs">
        {/* Home Team */}
        <div className={`flex items-center justify-between p-1.5 rounded ${homeBetter ? 'bg-purple-950/20 text-purple-200 font-semibold' : 'text-zinc-400'}`}>
          <div className="flex items-center gap-1.5 truncate">
            <span className={`w-1.5 h-1.5 rounded-full ${homeBetter ? 'bg-purple-500' : 'bg-zinc-700'}`}></span>
            <span className="truncate">{match.home_team}</span>
            {!isCompleted && <span className="text-[9px] text-zinc-600 font-mono">({match.home_prob?.toFixed(0)}%)</span>}
          </div>
          {isCompleted ? (
            <span className="font-mono font-bold text-white text-sm bg-zinc-900 px-2 py-0.5 rounded border border-zinc-800">{match.home_score}</span>
          ) : (
            <span className="font-mono text-purple-400">{match.home_adv_prob?.toFixed(0)}%</span>
          )}
        </div>
        
        {/* Away Team */}
        <div className={`flex items-center justify-between p-1.5 rounded ${!homeBetter ? 'bg-cyan-950/20 text-cyan-200 font-semibold' : 'text-zinc-400'}`}>
          <div className="flex items-center gap-1.5 truncate">
            <span className={`w-1.5 h-1.5 rounded-full ${!homeBetter ? 'bg-cyan-500' : 'bg-zinc-700'}`}></span>
            <span className="truncate">{match.away_team}</span>
            {!isCompleted && <span className="text-[9px] text-zinc-600 font-mono">({match.away_prob?.toFixed(0)}%)</span>}
          </div>
          {isCompleted ? (
            <span className="font-mono font-bold text-white text-sm bg-zinc-900 px-2 py-0.5 rounded border border-zinc-800">{match.away_score}</span>
          ) : (
            <span className="font-mono text-cyan-400">{match.away_adv_prob?.toFixed(0)}%</span>
          )}
        </div>
      </div>
    </div>
  );
}

/* ============================================================================
   VIEW 3: H2H MATCH PREDICTOR & SHAP EXPLANATIONS
   ============================================================================ */
function PredictorView({
  predictions,
  explanations,
  players,
  injuries,
  activeInjuryPlayer
}: {
  predictions: PredictionsResponse;
  explanations: ExplanationsResponse;
  players: PlayersResponse;
  injuries: InjuryScenario[];
  activeInjuryPlayer: string | null;
}) {
  const [mode, setMode] = useState<'scheduled' | 'custom'>('scheduled');

  // List of all 72 fixtures
  const scheduledFixtures = predictions.predictions || [];
  const [selectedFixtureId, setSelectedFixtureId] = useState<number>(scheduledFixtures[0]?.fixture_id || 1);

  // List of all unique teams from team_strength
  const teamList = players.team_strength.map(t => t.team).sort();
  const [customHome, setCustomHome] = useState<string>("Argentina");
  const [customAway, setCustomAway] = useState<string>("Portugal");

  // State-driven async custom prediction
  const [customResult, setCustomResult] = useState<any>(null);
  const [customLoading, setCustomLoading] = useState(false);

  // Client Poisson goals fallback calculator
  const calculatePoissonLocal = (eloDiff: number, avgDiff: number) => {
    let lambdaHome = 1.35 + (eloDiff / 500) + (avgDiff / 15);
    let lambdaAway = 1.35 - (eloDiff / 500) - (avgDiff / 15);
    lambdaHome = Math.max(0.3, Math.min(5.0, lambdaHome));
    lambdaAway = Math.max(0.3, Math.min(5.0, lambdaAway));
    
    let bestProb = -1;
    let bestScore = [0, 0];
    
    const factorial = (n: number): number => {
      if (n <= 1) return 1;
      return n * factorial(n - 1);
    };
    
    for (let gh = 0; gh <= 5; gh++) {
      const probH = Math.pow(lambdaHome, gh) * Math.exp(-lambdaHome) / factorial(gh);
      for (let ga = 0; ga <= 5; ga++) {
        const probA = Math.pow(lambdaAway, ga) * Math.exp(-lambdaAway) / factorial(ga);
        const jointProb = probH * probA;
        if (jointProb > bestProb) {
          bestProb = jointProb;
          bestScore = [gh, ga];
        }
      }
    }
    return { homeGoals: bestScore[0], awayGoals: bestScore[1], jointProb: bestProb };
  };

  // Client-side Custom Predictor Function (resilient offline fallback)
  const getCustomPredictionLocal = (home: string, away: string) => {
    const homeStrength = players.team_strength.find(t => t.team.toLowerCase() === home.toLowerCase());
    const awayStrength = players.team_strength.find(t => t.team.toLowerCase() === away.toLowerCase());
    
    if (!homeStrength || !awayStrength) return null;
    
    let eloHome = homeStrength.current_elo || 1600;
    let eloAway = awayStrength.current_elo || 1600;
    
    let avgHome = homeStrength.avg_impact || 50;
    let avgAway = awayStrength.avg_impact || 50;
    
    // Adjust metrics if player what-if injury is active!
    if (activeInjuryPlayer) {
      const activeInjuryObj = injuries.find(i => i.Player === activeInjuryPlayer);
      if (activeInjuryObj) {
        const dropFactor = 1 - (activeInjuryObj["Strength Drop %"] / 100);
        if (home.toLowerCase() === activeInjuryObj.Team.toLowerCase()) {
          avgHome *= dropFactor;
          eloHome *= dropFactor;
        }
        if (away.toLowerCase() === activeInjuryObj.Team.toLowerCase()) {
          avgAway *= dropFactor;
          eloAway *= dropFactor;
        }
      }
    }

    const eloDiff = eloHome - eloAway;
    const avgDiff = avgHome - avgAway;
    
    // Adjusted Elo difference
    const eloDiffAdj = eloDiff + (avgDiff * 12);
    
    // Win probability
    const winProbHome = 1 / (1 + Math.pow(10, -eloDiffAdj / 400));
    
    // Draw probability
    const diffMagnitude = Math.abs(eloDiffAdj);
    const drawProb = Math.max(0.12, 0.28 - (diffMagnitude / 3000));
    
    const rawHomeProb = winProbHome * (1 - drawProb);
    const rawAwayProb = (1 - winProbHome) * (1 - drawProb);
    
    const total = rawHomeProb + rawAwayProb + drawProb;
    const home_win_prob = Number((rawHomeProb / total).toFixed(4));
    const away_win_prob = Number((rawAwayProb / total).toFixed(4));
    const draw_prob = Number((drawProb / total).toFixed(4));
    
    let predicted_result = 'Draw';
    if (home_win_prob > away_win_prob && home_win_prob > draw_prob) {
      predicted_result = 'Home Win';
    } else if (away_win_prob > home_win_prob && away_win_prob > draw_prob) {
      predicted_result = 'Away Win';
    }

    const poisson = calculatePoissonLocal(eloDiff, avgDiff);
    
    const eloDiffNarrative = eloDiff > 0 
      ? `Higher Elo rating (+${Math.round(eloDiff)} pts) increases win chance by ${(Math.abs(eloDiff) / 20).toFixed(1)}%`
      : `Lower Elo rating (-${Math.round(Math.abs(eloDiff))} pts) decreases win chance by ${(Math.abs(eloDiff) / 20).toFixed(1)}%`;
       
    const squadQualityNarrative = avgDiff > 0
      ? `Superior player squad quality (+${avgDiff.toFixed(1)} average impact) increases win chance by ${(avgDiff * 2.5).toFixed(1)}%`
      : `Weaker player squad quality (-${Math.abs(avgDiff).toFixed(1)} average impact) decreases win chance by ${(Math.abs(avgDiff) * 2.5).toFixed(1)}%`;
       
    const formDiffHome = homeStrength.form_10 || 0.5;
    const formDiffAway = awayStrength.form_10 || 0.5;
    const formDiff = formDiffHome - formDiffAway;
    const formNarrative = formDiff > 0
      ? `Better recent tournament momentum (+${(formDiff * 100).toFixed(0)}%) increases win chance by ${(formDiff * 25).toFixed(1)}%`
      : `Poorer recent tournament momentum (-${(Math.abs(formDiff) * 100).toFixed(0)}%) decreases win chance by ${(Math.abs(formDiff) * 25).toFixed(1)}%`;

    return {
      home_win_prob,
      away_win_prob,
      draw_prob,
      predicted_result,
      predicted_home_goals: poisson.homeGoals,
      predicted_away_goals: poisson.awayGoals,
      poisson_joint_prob: poisson.jointProb,
      confidence: calculateEntropyConfidence(home_win_prob, draw_prob, away_win_prob),
      elo_diff: eloDiff,
      upset_alert: (eloDiff > 0 && away_win_prob > 0.30) || (eloDiff < 0 && home_win_prob > 0.30),
      reasons: [squadQualityNarrative, eloDiffNarrative, formNarrative]
    };
  };

  const calculateEntropyConfidence = (p_home: number, p_draw: number, p_away: number): number => {
    const total = p_home + p_draw + p_away;
    if (total <= 0) return 0.33;
    const p1 = p_home / total;
    const p2 = p_draw / total;
    const p3 = p_away / total;
    let entropy = 0;
    [p1, p2, p3].forEach(p => {
      if (p > 0) entropy -= p * Math.log2(p);
    });
    return Math.max(0, Math.min(1, 1 - (entropy / Math.log2(3))));
  };

  useEffect(() => {
    if (mode === 'custom') {
      let active = true;
      async function fetchCustom() {
        setCustomLoading(true);
        try {
          // Wrap API post predict call
          const response = await fetch(`${API_BASE}/predict`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ home_team: customHome, away_team: customAway })
          });
          if (response.ok) {
            const res = await response.json();
            
            // Adjust calculation on backend values locally if active injury scenario affects custom teams!
            if (activeInjuryPlayer) {
              const localAdjusted = getCustomPredictionLocal(customHome, customAway);
              if (active && localAdjusted) setCustomResult(localAdjusted);
            } else {
              if (active) setCustomResult(res);
            }
          } else {
            const localRes = getCustomPredictionLocal(customHome, customAway);
            if (active) setCustomResult(localRes);
          }
        } catch (e) {
          const localRes = getCustomPredictionLocal(customHome, customAway);
          if (active) setCustomResult(localRes);
        }
        setCustomLoading(false);
      }
      fetchCustom();
      return () => { active = false; };
    }
  }, [customHome, customAway, mode, activeInjuryPlayer]);

  // Find active prediction & explanation variables
  let homeTeam = "";
  let awayTeam = "";
  let homeWinP = 0;
  let drawP = 0;
  let awayWinP = 0;
  let predictedResult = "";
  let eloDiffVal = 0;
  let reasons: string[] = [];
  let dateText = "Simulation Matchup";
  let forecastScoreText = "";
  let confidence = 0.33;
  let showUpsetAlert = false;
  let isMajorUpset = false;

  if (mode === 'scheduled') {
    const activeFixture = scheduledFixtures.find(f => f.fixture_id === selectedFixtureId) || scheduledFixtures[0];
    if (activeFixture) {
      homeTeam = activeFixture.home_team;
      awayTeam = activeFixture.away_team;
      homeWinP = activeFixture.home_win_prob;
      drawP = activeFixture.draw_prob;
      awayWinP = activeFixture.away_win_prob;
      predictedResult = activeFixture.predicted_result;
      eloDiffVal = activeFixture.elo_diff;
      dateText = activeFixture.date;
      confidence = (activeFixture as any).confidence ?? 0.50;
      showUpsetAlert = (activeFixture as any).upset_alert ?? false;
      isMajorUpset = showUpsetAlert && (activeFixture.ensemble_away_win > 0.40 || activeFixture.away_win_prob > 0.40);

      const hGoals = (activeFixture as any).predicted_home_goals ?? 1;
      const aGoals = (activeFixture as any).predicted_away_goals ?? 1;
      const jProb = (activeFixture as any).poisson_joint_prob ?? 0.15;
      forecastScoreText = `ATLAS Forecast: ${hGoals} - ${aGoals} (${(jProb * 100).toFixed(0)}% joint prob)`;

      const activeExp = explanations.match_explanations.find(e => e.fixture_id === activeFixture.fixture_id);
      if (activeExp) {
        reasons = [activeExp.reason_1, activeExp.reason_2, activeExp.reason_3];
      }
    }
  } else {
    // Custom match prediction
    homeTeam = customHome;
    awayTeam = customAway;
    if (customResult) {
      homeWinP = customResult.home_win_prob;
      drawP = customResult.draw_prob;
      awayWinP = customResult.away_win_prob;
      predictedResult = customResult.predicted_result;
      eloDiffVal = customResult.elo_diff;
      confidence = customResult.confidence;
      showUpsetAlert = customResult.upset_alert;
      isMajorUpset = showUpsetAlert && customResult.away_win_prob > 0.40;
      reasons = customResult.reasons;

      const hGoals = customResult.predicted_home_goals ?? 0;
      const aGoals = customResult.predicted_away_goals ?? 0;
      const jProb = customResult.poisson_joint_prob ?? 0.15;
      forecastScoreText = `ATLAS Forecast: ${hGoals} - ${aGoals} (${(jProb * 100).toFixed(0)}% joint prob)`;
    }
  }

  // Get active teams strength
  const homeStr = players.team_strength.find(t => t.team.toLowerCase() === homeTeam.toLowerCase());
  const awayStr = players.team_strength.find(t => t.team.toLowerCase() === awayTeam.toLowerCase());

  // Setup Radar Data
  const radarData = [
    { subject: 'Squad Avg Rating', A: homeStr?.avg_impact || 50, B: awayStr?.avg_impact || 50, fullMark: 100 },
    { subject: 'Max Player Grade', A: homeStr?.max_impact || 50, B: awayStr?.max_impact || 50, fullMark: 100 },
    { subject: 'Top 5 Average', A: homeStr?.top5_avg || 50, B: awayStr?.top5_avg || 50, fullMark: 100 },
    { subject: 'Squad Depth', A: homeStr?.depth || 20, B: awayStr?.depth || 20, fullMark: 50 },
    { subject: 'Elo Normalised', A: homeStr?.current_elo ? (homeStr.current_elo - 1400) / 10 : 50, B: awayStr?.current_elo ? (awayStr.current_elo - 1400) / 10 : 50, fullMark: 100 },
    { subject: 'Form Coefficient', A: (homeStr?.form_10 || 0.5) * 100, B: (awayStr?.form_10 || 0.5) * 100, fullMark: 100 },
  ];

  // Active injury scenario checks
  const activeInjuryObj = injuries.find(i => i.Player === activeInjuryPlayer);
  const injuredTeam = activeInjuryObj?.Team;
  const homeInjured = activeInjuryPlayer && homeTeam.toLowerCase() === injuredTeam?.toLowerCase();
  const awayInjured = activeInjuryPlayer && awayTeam.toLowerCase() === injuredTeam?.toLowerCase();

  // Confidence indicators
  const confidenceLabel = confidence >= 0.50 ? "High Confidence" : confidence >= 0.25 ? "Medium Confidence" : "Low Confidence";
  const confidenceColor = confidence >= 0.50 ? "text-emerald-400" : confidence >= 0.25 ? "text-amber-400" : "text-rose-400";

  return (
    <div className="space-y-6">
      {/* Mode Switches */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Swords className="w-6 h-6 text-cyan-400" /> Match Prediction Simulator
          </h2>
          <p className="text-sm text-zinc-400">
            Predict outcomes dynamically and read SHAP local explanations for model predictions.
          </p>
        </div>

        <div className="flex bg-zinc-950/60 p-1 border border-zinc-800 rounded-xl max-w-sm">
          <button
            onClick={() => setMode('scheduled')}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition ${
              mode === 'scheduled'
                ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            WC 2026 Fixtures
          </button>
          <button
            onClick={() => setMode('custom')}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition ${
              mode === 'custom'
                ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            Custom H2H Lab
          </button>
        </div>
      </div>

      {/* Selectors Block */}
      <div className="glass-card p-6 rounded-2xl">
        {mode === 'scheduled' ? (
          <div className="flex flex-col md:flex-row items-center gap-4">
            <Calendar className="w-5 h-5 text-purple-400 shrink-0" />
            <div className="flex-1 w-full">
              <label className="block text-[10px] font-mono uppercase text-zinc-500 mb-1">
                Select World Cup 2026 Group Stage Fixture
              </label>
              <select
                value={selectedFixtureId}
                onChange={(e) => setSelectedFixtureId(Number(e.target.value))}
                className="w-full bg-zinc-900 border border-zinc-800 text-zinc-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-cyan-500"
              >
                {scheduledFixtures.map(f => (
                  <option key={f.fixture_id} value={f.fixture_id}>
                    Match {f.fixture_id} ({f.date}): {f.home_team} vs. {f.away_team}
                  </option>
                ))}
              </select>
            </div>
          </div>
        ) : (
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            {/* Team A */}
            <div className="flex-1 w-full">
              <label className="block text-[10px] font-mono uppercase text-zinc-500 mb-1">
                Home / Team A
              </label>
              <select
                value={customHome}
                onChange={(e) => {
                  setCustomHome(e.target.value);
                  if (e.target.value === customAway) {
                    const idx = teamList.findIndex(t => t !== e.target.value);
                    setCustomAway(teamList[idx]);
                  }
                }}
                className="w-full bg-zinc-900 border border-zinc-800 text-zinc-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-cyan-500"
              >
                {teamList.map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>

            {/* Icon */}
            <div className="shrink-0 flex items-center justify-center p-3 rounded-full bg-zinc-900 border border-zinc-800 text-zinc-500 mt-5">
              <ArrowRightLeft className="w-5 h-5 text-cyan-400 rotate-90 md:rotate-0" />
            </div>

            {/* Team B */}
            <div className="flex-1 w-full">
              <label className="block text-[10px] font-mono uppercase text-zinc-500 mb-1">
                Away / Team B
              </label>
              <select
                value={customAway}
                onChange={(e) => {
                  setCustomAway(e.target.value);
                  if (e.target.value === customHome) {
                    const idx = teamList.findIndex(t => t !== e.target.value);
                    setCustomHome(teamList[idx]);
                  }
                }}
                className="w-full bg-zinc-900 border border-zinc-800 text-zinc-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-cyan-500"
              >
                {teamList.map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Main Predictor Report Display */}
      {mode === 'custom' && customLoading ? (
        <div className="glass-card p-12 rounded-2xl flex flex-col items-center justify-center">
          <Loader2 className="w-8 h-8 text-cyan-400 animate-spin mb-2" />
          <p className="text-zinc-400 text-xs font-mono">Running H2H prediction engines...</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">
          {/* Probability display and team values */}
          <div className="xl:col-span-3 flex flex-col gap-6">
            <div className="glass-card p-8 rounded-2xl relative overflow-hidden flex flex-col justify-between">
              <div className="absolute top-0 right-0 p-4 font-mono text-[9px] text-zinc-600 uppercase">
                {dateText}
              </div>

              {/* Active Injury Banner */}
              {(homeInjured || awayInjured) && (
                <div className="mb-4 p-3 bg-rose-950/20 border border-rose-900/30 rounded-xl text-xs text-rose-300 flex items-center gap-2">
                  <AlertCircle className="w-4.5 h-4.5 text-rose-500 shrink-0" />
                  <div>
                    <span className="font-semibold">{activeInjuryPlayer} is INJURED</span> — Team strength reduced. Model ratings adjusted. See bracket deltas in Injury Lab.
                  </div>
                </div>
              )}

              {/* Teams display */}
              <div className="flex items-center justify-between py-6">
                <div className="text-left w-5/12">
                  <h3 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight leading-none truncate">
                    {homeTeam}
                  </h3>
                  <span className="text-[10px] text-zinc-500 font-mono tracking-widest uppercase block mt-1">
                    Home Team
                  </span>
                  <span className="text-xs text-zinc-400 block font-mono mt-2">
                    Elo: {homeStr?.current_elo ? Math.round(homeStr.current_elo) : "1600"}
                  </span>
                </div>

                <div className="text-center shrink-0 w-2/12 font-bold text-zinc-500 font-mono text-lg">
                  VS
                </div>

                <div className="text-right w-5/12">
                  <h3 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight leading-none truncate">
                    {awayTeam}
                  </h3>
                  <span className="text-[10px] text-zinc-500 font-mono tracking-widest uppercase block mt-1">
                    Away Team
                  </span>
                  <span className="text-xs text-zinc-400 block font-mono mt-2">
                    Elo: {awayStr?.current_elo ? Math.round(awayStr.current_elo) : "1600"}
                  </span>
                </div>
              </div>

              {/* Segmented probability bar */}
              <div className="space-y-2 mt-4">
                <div className="flex h-7 rounded-lg overflow-hidden text-[10px] font-mono font-bold text-white text-center shadow-lg">
                  {/* Home Win */}
                  <div
                    style={{ width: `${homeWinP * 100}%` }}
                    className="bg-gradient-to-r from-purple-600 to-indigo-500 flex items-center justify-center min-w-[20px] transition-all duration-500"
                  >
                    {(homeWinP * 100).toFixed(0)}%
                  </div>
                  {/* Draw */}
                  <div
                    style={{ width: `${drawP * 100}%` }}
                    className="bg-zinc-700/60 flex items-center justify-center min-w-[20px] transition-all duration-500 border-x border-zinc-800"
                  >
                    {(drawP * 100).toFixed(0)}%
                  </div>
                  {/* Away Win */}
                  <div
                    style={{ width: `${awayWinP * 100}%` }}
                    className="bg-gradient-to-r from-cyan-500 to-emerald-500 flex items-center justify-center min-w-[20px] transition-all duration-500"
                  >
                    {(awayWinP * 100).toFixed(0)}%
                  </div>
                </div>

                {/* Labels for segmented bar */}
                <div className="flex justify-between text-[10px] font-mono text-zinc-500 px-1">
                  <span>{homeTeam} Win</span>
                  <span>Draw</span>
                  <span>{awayTeam} Win</span>
                </div>
              </div>

              {/* Verdict statement */}
              <div className="mt-8 pt-6 border-t border-zinc-800/80 flex flex-col sm:flex-row items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[10px] font-mono uppercase text-zinc-500 block">
                      Model Prediction Verdict
                    </span>
                    {showUpsetAlert && (
                      <span className={`px-2 py-0.5 text-[8px] font-bold uppercase rounded-full animate-pulse ${
                        isMajorUpset 
                          ? 'bg-rose-950/40 text-rose-400 border border-rose-800/50' 
                          : 'bg-amber-950/40 text-amber-400 border border-amber-800/50'
                      }`}>
                        {isMajorUpset ? 'Major Upset Alert' : 'Upset Alert'}
                      </span>
                    )}
                  </div>
                  <span className="text-base sm:text-lg font-bold text-white block">
                    {predictedResult === "Home Win" && `${homeTeam} win predicted`}
                    {predictedResult === "Away Win" && `${awayTeam} win predicted`}
                    {predictedResult === "Draw" && "Draw match predicted"}
                  </span>
                  <span className="text-xs text-cyan-400/90 font-mono font-semibold block mt-1">
                    {forecastScoreText}
                  </span>
                </div>
                <div className="px-4 py-2 bg-cyan-950/20 border border-cyan-800/40 rounded-xl text-center min-w-[120px]">
                  <span className="text-[9px] font-mono uppercase text-zinc-500 block">
                    Confidence Score
                  </span>
                  <span className={`text-[10px] font-bold block mt-0.5 ${confidenceColor}`}>
                    {confidenceLabel}
                  </span>
                  <span className="text-sm font-extrabold text-cyan-400 font-mono">
                    {(confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            </div>

            {/* Explainability reasons */}
            <div className="glass-card p-6 rounded-2xl">
              <h4 className="text-base font-bold text-white flex items-center gap-2 mb-4">
                <Brain className="w-5 h-5 text-purple-400" /> SHAP Feature Contribution Waterfall
              </h4>
              {reasons.length > 0 ? (
                <div className="space-y-3">
                  {reasons.map((reason, index) => {
                    const isPositive = reason.includes("increases");
                    return (
                      <div
                        key={index}
                        className={`p-4 rounded-xl flex items-center gap-3 border text-xs ${
                          isPositive
                            ? "bg-emerald-950/15 border-emerald-900/30 text-emerald-300"
                            : "bg-rose-950/15 border-rose-900/30 text-rose-300"
                        }`}
                      >
                        <div
                          className={`w-2.5 h-2.5 rounded-full ${
                            isPositive ? "bg-emerald-500 animate-pulse" : "bg-rose-500"
                          }`}
                        ></div>
                        <p>{reason}</p>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-zinc-500 text-xs py-4 text-center">
                  Select a match fixture or run custom sim to inspect shap narrative logs.
                </div>
              )}
            </div>
          </div>

          {/* Radar Compare Chart */}
          <div className="xl:col-span-2 glass-card p-6 rounded-2xl flex flex-col">
            <div className="mb-4">
              <h4 className="text-base font-bold text-white">Attribute Heatmap Comparison</h4>
              <p className="text-xs text-zinc-400">Comparing tactical metrics from player squad values.</p>
            </div>
            <div className="flex-1 w-full h-80">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                  <PolarGrid stroke="#27272a" />
                  <PolarAngleAxis dataKey="subject" stroke="#a1a1aa" fontSize={9} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} stroke="#3f3f46" fontSize={8} />
                  <Radar name={homeTeam} dataKey="A" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.25} />
                  <Radar name={awayTeam} dataKey="B" stroke="#06b6d4" fill="#06b6d4" fillOpacity={0.25} />
                  <Legend wrapperStyle={{ fontSize: '10px' }} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ============================================================================
   VIEW 4: PLAYER INTELLIGENCE LEADERBOARD
   ============================================================================ */
function PlayersView({ players }: { players: PlayersResponse }) {
  const [searchQuery, setSearchQuery] = useState("");
  const top50 = players.top50 || [];

  const filteredPlayers = top50.filter(
    player =>
      player.player_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      player.team.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Users className="w-6 h-6 text-purple-400" /> Player Intelligence Leaderboard
          </h2>
          <p className="text-sm text-zinc-400">
            Scored out of 100.0, analyzing attacking efficiency, progression carries, and pass stats.
          </p>
        </div>

        {/* Search */}
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-zinc-500 absolute left-3.5 top-3.5" />
          <input
            type="text"
            placeholder="Search players or teams..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-zinc-950/60 border border-zinc-800/80 text-zinc-200 placeholder-zinc-500 rounded-xl pl-10 pr-4 py-2.5 text-sm focus:outline-none focus:border-purple-500 transition-all"
          />
        </div>
      </div>

      {/* Leaderboard Table Card */}
      <div className="glass-card rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-zinc-950/60 border-b border-zinc-800 text-zinc-400 uppercase tracking-wider font-mono">
                <th className="py-4 px-6 text-center w-16">Rank</th>
                <th className="py-4 px-4">Player Name</th>
                <th className="py-4 px-4">Team</th>
                <th className="py-4 px-4 text-center">Impact Score</th>
                <th className="py-4 px-4 text-center">xG / 90</th>
                <th className="py-4 px-4 text-center">Goals / 90</th>
                <th className="py-4 px-4 text-center">Key Passes / 90</th>
                <th className="py-4 px-4 text-center">Interceptions / 90</th>
                <th className="py-4 px-4 text-center">Prog Carries / 90</th>
                <th className="py-4 px-6 text-center">Pass Accuracy</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-900 text-zinc-300">
              {filteredPlayers.length > 0 ? (
                filteredPlayers.map((player, index) => (
                  <tr key={player.player_name} className="hover:bg-zinc-900/10 transition">
                    <td className="py-3 px-6 text-center font-mono font-bold text-zinc-500">{index + 1}</td>
                    <td className="py-3 px-4 font-semibold text-white">{player.player_name}</td>
                    <td className="py-3 px-4 text-zinc-400">{player.team}</td>
                    <td className="py-3 px-4 text-center font-extrabold text-glow-purple text-purple-400 font-mono">
                      {player.impact_score?.toFixed(1)}
                    </td>
                    <td className="py-3 px-4 text-center font-mono">{player.xg_p90?.toFixed(2)}</td>
                    <td className="py-3 px-4 text-center font-mono">{player.goals_p90?.toFixed(2)}</td>
                    <td className="py-3 px-4 text-center font-mono">{player.key_passes_p90?.toFixed(2)}</td>
                    <td className="py-3 px-4 text-center font-mono">{player.interceptions_p90?.toFixed(2)}</td>
                    <td className="py-3 px-4 text-center font-mono text-zinc-400">{player.prog_carries_p90?.toFixed(1)}</td>
                    <td className="py-3 px-6 text-center font-mono font-semibold">
                      {(player.pass_accuracy * 100).toFixed(0)}%
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={10} className="py-8 text-center text-zinc-500 font-mono text-xs">
                    No players match the search criteria.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* ============================================================================
   VIEW 5: INJURY WHAT-IF LAB
   ============================================================================ */
function WhatIfView({
  injuries,
  players,
  simulations,
  activeInjuryPlayer,
  setActiveInjuryPlayer
}: {
  injuries: InjuryScenario[];
  players: PlayersResponse;
  simulations: SimulationsResponse;
  activeInjuryPlayer: string | null;
  setActiveInjuryPlayer: (val: string | null) => void;
}) {
  const [selectedPlayer, setSelectedPlayer] = useState<string>(injuries[0]?.Player || "Mohamed Salah");
  const activeInjury = injuries.find(i => i.Player === selectedPlayer) || injuries[0];

  // Get active player detailed stats
  const activePlayerStats = players.top50.find(p => p.player_name === selectedPlayer);

  // States for what-if async simulation results
  const [whatIfResult, setWhatIfResult] = useState<any>(null);
  const [whatIfLoading, setWhatIfLoading] = useState<boolean>(false);

  // Fallback calculation helper (approximates deltas locally if backend simulator is offline)
  const computeLocalWhatIf = (injury: InjuryScenario) => {
    const baseTeamRow = simulations?.results.find(r => r.Team.toLowerCase() === injury.Team.toLowerCase());
    if (!baseTeamRow) return null;
    
    const dropPct = injury["Strength Drop %"];
    const scaleFactor = 1 - (dropPct / 100);
    
    return {
      team: injury.Team,
      strength_drop_pct: dropPct,
      player_name: injury.Player,
      isFallback: true,
      before: {
        champion: baseTeamRow["Champion %"],
        finalist: baseTeamRow["Finalist %"],
        semi_final: baseTeamRow["Semi-Final %"],
        quarter_final: baseTeamRow["Quarter-Final %"],
        r16: baseTeamRow["Round of 16 %"]
      },
      after: {
        champion: baseTeamRow["Champion %"] * scaleFactor * scaleFactor,
        finalist: baseTeamRow["Finalist %"] * scaleFactor,
        semi_final: baseTeamRow["Semi-Final %"] * (1 - (dropPct / 150)),
        quarter_final: baseTeamRow["Quarter-Final %"] * (1 - (dropPct / 200)),
        r16: baseTeamRow["Round of 16 %"] * (1 - (dropPct / 300))
      },
      narrative: `${injury.Player}'s absence reduces ${injury.Team}'s squad strength by ${dropPct.toFixed(1)}%. (Approximated locally due to service offline)`
    };
  };

  useEffect(() => {
    let active = true;
    async function runSimulation() {
      if (!activeInjury) return;
      setWhatIfLoading(true);
      try {
        const response = await runWhatIfSimulation(activeInjury.Team, activeInjury["Strength Drop %"], selectedPlayer);
        if (active) {
          if (response && response.status === "success") {
            setWhatIfResult(response.comparison);
          } else {
            setWhatIfResult(computeLocalWhatIf(activeInjury));
          }
          setWhatIfLoading(false);
        }
      } catch (e) {
        if (active) {
          setWhatIfResult(computeLocalWhatIf(activeInjury));
          setWhatIfLoading(false);
        }
      }
    }
    runSimulation();
    return () => { active = false; };
  }, [selectedPlayer, activeInjury]);

  const isScenarioActive = activeInjuryPlayer === selectedPlayer;
  const toggleScenario = () => {
    if (isScenarioActive) {
      setActiveInjuryPlayer(null);
    } else {
      setActiveInjuryPlayer(selectedPlayer);
    }
  };

  // Recharts Bar Data
  const chartData = whatIfResult ? [
    { name: 'R16', Baseline: whatIfResult.before.r16, 'With Injury': whatIfResult.after.r16 },
    { name: 'QF', Baseline: whatIfResult.before.quarter_final, 'With Injury': whatIfResult.after.quarter_final },
    { name: 'SF', Baseline: whatIfResult.before.semi_final, 'With Injury': whatIfResult.after.semi_final },
    { name: 'Final', Baseline: whatIfResult.before.finalist, 'With Injury': whatIfResult.after.finalist },
    { name: 'Champ', Baseline: whatIfResult.before.champion, 'With Injury': whatIfResult.after.champion },
  ] : [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Activity className="w-6 h-6 text-emerald-400" /> Injury What-If Lab
          </h2>
          <p className="text-sm text-zinc-400">
            Simulate the impact on a country's team strength if their key player is injured.
          </p>
        </div>

        {/* Activate Scenario Button */}
        {activeInjury && (
          <button
            onClick={toggleScenario}
            className={`px-4 py-2.5 rounded-xl text-xs font-semibold border transition-all flex items-center gap-2 cursor-pointer ${
              isScenarioActive 
                ? 'bg-rose-950/20 text-rose-400 border-rose-800/40 hover:bg-rose-950/40 shadow-sm shadow-rose-950/30' 
                : 'bg-zinc-900/60 text-zinc-300 border-zinc-800 hover:border-zinc-700 hover:bg-zinc-800/50'
            }`}
          >
            <AlertCircle className={`w-4 h-4 ${isScenarioActive ? 'text-rose-400 animate-pulse' : 'text-zinc-500'}`} />
            {isScenarioActive ? `${selectedPlayer} Active Scenario INJURED` : `Mark ${selectedPlayer} Injured`}
          </button>
        )}
      </div>

      {/* Selector Card */}
      <div className="glass-card p-6 rounded-2xl">
        <div className="flex flex-col md:flex-row items-center gap-4">
          <div className="w-full">
            <label className="block text-[10px] font-mono uppercase text-zinc-500 mb-1">
              Select Key Tournament Star
            </label>
            <select
              value={selectedPlayer}
              onChange={(e) => setSelectedPlayer(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-800 text-zinc-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-emerald-500"
            >
              {injuries.map(i => (
                <option key={i.Player} value={i.Player}>
                  {i.Player} ({i.Team}) — Impact: {i["Impact Score"]?.toFixed(1)}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Comparison Grid */}
      {activeInjury && (
        <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">
          {/* Simulation stats display */}
          <div className="xl:col-span-3 flex flex-col gap-6">
            <div className="glass-card p-8 rounded-2xl flex flex-col justify-between relative overflow-hidden group">
              <div className="absolute right-0 bottom-0 translate-x-4 translate-y-4 opacity-5 group-hover:scale-110 transition duration-300">
                <Activity className="w-36 h-36 text-white" />
              </div>

              <div>
                <span className="text-[10px] font-mono uppercase text-zinc-500 block">
                  Simulating Absence Impact
                </span>
                <h3 className="text-3xl font-extrabold text-white tracking-tight mt-1">
                  {activeInjury.Player}
                </h3>
                <span className="text-xs text-emerald-400 font-mono mt-1 block">
                  {activeInjury.Team} National Squad
                </span>
              </div>

              {/* Score comparisons */}
              <div className="grid grid-cols-2 gap-4 mt-8">
                <div className="p-4 bg-zinc-900/40 border border-zinc-800/40 rounded-xl text-center">
                  <span className="text-[10px] font-mono text-zinc-500 uppercase block">
                    Squad Rating (With Player)
                  </span>
                  <span className="text-2xl font-extrabold text-zinc-200 font-mono">
                    {activeInjury["Team Avg (with)"]?.toFixed(2)}
                  </span>
                </div>
                <div className="p-4 bg-rose-950/10 border border-rose-900/20 rounded-xl text-center">
                  <span className="text-[10px] font-mono text-zinc-500 uppercase block">
                    Squad Rating (Without Player)
                  </span>
                  <span className="text-2xl font-extrabold text-rose-400 font-mono">
                    {activeInjury["Team Avg (without)"]?.toFixed(2)}
                  </span>
                </div>
              </div>

              {/* Gauge indicator */}
              <div className="mt-8 pt-6 border-t border-zinc-800/80 flex items-center justify-between">
                <div>
                  <span className="text-[10px] font-mono uppercase text-zinc-500 block">
                    Computed Strength Drop
                  </span>
                  <span className="text-2xl font-extrabold text-rose-500 font-mono">
                    {activeInjury["Strength Drop %"]?.toFixed(2)}%
                  </span>
                </div>
                <div className="px-4 py-2 bg-rose-950/30 border border-rose-800/30 text-rose-400 rounded-xl text-xs font-semibold animate-pulse-slow">
                  Tactical Shock Predicted
                </div>
              </div>
            </div>

            {/* Narrative Card */}
            <div className="glass-card p-6 rounded-2xl border border-rose-500/20 bg-gradient-to-r from-rose-950/20 to-zinc-900/30 relative overflow-hidden group">
              <h4 className="text-xs font-bold text-rose-400 mb-2 font-mono uppercase tracking-wider flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-rose-400" /> Narrative Impact Explanation
                {whatIfResult?.isFallback && (
                  <span className="px-2 py-0.5 text-[8px] bg-amber-500/10 border border-amber-800/30 text-amber-400 rounded font-mono normal-case">
                    ⚠️ Offline Fallback
                  </span>
                )}
              </h4>
              
              {whatIfLoading ? (
                <div className="flex items-center gap-2 text-zinc-400 py-3 text-xs font-mono">
                  <Loader2 className="w-4 h-4 animate-spin text-rose-400" />
                  <span>Rerunning Monte Carlo simulations...</span>
                </div>
              ) : (
                <p className="text-sm text-zinc-300 leading-relaxed font-sans">
                  {whatIfResult?.narrative}
                </p>
              )}
            </div>
          </div>

          {/* Player profile stats */}
          <div className="xl:col-span-2 glass-card p-6 rounded-2xl flex flex-col justify-between">
            <div>
              <h4 className="text-base font-bold text-white mb-1">Key Player Attribute Card</h4>
              <p className="text-xs text-zinc-400 mb-6">Tactical breakdown for the selected squad star.</p>

              {activePlayerStats ? (
                <div className="space-y-4 text-xs">
                  <div className="flex justify-between py-2 border-b border-zinc-900 text-zinc-400">
                    <span>Tactical Rating Grade</span>
                    <span className="font-mono text-white font-semibold">
                      {activePlayerStats.impact_score?.toFixed(1)} / 100
                    </span>
                  </div>
                  <div className="flex justify-between py-2 border-b border-zinc-900 text-zinc-400">
                    <span>Expected Goals per 90 (xG)</span>
                    <span className="font-mono text-white font-semibold">
                      {activePlayerStats.xg_p90?.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between py-2 border-b border-zinc-900 text-zinc-400">
                    <span>Goals scored per 90</span>
                    <span className="font-mono text-white font-semibold">
                      {activePlayerStats.goals_p90?.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between py-2 border-b border-zinc-900 text-zinc-400">
                    <span>Key shot-creating passes per 90</span>
                    <span className="font-mono text-white font-semibold">
                      {activePlayerStats.key_passes_p90?.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between py-2 border-b border-zinc-900 text-zinc-400">
                    <span>Progressive carries per 90</span>
                    <span className="font-mono text-white font-semibold">
                      {activePlayerStats.prog_carries_p90?.toFixed(1)}
                    </span>
                  </div>
                  <div className="flex justify-between py-2 border-b border-zinc-900 text-zinc-400">
                    <span>Passing Accuracy Rate</span>
                    <span className="font-mono text-white font-semibold">
                      {(activePlayerStats.pass_accuracy * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              ) : (
                <div className="text-zinc-500 text-xs py-4 text-center">
                  Detailed attributes not loaded in players profile database.
                </div>
              )}
            </div>

            <div className="mt-6 p-4 bg-zinc-900/30 border border-zinc-800/60 rounded-xl text-[11px] text-zinc-400">
              Absence of this player alters the team's features inside the ATLAS classifier model. Squad features such as expected goals per match drop, forcing the model to calculate a lower probability of victory during simulated brackets.
            </div>
          </div>
        </div>
      )}

      {/* progression delta comparison bar chart */}
      {whatIfResult && (
        <div className="glass-card p-6 rounded-2xl">
          <div className="mb-4">
            <h4 className="text-base font-bold text-white">Progression Probability Delta (Before vs After)</h4>
            <p className="text-xs text-zinc-400">Comparing survival rate probabilities across tournament rounds.</p>
          </div>
          {whatIfLoading ? (
            <div className="h-64 flex items-center justify-center">
              <Loader2 className="w-6 h-6 text-rose-500 animate-spin" />
            </div>
          ) : (
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={chartData}
                  margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                >
                  <XAxis dataKey="name" stroke="#71717a" fontSize={11} />
                  <YAxis stroke="#71717a" fontSize={11} unit="%" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#09090b",
                      borderColor: "#27272a",
                      color: "#f4f4f7",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px' }} />
                  <Bar dataKey="Baseline" fill="#06b6d4" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="With Injury" fill="#f43f5e" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ============================================================================
   VIEW 6: EXPLAINABILITY HUB
   ============================================================================ */
function ExplainabilityView({
  explanations,
  modelComparison
}: {
  explanations: ExplanationsResponse;
  modelComparison: ModelComparisonResponse;
}) {
  const fiData = (explanations.feature_importance || []).slice(0, 10).map(item => ({
    name: item.feature,
    value: item.shap_importance * 100, // Show percentage
  }));

  // List of models
  const models = modelComparison.models || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Brain className="w-6 h-6 text-purple-400" /> Explainability & Performance Hub
          </h2>
          <p className="text-sm text-zinc-400">
            Interpret global ML metrics and check model calibration statistics on the test set.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Global Feature Importance Chart */}
        <div className="xl:col-span-2 glass-card p-6 rounded-2xl">
          <div className="mb-4">
            <h4 className="text-base font-bold text-white">Global SHAP Feature Importance</h4>
            <p className="text-xs text-zinc-400">Mean impact of top features on predicted match outcomes.</p>
          </div>
          <div className="h-96 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={fiData}
                layout="vertical"
                margin={{ top: 5, right: 20, left: 20, bottom: 5 }}
              >
                <XAxis type="number" stroke="#71717a" fontSize={11} unit="%" />
                <YAxis dataKey="name" type="category" stroke="#71717a" fontSize={10} width={130} />
                <Tooltip
                  formatter={(value) => [`${Number(value).toFixed(2)}%`, "SHAP Importance"]}
                  contentStyle={{
                    backgroundColor: "#09090b",
                    borderColor: "#27272a",
                    color: "#f4f4f7",
                    borderRadius: "8px",
                    fontSize: "12px",
                  }}
                />
                <Bar dataKey="value" fill="#a855f7" radius={[0, 4, 4, 0]}>
                  {fiData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={index % 2 === 0 ? "#8b5cf6" : "#06b6d4"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Feature dictionary glossary */}
        <div className="glass-card p-6 rounded-2xl flex flex-col justify-between">
          <div>
            <h4 className="text-base font-bold text-white mb-1">Feature Dictionary Glossary</h4>
            <p className="text-xs text-zinc-400 mb-6">Definitions of features that impact prediction outcomes.</p>

            <div className="space-y-4 text-xs">
              <div className="p-3 bg-zinc-900/30 border border-zinc-800/40 rounded-xl">
                <span className="font-semibold text-cyan-400 font-mono block mb-0.5">opp_conf_code</span>
                <p className="text-zinc-400 text-[11px]">Confederation profile code of the opponent (UEFA, CONMEBOL, CAF, etc.).</p>
              </div>
              <div className="p-3 bg-zinc-900/30 border border-zinc-800/40 rounded-xl">
                <span className="font-semibold text-cyan-400 font-mono block mb-0.5">is_knockout</span>
                <p className="text-zinc-400 text-[11px]">Flag indicating if the match is in a knockout stage, where draw rates collapse to zero.</p>
              </div>
              <div className="p-3 bg-zinc-900/30 border border-zinc-800/40 rounded-xl">
                <span className="font-semibold text-cyan-400 font-mono block mb-0.5">elo_diff</span>
                <p className="text-zinc-400 text-[11px]">Difference in Elo ratings between the team and its opponent.</p>
              </div>
              <div className="p-3 bg-zinc-900/30 border border-zinc-800/40 rounded-xl">
                <span className="font-semibold text-cyan-400 font-mono block mb-0.5">squad_quality_diff</span>
                <p className="text-zinc-400 text-[11px]">Computed average impact score gap based on underlying club prestige statistics.</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Model Performance Comparison Grid */}
      <div className="glass-card rounded-2xl overflow-hidden">
        <div className="p-6 border-b border-zinc-800">
          <h4 className="text-base font-bold text-white">ATLAS Model Performance Matrix</h4>
          <p className="text-xs text-zinc-400">Comparing test set metrics (World Cup 2022 fixtures) across candidate classifiers.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-zinc-950/60 border-b border-zinc-800 text-zinc-400 uppercase tracking-wider font-mono">
                <th className="py-3.5 px-6">Model</th>
                <th className="py-3.5 px-4 text-center">Accuracy</th>
                <th className="py-3.5 px-4 text-center">Log Loss</th>
                <th className="py-3.5 px-4 text-center">Brier Score</th>
                <th className="py-3.5 px-4 text-center">ROC AUC</th>
                <th className="py-3.5 px-4 text-center">F1 Weighted</th>
                <th className="py-3.5 px-4 text-center">MCC</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-900 text-zinc-300">
              {models.map((model) => {
                const isBest = model.Model === modelComparison.best_model;
                return (
                  <tr key={model.Model} className={`hover:bg-zinc-900/10 transition ${isBest ? "bg-cyan-950/5 text-cyan-200" : ""}`}>
                    <td className="py-3 px-6 font-semibold flex items-center gap-2">
                      {isBest && <Cpu className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />}
                      <span className={isBest ? "text-cyan-400 font-bold" : "text-white"}>{model.Model}</span>
                    </td>
                    <td className={`py-3 px-4 text-center font-mono ${isBest ? "font-bold text-cyan-400" : ""}`}>
                      {(model.Accuracy * 100).toFixed(2)}%
                    </td>
                    <td className="py-3 px-4 text-center font-mono">{model["Log Loss"]?.toFixed(3)}</td>
                    <td className="py-3 px-4 text-center font-mono">{model["Brier Score"]?.toFixed(3)}</td>
                    <td className="py-3 px-4 text-center font-mono">{model["ROC AUC"]?.toFixed(3)}</td>
                    <td className="py-3 px-4 text-center font-mono">{model["F1 Weighted"]?.toFixed(3)}</td>
                    <td className="py-3 px-4 text-center font-mono">{model.MCC?.toFixed(3)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
