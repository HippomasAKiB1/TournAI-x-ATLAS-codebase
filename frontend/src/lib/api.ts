import {
  PredictionsResponse,
  SimulationsResponse,
  PlayersResponse,
  ExplanationsResponse,
  ModelComparisonResponse,
  GroupStandingsResponse,
  InjuryScenario
} from '../types';

async function fetchJSON<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch static data from ${url}: ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export async function getPredictions(): Promise<PredictionsResponse> {
  return fetchJSON<PredictionsResponse>('/data/predictions.json');
}

export async function getSimulations(): Promise<SimulationsResponse> {
  return fetchJSON<SimulationsResponse>('/data/simulations.json');
}

export async function getPlayers(): Promise<PlayersResponse> {
  return fetchJSON<PlayersResponse>('/data/players.json');
}

export async function getExplanations(): Promise<ExplanationsResponse> {
  return fetchJSON<ExplanationsResponse>('/data/explanations.json');
}

export async function getModelComparison(): Promise<ModelComparisonResponse> {
  return fetchJSON<ModelComparisonResponse>('/data/model_comparison.json');
}

export async function getGroupStandings(): Promise<GroupStandingsResponse> {
  return fetchJSON<GroupStandingsResponse>('/data/group_standings.json');
}

export async function getInjuries(): Promise<InjuryScenario[]> {
  return fetchJSON<InjuryScenario[]>('/data/injuries.json');
}
