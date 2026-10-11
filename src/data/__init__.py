"""
NEW/src/data - Data Ingestion, Normalization & Quality Flagging Package
"""

from .loaders import load_india_raw_dataset, load_maharashtra_raw_dataset
from .normalization import normalize_india_dataframe, normalize_maharashtra_dataframe
from .quality import assess_india_quality, assess_maharashtra_quality, QualityConfig
from .pipeline import run_ingestion_pipeline

__all__ = [
    "load_india_raw_dataset",
    "load_maharashtra_raw_dataset",
    "normalize_india_dataframe",
    "normalize_maharashtra_dataframe",
    "assess_india_quality",
    "assess_maharashtra_quality",
    "QualityConfig",
    "run_ingestion_pipeline",
]
