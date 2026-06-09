import csv
from pathlib import Path

csv_path = Path("e:/AKiB's Project Book/TournAI-x-ATLAS-codebase/Dataset/wc2026_player_squad.csv")
positions = set()
with open(csv_path, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        positions.add(row.get("position_final"))

print("Unique positions:", positions)
