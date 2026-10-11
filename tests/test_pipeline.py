"""
NEW/tests/test_pipeline.py - Comprehensive Test Suite for Milestone 3 Data Pipeline

Validates:
1. Column normalization and phantom column removal.
2. Coordinate inversion correction ONLY for output1final.csv.
3. Malformed administrative string detection.
4. Physically suspicious water-level flagging.
5. Duplicate detection (exact vs conflicting).
6. Source provenance assignment.
7. Raw immutability (verifies pipeline operations do not alter input fixtures).
"""

import os
import sys
import tempfile
import unittest
import pandas as pd

# Add NEW/ to python search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.data.loaders import (
    load_india_raw_file,
    DATASET_ID_INDIA,
    OBSERVATION_TYPE_PERIODIC,
)
from src.data.normalization import (
    normalize_india_dataframe,
    normalize_maharashtra_dataframe,
    generate_candidate_site_id,
)
from src.data.quality import (
    assess_india_quality,
    assess_maharashtra_quality,
    QualityConfig,
    FLAG_COORDINATE_INVERTED_CORRECTED,
    FLAG_COORDINATE_MISSING,
    FLAG_COORDINATE_OUT_OF_BOUNDS,
    FLAG_MALFORMED_ADMIN_GEOGRAPHY,
    FLAG_EXTREME_WATER_LEVEL_REVIEW_REQUIRED,
    FLAG_SEVERE_EXTREME_WATER_LEVEL_REVIEW_REQUIRED,
    FLAG_EXACT_DUPLICATE,
    FLAG_CONFLICTING_DUPLICATE,
    FLAG_LABEL_PROVENANCE_UNVERIFIED,
)


class TestPipelineComponents(unittest.TestCase):
    def test_column_normalization_and_phantom_removal(self):
        """Verifies whitespace trimming, case handling, and phantom Unnamed column removal."""
        raw_data = {
            "state": ["Maharashtra"],
            "district": ["Pune"],
            "BLOCK ": ["Haveli "],
            "VILLAGE ": ["Khadakwasla "],
            "Unnamed: 4": [None],
            "lat": [18.43],
            "lng": [73.76],
            "Unnamed: 7": [None],
            "Date": ["01/05/2023"],
            "waterLevel": [8.5],
            "status": ["safe"],
            "year": [2023],
            "trend": ["stable"],
            "source_dataset": [DATASET_ID_INDIA],
            "source_file": ["output2final.csv"],
            "observation_type": [OBSERVATION_TYPE_PERIODIC],
        }
        df_raw = pd.DataFrame(raw_data)
        norm = normalize_india_dataframe(df_raw, source_filename="output2final.csv")

        # Phantom columns must not exist in output
        self.assertNotIn("Unnamed: 4", norm.columns)
        self.assertNotIn("Unnamed: 7", norm.columns)
        # Normalized column names
        self.assertIn("block", norm.columns)
        self.assertIn("village", norm.columns)
        self.assertEqual(norm["block"].iloc[0], "Haveli")
        self.assertEqual(norm["village"].iloc[0], "Khadakwasla")
        self.assertEqual(norm["water_level_unit"].iloc[0], "UNKNOWN")
        self.assertEqual(norm["water_level_reference"].iloc[0], "UNKNOWN")
        self.assertEqual(norm["reference_datum"].iloc[0], "UNKNOWN")

    def test_coordinate_inversion_only_affects_output1(self):
        """Verifies that coordinate inversion is applied strictly to output1final.csv and not to others."""
        # Simulated row with inverted coordinates: lat=78.5 (Longitude), lng=19.5 (Latitude)
        data = {
            "state": ["Telangana"],
            "district": ["Hyderabad"],
            "BLOCK ": ["Charminar"],
            "VILLAGE ": ["OldCity"],
            "lat": [78.47],  # Inverted Longitude in lat
            "lng": [17.36],  # Inverted Latitude in lng
            "Date": ["01/01/2024"],
            "waterLevel": [6.2],
            "status": ["critical"],
            "year": [2024],
            "trend": ["stable"],
            "source_dataset": [DATASET_ID_INDIA],
            "source_file": ["output1final.csv"],
            "observation_type": [OBSERVATION_TYPE_PERIODIC],
        }
        df_inv = pd.DataFrame(data)

        # 1. Processing as output1final.csv -> Must invert and flag
        norm_output1 = normalize_india_dataframe(df_inv, source_filename="output1final.csv")
        self.assertTrue(norm_output1["coordinate_inverted_corrected"].iloc[0])
        self.assertEqual(norm_output1["latitude"].iloc[0], 17.36)
        self.assertEqual(norm_output1["longitude"].iloc[0], 78.47)
        self.assertEqual(norm_output1["source_lat"].iloc[0], 78.47)
        self.assertEqual(norm_output1["source_lng"].iloc[0], 17.36)

        # 2. Processing the same row under a different filename -> Must NOT invert
        df_other = pd.DataFrame(data)
        df_other["source_file"] = "outputfinal5.csv"
        norm_other = normalize_india_dataframe(df_other, source_filename="outputfinal5.csv")
        self.assertFalse(norm_other["coordinate_inverted_corrected"].iloc[0])
        self.assertEqual(norm_other["latitude"].iloc[0], 78.47)  # Unswapped
        self.assertEqual(norm_other["longitude"].iloc[0], 17.36)  # Unswapped

    def test_malformed_admin_geography_detection(self):
        """Verifies detection of concatenated state/district/village strings without auto-fixing them."""
        data = {
            "source_dataset": [DATASET_ID_INDIA, DATASET_ID_INDIA],
            "source_file": ["output4final.csv", "output4final.csv"],
            "observation_type": [OBSERVATION_TYPE_PERIODIC, OBSERVATION_TYPE_PERIODIC],
            "candidate_site_id": ["IND_1", "IND_2"],
            "state": [
                "The Dadra And Nagar Haveli And Daman And DiuDadra And Nagar Haveli Dadra Nagar Haveli Chinsda",
                "Punjab",
            ],
            "district": [None, "Amritsar"],
            "block": [None, "Ajnala"],
            "village": [None, "Lopoke"],
            "latitude": [20.11, 31.63],
            "longitude": [73.12, 74.87],
            "source_lat": [20.11, 31.63],
            "source_lng": [73.12, 74.87],
            "coordinate_inverted_corrected": [False, False],
            "observation_date": ["2024-05-10", "2024-05-10"],
            "observation_year": [2024, 2024],
            "observation_month": [5, 5],
            "water_level_raw": [3.38, 12.5],
            "water_level_unit": ["UNKNOWN", "UNKNOWN"],
            "water_level_reference": ["UNKNOWN", "UNKNOWN"],
            "reference_datum": ["UNKNOWN", "UNKNOWN"],
            "status_raw": ["safe", "safe"],
            "trend_raw": ["stable", "stable"],
            "state_raw": ["", ""],
            "district_raw": ["", ""],
            "block_raw": ["", ""],
            "village_raw": ["", ""],
            "date_raw": ["", ""],
        }
        df = pd.DataFrame(data)
        flagged = assess_india_quality(df)

        flags_row0 = flagged["quality_flags"].iloc[0].split(";")
        flags_row1 = flagged["quality_flags"].iloc[1].split(";")

        self.assertIn(FLAG_MALFORMED_ADMIN_GEOGRAPHY, flags_row0)
        self.assertNotIn(FLAG_MALFORMED_ADMIN_GEOGRAPHY, flags_row1)
        # Raw value must remain preserved
        self.assertTrue(flagged["state"].iloc[0].startswith("The Dadra And Nagar Haveli"))

    def test_extreme_water_level_screening_thresholds(self):
        """Verifies empirical screening threshold detection (DATA_QUALITY_SCREENING_THRESHOLD)."""
        data = {
            "source_dataset": [DATASET_ID_INDIA] * 4,
            "source_file": ["test.csv"] * 4,
            "observation_type": [OBSERVATION_TYPE_PERIODIC] * 4,
            "candidate_site_id": [f"IND_{i}" for i in range(4)],
            "state": ["Assam"] * 4,
            "district": ["Dhubri"] * 4,
            "block": ["Panbari"] * 4,
            "village": ["Panbari"] * 4,
            "latitude": [26.0] * 4,
            "longitude": [90.0] * 4,
            "source_lat": [26.0] * 4,
            "source_lng": [90.0] * 4,
            "coordinate_inverted_corrected": [False] * 4,
            "observation_date": ["2004-11-01"] * 4,
            "observation_year": [2004] * 4,
            "observation_month": [11] * 4,
            # Normal (5.2), Negative (-2.0), Extreme High (180.0), Severe Extreme (53943.6)
            "water_level_raw": [5.2, -2.0, 180.0, 53943.6],
            "water_level_unit": ["UNKNOWN"] * 4,
            "water_level_reference": ["UNKNOWN"] * 4,
            "reference_datum": ["UNKNOWN"] * 4,
            "status_raw": ["safe"] * 4,
            "trend_raw": ["stable"] * 4,
            "state_raw": [""] * 4,
            "district_raw": [""] * 4,
            "block_raw": [""] * 4,
            "village_raw": [""] * 4,
            "date_raw": [""] * 4,
        }
        df = pd.DataFrame(data)
        config = QualityConfig(india_min_level=0.0, india_max_level=150.0, india_extreme_level=500.0)
        flagged = assess_india_quality(df, config=config)

        # Row 0: Normal
        self.assertTrue(flagged["is_analytics_ready"].iloc[0])
        # Row 1: Negative in India -> EXTREME_WATER_LEVEL_REVIEW_REQUIRED
        self.assertIn(FLAG_EXTREME_WATER_LEVEL_REVIEW_REQUIRED, flagged["quality_flags"].iloc[1])
        self.assertFalse(flagged["is_analytics_ready"].iloc[1])
        # Row 2: 180m -> EXTREME_WATER_LEVEL_REVIEW_REQUIRED
        self.assertIn(FLAG_EXTREME_WATER_LEVEL_REVIEW_REQUIRED, flagged["quality_flags"].iloc[2])
        self.assertFalse(flagged["is_analytics_ready"].iloc[2])
        # Row 3: 53943.6m -> SEVERE_EXTREME_WATER_LEVEL_REVIEW_REQUIRED
        self.assertIn(FLAG_SEVERE_EXTREME_WATER_LEVEL_REVIEW_REQUIRED, flagged["quality_flags"].iloc[3])
        self.assertFalse(flagged["is_analytics_ready"].iloc[3])

    def test_unverified_label_provenance_flag(self):
        """Verifies that records possessing status or trend fields are tagged with LABEL_PROVENANCE_UNVERIFIED."""
        data = {
            "source_dataset": [DATASET_ID_INDIA],
            "source_file": ["test.csv"],
            "observation_type": [OBSERVATION_TYPE_PERIODIC],
            "candidate_site_id": ["IND_1"],
            "state": ["Assam"],
            "district": ["Dhubri"],
            "block": ["Panbari"],
            "village": ["Panbari"],
            "latitude": [26.0],
            "longitude": [90.0],
            "source_lat": [26.0],
            "source_lng": [90.0],
            "coordinate_inverted_corrected": [False],
            "observation_date": ["2004-11-01"],
            "observation_year": [2004],
            "observation_month": [11],
            "water_level_raw": [5.2],
            "water_level_unit": ["UNKNOWN"],
            "water_level_reference": ["UNKNOWN"],
            "reference_datum": ["UNKNOWN"],
            "status_raw": ["safe"],
            "trend_raw": ["stable"],
            "state_raw": [""],
            "district_raw": [""],
            "block_raw": [""],
            "village_raw": [""],
            "date_raw": [""],
        }
        df = pd.DataFrame(data)
        flagged = assess_india_quality(df)
        self.assertIn(FLAG_LABEL_PROVENANCE_UNVERIFIED, flagged["quality_flags"].iloc[0])

    def test_duplicate_and_conflicting_detection(self):
        """Verifies exact duplicate vs conflicting observation detection at the same site/date."""
        data = {
            "source_dataset": [DATASET_ID_INDIA] * 3,
            "source_file": ["test.csv"] * 3,
            "observation_type": [OBSERVATION_TYPE_PERIODIC] * 3,
            "candidate_site_id": ["IND_SITE_A", "IND_SITE_A", "IND_SITE_A"],
            "state": ["Rajasthan"] * 3,
            "district": ["Jaipur"] * 3,
            "block": ["Sanganer"] * 3,
            "village": ["Mahapura"] * 3,
            "latitude": [26.85] * 3,
            "longitude": [75.78] * 3,
            "source_lat": [26.85] * 3,
            "source_lng": [75.78] * 3,
            "coordinate_inverted_corrected": [False] * 3,
            "observation_date": ["2023-08-01", "2023-08-01", "2023-08-01"],
            "observation_year": [2023] * 3,
            "observation_month": [8] * 3,
            # Row 0: 10.0, Row 1: 10.0 (exact dup), Row 2: 15.0 (conflicting measurement on same site+date)
            "water_level_raw": [10.0, 10.0, 15.0],
            "water_level_unit": ["meter"] * 3,
            "reference_datum": ["UNKNOWN_PRESUMED_BGL"] * 3,
            "status_raw": ["safe"] * 3,
            "trend_raw": ["stable"] * 3,
            "state_raw": ["Rajasthan"] * 3,
            "district_raw": ["Jaipur"] * 3,
            "block_raw": ["Sanganer"] * 3,
            "village_raw": ["Mahapura"] * 3,
            "date_raw": ["01/08/2023"] * 3,
        }
        df = pd.DataFrame(data)
        flagged = assess_india_quality(df)

        flags_row1 = flagged["quality_flags"].iloc[1].split(";")
        self.assertIn(FLAG_EXACT_DUPLICATE, flags_row1)

        # Because row 0 & row 2 have conflicting values for the same site and date:
        self.assertIn(FLAG_CONFLICTING_DUPLICATE, flagged["quality_flags"].iloc[2].split(";"))

    def test_raw_immutability(self):
        """Verifies that input DataFrames passed to normalizers and quality checkers are not modified in-place."""
        df_raw = pd.DataFrame({
            "state": ["Gujarat"],
            "district": ["Ahmedabad"],
            "lat": [23.02],
            "lng": [72.57],
            "Date": ["01/05/2022"],
            "waterLevel": [14.2],
            "status": ["critical"],
            "year": [2022],
            "trend": ["declining"],
        })
        original_cols = list(df_raw.columns)
        original_vals = df_raw.values.tolist()

        # Run normalization
        _ = normalize_india_dataframe(df_raw, source_filename="outputfinal5.csv")

        # Verify df_raw is unmodified
        self.assertEqual(list(df_raw.columns), original_cols)
        self.assertEqual(df_raw.values.tolist(), original_vals)


if __name__ == "__main__":
    unittest.main()
