# Comprehensive Data Quality & Forensics Findings

**Document Version:** 1.0  
**Milestone:** Milestone 2 (Data Forensics, Schema Verification & Canonical Data Model)  
**Date:** October 2026  
**Governing Standard:** [instruction.md](file:///d:/Projects%20ALL/DWLR_GRW_INDIA/instruction.md) (Rules 1, 2, 4, 5, 6, 9)

---

## 1. Executive Summary

During the data forensics phase of Milestone 2, **1,569,168 rows** of raw India-wide data and **218,791 rows** of Maharashtra telemetry data were audited using strictly read-only profiling tools.

This document catalogues every defect, anomaly, and provenance concern discovered across the raw source files. In accordance with project instructions, **none of these issues were silently repaired or deleted**. Every issue is detailed below with exact row counts, file locations, mathematical evidence, root-cause hypotheses, and non-destructive remediation proposals.

---

## 2. Issue Catalogue & Severity Matrix

| Issue ID | Category | Severity | Affected Files | Affected Rows | Description Summary |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DQ-01** | Geometry | **CRITICAL** | `output1final.csv` | **389,042** | Inverted coordinate headers (`lat` contains Longitude, `lng` contains Latitude). |
| **DQ-02** | Provenance | **CRITICAL** | All 6 India CSVs | **1,569,168** | Synthetic, uniform random classification labels (`status` and `trend`). |
| **DQ-03** | Schema | **HIGH** | `output4final.csv`, `outputfinal6.csv`, etc. | **480** | Geographic fields concatenated into `state` (Dadra & Nagar Haveli / Daman). |
| **DQ-04** | Schema | **MEDIUM** | `output2final.csv`, `output3final.csv`, `output4final.csv` | **429,653** | Phantom unnamed columns caused by trailing CSV delimiters. |
| **DQ-05** | Measurement| **HIGH** | `outputfinal6.csv` | **3** | Physically impossible extreme measurements in Assam (up to $53,943.6\,\text{m}$). |
| **DQ-06** | Hydrogeology| **HIGH** | All India & Maharashtra files | **1,787,959** | Incompatible sign conventions & unverified physical reference datums. |
| **DQ-07** | Formatting | **LOW** | All 6 India CSVs | **1,569,168** | Trailing whitespace in column headers (`'BLOCK '`, `'VILLAGE '`). |
| **DQ-08** | Incompleteness| **LOW** | Maharashtra CSV | **218,791** | Hydrographic columns (`Block`, `Village`, `River`) populated with `"-"`. |
| **DQ-09** | Missing Data| **LOW** | All India CSVs | **359 lat / 149 lng**| Null coordinates on a small fraction of monitoring records ($< 0.03\%$). |

---

## 3. Deep-Dive Forensic Analyses

### Issue DQ-01: Coordinate Inversion in `output1final.csv`
- **Affected File:** `NEW/data/raw/india/output1final.csv`
- **Affected Rows:** 389,042 rows (100% of rows with valid coordinates in the file).
- **Observed Evidence:**
  - Range of column `lat`: Minimum `68.53333`, Maximum `96.17737`.
  - Range of column `lng`: Minimum `8.08333`, Maximum `93.96577`.
  - In India, latitudes are strictly between $6.0^{\circ}\text{N}$ and $38.0^{\circ}\text{N}$, while longitudes are between $68.0^{\circ}\text{E}$ and $98.0^{\circ}\text{E}$.
  - Every single coordinate pair in this file has a value $> 50$ in `lat` and $< 40$ in `lng` (except for a few records in the Andaman islands where latitude is $<15$ and longitude is $>90$).
- **Root Cause:** Human error or automated ETL bug during the initial export of the January dataset, where column headers were mapped in reverse order.
- **Risk:** Plotting these coordinates without correction places Indian borewells into the Indian Ocean or Antarctica.
- **Remediation Proposal (Non-Destructive):**
  - Keep `output1final.csv` untouched in raw storage.
  - In the ingestion pipeline, apply a conditional schema mapping: for `output1final.csv`, map raw `lat` $\rightarrow$ canonical `longitude`, and raw `lng` $\rightarrow$ canonical `latitude`.
  - Tag all affected rows with `data_quality_flags: ["COORDINATE_INVERTED_IN_SOURCE"]`.

---

### Issue DQ-02: Synthetic / Mock Labels for `status` and `trend`
- **Affected Files:** All 6 India-wide CSV files.
- **Affected Rows:** 1,569,168 rows (100% of the dataset).
- **Observed Evidence:**
  1. *Exact Uniform Balance:*
     - `status`: ~25.0% `safe`, ~25.0% `semi-critical`, ~25.0% `critical`, ~25.0% `over-exploited`.
     - `trend`: ~33.3% `stable`, ~33.3% `declining`, ~33.3% `improving`.
  2. *Statistical Independence:*
     - One-way ANOVA $F$-test of `waterLevel` across `status` groups yielded $F = 0.531$, $p = 0.661$. The null hypothesis (means are identical) cannot be rejected.
     - One-way ANOVA $F$-test of `waterLevel` across `trend` groups yielded $F = 0.252$, $p = 0.777$.
     - Chi-square tests of independence with `state` ($p = 0.369$) and `year` ($p = 0.077$) confirm zero association.
- **Root Cause:** Prior to distribution, the original authors or data packagers generated uniform random synthetic labels (or assigned arbitrary mock values) to simulate a classification problem.
- **Risk:** Training any machine learning classifier on these labels constitutes learning pure random noise, producing deceptive performance metrics and scientifically invalid predictions.
- **Remediation Proposal (Non-Destructive):**
  - Retain verbatim strings in `status_raw` and `trend_raw` for provenance preservation.
  - Tag all rows with `data_quality_flags: ["PROVENANCE_LABEL_SYNTHETIC"]`.
  - Strictly prohibit these columns from entering any feature engineering, model training, or operational alert engines.

---

### Issue DQ-03: Concatenated Administrative Strings (Dadra & Nagar Haveli)
- **Affected Files:** `output1final.csv` (157), `output3final.csv` (4), `output4final.csv` (151), `outputfinal6.csv` (168).
- **Affected Rows:** 480 rows total.
- **Observed Evidence:**
  - Raw `state` value: `'The Dadra And Nagar Haveli And Daman And DiuDadra And Nagar Haveli Dadra Nagar Haveli Chinsda '`.
  - In these rows, raw `district`, `BLOCK `, and `VILLAGE ` are populated with `NaN`.
- **Root Cause:** A string concatenation error occurred during automated web-scraping or table parsing where tab/comma delimiters were stripped, fusing the state, district, block, and village into the first column.
- **Remediation Proposal (Non-Destructive):**
  - Implement a deterministic regex tokenization rule during ingestion:
    Match pattern: `^(The Dadra And Nagar Haveli And Daman And Diu)(Dadra And Nagar Haveli)(Dadra Nagar Haveli)(.*)$`
    Extract into standardized `state`, `district`, `subdistrict`, `village`.
  - Tag rows with `data_quality_flags: ["ADMIN_HIERARCHY_RECOVERED_FROM_CONCATENATION"]`.

---

### Issue DQ-04: Phantom Unnamed Columns
- **Affected Files:**
  - `output2final.csv`: 2 empty columns (`Unnamed: 4`, `Unnamed: 7`) $\times$ 112,737 rows = 225,474 null cells.
  - `output3final.csv`: 2 empty columns (`Unnamed: 4`, `Unnamed: 7`) $\times$ 120,021 rows = 240,042 null cells.
  - `output4final.csv`: 5 empty columns (`Unnamed: 4`, `Unnamed: 7`, `Unnamed: 13`, `Unnamed: 14`, `Unnamed: 15`) $\times$ 196,895 rows = 984,475 null cells.
- **Root Cause:** Extraneous delimiters (double commas `,,` or trailing commas) in the original export script.
- **Remediation Proposal:** Automatically drop unnamed null columns during schema validation.

---

### Issue DQ-05: Physically Impossible Extreme Measurements in Assam
- **Affected File:** `outputfinal6.csv`
- **Affected Rows:** 3 rows.
- **Observed Evidence:**
  - Row 264637: `Assam`, `Bongaigaon`, `Chalantapara`, Date: `01/11/2004`, `waterLevel`: **2,839.8 m**
  - Row 264684: `Assam`, `Dhubri`, `Panbari`, Date: `01/11/2004`, `waterLevel`: **53,943.6 m** (~54 km depth)
  - Row 264686: `Assam`, `Dhubri`, `Bagaribari`, Date: `01/11/2004`, `waterLevel`: **27,606.5 m**
- **Root Cause:** Manual data entry typo (e.g. typing `539436` instead of `5.39` or a misplaced decimal point), or an unparsed error code like `99999`.
- **Risk:** Distorts statewide and national statistics (mean water level in `outputfinal6.csv` rises from $6.8\,\text{m}$ to $7.06\,\text{m}$, and standard deviation balloons to $97.89\,\text{m}$).
- **Remediation Proposal (Non-Destructive):**
  - Do NOT delete the rows from raw storage.
  - Flag the records in the canonical layer:
    `data_quality_flags: ["PHYSICAL_OUTLIER_REJECTED"]`, `is_valid_for_analytics = FALSE`.
  - Exclude them from statistical aggregations and model baselines while preserving them for auditability.

---

### Issue DQ-06: Sign Convention & Datum Ambiguities
- **Observed Evidence:**
  - India-wide dataset: 100% non-negative ($0.0\,\text{m}$ to $299.3\,\text{m}$). Consistent with positive depth below ground level (m bgl).
  - Maharashtra telemetry dataset: 91.96% negative ($-1791.03\,\text{m}$ to $+213.318\,\text{m}$).
- **Root Cause:** Different agencies (CGWB vs. GSDA) and telemetry vendors utilize opposing sign conventions. In some telemetry systems, a rising sensor pressure or water head is recorded with negative depth coordinates.
- **Risk:** Merging the datasets directly would cause Maharashtra to appear as a massive artesian flood and India as deep drought.
- **Remediation Proposal:**
  - Store unmanipulated values in `water_level_raw`.
  - Explicitly assign `reference_datum` metadata:
    - India: `'UNKNOWN_PRESUMED_BGL'`
    - Maharashtra: `'UNKNOWN_MIXED_CONVENTION'`
  - Request authoritative calibration documentation before computing derived variables.

---

### Issue DQ-07: Trailing Whitespace in Column Headers
- **Affected Files:** All 6 India CSV files.
- **Affected Columns:** `'BLOCK '` (trailing space), `'VILLAGE '` (trailing space).
- **Remediation Proposal:** Automatically strip leading/trailing whitespace during DataFrame column loading.
