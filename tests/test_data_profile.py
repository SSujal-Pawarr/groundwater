"""
NEW/tests/test_data_profile.py - Test Suite for Read-Only Profiling Engine

Uses Python standard library `unittest` to ensure zero required third-party
test runners at the foundation stage.
"""

import os
import sys
import tempfile
import unittest

# Ensure NEW/ is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.data_profile import profile_india_file


class TestDataProfile(unittest.TestCase):
    def test_profile_india_file_normal_coords(self):
        """Tests profiling on a temporary fixture with normal Indian coordinates."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tf:
            tf.write(
                "state,district,BLOCK ,VILLAGE ,lat,lng,Date,waterLevel,status,year,trend\n"
                "Maharashtra,Pune,Haveli,Khadakwasla,18.43,73.76,01/05/2023,8.5,safe,2023,stable\n"
                "Maharashtra,Pune,Haveli,Khadakwasla,18.43,73.76,01/08/2023,4.2,safe,2023,improving\n"
            )
            temp_path = tf.name

        try:
            profile = profile_india_file(temp_path)
            self.assertEqual(profile["row_count"], 2)
            self.assertEqual(profile["col_count"], 11)
            self.assertEqual(profile["unique_states"], 1)
            self.assertEqual(profile["unique_districts"], 1)
            self.assertEqual(profile["coordinate_stats"]["swapped_lat_lng_count"], 0)
            self.assertEqual(profile["water_level_stats"]["min"], 4.2)
            self.assertEqual(profile["water_level_stats"]["max"], 8.5)
            self.assertEqual(profile["water_level_stats"]["negatives"], 0)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_profile_india_file_detects_swapped_coords(self):
        """Tests that profiling detects inverted lat/lng (longitude in lat column, latitude in lng column)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tf:
            tf.write(
                "state,district,BLOCK ,VILLAGE ,lat,lng,Date,waterLevel,status,year,trend\n"
                "Andhra Pradesh,Visakhapatnam,Bheemunipatnam,Tagarapuvalasa,83.42,17.93,01/01/2024,9.1,over-exploited,2024,stable\n"
            )
            temp_path = tf.name

        try:
            profile = profile_india_file(temp_path)
            self.assertEqual(profile["row_count"], 1)
            # lat=83.42 (>50) and lng=17.93 (<40) must be flagged as swapped
            self.assertEqual(profile["coordinate_stats"]["swapped_lat_lng_count"], 1)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()
