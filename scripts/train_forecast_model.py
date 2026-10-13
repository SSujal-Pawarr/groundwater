"""Train a Maharashtra groundwater-level regression forecast.

Example (from the repository root)::

    python scripts/train_forecast_model.py --target-date 2026-06-06

The horizon is measured from the latest date in the normalized dataset. Training
uses exact calendar-day targets at that same horizon, so missing dates are kept
as missing rather than interpolated. The chronological holdout is measured
against a persistence baseline before the final model is refit and saved.

This script predicts the numeric groundwater level only. M11 flood potential
has no observed flood ground-truth labels, and M12 Maharashtra structural stress
requires at least five years of history. Neither future flood probabilities nor
Maharashtra stress states are inferred or included in the model output.
"""
from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Sequence

import duckdb
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = ROOT / "data" / "processed" / "maharashtra" / "maharashtra_normalized.parquet"
DEFAULT_MODEL_DIR = ROOT / "models" / "groundwater_forecast"
DEFAULT_FORECAST_DIR = ROOT / "data" / "future_forecast"
LOGGER = logging.getLogger("groundwater_forecast")

# Features are all known at the forecast origin. Rolling statistics use only
# daily observations up to and including that origin; the target is strictly later.
FEATURE_COLUMNS = [
    "last_observed_level",
    "level_lag_1d",
    "level_lag_7d",
    "level_lag_30d",
    "rolling_mean_7d",
    "rolling_mean_30d",
    "rolling_std_7d",
    "observation_count_7d",
    "observation_count_30d",
    "days_since_last_observation",
    "target_month_sin",
    "target_month_cos",
    "target_day_sin",
    "target_day_cos",
    "target_year",
    "horizon_days",
    "latitude",
    "longitude",
    "elevation_msl",
]

OPTIONAL_NUMERIC_COLUMNS = ("latitude", "longitude", "elevation_msl")
OPTIONAL_STRING_COLUMNS = ("station_name", "state", "district")
MIN_TRAINING_ROWS = 500
MIN_TEST_ROWS = 100
MAX_ORIGIN_AGE_DAYS = 7


@dataclass(frozen=True)
class TrainingReport:
    region: str
    target: str
    target_date: str
    data_through: str
    horizon_days: int
    source_age_days: int
    training_rows: int
    test_rows: int
    forecast_sites: int
    stale_sites_skipped: int
    temporal_test_start: str
    model_metrics: dict[str, float]
    persistence_metrics: dict[str, float]
    unsupported_targets: dict[str, str]


def configure_logging(verbose: bool = False) -> None:
    """Configure concise console logging without changing root handlers twice."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )


def load_observations(parquet_path: Path) -> pd.DataFrame:
    """Load normalized Maharashtra records through DuckDB into pandas.

    Only columns needed by the level forecast are selected. If the normalized
    schema has ``is_analytics_ready``, only records explicitly marked ready are
    retained. Optional geographic columns are allowed to be absent.
    """
    if not parquet_path.is_file():
        raise FileNotFoundError(f"Normalized Maharashtra Parquet file not found: {parquet_path}")

    try:
        with duckdb.connect(database=":memory:", read_only=False) as connection:
            schema = connection.execute(
                "DESCRIBE SELECT * FROM read_parquet(?)", [str(parquet_path)]
            ).fetchdf()
            available = set(schema["column_name"].astype(str))
            required = {"candidate_site_id", "observation_timestamp", "water_level_raw"}
            missing = sorted(required - available)
            if missing:
                raise ValueError(f"Normalized dataset is missing required columns: {', '.join(missing)}")

            selections = [
                'CAST("candidate_site_id" AS VARCHAR) AS candidate_site_id',
                'TRY_CAST("observation_timestamp" AS TIMESTAMP) AS observation_timestamp',
                'TRY_CAST("water_level_raw" AS DOUBLE) AS water_level_raw',
            ]
            for column in OPTIONAL_NUMERIC_COLUMNS:
                if column in available:
                    selections.append(f'TRY_CAST("{column}" AS DOUBLE) AS "{column}"')
                else:
                    selections.append(f'CAST(NULL AS DOUBLE) AS "{column}"')
            for column in OPTIONAL_STRING_COLUMNS:
                if column in available:
                    selections.append(f'TRY_CAST("{column}" AS VARCHAR) AS "{column}"')
                else:
                    selections.append(f'CAST(NULL AS VARCHAR) AS "{column}"')

            where = ['"water_level_raw" IS NOT NULL', '"observation_timestamp" IS NOT NULL']
            if "is_analytics_ready" in available:
                where.append('TRY_CAST("is_analytics_ready" AS BOOLEAN) IS TRUE')

            query = (
                f"SELECT {', '.join(selections)} "
                "FROM read_parquet(?) "
                f"WHERE {' AND '.join(where)}"
            )
            frame = connection.execute(query, [str(parquet_path)]).fetchdf()
    except (duckdb.Error, OSError) as exc:
        raise RuntimeError(f"Could not read normalized Parquet data at {parquet_path}: {exc}") from exc

    frame["observation_timestamp"] = pd.to_datetime(frame["observation_timestamp"], errors="coerce")
    frame = frame.dropna(subset=["candidate_site_id", "observation_timestamp", "water_level_raw"])
    frame["date"] = frame["observation_timestamp"].dt.normalize()
    if frame.empty:
        raise ValueError("No valid analytics-ready groundwater observations were found.")
    return frame


def aggregate_daily(observations: pd.DataFrame) -> pd.DataFrame:
    """Aggregate 6-hourly observations to a daily site mean, without filling gaps."""
    grouping = ["candidate_site_id", "date"]
    aggregations: dict[str, tuple[str, str]] = {"water_level": ("water_level_raw", "mean")}
    for column in OPTIONAL_NUMERIC_COLUMNS:
        aggregations[column] = (column, "first")
    for column in OPTIONAL_STRING_COLUMNS:
        aggregations[column] = (column, "first")
    daily = observations.groupby(grouping, as_index=False, sort=True).agg(**aggregations)
    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.sort_values(grouping).reset_index(drop=True)
    if daily["candidate_site_id"].nunique() < 2:
        LOGGER.warning("Fewer than two monitoring sites are available; spatial generalization is limited.")
    return daily


def _feature_panel(site_data: pd.DataFrame, data_end: pd.Timestamp, horizon_days: int) -> pd.DataFrame:
    """Build daily, past-only features and exact-horizon labels for one site."""
    site_data = site_data.sort_values("date").drop_duplicates("date", keep="last")
    first_date = pd.Timestamp(site_data["date"].min()).normalize()
    target_end = data_end + pd.Timedelta(days=horizon_days)
    calendar = pd.date_range(first_date, target_end, freq="D")
    observed = site_data.set_index("date")["water_level"].reindex(calendar).astype(float)

    # Missing calendar days remain NaN. Forward fill is used only for the explicit
    # latest-known-level feature; it is never used to create training labels.
    last_observed_level = observed.ffill()
    observed_dates = pd.Series(calendar, index=calendar).where(observed.notna()).ffill()
    days_since_last = (pd.Series(calendar, index=calendar) - observed_dates).dt.days.astype(float)

    target_date = pd.Series(calendar, index=calendar).shift(-horizon_days)
    month = target_date.dt.month.astype(float)
    day_of_year = target_date.dt.dayofyear.astype(float)
    month_angle = 2.0 * np.pi * (month - 1.0) / 12.0
    day_angle = 2.0 * np.pi * (day_of_year - 1.0) / 365.2425
    rolling_source = observed

    metadata = site_data.iloc[-1]
    panel = pd.DataFrame(index=calendar)
    panel["candidate_site_id"] = str(metadata["candidate_site_id"])
    panel["origin_date"] = calendar
    panel["target_date"] = target_date.values
    panel["last_observed_level"] = last_observed_level.values
    panel["level_lag_1d"] = observed.shift(1).values
    panel["level_lag_7d"] = observed.shift(7).values
    panel["level_lag_30d"] = observed.shift(30).values
    panel["rolling_mean_7d"] = rolling_source.rolling(7, min_periods=3).mean().values
    panel["rolling_mean_30d"] = rolling_source.rolling(30, min_periods=10).mean().values
    panel["rolling_std_7d"] = rolling_source.rolling(7, min_periods=3).std().values
    panel["observation_count_7d"] = rolling_source.rolling(7, min_periods=1).count().values
    panel["observation_count_30d"] = rolling_source.rolling(30, min_periods=1).count().values
    panel["days_since_last_observation"] = days_since_last.values
    panel["target_month_sin"] = np.sin(month_angle.values)
    panel["target_month_cos"] = np.cos(month_angle.values)
    panel["target_day_sin"] = np.sin(day_angle.values)
    panel["target_day_cos"] = np.cos(day_angle.values)
    panel["target_year"] = target_date.dt.year.values.astype(float)
    panel["horizon_days"] = float(horizon_days)
    for column in OPTIONAL_NUMERIC_COLUMNS:
        panel[column] = float(metadata[column]) if pd.notna(metadata[column]) else np.nan
    for column in OPTIONAL_STRING_COLUMNS:
        panel[column] = metadata[column] if pd.notna(metadata[column]) else None
    panel["target_water_level"] = observed.shift(-horizon_days).values
    panel["current_observation"] = observed.values
    panel["observed_on_origin"] = observed.notna().values
    return panel


def build_training_and_forecast_frames(
    daily: pd.DataFrame,
    target_date: pd.Timestamp,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Timestamp, int]:
    """Create exact-day training pairs and one latest-origin forecast row per site."""
    data_end = pd.Timestamp(daily["date"].max()).normalize()
    horizon_days = int((target_date - data_end).days)
    if horizon_days <= 0:
        raise ValueError(f"Target date {target_date.date()} must be after data end {data_end.date()}.")

    panels = [
        _feature_panel(site_data, data_end, horizon_days)
        for _, site_data in daily.groupby("candidate_site_id", sort=False)
    ]
    all_rows = pd.concat(panels, ignore_index=True)
    training = all_rows.loc[
        all_rows["target_water_level"].notna()
        & all_rows["observed_on_origin"]
        & all_rows["target_date"].notna()
    ].copy()
    forecast = all_rows.loc[
        (all_rows["origin_date"] == data_end)
        & all_rows["last_observed_level"].notna()
        & (all_rows["days_since_last_observation"] <= MAX_ORIGIN_AGE_DAYS)
    ].copy()
    if forecast.empty:
        raise ValueError(
            f"No site has a valid observation within {MAX_ORIGIN_AGE_DAYS} days of the dataset end "
            f"({data_end.date()}); refusing to produce stale site forecasts."
        )
    if training.empty:
        raise ValueError(
            f"No exact {horizon_days}-day training pairs are available. "
            "Try a nearer target date or provide more history."
        )
    return training, forecast, data_end, horizon_days


def make_model(random_state: int = 42):
    """Construct a single global model; swap this factory to compare estimators."""
    regressor = HistGradientBoostingRegressor(
        max_iter=200,
        learning_rate=0.06,
        max_leaf_nodes=31,
        l2_regularization=1.0,
        random_state=random_state,
    )
    # Imputation handles incomplete lag windows and absent optional coordinates.
    return make_pipeline(
        SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True),
        regressor,
    )


def _regression_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    return {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
        "r2": float(r2_score(actual, predicted)) if len(actual) > 1 else float("nan"),
    }


def chronological_split(
    training: pd.DataFrame,
    minimum_training_rows: int,
    minimum_test_rows: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Timestamp]:
    """Hold out the final 20% of target dates; never randomly shuffle time series."""
    unique_dates = np.sort(training["target_date"].dropna().unique())
    if len(unique_dates) < 5:
        raise ValueError("At least five distinct target dates are required for a chronological holdout.")
    split_index = min(max(int(len(unique_dates) * 0.8), 1), len(unique_dates) - 1)
    test_start = pd.Timestamp(unique_dates[split_index])
    train = training.loc[training["target_date"] < test_start]
    test = training.loc[training["target_date"] >= test_start]
    if len(train) < minimum_training_rows or len(test) < minimum_test_rows:
        raise ValueError(
            f"Insufficient chronological pairs: train={len(train)} (minimum {minimum_training_rows}), "
            f"test={len(test)} (minimum {minimum_test_rows})."
        )
    return train, test, test_start


def train_forecast(
    observations: pd.DataFrame,
    target_date: pd.Timestamp,
    minimum_training_rows: int = MIN_TRAINING_ROWS,
    minimum_test_rows: int = MIN_TEST_ROWS,
    random_state: int = 42,
) -> tuple[object, pd.DataFrame, TrainingReport]:
    """Evaluate on a time holdout, compare persistence, then refit on all pairs."""
    daily = aggregate_daily(observations)
    training, forecast, data_end, horizon_days = build_training_and_forecast_frames(daily, target_date)
    train, test, test_start = chronological_split(training, minimum_training_rows, minimum_test_rows)

    validation_model = make_model(random_state)
    validation_model.fit(train[FEATURE_COLUMNS], train["target_water_level"])
    model_predictions = validation_model.predict(test[FEATURE_COLUMNS])
    persistence_predictions = test["last_observed_level"].to_numpy(dtype=float)
    actual = test["target_water_level"].to_numpy(dtype=float)
    model_metrics = _regression_metrics(actual, model_predictions)
    persistence_metrics = _regression_metrics(actual, persistence_predictions)

    # Fit the saved estimator on all valid pairs only after the holdout metrics
    # have been recorded. No held-out target is used for evaluation fitting.
    final_model = make_model(random_state)
    final_model.fit(training[FEATURE_COLUMNS], training["target_water_level"])
    forecasts = forecast[["candidate_site_id", "origin_date", "target_date", "last_observed_level"]].copy()
    forecasts["predicted_water_level"] = final_model.predict(forecast[FEATURE_COLUMNS])
    forecasts["horizon_days"] = horizon_days
    forecasts["water_level_unit"] = "meters"
    forecasts["data_through"] = data_end.date().isoformat()
    forecasts["forecast_scope"] = "water_level_regression_only"
    forecasts["flood_probability"] = np.nan
    forecasts["stress_state"] = "NOT_FORECAST"

    source_age_days = max((pd.Timestamp(date.today()) - data_end).days, 0)
    report = TrainingReport(
        region="maharashtra",
        target="daily mean water_level_raw",
        target_date=target_date.date().isoformat(),
        data_through=data_end.date().isoformat(),
        horizon_days=horizon_days,
        source_age_days=source_age_days,
        training_rows=int(len(train)),
        test_rows=int(len(test)),
        forecast_sites=int(len(forecasts)),
        stale_sites_skipped=int(daily["candidate_site_id"].nunique() - len(forecasts)),
        temporal_test_start=test_start.date().isoformat(),
        model_metrics=model_metrics,
        persistence_metrics=persistence_metrics,
        unsupported_targets={
            "flood_probability": "No flood ground-truth labels exist; M11 is retrospective, rule-based potential, not a flood probability.",
            "stress_state": "M12 Maharashtra structural stress requires at least five years of history; this dataset is too short.",
        },
    )
    return final_model, forecasts, report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_PATH, help="Normalized Maharashtra Parquet file.")
    parser.add_argument("--target-date", type=date.fromisoformat, required=True,
                        help="Future date to forecast (YYYY-MM-DD); training uses the same exact day horizon.")
    parser.add_argument("--model-out", type=Path, help="Model output path; defaults to models/groundwater_forecast/.")
    parser.add_argument("--forecast-out", type=Path, help="CSV output path; defaults to data/future_forecast/.")
    parser.add_argument("--min-train-rows", type=int, default=MIN_TRAINING_ROWS)
    parser.add_argument("--min-test-rows", type=int, default=MIN_TEST_ROWS)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    configure_logging(args.verbose)
    try:
        target_date = pd.Timestamp(args.target_date)
        observations = load_observations(args.data)
        LOGGER.info(
            "Loaded %s valid observations across %s sites (%s through %s).",
            f"{len(observations):,}",
            f"{observations['candidate_site_id'].nunique():,}",
            observations["date"].min().date(),
            observations["date"].max().date(),
        )
        model, forecasts, report = train_forecast(
            observations,
            target_date,
            minimum_training_rows=args.min_train_rows,
            minimum_test_rows=args.min_test_rows,
            random_state=args.random_state,
        )
        model_path = args.model_out or DEFAULT_MODEL_DIR / f"maharashtra_level_h{report.horizon_days}.joblib"
        forecast_path = args.forecast_out or DEFAULT_FORECAST_DIR / f"maharashtra_level_h{report.horizon_days}.csv"
        report_path = forecast_path.with_suffix(".metrics.json")
        model_path.parent.mkdir(parents=True, exist_ok=True)
        forecast_path.parent.mkdir(parents=True, exist_ok=True)

        model_artifact = {
            "model": model,
            "feature_columns": FEATURE_COLUMNS,
            "target": report.target,
            "region": report.region,
            "horizon_days": report.horizon_days,
            "target_date": report.target_date,
            "data_through": report.data_through,
            "metrics": asdict(report),
            "unsupported_targets": report.unsupported_targets,
        }
        joblib.dump(model_artifact, model_path)
        forecasts.to_csv(forecast_path, index=False)
        report_path.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")

        LOGGER.info("Saved model to %s", model_path)
        LOGGER.info("Saved %s site forecasts to %s", len(forecasts), forecast_path)
        LOGGER.info("Saved chronological evaluation report to %s", report_path)
        LOGGER.info("Model MAE %.4f; persistence baseline MAE %.4f", report.model_metrics["mae"], report.persistence_metrics["mae"])
        if report.source_age_days > 30:
            LOGGER.warning(
                "Dataset ends %s days before today. Forecasts are relative to data_through, not current conditions.",
                report.source_age_days,
            )
        LOGGER.warning("Flood probability and structural stress state are intentionally not forecast.")
        return 0
    except (FileNotFoundError, ValueError, RuntimeError, duckdb.Error, OSError) as exc:
        LOGGER.error("Forecast training failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())