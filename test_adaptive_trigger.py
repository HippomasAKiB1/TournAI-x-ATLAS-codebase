import sys
from pathlib import Path

# Add current workspace directory to Python path
sys.path.append(str(Path(__file__).resolve().parent))

from src.adaptive.pipeline_trigger import trigger_adaptive_update

if __name__ == "__main__":
    print("Running integration test for ATLAS adaptive learning loop...")
    
    # Test updating Mexico vs South Africa (Match 1 of World Cup 2026)
    # Mexico wins 2 - 1
    trigger_adaptive_update(
        home_team="Mexico",
        away_team="South Africa",
        home_score=2,
        away_score=1,
        stage="Group Stage"
    )
    print("Integration test finished successfully!")
