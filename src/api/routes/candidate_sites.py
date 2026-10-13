from fastapi import APIRouter, Query, Path, HTTPException
from pathlib import Path as FilePath
from typing import List, Optional
from src.api.dal import GroundwaterDAL

router = APIRouter(prefix="/api/v1")
dal = GroundwaterDAL()


def _require_dataset(path: FilePath):
    if not path.exists():
        relative_path = path.relative_to(dal.project_root)
        raise HTTPException(
            status_code=503,
            detail=(
                f"Dataset unavailable: {relative_path}. Restore this normalized Parquet file. "
                "If alert artifacts are available, run `python scripts/rebuild_processed_from_alerts.py`."
            ),
        )

# India Candidate Sites
@router.get("/india/candidate-sites", tags=["India"])
def list_india_candidate_sites(
    limit: int = Query(100, ge=1, le=5000), 
    offset: int = Query(0, ge=0),
    state: Optional[str] = None,
    min_lat: Optional[float] = None,
    max_lat: Optional[float] = None,
    min_lng: Optional[float] = None,
    max_lng: Optional[float] = None
):
    """List India candidate sites (analytical groupings)."""
    _require_dataset(dal.india_m3_path)
    return dal.get_india_candidate_sites(
        limit=limit, offset=offset, state=state,
        min_lat=min_lat, max_lat=max_lat, min_lng=min_lng, max_lng=max_lng
    )

@router.get("/india/candidate-sites/{candidate_site_id}/telemetry", tags=["India"])
def get_india_telemetry(
    candidate_site_id: str = Path(..., description="Analytical identifier for the site"),
    limit: int = Query(100, ge=1, le=1000), 
    offset: int = Query(0, ge=0)
):
    """Get periodic M3 telemetry observations."""
    results = dal.get_india_telemetry(candidate_site_id, limit, offset)
    if not results and offset == 0:
        raise HTTPException(status_code=404, detail="Site not found or no telemetry available.")
    return results

@router.get("/india/candidate-sites/{candidate_site_id}/alerts", tags=["India"])
def get_india_alerts(
    candidate_site_id: str = Path(..., description="Analytical identifier for the site"),
    limit: int = Query(100, ge=1, le=1000), 
    offset: int = Query(0, ge=0)
):
    """Get causal alert states for India candidate sites."""
    results = dal.get_india_alerts(candidate_site_id, limit, offset)
    if not results and offset == 0:
        raise HTTPException(status_code=404, detail="Site not found or no alerts available.")
    return results

@router.get("/india/candidate-sites/{candidate_site_id}/condition", tags=["India"])
def get_india_condition(
    candidate_site_id: str = Path(..., description="Analytical identifier for the site")
):
    """Get the latest statistical groundwater condition state for this site."""
    result = dal.get_india_latest_condition(candidate_site_id)
    if not result:
        raise HTTPException(status_code=404, detail="Site not found or no condition available.")
    # Add unknown unit constraint explicitly
    result["water_level_unit"] = "UNKNOWN"
    return result

# Maharashtra Candidate Sites
@router.get("/maharashtra/candidate-sites", tags=["Maharashtra"])
def list_mh_candidate_sites(
    limit: int = Query(100, ge=1, le=5000), 
    offset: int = Query(0, ge=0),
    district: Optional[str] = None,
    min_lat: Optional[float] = None,
    max_lat: Optional[float] = None,
    min_lng: Optional[float] = None,
    max_lng: Optional[float] = None
):
    """List Maharashtra candidate sites and station names."""
    _require_dataset(dal.mh_m3_path)
    return dal.get_mh_candidate_sites(
        limit=limit, offset=offset, district=district,
        min_lat=min_lat, max_lat=max_lat, min_lng=min_lng, max_lng=max_lng
    )

@router.get("/maharashtra/candidate-sites/{candidate_site_id}/telemetry", tags=["Maharashtra"])
def get_mh_telemetry(
    candidate_site_id: str = Path(..., description="Analytical identifier for the site"),
    limit: int = Query(100, ge=1, le=1000), 
    offset: int = Query(0, ge=0)
):
    """Get continuous 6-hourly M3 telemetry observations."""
    results = dal.get_mh_telemetry(candidate_site_id, limit, offset)
    if not results and offset == 0:
        raise HTTPException(status_code=404, detail="Site not found or no telemetry available.")
    return results

@router.get("/maharashtra/candidate-sites/{candidate_site_id}/alerts", tags=["Maharashtra"])
def get_mh_alerts(
    candidate_site_id: str = Path(..., description="Analytical identifier for the site"),
    limit: int = Query(100, ge=1, le=1000), 
    offset: int = Query(0, ge=0)
):
    """Get causal alert states for Maharashtra candidate sites."""
    results = dal.get_mh_alerts(candidate_site_id, limit, offset)
    if not results and offset == 0:
        raise HTTPException(status_code=404, detail="Site not found or no alerts available.")
    return results

@router.get("/maharashtra/candidate-sites/{candidate_site_id}/condition", tags=["Maharashtra"])
def get_mh_condition(
    candidate_site_id: str = Path(..., description="Analytical identifier for the site")
):
    """Get the latest statistical groundwater condition state for this site."""
    result = dal.get_mh_latest_condition(candidate_site_id)
    if not result:
        raise HTTPException(status_code=404, detail="Site not found or no condition available.")
    # Expose unit based on M3 normalization semantics
    result["water_level_unit"] = "meters"
    return result

@router.get("/maharashtra/candidate-sites/{candidate_site_id}/forecast", tags=["Maharashtra"])
def get_mh_forecast(
    candidate_site_id: str = Path(..., description="Analytical identifier for the site")
):
    """Get the latest next-valid-observation persistence forecast for this site."""
    result = dal.get_mh_latest_persistence_forecast(candidate_site_id)
    if not result:
        raise HTTPException(status_code=404, detail="Site not found or no analytics-ready observation available.")
    return result
