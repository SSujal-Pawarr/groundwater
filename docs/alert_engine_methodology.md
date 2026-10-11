# Causal Early-Warning & Alert Engine Methodology (Milestone 6)

**Purpose**
The Milestone 6 alert engine converts reliable groundwater observations and causal statistical signals into explainable early-warning states. It produces **statistical early-warning signals** designed to answer whether an observation has changed sufficiently relative to what was known *prior to that observation*. 

**Important Clarifications**
1. **Statistical Observation Classification:** The instantaneous analytical severity of an observation's deviation.
2. **Causal Anomaly Detection:** The robust identification of a statistical anomaly using only historical data available strictly before the current timestamp.
3. **Alert State:** The instantaneous status (e.g., NORMAL, WATCH) assigned to an observation.
4. **Alert Event:** An operational state tracking consecutive classifications over time to suppress noise. Transitions follow deterministic escalation and cooldown rules.
5. **Data-Quality Event:** An explicit classification for records failing automated QA/QC, which suppresses statistical alert evaluation entirely.
6. **Physical/Hydrological Interpretation:** The engine does **not** establish official groundwater stress, depletion, drought, or regulatory status. It operates purely on statistical deviation and is not ready for real-time operation until infrastructure for data ingestion pipelines is operational. Explicitly: no current alert threshold represents an official groundwater regulatory or hydrological limit.

---

## 1. Quality Gating
Observations undergo strict quality gating before any statistical alert generation. If an observation fails the data-quality checks, it yields a `DATA_QUALITY_EVENT`.
- Any observation missing the `is_analytics_ready=True` flag is gated.
- Any observation possessing disqualifying flags (e.g., `EXTREME_WATER_LEVEL_REVIEW_REQUIRED`, `COORDINATE_OUT_OF_BOUNDS`, `EXACT_DUPLICATE`) is gated.
This ensures statistical anomaly evaluation is completely separated from erroneous data handling.

---

## 2. Dataset Separation & Causal Requirements
India and Maharashtra datasets represent distinct sampling mechanisms (periodic vs. telemetry) and require different baseline anomaly mechanisms. However, both enforce **strict causal integrity**:
- An observation at time $T$ must ONLY be evaluated against data strictly $< T$.
- Information from $T+1, T+2...$ is never leaked into the historical baseline.
- If insufficient historical observations exist, the engine returns an explicit `INSUFFICIENT_HISTORY` state instead of inventing a score.

---

## 3. Causal Anomaly Detection — India Periodic Data
**Algorithm:** Strictly Backward-Looking Seasonal Z-Score.
- The historical mean and standard deviation are calculated for the target site and target season using *only strictly prior years*.
- To avoid loop-based bottlenecks over 1.5M records, cumulative sums and cumulative counts shifted by one observation are used.
- **Requirement:** A minimum of 5 distinct historical years of data is required to calculate standard deviations safely.

**Severity Configuration (Configurable Z-Score thresholds):**
- **WATCH:** $|Z| \ge 2.0$
- **WARNING:** $|Z| \ge 3.0$
- **CRITICAL_STATISTICAL_DEVIATION:** $|Z| \ge 4.0$
- **NORMAL:** $|Z| < 2.0$

---

## 4. Causal Anomaly Detection — Maharashtra Telemetry
**Algorithm:** Normalized Causal Persistence Residual Deviation.
- Analyzes the absolute deviation between the current reading and the strictly previous reading at that station ($|x_T - x_{T-1}|$).
- This residual is then **normalized (Z-score)** using a rolling standard deviation of the previous residuals over a strictly backward-looking window (e.g., 120 observations / ~30 days). This establishes a robust causal baseline derived purely from actual station volatility, rather than arbitrary physical distance thresholds.
- Requires a minimum of 20 historical observations to establish standard deviation.

**Large-Gap Handling Policy:**
- **Sequence Continuity Policy:** Because 15% of the data has gaps greater than the expected 6-hour interval (with the P95 gap at 48 hours), gaps exceeding 36 hours (which captures up to the ~90th percentile of continuous gaps) will generate a `SEQUENCE_GAPPED` state.
- **Clarification:** This is an operational policy to prevent comparing telemetry separated by weeks, not a hydrological fact. It explicitly distinguishes the *expected telemetry cadence* (6 hours) from the *sequence continuity policy* (36 hours).

**Severity Configuration (Configurable Causal Z-Score):**
- **WATCH:** $|Z| \ge 2.0$
- **WARNING:** $|Z| \ge 3.0$
- **CRITICAL_STATISTICAL_DEVIATION:** $|Z| \ge 4.0$
- **NORMAL:** $|Z| < 2.0$

---

## 5. Alert Event State Machine (Persistence & Cooldown)
The engine applies a deterministic state machine to convert instantaneous statistical classifications into coherent operational Alert Events.
- **Instantaneous Pass-through:** Non-operational states (`DATA_QUALITY_EVENT`, `SEQUENCE_GAPPED`, `INSUFFICIENT_HISTORY`) mask the row but do not clear the underlying active state.
- **Escalation:** Escalates immediately to the highest severity observed.
- **Cooldown & Recovery:** An active elevated state (e.g. WARNING) requires a configurable number of consecutive NORMAL instantaneous classifications (e.g. 3) to formally recover and transition back to NORMAL. Repeated high-severity anomalies sustain the state but do not generate duplicate, redundant events.

---

## 6. Model / Forecast Integration
ML models (such as `HistGradientBoosting`) were found in Milestone 5 to underperform simple persistence and historical seasonal baselines when predicting the strictly next observation. Therefore, to prioritize reliability and scientific validity, the current alert engine does not utilize complex ML models. The engine correctly relies on causal persistence and causal historical seasonal variance.

---

## 7. Testing & Reproducibility
- Extensive unittests validate the complete removal of future leakage and deterministic state machine transitions.
- Adding a future observation does not alter any historical alerts.
- Raw data inputs remain immutably preserved, satisfying strict non-destructive constraints.
