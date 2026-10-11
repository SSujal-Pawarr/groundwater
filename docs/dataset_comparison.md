# Dataset Comparison: India-wide vs. Maharashtra DWLR

**Document Version:** 1.0  
**Milestone:** Milestone 2 (Data Forensics, Schema Verification & Canonical Data Model)  
**Date:** October 2026  
**Governing Standard:** [instruction.md](file:///d:/Projects%20ALL/DWLR_GRW_INDIA/instruction.md) (Rules 1, 4, 6, 16, 17)

---

## 1. Executive Summary

A critical objective of Milestone 2 is to determine whether the **India-wide dataset** and the **Maharashtra DWLR dataset** can be unified into a cohesive hydrogeological intelligence platform.

### Crucial Finding: Two Fundamentally Different Observation Paradigms
- **Maharashtra Dataset:** High-frequency, automated digital telemetry (DWLR) recording groundwater levels every 6 hours over a short contemporary time window (5 months in 2026).
- **India-wide Dataset:** Multi-decadal periodic seasonal surveys (CGWB National Hydrograph Monitoring Stations) measured 4 times per year over 31 years (1994–2024).

These two datasets do not share identical sampling cadences, coordinate conventions, or measurement sign conventions. However, they are highly complementary:
- The **India-wide dataset** provides the **macro-temporal baseline** (30-year climate cycles, long-term depletion trends, pre-monsoon vs. post-monsoon aquifer recharge capacity).
- The **Maharashtra dataset** provides the **micro-temporal telemetry dynamics** (6-hourly diurnal drawdown, storm-event infiltration responses, immediate agricultural pumping impacts).

A common data model is technically feasible, but must explicitly distinguish between these observation paradigms rather than force-fitting them into a single homogeneous table.

---

## 2. Direct Architectural Comparison Table

| Attribute | India-wide Dataset (`NEW/data/raw/india/`) | Maharashtra DWLR Dataset (`NEW/data/raw/maharashtra/`) | Common Data Model Compatibility |
| :--- | :--- | :--- | :--- |
| **Source Agency** | Central Ground Water Board (CGWB) / National Water Informatics Centre (NWIC) *(inferred from monitoring pattern)* | Groundwater Surveys & Development Agency (GSDA) / Maharashtra GW *(explicit in `Agency` column)* | **COMPATIBLE:** Capture as `source_agency` string. |
| **Observation Type** | `PERIODIC_SEASONAL_SURVEY` | `HIGH_FREQUENCY_TELEMETRY` | **COMPATIBLE:** Must be partitioned or typed via `observation_type` discriminator. |
| **File Structure** | 6 CSV files partitioned by seasonal month and year bands (~159 MB total) | 1 single large CSV file (~29.2 MB) | **COMPATIBLE:** Abstracted by ingestion loaders. |
| **Total Records** | **1,569,168 rows** | **218,791 rows** | **COMPATIBLE:** Total 1.78M rows easily handled in columnar/relational storage. |
| **Geographic Scope** | All-India (33–37 states/UTs, 780+ districts) | Maharashtra only (34 districts) | **COMPATIBLE:** Hierarchical `Country → State → District`. |
| **Temporal Coverage** | **31 years:** `1994-01-01` to `2024-05-10` | **5 months:** `2026-01-01 00:00` to `2026-05-30 00:00` | **COMPATIBLE:** ISO 8601 timestamps represent both seasonal dates and 6-hourly times. |
| **Observation Frequency**| 4 times per year (Seasonal windows: Jan, Apr/May, Aug, Nov) | Every 6 hours (`00:00`, `06:00`, `12:00`, `18:00`) | **REQUIRES TYPE SEGREGATION:** Downsampling or multi-resolution storage needed. |
| **Station Identification**| **None explicit.** Implicit candidate key from `(lat, lng)` or `(state, district, block, village)`. | **Explicit string:** Column `Station` (1,016 unique stations, e.g. `AALEGAON`). | **REQUIRES MAPPING:** Maharashtra uses named stations; India requires candidate ID generation. |
| **Administrative Codes** | No LGD codes provided. Textual names only. | Includes official `State LGD Code` (27) and `District LGD Code` (e.g. 467). | **COMPATIBLE:** LGD codes can be joined via authoritative master dictionary. |
| **Coordinates Format** | Decimal degrees (`lat`, `lng`). Note: `output1final.csv` has coordinates **swapped**. | Decimal degrees (`Latitude`, `Longitude`). Normal bounds. | **COMPATIBLE:** Normalized to WGS84 `latitude` and `longitude` with swap flag for file 1. |
| **Elevation Datum** | Not provided (missing). | Explicit column `RL_MSL` (Reduced Level relative to MSL in meters). | **COMPATIBLE:** Store `elevation_msl` as optional nullable float. |
| **Measurement Field** | `waterLevel` (`float64`) | `Groundwater Level Telemetry 6 Hourly (meter)` (`float64`) | **COMPATIBLE:** Mapped to `water_level_raw`. |
| **Measurement Units** | Unlabeled in data; inferred meters from distribution. | Explicitly labeled as `meter` in column title. | **COMPATIBLE:** Documented as `meter`. |
| **Sign Convention & Datum**| **100% Non-negative:** $0.0\,\text{m}$ to $299.3\,\text{m}$. Median $3.6\,\text{m}$ (monsoon) to $7.6\,\text{m}$ (pre-monsoon). Typical depth bgl convention. | **91.96% Negative:** $-1791.03\,\text{m}$ to $+213.318\,\text{m}$. Legacy author assumed $-1 \cdot \text{depth}$. | **REQUIRES EXPLICIT MAPPING:** Must retain raw values and record `datum_reference` explicitly. Never silently invert! |
| **Data Quality Issues** | 1 file with inverted coordinates; 5 phantom unnamed columns; synthetic `status`/`trend` labels; 480 concatenated strings. | Extreme sensor spikes ($< -100\,\text{m}$, $> +50\,\text{m}$); missing hydrographic attributes (`Block`, `Village`, `River`). | **COMPATIBLE:** Standardized `data_quality_flags` bitmask or status array. |

---

## 3. Schema Comparison & Mapping

Below is the field-by-field mapping from the two raw schemas into the proposed Canonical Model:

| Canonical Model Target | Source: India-wide Dataset | Source: Maharashtra DWLR Dataset | Harmonization Logic |
| :--- | :--- | :--- | :--- |
| `dataset_id` | Hardcoded: `'INDIA_CGWB_HISTORICAL'` | Hardcoded: `'MAHARASHTRA_GSDA_TELEMETRY'` | Distinguishes data provenance. |
| `observation_type` | `'PERIODIC_SEASONAL'` | `'CONTINUOUS_TELEMETRY'` | Flags sampling cadence for ML and analytics. |
| `site_identifier` | Candidate generated ID: `IND_<hash(state,lat,lng)>` | Raw `Station` name (e.g. `'AALEGAON'`) | Canonical unique station identifier. |
| `state_name` | Raw `state` (trimmed, stripped of concatenated UT prefixes) | Raw `State` (`'Maharashtra'`) | Standardized Title Case. |
| `district_name` | Raw `district` (trimmed) | Raw `District` (trimmed) | Standardized Title Case. |
| `subdistrict_name` | Raw `BLOCK ` (trimmed) | Raw `Tehsil` (trimmed) | Subdistrict / Taluk level. |
| `village_name` | Raw `VILLAGE ` (trimmed) | Raw `Village` or `Station` name | Local settlement name. |
| `latitude` | `lat` (swapped with `lng` if file is `output1final.csv`) | Raw `Latitude` | WGS84 decimal latitude. |
| `longitude` | `lng` (swapped with `lat` if file is `output1final.csv`) | Raw `Longitude` | WGS84 decimal longitude. |
| `elevation_msl` | `NULL` | Raw `RL_MSL` | Elevation above MSL in meters. |
| `observation_timestamp`| Parsed `Date` (`%d/%m/%Y` $\rightarrow$ ISO 8601 `YYYY-MM-DDT00:00:00Z`) | Parsed `Data Acquisition Time` (`%d-%m-%Y %H:%M` $\rightarrow$ ISO 8601) | Normalized UTC or IST timestamp. |
| `water_level_raw` | Raw `waterLevel` | Raw `Groundwater Level Telemetry 6 Hourly (meter)` | Exact unmanipulated numeric measurement. |
| `water_level_unit` | `'UNKNOWN'` (unspecified in source) | `'meter'` (explicit in column header) | Physical measurement unit. |
| `water_level_reference` / `reference_datum` | `'UNKNOWN'` | `'UNKNOWN'` | Unresolved datum explicitly documented. |
| `quality_flags` | Array of flags: `[COORDINATE_INVERTED_CORRECTED]`, `[LABEL_PROVENANCE_UNVERIFIED]`, `[EXTREME_WATER_LEVEL_REVIEW_REQUIRED]` | Array of flags: `[CONFLICTING_DUPLICATE]`, `[EXTREME_WATER_LEVEL_REVIEW_REQUIRED]` | Audit traceability. |

---

## 4. Key Takeaways for Platform Architecture

1. **Do Not Merge Raw Files In Place:**
   The raw files must remain in their respective directories (`NEW/data/raw/india/` and `NEW/data/raw/maharashtra/`).
2. **Support Dual Analytics Paradigms:**
   - **Long-term Hydrogeological Trend Analysis:** Uses the India-wide 30-year dataset (Mann-Kendall trends, seasonal baseline estimation, long-term aquifer depletion).
   - **Real-Time Forecasting & Early Warning:** Uses the Maharashtra high-frequency telemetry dataset (24-hour forecasting, diurnal fluctuations, storm-surge recharge alerts).
3. **Preserve Untrusted Columns Without Validating Them:**
   The India `status` and `trend` columns must be stored as raw unparsed strings (`status_raw`, `trend_raw`) to preserve historical raw records, but excluded from all analytical features and model training.
