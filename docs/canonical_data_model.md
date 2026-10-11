# Canonical Conceptual Data Model Proposal

**Document Version:** 1.0  
**Milestone:** Milestone 2 (Data Forensics, Schema Verification & Canonical Data Model)  
**Date:** October 2026  
**Governing Standard:** [instruction.md](file:///d:/Projects%20ALL/DWLR_GRW_INDIA/instruction.md) (Rules 1, 4, 6, 17, 18)

---

## 1. Architectural Motivation

The India-wide groundwater intelligence platform requires a unified, extensible conceptual data model capable of ingesting and querying:
1. **Periodic Seasonal Monitoring Data:** Decadal, low-frequency manual well surveys (e.g. India CGWB national dataset).
2. **Automated Real-Time Telemetry Data:** Sub-daily, high-frequency digital telemetry (e.g. Maharashtra GSDA DWLR dataset).
3. **Future Telemetry Expansion:** India-wide DWLR networks from all states and union territories.

### Non-Negotiable Modeling Requirements
- **No Physical Database Implementation Yet:** This document proposes the conceptual and logical schema. Physical tables, DDL migrations, and ORMs are deferred to subsequent verified milestones.
- **Traceable Provenance:** Every record must track its source dataset, source filename, and raw measurement.
- **Unresolved Semantics Kept Explicit:** If reference datums or units are unconfirmed by official documentation, they are explicitly marked as `UNKNOWN`.
- **Preservation of Raw Fields:** Fields like `status` and `trend` from raw files are preserved verbatim as audit trails (`status_raw`, `trend_raw`), but decoupled from computational features.

---

## 2. Conceptual Domain Entities

The proposed model organizes groundwater information into six distinct conceptual domains:

```text
┌────────────────────────┐         ┌────────────────────────┐
│     Source Dataset     │         │   Geographic Entity    │
│  (Provenance / Agency) │         │ (Country/State/District│
└───────────┬────────────┘         └───────────┬────────────┘
            │                                  │
            ▼                                  ▼
┌───────────────────────────────────────────────────────────┐
│                    Monitoring Site                        │
│   (Station / Well / Borewell / Candidate Identity)       │
└───────────────────────────┬───────────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────┐
│               Groundwater Observation                     │
│    (Timestamp, Measurement, Quality Flags, Provenance)    │
└───────────────────────────┬───────────────────────────────┘
                            │
            ┌───────────────┴───────────────┐
            ▼                               ▼
┌────────────────────────┐      ┌────────────────────────┐
│  Periodic Observation  │      │ Telemetry Observation  │
│   (Seasonal Survey)    │      │  (High-Freq Continuous)│
└────────────────────────┘      └────────────────────────┘
```

---

## 3. Logical Entity Specifications

### Entity 1: `source_dataset` (Provenance Metadata)
Captures the overarching origin and administration of an ingested dataset.

| Attribute | Data Type | Nullable | Description / Semantics |
| :--- | :--- | :--- | :--- |
| `dataset_id` | String (PK) | No | Unique code (e.g., `'INDIA_CGWB_HISTORICAL'`, `'MAHARASHTRA_DWLR_TELEMETRY'`). |
| `dataset_name` | String | No | Human-readable title of the dataset. |
| `agency_name` | String | No | Organization responsible (e.g., `'CGWB'`, `'GSDA'`). |
| `observation_paradigm` | Enum | No | `'PERIODIC_SEASONAL'` or `'CONTINUOUS_TELEMETRY'`. |
| `nominal_frequency` | String | No | Expected sampling interval (`'SEASONAL_4X_YEAR'` or `'6_HOURLY'`). |
| `geographic_scope` | String | No | Geographic coverage (`'INDIA_NATIONAL'` or `'STATE_MAHARASHTRA'`). |
| `license_provenance` | String | Yes | Official data source link or portal reference. |

---

### Entity 2: `geographic_hierarchy` (Administrative Boundaries)
Standardized administrative spatial hierarchy aligned with the Local Government Directory (LGD).

| Attribute | Data Type | Nullable | Description / Semantics |
| :--- | :--- | :--- | :--- |
| `geo_id` | String (PK) | No | Canonical geographic identifier (composite or LGD based). |
| `state_name` | String | No | Standardized state/UT name. |
| `state_lgd_code` | Integer | Yes | Official LGD state code (e.g., `27` for Maharashtra; `UNKNOWN` for unlinked). |
| `district_name` | String | No | Standardized district name. |
| `district_lgd_code` | Integer | Yes | Official LGD district code (e.g., `467`). |
| `subdistrict_name` | String | Yes | Tehsil, Taluk, or Block name. |
| `village_name` | String | Yes | Settlement or revenue village name. |

---

### Entity 3: `monitoring_site` (Physical Monitoring Location)
Represents a unique physical monitoring well, piezometer, or DWLR station on the ground.

| Attribute | Data Type | Nullable | Description / Semantics |
| :--- | :--- | :--- | :--- |
| `site_id` | String (PK) | No | Canonical platform site identifier. |
| `site_code_source` | String | Yes | Identifier given by source agency (e.g. Station name `'AALEGAON'`; `NULL` if none). |
| `candidate_site_id` | String | No | Deterministic hash constructed from `(state, district, village, lat_4dp, lon_4dp)`. |
| `site_name` | String | No | Primary station or village label. |
| `site_type` | Enum | No | `'DWLR_BOREWELL'`, `'OPEN_DUG_WELL'`, `'PIEZOMETER'`, or `'UNKNOWN'`. |
| `latitude` | Float64 | No | WGS84 Latitude ($-90.0$ to $+90.0$; India bounds $6.0^{\circ}\text{N} - 38.0^{\circ}\text{N}$). |
| `longitude` | Float64 | No | WGS84 Longitude ($-180.0$ to $+180.0$; India bounds $68.0^{\circ}\text{E} - 98.0^{\circ}\text{E}$). |
| `elevation_msl` | Float64 | Yes | Reduced level relative to Mean Sea Level (meters); `UNKNOWN` if not provided. |
| `is_coordinate_swapped` | Boolean | No | Flag indicating if source file had coordinates inverted and required correction. |
| `geo_id` | String (FK) | Yes | Foreign key to `geographic_hierarchy`. |

---

### Entity 4: `groundwater_observation` (Core Fact Table)
Stores individual groundwater observations across both periodic surveys and telemetry.

| Attribute | Data Type | Nullable | Description / Semantics |
| :--- | :--- | :--- | :--- |
| `observation_id` | String (PK) | No | Unique observation record UUID or hash. |
| `site_id` | String (FK) | No | Link to `monitoring_site`. |
| `dataset_id` | String (FK) | No | Link to `source_dataset`. |
| `source_filename` | String | No | Raw source filename (e.g. `'output1final.csv'`). |
| `observation_timestamp`| Timestamp | No | Normalized observation date/time in ISO 8601 (`UTC` or `Asia/Kolkata`). |
| `water_level_raw` | Float64 | No | Unaltered numeric measurement from source file. |
| `water_level_unit` | String | No | Labeled unit; `'meter'` (verified for Maharashtra); `'UNKNOWN'` (unspecified in source for India). |
| `water_level_reference` / `reference_datum` | String | No | `'UNKNOWN'` for both datasets until datum is confirmed by authoritative engineering documentation. |
| `season_code` | Enum | Yes | `'RABI_WINTER'`, `'PRE_MONSOON'`, `'MONSOON'`, `'POST_MONSOON'`, or `'CONTINUOUS'`. |
| `status_raw` | String | Yes | Verbatim raw status label from source file (e.g. `'over-exploited'`, `'safe'`). |
| `trend_raw` | String | Yes | Verbatim raw trend label from source file (e.g. `'improving'`, `'declining'`). |
| `quality_flags` | Array/JSON | No | Structured flags: e.g. `["COORDINATE_INVERTED_CORRECTED"]`, `["LABEL_PROVENANCE_UNVERIFIED"]`, `["EXTREME_WATER_LEVEL_REVIEW_REQUIRED"]`. |
| `is_analytics_ready` | Boolean | No | Boolean flag indicating whether the observation passes empirical screening and sanity filters. |

---

## 4. Handling Unresolved Semantics & Data Quality

### A. Reference Datum Policy (Rule 6 in `instruction.md`)
Because official calibration documentation has not yet verified the exact physical datum:
- Values must **never** be inverted or mathematically adjusted in the database fact table.
- Both raw numeric values and explicit metadata flags (`water_level_reference = 'UNKNOWN'`, `reference_datum = 'UNKNOWN'`) must be preserved.
- When an analytical query requests `depth_bgl`, the system must:
  1. Return the value with an explicit disclosure of its unconfirmed datum.
  2. For Maharashtra records where negative values predominate, apply the documented transformation only in the presentation/analytics layer, never destructively in the database.

### B. Unverified Classification Labels Policy (Rule 9 in `instruction.md`)
- The unverified labels in `output1final.csv` through `outputfinal6.csv` (`status`, `trend`) must be isolated in `status_raw` and `trend_raw` and tagged with `LABEL_PROVENANCE_UNVERIFIED`.
- Analytical models, alerts, and dashboards must **never** consume `status_raw` or `trend_raw`.
- Platform status classifications will be computed dynamically from hydrogeologically validated algorithms in future milestones.

---

## 5. Architectural Readiness

This conceptual model accommodates:
1. Seamless queries across 30 years of national seasonal data for long-term climate trend detection.
2. High-speed indexing of 6-hourly telemetry for operational early warning.
3. Easy onboarding of new state telemetry feeds (Gujarat, Karnataka, Rajasthan, Punjab, etc.) as national DWLR expansion continues.
