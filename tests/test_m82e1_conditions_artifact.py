import unittest
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
CONDITIONS_DIR = DATA_DIR / "conditions"

INDIA_M3_PATH = PROCESSED_DIR / "india" / "india_normalized.parquet"
MH_M3_PATH = PROCESSED_DIR / "maharashtra" / "maharashtra_normalized.parquet"

INDIA_OUT_PATH = CONDITIONS_DIR / "india_conditions.parquet"
MH_OUT_PATH = CONDITIONS_DIR / "maharashtra_conditions.parquet"
METADATA_OUT_PATH = CONDITIONS_DIR / "metadata.json"

APPROVED_STATES = {
    "EXTREMELY_LOW",
    "LOW",
    "NORMAL_RANGE",
    "HIGH",
    "EXTREMELY_HIGH",
    "INSUFFICIENT_HISTORY"
}

class TestM82E1ConditionsArtifact(unittest.TestCase):
    
    def test_india_artifact_integrity(self):
        if not INDIA_M3_PATH.exists():
            self.skipTest("India M3 data not found")
            
        self.assertTrue(INDIA_OUT_PATH.exists(), "India conditions artifact must exist")
        
        m3_df = pd.read_parquet(INDIA_M3_PATH, columns=["candidate_site_id"])
        cond_df = pd.read_parquet(INDIA_OUT_PATH)
        
        # Row counts must match exactly
        self.assertEqual(len(m3_df), len(cond_df), "Row counts must match exactly")
        
        # Check approved states
        states = set(cond_df["condition_state"].unique())
        self.assertTrue(states.issubset(APPROVED_STATES), f"Found unapproved states: {states - APPROVED_STATES}")
        
        # Check required columns
        required_cols = [
            "candidate_site_id", "observation_date", "analytical_season", 
            "water_level_raw", "condition_state", "percentile", 
            "historical_sample_count", "historical_reference_group", "condition_method_version"
        ]
        for col in required_cols:
            self.assertIn(col, cond_df.columns, f"Missing column {col}")

    def test_maharashtra_artifact_integrity(self):
        if not MH_M3_PATH.exists():
            self.skipTest("Maharashtra M3 data not found")
            
        self.assertTrue(MH_OUT_PATH.exists(), "Maharashtra conditions artifact must exist")
        
        m3_df = pd.read_parquet(MH_M3_PATH, columns=["candidate_site_id"])
        cond_df = pd.read_parquet(MH_OUT_PATH)
        
        # Row counts must match exactly
        self.assertEqual(len(m3_df), len(cond_df), "Row counts must match exactly")
        
        # Check approved states
        states = set(cond_df["condition_state"].unique())
        self.assertTrue(states.issubset(APPROVED_STATES), f"Found unapproved states: {states - APPROVED_STATES}")
        
        # Check required columns
        required_cols = [
            "candidate_site_id", "observation_timestamp", "observation_date", 
            "water_level_raw", "condition_state", "percentile", 
            "historical_sample_count", "historical_reference_group", "condition_method_version"
        ]
        for col in required_cols:
            self.assertIn(col, cond_df.columns, f"Missing column {col}")
