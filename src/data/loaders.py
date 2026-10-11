"""
NEW/src/data/loaders.py - Raw Dataset Ingestion & Validation Loaders

Governing Principles (instruction.md):
- Strictly READ-ONLY: Never modifies raw files in place.
- Validates file existence and schema compatibility.
- Attaches traceable source provenance (source_file, source_dataset, observation_type).
"""

import os
import glob
from typing import Dict, List, Tuple, Optional
import pandas as pd


# Canonical Provenance Constants
DATASET_ID_INDIA = "INDIA_CGWB_HISTORICAL"
DATASET_ID_MAHARASHTRA = "MAHARASHTRA_GSDA_TELEMETRY"

OBSERVATION_TYPE_PERIODIC = "PERIODIC_SEASONAL"
OBSERVATION_TYPE_TELEMETRY = "CONTINUOUS_TELEMETRY"

# Minimum required columns (case-insensitive, whitespace-trimmed)
REQUIRED_COLS_INDIA = {"state", "district", "lat", "lng", "date", "waterlevel"}
REQUIRED_COLS_MAHARASHTRA = {
    "station",
    "district",
    "latitude",
    "longitude",
    "data acquisition time",
    "groundwater level telemetry 6 hourly (meter)",
}


def validate_file_exists(filepath: str) -> None:
    """Raises FileNotFoundError with a clear path if the file does not exist."""
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"[Loader Error] Required raw file not found at: {os.path.abspath(filepath)}")


def load_single_raw_csv(filepath: str, low_memory: bool = False) -> pd.DataFrame:
    """
    Safely reads a single raw CSV file without altering its contents.
    Validates file existence and non-zero size.
    """
    validate_file_exists(filepath)
    if os.path.getsize(filepath) == 0:
        raise ValueError(f"[Loader Error] File is empty: {filepath}")

    df = pd.read_csv(filepath, low_memory=low_memory)
    return df


def load_india_raw_file(filepath: str) -> pd.DataFrame:
    """
    Loads a single India periodic seasonal CSV file.
    Validates minimum expected schema, attaches provenance metadata:
      - source_file: basename of the file
      - source_dataset: INDIA_CGWB_HISTORICAL
      - observation_type: PERIODIC_SEASONAL
    """
    df = load_single_raw_csv(filepath, low_memory=False)
    fname = os.path.basename(filepath)

    # Validate columns (trimmed lowercase comparison)
    present_cols = {c.strip().lower() for c in df.columns}
    missing_required = REQUIRED_COLS_INDIA - present_cols
    if missing_required:
        raise ValueError(
            f"[Loader Error] File {fname} missing required columns: {sorted(list(missing_required))}. "
            f"Present columns: {df.columns.tolist()}"
        )

    # Attach provenance without modifying raw data columns
    df["source_file"] = fname
    df["source_dataset"] = DATASET_ID_INDIA
    df["observation_type"] = OBSERVATION_TYPE_PERIODIC

    return df


def load_india_raw_dataset(india_dir: str) -> List[Tuple[str, pd.DataFrame]]:
    """
    Discovers and loads all India raw CSV files from the specified directory.
    Returns a list of tuples: (filename, raw_dataframe).
    """
    if not os.path.isdir(india_dir):
        raise FileNotFoundError(f"[Loader Error] India raw directory not found: {india_dir}")

    csv_paths = sorted(glob.glob(os.path.join(india_dir, "*.csv")))
    if not csv_paths:
        raise FileNotFoundError(f"[Loader Error] No CSV files found in India raw directory: {india_dir}")

    loaded_files = []
    for path in csv_paths:
        fname = os.path.basename(path)
        df = load_india_raw_file(path)
        loaded_files.append((fname, df))

    return loaded_files


def load_maharashtra_raw_dataset(mh_filepath: str) -> pd.DataFrame:
    """
    Loads the Maharashtra continuous telemetry CSV file.
    Validates minimum expected schema, attaches provenance metadata:
      - source_file: basename of the file
      - source_dataset: MAHARASHTRA_GSDA_TELEMETRY
      - observation_type: CONTINUOUS_TELEMETRY
    """
    df = load_single_raw_csv(mh_filepath, low_memory=False)
    fname = os.path.basename(mh_filepath)

    present_cols = {c.strip().lower() for c in df.columns}
    missing_required = REQUIRED_COLS_MAHARASHTRA - present_cols
    if missing_required:
        raise ValueError(
            f"[Loader Error] Maharashtra telemetry file missing required columns: {sorted(list(missing_required))}. "
            f"Present columns: {df.columns.tolist()}"
        )

    # Attach provenance
    df["source_file"] = fname
    df["source_dataset"] = DATASET_ID_MAHARASHTRA
    df["observation_type"] = OBSERVATION_TYPE_TELEMETRY

    return df
