# Milestone 3: Data Ingestion & Quality Flagging Report

**Generated UTC:** `2026-10-02T19:20:24Z`  
**Execution Duration:** `27.75 seconds`  
**Governing Principles:** [instruction.md](file:///d:/Projects%20ALL/DWLR_GRW_INDIA/instruction.md)

---

## 1. Executive Summary

- **Total India Raw Observations Ingested:** `1,569,168` rows across 6 seasonal CSV files.
- **Total Maharashtra Telemetry Records Ingested:** `218,791` rows across 1,016 stations.
- **India Analytics-Ready Observations:** `1,542,448` (98.3%)
- **Maharashtra Analytics-Ready Observations:** `210,670` (96.29%)
- **Raw Data Immutability:** 100% preserved. Zero raw files modified, zero rows deleted.

---

## 2. India Periodic Seasonal Dataset Summary

### A. Ingestion Breakdown by Raw Source File
| Source File | Raw Rows Ingested | Coordinate Inversion Corrected |
| :--- | :--- | :--- |
| `output1final.csv` | 389,154 | YES (389,042 rows) |
| `output2final.csv` | 112,737 | NO |
| `output3final.csv` | 120,021 | NO |
| `output4final.csv` | 196,895 | NO |
| `outputfinal5.csv` | 363,147 | NO |
| `outputfinal6.csv` | 387,214 | NO |
| **Total** | **1,569,168** | **389,154** |

### B. Quality Flags Distribution (India)
| Quality Flag | Affected Rows | Description / Exclusion Impact |
| :--- | :--- | :--- |
| `LABEL_PROVENANCE_UNVERIFIED` | 1,569,168 | Documented in quality specification |
| `COORDINATE_INVERTED_CORRECTED` | 389,154 | Documented in quality specification |
| `CONFLICTING_DUPLICATE` | 24,900 | Documented in quality specification |
| `EXACT_DUPLICATE` | 1,476 | Documented in quality specification |
| `CANDIDATE_SITE_DATE_DUPLICATE` | 1,411 | Documented in quality specification |
| `MALFORMED_ADMIN_GEOGRAPHY` | 1,318 | Documented in quality specification |
| `COORDINATE_MISSING` | 357 | Documented in quality specification |
| `EXTREME_WATER_LEVEL_REVIEW_REQUIRED` | 159 | Documented in quality specification |
| `SEVERE_EXTREME_WATER_LEVEL_REVIEW_REQUIRED` | 3 | Documented in quality specification |

### C. Water Level Distribution & Sanity (India)
- **Minimum:** `0.0` (unit: UNKNOWN)
- **Median:** `5.2` (unit: UNKNOWN)
- **Mean:** `7.8562` (unit: UNKNOWN)
- **Maximum:** `53943.6` (unit: UNKNOWN) *(includes extreme numerical anomaly e.g. Assam 53,943.6)*
- **Missing Values:** `0`

---

## 3. Maharashtra Continuous Telemetry Dataset Summary

### A. Quality Flags Distribution (Maharashtra)
| Quality Flag | Affected Rows | Description / Exclusion Impact |
| :--- | :--- | :--- |
| `CONFLICTING_DUPLICATE` | 7,309 | Documented in quality specification |
| `EXTREME_WATER_LEVEL_REVIEW_REQUIRED` | 889 | Documented in quality specification |

### B. Water Level Distribution & Sanity (Maharashtra)
- **Minimum:** `-1791.03 meter` *(telemetry sensor excursion)*
- **Median:** `-10.09 meter`
- **Mean:** `-14.068 meter`
- **Maximum:** `213.318 meter` *(telemetry sensor excursion)*
- **Missing Values:** `0`

---

## 4. Analytics Exclusion Rationale

The following records are preserved in processed outputs but flagged with `is_analytics_ready = FALSE`:
1. **`EXTREME_WATER_LEVEL_REVIEW_REQUIRED` / `SEVERE_EXTREME_WATER_LEVEL_REVIEW_REQUIRED`:** Observations exceeding empirical screening thresholds (DATA_QUALITY_SCREENING_THRESHOLD) requiring review.
2. **`COORDINATE_OUT_OF_BOUNDS` / `COORDINATE_MISSING`:** Invalid geographic locations unable to map accurately.
3. **`EXACT_DUPLICATE`:** Identical duplicate entries in source exports.
4. **`CONFLICTING_DUPLICATE`:** Conflicting measurements recorded at the same site on the same date/timestamp.

These records remain fully accessible for data quality auditing and historical traceability.
