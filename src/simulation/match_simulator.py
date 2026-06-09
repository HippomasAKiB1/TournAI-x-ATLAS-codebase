import numpy as np

def simulate_match(home_probs) -> int:
    """Simulate a match given [loss_prob, draw_prob, win_prob] for the home team."""
    probs = np.array(home_probs, dtype=float)
    probs /= probs.sum()  # Normalize to ensure they sum to exactly 1.0
    return np.random.choice([0, 1, 2], p=probs)

def simulate_group(group_teams, fixture_probs, completed_matches=None) -> list:
    """Simulate group stage matches for a set of teams and return sorted standings."""
    if completed_matches is None:
        completed_matches = {}
    table = {t: {'Pts': 0, 'GD': 0, 'GF': 0} for t in group_teams}
    
    for (home, away), probs in fixture_probs.items():
        # Check if the match has an actual completed result
        # Try both perspectives
        actual_score = None
        key_h_a = (home.lower(), away.lower())
        key_a_h = (away.lower(), home.lower())
        
        if key_h_a in completed_matches:
            actual_score = completed_matches[key_h_a] # (home_score, away_score)
        elif key_a_h in completed_matches:
            score_a, score_h = completed_matches[key_a_h]
            actual_score = (score_h, score_a)
            
        if actual_score is not None:
            goals_h, goals_a = actual_score
            if goals_h > goals_a:
                table[home]['Pts'] += 3
            elif goals_h == goals_a:
                table[home]['Pts'] += 1
                table[away]['Pts'] += 1
            else:
                table[away]['Pts'] += 3
        else:
            result = simulate_match(probs)
            if result == 2:  # Home win
                table[home]['Pts'] += 3
                goals_h, goals_a = max(1, np.random.poisson(1.8)), np.random.poisson(0.8)
                if goals_h <= goals_a:
                    goals_h = goals_a + 1
            elif result == 1:  # Draw
                table[home]['Pts'] += 1
                table[away]['Pts'] += 1
                goals_h = goals_a = np.random.poisson(1.1)
            else:  # Away win
                table[away]['Pts'] += 3
                goals_a, goals_h = max(1, np.random.poisson(1.8)), np.random.poisson(0.8)
                if goals_a <= goals_h:
                    goals_a = goals_h + 1
                
        table[home]['GF'] += goals_h
        table[home]['GD'] += (goals_h - goals_a)
        table[away]['GF'] += goals_a
        table[away]['GD'] += (goals_a - goals_h)
        
    # Sort teams by Pts, then GD, then GF, with random fallback
    sorted_teams = sorted(
        table.items(),
        key=lambda x: (x[1]['Pts'], x[1]['GD'], x[1]['GF'], np.random.random()),
        reverse=True
    )
    return sorted_teams

def simulate_knockout_match(team_a, team_b, team_elos: dict) -> str:
    """Simulate a knockout match between two teams using Elo ratings."""
    elo_a = team_elos.get(team_a, 1700)
    elo_b = team_elos.get(team_b, 1700)
    
    expected_a = 1.0 / (1.0 + 10.0 ** ((elo_b - elo_a) / 400.0))
    
    # Knockout matches cannot end in a draw
    if np.random.random() < expected_a:
        return team_a
    return team_b
