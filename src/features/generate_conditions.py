import os
import sys
from pathlib import Path
import pandas as pd
import json
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from features.conditions import compute_india_conditions, compute_maharashtra_conditions, CONDITION_VERSION
from features.seasonal import assign_india_season

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
CONDITIONS_DIR = DATA_DIR / "conditions"

INDIA_M3_PATH = PROCESSED_DIR / "india" / "india_normalized.parquet"
MH_M3_PATH = PROCESSED_DIR / "maharashtra" / "maharashtra_normalized.parquet"

INDIA_OUT_PATH = CONDITIONS_DIR / "india_conditions.parquet"
MH_OUT_PATH = CONDITIONS_DIR / "maharashtra_conditions.parquet"
METADATA_OUT_PATH = CONDITIONS_DIR / "metadata.json"

INDIA_COLS = [
    "candidate_site_id",
    "observation_date",
    "analytical_season",
    "water_level_raw",
    "condition_state",
    "percentile",
    "historical_sample_count",
    "historical_reference_group",
    "condition_method_version"
]

MH_COLS = [
    "candidate_site_id",
    "observation_timestamp",
    "observation_date",
    "water_level_raw",
    "condition_state",
    "percentile",
    "historical_sample_count",
    "historical_reference_group",
    "condition_method_version"
]

def generate_artifacts():
    print("M8.2-E.1 Condition Artifact Generation Started")
    print("==============================================")
    
    CONDITIONS_DIR.mkdir(parents=True, exist_ok=True)
    metadata = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "method_version": CONDITION_VERSION,
        "artifacts": {}
    }

    # 1. India
    if INDIA_M3_PATH.exists():
        print("Processing India...")
        india_df = pd.read_parquet(INDIA_M3_PATH)
        india_df = assign_india_season(india_df)
        source_count = len(india_df)
        
        india_cond = compute_india_conditions(india_df)
        india_cond = india_cond[INDIA_COLS].copy()
        
        out_count = len(india_cond)
        india_cond.to_parquet(INDIA_OUT_PATH, index=False)
        
        counts = india_cond["condition_state"].value_counts().to_dict()
        print(f"India source rows: {source_count}")
        print(f"India output rows: {out_count}")
        print(f"State distribution: {counts}")
        
        metadata["artifacts"]["india"] = {
            "source_rows": source_count,
            "output_rows": out_count,
            "state_distribution": counts,
            "path": "data/conditions/india_conditions.parquet"
        }
    else:
        print("India M3 data not found. Skipping.")

    # 2. Maharashtra
    if MH_M3_PATH.exists():
        print("\nProcessing Maharashtra...")
        mh_df = pd.read_parquet(MH_M3_PATH)
        source_count = len(mh_df)
        
        mh_cond = compute_maharashtra_conditions(mh_df)
        mh_cond = mh_cond[MH_COLS].copy()
        
        out_count = len(mh_cond)
        mh_cond.to_parquet(MH_OUT_PATH, index=False)
        
        counts = mh_cond["condition_state"].value_counts().to_dict()
        print(f"Maharashtra source rows: {source_count}")
        print(f"Maharashtra output rows: {out_count}")
        print(f"State distribution: {counts}")
        
        metadata["artifacts"]["maharashtra"] = {
            "source_rows": source_count,
            "output_rows": out_count,
            "state_distribution": counts,
            "path": "data/conditions/maharashtra_conditions.parquet"
        }
    else:
        print("Maharashtra M3 data not found. Skipping.")

    # Write metadata
    with open(METADATA_OUT_PATH, "w") as f:
        json.dump(metadata, f, indent=2)
        
    print("\nGeneration Complete.")

if __name__ == "__main__":
    generate_artifacts()
