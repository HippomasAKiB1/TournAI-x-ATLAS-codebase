import sys
import os
import json
import shutil
import pandas as pd
from pathlib import Path

# Add workspace directory to python path
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from backend.app.db.session import SessionLocal, engine, Base
from backend.app.db.models import Match
from src.adaptive.pipeline_trigger import trigger_adaptive_update

def main():
    print("==================================================")
    print("Testing Knockout Freeze Outcome Algorithm...")
    print("==================================================")

    # 1. Backup dataset files to prevent pollution
    backup_files = {
        ROOT / "Dataset" / "atlas_train_ready_final.csv": ROOT / "Dataset" / "atlas_train_ready_final.csv.bak",
        ROOT / "Dataset" / "wc2026_team_strength.csv": ROOT / "Dataset" / "wc2026_team_strength.csv.bak",
        ROOT / "Dataset" / "wc2026_fixtures.csv": ROOT / "Dataset" / "wc2026_fixtures.csv.bak",
        ROOT / "Dataset" / "wc2026_fixture_features.csv": ROOT / "Dataset" / "wc2026_fixture_features.csv.bak"
    }
    
    for orig, bak in backup_files.items():
        if orig.exists():
            shutil.copy2(orig, bak)
    print("  [OK] Backed up original dataset CSV files.")

    db = SessionLocal()
    original_matches = {}
    try:
        # 2. Complete all Group J and Group I matches to deterministically place Mexico as 1J and Germany as 2I
        # Group J matches:
        # Match 1: Mexico vs South Africa
        # Match 2: South Korea vs Czech Republic
        # Match 25: Czech Republic vs South Africa
        # Match 26: Mexico vs South Korea
        # Match 52: South Africa vs South Korea
        # Match 53: Mexico vs Czech Republic
        group_j_scores = {
            1: (3, 0),
            2: (2, 1),
            25: (0, 1),
            26: (2, 0),
            52: (1, 1),
            53: (1, 0)
        }
        
        # Group I matches:
        # Match 11: Germany vs Curaao
        # Match 12: Ivory Coast vs Ecuador
        # Match 35: Germany vs Ivory Coast
        # Match 36: Ecuador vs Curaao
        # Match 57: Curaao vs Ivory Coast
        # Match 58: Ecuador vs Germany
        group_i_scores = {
            11: (2, 0),
            12: (3, 1),
            35: (1, 2),
            36: (2, 1),
            57: (0, 2),
            58: (1, 1)
        }
        
        scores_to_set = {**group_j_scores, **group_i_scores}
        for mid, (h_score, a_score) in scores_to_set.items():
            match = db.query(Match).filter(Match.id == mid).first()
            if match:
                original_matches[mid] = {
                    "home_score": match.home_score,
                    "away_score": match.away_score,
                    "status": match.status
                }
                match.home_score = h_score
                match.away_score = a_score
                match.status = "completed"
        db.commit()
        print("  [OK] Set up deterministic Group J and Group I completed match standings in DB.")

        # 3. Add a completed knockout match in Round of 32: Mexico plays Germany and Mexico wins 3-0
        db.query(Match).filter(
            Match.home_team == "Mexico",
            Match.away_team == "Germany",
            Match.stage == "Round of 32"
        ).delete()
        
        mock_knockout = Match(
            home_team="Mexico",
            away_team="Germany",
            home_score=3,
            away_score=0,
            stage="Round of 32",
            status="completed"
        )
        db.add(mock_knockout)
        db.commit()
        print("  [OK] Created mock completed Round of 32 Match: Mexico 3 - 0 Germany.")
        
        # 4. Trigger the adaptive pipeline
        print("  Running adaptive trigger update...")
        trigger_adaptive_update(
            home_team="Mexico",
            away_team="Germany",
            home_score=3,
            away_score=0,
            stage="Round of 32"
        )
        print("  [OK] Completed adaptive pipeline execution.")
        
        # 5. Verify simulations.json results
        sim_path = ROOT / "frontend" / "public" / "data" / "simulations.json"
        with open(sim_path, "r", encoding="utf-8") as f:
            sim_data = json.load(f)
            
        mexico_stats = None
        germany_stats = None
        for team in sim_data.get("results", []):
            if team["Team"] == "Mexico":
                mexico_stats = team
            elif team["Team"] == "Germany":
                germany_stats = team
                
        if mexico_stats is None or germany_stats is None:
            print("  [ERROR] Mexico or Germany statistics missing from simulations.json!")
            sys.exit(1)
            
        print("\nVerification Results:")
        print(f"  Mexico Round of 16 odds: {mexico_stats.get('Round of 16 %')}% (Expected: 100.0%)")
        print(f"  Germany Round of 16 odds: {germany_stats.get('Round of 16 %')}% (Expected: 0.0%)")
        
        # Check assertions
        assert float(mexico_stats.get('Round of 16 %')) == 100.0, "Mexico Round of 16 odds should be 100.0%"
        assert float(germany_stats.get('Round of 16 %')) == 0.0, "Germany Round of 16 odds should be 0.0%"
        
        # 6. Verify bracket.json has the FT scores
        bracket_path = ROOT / "frontend" / "public" / "data" / "bracket.json"
        with open(bracket_path, "r", encoding="utf-8") as f:
            bracket_data = json.load(f)
            
        mexico_match_in_bracket = None
        for m in bracket_data.get("r32", []):
            if (m["home_team"] == "Mexico" and m["away_team"] == "Germany") or \
               (m["home_team"] == "Germany" and m["away_team"] == "Mexico"):
                mexico_match_in_bracket = m
                break
                
        if mexico_match_in_bracket is None:
            print("  [WARN] Mexico vs Germany match not found in bracket.json.")
        else:
            print(f"  Bracket Match Info:")
            print(f"    Home Team: {mexico_match_in_bracket.get('home_team')} (Score: {mexico_match_in_bracket.get('home_score')})")
            print(f"    Away Team: {mexico_match_in_bracket.get('away_team')} (Score: {mexico_match_in_bracket.get('away_score')})")
            assert mexico_match_in_bracket.get('home_score') == 3, "Bracket home score should be 3"
            assert mexico_match_in_bracket.get('away_score') == 0, "Bracket away score should be 0"
            
        print("\n==================================================")
        print("SUCCESS: Knockout Freeze Outcome verification passed!")
        print("==================================================")
        
    except Exception as e:
        print(f"  [ERROR] Test failed with error: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        # Restore original group stage matches
        if original_matches:
            for mid, original in original_matches.items():
                match = db.query(Match).filter(Match.id == mid).first()
                if match:
                    match.home_score = original["home_score"]
                    match.away_score = original["away_score"]
                    match.status = original["status"]
            db.commit()
            print("  [OK] Restored original group stage matches in DB.")
            
        # Clean up mock knockout match to prevent polluting database
        db.query(Match).filter(
            Match.home_team == "Mexico",
            Match.away_team == "Germany",
            Match.stage == "Round of 32"
        ).delete()
        db.commit()
        print("  [OK] Cleaned up mock knockout match from DB.")
        db.close()
        
        # Restore backup files
        for orig, bak in backup_files.items():
            if bak.exists():
                try:
                    shutil.move(str(bak), str(orig))
                except Exception as e:
                    print(f"  [WARN] Failed to restore {orig.name}: {e}")
        print("  [OK] Restored original dataset CSV files.")

if __name__ == "__main__":
    main()
