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
  Sparkles
} from "lucide-react";
import {
  getPredictions,
  getSimulations,
  getPlayers,
  getExplanations,
  getModelComparison,
  getGroupStandings,
  getInjuries
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

  // Navigation State
  const [activeTab, setActiveTab] = useState<'dashboard' | 'standings' | 'predictor' | 'players' | 'whatif' | 'explain'>('dashboard');

  // Load Data
  useEffect(() => {
    async function loadData() {
      try {
        const [
          predData,
          simData,
          playerData,
          expData,
          modelData,
          standingsData,
          injuryData
        ] = await Promise.all([
          getPredictions(),
          getSimulations(),
          getPlayers(),
          getExplanations(),
          getModelComparison(),
          getGroupStandings(),
          getInjuries()
        ]);

        setPredictions(predData);
        setSimulations(simData);
        setPlayers(playerData);
        setExplanations(expData);
        setModelComparison(modelData);
        setGroupStandings(standingsData);
        setInjuries(injuryData);
        setLoading(false);
      } catch (err) {
        console.error(err);
        setError(err instanceof Error ? err.message : 'Unknown error loading static assets.');
        setLoading(false);
      }
    }
    loadData();
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
            { id: 'standings', label: 'Group Standings', icon: Grid },
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
          <DashboardView simulations={simulations} players={players} />
        )}
        {activeTab === 'standings' && groupStandings && (
          <StandingsView standings={groupStandings} />
        )}
        {activeTab === 'predictor' && predictions && explanations && players && (
          <PredictorView
            predictions={predictions}
            explanations={explanations}
            players={players}
          />
        )}
        {activeTab === 'players' && players && (
          <PlayersView players={players} />
        )}
        {activeTab === 'whatif' && injuries && players && (
          <WhatIfView injuries={injuries} players={players} />
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
  players
}: {
  simulations: SimulationsResponse;
  players: PlayersResponse | null;
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

  // Gradient helper for chart bars
  const colors = ["#a855f7", "#ec4899", "#3b82f6", "#06b6d4", "#10b981", "#f59e0b", "#ef4444", "#6366f1", "#8b5cf6", "#14b8a6", "#84cc16", "#06b6d4"];

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
        <div className="px-4 py-2 bg-purple-950/30 border border-purple-800/40 rounded-xl text-xs text-purple-300 font-semibold flex items-center gap-2 animate-pulse-slow">
          <Sparkles className="w-4 h-4 text-purple-400" /> Global Predictions Active
        </div>
      </div>

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

        {/* Top 10 probabilities list */}
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
   VIEW 2: GROUP STAGE STANDINGS
   ============================================================================ */
function StandingsView({ standings }: { standings: GroupStandingsResponse }) {
  const groupsList = Object.keys(standings).sort((a, b) => a.localeCompare(b));
  const [selectedGroup, setSelectedGroup] = useState<string>(groupsList[0] || "Group A");

  const currentGroupData = standings[selectedGroup] || [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
          <Grid className="w-6 h-6 text-cyan-400" /> Group Stage Standings Simulator
        </h2>
        <p className="text-sm text-zinc-400">
          Predicted rankings and advancement outcomes for all 12 World Cup 2026 groups.
        </p>
      </div>

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
            <h3 className="text-lg font-bold text-white">{selectedGroup} standings</h3>
            <p className="text-xs text-zinc-400">Simulation details for {selectedGroup} matches.</p>
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
                <th className="py-3.5 px-6 text-center">Advancement Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-900 text-zinc-300">
              {currentGroupData.map((team) => {
                const gdSign = team.GD > 0 ? `+${team.GD}` : team.GD;
                
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
                    <td className="py-4 px-6 text-center">{qualBadge}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

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

/* ============================================================================
   VIEW 3: H2H MATCH PREDICTOR & SHAP EXPLANATIONS
   ============================================================================ */
function PredictorView({
  predictions,
  explanations,
  players
}: {
  predictions: PredictionsResponse;
  explanations: ExplanationsResponse;
  players: PlayersResponse;
}) {
  const [mode, setMode] = useState<'scheduled' | 'custom'>('scheduled');

  // List of all 72 fixtures
  const scheduledFixtures = predictions.predictions || [];
  const [selectedFixtureId, setSelectedFixtureId] = useState<number>(scheduledFixtures[0]?.fixture_id || 1);

  // List of all unique teams from team_strength
  const teamList = players.team_strength.map(t => t.team).sort();
  const [customHome, setCustomHome] = useState<string>("Argentina");
  const [customAway, setCustomAway] = useState<string>("Portugal");

  // Dynamic Custom Predictor Function
  const getCustomPrediction = (home: string, away: string) => {
    const homeStrength = players.team_strength.find(t => t.team.toLowerCase() === home.toLowerCase());
    const awayStrength = players.team_strength.find(t => t.team.toLowerCase() === away.toLowerCase());
    
    if (!homeStrength || !awayStrength) return null;
    
    const eloHome = homeStrength.current_elo || 1600;
    const eloAway = awayStrength.current_elo || 1600;
    const eloDiff = eloHome - eloAway;
    
    const avgHome = homeStrength.avg_impact || 50;
    const avgAway = awayStrength.avg_impact || 50;
    const avgDiff = avgHome - avgAway;
    
    // Calculate adjusted ELO difference
    const eloDiffAdj = eloDiff + (avgDiff * 12);
    
    // Win probability using sigmoid
    const winProbHome = 1 / (1 + Math.pow(10, -eloDiffAdj / 400));
    
    // Draw probability scales down with larger differences
    const diffMagnitude = Math.abs(eloDiffAdj);
    const drawProb = Math.max(0.12, 0.28 - (diffMagnitude / 3000));
    
    const rawHomeProb = winProbHome * (1 - drawProb);
    const rawAwayProb = (1 - winProbHome) * (1 - drawProb);
    
    // Normalize
    const total = rawHomeProb + rawAwayProb + drawProb;
    const home_win_prob = Number((rawHomeProb / total).toFixed(4));
    const away_win_prob = Number((rawAwayProb / total).toFixed(4));
    const draw_prob = Number((drawProb / total).toFixed(4));
    
    let predicted_result: 'Home Win' | 'Draw' | 'Away Win' = 'Draw';
    if (home_win_prob > away_win_prob && home_win_prob > draw_prob) {
      predicted_result = 'Home Win';
    } else if (away_win_prob > home_win_prob && away_win_prob > draw_prob) {
      predicted_result = 'Away Win';
    }
    
    // Generate Custom Explainability Narratives
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
      confidence: Math.max(home_win_prob, away_win_prob, draw_prob),
      elo_diff: eloDiff,
      reasons: [squadQualityNarrative, eloDiffNarrative, formNarrative]
    };
  };

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

      const activeExp = explanations.match_explanations.find(e => e.fixture_id === activeFixture.fixture_id);
      if (activeExp) {
        reasons = [activeExp.reason_1, activeExp.reason_2, activeExp.reason_3];
      }
    }
  } else {
    // Custom match simulation
    homeTeam = customHome;
    awayTeam = customAway;
    const customResult = getCustomPrediction(customHome, customAway);
    if (customResult) {
      homeWinP = customResult.home_win_prob;
      drawP = customResult.draw_prob;
      awayWinP = customResult.away_win_prob;
      predictedResult = customResult.predicted_result;
      eloDiffVal = customResult.elo_diff;
      reasons = customResult.reasons;
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
      <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">
        {/* Probability display and team values */}
        <div className="xl:col-span-3 flex flex-col gap-6">
          <div className="glass-card p-8 rounded-2xl relative overflow-hidden flex flex-col justify-between">
            <div className="absolute top-0 right-0 p-4 font-mono text-[9px] text-zinc-600 uppercase">
              {dateText}
            </div>

            {/* Teams display */}
            <div className="flex items-center justify-between py-6">
              <div className="text-left w-5/12">
                <h3 className="text-3xl font-extrabold text-white tracking-tight leading-none truncate">
                  {homeTeam}
                </h3>
                <span className="text-[10px] text-zinc-500 font-mono tracking-widest uppercase block mt-1">
                  Home Team
                </span>
                <span className="text-xs text-zinc-400 block font-mono mt-2">
                  Elo: {homeStr?.current_elo ? Math.round(homeStr.current_elo) : "N/A"}
                </span>
              </div>

              <div className="text-center shrink-0 w-2/12 font-bold text-zinc-500 font-mono text-lg">
                VS
              </div>

              <div className="text-right w-5/12">
                <h3 className="text-3xl font-extrabold text-white tracking-tight leading-none truncate">
                  {awayTeam}
                </h3>
                <span className="text-[10px] text-zinc-500 font-mono tracking-widest uppercase block mt-1">
                  Away Team
                </span>
                <span className="text-xs text-zinc-400 block font-mono mt-2">
                  Elo: {awayStr?.current_elo ? Math.round(awayStr.current_elo) : "N/A"}
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
                <span className="text-[10px] font-mono uppercase text-zinc-500 block">
                  Model Prediction Verdict
                </span>
                <span className="text-lg font-bold text-white">
                  {predictedResult === "Home Win" && `${homeTeam} win predicted`}
                  {predictedResult === "Away Win" && `${awayTeam} win predicted`}
                  {predictedResult === "Draw" && "Draw match predicted"}
                </span>
              </div>
              <div className="px-4 py-2 bg-cyan-950/20 border border-cyan-800/40 rounded-xl text-center">
                <span className="text-[9px] font-mono uppercase text-zinc-500 block">
                  Confidence Score
                </span>
                <span className="text-sm font-extrabold text-cyan-400 font-mono">
                  {(homeWinP > awayWinP && homeWinP > drawP ? homeWinP : awayWinP > homeWinP && awayWinP > drawP ? awayWinP : drawP).toFixed(1)}
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
    </div>
  );
}

/* ============================================================================
   VIEW 4: PLAYER INTELLIGENCE LEADERBOARD
   ============================================================================ */
function PlayersView({ players }: { players: PlayersResponse }) {
  const [searchQuery, setSearchQuery] = useState("");
  const top50 = players.top50 || [];

  // Filter players
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
  players
}: {
  injuries: InjuryScenario[];
  players: PlayersResponse;
}) {
  const [selectedPlayer, setSelectedPlayer] = useState<string>(injuries[0]?.Player || "Mohamed Salah");

  const activeInjury = injuries.find(i => i.Player === selectedPlayer) || injuries[0];

  // Get active player detailed stats
  const activePlayerStats = players.top50.find(p => p.player_name === selectedPlayer);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
          <Activity className="w-6 h-6 text-emerald-400" /> Injury What-If Lab
        </h2>
        <p className="text-sm text-zinc-400">
          Simulate the impact on a country's team strength if their key player is injured.
        </p>
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
            <div className="glass-card p-8 rounded-2xl flex flex-col justify-between h-full relative overflow-hidden group">
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
          </div>

          {/* Player profile stats */}
          <div className="xl:col-span-2 glass-card p-6 rounded-2xl flex flex-col justify-between">
            <div>
              <h4 className="text-base font-bold text-white mb-1">Key Player Attribute card</h4>
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
