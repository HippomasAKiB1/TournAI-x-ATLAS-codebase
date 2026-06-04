import {
  PredictionsResponse,
  SimulationsResponse,
  PlayersResponse,
  ExplanationsResponse,
  ModelComparisonResponse,
  GroupStandingsResponse,
  InjuryScenario
} from '../types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

async function fetchWithFallback<T>(apiPath: string, staticPath: string): Promise<T> {
  try {
    const response = await fetch(`${API_BASE_URL}${apiPath}`);
    if (response.ok) {
      return await response.json() as T;
    }
  } catch (err) {
    console.warn(`Backend API not reachable at ${API_BASE_URL}${apiPath}. Falling back to static file.`, err);
  }
  
  // Fallback to static JSON file in public folder
  const response = await fetch(staticPath);
  if (!response.ok) {
    throw new Error(`Failed to fetch static fallback from ${staticPath}: ${response.statusText}`);
  }
  return response.json() as T;
}

export async function getPredictions(): Promise<PredictionsResponse> {
  return fetchWithFallback<PredictionsResponse>('/predictions', '/data/predictions.json');
}

export async function getSimulations(): Promise<SimulationsResponse> {
  return fetchWithFallback<SimulationsResponse>('/simulations', '/data/simulations.json');
}

export async function getPlayers(): Promise<PlayersResponse> {
  return fetchWithFallback<PlayersResponse>('/players', '/data/players.json');
}

export async function getExplanations(): Promise<ExplanationsResponse> {
  return fetchWithFallback<ExplanationsResponse>('/explanations', '/data/explanations.json');
}

export async function getModelComparison(): Promise<ModelComparisonResponse> {
  return fetchWithFallback<ModelComparisonResponse>('/model_comparison', '/data/model_comparison.json');
}

export async function getGroupStandings(): Promise<GroupStandingsResponse> {
  return fetchWithFallback<GroupStandingsResponse>('/group_standings', '/data/group_standings.json');
}

export async function getInjuries(): Promise<InjuryScenario[]> {
  return fetchWithFallback<InjuryScenario[]>('/injuries', '/data/injuries.json');
}

export async function predictCustomMatch(homeTeam: string, awayTeam: string): Promise<any> {
  try {
    const response = await fetch(`${API_BASE_URL}/predict`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ home_team: homeTeam, away_team: awayTeam }),
    });
    if (response.ok) {
      return await response.json();
    }
  } catch (err) {
    console.warn(`Backend custom prediction failed. Falling back to client calculation.`, err);
  }
  return null; // Return null so the client knows to run local fallback calculation
}

export async function getBracketProbabilities(): Promise<any> {
  return fetchWithFallback<any>('/tracker/bracket', '/data/bracket.json');
}

export async function getQualificationProbabilities(): Promise<any> {
  return fetchWithFallback<any>('/tracker/qualification', '/data/qualification.json');
}

export async function runWhatIfSimulation(team: string, strengthDropPct: number, playerName?: string): Promise<any> {
  try {
    const response = await fetch(`${API_BASE_URL}/simulate/whatif`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ team, strength_drop_pct: strengthDropPct, player_name: playerName }),
    });
    if (response.ok) {
      return await response.json();
    }
  } catch (err) {
    console.warn(`Backend what-if simulation failed.`, err);
  }
  return null;
}

export async function getLatestShift(): Promise<any> {
  try {
    const response = await fetch(`${API_BASE_URL}/latest_shift`);
    if (response.ok) {
      return await response.json();
    }
  } catch (err) {
    console.warn(`Backend latest_shift failed. Returning fallback description.`, err);
  }
  return {
    shift_narrative: "No matches have been ingested yet. All 72 group stage matches are currently simulated baselines. Use the Live Ingestion Control panel below to ingest actual scores and see real-time probability shifts!"
  };
}

export async function getPipelineStatus(): Promise<any> {
  try {
    const response = await fetch(`${API_BASE_URL}/pipeline/status`);
    if (response.ok) {
      return await response.json();
    }
  } catch (err) {
    console.warn(`Backend pipeline status failed.`, err);
  }
  return { status: 'idle', last_run_time: null, error: null };
}

export async function getDbMatches(): Promise<any[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/matches`);
    if (response.ok) {
      return await response.json();
    }
  } catch (err) {
    console.warn(`Backend getDbMatches failed.`, err);
  }
  return [];
}

export async function ingestMatch(homeTeam: string, awayTeam: string, homeScore: number, awayScore: number, stage: string = 'Group Stage', secretKey: string = 'atlas-admin-secret-key-2026'): Promise<any> {
  try {
    const response = await fetch(`${API_BASE_URL}/ingest`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-ATLAS-KEY': secretKey
      },
      body: JSON.stringify({
        home_team: homeTeam,
        away_team: awayTeam,
        home_score: homeScore,
        away_score: awayScore,
        stage: stage
      }),
    });
    return await response.json();
  } catch (err) {
    console.error('Failed to ingest match', err);
    throw err;
  }
}
