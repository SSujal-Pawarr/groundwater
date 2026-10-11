# Forecasting & Anomaly Detection Methodology

**Document Version:** 1.1 (Correction Pass)
**Milestone:** Milestone 5 (Forecasting & Anomaly Detection)  
**Date:** October 2026  
**Governing Standard:** `instruction.md`

---

## 1. Problem Definition

Forecasting is evaluated strictly chronologically. The goal is to determine if Machine Learning adds predictive value over simple baselines without future leakage.

### 1.1 India Forecasting Experiment
- **Dataset:** India periodic observations.
- **Problem Statement:** Given historical observations at an analytical site, predict the groundwater level at the next available seasonal observation for that site.
- **Horizon:** strictly the next chronological observation `target_next_value = shift(-1)`.
- **Target Variable:** `water_level_raw` (shifted backwards to align next observation with current features).
- **Temporal Splitting:** Data is chronologically ordered per site. The dataset is split strictly by `observation_date` (Train: ~earliest 70%, Val: next 15%, Test: latest 15%).
- **Eligibility Criteria:** Rather than using an arbitrary top-N/top-k/site-count sampling, scientific eligibility requires a site to have **$\ge$ 5 distinct years of observations**. 
  - **Justification:** This is strictly an **experimental eligibility rule** to guarantee enough historical data for valid chronological splitting (train/val/test) and computing historical seasonal statistics. It is **not** a physical or hydrological law.
  - **Distribution of distinct years per site:** mean 12.3, std 10.1, min 1, P25 3, median 10, P75 19, max 31.
  - **Total candidate sites:** 41,069.
  - **Eligible sites:** 29,185.
  - **Excluded sites:** 11,884.
  - **Total candidate observations:** 1,569,168.
  - **Eligible observations:** 1,528,900.
  - **Excluded observations:** 40,268.

### 1.2 Target Construction (India)
- **Target Variable:** `target_next_value = shift(-1)`. This represents the **next chronologically available observation** for the same site, NOT a fixed forecast horizon. 
- **Time Gap Distribution (Current to Target):** mean 122.9 days, median 92.0 days, P25 71.0 days, P75 122.0 days, max 10,833 days. 
- **Terminology:** This is a "next-observation prediction" (one-step-ahead experiment). It cannot be described as a fixed forecast horizon (e.g., "predicting 90 days out") because the actual time gap between observations varies.

### 1.2 Maharashtra Forecasting Experiment
- **Dataset:** Maharashtra continuous telemetry.
- **Problem Statement:** Given observations up to timestamp $T$, predict the groundwater level at the next telemetry ping.
- **Horizon / Cadence:** The models predict the **next available observation**.
  - **Timestamp-gap statistics between consecutive observations:** median 6.0 hours, P25 6.0 hours, P75 6.0 hours, P95 48.0 hours, max 2160.0 hours.
  - **Consecutive observations exactly 6 hours apart:** 85.11%.
  - Because 15% of gaps exceed 6 hours, we distinguish this as a "next-observation prediction", not strictly a "6-hour-ahead prediction".
- **Target Variable:** `water_level_raw` (shifted backwards).
- **Temporal Splitting:** Chronological split by `observation_timestamp` across all data.

---

## 2. Baselines Evaluated

Before ML models were trained, two transparent baselines were evaluated.

### 2.1 Persistence Baseline
- **Prediction:** $\hat{y}_{t} = y_{t-1}$ (the most recent available observation at the same site).
- **Evaluation Context:** For the Maharashtra 6-hourly telemetry, persistence is an extremely strong baseline due to high temporal autocorrelation. Surprisingly, for the India periodic dataset with eligible sites, persistence also proved highly performant across the 1.5M samples.

### 2.2 Seasonal Historical Baseline (India)
- **Prediction:** $\hat{y}_{t, s} = \frac{1}{| \{ y_{<t, s} \} |} \sum y_{<t, s}$ (the mean of all strictly prior years' observations for the same site and same season).
- **Leakage Prevention:** For predicting year $Y$, only observations strictly $<Y$ are used. Implemented via a highly vectorized `cumsum() - current_value` formulation sorted chronologically to guarantee zero leakage.

---

## 3. ML Models Evaluated

- **Model Architecture:** Histogram-based Gradient Boosting Regressor (`HistGradientBoostingRegressor`) and simple `LinearRegression`.
- **Features (India):** Reusable features built in M4. Features used: current `water_level_raw`, `lag_1` (previous observation), and `observation_month`.
- **Features (Maharashtra):** Current `water_level_raw`, previous observation (`lag_1`), and `hour` of day.
- **Leakage Prevention:** No target encoding, rolling averages, or future information were leaked into the training features. Explicit unit tests confirm strict chronological validity.

---

## 4. Evaluation Metrics

All models are evaluated on the held-out chronological test set (approx 225k rows for India, 32k for Maharashtra) using standard regression metrics:
- **MAE:** Mean Absolute Error
- **RMSE:** Root Mean Squared Error
- **R²:** Coefficient of Determination
- **MedAE:** Median Absolute Error

---

## 5. Anomaly Detection

Statistical anomalies are computed separately from physical data-quality flags.

### 5.1 India: Seasonal Z-Score
- **Methodology:** A z-score is computed per site and season using the historical mean and standard deviation: $z = (x - \mu_{site, season}) / \sigma_{site, season}$.
- **Important Classification:** Because the mean and standard deviation currently utilize the complete historical dataset (future observations are leaked into the past), this is strictly **DESCRIPTIVE HISTORICAL ANOMALY ANALYSIS**. This is **not** causal real-time anomaly detection. It is not production-ready for real-time alerts.
- **Threshold:** $|z| > 3$ is flagged as a statistical anomaly.
- **Result:** Detected 9,180 anomalies (0.60%) on the eligible dataset.

### 5.2 Maharashtra: Robust Residual Anomaly Detection
- **Methodology:** Telemetry anomalies are detected by analyzing the residuals from the persistence baseline (i.e., step changes between readings). The Median Absolute Deviation (MAD) of residuals is calculated per station to generate a robust z-score.
- **Threshold:** $|robust\_z| > 5$ on the persistence residual is flagged as a statistical anomaly.
- **Result:** Detected 0 anomalies. The 6-hourly cadence is extremely smooth.

*Note: Raw observations are preserved. Statistical anomalies remain completely distinct from physical data-quality flags. Future operationalization will require building a **future production causal alerting** mechanism that isolates baseline distributions strictly from preceding timestamps.*

---

## 6. Weather & Uncertainty Deferral

- **Weather Data:** No weather data was included in this milestone. Without authoritative, temporally and spatially aligned weather data, inserting synthetic or generalized weather features would violate Rule 1.
- **Uncertainty Estimation:** Point forecasts were generated. Statistically rigorous prediction intervals are deferred until baseline deterministic models are fully vetted.

---

## 7. Conclusions & Limitations

1. **India Baseline Strength:** Evaluating the fully eligible scientific population (1.5M rows, 29k sites) revealed that the simple **Persistence Baseline is extremely robust** ($R^2 \approx 0.84$). Machine Learning models failed to beat Persistence on a 1-step horizon, often overfitting to the noise in disparate geographic locations.
2. **Maharashtra Baseline Strength:** The 6-hourly telemetry in Maharashtra yields a Persistence baseline with almost zero error ($R^2 \approx 0.995$). Short horizon ML (1-step/6 hours) cannot justify its complexity. A 24-hour/multi-day horizon should be evaluated in future operationalization milestones.
3. **Strict Validation:** Unit tests explicitly assert that target alignment ($T+1$) and chronological splitting strictly maintain data integrity. No "top-N" arbitrary subsets were used in final ML evaluation.
