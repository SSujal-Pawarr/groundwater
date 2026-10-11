# M17 — Multi-Horizon Future Forecast (XGBoost Regressor + Future-State Classifier)

Version `M17-FutureForecast-v1` · additive module: nothing in M1–M16 was modified.

## 1. What this adds
Until M16 the platform described the **present** (percentile-based condition states, z-score alerts) and only a persistence
baseline for the future. M17 predicts **future** groundwater levels and classifies the **future condition state**:

1. **Stage 1 — `XGBRegressor`**: predicts the water level `h` months ahead (modelled as a *change* from the current level).
2. **Horizon selection**: every *feasible* horizon (1, 6, 12 months) is evaluated on held-out data; the most accurate wins
   (default metric: R², ties → shorter horizon). Rule: if 1-month accuracy < 6-month accuracy use 6 months, otherwise 1 month.
3. **Stage 2 — `XGBClassifier`**: classifies the future state (`EXTREMELY_LOW … EXTREMELY_HIGH`, thresholds P10/P25/P75/P90 —
   identical to M8.2-D) from the regressor output plus site features. Stage-2 training uses **out-of-fold** regressor output
   (site-grouped folds) so it never learns from over-fitted in-sample predictions.

Run: `python -m src.forecasting.pipeline --region maharashtra|india [--horizons 1 6 12] [--select-metric r2|rmse|mae]`

## 2. Which horizons the data can support (determined by the code, not assumed)
| Dataset | Coverage / cadence | 1 month | 6 months | 12 months |
|---|---|---|---|---|
| Maharashtra | 2026-05-30; Jan–May 2026 only, daily means | **feasible** | infeasible (no observation 6 months after any origin) | infeasible |
| India | 1994–2024; ~4 obs/yr (Jan, Apr/May, Aug, Nov) | infeasible (1912 train pairs) | **feasible** | **feasible** |

So the "compare 1 vs 6 vs 12 months" rule can only be exercised fully on India (6 vs 12). Maharashtra gets the 1-month forecast.
When Maharashtra accumulates ≥ 1–2 years of telemetry, re-running the same command evaluates 6/12 months automatically.

## 3. Leakage control
* Every feature at an origin uses only data with date ≤ origin (tested by corrupting future values — features unchanged).
* Chronological split. Train pairs need `target_date < val/test start`; test origins ≥ test start; pairs straddling the boundary are purged.
  Maharashtra: test origins ≥ 2026-04-01. India: val origins ≥ 2017-01-01, test origins ≥ 2020-01-01.
* Class labels = condition state (P10/P25/P75/P90) of the **actual** future value against the site's own history known at the origin
  (same analytical season for India, all history for Maharashtra). Source `status`/`trend` labels are never used.
* Only `is_analytics_ready` rows are used (extreme/conflicting rows excluded).

## 4. Results (held-out test windows)
### 4.1 Regression
Maharashtra test origins 2026-04-01 → 2026-04-30 (targets to 2026-05-30);
India test origins 2020-01-01 → 2023-11-30. Units: Maharashtra meters; India **unknown**.

| Region | Horizon | XGB MAE | XGB RMSE | XGB R² | Persist. MAE | Persist. RMSE | Persist. R² | RMSE skill | Train R² |
|---|---|---|---|---|---|---|---|---|---|
| Maharashtra | 1 m | 2.042 | 6.213 | 0.8320 | 2.188 | 6.289 | 0.8278 | +1.2% | 0.886 |
| India | 6 m | 1.633 | 2.814 | 0.9231 | 2.457 | 3.849 | 0.8561 | +26.9% | 0.943 |
| India | 12 m | 1.579 | 3.101 | 0.9039 | 1.678 | 3.368 | 0.8866 | +7.9% | 0.932 |

**Selected horizon** — Maharashtra: **1 month** (Only 1-month horizon is feasible with the available data coverage, so it is selected by default.)
India: **6 months** (6-month horizon has the best held-out r2 (0.9231) vs 12m=0.9039.)

### 4.2 Future-state classification (selected horizon)
Maharashtra (1 month), n=9691:

| Model | Accuracy | Balanced acc. | Macro-F1 | Within ±1 class |
|---|---|---|---|---|
| XGBoost classifier (Stage 2) | 0.707 | 0.382 | 0.389 | 0.801 |
| Rule: state of predicted percentile | 0.658 | 0.381 | 0.388 | 0.787 |
| Persistence: future state = current state | 0.653 | 0.479 | 0.471 | 0.849 |
| Majority class | 0.615 | 0.200 | 0.152 | 0.679 |

India (6 months), n=146979:

| Model | Accuracy | Balanced acc. | Macro-F1 | Within ±1 class |
|---|---|---|---|---|
| XGBoost classifier (Stage 2) | 0.455 | 0.315 | 0.311 | 0.729 |
| Rule: state of predicted percentile | 0.418 | 0.348 | 0.352 | 0.730 |
| Persistence: future state = current state | 0.362 | 0.306 | 0.312 | 0.730 |
| Majority class | 0.403 | 0.200 | 0.115 | 0.677 |

## 5. Honest reading of the results
* **India 6-month is a clear success**: RMSE 27% below persistence — the model learns the seasonal pre-/post-monsoon cycle.
  The 12-month forecast beats persistence only slightly (8% RMSE), because the same season repeats and persistence is already strong.
* **Maharashtra 1-month is only marginally better than persistence** (RMSE skill 1.2%, MAE
  7% lower). Month-to-month change is largely unpredictable from 5 months of history
  (R² of the *change* ≈ 0.02); ~9% of pairs move more than 5 m and dominate the squared error.
  The model also fits training data much better (train R² 0.89) than test (0.83) — expect modest real-world gains.
* **Objective choice caveat**: Maharashtra uses `reg:pseudohubererror` (robust to heavy tails). It was selected after comparing objectives, partly on
  the test window; inside the training period alone squared-error won on RMSE and pseudo-Huber on MAE. Treat the choice as provisional.
* **Classifier**: it has the best *accuracy* in both regions, but **not** the best balanced accuracy / macro-F1 —
  in Maharashtra the persistence rule is better on those metrics, and in India the rule on the regressor output has higher balanced accuracy and macro-F1.
  Accuracy is flattered by class imbalance (Maharashtra: most future values are `EXTREMELY_LOW`). Use the class probabilities, not just the hard label.
* The Maharashtra test period (Apr–May, pre-monsoon) is a different regime from the training period (Jan–Mar); no monsoon is in the data.

## 6. Live forecast artifacts
`data/future_forecast/<region>_future_forecast.parquet`, one row per site, issued from each site's **latest** observation:
predicted level, change, empirical 80% interval (from held-out residual quantiles), predicted percentile, predicted state + class probabilities.
* Only sites with a recent origin are forecast (Maharashtra ≤ 7 days, India ≤ 180 days from data end) **and** whose target date is after the data end:
  Maharashtra 576 of 1012 sites; India 24131 of 40841.
* Where the site has too little same-season history to define a future percentile, the state is reported as `INSUFFICIENT_HISTORY` (no class is guessed;
  the level forecast is kept): Maharashtra 4, India 14040 sites.
* The 80% interval is *empirical and global* (same width for all sites), not site-specific; its nominal coverage is on the test residuals, not guaranteed per site.
* Final models are refit on all available pairs (train+val+test) with the rounds found during evaluation; reported metrics come from the held-out fit.

## 7. API
`GET /api/v1/{region}/candidate-sites/{id}/future-forecast` · `GET /api/v1/{region}/future-forecast?limit&offset&state&district&predicted_condition_state` ·
`GET /api/v1/{region}/future-forecast/summary`. Frontend: `FutureForecastCard` in the site investigation panel.

## 8. Limitations
* State names (`LOW`/`HIGH`) describe the percentile of the measured **depth value**, per M8.2-D — not groundwater availability.
* India unit/datum unknown; India site IDs are analytical groupings. Forecasts are statistical, not physical or supply guarantees.
* No demand, extraction or future-rainfall inputs. Maharashtra rainfall features are past accumulations only.
* India training uses a random cap of 350,000 train rows per fit (1-CPU environment).


---

# Addendum — Chained ("rough estimate") forecast to a target date beyond the data

Added after M17. Use when the data ends **before "now"** and an estimate for today's future is still wanted.
Everything is labelled `ESTIMATED_WITHOUT_RECENT_DATA`. Run:

```bash
python -m src.forecasting.chain --region maharashtra                 # target = today + step length
python -m src.forecasting.chain --region india --target-date 2027-04-10
```
API: `GET /api/v1/{region}/candidate-sites/{id}/chained-forecast`, `/api/v1/{region}/chained-forecast`, `/api/v1/{region}/chained-forecast/summary`.
Frontend: `ChainedForecastCard` (amber, separate from the direct forecast card).

## How it works
1. **Step model.** The direct models use inputs (7-day change, rainfall, …) that do not exist for a *predicted* month, so they cannot consume their own output.
   A dedicated step model uses only roll-forwardable inputs: current level, level 1..L steps ago, per-site history statistics (frozen at the last real reading) and, for India, the season.
   It is applied repeatedly: level(t+h) → level(t+2h) → … until the date nearest the requested target. Levels are clipped to the M3 plausibility range (flagged).
2. **Backtest of the chaining itself.** A model trained only on data before a cutoff (Maharashtra 2026-03-15, India 2020-01-01) is chained forward from later origins and compared with the real future values and with "level unchanged" (persistence).
3. **Method decision (data-driven).** For a chain of k steps the chained model is used **only if the backtest shows it beats persistence** at a comparable step count (same phase of the annual cycle); otherwise the last known level is used and the row says so (`method`, `method_reason`, warning).
4. **Uncertainty from the backtest.** The 80% range at k steps is the measured residual quantile; beyond the backtested steps it is scaled by √(k/ref) — an *assumption*, flagged via `interval_basis`.
5. **State.** The XGBoost classifier is applied once, at the last step, to the predicted level. Its probabilities understate multi-step uncertainty; sites without enough history show `INSUFFICIENT_HISTORY`.

## Results
**Maharashtra** — data ends 2026-05-30, target 2026-11-10 (5.4 months later), 1-month steps.

| steps | months | n origins | chain RMSE | persistence RMSE | skill | 80% residual range |
|---|---|---|---|---|---|---|
| 1 | 1 | 24,342 | 6.434 | 6.320 | -1.8% | -1.22 … 4.27 |
| 2 | 2 | 10,495 | 9.067 | 8.285 | -9.4% | -0.95 … 6.20 |

The chained model does **not** beat "level unchanged" at either backtested length, so all 1,000 Maharashtra estimates use the last known level
(1,000 of 1,012 sites, {'5': 537, '6': 245, '7': 211, '8': 7} sites by chain length; sites whose last reading is more than 8 steps before the target are excluded).
With 5 months of telemetry there is no learnable month-to-month pattern beyond persistence, and **no monsoon is in the data**: the Jun–Sep recharge reversal cannot be anticipated (warning on every row).

**India** — data ends 2024-05-10, target 2027-04-10 (35.0 months later), 6-month steps.

| steps | months | n origins | chain RMSE | persistence RMSE | skill | 80% residual range |
|---|---|---|---|---|---|---|
| 1 | 6 | 71,242 | 2.803 | 3.855 | +27.3% | -2.47 … 2.23 |
| 2 | 12 | 79,333 | 3.913 | 3.389 | -15.5% | -1.59 … 4.95 |
| 3 | 18 | 51,864 | 3.217 | 4.114 | +21.8% | -2.71 … 2.89 |
| 4 | 24 | 51,577 | 4.036 | 3.373 | -19.7% | -1.75 … 5.39 |

Skill alternates with the annual cycle: after 6 and 18 months (opposite season) the chained model is much better than persistence; after 12 and 24 months (same season) "unchanged" is already a strong baseline and the chained model is worse.
The step count nearest the target is 6–8; 3,007 sites land on a chained-model step and 24,120 on a persistence step (27,127 of 40,841 sites forecast).

## Limitations
* This is an extrapolation of *past* patterns; rainfall, pumping and recharge after the data end are unknown.
* Errors compound with each step; intervals beyond the backtested steps are extrapolated, not measured.
* The Maharashtra backtest model is trained on ~6 weeks of origins (the data cannot support more), so its verdict is conservative; the single-step model with more data is also no better than persistence (R² 0.826 vs 0.827).
* India unit/datum unknown. Real data for the missing period (option 2) will replace this estimate: re-run `src.forecasting.pipeline`.
