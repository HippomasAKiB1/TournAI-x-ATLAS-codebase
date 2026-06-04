import pandas as pd
import numpy as np

def aggregate_team_strength(df_players_with_impact: pd.DataFrame, df_team_strength: pd.DataFrame) -> pd.DataFrame:
    """Aggregate individual player scores into team-level profiles and merge with team Elo ratings."""
    # Compute aggregate team metrics from players
    team_metrics = df_players_with_impact.groupby('team').agg(
        avg_impact=('impact_score', 'mean'),
        max_impact=('impact_score', 'max'),
        squad_size=('player_id', 'count'),
        top5_avg=('impact_score', lambda x: x.nlargest(5).mean() if len(x) >= 5 else x.mean()),
        depth=('impact_score', lambda x: x.nlargest(11).mean() - x.nsmallest(max(1, len(x)-11)).mean() if len(x) > 11 else 0.0),
    ).round(2)
    
    # Merge with team Elo ratings and form from wc2026_team_strength.csv
    team_strength = team_metrics.merge(
        df_team_strength[['team', 'current_elo', 'form_10']],
        on='team', how='left'
    )
    
    # Sort teams by their average player impact
    team_strength = team_strength.sort_values('avg_impact', ascending=False)
    
    return team_strength
