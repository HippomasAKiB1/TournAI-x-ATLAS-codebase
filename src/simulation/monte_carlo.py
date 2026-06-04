import numpy as np
import pandas as pd
from collections import defaultdict
from tqdm import tqdm
from .match_simulator import simulate_group, simulate_knockout_match

class ATLASMonteCarloSimulator:
    """Monte Carlo simulator for executing tournament-wide simulations of the 48-team FIFA World Cup."""
    def __init__(self, groups: dict, fixture_probs_lookup: dict, team_elos: dict, all_teams: list):
        self.groups = groups
        self.fixture_probs_lookup = fixture_probs_lookup
        self.team_elos = team_elos
        self.all_teams = all_teams
        self.team_stages = defaultdict(lambda: {
            'group_exit': 0, 'r32': 0, 'r16': 0,
            'qf': 0, 'sf': 0, 'final': 0, 'champion': 0
        })
        
    def run_simulations(self, n_simulations: int = 10000, show_progress: bool = True) -> pd.DataFrame:
        """Run N simulations of the entire tournament structure and aggregate probabilities."""
        self.team_stages.clear()
        
        iterator = range(n_simulations)
        if show_progress:
            iterator = tqdm(iterator, desc="  Simulating Tournament", ncols=80)
            
        for _ in iterator:
            # --- Group Stage ---
            group_results = {}
            third_place_teams = []
            
            for label, group_teams_list in self.groups.items():
                # Filter fixture probs for this group
                grp_fixture_probs = {}
                for home, away in self.fixture_probs_lookup:
                    if home in group_teams_list and away in group_teams_list:
                        grp_fixture_probs[(home, away)] = self.fixture_probs_lookup[(home, away)]
                        
                standings_sim = simulate_group(group_teams_list, grp_fixture_probs)
                
                # Top 2 advance directly
                for pos, (team, stats) in enumerate(standings_sim):
                    if pos < 2:
                        group_results.setdefault(label, []).append(team)
                        self.team_stages[team]['r32'] += 1
                    elif pos == 2:
                        third_place_teams.append((team, stats))
                    else:
                        self.team_stages[team]['group_exit'] += 1
                        
            # Best 8 third-place teams advance
            # Sort by Pts, GD, GF, and then a random tie-breaker
            third_place_teams.sort(
                key=lambda x: (x[1]['Pts'], x[1]['GD'], x[1]['GF'], np.random.random()),
                reverse=True
            )
            
            for team, _ in third_place_teams[:8]:
                self.team_stages[team]['r32'] += 1
            for team, _ in third_place_teams[8:]:
                self.team_stages[team]['group_exit'] += 1
                
            # --- Knockout Stage ---
            # Collect all 32 advancing teams
            advancing = []
            for label in sorted(group_results.keys()):
                advancing.extend(group_results[label])
            advancing.extend([t for t, _ in third_place_teams[:8]])
            
            # Shuffle bracket placement for simplicity
            np.random.shuffle(advancing)
            
            # Round of 32 (32 teams -> 16)
            r16_teams = []
            for i in range(0, len(advancing), 2):
                if i + 1 < len(advancing):
                    winner = simulate_knockout_match(advancing[i], advancing[i+1], self.team_elos)
                    r16_teams.append(winner)
                    self.team_stages[winner]['r16'] += 1
                else:
                    r16_teams.append(advancing[i])
                    self.team_stages[advancing[i]]['r16'] += 1
                    
            # Round of 16 (16 -> 8)
            qf_teams = []
            for i in range(0, len(r16_teams), 2):
                if i + 1 < len(r16_teams):
                    winner = simulate_knockout_match(r16_teams[i], r16_teams[i+1], self.team_elos)
                    qf_teams.append(winner)
                    self.team_stages[winner]['qf'] += 1
                    
            # Quarter-finals (8 -> 4)
            sf_teams = []
            for i in range(0, len(qf_teams), 2):
                if i + 1 < len(qf_teams):
                    winner = simulate_knockout_match(qf_teams[i], qf_teams[i+1], self.team_elos)
                    sf_teams.append(winner)
                    self.team_stages[winner]['sf'] += 1
                    
            # Semi-finals (4 -> 2)
            finalists = []
            for i in range(0, len(sf_teams), 2):
                if i + 1 < len(sf_teams):
                    winner = simulate_knockout_match(sf_teams[i], sf_teams[i+1], self.team_elos)
                    finalists.append(winner)
                    self.team_stages[winner]['final'] += 1
                    
            # Final (2 -> 1)
            if len(finalists) == 2:
                champion = simulate_knockout_match(finalists[0], finalists[1], self.team_elos)
                self.team_stages[champion]['champion'] += 1
                
        # --- Format Results Table ---
        sim_results = []
        for team in self.all_teams:
            stages = self.team_stages[team]
            sim_results.append({
                'Team': team,
                'Champion %': round(stages['champion'] / n_simulations * 100.0, 2),
                'Finalist %': round(stages['final'] / n_simulations * 100.0, 2),
                'Semi-Final %': round(stages['sf'] / n_simulations * 100.0, 2),
                'Quarter-Final %': round(stages['qf'] / n_simulations * 100.0, 2),
                'Round of 16 %': round(stages['r16'] / n_simulations * 100.0, 2),
                'Round of 32 %': round(stages['r32'] / n_simulations * 100.0, 2),
                'Group Exit %': round(stages['group_exit'] / n_simulations * 100.0, 2),
            })
            
        return pd.DataFrame(sim_results).sort_values('Champion %', ascending=False)
