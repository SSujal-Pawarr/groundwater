import pandas as pd
import json
from pathlib import Path
import sys

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from features.flood_intelligence import compute_maharashtra_flood_potential, compute_india_flood_potential

PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"

def run():
    print("Loading datasets...")
    mh_m3 = pd.read_parquet(DATA_DIR / "processed/maharashtra/maharashtra_normalized.parquet")
    mh_cond = pd.read_parquet(DATA_DIR / "conditions/maharashtra_conditions.parquet")
    mh_weather = pd.read_parquet(DATA_DIR / "features/maharashtra/maharashtra_weather_ml_ready.parquet")
    
    print("Computing Maharashtra Flood Potential...")
    mh_flood = compute_maharashtra_flood_potential(mh_m3, mh_cond, mh_weather)
    
    print("\nMaharashtra Results:")
    print(f"Total evaluated records: {len(mh_flood)}")
    
    dist = mh_flood['flood_potential_state'].value_counts().to_dict()
    print("State Distribution:")
    print(json.dumps(dist, indent=2))
    
    valid_mh = mh_flood[mh_flood['flood_potential_state'] != 'INSUFFICIENT_EVIDENCE']
    print(f"Valid records with full evidence: {len(valid_mh)}")
    print("Groundwater Percentile Stats:")
    print(valid_mh['groundwater_percentile'].describe())
    print("\nPrecipitation 7D Stats:")
    print(valid_mh['precip_sum_7d'].describe())
    print("\nGroundwater Rise Rate (m/day):")
    print(valid_mh['groundwater_rise_rate'].describe())
    print("\nSpatial Elevated Fraction:")
    print(valid_mh['spatial_elevated_fraction'].describe())
    
    # Save artifact
    out_dir = DATA_DIR / "flood_intelligence"
    out_dir.mkdir(exist_ok=True, parents=True)
    mh_flood.to_parquet(out_dir / "maharashtra_flood_potential.parquet", index=False)
    
    # India
    print("\nLoading India datasets...")
    india_m3 = pd.read_parquet(DATA_DIR / "processed/india/india_normalized.parquet")
    india_cond = pd.read_parquet(DATA_DIR / "conditions/india_conditions.parquet")
    
    print("Computing India Flood Potential...")
    india_flood = compute_india_flood_potential(india_m3, india_cond)
    india_dist = india_flood['flood_potential_state'].value_counts().to_dict()
    print("India State Distribution:")
    print(json.dumps(india_dist, indent=2))
    
    india_flood.to_parquet(out_dir / "india_flood_potential.parquet", index=False)
    print("Artifacts saved successfully.")

if __name__ == "__main__":
    run()
