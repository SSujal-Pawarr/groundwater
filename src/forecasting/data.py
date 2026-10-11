"""Load valid (analytics-ready) observations into a compact observation table."""
from __future__ import annotations
import numpy as np
import pandas as pd
from .config import ROOT, DatasetConfig


def _resolve_source(cfg: DatasetConfig):
    for rel in cfg.source_files:
        p = ROOT / rel
        if p.exists():
            return p
    raise FileNotFoundError(f"No source parquet found for {cfg.region}: tried {cfg.source_files}")


def load_observations(cfg: DatasetConfig) -> pd.DataFrame:
    """
    Returns one row per valid observation:
      site, date, value, lat, lon, state, district, unit [+ dataset specific cols]
    Maharashtra (6-hourly) is aggregated to a DAILY mean per site.
    Only rows with is_analytics_ready == True are used (extreme / conflicting rows excluded).
    """
    path = _resolve_source(cfg)
    df = pd.read_parquet(path)
    if "is_analytics_ready" in df.columns:
        df = df[df["is_analytics_ready"].astype(bool)]
    df = df[df["water_level_raw"].notna()].copy()
    df["_ts"] = pd.to_datetime(df[cfg.time_col])

    if cfg.region == "maharashtra":
        df["date"] = df["_ts"].dt.normalize()
        agg = df.groupby(["candidate_site_id", "date"], sort=True).agg(
            value=("water_level_raw", "mean"),
            lat=("latitude", "first"), lon=("longitude", "first"),
            elevation=("elevation_msl", "first"),
            state=("state", "first"), district=("district", "first"),
            unit=("water_level_unit", "first"),
        ).reset_index()
        agg["group"] = "ALL"
        agg = _attach_precip_mh(agg)
    else:
        df["date"] = df["_ts"].dt.normalize()
        df = df.sort_values(["candidate_site_id", "date"]).drop_duplicates(["candidate_site_id", "date"], keep="first")
        agg = pd.DataFrame({
            "candidate_site_id": df["candidate_site_id"].values,
            "date": df["date"].values,
            "value": df["water_level_raw"].astype("float64").values,
            "lat": df["latitude"].values, "lon": df["longitude"].values,
            "state": df["state"].values, "district": df["district"].values,
            "unit": df["water_level_unit"].values,
            "group": df["analytical_season"].astype(str).values,
        })
    agg = agg.sort_values(["candidate_site_id", "date"]).reset_index(drop=True)
    agg["unit"] = agg["unit"].fillna(cfg.unit_default)
    return agg


def _attach_precip_mh(agg: pd.DataFrame) -> pd.DataFrame:
    """Past-only rainfall accumulations (known at the origin) from the M11 artifact, if present."""
    p = ROOT / "data" / "flood_intelligence" / "maharashtra_flood_potential.parquet"
    if not p.exists():
        return agg
    f = pd.read_parquet(p, columns=["candidate_site_id", "observation_timestamp", "precip_sum_7d", "precip_sum_30d"])
    f["date"] = pd.to_datetime(f["observation_timestamp"]).dt.normalize()
    f = f.groupby(["candidate_site_id", "date"], sort=False)[["precip_sum_7d", "precip_sum_30d"]].last().reset_index()
    return agg.merge(f, on=["candidate_site_id", "date"], how="left")


def season_of_month_map(obs: pd.DataFrame) -> dict:
    """month -> most common analytical group (used to label a *future* target date)."""
    m = obs["date"].dt.month
    tab = obs.assign(_m=m).groupby(["_m", "group"]).size().reset_index(name="n")
    tab = tab.sort_values(["_m", "n"], ascending=[True, False]).drop_duplicates("_m")
    return dict(zip(tab["_m"], tab["group"]))
