import pandas as pd
from src.features.drought_intelligence import compute_drought_intelligence
from src.features.seasonal import assign_india_season
import os
from pathlib import Path

def run():
    print("Loading dataset...")
    df = pd.read_parquet("data/processed/india/india_normalized.parquet")
    df = assign_india_season(df)
    print("Running M10 Drought Intelligence Engine...")
    res = compute_drought_intelligence(df)
    out_dir = Path("data/drought_intelligence")
    out_dir.mkdir(exist_ok=True)
    res.to_parquet(out_dir / "india_drought_intelligence.parquet", index=False)
    
    # Do for MH if applicable, wait, M10 was India only?
    print("M10 done")
if __name__ == '__main__':
    run()
