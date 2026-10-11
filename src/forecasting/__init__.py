"""
Future (multi-horizon) groundwater forecasting.

Two-stage design:
  Stage 1  XGBoost *Regressor*  -> predicts the water level `h` months ahead.
  Stage 2  XGBoost *Classifier* -> classifies the predicted future condition state
                                   using the Stage-1 output.
A horizon-selection step compares the regression accuracy of every feasible
horizon (1, 6, 12 months) and keeps the most accurate one.

This package is additive: it only READS existing artifacts and WRITES to
data/future_forecast/, models/future_forecast/ and docs/future_forecast_results_*.json.
"""
FUTURE_FORECAST_VERSION = "M17-FutureForecast-v1"
