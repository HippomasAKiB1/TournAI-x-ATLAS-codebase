import pandas as pd
import numpy as np

def simulate_injury_scenarios(df_players_with_impact: pd.DataFrame, top_n_players: int = 10) -> pd.DataFrame:
    """Simulate key player injuries to analyze their impact on team strength."""
    # Identify top players by impact score
    key_players = df_players_with_impact.nlargest(top_n_players, 'impact_score')
    injury_scenarios = []
    
    for _, player in key_players.iterrows():
        team = player['team']
        player_name = player['player_name']
        player_score = player['impact_score']
        
        # Calculate team average impact with and without the player
        team_players = df_players_with_impact[df_players_with_impact['team'] == team]
        team_avg_with = team_players['impact_score'].mean()
        
        team_players_without = team_players[team_players['player_name'] != player_name]
        if len(team_players_without) > 0:
            team_avg_without = team_players_without['impact_score'].mean()
        else:
            team_avg_without = 0.0
            
        pct_drop = ((team_avg_with - team_avg_without) / team_avg_with * 100.0) if team_avg_with > 0 else 0.0
        
        injury_scenarios.append({
            'Player': player_name,
            'Team': team,
            'Impact Score': player_score,
            'Team Avg (with)': round(team_avg_with, 2),
            'Team Avg (without)': round(team_avg_without, 2),
            'Strength Drop %': round(pct_drop, 2)
        })
        
    return pd.DataFrame(injury_scenarios)
