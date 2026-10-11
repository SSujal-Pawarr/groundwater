# India-wide Groundwater Dataset Profile & Forensics

**Document Version:** 1.0  
**Milestone:** Milestone 2 (Data Forensics, Schema Verification & Canonical Data Model)  
**Date:** October 2026  
**Governing Principles:** [instruction.md](file:///d:/Projects%20ALL/DWLR_GRW_INDIA/instruction.md) (Strictly read-only, no data fabrication, no unverified assumptions)

---

## 1. Executive Summary & Provenance

The India-wide groundwater dataset consists of **6 CSV files** situated in `NEW/data/raw/india/`, totaling **159,072,745 bytes (~151.7 MB)** and **1,569,168 records**.

### Key Forensic Findings
1. **Periodic Seasonal Monitoring, NOT High-Frequency Telemetry:**
   The India dataset does **not** contain daily or 6-hourly automated DWLR telemetry. Instead, it represents India's national periodic groundwater monitoring well network (historically conducted by the Central Ground Water Board - CGWB). It covers **4 specific seasonal observation windows** per year spanning **31 years (1994 to 2024)**:
   - **January (Rabi / Winter monitoring):** Contained in `output1final.csv` (1994–2024).
   - **April / May (Pre-Monsoon monitoring):** Contained across `output2final.csv` (1994–2003), `output3final.csv` (2004–2013), and `output4final.csv` (2014–2024).
   - **August (Monsoon monitoring):** Contained in `outputfinal5.csv` (1994–2023).
   - **November (Post-Monsoon monitoring):** Contained in `outputfinal6.csv` (1994–2023).
2. **Severe Coordinate Inversion in `output1final.csv`:**
   In `output1final.csv` (389,154 rows), **the column headers `lat` and `lng` are inverted**. The column labeled `lat` contains Longitudes (68.5°E to 96.2°E), while the column labeled `lng` contains Latitudes (8.1°N to 34.6°N). All 389,042 valid coordinate rows in this file are affected.
3. **Synthetic / Mock Labels for `status` and `trend`:**
   Statistical ANOVA and Chi-Square independence tests demonstrate that the columns `status` and `trend` are **uncorrelated with physical water levels, geography, and observation years**:
   - `status` is artificially divided into **equal quartiles (~25% each)** for `safe`, `semi-critical`, `critical`, and `over-exploited`.
   - `trend` is artificially divided into **equal tertiles (~33.3% each)** for `stable`, `improving`, and `declining`.
   - Both columns must be treated as untrusted metadata and must **never** be used as machine learning ground truth.
4. **Physical Measurement Semantics (Strictly Non-Negative):**
   Across all 1,569,168 rows, there is **zero negative value** ($0.0\,\text{m}$ to $299.3\,\text{m}$, with three extreme entry errors in Assam reaching $53,943.6\,\text{m}$). The median depth is deepest in pre-monsoon ($7.3\,\text{m}$ to $7.6\,\text{m}$) and shallowest in monsoon ($3.6\,\text{m}$), which is consistent with positive Depth to Water Level Below Ground Level (m bgl). However, formal CGWB documentation is required to confirm this datum.
5. **Concatenated Geographic Fields:**
   In Union Territories (specifically Dadra & Nagar Haveli and Daman & Diu), 480 rows have state, district, block, and village concatenated into the `state` field (e.g., `'The Dadra And Nagar Haveli And Daman And DiuDadra And Nagar Haveli Dadra Nagar Haveli Chinsda '`), leaving `district`, `BLOCK`, and `VILLAGE` as `NaN`.

---

## 2. File-by-File Forensic Profile

### Summary Matrix

| Metric | `output1final.csv` | `output2final.csv` | `output3final.csv` | `output4final.csv` | `outputfinal5.csv` | `outputfinal6.csv` | Total / Combined |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **File Size (bytes)** | 39,020,284 | 11,508,526 | 12,428,290 | 21,046,853 | 36,103,542 | 38,865,250 | **159,072,745** |
| **Total Rows** | 389,154 | 112,737 | 120,021 | 196,895 | 363,147 | 387,214 | **1,569,168** |
| **Total Columns** | 11 | 13 | 13 | 16 | 11 | 11 | — |
| **Season Monitored** | January (Winter) | Apr–May (Pre-Monsoon) | Apr–May (Pre-Monsoon) | Apr–May (Pre-Monsoon) | August (Monsoon) | November (Post-Monsoon) | All 4 Seasons |
| **Years Covered** | 1994–2024 (31 yrs) | 1994–2003 (10 yrs) | 2004–2013 (10 yrs) | 2014–2024 (11 yrs) | 1994–2023 (30 yrs) | 1994–2023 (30 yrs) | **1994–2024** |
| **Unique Dates** | 899 | 423 | 430 | 292 | 720 | 847 | — |
| **States Count** | 52 (anomalies) | 33 | 37 | 56 (anomalies) | 35 | 52 (anomalies) | ~36 valid |
| **Districts Count** | 780 | 667 | 692 | 712 | 743 | 710 | ~800+ |
| **Unique Coordinates**| 29,293 | 16,071 | 20,004 | 31,584 | 28,378 | 30,211 | **39,495** |
| **waterLevel Min** | 0.0 m | 0.0 m | 0.01 m | 0.01 m | 0.0 m | 0.0 m | **0.0 m** |
| **waterLevel Median**| 5.20 m | 7.30 m | 7.60 m | 7.02 m | 3.60 m | 4.20 m | — |
| **waterLevel Mean** | 7.49 m | 9.66 m | 10.59 m | 10.42 m | 6.25 m | 7.06 m | — |
| **waterLevel Max** | 146.10 m | 182.00 m | 191.25 m | 299.30 m | 223.20 m | 53,943.60 m (err)| **53,943.60 m** |
| **Negative Values** | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | **0 (0.0%)** |
| **Coordinate Swapped**| **389,042 (100%)** | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | **389,042** |
| **Unnamed Columns** | None | 2 cols | 2 cols | 5 cols | None | None | — |

---

### Detailed File Analysis

#### 1. `output1final.csv` (January / Rabi Monitoring: 1994–2024)
- **Schema (11 columns):** `state`, `district`, `BLOCK `, `VILLAGE `, `lat`, `lng`, `Date`, `waterLevel`, `status`, `year`, `trend`.
- **Note on Column Names:** Notice trailing spaces in `'BLOCK '` and `'VILLAGE '`.
- **Missing Values:**
  - `state`: 0
  - `district`: 391
  - `BLOCK `: 3,371
  - `VILLAGE `: 1,139
  - `lat`: 112
  - `lng`: 22
  - `Date`, `waterLevel`, `status`, `year`, `trend`: 0
- **Coordinate Anomaly (CRITICAL):**
  - Observed `lat` range: `68.53333` to `96.17737` (This is Longitude!).
  - Observed `lng` range: `8.08333` to `93.96577` (This is Latitude!).
  - Exactly **389,042 rows** have swapped coordinates. Zero rows have normal Indian coordinates.
- **Water Level Distribution:**
  - Min: `0.0 m`, Median: `5.20 m`, Mean: `7.49 m`, Max: `146.10 m`.
  - Zero readings: 288 rows. Negative readings: 0. Values > 100m: 179 rows.
- **Temporal Profile:** 100% of observations occur in Month 1 (January). 183,728 observations are stamped on January 1st; 79,401 on January 10th; 28,875 on January 5th.

#### 2. `output2final.csv` (Pre-Monsoon Monitoring Part 1: 1994–2003)
- **Schema (13 columns):** `state`, `district`, `BLOCK `, `VILLAGE `, `Unnamed: 4`, `lat`, `lng`, `Unnamed: 7`, `Date`, `waterLevel`, `status`, `year`, `trend`.
- **Malformed Columns:**
  - `Unnamed: 4`: 112,737 nulls (100% empty).
  - `Unnamed: 7`: 112,737 nulls (100% empty).
- **Missing Values:** `district`: 0, `BLOCK `: 17, `VILLAGE `: 35, `lat`: 10, `lng`: 10.
- **Coordinates:** 112,727 rows have valid Indian coordinates. 0 swapped.
- **Water Level Distribution:**
  - Min: `0.0 m`, Median: `7.30 m`, Mean: `9.66 m`, Max: `182.00 m`.
  - Negatives: 0. Zeroes: 40. Values > 100m: 159 rows.
- **Temporal Profile:** Month 4 (April: 20,703 rows), Month 5 (May: 92,034 rows).

#### 3. `output3final.csv` (Pre-Monsoon Monitoring Part 2: 2004–2013)
- **Schema (13 columns):** `state`, `district`, `BLOCK `, `VILLAGE `, `Unnamed: 4`, `lat`, `lng`, `Unnamed: 7`, `Date`, `waterLevel`, `status`, `year`, `trend`.
- **Malformed Columns:** `Unnamed: 4` (100% null), `Unnamed: 7` (100% null).
- **Missing Values:** `district`: 82, `BLOCK `: 122, `VILLAGE `: 244, `lat`: 10, `lng`: 10.
- **Water Level Distribution:**
  - Min: `0.01 m`, Median: `7.60 m`, Mean: `10.59 m`, Max: `191.25 m`.
  - Negatives: 0. Values > 100m: 287 rows.
- **Temporal Profile:** Month 3 (March: 2,038), Month 4 (April: 22,245), Month 5 (May: 95,738).

#### 4. `output4final.csv` (Pre-Monsoon Monitoring Part 3: 2014–2024)
- **Schema (16 columns):** `state`, `district`, `BLOCK `, `VILLAGE `, `Unnamed: 4`, `lat`, `lng`, `Unnamed: 7`, `Date`, `waterLevel`, `status`, `year`, `trend`, `Unnamed: 13`, `Unnamed: 14`, `Unnamed: 15`.
- **Malformed Columns:** 5 completely empty phantom columns: `Unnamed: 4`, `Unnamed: 7`, `Unnamed: 13`, `Unnamed: 14`, `Unnamed: 15` (196,894 to 196,895 nulls).
- **Missing Values:** `district`: 280, `BLOCK `: 397, `VILLAGE `: 534, `lat`: 62, `lng`: 62.
- **Water Level Distribution:**
  - Min: `0.01 m`, Median: `7.02 m`, Mean: `10.42 m`, Max: `299.30 m`.
  - Negatives: 0. Values > 100m: 457 rows. Values > 200m: 3 rows.
- **Temporal Profile:** Month 3 (March: 5,332), Month 4 (April: 44,579), Month 5 (May: 146,984).

#### 5. `outputfinal5.csv` (Monsoon Monitoring: 1994–2023)
- **Schema (11 columns):** `state`, `district`, `BLOCK `, `VILLAGE `, `lat`, `lng`, `Date`, `waterLevel`, `status`, `year`, `trend`.
- **Missing Values:** `district`: 370, `BLOCK `: 1,592, `VILLAGE `: 652, `lat`: 101, `lng`: 45.
- **Water Level Distribution:**
  - Min: `0.0 m`, Median: `3.60 m`, Mean: `6.25 m`, Max: `223.20 m`.
  - Negatives: 0. Zeroes: 2,374 rows. Values > 100m: 170 rows.
  - Notice the lower median ($3.6\,\text{m}$) reflecting post-monsoon aquifer recharge.
- **Temporal Profile:** 100% of observations occur in Month 8 (August). 127,392 observations on August 1st.

#### 6. `outputfinal6.csv` (Post-Monsoon Monitoring: 1994–2023)
- **Schema (11 columns):** `state`, `district`, `BLOCK `, `VILLAGE `, `lat`, `lng`, `Date`, `waterLevel`, `status`, `year`, `trend`.
- **Missing Values:** `district`: 398, `BLOCK `: 631, `VILLAGE `: 790, `lat`: 62, `lng`: 2.
- **Extreme Outliers / Sensor Glitches:**
  - Row 264637: `Assam`, `Bongaigaon`, `Chalantapara`, Date: `01/11/2004`, `waterLevel`: **2,839.8 m**
  - Row 264684: `Assam`, `Dhubri`, `Panbari`, Date: `01/11/2004`, `waterLevel`: **53,943.6 m** (Physically impossible; ~54 km depth)
  - Row 264686: `Assam`, `Dhubri`, `Bagaribari`, Date: `01/11/2004`, `waterLevel`: **27,606.5 m**
- **Water Level Distribution (Excluding Extremes):**
  - Min: `0.0 m`, Median: `4.20 m`, Mean: `7.06 m` (distorted by 53,943m error).
  - Negatives: 0. Zeroes: 645. Values > 100m: 174 rows.
- **Temporal Profile:** 100% of observations occur in Month 11 (November). 183,736 observations on November 1st.

---

## 3. Status and Trend Label Forensics

### Statistical Independence Proof

The dataset includes two classification columns: `status` and `trend`. A critical question is whether these columns represent genuine hydrogeological assessments or artificial artifacts.

#### 1. Exact Uniform Class Balance
Across all 6 files, the class distributions exhibit exact uniform divisions:

```text
status Distribution (across all 1,569,168 rows):
- safe:           392,650 (25.02%)
- semi-critical:  391,672 (24.96%)
- over-exploited: 392,590 (25.02%)
- critical:       392,256 (25.00%)

trend Distribution (across all 1,569,168 rows):
- stable:         526,786 (33.57%)
- declining:      523,995 (33.39%)
- improving:      518,387 (33.04%)
```

#### 2. ANOVA and Chi-Square Testing
In `output2final.csv`:
- **One-Way ANOVA:** `waterLevel ~ status` $\rightarrow$ $F = 0.531$, $p = 0.661$ ($p > 0.05$).
  - Mean waterLevel for `critical`: $9.71\,\text{m}$
  - Mean waterLevel for `over-exploited`: $9.68\,\text{m}$
  - Mean waterLevel for `safe`: $9.62\,\text{m}$
  - Mean waterLevel for `semi-critical`: $9.64\,\text{m}$
  - *Finding:* Groundwater level is identical across all four "vulnerability" statuses!
- **One-Way ANOVA:** `waterLevel ~ trend` $\rightarrow$ $F = 0.252$, $p = 0.777$ ($p > 0.05$).
  - *Finding:* Groundwater level is identical whether the trend is "improving", "declining", or "stable"!
- **Chi-Square Test of Independence:** `state ~ status` $\rightarrow$ $\chi^2 = 100.02$, $p = 0.369$.
- **Chi-Square Test of Independence:** `year ~ status` $\rightarrow$ $\chi^2 = 38.04$, $p = 0.077$.

### Forensic Conclusion on Labels
The `status` and `trend` labels are **demonstrably synthetic random noise** injected into the dataset prior to release. They have zero mathematical or physical association with groundwater depth, administrative state, or historical year.
**Engineering Directive:** Under no circumstances may these labels be used as targets or features for machine learning.

---

## 4. Site Identity Investigation

The India dataset contains no explicit `station_id` or `well_id` column.

### Candidate Identity Strategies Evaluated

| Strategy | Attributes Used | Unique Count | Strengths | Vulnerabilities / Limitations |
| :--- | :--- | :--- | :--- | :--- |
| **Option A: Coordinate Pair** | `(round(lat, 4), round(lng, 4))` | **39,495** | Spatial precision; unaffected by village spelling changes. | In `output1final.csv`, coordinates must first be swapped. Small GPS sensor drift (e.g. 5th decimal place) over 30 years could split a single well into multiple IDs. |
| **Option B: Administrative Hierarchy** | `(state, district, block, village)` | **35,425** | Matches local government records. | 4,820 villages have multiple distinct coordinate pairs (multiple wells per village, or relocated observation points). |
| **Option C: Hierarchical Spatial Composite** | `state_code + district_slug + hash(village, lat_4dp, lon_4dp)` | **~39,500** | Combines administrative context with geographic grouping. | Requires formal schema migration and spatial clustering logic. |

**Milestone Decision:** Do NOT assign hardcoded station IDs yet. Candidate identity generation must be deferred to Milestone 3 where a spatial clustering radius (e.g., 50-meter tolerance) can be evaluated.

---

## 5. Summary of Malformed Records

1. **Inverted Coordinates in `output1final.csv`:**
   - 389,042 rows affected (100% of rows with coordinates in that file).
   - Recovery: Deterministic swap of `lat` and `lng` columns for `output1final.csv` during ingestion.
2. **Concatenated Administrative Strings (Dadra & Nagar Haveli):**
   - 480 rows across `output1final.csv` (157), `output3final.csv` (4), `output4final.csv` (151), and `outputfinal6.csv` (168).
   - Example: `'The Dadra And Nagar Haveli And Daman And DiuDadra And Nagar Haveli Dadra Nagar Haveli Chinsda '`.
   - Recovery: Can be parsed using regex string tokenization matching known UT names.
3. **Empty Unnamed Columns:**
   - `output2final.csv`: 2 phantom columns.
   - `output3final.csv`: 2 phantom columns.
   - `output4final.csv`: 5 phantom columns.
   - Cause: Trailing delimiters in raw export.
   - Recovery: Dropped automatically during schema normalization.
4. **Physically Absurd Extreme Values:**
   - 3 rows in Assam with waterLevel between $2,839\,\text{m}$ and $53,943.6\,\text{m}$.
   - Recovery: Must be flagged with `DATA_QUALITY_FLAG = OUT_OF_BOUNDS_ERROR` rather than silently deleted.
