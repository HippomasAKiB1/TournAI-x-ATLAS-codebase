import os
import pandas as pd
from pathlib import Path

# Fallback path to the local Dataset directory
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "Dataset"

def load_dataset(name: str, data_dir: Path = DEFAULT_DATA_DIR) -> pd.DataFrame:
    """Load a specific CSV dataset from the data directory."""
    path = Path(data_dir) / name
    if not path.exists():
        raise FileNotFoundError(f"Dataset file {path} not found.")
    return pd.read_csv(path)

def load_train_ready_data(data_dir: Path = DEFAULT_DATA_DIR) -> pd.DataFrame:
    """Load the historical WC match training/testing dataset (atlas_train_ready_final.csv)."""
    return load_dataset("atlas_train_ready_final.csv", data_dir)

def load_player_match_stats(data_dir: Path = DEFAULT_DATA_DIR) -> pd.DataFrame:
    """Load the player-level match stats (sb_player_match_stats.csv)."""
    return load_dataset("sb_player_match_stats.csv", data_dir)

def load_wc2026_fixtures(data_dir: Path = DEFAULT_DATA_DIR) -> pd.DataFrame:
    """Load the World Cup 2026 group stage fixture schedule (wc2026_fixtures.csv)."""
    return load_dataset("wc2026_fixtures.csv", data_dir)

def load_wc2026_fixture_features(data_dir: Path = DEFAULT_DATA_DIR) -> pd.DataFrame:
    """Load pre-computed features for the World Cup 2026 fixtures (wc2026_fixture_features.csv)."""
    return load_dataset("wc2026_fixture_features.csv", data_dir)

def load_wc2026_team_strength(data_dir: Path = DEFAULT_DATA_DIR) -> pd.DataFrame:
    """Load World Cup 2026 team strength profiles (wc2026_team_strength.csv)."""
    return load_dataset("wc2026_team_strength.csv", data_dir)

def load_wc2026_player_squad(data_dir: Path = DEFAULT_DATA_DIR) -> pd.DataFrame:
    """Load World Cup 2026 squads player metrics (wc2026_player_squad.csv)."""
    return load_dataset("wc2026_player_squad.csv", data_dir)
