def calculate_elo_win_prob(elo_team: float, elo_opponent: float) -> float:
    """Calculate the expected score (win probability) using the Elo formula."""
    return 1.0 / (1.0 + 10.0 ** ((elo_opponent - elo_team) / 400.0))

def update_elo_ratings(
    elo_home: float,
    elo_away: float,
    home_score: int,
    away_score: int,
    is_knockout: bool = False,
    k_factor: float = 60.0
) -> tuple[float, float]:
    """
    Calculate and return the updated Elo ratings for home and away teams.
    S = 1.0 for a win, 0.5 for a draw, 0.0 for a loss.
    """
    # Expected scores
    expected_home = calculate_elo_win_prob(elo_home, elo_away)
    expected_away = 1.0 - expected_home
    
    # Actual scores
    if home_score > away_score:
        actual_home = 1.0
        actual_away = 0.0
    elif home_score < away_score:
        actual_home = 0.0
        actual_away = 1.0
    else:
        actual_home = 0.5
        actual_away = 0.5
        
    # Elo changes
    new_elo_home = elo_home + k_factor * (actual_home - expected_home)
    new_elo_away = elo_away + k_factor * (actual_away - expected_away)
    
    return round(new_elo_home, 2), round(new_elo_away, 2)
