"""
Read-only endpoints for the multi-horizon future forecast (M17).
Serves artifacts written by `python -m src.forecasting.pipeline`; it does not touch the existing DAL/routes.
"""
from __future__ import annotations
import json
from typing import Dict, Literal, Optional, Tuple

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from src.forecasting.config import OUT_DIR as _DEFAULT_OUT_DIR

router = APIRouter(prefix="/api/v1", tags=["future-forecast"])

# Module-level so tests can monkeypatch it.
OUT_DIR = _DEFAULT_OUT_DIR
Region = Literal["india", "maharashtra"]
_cache: Dict[str, Tuple[float, pd.DataFrame]] = {}


def _load(region: str) -> Optional[pd.DataFrame]:
    path = OUT_DIR / f"{region}_future_forecast.parquet"
    if not path.exists():
        return None
    mtime = path.stat().st_mtime
    hit = _cache.get(str(path))
    if hit and hit[0] == mtime:
        return hit[1]
    df = pd.read_parquet(path)
    _cache[str(path)] = (mtime, df)
    return df


def _records(df: pd.DataFrame):
    # to_json converts NaN -> null and numpy scalars -> python scalars
    return json.loads(df.to_json(orient="records"))


def _not_generated(region: str):
    return HTTPException(
        status_code=404,
        detail=f"Future forecast for '{region}' has not been generated. "
               f"Run: python -m src.forecasting.pipeline --region {region}",
    )


@router.get("/{region}/future-forecast/summary")
def future_forecast_summary(region: Region):
    """Horizon comparison (1/6/12 months), selected horizon, regression + classification accuracy."""
    path = OUT_DIR / f"{region}_summary.json"
    if not path.exists():
        raise _not_generated(region)
    return json.loads(path.read_text())


@router.get("/{region}/future-forecast")
def list_future_forecasts(
    region: Region,
    limit: int = Query(100, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    state: Optional[str] = None,
    district: Optional[str] = None,
    predicted_condition_state: Optional[str] = None,
):
    df = _load(region)
    if df is None:
        raise _not_generated(region)
    if state:
        df = df[df["state"] == state]
    if district:
        df = df[df["district"] == district]
    if predicted_condition_state:
        df = df[df["predicted_condition_state"] == predicted_condition_state]
    return _records(df.iloc[offset: offset + limit])


@router.get("/{region}/candidate-sites/{candidate_site_id}/future-forecast")
def site_future_forecast(region: Region, candidate_site_id: str):
    df = _load(region)
    if df is not None:
        row = df[df["candidate_site_id"] == candidate_site_id]
        if not row.empty:
            out = _records(row.iloc[:1])[0]
            probs = {k[len("prob_"):]: out.pop(k) for k in [k for k in list(out) if k.startswith("prob_")]}
            out["predicted_condition_probabilities"] = probs
            out["forecast_source"] = "direct_m17"
            return out

    # Some sites are excluded from the direct M17 artifact because their latest
    # observation is stale. Use the precomputed chained estimate when available,
    # while clearly marking its weaker no-recent-data semantics.
    chained = _load_chain(region)
    if chained is not None:
        row = chained[chained["candidate_site_id"] == candidate_site_id]
        if not row.empty:
            out = _records(row.iloc[:1])[0]
            probs = {k[len("prob_"):]: out.pop(k) for k in [k for k in list(out) if k.startswith("prob_")]}
            out["predicted_condition_probabilities"] = probs
            out["horizon_months"] = out.get("months_to_target", out.get("n_steps", 1) * out.get("step_months", 1))
            out["target_date"] = out.get("predicted_for_date") or out.get("requested_target_date")
            out["forecast_source"] = "chained_fallback"
            out["forecast_method"] = out.get("method", "persistence_fallback")
            out["forecast_reason"] = out.get("method_reason")
            out["warnings"] = [warning for warning in (out.get("warnings") or "").split("; ") if warning]
            return out

    if df is None:
        raise _not_generated(region)
    raise HTTPException(
        status_code=404,
        detail="No direct or chained forecast is available for this site (its observation history may be too old).",
    )


# ---------------------------------------------------------------------------
# Chained ("rolled-forward") estimate to a target date beyond the end of the data
# ---------------------------------------------------------------------------
def _load_chain(region: str) -> Optional[pd.DataFrame]:
    path = OUT_DIR / f"{region}_chained_forecast.parquet"
    if not path.exists():
        return None
    mtime = path.stat().st_mtime
    key = f"chain::{path}"
    hit = _cache.get(key)
    if hit and hit[0] == mtime:
        return hit[1]
    df = pd.read_parquet(path)
    _cache[key] = (mtime, df)
    return df


def _chain_not_generated(region: str):
    return HTTPException(
        status_code=404,
        detail=f"Chained forecast for '{region}' has not been generated. "
               f"Run: python -m src.forecasting.chain --region {region}",
    )


@router.get("/{region}/chained-forecast/summary")
def chained_forecast_summary(region: Region):
    """Backtest of the chaining procedure (error vs number of steps), method decision and caveats."""
    path = OUT_DIR / f"{region}_chain_summary.json"
    if not path.exists():
        raise _chain_not_generated(region)
    return json.loads(path.read_text())


@router.get("/{region}/chained-forecast")
def list_chained_forecasts(
    region: Region,
    limit: int = Query(100, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    state: Optional[str] = None,
    district: Optional[str] = None,
):
    df = _load_chain(region)
    if df is None:
        raise _chain_not_generated(region)
    if state:
        df = df[df["state"] == state]
    if district:
        df = df[df["district"] == district]
    df = df.drop(columns=["path_levels"], errors="ignore")
    return _records(df.iloc[offset: offset + limit])


@router.get("/{region}/candidate-sites/{candidate_site_id}/chained-forecast")
def site_chained_forecast(region: Region, candidate_site_id: str):
    df = _load_chain(region)
    if df is None:
        raise _chain_not_generated(region)
    row = df[df["candidate_site_id"] == candidate_site_id]
    if row.empty:
        raise HTTPException(
            status_code=404,
            detail="No chained estimate for this site (its last reading is too far before the target date).",
        )
    out = _records(row.iloc[:1])[0]
    probs = {k[len("prob_"):]: out.pop(k) for k in [k for k in list(out) if k.startswith("prob_")]}
    out["predicted_condition_probabilities"] = probs
    out["warnings"] = [w for w in (out.get("warnings") or "").split("; ") if w]
    out["path_levels"] = json.loads(out["path_levels"]) if out.get("path_levels") else []
    return out
