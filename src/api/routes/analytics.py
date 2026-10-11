from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List, Dict, Any

from src.api.dal import GroundwaterDAL
from src.features.advanced_analytics import AdvancedAnalytics
import pandas as pd

router = APIRouter(prefix="/api/v1", tags=["Analytics"])

def get_dal():
    dal = GroundwaterDAL()
    try:
        yield dal
    finally:
        pass

def get_cross_intel(dal: GroundwaterDAL, region: str, candidate_site_id: str) -> Dict[str, Any]:
    if region == "india":
        cond = dal.get_india_latest_condition(candidate_site_id)
        alert = dal.get_india_alerts(candidate_site_id, limit=1)
        drought = dal.get_india_latest_drought(candidate_site_id)
        flood = dal.get_india_latest_flood_potential(candidate_site_id)
        stress = dal.get_india_latest_stress(candidate_site_id)
        
        return {
            "candidate_site_id": candidate_site_id,
            "condition": cond["condition_state"] if cond else "INSUFFICIENT_EVIDENCE",
            "alert": alert[0]["alert_event_state"] if alert else "INSUFFICIENT_EVIDENCE",
            "forecast": "UNAVAILABLE", # India has no persistence forecast
            "drought": drought["drought_status"] if drought else "INSUFFICIENT_HISTORY",
            "flood_potential": flood["flood_potential_state"] if flood else "INSUFFICIENT_EVIDENCE",
            "stress": stress["stress_state"] if stress else "INSUFFICIENT_EVIDENCE",
        }
    else:
        cond = dal.get_mh_latest_condition(candidate_site_id)
        alert = dal.get_mh_alerts(candidate_site_id, limit=1)
        forecast = dal.get_mh_latest_persistence_forecast(candidate_site_id)
        flood = dal.get_mh_latest_flood_potential(candidate_site_id)
        stress = dal.get_mh_latest_stress(candidate_site_id)
        
        return {
            "candidate_site_id": candidate_site_id,
            "condition": cond["condition_state"] if cond else "INSUFFICIENT_EVIDENCE",
            "alert": alert[0]["alert_event_state"] if alert else "INSUFFICIENT_EVIDENCE",
            "forecast": "PERSISTENCE" if forecast else "INSUFFICIENT_EVIDENCE",
            "drought": "INSUFFICIENT_HISTORY", # MH has no drought
            "flood_potential": flood["flood_potential_state"] if flood else "INSUFFICIENT_EVIDENCE",
            "stress": stress["stress_state"] if stress else "INSUFFICIENT_EVIDENCE",
        }


@router.get("/{region}/candidate-sites/{candidate_site_id}/analytics")
def get_site_analytics(region: str, candidate_site_id: str, dal: GroundwaterDAL = Depends(get_dal)):
    if region not in ["india", "maharashtra"]:
        raise HTTPException(status_code=400, detail="Invalid region")
        
    if region == "india":
        raw_data = dal.get_india_telemetry(candidate_site_id, limit=100000)
        date_col = "observation_date"
    else:
        raw_data = dal.get_mh_telemetry(candidate_site_id, limit=100000)
        date_col = "observation_timestamp"
        
    cross_intel = get_cross_intel(dal, region, candidate_site_id)
    
    df = pd.DataFrame(raw_data)
    analytics = AdvancedAnalytics.get_site_analytics(df, cross_intel, date_col=date_col)
    analytics["candidate_site_id"] = candidate_site_id
    analytics["region"] = region
    
    # Calculate YoY only for India
    if region == "india":
        yoy = AdvancedAnalytics.calculate_yoy_comparison(df, date_col=date_col)
        analytics["year_over_year"] = yoy
        
    return analytics

@router.get("/{region}/candidate-sites/{candidate_site_id}/percentile-trajectory")
def get_site_percentile_trajectory(region: str, candidate_site_id: str, dal: GroundwaterDAL = Depends(get_dal)):
    if region not in ["india", "maharashtra"]:
        raise HTTPException(status_code=400, detail="Invalid region")
        
    if region == "india":
        raw_data = dal.get_india_telemetry(candidate_site_id, limit=100000)
        date_col = "observation_date"
    else:
        raw_data = dal.get_mh_telemetry(candidate_site_id, limit=100000)
        date_col = "observation_timestamp"
        
    df = pd.DataFrame(raw_data)
    points = AdvancedAnalytics.calculate_percentile_trajectory(df, date_col=date_col)
    
    return {
        "candidate_site_id": candidate_site_id,
        "points": points
    }

@router.get("/{region}/candidate-sites/{candidate_site_id}/timeline")
def get_site_timeline(region: str, candidate_site_id: str, dal: GroundwaterDAL = Depends(get_dal)):
    if region not in ["india", "maharashtra"]:
        raise HTTPException(status_code=400, detail="Invalid region")
        
    if region == "india":
        raw_data = dal.get_india_telemetry(candidate_site_id, limit=100000)
        date_col = "observation_date"
    else:
        raw_data = dal.get_mh_telemetry(candidate_site_id, limit=100000)
        date_col = "observation_timestamp"
        
    if not raw_data:
        return {"candidate_site_id": candidate_site_id, "points": []}
        
    # We need to compute rate of change.
    df = pd.DataFrame(raw_data)
    from src.features.trends import compute_rate_of_change
    roc_df = compute_rate_of_change(df, site_col="candidate_site_id", date_col=date_col)
    
    # We join this with the condition and alert state if we want? But wait, the API requirements just say:
    # time series for groundwater level, historical percentile, rate of change, condition state, alert state
    # This might be simpler if we just merge from DAL? 
    # M82D condition table has condition_state. M6 has alert_state.
    points = []
    
    import math
    for idx, row in roc_df.iterrows():
        roc = float(row["rate_per_day"]) if "rate_per_day" in row and pd.notnull(row["rate_per_day"]) else None
        dt = pd.to_datetime(row[date_col]).strftime("%Y-%m-%dT%H:%M:%SZ")
        points.append({
            "timestamp": dt,
            "water_level": float(row["water_level_raw"]) if pd.notnull(row["water_level_raw"]) else None,
            "rate_of_change": roc
        })
        
    # It says "condition state" and "alert state". We can query those from M82d and M6, but it's probably easier to just return them as separate lists or merge them here. 
    # Actually, fetching condition and alert state for each observation might be slow.
    # Let's fetch the entire condition/alert history for this site and merge on date.
    if region == "india":
        cond_data = pd.DataFrame(dal._query(f"SELECT observation_date as ts, condition_state FROM '{dal.india_m82d_path.as_posix()}' WHERE candidate_site_id = '{candidate_site_id}'"))
        alert_data = pd.DataFrame(dal._query(f"SELECT observation_date as ts, alert_event_state FROM '{dal.india_m6_path.as_posix()}' WHERE candidate_site_id = '{candidate_site_id}'"))
    else:
        cond_data = pd.DataFrame(dal._query(f"SELECT observation_timestamp as ts, condition_state FROM '{dal.mh_m82d_path.as_posix()}' WHERE candidate_site_id = '{candidate_site_id}'"))
        alert_data = pd.DataFrame(dal._query(f"SELECT observation_timestamp as ts, alert_event_state FROM '{dal.mh_m6_path.as_posix()}' WHERE candidate_site_id = '{candidate_site_id}'"))
        
    # convert dates to match formatting
    cond_map = {}
    if not cond_data.empty:
        cond_data["ts"] = pd.to_datetime(cond_data["ts"]).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        cond_map = cond_data.set_index("ts")["condition_state"].to_dict()
        
    alert_map = {}
    if not alert_data.empty:
        alert_data["ts"] = pd.to_datetime(alert_data["ts"]).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        alert_map = alert_data.set_index("ts")["alert_event_state"].to_dict()
        
    for p in points:
        p["condition_state"] = cond_map.get(p["timestamp"])
        p["alert_state"] = alert_map.get(p["timestamp"])

    return {
        "candidate_site_id": candidate_site_id,
        "points": points
    }


@router.get("/{region}/districts/{district}/analytics")
def get_district_analytics(region: str, district: str, dal: GroundwaterDAL = Depends(get_dal)):
    if region not in ["india", "maharashtra"]:
        raise HTTPException(status_code=400, detail="Invalid region")
        
    return AdvancedAnalytics.get_district_analytics(dal, region, district)
