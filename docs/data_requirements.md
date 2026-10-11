# Data Requirements Specification: DWLR Telemetry Ingestion

**Document Version:** 1.0  
**Current Milestone:** Milestone 1 (Foundation Initialization & Legacy Audit)  
**Governing Standard:** [instruction.md](file:///d:/Projects%20ALL/DWLR_GRW_INDIA/instruction.md) (Rules 1, 3, 4, 5, 6, 16, 17)

---

## 1. Overview & Purpose

Before designing or implementing the automated data ingestion, cleaning, and normalization pipeline, both the **India-wide DWLR dataset** and the **Maharashtra DWLR dataset** must undergo rigorous data profiling.

This document formalizes the mandatory inspection checklist. Under no circumstances may pipeline code assume column names, units, physical reference datums, sampling frequencies, or coordinate systems without documented verification.

Where values are not yet directly verified from source data files, they are explicitly marked as:  
`UNKNOWN — REQUIRES DATA INSPECTION`.

---

## 2. Pre-Pipeline Data Inspection Matrix

| Requirement Attribute | Maharashtra DWLR Dataset (Status & Findings) | India-wide DWLR Dataset (Status & Requirements) |
| :--- | :--- | :--- |
| **1. File Format & Encoding** | **VERIFIED:** CSV format (`UTF-8` encoded text, comma-delimited). File size: 29.2 MB. | **UNKNOWN — REQUIRES DATA INSPECTION** (Must verify file format: CSV, Parquet, GeoPackage, API JSON, or Excel; encoding: UTF-8 or CP-1252). |
| **2. Dataset Schema & Columns** | **VERIFIED (21 columns):** `SlNo`, `Station`, `Agency`, `State LGD Code`, `State`, `District LGD Code`, `District`, `Tehsil`, `Block`, `Village`, `River`, `Basin`, `Tributary`, `Subtributary`, `SubSubtributary`, `Local River`, `Latitude`, `Longitude`, `RL_MSL`, `Data Acquisition Time`, `Groundwater Level Telemetry 6 Hourly (meter)`. | **UNKNOWN — REQUIRES DATA INSPECTION** (Must inspect raw file headers, data types, and determine column mapping to unified schema). |
| **3. Station Identifier** | **VERIFIED:** Column `Station` (1,016 unique stations). Upper-case string (e.g. `AALEGAON`, `SAVALI`). Needs verification if station names are globally unique or if composite keys (`State + District + Station`) are required. | **UNKNOWN — REQUIRES DATA INSPECTION** (Must identify station identifier column: CGWB Site ID, WRIS Code, or Station Name; verify uniqueness). |
| **4. State Identifier** | **VERIFIED:** Column `State` (`Maharashtra`) and `State LGD Code` (`27`). | **UNKNOWN — REQUIRES DATA INSPECTION** (Must verify state naming conventions, LGD codes, spelling variations across 28 states & 8 UTs). |
| **5. District Identifier** | **VERIFIED:** Column `District` (34 unique districts) and `District LGD Code`. | **UNKNOWN — REQUIRES DATA INSPECTION** (Must verify district names against official Census/LGD 2021+ administrative master lists). |
| **6. Subdistrict / Tehsil / Block**| **PARTIALLY VERIFIED:** Column `Tehsil` contains subdistrict names; `Block` contains `"-"` for nearly all rows. | **UNKNOWN — REQUIRES DATA INSPECTION** (Must verify presence and coverage of subdistrict, taluk, block, or tehsil hierarchies). |
| **7. Latitude** | **VERIFIED:** Column `Latitude` (`float64`). Observed values in Maharashtra range between approx. 15.6°N and 22.0°N. | **UNKNOWN — REQUIRES DATA INSPECTION** (Must verify coordinate format: decimal degrees vs DMS; range checks: 6.0°N to 37.5°N for India). |
| **8. Longitude** | **VERIFIED:** Column `Longitude` (`float64`). Observed values in Maharashtra range between approx. 72.6°E and 80.9°E. | **UNKNOWN — REQUIRES DATA INSPECTION** (Must verify coordinate format: decimal degrees vs DMS; range checks: 68.0°E to 97.5°E for India). |
| **9. Groundwater Measurement Field**| **VERIFIED:** Column name `Groundwater Level Telemetry 6 Hourly (meter)`. Numeric `float64`. | **UNKNOWN — REQUIRES DATA INSPECTION** (Must identify the exact column representing groundwater level; check for raw vs corrected readings). |
| **10. Measurement Unit** | **VERIFIED:** Labeled as `meter` in column title. | **UNKNOWN — REQUIRES DATA INSPECTION** (Must verify whether values are in meters, feet, or raw sensor pressure; check for unit variations across states). |
| **11. Reference Datum** | **UNKNOWN — REQUIRES DATA INSPECTION:** Observed values contain both negative (91.96%) and positive (8.04%) numbers. Legacy code assumed negative means Depth Below Ground Level (m bgl). Official CGWB / GSDA confirmation is required to prove whether measurements are depth bgl, head above sensor, or elevation above MSL. | **UNKNOWN — REQUIRES DATA INSPECTION** (Crucial: CGWB telemetry often records Depth Below Ground Level (m bgl) as positive, whereas piezometric head is relative to MSL. Must determine exact reference datum). |
| **12. Timestamp Field & Format** | **VERIFIED:** Column `Data Acquisition Time`. Format: `%d-%m-%Y %H:%M` (e.g., `01-01-2026 00:00`). | **UNKNOWN — REQUIRES DATA INSPECTION** (Must inspect timestamp format: ISO 8601, DD/MM/YYYY, or Epoch; determine timezone assumptions: IST [UTC+5:30] vs UTC). |
| **13. Sampling Frequency** | **VERIFIED:** 6-hourly nominal interval (`00:00`, `06:00`, `12:00`, `18:00`). | **UNKNOWN — REQUIRES DATA INSPECTION** (Must determine sampling cadence: hourly, 6-hourly, daily, or irregular). |
| **14. Date Coverage** | **VERIFIED:** Spans `01-01-2026 00:00` to `30-05-2026 00:00` (150 days). | **UNKNOWN — REQUIRES DATA INSPECTION** (Must identify start date, end date, and historical depth of national data). |
| **15. Missing Values** | **VERIFIED:** 0 null values in the groundwater column. Hydrographic fields (`Block`, `Village`, `River`, `Basin`, `Tributary`) contain literal `"-"` placeholder strings. | **UNKNOWN — REQUIRES DATA INSPECTION** (Must profile null percentages per column and identify sentinel missing-value markers like `-999`, `NaN`, `null`, `""`). |
| **16. Duplicates** | **UNKNOWN — REQUIRES DATA INSPECTION:** Need systematic verification of duplicate timestamps per station (`Station + Data Acquisition Time`). | **UNKNOWN — REQUIRES DATA INSPECTION** (Must check for duplicated station-timestamp records across multiple ingestion files). |
| **17. Outliers & Sensor Errors** | **VERIFIED:** Sensor readings exhibit severe outliers: minimum is `-1791.03 m`, maximum is `+213.318 m`. 889 values fall outside physical bounds `[-100, +50]`. | **UNKNOWN — REQUIRES DATA INSPECTION** (Must establish physical plausibility bounds based on local aquifer depths and topography). |
| **18. Geographic Consistency** | **UNKNOWN — REQUIRES DATA INSPECTION:** Need validation that all station coordinates fall strictly within their designated district/state polygons using shapefile point-in-polygon checks. | **UNKNOWN — REQUIRES DATA INSPECTION** (Must detect swapped lat/lon, inverted coordinates, or points outside Indian territorial waters/land boundaries). |
| **19. Temporal Consistency** | **UNKNOWN — REQUIRES DATA INSPECTION:** Need station-by-station gap profiling to detect missing transmission windows, dead sensors, and battery failures. | **UNKNOWN — REQUIRES DATA INSPECTION** (Must profile continuity of telemetry transmissions across national network). |
| **20. Metadata & Source Information**| **PARTIALLY VERIFIED:** Column `Agency` states `Maharashtra GW`. `RL_MSL` provides reduced level in meters for some stations. Official data dictionary or sensor manual is not yet attached. | **UNKNOWN — REQUIRES DATA INSPECTION** (Must document authoritative source: CGWB, Ministry of Jal Shakti, India-WRIS, or State Groundwater Authorities). |

---

## 3. Pre-Pipeline Validation Criteria

Before any code in `NEW/src/` marks a raw dataset as ready for downstream analytics:
1. Every unknown item above must be systematically investigated using read-only profiling scripts.
2. A formal dataset dictionary must be generated detailing the verified meaning of each field.
3. The reference datum must be conclusively identified from official documentation or physical benchmarks.
4. Validation flags (e.g., `VALID`, `OUT_OF_BOUNDS`, `SENSOR_STUCK`, `TEMPORAL_GAP`) must be applied without destructively dropping raw data rows.
