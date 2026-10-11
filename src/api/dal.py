import os
from pathlib import Path
import duckdb
import math
from typing import Optional, List, Dict, Any

class GroundwaterDAL:
    def __init__(self):
        self.project_root = Path(os.path.abspath(__file__)).parent.parent.parent
        self.india_m3_path = self.project_root / "data" / "processed" / "india" / "india_normalized.parquet"
        self.mh_m3_path = self.project_root / "data" / "processed" / "maharashtra" / "maharashtra_normalized.parquet"
        
        self.india_m6_path = self.project_root / "data" / "alerts" / "india_alerts.parquet"
        self.mh_m6_path = self.project_root / "data" / "alerts" / "maharashtra_alerts.parquet"
        
        self.india_m82d_path = self.project_root / "data" / "conditions" / "india_conditions.parquet"
        self.mh_m82d_path = self.project_root / "data" / "conditions" / "maharashtra_conditions.parquet"
        
        self.india_m10_path = self.project_root / "data" / "drought_intelligence" / "india_drought_intelligence.parquet"
        self.india_m11_path = self.project_root / "data" / "flood_intelligence" / "india_flood_potential.parquet"
        self.mh_m11_path = self.project_root / "data" / "flood_intelligence" / "maharashtra_flood_potential.parquet"
        self.india_m12_path = self.project_root / "data" / "stress_intelligence" / "india_stress_intelligence.parquet"
        self.mh_m12_path = self.project_root / "data" / "stress_intelligence" / "maharashtra_stress_intelligence.parquet"
        
        self.conn = duckdb.connect(database=':memory:', read_only=False)

    def is_healthy(self) -> bool:
        try:
            cur = self.conn.cursor()
            try:
                res = cur.execute("SELECT 1").fetchone()
            finally:
                cur.close()
            return res == (1,)
        except Exception:
            return False

    def _clean_row(self, row_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Convert NaNs and infinities to None for strict JSON serialization."""
        clean = {}
        for k, v in row_dict.items():
            if isinstance(v, float):
                if math.isnan(v) or math.isinf(v):
                    clean[k] = None
                else:
                    clean[k] = v
            elif pd.isna(v) if 'pd' in globals() else v is None: # Quick check if pandas NA
                clean[k] = None
            else:
                clean[k] = v
        return clean

    def _query(self, sql: str, params: list = None) -> List[Dict[str, Any]]:
        params = params or []
        try:
            # One cursor per query: a single shared DuckDB connection is not safe when FastAPI serves
            # several requests concurrently (results were being swapped between threads -> intermittent 500s).
            cur = self.conn.cursor()
            try:
                df = cur.execute(sql, params).fetchdf()
            finally:
                cur.close()
            # replace nans
            import numpy as np
            import pandas as pd
            df = df.replace({np.nan: None})
            
            # Convert timestamp to ISO 8601 strings explicitly if needed
            for col in df.select_dtypes(include=['datetime64[ns, UTC]', 'datetime64[ns]']).columns:
                df[col] = df[col].dt.strftime('%Y-%m-%dT%H:%M:%SZ')

            rows = df.to_dict(orient="records")
            return [self._clean_row(row) for row in rows]
        except Exception as e:
            # We raise so FastAPI can handle it
            raise e

    def get_india_candidate_sites(self, limit: int = 100, offset: int = 0, state: Optional[str] = None,
                                  min_lat: Optional[float] = None, max_lat: Optional[float] = None,
                                  min_lng: Optional[float] = None, max_lng: Optional[float] = None):
        if not self.india_m3_path.exists():
            return []
            
        where_clauses = ["latitude IS NOT NULL AND longitude IS NOT NULL"]
        params = []
        if state:
            where_clauses.append("state = ?")
            params.append(state)
        
        if min_lat is not None and max_lat is not None and min_lng is not None and max_lng is not None:
            where_clauses.append("latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ?")
            params.extend([min_lat, max_lat, min_lng, max_lng])
            
        where_sql = " AND ".join(where_clauses)

        if not self.india_m82d_path.exists():
            sql = f"""
                SELECT DISTINCT candidate_site_id, state, district, block, village, latitude, longitude,
                                CAST(NULL AS VARCHAR) AS condition_state
                FROM '{self.india_m3_path.as_posix()}'
                WHERE {where_sql}
                ORDER BY candidate_site_id LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            return self._query(sql, params)

        sql = f"""
            WITH sites AS (
                SELECT DISTINCT candidate_site_id, state, district, block, village, latitude, longitude
                FROM '{self.india_m3_path.as_posix()}'
                WHERE {where_sql}
                ORDER BY candidate_site_id
                LIMIT ? OFFSET ?
            ),
            latest_cond AS (
                SELECT candidate_site_id, condition_state FROM (
                    SELECT candidate_site_id, condition_state, ROW_NUMBER() OVER (PARTITION BY candidate_site_id ORDER BY observation_date DESC) as rn
                    FROM '{self.india_m82d_path.as_posix()}' WHERE candidate_site_id IN (SELECT candidate_site_id FROM sites)
                ) WHERE rn = 1
            ),
            latest_alert AS (
                SELECT candidate_site_id, alert_event_state FROM (
                    SELECT candidate_site_id, alert_event_state, ROW_NUMBER() OVER (PARTITION BY candidate_site_id ORDER BY observation_date DESC) as rn
                    FROM '{self.india_m6_path.as_posix()}' WHERE candidate_site_id IN (SELECT candidate_site_id FROM sites)
                ) WHERE rn = 1
            ),
            latest_drought AS (
                SELECT candidate_site_id, drought_status FROM (
                    SELECT candidate_site_id, drought_status, ROW_NUMBER() OVER (PARTITION BY candidate_site_id ORDER BY observation_date DESC) as rn
                    FROM '{self.india_m10_path.as_posix()}' WHERE candidate_site_id IN (SELECT candidate_site_id FROM sites)
                ) WHERE rn = 1
            ),
            latest_flood AS (
                SELECT candidate_site_id, flood_potential_state FROM (
                    SELECT candidate_site_id, flood_potential_state, ROW_NUMBER() OVER (PARTITION BY candidate_site_id ORDER BY observation_timestamp DESC) as rn
                    FROM '{self.india_m11_path.as_posix()}' WHERE candidate_site_id IN (SELECT candidate_site_id FROM sites)
                ) WHERE rn = 1
            ),
            latest_stress AS (
                SELECT candidate_site_id, stress_state FROM (
                    SELECT candidate_site_id, stress_state, ROW_NUMBER() OVER (PARTITION BY candidate_site_id ORDER BY observation_date DESC) as rn
                    FROM '{self.india_m12_path.as_posix()}' WHERE candidate_site_id IN (SELECT candidate_site_id FROM sites)
                ) WHERE rn = 1
            )
            SELECT s.candidate_site_id, s.state, s.district, s.block, s.village, s.latitude, s.longitude, 
                   c.condition_state, a.alert_event_state, d.drought_status as drought_state, f.flood_potential_state, st.stress_state
            FROM sites s
            LEFT JOIN latest_cond c ON s.candidate_site_id = c.candidate_site_id
            LEFT JOIN latest_alert a ON s.candidate_site_id = a.candidate_site_id
            LEFT JOIN latest_drought d ON s.candidate_site_id = d.candidate_site_id
            LEFT JOIN latest_flood f ON s.candidate_site_id = f.candidate_site_id
            LEFT JOIN latest_stress st ON s.candidate_site_id = st.candidate_site_id
            ORDER BY s.candidate_site_id
        """
        params.extend([limit, offset])
        return self._query(sql, params)

    def get_mh_candidate_sites(self, limit: int = 100, offset: int = 0, district: Optional[str] = None,
                               min_lat: Optional[float] = None, max_lat: Optional[float] = None,
                               min_lng: Optional[float] = None, max_lng: Optional[float] = None):
        if not self.mh_m3_path.exists():
            return []
            
        where_clauses = ["latitude IS NOT NULL AND longitude IS NOT NULL"]
        params = []
        if district:
            where_clauses.append("district = ?")
            params.append(district)
            
        if min_lat is not None and max_lat is not None and min_lng is not None and max_lng is not None:
            where_clauses.append("latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ?")
            params.extend([min_lat, max_lat, min_lng, max_lng])
            
        where_sql = " AND ".join(where_clauses)

        if not self.mh_m6_path.exists():
            sql = f"""
                SELECT DISTINCT candidate_site_id, station_name, state, district, subdistrict, latitude, longitude, elevation_msl,
                                CAST(NULL AS VARCHAR) AS alert_event_state
                FROM '{self.mh_m3_path.as_posix()}'
                WHERE {where_sql}
                ORDER BY candidate_site_id LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            return self._query(sql, params)

        sql = f"""
            WITH sites AS (
                SELECT DISTINCT candidate_site_id, station_name, state, district, subdistrict, latitude, longitude, elevation_msl
                FROM '{self.mh_m3_path.as_posix()}'
                WHERE {where_sql}
                ORDER BY candidate_site_id
                LIMIT ? OFFSET ?
            ),
            latest_cond AS (
                SELECT candidate_site_id, condition_state FROM (
                    SELECT candidate_site_id, condition_state, ROW_NUMBER() OVER (PARTITION BY candidate_site_id ORDER BY observation_timestamp DESC) as rn
                    FROM '{self.mh_m82d_path.as_posix()}' WHERE candidate_site_id IN (SELECT candidate_site_id FROM sites)
                ) WHERE rn = 1
            ),
            latest_alerts AS (
                SELECT candidate_site_id, alert_event_state FROM (
                    SELECT candidate_site_id, alert_event_state, ROW_NUMBER() OVER (PARTITION BY candidate_site_id ORDER BY observation_timestamp DESC) as rn
                    FROM '{self.mh_m6_path.as_posix()}' WHERE candidate_site_id IN (SELECT candidate_site_id FROM sites)
                ) WHERE rn = 1
            ),
            latest_flood AS (
                SELECT candidate_site_id, flood_potential_state FROM (
                    SELECT candidate_site_id, flood_potential_state, ROW_NUMBER() OVER (PARTITION BY candidate_site_id ORDER BY observation_timestamp DESC) as rn
                    FROM '{self.mh_m11_path.as_posix()}' WHERE candidate_site_id IN (SELECT candidate_site_id FROM sites)
                ) WHERE rn = 1
            ),
            latest_stress AS (
                SELECT candidate_site_id, stress_state FROM (
                    SELECT candidate_site_id, stress_state, ROW_NUMBER() OVER (PARTITION BY candidate_site_id ORDER BY observation_timestamp DESC) as rn
                    FROM '{self.mh_m12_path.as_posix()}' WHERE candidate_site_id IN (SELECT candidate_site_id FROM sites)
                ) WHERE rn = 1
            )
            SELECT s.candidate_site_id, s.station_name, s.state, s.district, s.subdistrict, s.latitude, s.longitude, s.elevation_msl, 
                   c.condition_state, a.alert_event_state, NULL as drought_state, f.flood_potential_state, st.stress_state
            FROM sites s
            LEFT JOIN latest_cond c ON s.candidate_site_id = c.candidate_site_id
            LEFT JOIN latest_alerts a ON s.candidate_site_id = a.candidate_site_id
            LEFT JOIN latest_flood f ON s.candidate_site_id = f.candidate_site_id
            LEFT JOIN latest_stress st ON s.candidate_site_id = st.candidate_site_id
            ORDER BY s.candidate_site_id
        """
        params.extend([limit, offset])
        return self._query(sql, params)

    def get_india_telemetry(self, site_id: str, limit: int = 100, offset: int = 0):
        if not self.india_m3_path.exists():
            return []
            
        sql = f"""
            SELECT candidate_site_id, observation_date, observation_year, observation_month, water_level_raw, quality_flags, is_analytics_ready
            FROM '{self.india_m3_path.as_posix()}'
            WHERE candidate_site_id = ?
            ORDER BY observation_date DESC
            LIMIT ? OFFSET ?
        """
        return self._query(sql, [site_id, limit, offset])

    def get_mh_telemetry(self, site_id: str, limit: int = 100, offset: int = 0):
        if not self.mh_m3_path.exists():
            return []
            
        sql = f"""
            SELECT candidate_site_id, observation_timestamp, observation_date, water_level_raw, quality_flags, is_analytics_ready
            FROM '{self.mh_m3_path.as_posix()}'
            WHERE candidate_site_id = ?
            ORDER BY observation_timestamp DESC
            LIMIT ? OFFSET ?
        """
        return self._query(sql, [site_id, limit, offset])

    def get_india_alerts(self, site_id: str, limit: int = 100, offset: int = 0):
        if not self.india_m6_path.exists():
            return []
            
        sql = f"""
            SELECT observation_date, analytical_season, water_level_raw, 
                   historical_reference, historical_std, standardized_score, historical_sample_count,
                   instantaneous_state, alert_event_state, detector_version
            FROM '{self.india_m6_path.as_posix()}'
            WHERE candidate_site_id = ?
            ORDER BY observation_date DESC
            LIMIT ? OFFSET ?
        """
        return self._query(sql, [site_id, limit, offset])

    def get_mh_alerts(self, site_id: str, limit: int = 100, offset: int = 0):
        if not self.mh_m6_path.exists():
            return []
            
        sql = f"""
            SELECT observation_timestamp, water_level_raw, historical_reference, 
                   deviation, historical_std, standardized_score, time_since_previous_obs_hours,
                   instantaneous_state, alert_event_state, detector_version
            FROM '{self.mh_m6_path.as_posix()}'
            WHERE candidate_site_id = ?
            ORDER BY observation_timestamp DESC
            LIMIT ? OFFSET ?
        """
        return self._query(sql, [site_id, limit, offset])

    def get_india_latest_condition(self, site_id: str):
        if not self.india_m82d_path.exists():
            return None
            
        sql = f"""
            SELECT candidate_site_id, observation_date, analytical_season, water_level_raw, 
                   condition_state, percentile, historical_sample_count,
                   historical_reference_group, condition_method_version
            FROM '{self.india_m82d_path.as_posix()}'
            WHERE candidate_site_id = ?
            ORDER BY observation_date DESC
            LIMIT 1
        """
        results = self._query(sql, [site_id])
        return results[0] if results else None

    def get_mh_latest_condition(self, site_id: str):
        if not self.mh_m82d_path.exists():
            return None
            
        sql = f"""
            SELECT candidate_site_id, observation_timestamp, water_level_raw, 
                   condition_state, percentile, historical_sample_count,
                   historical_reference_group, condition_method_version
            FROM '{self.mh_m82d_path.as_posix()}'
            WHERE candidate_site_id = ?
            ORDER BY observation_timestamp DESC
            LIMIT 1
        """
        results = self._query(sql, [site_id])
        return results[0] if results else None

    def get_mh_latest_persistence_forecast(self, site_id: str):
        if not self.mh_m3_path.exists():
            return None
            
        sql = f"""
            SELECT candidate_site_id, observation_timestamp, water_level_raw
            FROM '{self.mh_m3_path.as_posix()}'
            WHERE candidate_site_id = ? AND is_analytics_ready = true
            ORDER BY observation_timestamp DESC
            LIMIT 1
        """
        results = self._query(sql, [site_id])
        if not results:
            return None
            
        row = results[0]
        return {
            "candidate_site_id": row["candidate_site_id"],
            "latest_observation_timestamp": row["observation_timestamp"],
            "latest_water_level": row["water_level_raw"],
            "predicted_next_water_level": row["water_level_raw"],
            "water_level_unit": "meters",
            "forecast_type": "NEXT_VALID_OBSERVATION",
            "forecast_method": "PERSISTENCE",
            "model_version": "persistence-v1"
        }

    def get_india_latest_drought(self, site_id: str):
        if not self.india_m10_path.exists():
            return None
            
        sql = f"""
            SELECT *
            FROM '{self.india_m10_path.as_posix()}'
            WHERE candidate_site_id = ?
            ORDER BY observation_date DESC
            LIMIT 1
        """
        results = self._query(sql, [site_id])
        return results[0] if results else None

    def get_india_latest_flood_potential(self, site_id: str):
        if not self.india_m11_path.exists():
            return None
            
        sql = f"""
            SELECT *
            FROM '{self.india_m11_path.as_posix()}'
            WHERE candidate_site_id = ?
            ORDER BY observation_timestamp DESC
            LIMIT 1
        """
        results = self._query(sql, [site_id])
        return results[0] if results else None

    def get_mh_latest_flood_potential(self, site_id: str):
        if not self.mh_m11_path.exists():
            return None
            
        sql = f"""
            SELECT *
            FROM '{self.mh_m11_path.as_posix()}'
            WHERE candidate_site_id = ?
            ORDER BY observation_timestamp DESC
            LIMIT 1
        """
        results = self._query(sql, [site_id])
        return results[0] if results else None

    def get_india_latest_stress(self, site_id: str):
        if not self.india_m12_path.exists():
            return None
            
        sql = f"""
            SELECT *
            FROM '{self.india_m12_path.as_posix()}'
            WHERE candidate_site_id = ?
            ORDER BY observation_date DESC
            LIMIT 1
        """
        results = self._query(sql, [site_id])
        return results[0] if results else None

    def get_mh_latest_stress(self, site_id: str):
        if not self.mh_m12_path.exists():
            return None
            
        sql = f"""
            SELECT *
            FROM '{self.mh_m12_path.as_posix()}'
            WHERE candidate_site_id = ?
            ORDER BY observation_timestamp DESC
            LIMIT 1
        """
        results = self._query(sql, [site_id])
        return results[0] if results else None
