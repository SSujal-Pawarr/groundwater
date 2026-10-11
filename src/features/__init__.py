"""
NEW/src/features - Hydrogeological Feature Engineering Package

Milestone 4: Spatial/temporal structure analysis, seasonal features,
lag/rolling features, trend analysis, anomaly indices, and baseline analytics.

Design Principles:
- All features derived from real normalized data only.
- No future leakage in temporal features.
- Dataset-specific logic where temporal structures differ.
- Shared utilities only where genuinely appropriate.
- Provenance preserved for every derived feature.
"""

from .spatial import (
    build_analytical_site_id,
    analyze_location_consistency,
    compute_site_observation_summary,
)
from .temporal import (
    compute_india_temporal_profile,
    compute_maharashtra_temporal_profile,
    compute_observation_gaps,
)
from .seasonal import (
    assign_india_season,
    compute_seasonal_statistics,
    compute_seasonal_anomaly,
    compute_yoy_seasonal_change,
)
from .trends import (
    compute_location_trend,
    compute_rate_of_change,
)
from .anomaly import (
    compute_seasonal_z_score,
)
from .baselines import (
    compute_persistence_baseline,
    compute_seasonal_historical_baseline,
    compute_maharashtra_persistence_baseline,
)

__all__ = [
    "build_analytical_site_id",
    "analyze_location_consistency",
    "compute_site_observation_summary",
    "compute_india_temporal_profile",
    "compute_maharashtra_temporal_profile",
    "compute_observation_gaps",
    "assign_india_season",
    "compute_seasonal_statistics",
    "compute_seasonal_anomaly",
    "compute_yoy_seasonal_change",
    "compute_location_trend",
    "compute_rate_of_change",
    "compute_seasonal_z_score",
    "compute_persistence_baseline",
    "compute_seasonal_historical_baseline",
    "compute_maharashtra_persistence_baseline",
]
