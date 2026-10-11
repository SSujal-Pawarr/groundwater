"""
NEW/src/features/advanced_analytics.py - Advanced Groundwater Analytics
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import math
from scipy import stats

from src.features.trends import compute_location_trend, compute_rate_of_change
from src.features.seasonal import assign_india_season

def _add_analytical_season(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    df_out = df.copy()
    if "_parsed_date" not in df_out.columns:
        df_out["_parsed_date"] = pd.to_datetime(df_out[date_col], errors="coerce")
    if "observation_month" not in df_out.columns:
        df_out["observation_month"] = df_out["_parsed_date"].dt.month
    return assign_india_season(df_out)

class AdvancedAnalytics:
    @staticmethod
    def get_site_analytics(df: pd.DataFrame, cross_intelligence: Dict[str, Any], date_col: str = "observation_date") -> Dict[str, Any]:
        """Compute all site-level analytics for a given site dataframe."""
        if df.empty:
            return {
                "observation_summary": {"error": "Insufficient history"},
                "water_level_statistics": {},
                "trend": {},
                "seasonal": {},
                "recent_behavior": {},
                "data_quality": {},
                "cross_intelligence": cross_intelligence
            }

        df = df.copy()
        df["_parsed_date"] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.sort_values("_parsed_date").reset_index(drop=True)
        
        valid_df = df.dropna(subset=["water_level_raw"])
        invalid_count = int(len(df) - len(valid_df))
        valid_count = int(len(valid_df))
        
        if valid_count == 0:
            return {
                "observation_summary": {"error": "No valid water level observations"},
                "water_level_statistics": {},
                "trend": {},
                "seasonal": {},
                "recent_behavior": {},
                "data_quality": {"invalid_observation_count": invalid_count},
                "cross_intelligence": cross_intelligence
            }

        # 1. Observation Summary
        first_obs = df["_parsed_date"].min()
        latest_obs = df["_parsed_date"].max()
        span_days = (latest_obs - first_obs).days if pd.notnull(first_obs) and pd.notnull(latest_obs) else 0
        
        # 2. Water Level Stats
        vals = valid_df["water_level_raw"]
        stats_dict = {
            "mean": float(vals.mean()),
            "median": float(vals.median()),
            "minimum": float(vals.min()),
            "maximum": float(vals.max()),
            "standard_deviation": float(vals.std()) if valid_count > 1 else None,
            "p10": float(vals.quantile(0.10)),
            "p25": float(vals.quantile(0.25)),
            "p50": float(vals.quantile(0.50)),
            "p75": float(vals.quantile(0.75)),
            "p90": float(vals.quantile(0.90)),
        }
        
        # 3. Trend
        trend_result = {}
        if valid_count >= 10 and span_days >= 3 * 365:
            # use existing compute_location_trend
            t_df = compute_location_trend(valid_df, site_col="candidate_site_id", date_col=date_col, min_observations=10, min_years_span=3)
            if not t_df.empty:
                t_row = t_df.iloc[0]
                trend_result = {
                    "trend_direction": t_row["trend_direction"],
                    "trend_rate": t_row["slope_per_year"],
                    "trend_method": t_row["method"]
                }
        
        # 4. Seasonal
        seasonal = {}
        if "analytical_season" not in valid_df.columns:
            valid_df = _add_analytical_season(valid_df, date_col=date_col)
            
        if "analytical_season" in valid_df.columns:
            # latest season
            latest_row = valid_df.iloc[-1]
            latest_season = latest_row["analytical_season"]
            season_df = valid_df[valid_df["analytical_season"] == latest_season]
            seasonal = {
                "analytical_season": latest_season,
                "seasonal_median": float(season_df["water_level_raw"].median())
            }

        # 5. Recent Behavior
        recent_behavior = {}
        if valid_count >= 2:
            roc_df = compute_rate_of_change(valid_df, site_col="candidate_site_id", date_col="_parsed_date")
            latest_roc = roc_df.iloc[-1]
            prev_roc = roc_df.iloc[-2] if len(roc_df) >= 3 else None
            recent_behavior = {
                "latest_change": float(latest_roc["wl_change"]) if pd.notnull(latest_roc.get("wl_change")) else None,
                "recent_rate_of_change": float(latest_roc["rate_per_day"]) if pd.notnull(latest_roc.get("rate_per_day")) else None,
            }
            if prev_roc is not None:
                 recent_behavior["previous_change"] = float(prev_roc["wl_change"]) if pd.notnull(prev_roc.get("wl_change")) else None
                 
        # Clean up NaNs from stats dicts
        def clean_dict(d):
            return {k: (v if pd.notnull(v) and not math.isnan(v) else None) for k, v in d.items()}

        stats_dict = clean_dict(stats_dict)
        recent_behavior = clean_dict(recent_behavior)

        return {
            "observation_summary": {
                "observation_count": int(len(df)),
                "first_observation": first_obs.strftime("%Y-%m-%dT%H:%M:%SZ") if pd.notnull(first_obs) else None,
                "latest_observation": latest_obs.strftime("%Y-%m-%dT%H:%M:%SZ") if pd.notnull(latest_obs) else None,
                "observation_span_days": int(span_days),
                "valid_observation_count": valid_count,
                "invalid_observation_count": invalid_count,
            },
            "water_level_statistics": stats_dict,
            "trend": trend_result,
            "seasonal": seasonal,
            "recent_behavior": recent_behavior,
            "data_quality": {
                "valid_observation_count": valid_count,
                "invalid_observation_count": invalid_count,
                "coverage_percentage": None  # Handled separately if expected cadence exists
            },
            "cross_intelligence": cross_intelligence
        }

    @staticmethod
    def calculate_percentile_trajectory(df: pd.DataFrame, date_col: str = "observation_date") -> List[Dict[str, Any]]:
        """
        Calculate historical percentile trajectory with strict leak prevention.
        The reference population for observation N is observations [0..N-1].
        """
        if df.empty:
            return []
            
        df = df.copy()
        df["_parsed_date"] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.sort_values("_parsed_date").reset_index(drop=True)
        valid_df = df.dropna(subset=["water_level_raw"])
        
        trajectory = []
        
        # ensure season exists
        if "analytical_season" not in valid_df.columns:
            valid_df = _add_analytical_season(valid_df, date_col="_parsed_date")

        historical_values = []
        for idx, row in valid_df.iterrows():
            val = row["water_level_raw"]
            
            # calculate percentile based on historical_values BEFORE this one
            if len(historical_values) > 0:
                percentile = float(stats.percentileofscore(historical_values, val) / 100.0)
            else:
                percentile = None
                
            trajectory.append({
                "timestamp": row["_parsed_date"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                "water_level": float(val),
                "historical_percentile": percentile,
                "analytical_season": row.get("analytical_season", None)
            })
            historical_values.append(val)
            
        return trajectory

    @staticmethod
    def calculate_yoy_comparison(df: pd.DataFrame, date_col: str = "observation_date") -> Dict[str, Any]:
        """
        Year over Year analytical comparison.
        Matches latest observation to previous year's observation in same analytical season.
        """
        if df.empty:
            return {}
            
        df = df.copy()
        df["_parsed_date"] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.sort_values("_parsed_date").reset_index(drop=True)
        valid_df = df.dropna(subset=["water_level_raw"])
        
        if valid_df.empty:
            return {}
            
        if "analytical_season" not in valid_df.columns:
            valid_df = _add_analytical_season(valid_df, date_col="_parsed_date")
            
        latest_row = valid_df.iloc[-1]
        latest_season = latest_row.get("analytical_season")
        latest_year = latest_row["_parsed_date"].year
        
        # look for same season in previous year
        prev_df = valid_df[(valid_df["analytical_season"] == latest_season) & (valid_df["_parsed_date"].dt.year == latest_year - 1)]
        if not prev_df.empty:
            prev_row = prev_df.iloc[-1] # closest to end of that season
            return {
                "current_value": float(latest_row["water_level_raw"]),
                "previous_year_value": float(prev_row["water_level_raw"]),
                "difference": float(latest_row["water_level_raw"] - prev_row["water_level_raw"])
            }
            
        return {}

    @staticmethod
    def get_district_analytics(dal, region: str, district: str) -> Dict[str, Any]:
        """Compute district-level distributions across the intelligence modules."""
        # 1. Fetch sites in district
        if region == "india":
            # fetch india sites
            sql = f"SELECT DISTINCT candidate_site_id FROM '{dal.india_m3_path.as_posix()}' WHERE district = ?"
            sites_df = dal.conn.execute(sql, [district]).fetchdf()
        else:
            sql = f"SELECT DISTINCT candidate_site_id FROM '{dal.mh_m3_path.as_posix()}' WHERE district = ?"
            sites_df = dal.conn.execute(sql, [district]).fetchdf()
            
        if sites_df.empty:
            return {
                "region": region,
                "district": district,
                "site_count": 0,
                "condition_distribution": {},
                "alert_distribution": {},
                "drought_distribution": {},
                "flood_distribution": {},
                "stress_distribution": {},
                "data_quality_distribution": {}
            }
            
        site_ids = sites_df["candidate_site_id"].tolist()
        site_count = len(site_ids)
        
        # Build IN clause string safely since it's just a list of candidate_site_ids we just got from duckdb
        id_list = ",".join([f"'{s}'" for s in site_ids])
        
        # Helper to get distributions
        def get_dist(parquet_path, col_name, date_col):
            if not parquet_path or not parquet_path.exists():
                return {}
            # Need to get latest state per site, then group
            sql = f'''
                WITH latest AS (
                    SELECT candidate_site_id, {col_name},
                           ROW_NUMBER() OVER(PARTITION BY candidate_site_id ORDER BY {date_col} DESC) as rn
                    FROM '{parquet_path.as_posix()}'
                    WHERE candidate_site_id IN ({id_list})
                )
                SELECT {col_name}, COUNT(*) as cnt
                FROM latest
                WHERE rn = 1 AND {col_name} IS NOT NULL
                GROUP BY {col_name}
            '''
            df = dal.conn.execute(sql).fetchdf()
            total = df['cnt'].sum()
            if total == 0:
                return {}
            return {row[col_name]: f"{round((row['cnt'] / total) * 100)}%" for _, row in df.iterrows()}

        # Map regions to paths and columns
        if region == "india":
            cond_path, cond_col, cond_date = dal.india_m82d_path, "condition_state", "observation_date"
            alert_path, alert_col, alert_date = dal.india_m6_path, "alert_event_state", "observation_date"
            drought_path, drought_col, drought_date = dal.india_m10_path, "drought_state", "observation_date"
            flood_path, flood_col, flood_date = dal.india_m11_path, "flood_potential_state", "observation_date"
            stress_path, stress_col, stress_date = dal.india_m12_path, "stress_state", "observation_date"
        else:
            cond_path, cond_col, cond_date = dal.mh_m82d_path, "condition_state", "observation_timestamp"
            alert_path, alert_col, alert_date = dal.mh_m6_path, "alert_event_state", "observation_timestamp"
            drought_path, drought_col, drought_date = None, None, None # MH has no drought
            flood_path, flood_col, flood_date = dal.mh_m11_path, "flood_potential_state", "observation_timestamp"
            stress_path, stress_col, stress_date = dal.mh_m12_path, "stress_state", "observation_timestamp"

        return {
            "region": region,
            "district": district,
            "site_count": site_count,
            "condition_distribution": get_dist(cond_path, cond_col, cond_date),
            "alert_distribution": get_dist(alert_path, alert_col, alert_date),
            "drought_distribution": get_dist(drought_path, drought_col, drought_date) if drought_path else {},
            "flood_distribution": get_dist(flood_path, flood_col, flood_date),
            "stress_distribution": get_dist(stress_path, stress_col, stress_date),
            "data_quality_distribution": {
                "total_candidate_sites": site_count
            }
        }
