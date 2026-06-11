"use client";

import React, { useState } from "react";
import { useTournament } from "../../context/TournamentContext";
import {
  Trophy,
  Grid,
  Info,
  Loader2
} from "lucide-react";

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

export default function BracketPage() {
  const { 
    loading, 
    groupStandings, 
    bracket, 
    simulations 
  } = useTournament();

  const [subTab, setSubTab] = useState<'groups' | 'bracket'>('groups');
  
  if (loading || !groupStandings || !bracket || !simulations) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center py-20">
        <Loader2 className="h-10 w-10 animate-spin text-cyan-400 mb-4" />
        <p className="text-sm text-zinc-400 font-medium">Loading Simulations & Tournament Bracket...</p>
      </div>
    );
  }

  const groupsList = Object.keys(groupStandings).sort((a, b) => a.localeCompare(b));
  // Default selected group
  const [selectedGroup, setSelectedGroup] = useState<string>(groupsList[0] || "Group A");
  const currentGroupData = groupStandings[selectedGroup] || [];

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-6">
      
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white flex items-center gap-2">
            <Grid className="h-8 w-8 text-cyan-400" /> Standings & Bracket Tracker
          </h1>
          <p className="text-sm text-zinc-400 mt-1">
            Observe real-time group placements and simulated advancement paths.
          </p>
        </div>

        {/* View Toggle tabs */}
        <div className="flex bg-zinc-950/60 p-1 border border-zinc-800 rounded-xl max-w-sm shrink-0">
          <button
            onClick={() => setSubTab('groups')}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ${
              subTab === 'groups'
                ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 font-bold"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            Group Standings
          </button>
          <button
            onClick={() => setSubTab('bracket')}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ${
              subTab === 'bracket'
                ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 font-bold"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            Knockout Bracket
          </button>
        </div>
      </div>

      {subTab === 'groups' ? (
        <div className="space-y-6">
          {/* Selectable Groups Row */}
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-12 gap-2">
            {groupsList.map((group) => {
              const letter = group.replace("Group ", "");
              const isSelected = selectedGroup === group;
              return (
                <button
                  key={group}
                  onClick={() => setSelectedGroup(group)}
                  className={`py-2 px-1 text-center font-mono font-bold text-xs rounded-lg transition-all cursor-pointer ${
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

          {/* Group Table Card */}
          <div className="glass-card rounded-2xl overflow-hidden">
            <div className="p-6 border-b border-zinc-800 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-white">{selectedGroup} Standings</h3>
                <p className="text-xs text-zinc-400">Chances calculated via 10,000 Monte Carlo simulator iterations.</p>
              </div>
              <span className="px-3 py-1 bg-zinc-900 border border-zinc-800 text-zinc-500 font-mono text-[10px] uppercase rounded-full select-none">
                Live Table
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-zinc-950/40 border-b border-zinc-800 text-zinc-500 font-mono uppercase">
                    <th className="py-4 px-6 text-center w-16">Rank</th>
                    <th className="py-4 px-4 font-semibold">Team</th>
                    <th className="py-4 px-4 text-center">MP</th>
                    <th className="py-4 px-4 text-center">W</th>
                    <th className="py-4 px-4 text-center">D</th>
                    <th className="py-4 px-4 text-center">L</th>
                    <th className="py-4 px-4 text-center">GF</th>
                    <th className="py-4 px-4 text-center">GA</th>
                    <th className="py-4 px-4 text-center">GD</th>
                    <th className="py-4 px-4 text-center">Pts</th>
                    <th className="py-4 px-4 text-center">Group Outcomes Projections</th>
                    <th className="py-4 px-6 text-center">Advancement Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-900 text-zinc-300">
                  {currentGroupData.map((team) => {
                    const gdSign = team.GD > 0 ? `+${team.GD}` : team.GD;
                    const simRow = simulations.results.find(r => r.Team.toLowerCase() === team.Team.toLowerCase());
                    const r32Pct = simRow ? simRow["Round of 32 %"] : 0.0;

                    // Advancement color indicator
                    let statusLabel = "Eliminated";
                    let statusColor = "bg-rose-950/30 text-rose-400 border border-rose-800/40";
                    if (team.Qualifies === "Yes") {
                      statusLabel = "Qualified";
                      statusColor = "bg-emerald-950/30 text-emerald-400 border border-emerald-800/40";
                    } else if (team.Qualifies?.includes("Maybe")) {
                      statusLabel = "3rd Place Playoff";
                      statusColor = "bg-amber-950/30 text-amber-400 border border-amber-800/40";
                    }

                    return (
                      <tr key={team.Team} className="hover:bg-zinc-900/10 transition">
                        <td className="py-4 px-6 text-center font-mono font-extrabold text-zinc-400">{team.Position}</td>
                        <td className="py-4 px-4 font-bold text-white text-sm flex items-center gap-2">
                          {FLAG_MAP[team.Team] ? (
                            <img src={FLAG_MAP[team.Team]} alt={team.Team} className="h-4 w-5 object-contain rounded-sm" />
                          ) : (
                            <span>🏳️</span>
                          )}
                          <span>{team.Team}</span>
                        </td>
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
                            <span className="px-2 py-0.5 rounded bg-cyan-950/40 border border-cyan-800/30 text-cyan-400">First: {r32Pct.toFixed(0)}%</span>
                          </div>
                        </td>
                        <td className="py-4 px-6 text-center">
                          <span className={`px-2.5 py-1 text-[10px] font-bold rounded-full ${statusColor}`}>
                            {statusLabel}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        /* Interactive Bracket Tree */
        <div className="glass-card p-6 rounded-2xl space-y-6">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Trophy className="w-5 h-5 text-amber-400 animate-pulse" /> Knockout Stage Projections
              </h3>
              <p className="text-xs text-zinc-400">Projected winners lock dynamically as matches complete.</p>
            </div>
            <span className="text-[10px] font-mono text-zinc-500 bg-zinc-900 border border-zinc-800 px-3 py-1 rounded-full uppercase">
              Swipe/Scroll Horizontally
            </span>
          </div>

          <div className="w-full overflow-x-auto pb-6 scrollbar-thin scrollbar-thumb-zinc-800">
            <div className="flex gap-8 p-2 min-w-[1500px] justify-between items-stretch">
              
              {/* Round of 32 */}
              <div className="flex flex-col justify-around py-2 space-y-4 w-64 shrink-0">
                <h4 className="text-xs font-bold font-mono tracking-wider text-zinc-500 text-center uppercase border-b border-zinc-900 pb-2 mb-2">Round of 32</h4>
                {bracket.r32?.map((match: any) => (
                  <BracketMatchCard key={match.match_id} match={match} />
                ))}
              </div>

              {/* Round of 16 */}
              <div className="flex flex-col justify-around py-2 space-y-4 w-64 shrink-0">
                <h4 className="text-xs font-bold font-mono tracking-wider text-zinc-500 text-center uppercase border-b border-zinc-900 pb-2 mb-2">Round of 16</h4>
                {bracket.r16?.map((match: any) => (
                  <BracketMatchCard key={match.match_id} match={match} />
                ))}
              </div>

              {/* Quarter Finals */}
              <div className="flex flex-col justify-around py-2 space-y-4 w-64 shrink-0">
                <h4 className="text-xs font-bold font-mono tracking-wider text-zinc-500 text-center uppercase border-b border-zinc-900 pb-2 mb-2">Quarter-Finals</h4>
                {bracket.qf?.map((match: any) => (
                  <BracketMatchCard key={match.match_id} match={match} />
                ))}
              </div>

              {/* Semi Finals */}
              <div className="flex flex-col justify-around py-2 space-y-4 w-64 shrink-0">
                <h4 className="text-xs font-bold font-mono tracking-wider text-zinc-500 text-center uppercase border-b border-zinc-900 pb-2 mb-2">Semi-Finals</h4>
                {bracket.sf?.map((match: any) => (
                  <BracketMatchCard key={match.match_id} match={match} />
                ))}
              </div>

              {/* Final */}
              <div className="flex flex-col justify-around py-2 space-y-4 w-64 shrink-0">
                <h4 className="text-xs font-bold font-mono tracking-wider text-zinc-500 text-center uppercase border-b border-zinc-900 pb-2 mb-2">Final</h4>
                {bracket.final?.map((match: any) => (
                  <BracketMatchCard key={match.match_id} match={match} />
                ))}
              </div>

              {/* Projected Champion */}
              <div className="flex flex-col justify-center py-2 w-64 shrink-0">
                <h4 className="text-xs font-bold font-mono tracking-wider text-zinc-500 text-center uppercase border-b border-zinc-900 pb-2 mb-2">Projected Champion</h4>
                {bracket.final[0] && (() => {
                  const fMatch = bracket.final[0];
                  const homeBetter = fMatch.home_adv_prob >= fMatch.away_adv_prob;
                  const champName = homeBetter ? fMatch.home_team : fMatch.away_team;
                  const champProb = homeBetter ? fMatch.home_adv_prob : fMatch.away_adv_prob;
                  return (
                    <div className="glass-card p-6 rounded-2xl border-2 border-amber-500/40 bg-gradient-to-br from-amber-950/20 to-yellow-950/10 text-center shadow-lg relative overflow-hidden py-10">
                      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-amber-500 to-yellow-300"></div>
                      <div className="relative flex justify-center items-center mb-4">
                        <Trophy className="w-12 h-12 text-amber-400 animate-pulse z-10" />
                        {FLAG_MAP[champName] && (
                          <img src={FLAG_MAP[champName]} alt={champName} className="absolute h-10 w-12 object-contain opacity-25 rounded-md" />
                        )}
                      </div>
                      <h5 className="text-lg font-extrabold text-white tracking-tight uppercase leading-none">{champName}</h5>
                      <span className="text-[10px] text-zinc-500 font-mono tracking-widest uppercase block mt-2">Projected Winner</span>
                      <div className="mt-4 px-4 py-1.5 bg-amber-500/20 border border-amber-500/30 text-amber-300 rounded-full inline-block font-mono text-xs font-bold">
                        {champProb?.toFixed(1)}% Championship Probability
                      </div>
                    </div>
                  );
                })()}
              </div>

            </div>
          </div>
        </div>
      )}

      {/* Info Warning Banner */}
      <div className="flex gap-3 p-4 bg-zinc-900/30 border border-zinc-800/60 rounded-2xl text-xs text-zinc-400 items-start">
        <Info className="w-4.5 h-4.5 text-cyan-400 shrink-0 mt-0.5" />
        <div>
          <p className="font-semibold text-zinc-300 mb-0.5">FIFA World Cup 2026 Format Rules</p>
          <p>
            The tournament features 48 nations split into 12 groups of 4. The top 2 teams in each group automatically advance, joined by the 8 highest-ranked 3rd place teams, forming the Round of 32 knockout grid.
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
    <div className="glass-card p-3.5 rounded-xl border border-zinc-800/80 bg-zinc-950/40 w-64 shadow-lg hover:border-cyan-500/30 transition-all duration-200">
      <div className="text-[9px] font-mono text-zinc-500 mb-1.5 flex justify-between">
        <span>Match {match.match_id}</span>
        {isCompleted ? (
          <span className="text-emerald-400 font-bold uppercase tracking-wider text-[8px] bg-emerald-950/20 border border-emerald-900/45 px-1.5 py-0.5 rounded">FT</span>
        ) : (
          <span className="text-cyan-400/80">Slot Win %</span>
        )}
      </div>
      <div className="space-y-1.5 text-xs">
        
        {/* Home Team */}
        <div className={`flex items-center justify-between p-1.5 rounded ${homeBetter ? 'bg-purple-950/20 text-purple-200 font-semibold' : 'text-zinc-400'}`}>
          <div className="flex items-center gap-1.5 truncate">
            {FLAG_MAP[match.home_team] ? (
              <img src={FLAG_MAP[match.home_team]} alt={match.home_team} className="h-3.5 w-4.5 object-contain rounded-sm shrink-0" />
            ) : (
              <span className={`w-1.5 h-1.5 rounded-full ${homeBetter ? 'bg-purple-500' : 'bg-zinc-700'}`}></span>
            )}
            <span className="truncate">{match.home_team}</span>
            {!isCompleted && <span className="text-[9px] text-zinc-600 font-mono">({match.home_prob?.toFixed(0)}%)</span>}
          </div>
          {isCompleted ? (
            <span className="font-mono font-bold text-white text-xs bg-zinc-900 px-2 py-0.5 rounded border border-zinc-800">{match.home_score}</span>
          ) : (
            <span className="font-mono text-purple-400">{match.home_adv_prob?.toFixed(0)}%</span>
          )}
        </div>
        
        {/* Away Team */}
        <div className={`flex items-center justify-between p-1.5 rounded ${!homeBetter ? 'bg-cyan-950/20 text-cyan-200 font-semibold' : 'text-zinc-400'}`}>
          <div className="flex items-center gap-1.5 truncate">
            {FLAG_MAP[match.away_team] ? (
              <img src={FLAG_MAP[match.away_team]} alt={match.away_team} className="h-3.5 w-4.5 object-contain rounded-sm shrink-0" />
            ) : (
              <span className={`w-1.5 h-1.5 rounded-full ${!homeBetter ? 'bg-cyan-500' : 'bg-zinc-700'}`}></span>
            )}
            <span className="truncate">{match.away_team}</span>
            {!isCompleted && <span className="text-[9px] text-zinc-600 font-mono">({match.away_prob?.toFixed(0)}%)</span>}
          </div>
          {isCompleted ? (
            <span className="font-mono font-bold text-white text-xs bg-zinc-900 px-2 py-0.5 rounded border border-zinc-800">{match.away_score}</span>
          ) : (
            <span className="font-mono text-cyan-400">{match.away_adv_prob?.toFixed(0)}%</span>
          )}
        </div>

      </div>
    </div>
  );
}
