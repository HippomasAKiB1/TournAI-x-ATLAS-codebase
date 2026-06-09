import numpy as np
import pandas as pd
from collections import defaultdict
from tqdm import tqdm
from .match_simulator import simulate_group, simulate_knockout_match

class ATLASMonteCarloSimulator:
    """Monte Carlo simulator for executing tournament-wide simulations of the 48-team FIFA World Cup."""
    def __init__(self, groups: dict, fixture_probs_lookup: dict, team_elos: dict, all_teams: list,
                 completed_group_scores: dict = None, completed_knockouts: dict = None):
        self.groups = groups
        self.fixture_probs_lookup = fixture_probs_lookup
        self.team_elos = team_elos
        self.all_teams = all_teams
        self.completed_group_scores = completed_group_scores or {}
        self.completed_knockouts = completed_knockouts or {}
        self.team_stages = defaultdict(lambda: {
            'group_exit': 0, 'r32': 0, 'r16': 0,
            'qf': 0, 'sf': 0, 'final': 0, 'champion': 0
        })
        self.team_positions = defaultdict(lambda: [0, 0, 0, 0])
        
    def _get_knockout_winner(self, team_a: str, team_b: str, stage: str) -> str:
        """Helper to check if a knockout match was already completed in real life and return the winner."""
        key1 = (team_a.lower(), team_b.lower(), stage.lower())
        key2 = (team_b.lower(), team_a.lower(), stage.lower())
        if key1 in self.completed_knockouts:
            return self.completed_knockouts[key1]
        if key2 in self.completed_knockouts:
            return self.completed_knockouts[key2]
        return None
        
    def run_simulations(self, n_simulations: int = 10000, show_progress: bool = True) -> pd.DataFrame:
        """Run N simulations of the entire tournament structure and aggregate probabilities."""
        self.team_stages.clear()
        self.team_positions.clear()
        
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
                        
                standings_sim = simulate_group(group_teams_list, grp_fixture_probs, self.completed_group_scores)
                
                # Top 2 advance directly
                for pos, (team, stats) in enumerate(standings_sim):
                    self.team_positions[team][pos] += 1
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
                
            # --- Knockout Stage (Deterministic pairing conforming to bracket) ---
            # Group winners vs runners up pairings:
            group_pairs = [
                ('A', 'B'), # Match 1: 1A vs 2B
                ('C', 'D'), # Match 2: 1C vs 2D
                ('E', 'F'), # Match 3: 1E vs 2F
                ('G', 'H'), # Match 4: 1G vs 2H
                ('I', 'J'), # Match 5: 1I vs 2J
                ('K', 'L'), # Match 6: 1K vs 2L
                ('B', 'A'), # Match 7: 1B vs 2A
                ('D', 'C'), # Match 8: 1D vs 2C
                ('F', 'E'), # Match 9: 1F vs 2E
                ('H', 'G'), # Match 10: 1H vs 2G
                ('J', 'I'), # Match 11: 1J vs 2I
                ('L', 'K'), # Match 12: 1L vs 2K
            ]
            
            r32_pairings = []
            for h_grp, a_grp in group_pairs:
                h_team = group_results.get(h_grp, ['TBD', 'TBD'])[0]
                a_team = group_results.get(a_grp, ['TBD', 'TBD'])[1]
                r32_pairings.append((h_team, a_team))
                
            # Third-place matchups (Match 13-16)
            best_thirds_teams = [t for t, _ in third_place_teams[:8]]
            while len(best_thirds_teams) < 8:
                best_thirds_teams.append("TBD")
                
            r32_pairings.append((best_thirds_teams[0], best_thirds_teams[1]))
            r32_pairings.append((best_thirds_teams[2], best_thirds_teams[3]))
            r32_pairings.append((best_thirds_teams[4], best_thirds_teams[5]))
            r32_pairings.append((best_thirds_teams[6], best_thirds_teams[7]))
            
            # Round of 32 (32 teams -> 16)
            r16_teams = []
            for team_a, team_b in r32_pairings:
                actual_winner = self._get_knockout_winner(team_a, team_b, "Round of 32")
                if actual_winner:
                    winner = actual_winner
                else:
                    winner = simulate_knockout_match(team_a, team_b, self.team_elos)
                r16_teams.append(winner)
                self.team_stages[winner]['r16'] += 1
                    
            # Round of 16 (16 -> 8)
            qf_teams = []
            for i in range(0, len(r16_teams), 2):
                team_a = r16_teams[i]
                team_b = r16_teams[i+1]
                actual_winner = self._get_knockout_winner(team_a, team_b, "Round of 16")
                if actual_winner:
                    winner = actual_winner
                else:
                    winner = simulate_knockout_match(team_a, team_b, self.team_elos)
                qf_teams.append(winner)
                self.team_stages[winner]['qf'] += 1
                    
            # Quarter-finals (8 -> 4)
            sf_teams = []
            for i in range(0, len(qf_teams), 2):
                team_a = qf_teams[i]
                team_b = qf_teams[i+1]
                actual_winner = self._get_knockout_winner(team_a, team_b, "Quarter-Final")
                if actual_winner:
                    winner = actual_winner
                else:
                    winner = simulate_knockout_match(team_a, team_b, self.team_elos)
                sf_teams.append(winner)
                self.team_stages[winner]['sf'] += 1
                    
            # Semi-finals (4 -> 2)
            finalists = []
            for i in range(0, len(sf_teams), 2):
                team_a = sf_teams[i]
                team_b = sf_teams[i+1]
                actual_winner = self._get_knockout_winner(team_a, team_b, "Semi-Final")
                if actual_winner:
                    winner = actual_winner
                else:
                    winner = simulate_knockout_match(team_a, team_b, self.team_elos)
                finalists.append(winner)
                self.team_stages[winner]['final'] += 1
                    
            # Final (2 -> 1)
            if len(finalists) == 2:
                team_a = finalists[0]
                team_b = finalists[1]
                actual_winner = self._get_knockout_winner(team_a, team_b, "Final")
                if actual_winner:
                    winner = actual_winner
                else:
                    winner = simulate_knockout_match(team_a, team_b, self.team_elos)
                self.team_stages[winner]['champion'] += 1
                
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
            
        # --- Compute group qualification percentages ---
        self.team_positions_pct = {}
        for team in self.all_teams:
            pos_counts = self.team_positions[team]
            self.team_positions_pct[team] = {
                'first_place': round(pos_counts[0] / n_simulations * 100.0, 2),
                'second_place': round(pos_counts[1] / n_simulations * 100.0, 2),
                'third_place': round(pos_counts[2] / n_simulations * 100.0, 2),
                'fourth_place': round(pos_counts[3] / n_simulations * 100.0, 2)
            }
            
        return pd.DataFrame(sim_results).sort_values('Champion %', ascending=False)
