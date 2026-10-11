# M8.2-C Experiment Results: Weather-Enhanced ML Forecasting

## 1. Dataset Version & Split Methodology
- **Source Artifact:** `data/features/maharashtra/maharashtra_weather_ml_ready.parquet`
- **Total ML-Ready Observations:** 210,468 rows (after removing conflicting duplicates and nulls).
- **Split Methodology:** Strict Target-Isolated Chronological Split
  - Cutoffs were dynamically calculated at the 70th and 85th percentiles of `observation_timestamp_utc`.
  - **T_train:** `2026-04-05 06:30:00`
  - **T_val:** `2026-04-27 06:30:00`
  - A strict boundary enforcement was applied to ensure `target_timestamp_utc` did not cross into a future dataset partition. 1,752 boundary-crossing rows were safely discarded to guarantee absolutely zero temporal leakage.
- **Data Populations:**
  - **Train:** 147,029
  - **Validation:** 30,408
  - **Test:** 31,279

## 2. Model Configurations
- **Model A (Persistence Baseline):** Predicts `y_pred = water_level_raw` of the current observation.
- **Model B (Groundwater-Only Baseline - Exact M5 Match):** `HistGradientBoostingRegressor` using features: `water_level_raw`, `lag_1` (the chronologically previous valid observation), and `hour`.
- **Model C (Groundwater + Weather):** `HistGradientBoostingRegressor` using Model B features + all 14 cumulative and temporal weather features (Precipitation, ET0, Temperature, Humidity).

## 3. Corrected Validation-Based Weather Ablation
*Note: The original experiment mistakenly selected the best weather configuration using the Test set. This has been corrected. The configurations are now strictly evaluated on the untouched Validation set to prevent leakage.*

Ablation study (evaluated on **Validation** set MAE):
- **GW Only:** 5.138m
- **GW + Precipitation:** 4.395m
- **GW + Precipitation + ET0:** 3.130m
- **GW + All (incl. Temp/Humidity):** 3.853m

**Selection:** GW + Precipitation + ET0 was identified as the optimal ML configuration based purely on validation performance. Temperature and Humidity degraded performance, indicating they introduced noise/overfitting.

## 4. Final Lock: Untouched Test Set Results
The optimal ML configuration (GW + Precip + ET0) and the Persistence baseline were evaluated **exactly once** on the Test Set.

| Model | MAE (m) | MedAE (m) | RMSE (m) | R² |
|---|---|---|---|---|
| **Persistence** | 0.348 | 0.020 | 4.25 | 0.997 |
| **Best ML (GW+Precip+ET0)** | 3.863 | 0.098 | 74.75 | 0.084 |

## 5. Final Horizon-Wise Results (Test Set)

### Horizon <= 6h (N = 28,114)
| Model | MAE (m) | MedAE (m) | RMSE (m) | R² |
|---|---|---|---|---|
| **Persistence** | 0.322 | 0.020 | 4.40 | 0.997 |
| **Best ML Model** | 3.893 | 0.096 | 75.36 | 0.083 |

### Horizon >6h to <= 24h (N = 1,239)
| Model | MAE (m) | MedAE (m) | RMSE (m) | R² |
|---|---|---|---|---|
| **Persistence** | 0.374 | 0.030 | 1.82 | 0.999 |
| **Best ML Model** | 3.458 | 0.095 | 70.05 | 0.080 |

### Horizon >24h to <= 48h (N = 194)
| Model | MAE (m) | MedAE (m) | RMSE (m) | R² |
|---|---|---|---|---|
| **Persistence** | 0.356 | 0.040 | 1.46 | 0.989 |
| **Best ML Model** | 0.481 | 0.088 | 1.51 | 0.988 |

### Horizon > 48h (N = 1,732)
| Model | MAE (m) | MedAE (m) | RMSE (m) | R² |
|---|---|---|---|---|
| **Persistence** | 0.763 | 0.105 | 2.96 | 0.998 |
| **Best ML Model** | 4.040 | 0.176 | 72.14 | 0.089 |

## 6. Extreme-Error Audit
The Best ML model showed a massive discrepancy between MAE (3.86m) and RMSE (74.75m). An extreme-error audit was conducted on the test set predictions:
- **Max Absolute Error:** 1,765.8 meters
- **Errors > 10m:** 370 cases (out of 31,279)
- **RMSE Contribution:** 
  - Full RMSE: 74.75m
  - RMSE excluding the 370 outlier cases (>10m error): **1.20m**

The ML model fundamentally failed to predict the extreme, mechanically faulty -1791m readings present in the raw data, resulting in squared errors that completely dominated the RMSE. In contrast, Persistence safely copies the anomalous reading forward, avoiding the catastrophic penalty. 

## 7. Persistence Dominance
- **Persistence vs GW-Only ML:** Persistence reduces overall MAE from 5.518m to 0.348m (a 93.7% improvement). 
- **Persistence vs Final Weather ML:** Persistence reduces overall MAE from 3.863m to 0.348m (a 91.0% improvement).
- **Horizon consistency:** Persistence utterly dominates at all horizons, remaining highly accurate (MAE 0.76m) even beyond 48 hours.

## 8. Final Scientific Interpretation
- **Does weather provide incremental value over groundwater alone?** Yes. Weather provides incremental predictive value relative to the tested groundwater-only ML model (dropping test MAE from 5.518m to 3.863m).
- **Does weather improve operational forecasting?** **No.** The current evidence does not justify replacing persistence with weather-enhanced ML for operational Maharashtra forecasting.
- **Scientific Conclusion:** Adding ERA5 weather features provides a measurable secondary signal. However, a naïve Persistence baseline achieves a highly accurate 0.34m MAE across the entire dataset, heavily outperforming the ML model. Furthermore, Persistence is natively robust to the mechanical anomalies (e.g. -1791m probe failures) that severely compromise the ML model's squared error metrics.

**Recommendation:** Do not deploy the weather-enhanced ML model. Rely on the existing M5 Persistence methodology for robust short-term forecasting.
