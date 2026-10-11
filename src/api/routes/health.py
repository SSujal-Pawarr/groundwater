from fastapi import APIRouter
from src.api.dal import GroundwaterDAL

router = APIRouter()
dal = GroundwaterDAL()

@router.get("/health", tags=["System"])
def health_check():
    """Basic API readiness and DAL connection check."""
    return {
        "status": "ok",
        "dal_healthy": dal.is_healthy()
    }
