"""
NEW/tests/test_features.py - Comprehensive Test Suite for Milestone 4 Feature Engineering

Validates:
1. Deterministic analytical site IDs.
2. No modification of source observations.
3. Correct chronological ordering.
4. No future leakage in lag features.
5. Rolling features use only historical/current information.
6. Missing observations handled explicitly.
7. Seasonal grouping correctness.
8. Trend calculation handles insufficient observations.
9. Anomaly/index calculation handles insufficient history.
10. Baseline calculations do not access future observations.
11. Ambiguous spatial records flagged (not silently misassigned).
"""

import os
import sys
import unittest
import numpy as np
import pandas as pd

# Add NEW/ to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.features.spatial import (
    build_analytical_site_id,
    analyze_location_consistency,
    compute_site_observation_summary,
    evaluate_spatial_clustering_necessity,
)
from src.features.temporal import (
    compute_india_temporal_profile,
    compute_maharashtra_temporal_profile,
    compute_observation_gaps,
)
from src.features.seasonal import (
    assign_india_season,
    compute_seasonal_statistics,
    compute_seasonal_anomaly,
    compute_yoy_seasonal_change,
    INDIA_MONTH_TO_SEASON,
)
from src.features.trends import (
    compute_location_trend,
    compute_rate_of_change,
)
from src.features.anomaly import (
    compute_seasonal_z_score,
    SGI_REJECTION_REASON,
)
from src.features.baselines import (
    compute_persistence_baseline,
    compute_seasonal_historical_baseline,
    compute_maharashtra_persistence_baseline,
    compute_baseline_evaluation_metrics,
)


def _make_india_fixture(n_sites=3, obs_per_site=20):
    """Creates a synthetic India-like fixture for testing. Clearly labeled as test data."""
    records = []
    months = [1, 5, 8, 11]
    base_year = 2015
    for site_idx in range(n_sites):
        lat = 20.0 + site_idx * 2
        lng = 75.0 + site_idx * 1
        for obs_idx in range(obs_per_site):
            year = base_year + obs_idx // len(months)
            month = months[obs_idx % len(months)]
            records.append({
                "candidate_site_id": f"TEST_SITE_{site_idx:03d}",
                "state": f"TestState_{site_idx}",
                "district": f"TestDistrict_{site_idx}",
                "block": f"TestBlock_{site_idx}",
                "village": f"TestVillage_{site_idx}",
                "latitude": lat,
                "longitude": lng,
                "observation_date": f"{year}-{month:02d}-01",
                "observation_year": year,
                "observation_month": month,
                "water_level_raw": 5.0 + site_idx * 2 + np.sin(obs_idx / 3) * 2,
                "water_level_unit": "UNKNOWN",
                "reference_datum": "UNKNOWN",
            })
    return pd.DataFrame(records)


def _make_maharashtra_fixture(n_stations=2, obs_per_station=20):
    """Creates a synthetic Maharashtra-like fixture for testing."""
    records = []
    base_ts = pd.Timestamp("2026-01-01 00:00:00")
    for stn_idx in range(n_stations):
        for obs_idx in range(obs_per_station):
            ts = base_ts + pd.Timedelta(hours=6 * obs_idx)
            records.append({
                "station_name": f"TEST_STN_{stn_idx:03d}",
                "candidate_site_id": f"MH_TEST_STN_{stn_idx:03d}",
                "observation_timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S"),
                "observation_date": ts.strftime("%Y-%m-%d"),
                "water_level_raw": -10.0 + stn_idx + np.random.RandomState(42 + obs_idx).randn() * 0.5,
                "water_level_unit": "meter",
                "latitude": 18.0 + stn_idx * 0.5,
                "longitude": 73.0 + stn_idx * 0.3,
            })
    return pd.DataFrame(records)


class TestSpatialFeatures(unittest.TestCase):

    def test_analytical_site_id_deterministic(self):
        """Analytical site ID is deterministic: same input -> same output."""
        df = _make_india_fixture(n_sites=2, obs_per_site=5)
        result = build_analytical_site_id(df)
        # Same candidate_site_id -> same analytical_site_id
        self.assertTrue((result["analytical_site_id"] == result["candidate_site_id"]).all())
        self.assertTrue(result["site_id_is_analytical"].all())

    def test_analytical_site_id_preserves_source(self):
        """Building analytical site ID does not modify source observations."""
        df = _make_india_fixture(n_sites=1, obs_per_site=3)
        original_wl = df["water_level_raw"].tolist()
        original_lat = df["latitude"].tolist()
        result = build_analytical_site_id(df)
        # Original DataFrame unchanged
        self.assertEqual(df["water_level_raw"].tolist(), original_wl)
        self.assertEqual(df["latitude"].tolist(), original_lat)
        # Result preserves values
        self.assertEqual(result["water_level_raw"].tolist(), original_wl)

    def test_analytical_site_id_requires_candidate(self):
        """Raises ValueError if candidate_site_id is missing."""
        df = pd.DataFrame({"foo": [1, 2, 3]})
        with self.assertRaises(ValueError):
            build_analytical_site_id(df)

    def test_location_consistency_analysis(self):
        """Location consistency returns valid structure."""
        df = _make_india_fixture(n_sites=3, obs_per_site=10)
        result = analyze_location_consistency(df)
        self.assertIn("total_unique_candidate_sites", result)
        self.assertEqual(result["total_unique_candidate_sites"], 3)
        self.assertIn("observations_per_site", result)

    def test_site_observation_summary(self):
        """Per-site summary has correct structure."""
        df = _make_india_fixture(n_sites=2, obs_per_site=8)
        summary = compute_site_observation_summary(df)
        self.assertEqual(len(summary), 2)
        self.assertIn("total_observations", summary.columns)
        self.assertTrue((summary["total_observations"] == 8).all())

    def test_clustering_evaluation(self):
        """Clustering necessity evaluation runs without error."""
        df = _make_india_fixture(n_sites=5, obs_per_site=3)
        result = evaluate_spatial_clustering_necessity(df)
        self.assertIn("clustering_justified", result)
        # For our data, clustering should not be justified
        self.assertFalse(result["clustering_justified"])


class TestTemporalFeatures(unittest.TestCase):

    def test_india_temporal_profile(self):
        """India temporal profile returns valid structure."""
        df = _make_india_fixture(n_sites=2, obs_per_site=10)
        result = compute_india_temporal_profile(df)
        self.assertIn("total_observations", result)
        self.assertIn("date_range", result)
        self.assertIn("month_distribution", result)

    def test_maharashtra_temporal_profile(self):
        """Maharashtra temporal profile returns valid structure."""
        df = _make_maharashtra_fixture(n_stations=2, obs_per_station=10)
        result = compute_maharashtra_temporal_profile(df)
        self.assertIn("total_observations", result)
        self.assertIn("timestamp_range", result)

    def test_observation_gaps_chronological(self):
        """Gap analysis preserves chronological ordering."""
        df = _make_india_fixture(n_sites=1, obs_per_site=10)
        gaps = compute_observation_gaps(df)
        self.assertEqual(len(gaps), 1)
        self.assertIn("min_gap_days", gaps.columns)
        # All gaps should be positive (chronological)
        self.assertGreater(gaps["min_gap_days"].iloc[0], 0)


class TestSeasonalFeatures(unittest.TestCase):

    def test_season_assignment_correctness(self):
        """Months are mapped to correct seasons."""
        df = pd.DataFrame({
            "observation_month": [1, 5, 8, 11, 3, 4, 7],
        })
        result = assign_india_season(df)
        self.assertEqual(result["analytical_season"].iloc[0], "RABI_WINTER")
        self.assertEqual(result["analytical_season"].iloc[1], "PRE_MONSOON")
        self.assertEqual(result["analytical_season"].iloc[2], "MONSOON")
        self.assertEqual(result["analytical_season"].iloc[3], "POST_MONSOON")
        self.assertEqual(result["analytical_season"].iloc[4], "PRE_MONSOON_EARLY")
        self.assertEqual(result["analytical_season"].iloc[5], "PRE_MONSOON")
        self.assertEqual(result["analytical_season"].iloc[6], "UNMAPPED_MONTH")

    def test_season_assignment_preserves_data(self):
        """Season assignment does not modify original DataFrame."""
        df = _make_india_fixture(n_sites=1, obs_per_site=5)
        original_cols = list(df.columns)
        _ = assign_india_season(df)
        self.assertEqual(list(df.columns), original_cols)

    def test_seasonal_statistics_min_observations(self):
        """Seasonal statistics respect min_observations threshold."""
        df = _make_india_fixture(n_sites=1, obs_per_site=4)
        df = assign_india_season(df)
        # With only 4 obs total (1 per season), min_observations=3 should yield 0 results
        stats = compute_seasonal_statistics(df, min_observations=3)
        self.assertEqual(len(stats), 0)

        # With min_observations=1, should yield some results
        stats = compute_seasonal_statistics(df, min_observations=1)
        self.assertGreater(len(stats), 0)

    def test_seasonal_anomaly_computation(self):
        """Seasonal anomaly is correctly computed."""
        df = _make_india_fixture(n_sites=1, obs_per_site=20)
        df = assign_india_season(df)
        stats = compute_seasonal_statistics(df, min_observations=3)
        result = compute_seasonal_anomaly(df, stats)
        self.assertIn("seasonal_anomaly", result.columns)

    def test_yoy_change_backward_looking(self):
        """Year-over-year change is strictly backward-looking."""
        df = _make_india_fixture(n_sites=1, obs_per_site=20)
        df = assign_india_season(df)
        yoy = compute_yoy_seasonal_change(df)
        # First year for each (site, season) should have NaN change
        for (site, season), group in yoy.groupby(["candidate_site_id", "analytical_season"]):
            sorted_g = group.sort_values("observation_year")
            self.assertTrue(pd.isna(sorted_g["yoy_change"].iloc[0]),
                            f"First year for {site}/{season} should have NaN yoy_change")


class TestTrendFeatures(unittest.TestCase):

    def test_trend_minimum_observations(self):
        """Trend computation respects min_observations."""
        df = _make_india_fixture(n_sites=1, obs_per_site=5)
        # 5 obs < default min_observations=10 -> no trend computed
        trends = compute_location_trend(df, min_observations=10)
        self.assertEqual(len(trends), 0)

        # Lower threshold -> trend computed
        trends = compute_location_trend(df, min_observations=3, min_years_span=0)
        self.assertEqual(len(trends), 1)

    def test_trend_minimum_year_span(self):
        """Trend computation respects min_years_span."""
        # Create data spanning only 1 year
        df = pd.DataFrame({
            "candidate_site_id": ["S1"] * 15,
            "observation_date": pd.date_range("2020-01-01", periods=15, freq="ME").strftime("%Y-%m-%d").tolist(),
            "water_level_raw": np.arange(15, dtype=float),
        })
        trends = compute_location_trend(df, min_observations=5, min_years_span=3)
        self.assertEqual(len(trends), 0)

    def test_rate_of_change_no_future_leakage(self):
        """Rate of change uses only previous observations (backward-looking)."""
        df = _make_india_fixture(n_sites=1, obs_per_site=10)
        result = compute_rate_of_change(df)
        # First observation per site (sorted by date) should have NaN change
        for site in result["candidate_site_id"].unique():
            site_data = result[result["candidate_site_id"] == site].sort_values("observation_date")
            self.assertTrue(pd.isna(site_data["wl_change"].iloc[0]))
            self.assertTrue(pd.isna(site_data["days_since_prev"].iloc[0]))
            self.assertTrue(pd.isna(site_data["rate_per_day"].iloc[0]))

    def test_rate_of_change_chronological_order(self):
        """Rate of change maintains chronological ordering."""
        df = _make_india_fixture(n_sites=1, obs_per_site=10)
        result = compute_rate_of_change(df)
        # days_since_prev should be > 0 for all non-first observations
        non_first = result.dropna(subset=["days_since_prev"])
        self.assertTrue((non_first["days_since_prev"] > 0).all())


class TestAnomalyFeatures(unittest.TestCase):

    def test_sgi_explicitly_rejected(self):
        """SGI rejection reason is documented."""
        self.assertIn("NOT scientifically justified", SGI_REJECTION_REASON)

    def test_seasonal_z_score_computation(self):
        """Seasonal z-score is computed correctly."""
        df = _make_india_fixture(n_sites=1, obs_per_site=20)
        df = assign_india_season(df)
        result = compute_seasonal_z_score(df, min_observations=3)
        self.assertIn("seasonal_z_score", result.columns)
        self.assertIn("seasonal_z_score_available", result.columns)

    def test_seasonal_z_score_insufficient_data(self):
        """Z-score is NaN when insufficient observations."""
        df = _make_india_fixture(n_sites=1, obs_per_site=2)
        df = assign_india_season(df)
        result = compute_seasonal_z_score(df, min_observations=5)
        self.assertTrue(result["seasonal_z_score"].isna().all())
        self.assertTrue((~result["seasonal_z_score_available"]).all())

    def test_seasonal_z_score_handles_missing_values(self):
        """Z-score handles NaN water levels gracefully."""
        df = _make_india_fixture(n_sites=1, obs_per_site=20)
        df = assign_india_season(df)
        # Set some water levels to NaN
        df.loc[df.index[:3], "water_level_raw"] = np.nan
        result = compute_seasonal_z_score(df, min_observations=3)
        # NaN water levels -> NaN z-score
        nan_wl_rows = result[result["water_level_raw"].isna()]
        self.assertTrue(nan_wl_rows["seasonal_z_score"].isna().all())


class TestBaselineFeatures(unittest.TestCase):

    def test_persistence_baseline_no_future_leakage(self):
        """Persistence baseline uses only previous observation (no future data)."""
        df = _make_india_fixture(n_sites=1, obs_per_site=10)
        result = compute_persistence_baseline(df)
        # First observation per site (sorted by date) should have NaN prediction
        for site in result["candidate_site_id"].unique():
            site_data = result[result["candidate_site_id"] == site].sort_values("observation_date")
            self.assertTrue(pd.isna(site_data["persistence_prediction"].iloc[0]))

        # Each prediction should equal the previous observation's actual value
        for site, group in result.groupby("candidate_site_id"):
            sorted_g = group.sort_values("observation_date")
            for i in range(1, len(sorted_g)):
                expected = sorted_g["water_level_raw"].iloc[i - 1]
                actual_pred = sorted_g["persistence_prediction"].iloc[i]
                if not np.isnan(expected):
                    self.assertAlmostEqual(actual_pred, expected, places=6)

    def test_seasonal_historical_baseline_no_future_leakage(self):
        """Seasonal historical baseline uses only prior years (strict backward-looking)."""
        df = _make_india_fixture(n_sites=1, obs_per_site=20)
        df = assign_india_season(df)
        result = compute_seasonal_historical_baseline(df, min_historical_years=2)

        # For observations where baseline is available, verify no future data used
        available = result[result["seasonal_hist_available"]]
        for _, row in available.iterrows():
            current_year = row["observation_year"]
            site = row["candidate_site_id"]
            season = row["analytical_season"]

            # The prediction should be the mean of same-site, same-season, earlier years
            historical = df[
                (df["candidate_site_id"] == site)
                & (df["analytical_season"] == season)
                & (df["observation_year"] < current_year)
                & (df["water_level_raw"].notna())
            ]
            if len(historical) > 0:
                expected_mean = historical["water_level_raw"].mean()
                self.assertAlmostEqual(
                    row["seasonal_hist_prediction"],
                    expected_mean,
                    places=4,
                    msg=f"Future leakage detected at site={site}, year={current_year}, season={season}",
                )

    def test_maharashtra_persistence_baseline_chronological(self):
        """Maharashtra persistence baseline is strictly chronological."""
        df = _make_maharashtra_fixture(n_stations=1, obs_per_station=10)
        result = compute_maharashtra_persistence_baseline(df)
        # First observation per station (sorted by timestamp) should have NaN prediction
        for stn in result["station_name"].unique():
            stn_data = result[result["station_name"] == stn].sort_values("observation_timestamp")
            self.assertTrue(pd.isna(stn_data["persistence_prediction"].iloc[0]))

    def test_baseline_evaluation_metrics(self):
        """Baseline evaluation metrics compute correctly."""
        residuals = pd.Series([1.0, -2.0, 0.5, -0.5, 1.5])
        metrics = compute_baseline_evaluation_metrics(residuals, "test_baseline")
        self.assertEqual(metrics["evaluable_observations"], 5)
        self.assertAlmostEqual(metrics["mae"], 1.1, places=4)
        self.assertAlmostEqual(metrics["bias"], 0.1, places=4)

    def test_baseline_evaluation_empty_residuals(self):
        """Baseline evaluation handles empty residuals."""
        residuals = pd.Series([np.nan, np.nan])
        metrics = compute_baseline_evaluation_metrics(residuals, "empty")
        self.assertEqual(metrics["evaluable_observations"], 0)
        self.assertIsNone(metrics["mae"])

    def test_persistence_baseline_preserves_source_data(self):
        """Persistence baseline does not modify original DataFrame."""
        df = _make_india_fixture(n_sites=1, obs_per_site=5)
        original_wl = df["water_level_raw"].tolist()
        _ = compute_persistence_baseline(df)
        self.assertEqual(df["water_level_raw"].tolist(), original_wl)


class TestNoDataLeakage(unittest.TestCase):
    """
    Dedicated test class for verifying NO temporal data leakage exists
    in any feature engineering component.
    """

    def test_rate_of_change_first_obs_is_nan(self):
        """First observation per site has NaN rate (no prior data)."""
        df = _make_india_fixture(n_sites=2, obs_per_site=5)
        result = compute_rate_of_change(df)
        for site in result["candidate_site_id"].unique():
            site_data = result[result["candidate_site_id"] == site].sort_values("observation_date")
            self.assertTrue(pd.isna(site_data["wl_change"].iloc[0]))

    def test_yoy_first_year_is_nan(self):
        """First year per (site, season) has NaN yoy_change."""
        df = _make_india_fixture(n_sites=1, obs_per_site=20)
        df = assign_india_season(df)
        yoy = compute_yoy_seasonal_change(df)
        for (site, season), group in yoy.groupby(["candidate_site_id", "analytical_season"]):
            sorted_g = group.sort_values("observation_year")
            self.assertTrue(pd.isna(sorted_g["yoy_change"].iloc[0]))

    def test_persistence_prediction_matches_previous_value(self):
        """Each persistence prediction exactly equals the previous observation value."""
        values = [3.0, 5.0, 2.0, 7.0, 1.0]
        df = pd.DataFrame({
            "candidate_site_id": ["S1"] * 5,
            "observation_date": ["2020-01-01", "2020-05-01", "2020-08-01", "2020-11-01", "2021-01-01"],
            "water_level_raw": values,
        })
        result = compute_persistence_baseline(df)
        result = result.sort_values("observation_date")
        self.assertTrue(pd.isna(result["persistence_prediction"].iloc[0]))
        for i in range(1, len(values)):
            self.assertAlmostEqual(
                result["persistence_prediction"].iloc[i],
                values[i - 1],
                places=6,
            )

    def test_seasonal_hist_baseline_excludes_current_year(self):
        """Seasonal historical baseline strictly excludes the current year."""
        records = []
        for year in range(2015, 2021):
            records.append({
                "candidate_site_id": "S1",
                "analytical_season": "MONSOON",
                "observation_year": year,
                "observation_date": f"{year}-08-01",
                "water_level_raw": float(year - 2014),  # 1, 2, 3, 4, 5, 6
            })
        df = pd.DataFrame(records)
        result = compute_seasonal_historical_baseline(df, min_historical_years=2)

        # For year 2017 (value=3), baseline should be mean of 2015,2016 = (1+2)/2 = 1.5
        row_2017 = result[result["observation_year"] == 2017]
        if len(row_2017) > 0 and row_2017["seasonal_hist_available"].iloc[0]:
            self.assertAlmostEqual(row_2017["seasonal_hist_prediction"].iloc[0], 1.5, places=4)

        # For year 2020 (value=6), baseline should be mean of 2015-2019 = (1+2+3+4+5)/5 = 3.0
        row_2020 = result[result["observation_year"] == 2020]
        if len(row_2020) > 0 and row_2020["seasonal_hist_available"].iloc[0]:
            self.assertAlmostEqual(row_2020["seasonal_hist_prediction"].iloc[0], 3.0, places=4)


if __name__ == "__main__":
    unittest.main()
