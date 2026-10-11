import pandas as pd
import numpy as np
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class PersistenceForecastGenerator:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        
    def generate(self) -> pd.DataFrame:
        """Generates a persistence forecast using the next-valid-observation target."""
        # 1. Quality Policy
        # Exclude INVALID_OR_EMPTY, UNREALISTIC_WATER_LEVEL, CONFLICTING_DUPLICATE
        # is_analytics_ready cleanly encapsulates this and removes nulls
        df_valid = self.df[self.df['is_analytics_ready'] == True].copy()
        
        # 2. Chronological Ordering
        df_valid = df_valid.sort_values(by=['candidate_site_id', 'observation_timestamp'])
        
        # 3. Target Definition (Next valid observation)
        df_valid['target_timestamp'] = df_valid.groupby('candidate_site_id')['observation_timestamp'].shift(-1)
        df_valid['actual_water_level'] = df_valid.groupby('candidate_site_id')['water_level_raw'].shift(-1)
        
        # 4. Terminal Observation Exclusion
        df_valid = df_valid.dropna(subset=['target_timestamp', 'actual_water_level']).copy()
        
        # 5. Horizon Calculation
        obs_time = pd.to_datetime(df_valid['observation_timestamp'], format='mixed', utc=True)
        target_time = pd.to_datetime(df_valid['target_timestamp'], format='mixed', utc=True)
        df_valid['forecast_horizon_hours'] = (target_time - obs_time).dt.total_seconds() / 3600.0
        
        # 6. Future Leakage Prevention: Prediction strictly equals current
        df_valid['observed_water_level'] = df_valid['water_level_raw']
        df_valid['predicted_water_level'] = df_valid['observed_water_level']
        df_valid['prediction_timestamp'] = df_valid['observation_timestamp']
        
        # 7. Metadata
        df_valid['model_name'] = 'persistence'
        df_valid['model_version'] = 'persistence-v1'
        
        schema = [
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
        return df_valid[schema]

if __name__ == "__main__":
    import os
    mh_path = Path("data/processed/maharashtra/maharashtra_normalized.parquet")
        
    df = pd.read_parquet(mh_path)
    generator = PersistenceForecastGenerator(df)
    forecast_df = generator.generate()
    
    out_dir = Path("data/forecasts")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "maharashtra_persistence_forecast.parquet"
    
    forecast_df.to_parquet(out_path, index=False)
    print(f"Saved to {out_path}")
