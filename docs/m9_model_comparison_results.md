# M9 Model Comparison Results

## 1. Introduction & Methodology
Milestone M9 evaluated four predictive models on the Maharashtra next-valid-observation forecasting task. The objective was to determine whether advanced machine learning (including a new XGBoost model) can outperform the naive Persistence baseline, utilizing the strictly isolated chronological test set (T_train: 2026-04-05, T_val: 2026-04-27).

**Evaluated Models:**
1. **Persistence:** Naive baseline predicting `y_pred = water_level_raw` (M8.3 production).
2. **HistGradientBoosting (GW Only):** Uses historical groundwater levels, lag features, and time (from M5).
3. **HistGradientBoosting (Weather ML):** Uses GW features + optimal ERA5 weather features (Precipitation + ET0) (from M8.2-C).
4. **XGBoost (New in M9):** Uses the exact same features as the Weather ML model (GW + Precip + ET0), with `n_estimators=100`, `max_depth=6`, `learning_rate=0.1`.

All evaluations used the pre-computed `maharashtra_weather_ml_ready.parquet` artifact (N=210,468 rows), retaining the exact Target-Isolated Chronological Split to prevent temporal leakage.

## 2. Overall Test Set Performance

The performance of the models was evaluated entirely on the unseen Test partition (N=31,272):

| Model | MAE (m) | RMSE (m) | R² | Median AE (m) |
|---|---|---|---|---|
| **Persistence (Baseline)** | **0.348** | **4.25** | **0.997** | **0.020** |
| **XGBoost (New M9 Model)** | 3.910 | 74.51 | 0.090 | 0.179 |
| **HistGradientBoosting (Weather ML)** | 3.969 | 73.49 | 0.114 | 0.098 |

*Note: The GW-only HistGradientBoosting model (from M5) previously scored an MAE of 5.518m.*

## 3. Horizon Analysis (Test Set)

### Horizon <= 6h (N = 28,107)
| Model | MAE (m) | RMSE (m) |
|---|---|---|
| **Persistence** | **0.322** | **4.40** |
| **XGBoost** | 3.943 | 75.14 |
| **HistGradientBoosting** | 3.998 | 74.05 |

### Horizon >6h to <= 24h (N = 1,239)
| Model | MAE (m) | RMSE (m) |
|---|---|---|
| **Persistence** | **0.374** | **1.82** |
| **XGBoost** | 3.491 | 69.39 |
| **HistGradientBoosting** | 3.542 | 68.81 |

### Horizon > 48h (N = 1,732)
| Model | MAE (m) | RMSE (m) |
|---|---|---|
| **Persistence** | **0.763** | **2.96** |
| **XGBoost** | 4.059 | 71.93 |
| **HistGradientBoosting** | 4.197 | 71.78 |

## 4. Extreme-Error Audit

The machine learning models exhibited severe RMSE inflation. An extreme-error audit was conducted on the new XGBoost model:
- **Maximum Absolute Error:** 1,737.48 meters
- **Errors > 10m:** 317 cases
- **RMSE (Excluding >10m errors):** 1.17 meters (vs 74.51m full RMSE)

**Extreme Error Context:** Both ML models exhibit very large errors on extreme observations present in the test set. These observations dominate RMSE. Persistence has a much lower official test error under the current evaluation setup.

## 5. Scientific Conclusion & Production Recommendation

**Does ML beat persistence?**
**No.** Both the existing HistGradientBoosting and the newly implemented XGBoost model are completely dominated by the Persistence baseline across all metrics (MAE, RMSE, Median AE) and all forecasting horizons. XGBoost showed marginally better MAE (3.91m) compared to HGB (3.97m), but both fall massively short of Persistence (0.35m MAE).

**Production Recommendation:**
- **Do not promote the XGBoost or HGB ML models to production.** 
- The XGBoost implementation has been retained in `src/models/m9_xgboost_experiment.py` as an explicit negative result for historical/auditing purposes.
- **Maintain Persistence** as the operational forecasting system for short-term predictions.

## 6. System Integrity
- No changes were made to existing data processing or splitting logic.
- The full test suite (`pytest tests/`) was executed with 106 tests passing successfully, confirming zero regressions to the production pipeline.
