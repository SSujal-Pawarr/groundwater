import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from src.models.persistence_forecast import PersistenceForecastGenerator

@pytest.fixture
def sample_mh_data():
    return pd.DataFrame({
        'candidate_site_id': ['MH_1', 'MH_1', 'MH_1', 'MH_2', 'MH_2', 'MH_3'],
        'observation_timestamp': [
            '2025-01-01T00:00:00Z',
            '2025-01-01T06:00:00Z',
            '2025-01-01T12:00:00Z',
            '2025-02-01T00:00:00Z',
            '2025-02-01T24:00:00Z', # Invalid timestamp format for test, will use valid
            '2025-03-01T00:00:00Z'
        ],
        'water_level_raw': [10.0, 10.5, 11.0, 20.0, 22.0, 5.0],
        'is_analytics_ready': [True, True, False, True, True, True]
    })

@pytest.fixture
def valid_mh_data():
    return pd.DataFrame({
        'candidate_site_id': ['MH_1', 'MH_1', 'MH_1', 'MH_1', 'MH_2', 'MH_2'],
        'observation_timestamp': [
            '2025-01-01T00:00:00Z',
            '2025-01-01T06:00:00Z', # 6h horizon
            '2025-01-01T12:00:00Z', # 6h horizon
            '2025-01-02T12:00:00Z', # 24h horizon
            '2025-02-01T00:00:00Z',
            '2025-02-03T00:00:00Z'  # 48h horizon
        ],
        'water_level_raw': [10.0, 10.5, 11.0, 12.0, 20.0, 22.0],
        'is_analytics_ready': [True, True, False, True, True, True]
    })

class TestM831PersistenceForecast:
    
    def test_schema_integrity(self, valid_mh_data):
        gen = PersistenceForecastGenerator(valid_mh_data)
        df = gen.generate()
        
        expected_schema = [
            'candidate_site_id',
            'prediction_timestamp',
            'target_timestamp',
            'forecast_horizon_hours',
            'observed_water_level',
            'predicted_water_level',
            'actual_water_level',
            'model_name',
            'model_version'
        ]
        assert list(df.columns) == expected_schema
        assert len(df) > 0
        
    def test_chronological_ordering_and_target_correctness(self, valid_mh_data):
        gen = PersistenceForecastGenerator(valid_mh_data)
        df = gen.generate()
        
        mh1 = df[df['candidate_site_id'] == 'MH_1'].reset_index(drop=True)
        # MH_1 has 3 valid records (index 0, 1, 3). So 2 forecast pairs.
        assert len(mh1) == 2
        
        # Row 1: 00:00 -> 06:00
        assert mh1.loc[0, 'prediction_timestamp'] == '2025-01-01T00:00:00Z'
        assert mh1.loc[0, 'target_timestamp'] == '2025-01-01T06:00:00Z'
        assert mh1.loc[0, 'forecast_horizon_hours'] == 6.0
        
        # Row 2: 06:00 -> next valid is 01-02T12:00 (index 2 was false)
        assert mh1.loc[1, 'prediction_timestamp'] == '2025-01-01T06:00:00Z'
        assert mh1.loc[1, 'target_timestamp'] == '2025-01-02T12:00:00Z'
        assert mh1.loc[1, 'forecast_horizon_hours'] == 30.0

    def test_terminal_observation_exclusion(self, valid_mh_data):
        gen = PersistenceForecastGenerator(valid_mh_data)
        df = gen.generate()
        
        # Site MH_2 has 2 valid obs. Means 1 forecast pair.
        mh2 = df[df['candidate_site_id'] == 'MH_2']
        assert len(mh2) == 1
        
        # The terminal observations (01-02 12:00 for MH_1, 02-03 for MH_2) should not appear in prediction_timestamp
        assert '2025-01-02T12:00:00Z' not in df['prediction_timestamp'].values
        assert '2025-02-03T00:00:00Z' not in df['prediction_timestamp'].values
        
    def test_predicted_equals_observed_no_leakage(self, valid_mh_data):
        gen = PersistenceForecastGenerator(valid_mh_data)
        df = gen.generate()
        
        # Core property of persistence:
        pd.testing.assert_series_equal(df['predicted_water_level'], df['observed_water_level'], check_names=False)
        
        # The actual target remains separate
        assert not df['predicted_water_level'].equals(df['actual_water_level'])
        
    def test_quality_filtering(self, valid_mh_data):
        gen = PersistenceForecastGenerator(valid_mh_data)
        df = gen.generate()
        
        # Index 2 (12:00) had is_analytics_ready = False
        assert '2025-01-01T12:00:00Z' not in df['prediction_timestamp'].values
        assert '2025-01-01T12:00:00Z' not in df['target_timestamp'].values

    def test_deterministic_generation(self, valid_mh_data):
        gen1 = PersistenceForecastGenerator(valid_mh_data).generate()
        gen2 = PersistenceForecastGenerator(valid_mh_data.copy()).generate()
        
        pd.testing.assert_frame_equal(gen1, gen2)

    def test_no_india_artifact(self):
        # The test checks that we don't accidentally try to create an India artifact.
        p = Path("data/forecasts/india_persistence_forecast.parquet")
        assert not p.exists()
