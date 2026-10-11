"""
NEW/src/data_profile.py - Read-Only Comprehensive Data Profiling Engine
For India-wide and Maharashtra Groundwater DWLR / Monitoring Datasets.

Governing Principles (instruction.md):
- Strictly READ-ONLY: Never modifies raw files.
- Never fabricates, estimates, or silently alters data.
- Reproducible, auditable statistics directly calculated from source CSVs.
"""

import os
import glob
import json
from typing import Dict, List, Any
import numpy as np
import pandas as pd


def profile_india_file(filepath: str) -> Dict[str, Any]:
    """Profiles a single India CSV file without modifying it."""
    filename = os.path.basename(filepath)
    filesize = os.path.getsize(filepath)

    # Read raw CSV
    df = pd.read_csv(filepath, low_memory=False)
    row_count = len(df)
    col_count = len(df.columns)
    col_names = df.columns.tolist()

    # Clean column names for internal access (preserving original list for audit)
    clean_cols = {c: c.strip() for c in col_names}
    df_clean = df.rename(columns=clean_cols)

    # Missing values
    missing_per_col = {col: int(df[col].isnull().sum()) for col in col_names}

    # Geographic fields profiling
    state_col = "state" if "state" in df_clean.columns else None
    district_col = "district" if "district" in df_clean.columns else None
    block_col = "BLOCK" if "BLOCK" in df_clean.columns else None
    village_col = "VILLAGE" if "VILLAGE" in df_clean.columns else None
    lat_col = "lat" if "lat" in df_clean.columns else None
    lng_col = "lng" if "lng" in df_clean.columns else None
    date_col = "Date" if "Date" in df_clean.columns else None
    wl_col = "waterLevel" if "waterLevel" in df_clean.columns else None
    status_col = "status" if "status" in df_clean.columns else None
    trend_col = "trend" if "trend" in df_clean.columns else None
    year_col = "year" if "year" in df_clean.columns else None

    # Strip strings where applicable for unique counts
    unique_states = int(df_clean[state_col].astype(str).str.strip().nunique()) if state_col else 0
    unique_districts = int(df_clean[district_col].astype(str).str.strip().nunique()) if district_col else 0
    unique_blocks = int(df_clean[block_col].astype(str).str.strip().nunique()) if block_col else 0
    unique_villages = int(df_clean[village_col].astype(str).str.strip().nunique()) if village_col else 0

    # Coordinate pairs
    coord_pairs = 0
    if lat_col and lng_col:
        coord_pairs = int(df_clean[[lat_col, lng_col]].drop_duplicates().shape[0])

    # Date profiling
    date_min = None
    date_max = None
    unique_dates = 0
    obs_by_year = {}
    obs_by_month = {}
    obs_by_day = {}

    if date_col:
        unique_dates = int(df_clean[date_col].nunique())
        # Try parsing dates safely
        parsed_dates = pd.to_datetime(df_clean[date_col], format="%d/%m/%Y", errors="coerce")
        # Fallback if format varies
        unparsed_mask = parsed_dates.isnull() & df_clean[date_col].notnull()
        if unparsed_mask.sum() > 0:
            parsed_dates_fallback = pd.to_datetime(df_clean.loc[unparsed_mask, date_col], errors="coerce")
            parsed_dates.loc[unparsed_mask] = parsed_dates_fallback

        valid_dates = parsed_dates.dropna()
        if len(valid_dates) > 0:
            date_min = str(valid_dates.min().strftime("%Y-%m-%d"))
            date_max = str(valid_dates.max().strftime("%Y-%m-%d"))
            obs_by_year = {str(k): int(v) for k, v in valid_dates.dt.year.value_counts().sort_index().items()}
            obs_by_month = {str(k): int(v) for k, v in valid_dates.dt.month.value_counts().sort_index().items()}
            obs_by_day = {str(k): int(v) for k, v in valid_dates.dt.day.value_counts().sort_index().items()}

    # Water Level profiling
    wl_stats = {}
    if wl_col:
        # Convert numeric coercing errors
        wl_series = pd.to_numeric(df_clean[wl_col], errors="coerce")
        valid_wl = wl_series.dropna()
        if len(valid_wl) > 0:
            wl_stats = {
                "count": int(len(valid_wl)),
                "null_count": int(wl_series.isnull().sum()),
                "min": float(valid_wl.min()),
                "max": float(valid_wl.max()),
                "mean": float(round(valid_wl.mean(), 4)),
                "median": float(round(valid_wl.median(), 4)),
                "std": float(round(valid_wl.std(), 4)),
                "quantiles": {
                    "q01": float(round(valid_wl.quantile(0.01), 4)),
                    "q05": float(round(valid_wl.quantile(0.05), 4)),
                    "q25": float(round(valid_wl.quantile(0.25), 4)),
                    "q50": float(round(valid_wl.quantile(0.50), 4)),
                    "q75": float(round(valid_wl.quantile(0.75), 4)),
                    "q95": float(round(valid_wl.quantile(0.95), 4)),
                    "q99": float(round(valid_wl.quantile(0.99), 4)),
                },
                "zeros": int((valid_wl == 0).sum()),
                "negatives": int((valid_wl < 0).sum()),
                "positives": int((valid_wl > 0).sum()),
                "extreme_high_gt_100": int((valid_wl > 100).sum()),
                "extreme_high_gt_500": int((valid_wl > 500).sum()),
                "extreme_negative_lt_minus_10": int((valid_wl < -10).sum()),
            }

    # Status & Trend distributions
    status_dist = {}
    if status_col:
        status_dist = {str(k): int(v) for k, v in df_clean[status_col].astype(str).str.strip().value_counts().items()}

    trend_dist = {}
    if trend_col:
        trend_dist = {str(k): int(v) for k, v in df_clean[trend_col].astype(str).str.strip().value_counts().items()}

    # Duplicates
    full_duplicates = int(df.duplicated().sum())

    # Candidate key duplicates
    cand_dup_coord_date = 0
    if lat_col and lng_col and date_col:
        cand_dup_coord_date = int(df_clean.duplicated(subset=[lat_col, lng_col, date_col]).sum())

    cand_dup_loc_date = 0
    if state_col and district_col and block_col and village_col and date_col:
        cand_dup_loc_date = int(df_clean.duplicated(subset=[state_col, district_col, block_col, village_col, date_col]).sum())

    # Coordinate Validation
    coord_stats = {}
    if lat_col and lng_col:
        lat_series = pd.to_numeric(df_clean[lat_col], errors="coerce")
        lng_series = pd.to_numeric(df_clean[lng_col], errors="coerce")
        valid_coords = lat_series.notnull() & lng_series.notnull()

        # Swapped coords: in India lat is 6-38, lon is 68-98. If lat > 50 and lon < 40, likely swapped!
        swapped_mask = (lat_series > 50) & (lng_series < 40)
        swapped_count = int(swapped_mask.sum())

        # Out of bounds India (even after considering swap):
        # Lat [6.0, 38.0], Lon [68.0, 98.0]
        unswapped_in_india = (lat_series >= 6.0) & (lat_series <= 38.0) & (lng_series >= 68.0) & (lng_series <= 98.0)
        swapped_in_india = (lng_series >= 6.0) & (lng_series <= 38.0) & (lat_series >= 68.0) & (lat_series <= 98.0)
        impossible_count = int((~(unswapped_in_india | swapped_in_india) & valid_coords).sum())

        coord_stats = {
            "lat_min": float(lat_series.min()) if valid_coords.any() else None,
            "lat_max": float(lat_series.max()) if valid_coords.any() else None,
            "lng_min": float(lng_series.min()) if valid_coords.any() else None,
            "lng_max": float(lng_series.max()) if valid_coords.any() else None,
            "missing_lat": int(lat_series.isnull().sum()),
            "missing_lng": int(lng_series.isnull().sum()),
            "swapped_lat_lng_count": swapped_count,
            "impossible_coords_count": impossible_count,
        }

    return {
        "filename": filename,
        "filesize_bytes": filesize,
        "row_count": row_count,
        "col_count": col_count,
        "col_names": col_names,
        "missing_per_col": missing_per_col,
        "unique_states": unique_states,
        "unique_districts": unique_districts,
        "unique_blocks": unique_blocks,
        "unique_villages": unique_villages,
        "unique_coordinate_pairs": coord_pairs,
        "date_min": date_min,
        "date_max": date_max,
        "unique_dates": unique_dates,
        "observations_by_year": obs_by_year,
        "observations_by_month": obs_by_month,
        "observations_by_day": obs_by_day,
        "water_level_stats": wl_stats,
        "status_distribution": status_dist,
        "trend_distribution": trend_dist,
        "full_duplicates": full_duplicates,
        "dup_coord_date": cand_dup_coord_date,
        "dup_loc_date": cand_dup_loc_date,
        "coordinate_stats": coord_stats,
    }


def profile_maharashtra_file(filepath: str) -> Dict[str, Any]:
    """Profiles the Maharashtra DWLR 6-hourly telemetry file without modifying it."""
    filename = os.path.basename(filepath)
    filesize = os.path.getsize(filepath)

    df = pd.read_csv(filepath)
    row_count = len(df)
    col_names = df.columns.tolist()

    gw_col = "Groundwater Level Telemetry 6 Hourly (meter)"
    time_col = "Data Acquisition Time"

    dt = pd.to_datetime(df[time_col], format="%d-%m-%Y %H:%M", errors="coerce")

    wl = df[gw_col]

    return {
        "filename": filename,
        "filesize_bytes": filesize,
        "row_count": row_count,
        "col_count": len(col_names),
        "col_names": col_names,
        "missing_per_col": {c: int(df[c].isnull().sum()) for c in col_names},
        "unique_stations": int(df["Station"].nunique()),
        "unique_districts": int(df["District"].nunique()),
        "unique_tehsils": int(df["Tehsil"].nunique()),
        "unique_coordinate_pairs": int(df[["Latitude", "Longitude"]].drop_duplicates().shape[0]),
        "date_min": str(dt.min()),
        "date_max": str(dt.max()),
        "unique_timestamps": int(df[time_col].nunique()),
        "water_level_stats": {
            "count": int(wl.count()),
            "null_count": int(wl.isnull().sum()),
            "min": float(wl.min()),
            "max": float(wl.max()),
            "mean": float(round(wl.mean(), 4)),
            "median": float(round(wl.median(), 4)),
            "std": float(round(wl.std(), 4)),
            "negatives": int((wl < 0).sum()),
            "positives": int((wl >= 0).sum()),
            "out_of_physical_range": int(((wl < -100) | (wl > 50)).sum()),
        },
        "full_duplicates": int(df.duplicated().sum()),
        "dup_station_time": int(df.duplicated(subset=["Station", time_col]).sum()),
    }


if __name__ == "__main__":
    print("[Data Profile Engine] Starting read-only data profiling...")
    india_files = sorted(glob.glob("NEW/data/raw/india/*.csv"))
    print(f"Found {len(india_files)} India CSV files.")

    all_india_profiles = []
    for f in india_files:
        print(f"Profiling {os.path.basename(f)}...")
        p = profile_india_file(f)
        all_india_profiles.append(p)

    mh_path = "NEW/data/raw/maharashtra/gwl_tel_6_hourly_maharashtra_gw_mh_2026_2030 (1).csv"
    if not os.path.exists(mh_path):
        mh_path = "MINI PROJECT TE/gwl_tel_6_hourly_maharashtra_gw_mh_2026_2030 (1).csv"

    print(f"Profiling Maharashtra file from {mh_path}...")
    mh_profile = profile_maharashtra_file(mh_path)

    output = {
        "india_files": all_india_profiles,
        "maharashtra_file": mh_profile,
    }

    # Save read-only profile report in scratch or docs
    out_json = "NEW/docs/data_profiling_results.json"
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(output, fh, indent=2)

    print(f"[Data Profile Engine] Profiling complete! Results saved to {out_json}")
