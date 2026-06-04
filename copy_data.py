import os
import json
import shutil
import math
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent
output_json_dir = ROOT / "output" / "json"
output_results_dir = ROOT / "output" / "results"
frontend_public_data = ROOT / "frontend" / "public" / "data"

# Create directory if it doesn't exist
frontend_public_data.mkdir(parents=True, exist_ok=True)

def sanitize_nans(obj):
    """Recursively replace float NaN and Inf values with None (JSON null)."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: sanitize_nans(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_nans(x) for x in obj]
    return obj

# Copy and sanitize JSON files
json_files = [
    "predictions.json",
    "simulations.json",
    "players.json",
    "explanations.json",
    "model_comparison.json",
    "group_standings.json"
]

print("Starting file copy and JSON sanitization to frontend...")
for file in json_files:
    src = output_json_dir / file
    dst = frontend_public_data / file
    if src.exists():
        try:
            # Read JSON file (python's json handles NaN natively)
            with open(src, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Sanitize NaNs
            clean_data = sanitize_nans(data)
            
            # Write clean compliant JSON
            with open(dst, 'w', encoding='utf-8') as f:
                json.dump(clean_data, f, indent=2, ensure_ascii=False)
            print(f"  [OK] Sanitized and copied {file} to frontend/public/data/")
        except Exception as e:
            print(f"  [ERR] Failed processing {file}: {e}")
    else:
        print(f"  [WARN] Warning: {src} does not exist!")

# Convert and sanitize what_if_injuries.csv to injuries.json
csv_path = output_results_dir / "what_if_injuries.csv"
if csv_path.exists():
    try:
        df = pd.read_csv(csv_path)
        injuries_list = df.to_dict('records')
        clean_injuries = sanitize_nans(injuries_list)
        
        # Save as JSON
        dst_json = frontend_public_data / "injuries.json"
        with open(dst_json, 'w', encoding='utf-8') as f:
            json.dump(clean_injuries, f, indent=2, ensure_ascii=False)
        print("  [OK] Converted, sanitized and copied what_if_injuries.csv to injuries.json")
    except Exception as e:
        print(f"  [ERR] Failed processing injuries CSV: {e}")
else:
    print(f"  [WARN] Warning: {csv_path} does not exist!")

print("Data setup and JSON sanitization complete!")
