"""
NEW/src/alerting/config.py - Causal Alert Engine Configuration

Defines statistical severity thresholds and data requirements for alerts.
IMPORTANT: These are statistical/analytical policies, not official hydrological thresholds.
"""

from dataclasses import dataclass, field
from typing import Set

@dataclass
class AlertConfig:
    # --- India Periodic Settings ---
    # Minimum distinct historical years needed before calculating an anomaly score
    india_min_historical_years: int = 5
    
    # Statistical Severity Thresholds for India (Z-Score of deviation from strictly prior historical mean)
    # These are unitless standard deviations
    india_z_watch: float = 2.0
    india_z_warning: float = 3.0
    india_z_critical: float = 4.0
    
    # --- Maharashtra Telemetry Settings ---
    # Empirical Sequence Break Policy
    # 36 hours captures up to the ~90th percentile of gaps while breaking true missing periods.
    # This is an operational policy to prevent comparing telemetry separated by weeks,
    # not a hydrological fact.
    mh_max_gap_hours: float = 36.0
    
    # Minimum history to form a reference standard deviation
    mh_min_historical_obs: int = 20
    
    # Statistical Severity Thresholds for Maharashtra
    # Using Z-Score of the persistence residual (normalized by strictly backward-looking std dev)
    mh_z_watch: float = 2.0
    mh_z_warning: float = 3.0
    mh_z_critical: float = 4.0
    
    # --- State Machine Settings ---
    # Number of consecutive NORMAL instantaneous classifications needed to recover
    # an active alert event back to NORMAL state.
    recovery_cooldown_periods: int = 3
    
    # --- Quality Gating ---
    # If any of these flags are present, the observation generates a DATA_QUALITY_EVENT instead of a statistical alert
    disqualifying_flags: Set[str] = field(default_factory=lambda: {
        "EXTREME_WATER_LEVEL_REVIEW_REQUIRED",
        "SEVERE_EXTREME_WATER_LEVEL_REVIEW_REQUIRED",
        "COORDINATE_OUT_OF_BOUNDS",
        "COORDINATE_MISSING",
        "EXACT_DUPLICATE",
        "CONFLICTING_DUPLICATE"
    })

    # Alert States
    STATE_NORMAL = "NORMAL"
    STATE_WATCH = "WATCH"
    STATE_WARNING = "WARNING"
    STATE_CRITICAL = "CRITICAL_STATISTICAL_DEVIATION"
    STATE_INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    STATE_GAPPED = "SEQUENCE_GAPPED"
    STATE_DATA_QUALITY = "DATA_QUALITY_EVENT"
    
    # Rank of operational states for escalation
    SEVERITY_RANK = {
        STATE_NORMAL: 0,
        STATE_WATCH: 1,
        STATE_WARNING: 2,
        STATE_CRITICAL: 3
    }
