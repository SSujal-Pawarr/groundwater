import unittest
import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from alerting.config import AlertConfig
from alerting.engine import generate_india_alerts, generate_maharashtra_alerts, _apply_state_machine

class TestCausalAlertEngine(unittest.TestCase):
    
    def setUp(self):
        self.config = AlertConfig()
        
    def test_state_machine_escalation_and_recovery(self):
        # NORMAL -> WATCH -> WARNING -> CRITICAL -> NORMAL (after 3 cools)
        states = np.array([
            self.config.STATE_NORMAL,
            self.config.STATE_WATCH,
            self.config.STATE_WATCH,
            self.config.STATE_WARNING,
            self.config.STATE_CRITICAL,
            self.config.STATE_NORMAL, # 1
            self.config.STATE_NORMAL, # 2
            self.config.STATE_NORMAL, # 3 -> Recover
            self.config.STATE_WATCH
        ])
        
        out = _apply_state_machine(states, self.config)
        
        expected = [
            self.config.STATE_NORMAL,
            self.config.STATE_WATCH,
            self.config.STATE_WATCH, # Remains watch
            self.config.STATE_WARNING, # Escalates
            self.config.STATE_CRITICAL, # Escalates
            self.config.STATE_CRITICAL, # Cool 1
            self.config.STATE_CRITICAL, # Cool 2
            self.config.STATE_NORMAL, # Cool 3 -> Recovery
            self.config.STATE_WATCH
        ]
        
        self.assertEqual(list(out), expected)
        
    def test_state_machine_non_operational_passthrough(self):
        states = np.array([
            self.config.STATE_NORMAL,
            self.config.STATE_WARNING,
            self.config.STATE_DATA_QUALITY,
            self.config.STATE_NORMAL,
            self.config.STATE_NORMAL,
            self.config.STATE_NORMAL
        ])
        
        out = _apply_state_machine(states, self.config)
        
        expected = [
            self.config.STATE_NORMAL,
            self.config.STATE_WARNING,
            self.config.STATE_DATA_QUALITY, # Passed through for this row
            self.config.STATE_WARNING, # Cool 1
            self.config.STATE_WARNING, # Cool 2
            self.config.STATE_NORMAL  # Cool 3 -> Recover
        ]
        self.assertEqual(list(out), expected)

    def test_first_observation_handled_correctly(self):
        df = pd.DataFrame({
            "candidate_site_id": ["A"],
            "analytical_season": ["Pre-Monsoon"],
            "observation_year": [2010],
            "water_level_raw": [10.0],
            "observation_date": ["2010-05-01"],
            "is_analytics_ready": [True],
            "quality_flags": [""]
        })
        out = generate_india_alerts(df, self.config)
        self.assertEqual(out.iloc[0]["alert_event_state"], self.config.STATE_INSUFFICIENT_HISTORY)

    def test_historical_statistics_exclude_current_and_future(self):
        # 5 strictly prior years (2010-2014), predicting 2015
        df = pd.DataFrame({
            "candidate_site_id": ["A"] * 7,
            "analytical_season": ["Pre-Monsoon"] * 7,
            "observation_year": [2010, 2011, 2012, 2013, 2014, 2015, 2016],
            "water_level_raw": [10.0, 10.0, 10.0, 10.0, 10.0, 100.0, 50.0],
            "observation_date": [f"{y}-05-01" for y in range(2010, 2017)],
            "is_analytics_ready": [True] * 7,
            "quality_flags": [""] * 7
        })
        
        out = generate_india_alerts(df, self.config)
        # For 2015 (index 5)
        row_2015 = out[out["observation_year"] == 2015].iloc[0]
        self.assertEqual(row_2015["historical_sample_count"], 5)
        self.assertEqual(row_2015["historical_reference"], 10.0)
        self.assertEqual(row_2015["deviation"], 90.0)
        
        self.assertTrue(pd.notna(row_2015["alert_event_state"]))

    def test_adding_future_observation_does_not_change_past_alert(self):
        # Note: We must ensure enough history to generate valid alerts.
        # But this tests causal integrity of the output.
        df_past = pd.DataFrame({
            "station_name": ["S1"] * 25,
            "observation_timestamp": [f"2026-01-01 {i:02d}:00:00" for i in range(24)] + ["2026-01-02 00:00:00"],
            "water_level_raw": [5.0] * 24 + [100.0],
            "is_analytics_ready": [True] * 25,
            "quality_flags": [""] * 25
        })
        
        out_past = generate_maharashtra_alerts(df_past, self.config)
        past_state = out_past.iloc[24]["alert_event_state"]
        
        df_future = pd.concat([df_past, pd.DataFrame({
            "station_name": ["S1"],
            "observation_timestamp": ["2026-01-02 01:00:00"],
            "water_level_raw": [200.0],
            "is_analytics_ready": [True],
            "quality_flags": [""]
        })]).reset_index(drop=True)
        
        out_future = generate_maharashtra_alerts(df_future, self.config)
        new_past_state = out_future.iloc[24]["alert_event_state"]
        
        self.assertEqual(past_state, new_past_state)

    def test_large_time_gaps_handled_explicitly(self):
        df = pd.DataFrame({
            "station_name": ["S1", "S1"],
            "observation_timestamp": ["2026-01-01 00:00:00", "2026-01-03 00:00:00"], # 48 hours gap
            "water_level_raw": [5.0, 6.0],
            "is_analytics_ready": [True, True],
            "quality_flags": ["", ""]
        })
        out = generate_maharashtra_alerts(df, self.config)
        self.assertEqual(out.iloc[1]["alert_event_state"], self.config.STATE_GAPPED)

    def test_schema_integrity(self):
        # Verify the public output schema contains necessary fields
        df_in = pd.DataFrame({
            "candidate_site_id": ["A"],
            "analytical_season": ["Pre-Monsoon"],
            "observation_year": [2010],
            "water_level_raw": [10.0],
            "observation_date": ["2010-05-01"],
            "is_analytics_ready": [True],
            "quality_flags": [""]
        })
        out_in = generate_india_alerts(df_in, self.config)
        
        expected_india_cols = {
            "candidate_site_id", "observation_date", "analytical_season",
            "water_level_raw", "historical_reference", "deviation", "historical_std",
            "standardized_score", "historical_sample_count",
            "instantaneous_state", "alert_event_state"
        }
        for col in expected_india_cols:
            self.assertIn(col, out_in.columns)
            
        df_mh = pd.DataFrame({
            "station_name": ["S1"],
            "observation_timestamp": ["2026-01-01 00:00:00"],
            "water_level_raw": [5.0],
            "is_analytics_ready": [True],
            "quality_flags": [""]
        })
        out_mh = generate_maharashtra_alerts(df_mh, self.config)
        expected_mh_cols = {
            "station_name", "observation_timestamp", "water_level_raw",
            "historical_reference", "deviation", "historical_std", "standardized_score",
            "time_since_previous_obs_hours", "instantaneous_state", "alert_event_state"
        }
        for col in expected_mh_cols:
            self.assertIn(col, out_mh.columns)

if __name__ == "__main__":
    unittest.main()
