"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { 
  PredictionsResponse, 
  SimulationsResponse, 
  PlayersResponse, 
  GroupStandingsResponse, 
  InjuryScenario 
} from "../types";
import { 
  getPredictions, 
  getSimulations, 
  getPlayers, 
  getGroupStandings, 
  getLatestShift,
  getPipelineStatus,
  getBracketProbabilities
} from "../lib/api";

interface TournamentContextType {
  loading: boolean;
  error: string | null;
  predictions: PredictionsResponse | null;
  simulations: SimulationsResponse | null;
  players: PlayersResponse | null;
  groupStandings: GroupStandingsResponse | null;
  bracket: any;
  latestShift: any;
  pipelineStatus: any;
  activeInjuryPlayer: string | null;
  setActiveInjuryPlayer: (name: string | null) => void;
  refreshData: () => Promise<void>;
}

const TournamentContext = createContext<TournamentContextType | undefined>(undefined);

export function TournamentProvider({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // States
  const [predictions, setPredictions] = useState<PredictionsResponse | null>(null);
  const [simulations, setSimulations] = useState<SimulationsResponse | null>(null);
  const [players, setPlayers] = useState<PlayersResponse | null>(null);
  const [groupStandings, setGroupStandings] = useState<GroupStandingsResponse | null>(null);
  const [bracket, setBracket] = useState<any>(null);
  const [latestShift, setLatestShift] = useState<any>(null);
  const [pipelineStatus, setPipelineStatus] = useState<any>({ status: "idle" });

  const [activeInjuryPlayer, setActiveInjuryPlayer] = useState<string | null>(null);

  const loadData = async () => {
    try {
      const [
        predData,
        simData,
        playerData,
        standingsData,
        bracketData,
        shiftData,
        statusData
      ] = await Promise.all([
        getPredictions(),
        getSimulations(),
        getPlayers(),
        getGroupStandings(),
        getBracketProbabilities(),
        getLatestShift(),
        getPipelineStatus()
      ]);

      setPredictions(predData);
      setSimulations(simData);
      setPlayers(playerData);
      setGroupStandings(standingsData);
      setBracket(bracketData);
      setLatestShift(shiftData);
      setPipelineStatus(statusData);
      setError(null);
    } catch (err: any) {
      console.error("Error loading tournament context data:", err);
      setError("Failed to sync tournament analytics. Operating on client-side cache fallback.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();

    // Setup SSE connection
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
    const sseUrl = `${API_BASE}/sse/pipeline`;
    let eventSource: EventSource | null = null;

    try {
      console.log("Connecting to SSE live updates at:", sseUrl);
      eventSource = new EventSource(sseUrl);

      eventSource.onmessage = (event) => {
        try {
          const update = JSON.parse(event.data);
          if (update.event === "pipeline_complete") {
            console.log("SSE update: Pipeline complete. Refreshing data...");
            loadData();
          }
        } catch (e) {
          console.error("Error parsing SSE event data:", e);
        }
      };

      eventSource.onerror = (err) => {
        console.warn("SSE connection error, fallback to periodic polling.", err);
        if (eventSource) {
          eventSource.close();
        }
      };
    } catch (e) {
      console.warn("EventSource init failed. Falling back to simple intervals.", e);
    }

    // Polling fallback check every 30 seconds
    const interval = setInterval(async () => {
      try {
        const freshStatus = await getPipelineStatus();
        setPipelineStatus(freshStatus);
        
        if (freshStatus.status === "idle" && freshStatus.last_run_time) {
          loadData();
        }
      } catch (err) {
        console.warn("Polling status failed:", err);
      }
    }, 30000);

    return () => {
      if (eventSource) {
        eventSource.close();
      }
      clearInterval(interval);
    };
  }, []);

  return (
    <TournamentContext.Provider
      value={{
        loading,
        error,
        predictions,
        simulations,
        players,
        groupStandings,
        bracket,
        latestShift,
        pipelineStatus,
        activeInjuryPlayer,
        setActiveInjuryPlayer,
        refreshData: loadData
      }}
    >
      {children}
    </TournamentContext.Provider>
  );
}

export function useTournament() {
  const context = useContext(TournamentContext);
  if (context === undefined) {
    throw new Error("useTournament must be used within a TournamentProvider");
  }
  return context;
}
