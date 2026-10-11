"""
Rebuild data/processed/{india,maharashtra}/*_normalized.parquet from data/alerts/*_alerts.parquet.

Why: data/processed/ is git-ignored, so a fresh clone/zip has no normalized files and the dashboard map is empty.
The M6 alert files contain every M3 normalized column unchanged (same rows) plus the M6 alert columns, so the M3
files can be recovered by dropping the M6-only columns. Existing files are never overwritten.

Usage:  python scripts/rebuild_processed_from_alerts.py
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
M6_ONLY = {
    "india": ["historical_reference", "historical_std", "historical_sample_count", "deviation", "standardized_score",
              "instantaneous_state", "time_since_previous_obs_days", "alert_event_state", "detector_version"],
    "maharashtra": ["time_since_previous_obs_hours", "historical_reference", "deviation", "historical_std",
                    "standardized_score", "instantaneous_state", "alert_event_state", "detector_version"],
}

for region, drop in M6_ONLY.items():
    src = ROOT / "data" / "alerts" / f"{region}_alerts.parquet"
    dst = ROOT / "data" / "processed" / region / f"{region}_normalized.parquet"
    if dst.exists():
        print(f"[skip] {dst} already exists (not overwritten)")
        continue
    if not src.exists():
        print(f"[error] missing {src}")
        continue
    df = pd.read_parquet(src)
    df = df.drop(columns=[c for c in drop if c in df.columns])
    dst.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(dst, index=False)
    print(f"[ok] wrote {dst}  rows={len(df):,} cols={df.shape[1]}")
