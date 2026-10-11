"""
NEW/src/data/normalization.py - Schema Normalization & Deterministic Coordinate Inversion Handling

Governing Principles (instruction.md):
- Strictly preserves raw values alongside normalized fields.
- Coordinate swapping applied ONLY to documented affected source (output1final.csv).
- Phantom export columns (Unnamed: *) removed only in normalized output.
- No unverified units or reference datums assumed.
"""

import hashlib
from typing import Dict, List, Optional
import numpy as np
import pandas as pd


def generate_candidate_site_id(
    state: Optional[str],
    district: Optional[str],
    block: Optional[str],
    village: Optional[str],
    lat: Optional[float],
    lng: Optional[float],
) -> str:
    """
    Generates a deterministic, reproducible candidate site ID from administrative
    and 4-decimal-place geographic coordinates.
    """
    s = str(state or "").strip().upper()
    d = str(district or "").strip().upper()
    b = str(block or "").strip().upper()
    v = str(village or "").strip().upper()
    lat_str = f"{float(lat):.4f}" if pd.notnull(lat) else "NONE"
    lng_str = f"{float(lng):.4f}" if pd.notnull(lng) else "NONE"

    raw_key = f"{s}|{d}|{b}|{v}|{lat_str}|{lng_str}".encode("utf-8")
    hash_digest = hashlib.sha256(raw_key).hexdigest()[:12]
    return f"IND_{hash_digest}"


def normalize_india_dataframe(df: pd.DataFrame, source_filename: str) -> pd.DataFrame:
    """
    Normalizes a single India periodic seasonal raw DataFrame:
    1. Removes phantom export columns (Unnamed: *).
    2. Strips whitespace from column names ('BLOCK ' -> 'block', 'VILLAGE ' -> 'village').
    3. Handles coordinate inversion ONLY for 'output1final.csv':
       - source_lat and source_lng are preserved verbatim.
       - If source is output1final.csv, latitude = source_lng, longitude = source_lat.
       - For all other sources, latitude = source_lat, longitude = source_lng.
    4. Parses Date into ISO-8601 string while preserving raw Date.
    5. Preserves status_raw, trend_raw, water_level_raw.
    6. Constructs candidate_site_id.
    """
    # 1. Drop phantom Unnamed columns
    cols_to_drop = [c for c in df.columns if c.startswith("Unnamed:")]
    df_norm = df.drop(columns=cols_to_drop).copy()

    # 2. Normalize column names (whitespace trimmed, lowercase)
    clean_cols = {c: c.strip() for c in df_norm.columns}
    df_norm = df_norm.rename(columns=clean_cols)

    # Ensure provenance fields exist
    if "source_file" not in df_norm.columns:
        df_norm["source_file"] = source_filename
    if "source_dataset" not in df_norm.columns:
        df_norm["source_dataset"] = "INDIA_CGWB_HISTORICAL"
    if "observation_type" not in df_norm.columns:
        df_norm["observation_type"] = "PERIODIC_SEASONAL"

    # 3. Preserve raw fields
    df_norm["source_lat"] = pd.to_numeric(df_norm["lat"], errors="coerce")
    df_norm["source_lng"] = pd.to_numeric(df_norm["lng"], errors="coerce")
    df_norm["water_level_raw"] = pd.to_numeric(df_norm["waterLevel"], errors="coerce")
    df_norm["water_level_unit"] = "UNKNOWN"  # Unspecified in source metadata
    df_norm["water_level_reference"] = "UNKNOWN"  # Unresolved reference datum
    df_norm["reference_datum"] = "UNKNOWN"

    df_norm["state_raw"] = df_norm["state"].astype(str)
    df_norm["district_raw"] = df_norm["district"].astype(str) if "district" in df_norm.columns else ""
    df_norm["block_raw"] = df_norm["BLOCK"].astype(str) if "BLOCK" in df_norm.columns else ""
    df_norm["village_raw"] = df_norm["VILLAGE"].astype(str) if "VILLAGE" in df_norm.columns else ""
    df_norm["date_raw"] = df_norm["Date"].astype(str)
    df_norm["status_raw"] = df_norm["status"].astype(str) if "status" in df_norm.columns else ""
    df_norm["trend_raw"] = df_norm["trend"].astype(str) if "trend" in df_norm.columns else ""

    # Normalized text fields (cleaned whitespace)
    df_norm["state"] = df_norm["state"].astype(str).str.strip()
    df_norm["district"] = df_norm["district"].astype(str).str.strip() if "district" in df_norm.columns else ""
    df_norm["block"] = df_norm["BLOCK"].astype(str).str.strip() if "BLOCK" in df_norm.columns else ""
    df_norm["village"] = df_norm["VILLAGE"].astype(str).str.strip() if "VILLAGE" in df_norm.columns else ""

    # Replace literal 'nan' or empty strings with np.nan safely
    for col in ["district", "block", "village"]:
        df_norm[col] = df_norm[col].mask(df_norm[col].isin(["nan", "None", ""]))

    # 4. Deterministic Coordinate Handling
    is_output1 = source_filename.lower().startswith("output1final")
    if is_output1:
        # Documented forensic fact: output1final.csv has lat and lng columns inverted
        df_norm["latitude"] = df_norm["source_lng"]
        df_norm["longitude"] = df_norm["source_lat"]
        df_norm["coordinate_inverted_corrected"] = True
    else:
        df_norm["latitude"] = df_norm["source_lat"]
        df_norm["longitude"] = df_norm["source_lng"]
        df_norm["coordinate_inverted_corrected"] = False

    # 5. Timestamp Normalization (preserve raw Date)
    parsed_date = pd.to_datetime(df_norm["Date"], format="%d/%m/%Y", errors="coerce")
    # Fallback parsing if any records vary
    unparsed_mask = parsed_date.isnull() & df_norm["Date"].notnull()
    if unparsed_mask.sum() > 0:
        fallback = pd.to_datetime(df_norm.loc[unparsed_mask, "Date"], errors="coerce")
        parsed_date.loc[unparsed_mask] = fallback

    df_norm["observation_date"] = parsed_date.dt.strftime("%Y-%m-%d")
    df_norm["observation_year"] = pd.to_numeric(df_norm["year"], errors="coerce")
    df_norm["observation_month"] = parsed_date.dt.month

    # 6. Candidate Site ID construction
    # Vectorized / apply candidate site ID
    df_norm["candidate_site_id"] = [
        generate_candidate_site_id(st, dt, bl, vl, lt, ln)
        for st, dt, bl, vl, lt, ln in zip(
            df_norm["state"],
            df_norm["district"],
            df_norm["block"],
            df_norm["village"],
            df_norm["latitude"],
            df_norm["longitude"],
        )
    ]

    # Select and order normalized output columns
    output_cols = [
        "source_dataset",
        "source_file",
        "observation_type",
        "candidate_site_id",
        "state",
        "district",
        "block",
        "village",
        "latitude",
        "longitude",
        "source_lat",
        "source_lng",
        "coordinate_inverted_corrected",
        "observation_date",
        "observation_year",
        "observation_month",
        "water_level_raw",
        "water_level_unit",
        "water_level_reference",
        "reference_datum",
        "status_raw",
        "trend_raw",
        "state_raw",
        "district_raw",
        "block_raw",
        "village_raw",
        "date_raw",
    ]

    return df_norm[output_cols].copy()


def normalize_maharashtra_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalizes the Maharashtra continuous 6-hourly telemetry raw DataFrame:
    1. Preserves raw fields alongside normalized fields.
    2. Maps station names, coordinates, and RL_MSL.
    3. Parses 6-hourly timestamps into ISO-8601 strings.
    4. Preserves water_level_raw, unit, and unresolved reference datum.
    5. Constructs candidate_site_id = 'MH_' + station_name.
    """
    df_norm = df.copy()

    # Raw field preservation
    df_norm["source_lat"] = pd.to_numeric(df_norm["Latitude"], errors="coerce")
    df_norm["source_lng"] = pd.to_numeric(df_norm["Longitude"], errors="coerce")
    df_norm["latitude"] = df_norm["source_lat"]
    df_norm["longitude"] = df_norm["source_lng"]
    df_norm["coordinate_inverted_corrected"] = False

    gw_col = "Groundwater Level Telemetry 6 Hourly (meter)"
    df_norm["water_level_raw"] = pd.to_numeric(df_norm[gw_col], errors="coerce")
    df_norm["water_level_unit"] = "meter"
    df_norm["water_level_reference"] = "UNKNOWN"
    df_norm["reference_datum"] = "UNKNOWN"

    time_col = "Data Acquisition Time"
    df_norm["data_acquisition_time_raw"] = df_norm[time_col].astype(str)
    parsed_time = pd.to_datetime(df_norm[time_col], format="%d-%m-%Y %H:%M", errors="coerce")
    df_norm["observation_timestamp"] = parsed_time.dt.strftime("%Y-%m-%dT%H:%M:%S")
    df_norm["observation_date"] = parsed_time.dt.strftime("%Y-%m-%d")

    # Administrative & Station metadata
    df_norm["station_name"] = df_norm["Station"].astype(str).str.strip().str.upper()
    df_norm["state"] = df_norm["State"].astype(str).str.strip()
    df_norm["state_lgd_code"] = pd.to_numeric(df_norm["State LGD Code"], errors="coerce")
    df_norm["district"] = df_norm["District"].astype(str).str.strip()
    df_norm["district_lgd_code"] = pd.to_numeric(df_norm["District LGD Code"], errors="coerce")
    df_norm["subdistrict"] = df_norm["Tehsil"].astype(str).str.strip()
    df_norm["elevation_msl"] = pd.to_numeric(df_norm["RL_MSL"], errors="coerce")
    df_norm["agency"] = df_norm["Agency"].astype(str).str.strip()

    # Candidate Site ID for Maharashtra
    df_norm["candidate_site_id"] = "MH_" + df_norm["station_name"]

    output_cols = [
        "source_dataset",
        "source_file",
        "observation_type",
        "candidate_site_id",
        "station_name",
        "state",
        "state_lgd_code",
        "district",
        "district_lgd_code",
        "subdistrict",
        "latitude",
        "longitude",
        "source_lat",
        "source_lng",
        "coordinate_inverted_corrected",
        "elevation_msl",
        "observation_timestamp",
        "observation_date",
        "water_level_raw",
        "water_level_unit",
        "water_level_reference",
        "reference_datum",
        "agency",
        "data_acquisition_time_raw",
    ]

    return df_norm[output_cols].copy()
