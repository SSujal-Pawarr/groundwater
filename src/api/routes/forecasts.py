"""API for the trained Maharashtra groundwater-level regression model."""
from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from src.forecasting.chain import MAX_STEPS, add_step_lags, chained_forecast
from src.forecasting.config import CONDITION_ORDER, CONFIGS, MODEL_DIR as CHAIN_MODEL_DIR, OUT_DIR as FUTURE_FORECAST_DIR
from src.forecasting.data import load_observations as load_forecast_observations, season_of_month_map
from src.forecasting.features import build_features
from scripts.train_forecast_model import (
    DEFAULT_DATA_PATH,
    FEATURE_COLUMNS,
    aggregate_daily,
    build_training_and_forecast_frames,
    load_observations,
)

LOGGER = logging.getLogger(__name__)
router = APIRouter(prefix="/api/forecast", tags=["regression-forecast"])

ROOT = Path(__file__).resolve().parents[3]
MODEL_DIR = ROOT / "models" / "groundwater_forecast"
DATA_PATH = DEFAULT_DATA_PATH
CHAIN_SUMMARY_PATH = FUTURE_FORECAST_DIR / "maharashtra_chain_summary.json"
_model_cache: tuple[int, dict[str, Any]] | None = None
_daily_cache: tuple[int, pd.DataFrame] | None = None
_chain_context_cache: tuple[tuple[int, ...], dict[str, Any]] | None = None
_chain_results_cache: dict[tuple[tuple[int, ...], str], tuple[pd.DataFrame, pd.DataFrame]] = {}
_site_chain_cache: dict[tuple[tuple[int, ...], str, str], tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]] = {}
_direct_joblib_levels_cache: dict[str, dict[str, float]] = {}
_direct_artifact_cache: tuple[int, pd.DataFrame] | None = None

UNSUPPORTED_TARGETS = {
    "flood_probability": (
        "Not available: the dataset has no observed flood ground-truth labels; "
        "M11 is retrospective rule-based potential, not a flood probability."
    ),
    "stress_state": (
        "Not forecast: Maharashtra structural stress requires at least five years "
        "of history, while this dataset is shorter."
    ),
}


def _latest_model_path() -> Path:
    candidates = list(MODEL_DIR.glob("maharashtra_level_h*.joblib"))
    if not candidates:
        raise HTTPException(
            status_code=503,
            detail=(
                f"No Maharashtra regression model found in {MODEL_DIR}. "
                "Train one with scripts/train_forecast_model.py."
            ),
        )
    return max(candidates, key=lambda path: path.stat().st_mtime_ns)


def _load_model() -> tuple[dict[str, Any], Path]:
    global _model_cache
    path = _latest_model_path()
    modified = path.stat().st_mtime_ns
    if _model_cache is None or _model_cache[0] != modified:
        try:
            artifact = joblib.load(path)
        except Exception as exc:
            LOGGER.exception("Unable to load forecast model at %s", path)
            raise HTTPException(status_code=500, detail="Saved forecast model could not be loaded.") from exc
        if not isinstance(artifact, dict) or "model" not in artifact:
            raise HTTPException(status_code=500, detail="Saved forecast model has an unsupported format.")
        _model_cache = (modified, artifact)
    return _model_cache[1], path


def _load_daily_data() -> pd.DataFrame:
    global _daily_cache
    if not DATA_PATH.is_file():
        raise HTTPException(status_code=503, detail=f"Normalized Maharashtra data is missing: {DATA_PATH}")
    modified = DATA_PATH.stat().st_mtime_ns
    if _daily_cache is None or _daily_cache[0] != modified:
        try:
            observations = load_observations(DATA_PATH)
            _daily_cache = (modified, aggregate_daily(observations))
        except (OSError, ValueError, RuntimeError) as exc:
            LOGGER.exception("Unable to load normalized Maharashtra data")
            raise HTTPException(status_code=500, detail="Normalized Maharashtra data could not be loaded.") from exc
    return _daily_cache[1]


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert pandas/numpy values and NaNs into JSON-safe Python values."""
    return json.loads(frame.to_json(orient="records", date_format="iso"))


def _load_chain_context() -> dict[str, Any]:
    """Load cached step models and feature context used for arbitrary target dates."""
    global _chain_context_cache
    cfg = CONFIGS["maharashtra"]
    if not CHAIN_SUMMARY_PATH.is_file():
        raise HTTPException(
            status_code=503,
            detail="M17 chained forecast models are unavailable. Run `python -m src.forecasting.chain --region maharashtra` first.",
        )
    try:
        summary = json.loads(CHAIN_SUMMARY_PATH.read_text(encoding="utf-8"))
        step_months = int(summary["step_months"])
        reg_path = CHAIN_MODEL_DIR / f"maharashtra_step{step_months}_regressor.json"
        cls_path = CHAIN_MODEL_DIR / f"maharashtra_step{step_months}_classifier.json"
        required_paths = (DATA_PATH, CHAIN_SUMMARY_PATH, reg_path, cls_path)
        if any(not path.is_file() for path in required_paths):
            missing = [str(path) for path in required_paths if not path.is_file()]
            raise HTTPException(status_code=503, detail=f"Forecast inputs are missing: {', '.join(missing)}")

        signature = tuple(path.stat().st_mtime_ns for path in required_paths)
        if _chain_context_cache is not None and _chain_context_cache[0] == signature:
            return _chain_context_cache[1]

        from xgboost import XGBClassifier, XGBRegressor

        regressor = XGBRegressor()
        regressor.load_model(str(reg_path))
        classifier = XGBClassifier()
        classifier.load_model(str(cls_path))
        observations = load_forecast_observations(cfg)
        features = build_features("maharashtra", observations)
        features = add_step_lags(features, observations, "maharashtra", step_months, cfg.tolerance_days[step_months])
        daily_observations = aggregate_daily(load_observations(DATA_PATH))
        backtest = {
            int(step): metrics
            for step, metrics in summary.get("chain_backtest", {}).get("by_steps", {}).items()
        }
        context = {
            "signature": signature,
            "cfg": cfg,
            "step_months": step_months,
            "regressor": regressor,
            "classifier": classifier,
            "observations": observations,
            "features": features,
            "daily_observations": daily_observations,
            "season_map": season_of_month_map(observations),
            "group_table": observations.groupby(["candidate_site_id", "group"])["value"].mean(),
            "backtest": backtest,
            "summary": summary,
        }
        _chain_context_cache = (signature, context)
        _chain_results_cache.clear()
        return context
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.exception("Unable to load saved M17 chained forecast models")
        raise HTTPException(status_code=500, detail="Saved chained forecast models could not be loaded.") from exc


def _run_chained_forecast(target_date: date, site_id: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    context = _load_chain_context()
    target = pd.Timestamp(target_date)
    data_end = context["observations"]["date"].max().normalize()
    if target <= data_end:
        raise HTTPException(status_code=422, detail=f"Target date must be after the data end ({data_end.date()}).")

    if site_id:
        site_key = (context["signature"], target_date.isoformat(), site_id)
        cached_site = _site_chain_cache.get(site_key)
        if cached_site is not None:
            return cached_site[0].copy(), cached_site[1], cached_site[2]

        site_feats = context["features"][context["features"]["candidate_site_id"] == site_id]
        site_obs = context["observations"][context["observations"]["candidate_site_id"] == site_id]
        if site_feats.empty:
            raise HTTPException(status_code=404, detail=f"Site {site_id} not found in model features.")
        try:
            forecasts, _ = chained_forecast(
                context["cfg"],
                "maharashtra",
                context["step_months"],
                site_feats,
                site_obs,
                context["regressor"],
                context["classifier"],
                context["group_table"],
                context["season_map"],
                context["backtest"],
                target,
                MAX_STEPS["maharashtra"],
            )
        except Exception as exc:
            LOGGER.exception("M17 chained forecast failed for site %s on %s", site_id, target_date)
            raise HTTPException(status_code=500, detail="M17 chained forecast could not be generated.") from exc
        station_metadata = (
            context["daily_observations"][context["daily_observations"]["candidate_site_id"] == site_id][["candidate_site_id", "station_name"]]
            .drop_duplicates("candidate_site_id", keep="last")
        )
        forecasts = forecasts.merge(station_metadata, on="candidate_site_id", how="left")
        res_tuple = (forecasts, context["daily_observations"], context["summary"])
        _site_chain_cache[site_key] = res_tuple
        while len(_site_chain_cache) > 200:
            _site_chain_cache.pop(next(iter(_site_chain_cache)))
        return forecasts, context["daily_observations"], context["summary"]

    cache_key = (context["signature"], target_date.isoformat())
    cached = _chain_results_cache.get(cache_key)
    if cached is None:
        try:
            forecasts, _ = chained_forecast(
                context["cfg"],
                "maharashtra",
                context["step_months"],
                context["features"],
                context["observations"],
                context["regressor"],
                context["classifier"],
                context["group_table"],
                context["season_map"],
                context["backtest"],
                target,
                MAX_STEPS["maharashtra"],
            )
        except Exception as exc:
            LOGGER.exception("M17 chained forecast failed for %s", target_date)
            raise HTTPException(status_code=500, detail="M17 chained forecast could not be generated.") from exc
        if forecasts.empty:
            maximum = data_end + pd.DateOffset(months=context["step_months"] * MAX_STEPS["maharashtra"])
            raise HTTPException(
                status_code=422,
                detail=f"No sites are eligible for this target date. The current model supports dates through {maximum.date()}.",
            )
        station_metadata = (
            context["daily_observations"][["candidate_site_id", "station_name"]]
            .drop_duplicates("candidate_site_id", keep="last")
        )
        forecasts = forecasts.merge(station_metadata, on="candidate_site_id", how="left")
        cached = (forecasts, context["daily_observations"])
        _chain_results_cache[cache_key] = cached
        while len(_chain_results_cache) > 4:
            _chain_results_cache.pop(next(iter(_chain_results_cache)))
    return cached[0].copy(), cached[1], context["summary"]


def _direct_model_levels(artifact: dict[str, Any], target_date: date, daily: pd.DataFrame) -> dict[str, float]:
    """Expose the joblib direct regression only for the exact date it was trained for."""
    target_str = target_date.isoformat()
    if str(artifact.get("target_date")) != target_str:
        return {}
    if target_str in _direct_joblib_levels_cache:
        return _direct_joblib_levels_cache[target_str]
    try:
        _, forecast_frame, _, _ = build_training_and_forecast_frames(daily, pd.Timestamp(target_date))
        columns = artifact.get("feature_columns", FEATURE_COLUMNS)
        values = artifact["model"].predict(forecast_frame[columns])
        result = dict(zip(forecast_frame["candidate_site_id"].astype(str), map(float, values)))
        _direct_joblib_levels_cache[target_str] = result
        return result
    except Exception:
        LOGGER.exception("Direct joblib forecast failed for its trained target date")
        return {}


def _load_direct_m17(target_date: date) -> dict[str, float]:
    """Load persisted direct M17 values only when their artifact target matches."""
    global _direct_artifact_cache
    path = FUTURE_FORECAST_DIR / "maharashtra_future_forecast.parquet"
    if not path.is_file():
        return {}
    modified = path.stat().st_mtime_ns
    try:
        if _direct_artifact_cache is None or _direct_artifact_cache[0] != modified:
            _direct_artifact_cache = (modified, pd.read_parquet(path))
        frame = _direct_artifact_cache[1]
        matching = frame[pd.to_datetime(frame["target_date"]).dt.date == target_date]
        return dict(zip(matching["candidate_site_id"].astype(str), matching["predicted_water_level"].astype(float)))
    except Exception:
        LOGGER.exception("Unable to read persisted direct M17 forecast artifact")
        return {}


@router.get("/maharashtra")
def get_maharashtra_regression_forecast(
    target_date: date | None = Query(default=None, description="The trained target date (YYYY-MM-DD)."),
    candidate_site_id: str | None = Query(default=None, min_length=1),
):
    """Return forecasts for a selected date using available trained project models.

    The recursive M17 step models support multiple future dates. Fixed-horizon
    joblib and direct-M17 outputs are included only when their saved target date
    exactly matches the request.
    """
    artifact, model_path = _load_model()
    try:
        default_date = date.fromisoformat(str(artifact["target_date"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail="Saved joblib model is missing valid target-date metadata.") from exc
    requested_date = target_date or default_date
    context = _load_chain_context()

    try:
        forecasts, daily, chain_summary = _run_chained_forecast(requested_date, site_id=candidate_site_id)
    except TypeError:
        forecasts, daily, chain_summary = _run_chained_forecast(requested_date)

    obs_df = context.get("daily_observations") if "daily_observations" in context else daily
    if "station_name" in obs_df.columns:
        meta = obs_df[["candidate_site_id", "station_name"]].drop_duplicates("candidate_site_id", keep="last")
    else:
        meta = forecasts[["candidate_site_id", "station_name"]].drop_duplicates("candidate_site_id", keep="last")

    if "district" in obs_df.columns:
        meta = meta.merge(obs_df[["candidate_site_id", "district"]].drop_duplicates("candidate_site_id", keep="last"), on="candidate_site_id", how="left")
    elif "observations" in context and "district" in context["observations"].columns:
        meta = meta.merge(context["observations"][["candidate_site_id", "district"]].drop_duplicates("candidate_site_id", keep="last"), on="candidate_site_id", how="left")
    else:
        meta["district"] = None

    dropdown_locations = [
        {"candidate_site_id": r.candidate_site_id, "station_name": getattr(r, "station_name", None), "district": getattr(r, "district", None)}
        for r in meta.itertuples(index=False)
    ]
    direct_joblib = _direct_model_levels(artifact, requested_date, daily)
    direct_m17 = _load_direct_m17(requested_date)
    forecasts = forecasts.copy()
    forecasts["trained_regression_water_level"] = forecasts["candidate_site_id"].map(direct_joblib)
    forecasts["direct_m17_water_level"] = forecasts["candidate_site_id"].map(direct_m17)
    forecasts = forecasts.sort_values("candidate_site_id")

    location_columns = [
        "candidate_site_id", "station_name", "district", "state", "lat", "lon", "water_level_unit",
        "origin_date", "origin_water_level", "requested_target_date", "predicted_for_date",
        "predicted_water_level", "predicted_change", "predicted_lower_80", "predicted_upper_80",
        "interval_basis", "method", "method_reason", "n_steps", "step_months", "backtested_steps",
        "data_gap_days", "predicted_condition_state", "predicted_state_confidence",
        "trained_regression_water_level", "direct_m17_water_level", "warnings", "path_levels",
        *[f"prob_{state}" for state in CONDITION_ORDER],
    ]
    serialized = _records(forecasts[location_columns])
    locations: list[dict[str, Any]] = []
    for row in serialized:
        row["latitude"] = row.pop("lat")
        row["longitude"] = row.pop("lon")
        row["forecast_origin_date"] = row.get("origin_date")
        row["last_observation_date"] = row.get("origin_date")
        row["target_date"] = requested_date.isoformat()
        row["predicted_condition_probabilities"] = {
            key.removeprefix("prob_"): row.pop(key)
            for key in list(row)
            if key.startswith("prob_")
        }
        row["warnings"] = [warning for warning in (row.get("warnings") or "").split("; ") if warning]
        try:
            row["path_levels"] = json.loads(row.get("path_levels") or "[]")
        except (TypeError, json.JSONDecodeError):
            row["path_levels"] = []
        locations.append(row)

    selected_location = None
    if candidate_site_id:
        selected_location = next((row.copy() for row in locations if row["candidate_site_id"] == candidate_site_id), None)
        if selected_location is None:
            raise HTTPException(status_code=404, detail="No forecast is available for this site and target date.")
        origin = pd.Timestamp(selected_location["origin_date"])
        site_history = daily[
            (daily["candidate_site_id"] == candidate_site_id) & (daily["date"] <= origin)
        ].sort_values("date").tail(60)
        selected_location["history"] = [
            {"date": pd.Timestamp(row.date).date().isoformat(), "water_level": float(row.water_level)}
            for row in site_history.itertuples(index=False)
        ]

    context = _load_chain_context()
    data_end = context["observations"]["date"].max().normalize()
    maximum_target_date = data_end + pd.DateOffset(
        months=context["step_months"] * MAX_STEPS["maharashtra"]
    )
    direct_date = str(artifact.get("target_date"))
    persisted_direct_file = FUTURE_FORECAST_DIR / "maharashtra_future_forecast.parquet"
    direct_m17_date = None
    if persisted_direct_file.is_file():
        try:
            direct_df = _direct_artifact_cache[1] if _direct_artifact_cache else pd.read_parquet(persisted_direct_file)
            if "target_date" in direct_df and not direct_df.empty:
                direct_m17_date = str(pd.to_datetime(direct_df["target_date"]).max().date())
        except Exception:
            LOGGER.exception("Unable to read direct-M17 target date")

    return {
        "region": "maharashtra",
        "target_date": requested_date.isoformat(),
        "data_through": data_end.date().isoformat(),
        "max_target_date": maximum_target_date.date().isoformat(),
        "source_age_days": max((pd.Timestamp(date.today()) - data_end).days, 0),
        "step_months": context["step_months"],
        "water_level_unit": "meters",
        "locations": dropdown_locations if candidate_site_id else locations,
        "selected_location": selected_location,
        "models": {
            "chained_m17": {"available": True, "target_date": requested_date.isoformat()},
            "trained_gradient_boosting": {
                "available": requested_date.isoformat() == direct_date,
                "trained_target_date": direct_date,
                "model_file": model_path.name,
            },
            "direct_m17": {
                "available": bool(direct_m17),
                "trained_target_date": direct_m17_date,
            },
        },
        "chain_backtest": chain_summary.get("chain_backtest", {}),
        "unsupported_targets": UNSUPPORTED_TARGETS,
    }