import pandas as pd
from collections import defaultdict

def extract_groups_from_fixtures(df_fixtures: pd.DataFrame) -> dict:
    """Extract team-group mappings from the fixture list (12 groups of 4)."""
    teams_per_fixture = list(zip(df_fixtures['home_team'], df_fixtures['away_team']))
    
    # Track opponents to identify groups
    team_opponents = defaultdict(set)
    for home, away in teams_per_fixture:
        team_opponents[home].add(away)
        team_opponents[away].add(home)
        
    groups = {}
    assigned = set()
    group_letter = 0
    group_labels = 'ABCDEFGHIJKL'
    
    all_teams = sorted(set(df_fixtures['home_team']) | set(df_fixtures['away_team']))
    for team in all_teams:
        if team in assigned:
            continue
        # A group consists of the team and all of its opponents
        group_members = {team} | team_opponents[team]
        
        # Verify it's a valid group of 4 teams (or fallback if fixtures are incomplete)
        if len(group_members) <= 4 and len(group_members) >= 3:
            label = group_labels[group_letter]
            groups[label] = sorted(group_members)
            assigned.update(group_members)
            group_letter += 1
            if group_letter >= 12:
                break
                
    return groups

def compute_group_standings(df_predictions: pd.DataFrame, df_fixtures: pd.DataFrame) -> pd.DataFrame:
    """Compute the predicted standings for each of the 12 groups."""
    groups = extract_groups_from_fixtures(df_fixtures)
    standings_rows = []
    
    for label, teams in sorted(groups.items()):
        # Initialize team statistics
        table = {t: {'MP': 0, 'W': 0, 'D': 0, 'L': 0, 'GF': 0, 'GA': 0, 'GD': 0, 'Pts': 0} for t in teams}
        
        # Find predicted matches for this group
        group_fixtures = df_predictions[
            (df_predictions['home_team'].isin(teams)) &
            (df_predictions['away_team'].isin(teams))
        ]
        
        for _, fix in group_fixtures.iterrows():
            home = fix['home_team']
            away = fix['away_team']
            pred = fix['predicted_result']
            
            table[home]['MP'] += 1
            table[away]['MP'] += 1
            
            # Predict realistic goals based on predicted outcome
            if pred == 'Home Win':
                table[home]['W'] += 1
                table[away]['L'] += 1
                table[home]['Pts'] += 3
                table[home]['GF'] += 2
                table[home]['GA'] += 1
                table[away]['GF'] += 1
                table[away]['GA'] += 2
            elif pred == 'Draw':
                table[home]['D'] += 1
                table[away]['D'] += 1
                table[home]['Pts'] += 1
                table[away]['Pts'] += 1
                table[home]['GF'] += 1
                table[home]['GA'] += 1
                table[away]['GF'] += 1
                table[away]['GA'] += 1
            else:  # Away Win
                table[away]['W'] += 1
                table[home]['L'] += 1
                table[away]['Pts'] += 3
                table[away]['GF'] += 2
                table[away]['GA'] += 1
                table[home]['GF'] += 1
                table[home]['GA'] += 2
                
        for team in table:
            table[team]['GD'] = table[team]['GF'] - table[team]['GA']
            
        # Sort group by Pts, then Goal Difference (GD), then Goals For (GF)
        sorted_table = sorted(table.items(), key=lambda x: (x[1]['Pts'], x[1]['GD'], x[1]['GF']), reverse=True)
        
        for pos, (team, stats) in enumerate(sorted_table, 1):
            stats_row = {'Group': label, 'Position': pos, 'Team': team}
            stats_row.update(stats)
            stats_row['Qualifies'] = 'Yes' if pos <= 2 else 'Maybe (3rd)'
            standings_rows.append(stats_row)
            
    return pd.DataFrame(standings_rows)
