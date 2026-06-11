"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getApiBaseUrl } from "../../lib/config";
import { 
  Trophy, 
  User, 
  LogOut, 
  CheckCircle2, 
  Calendar, 
  Sparkles, 
  ArrowLeft, 
  Loader2, 
  AlertCircle,
  HelpCircle,
  Clock,
  ChevronRight
} from "lucide-react";

interface DBModelMatch {
  id: number;
  home_team: string;
  away_team: string;
  home_score: number | null;
  away_score: number | null;
  stage: string;
  status: 'scheduled' | 'completed';
  date: string | null;
}

interface UserPredictionResponse {
  id: number;
  user_id: number;
  match_id: number;
  predicted_home_score: number;
  predicted_away_score: number;
  points_earned: number;
}

interface LeaderboardRow {
  username: string;
  total_predictions: number;
  total_points: number;
}

export default function CompetitionPage() {
  const router = useRouter();
  
  // Auth state
  const [token, setToken] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<string | null>(null);
  
  // Data states
  const [matches, setMatches] = useState<DBModelMatch[]>([]);
  const [myPredictions, setMyPredictions] = useState<UserPredictionResponse[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderboardRow[]>([]);
  
  // Interactive UI states
  const [activeSubTab, setActiveSubTab] = useState<'predict' | 'leaderboard'>('predict');
  const [loading, setLoading] = useState(true);
  const [submitLoading, setSubmitLoading] = useState<Record<number, boolean>>({});
  const [predictInputs, setPredictInputs] = useState<Record<number, { home: string; away: string }>>({});
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const API_BASE = getApiBaseUrl();

  // Check auth and load data
  useEffect(() => {
    const storedToken = localStorage.getItem("token");
    const storedUsername = localStorage.getItem("username");
    
    if (!storedToken) {
      router.push("/auth");
      return;
    }
    
    setToken(storedToken);
    setCurrentUser(storedUsername);
    
    loadDashboardData(storedToken);
  }, [router]);

  const loadDashboardData = async (authToken: string) => {
    setLoading(true);
    setError(null);
    try {
      // 1. Fetch matches
      const matchesRes = await fetch(`${API_BASE}/matches`);
      if (!matchesRes.ok) throw new Error("Failed to load match fixtures");
      const matchesData = await matchesRes.json();
      setMatches(matchesData);
      
      // 2. Fetch my predictions
      const predictionsRes = await fetch(`${API_BASE}/predictions/my`, {
        headers: {
          "Authorization": `Bearer ${authToken}`
        }
      });
      if (!predictionsRes.ok) throw new Error("Failed to load user predictions");
      const predictionsData = await predictionsRes.json();
      setMyPredictions(predictionsData);
      
      // 3. Initialize prediction inputs from existing submissions
      const inputs: Record<number, { home: string; away: string }> = {};
      predictionsData.forEach((pred: UserPredictionResponse) => {
        inputs[pred.match_id] = {
          home: String(pred.predicted_home_score),
          away: String(pred.predicted_away_score)
        };
      });
      setPredictInputs(inputs);
      
      // 4. Fetch leaderboard
      const leaderboardRes = await fetch(`${API_BASE}/competition/leaderboard`);
      if (!leaderboardRes.ok) throw new Error("Failed to load leaderboard");
      const leaderboardData = await leaderboardRes.json();
      setLeaderboard(leaderboardData);
      
    } catch (err) {
      console.error(err);
      setError("Failed to load competition data. Ensure the FastAPI backend is running.");
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (matchId: number, team: 'home' | 'away', val: string) => {
    // Only allow digits
    const cleaned = val.replace(/\D/g, "");
    setPredictInputs(prev => ({
      ...prev,
      [matchId]: {
        ...prev[matchId],
        [team]: cleaned
      }
    }));
  };

  const handlePredictionSubmit = async (matchId: number) => {
    const input = predictInputs[matchId];
    if (!input || input.home === "" || input.away === "") {
      setError("Please fill in both scores before submitting.");
      return;
    }
    
    setError(null);
    setSuccessMsg(null);
    setSubmitLoading(prev => ({ ...prev, [matchId]: true }));
    
    try {
      const res = await fetch(`${API_BASE}/predictions/submit`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          match_id: matchId,
          predicted_home_score: parseInt(input.home, 10),
          predicted_away_score: parseInt(input.away, 10)
        })
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || "Submission failed");
      }
      
      setSuccessMsg("Prediction recorded!");
      
      // Update my predictions local state
      setMyPredictions(prev => {
        const filtered = prev.filter(p => p.match_id !== matchId);
        return [...filtered, data];
      });
      
      // Reload leaderboard to reflect any new prediction stats
      const leaderboardRes = await fetch(`${API_BASE}/competition/leaderboard`);
      if (leaderboardRes.ok) {
        const leaderboardData = await leaderboardRes.json();
        setLeaderboard(leaderboardData);
      }
      
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error submitting prediction");
    } finally {
      setSubmitLoading(prev => ({ ...prev, [matchId]: false }));
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    router.push("/auth");
  };

  // Find user's score summary
  const myTotalPredictions = myPredictions.length;
  const myTotalPoints = myPredictions.reduce((sum, p) => sum + p.points_earned, 0);
  const myRank = leaderboard.findIndex(row => row.username === currentUser) + 1;

  // Filter matches into upcoming/completed
  const upcomingMatches = matches.filter(m => m.status === 'scheduled');
  const completedMatches = matches.filter(m => m.status === 'completed');

  if (loading) {
    return (
      <div className="flex flex-col flex-1 items-center justify-center min-h-screen bg-[#030308]">
        <div className="relative flex flex-col items-center">
          <Loader2 className="w-12 h-12 text-cyan-400 animate-spin mb-4" />
          <h2 className="text-xl font-semibold text-zinc-300 tracking-wider">Loading League...</h2>
          <p className="text-sm text-zinc-500 mt-2 font-mono">Syncing Database with ATLAS engine...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col lg:flex-row bg-[#030308] cyber-grid">
      {/* Sidebar Layout */}
      <aside className="w-full lg:w-72 bg-zinc-950/80 border-b lg:border-b-0 lg:border-r border-zinc-800/80 backdrop-blur-xl flex flex-col z-10">
        <div className="p-6 border-b border-zinc-800/80 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-purple-600 to-cyan-400 flex items-center justify-center font-bold text-white shadow-lg shadow-purple-500/20">
              A
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight bg-gradient-to-r from-white to-zinc-400 bg-clip-text text-transparent">
                ATLAS LEAGUE
              </h1>
              <span className="text-xs text-purple-400 font-mono tracking-widest block uppercase">
                Prediction arena
              </span>
            </div>
          </div>
        </div>

        {/* Sidebar Nav */}
        <nav className="flex-1 p-4 space-y-1.5">
          <button
            onClick={() => router.push("/")}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/50 border border-transparent transition-all"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Live Dashboard
          </button>
          
          <button
            onClick={() => setActiveSubTab('predict')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
              activeSubTab === 'predict'
                ? "bg-gradient-to-r from-purple-900/40 to-cyan-900/40 text-cyan-300 border border-cyan-500/30 text-glow-cyan"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/50 border border-transparent"
            }`}
          >
            <Trophy className="w-4 h-4 text-cyan-400" />
            Predict Fixtures
          </button>

          <button
            onClick={() => setActiveSubTab('leaderboard')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
              activeSubTab === 'leaderboard'
                ? "bg-gradient-to-r from-purple-900/40 to-cyan-900/40 text-cyan-300 border border-cyan-500/30 text-glow-cyan"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/50 border border-transparent"
            }`}
          >
            <User className="w-4 h-4 text-cyan-400" />
            Global Standings
          </button>
        </nav>

        {/* User profile section */}
        <div className="p-5 border-t border-zinc-800/80 bg-zinc-950/40 flex flex-col gap-3">
          <div className="flex items-center gap-3 p-3 rounded-xl bg-zinc-900/50 border border-zinc-800">
            <div className="w-8 h-8 rounded-full bg-cyan-900/50 border border-cyan-500/30 flex items-center justify-center font-bold text-cyan-400 uppercase">
              {currentUser ? currentUser.substring(0, 2) : "FN"}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold text-zinc-300 truncate">@{currentUser}</p>
              <p className="text-[10px] text-zinc-500 font-mono">Fan Competitor</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full py-2.5 rounded-xl border border-zinc-800 hover:border-rose-900/50 hover:bg-rose-950/15 text-zinc-400 hover:text-rose-400 text-xs font-medium transition-all flex items-center justify-center gap-2"
          >
            <LogOut className="w-3.5 h-3.5" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 p-4 lg:p-8 overflow-y-auto max-h-screen relative z-10">
        
        {/* Greetings and Score Summary Cards */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 mb-8">
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              Welcome, <span className="text-cyan-400">@{currentUser}</span>!
              <Sparkles className="w-5 h-5 text-purple-400 animate-pulse" />
            </h2>
            <p className="text-sm text-zinc-400 mt-1">Submit predictions, score points, and conquer the global leaderboard.</p>
          </div>

          <div className="grid grid-cols-3 gap-4 shrink-0">
            <div className="bg-zinc-950/60 border border-zinc-800 rounded-xl p-3.5 text-center min-w-28">
              <span className="text-[10px] font-mono text-zinc-500 uppercase block tracking-wider">Points</span>
              <span className="text-2xl font-black text-white">{myTotalPoints}</span>
            </div>
            <div className="bg-zinc-950/60 border border-zinc-800 rounded-xl p-3.5 text-center min-w-28">
              <span className="text-[10px] font-mono text-zinc-500 uppercase block tracking-wider">Guessed</span>
              <span className="text-2xl font-black text-cyan-400">{myTotalPredictions}</span>
            </div>
            <div className="bg-zinc-950/60 border border-zinc-800 rounded-xl p-3.5 text-center min-w-28">
              <span className="text-[10px] font-mono text-zinc-500 uppercase block tracking-wider">Rank</span>
              <span className="text-2xl font-black text-purple-400">{myRank > 0 ? `#${myRank}` : "N/A"}</span>
            </div>
          </div>
        </div>

        {/* Message Alerts */}
        {error && (
          <div className="mb-6 flex items-start gap-3 p-4 rounded-xl bg-rose-950/20 border border-rose-800/30 text-rose-300 text-sm">
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div className="mb-6 flex items-start gap-3 p-4 rounded-xl bg-emerald-950/20 border border-emerald-800/30 text-emerald-300 text-sm">
            <CheckCircle2 className="w-5 h-5 shrink-0 mt-0.5" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Tab Selection */}
        {activeSubTab === 'predict' ? (
          <div className="space-y-8">
            
            {/* Scoring guide alert */}
            <div className="p-4 rounded-xl bg-purple-950/15 border border-purple-800/30 flex items-start gap-3.5">
              <HelpCircle className="w-5 h-5 text-purple-400 shrink-0 mt-0.5" />
              <div className="text-xs text-zinc-400">
                <strong className="text-zinc-200">How Scoring Works:</strong>
                <ul className="list-disc pl-4 mt-1.5 space-y-1">
                  <li><strong className="text-emerald-400">+3 Points</strong>: Guess the exact final score line (e.g. predicted 2-1, final score 2-1).</li>
                  <li><strong className="text-cyan-400">+1 Point</strong>: Guess the correct outcome (Win/Loss/Draw) but not the exact score.</li>
                  <li><strong className="text-zinc-500">0 Points</strong>: Incorrect prediction outcome.</li>
                </ul>
              </div>
            </div>

            {/* Upcoming fixtures section */}
            <div>
              <h3 className="text-sm font-mono uppercase tracking-wider text-zinc-400 mb-4 flex items-center gap-2">
                <Clock className="w-4 h-4 text-cyan-400" />
                Fixtures to Predict ({upcomingMatches.length})
              </h3>
              
              {upcomingMatches.length === 0 ? (
                <div className="border border-zinc-800/50 bg-zinc-950/20 rounded-2xl p-12 text-center text-zinc-500 text-sm">
                  All match fixtures are completed or no fixtures found.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {upcomingMatches.map((match) => {
                    const existing = myPredictions.find(p => p.match_id === match.id);
                    const input = predictInputs[match.id] || { home: "", away: "" };
                    const isSubmitting = submitLoading[match.id] || false;
                    
                    return (
                      <div 
                        key={match.id} 
                        className="bg-zinc-950/50 border border-zinc-800/80 hover:border-zinc-700/80 rounded-2xl p-5 backdrop-blur-sm transition-all duration-300 relative group overflow-hidden"
                      >
                        {/* Top Line accent */}
                        {existing && (
                          <div className="absolute top-0 left-0 right-0 h-[1.5px] bg-cyan-500/50"></div>
                        )}
                        
                        <div className="flex items-center justify-between text-[10px] font-mono text-zinc-500 mb-4">
                          <span className="uppercase tracking-wider">Fixture #{match.id}</span>
                          <span className="flex items-center gap-1.5">
                            <Calendar className="w-3.5 h-3.5" />
                            {match.date || "TBD"}
                          </span>
                        </div>

                        <div className="grid grid-cols-7 items-center gap-2 my-2">
                          {/* Home team */}
                          <div className="col-span-2 text-right">
                            <p className="text-xs font-semibold text-zinc-300 uppercase tracking-tight truncate">{match.home_team}</p>
                          </div>
                          
                          {/* Inputs / Versus */}
                          <div className="col-span-3 flex items-center justify-center gap-2 px-1">
                            <input
                              type="text"
                              value={input.home}
                              onChange={(e) => handleInputChange(match.id, 'home', e.target.value)}
                              placeholder="-"
                              maxLength={2}
                              disabled={isSubmitting}
                              className="w-10 h-10 rounded-xl bg-zinc-900 border border-zinc-800 text-center font-bold text-base text-white focus:outline-none focus:border-cyan-500/80 transition-colors"
                            />
                            <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">vs</span>
                            <input
                              type="text"
                              value={input.away}
                              onChange={(e) => handleInputChange(match.id, 'away', e.target.value)}
                              placeholder="-"
                              maxLength={2}
                              disabled={isSubmitting}
                              className="w-10 h-10 rounded-xl bg-zinc-900 border border-zinc-800 text-center font-bold text-base text-white focus:outline-none focus:border-cyan-500/80 transition-colors"
                            />
                          </div>
                          
                          {/* Away team */}
                          <div className="col-span-2 text-left">
                            <p className="text-xs font-semibold text-zinc-300 uppercase tracking-tight truncate">{match.away_team}</p>
                          </div>
                        </div>

                        {/* Submit Actions */}
                        <div className="mt-5 flex items-center justify-between pt-4 border-t border-zinc-900">
                          <div>
                            {existing ? (
                              <span className="text-[10px] font-mono text-emerald-400 flex items-center gap-1">
                                <CheckCircle2 className="w-3.5 h-3.5" />
                                Predicted: {existing.predicted_home_score} - {existing.predicted_away_score}
                              </span>
                            ) : (
                              <span className="text-[10px] font-mono text-zinc-500">
                                Not predicted yet
                              </span>
                            )}
                          </div>
                          
                          <button
                            onClick={() => handlePredictionSubmit(match.id)}
                            disabled={isSubmitting || input.home === "" || input.away === ""}
                            className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-all duration-300 disabled:opacity-30 disabled:pointer-events-none ${
                              existing 
                                ? "bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border border-zinc-800" 
                                : "bg-gradient-to-r from-purple-600 to-cyan-500 text-white shadow-md shadow-cyan-500/5 hover:shadow-cyan-500/15"
                            }`}
                          >
                            {isSubmitting ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            ) : existing ? (
                              "Update Guess"
                            ) : (
                              "Save Score"
                            )}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Completed predictions */}
            <div>
              <h3 className="text-sm font-mono uppercase tracking-wider text-zinc-400 mb-4 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Completed Match Results ({completedMatches.length})
              </h3>
              
              {completedMatches.length === 0 ? (
                <div className="border border-zinc-800/50 bg-zinc-950/20 rounded-2xl p-8 text-center text-zinc-500 text-sm">
                  No completed matches to show yet.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {completedMatches.map((match) => {
                    const prediction = myPredictions.find(p => p.match_id === match.id);
                    const gotExact = prediction?.points_earned === 3;
                    const gotOutcome = prediction?.points_earned === 1;
                    
                    let pointsBadgeColor = "bg-zinc-900 border-zinc-800 text-zinc-500";
                    let pointsLabel = "0 pts";
                    if (prediction) {
                      if (gotExact) {
                        pointsBadgeColor = "bg-emerald-950/30 border-emerald-500/20 text-emerald-400";
                        pointsLabel = "+3 pts (Exact)";
                      } else if (gotOutcome) {
                        pointsBadgeColor = "bg-cyan-950/30 border-cyan-500/20 text-cyan-400";
                        pointsLabel = "+1 pt (Outcome)";
                      }
                    } else {
                      pointsLabel = "No prediction";
                    }

                    return (
                      <div 
                        key={match.id}
                        className="bg-zinc-950/30 border border-zinc-900 rounded-2xl p-5"
                      >
                        <div className="flex items-center justify-between text-[10px] font-mono text-zinc-500 mb-4">
                          <span className="uppercase tracking-wider">Fixture #{match.id} (Finished)</span>
                          <span>{match.date || "TBD"}</span>
                        </div>

                        <div className="flex items-center justify-between my-2">
                          <div className="flex-1 text-right pr-4">
                            <span className="text-xs font-semibold text-zinc-300 uppercase tracking-tight">{match.home_team}</span>
                          </div>
                          
                          <div className="flex items-center gap-3 px-3 py-1 bg-zinc-900 border border-zinc-800/80 rounded-xl">
                            <span className="font-bold text-zinc-100">{match.home_score}</span>
                            <span className="text-[10px] text-zinc-600 font-bold uppercase">FT</span>
                            <span className="font-bold text-zinc-100">{match.away_score}</span>
                          </div>
                          
                          <div className="flex-1 text-left pl-4">
                            <span className="text-xs font-semibold text-zinc-300 uppercase tracking-tight">{match.away_team}</span>
                          </div>
                        </div>

                        <div className="mt-5 pt-3.5 border-t border-zinc-900 flex items-center justify-between">
                          <div className="text-[10px] font-mono text-zinc-500">
                            Your guess: {prediction ? `${prediction.predicted_home_score} - ${prediction.predicted_away_score}` : "None"}
                          </div>
                          
                          <div className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${pointsBadgeColor}`}>
                            {pointsLabel}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

          </div>
        ) : (
          /* Leaderboard Tab */
          <div className="bg-zinc-950/50 border border-zinc-800 rounded-2xl p-6 backdrop-blur-sm overflow-hidden">
            <div className="flex items-center gap-3 mb-6">
              <Trophy className="w-6 h-6 text-cyan-400" />
              <div>
                <h3 className="text-lg font-bold text-white uppercase tracking-tight">Global Leaderboard</h3>
                <p className="text-xs text-zinc-500 mt-0.5">Rankings of all fan participants based on total prediction points.</p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-zinc-800 text-[10px] font-mono text-zinc-500 uppercase tracking-wider">
                    <th className="py-4 px-4 font-normal">Rank</th>
                    <th className="py-4 px-4 font-normal">Username</th>
                    <th className="py-4 px-4 font-normal text-center">Predictions</th>
                    <th className="py-4 px-4 font-normal text-right">Total Points</th>
                  </tr>
                </thead>
                <tbody>
                  {leaderboard.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="py-8 text-center text-zinc-500 text-sm">
                        No scoreboard rankings compiled yet.
                      </td>
                    </tr>
                  ) : (
                    leaderboard.map((row, index) => {
                      const rank = index + 1;
                      const isMe = row.username === currentUser;
                      
                      // Trophy logic
                      let trophyIcon = null;
                      if (rank === 1) trophyIcon = <span className="text-yellow-500 text-lg mr-1">🏆</span>;
                      else if (rank === 2) trophyIcon = <span className="text-zinc-400 text-lg mr-1">🥈</span>;
                      else if (rank === 3) trophyIcon = <span className="text-amber-600 text-lg mr-1">🥉</span>;

                      return (
                        <tr 
                          key={row.username}
                          className={`border-b border-zinc-900 text-sm hover:bg-zinc-900/30 transition-all ${
                            isMe ? "bg-purple-950/10 text-cyan-300 font-semibold" : "text-zinc-400"
                          }`}
                        >
                          <td className="py-4 px-4 font-mono font-bold text-zinc-500">
                            {trophyIcon || `${rank}.`}
                          </td>
                          <td className="py-4 px-4 flex items-center gap-2">
                            <span>@{row.username}</span>
                            {isMe && (
                              <span className="text-[9px] font-mono font-extrabold uppercase px-1.5 py-0.5 rounded bg-cyan-950 border border-cyan-500/20 text-cyan-400">
                                You
                              </span>
                            )}
                          </td>
                          <td className="py-4 px-4 text-center font-mono">
                            {row.total_predictions}
                          </td>
                          <td className="py-4 px-4 text-right font-mono font-bold text-white">
                            {row.total_points} pts
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

      </main>
    </div>
  );
}
