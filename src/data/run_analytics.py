"""
NEW/src/data/run_analytics.py - Orchestrator for M4-M6 analytics
Persists analytical outputs as static artifacts for the M7 API.
"""
import os
import pandas as pd
from pathlib import Path
from src.alerting.engine import generate_india_alerts, generate_maharashtra_alerts
from src.alerting.config import AlertConfig

def run_pipeline():
    project_root = Path(os.path.abspath(__file__)).parent.parent.parent
    
    india_in_path = project_root / "data" / "processed" / "india" / "india_normalized.parquet"
    mh_in_path = project_root / "data" / "processed" / "maharashtra" / "maharashtra_normalized.parquet"
    
    out_dir = project_root / "data" / "alerts"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print("Loading India M3 artifact...")
    if india_in_path.exists():
        df_ind = pd.read_parquet(india_in_path)
        print(f"Generating India alerts for {len(df_ind)} rows...")
        from src.features.seasonal import assign_india_season
        df_ind = assign_india_season(df_ind)
        df_ind_alerts = generate_india_alerts(df_ind)
        out_ind = out_dir / "india_alerts.parquet"
        df_ind_alerts.to_parquet(out_ind, index=False)
        print(f"Saved {out_ind}")
    else:
        print(f"Missing {india_in_path}")
        
    print("Loading Maharashtra M3 artifact...")
    if mh_in_path.exists():
        df_mh = pd.read_parquet(mh_in_path)
        print(f"Generating Maharashtra alerts for {len(df_mh)} rows...")
        df_mh_alerts = generate_maharashtra_alerts(df_mh)
        out_mh = out_dir / "maharashtra_alerts.parquet"
        df_mh_alerts.to_parquet(out_mh, index=False)
        print(f"Saved {out_mh}")
    else:
        print(f"Missing {mh_in_path}")

if __name__ == "__main__":
    run_pipeline()
