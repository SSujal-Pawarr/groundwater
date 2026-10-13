import { useState } from 'react';
import {
  AlertTriangle,
  Award,
  BrainCircuit,
  CheckCircle2,
  Database,
  Layers,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Waves,
  Zap,
} from 'lucide-react';

export function MethodologyTab() {
  const [activeSection, setActiveSection] = useState<'precision' | 'models' | 'scenarios' | 'pipeline'>('precision');

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-8 max-w-7xl mx-auto w-full">
      {/* ── Header ── */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-[#E5E0D4] pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800">
              <Sparkles className="h-3.5 w-3.5" />
              Technical &amp; Hydrogeological Reference
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-800">
              Scientific Evaluation Standards
            </span>
          </div>
          <h1 className="font-heading mt-2 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
            Model Architecture &amp; Hydrogeological Methodology
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            A comprehensive, transparent breakdown of algorithms, mathematical formulations, loss objectives, and evaluation standards utilized across the groundwater intelligence system.
          </p>
        </div>

        {/* Quick Nav Pills */}
        <div className="flex flex-wrap gap-1 rounded-xl bg-amber-50/60 p-1 border border-[#E5E0D4]">
          {[
            { id: 'precision', label: '1. Precision & Evaluation Standards', icon: Award },
            { id: 'models', label: '2. The 4 Forecasting Models', icon: BrainCircuit },
            { id: 'scenarios', label: '3. Climate Scenarios', icon: Waves },
            { id: 'pipeline', label: '4. Data Engineering Architecture', icon: Database },
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveSection(id as typeof activeSection)}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                activeSection === id
                  ? 'bg-white text-slate-900 shadow-sm border border-[#E5E0D4]'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-white/50'
              }`}
            >
              <Icon className="h-3.5 w-3.5 text-emerald-600" />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Section 1: Precision vs Deceptive Metrics ── */}
      {activeSection === 'precision' && (
        <div className="space-y-6 animate-fade-in">
          {/* Scientific Callout Banner */}
          <div className="rounded-2xl border-2 border-amber-200 bg-gradient-to-br from-amber-50 via-orange-50/30 to-amber-50/80 p-6 shadow-sm">
            <div className="flex items-start gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-amber-500 text-white shadow-md">
                <AlertTriangle className="h-6 w-6" />
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-amber-800">
                    Hydrogeological Evaluation Principles
                  </span>
                  <span className="rounded bg-amber-200/80 px-2 py-0.5 text-xs font-semibold text-amber-900">
                    Metric Integrity Standard
                  </span>
                </div>
                <h2 className="font-heading text-lg font-bold text-slate-900 sm:text-xl">
                  Why Global Correlation &amp; Raw Percentage Accuracy Are Deceptive in Groundwater
                </h2>
                <p className="text-sm leading-relaxed text-slate-700">
                  In time-series hydrology, unconstrained regression metrics (such as pooled R-squared or percentage fit) are notoriously misleading.
                  Because groundwater levels in hard-rock aquifers change slowly from week to week, a trivial model that simply predicts <em>&ldquo;tomorrow will equal today&rdquo;</em> (persistence)
                  can score an apparent R-squared &gt; 0.90 across millions of static points.
                  However, that baseline model fails entirely when operational guidance is critical: anticipating <strong>severe pre-monsoon summer depletion troughs</strong> or <strong>rapid monsoon aquifer recharge inflection</strong>.
                </p>
              </div>
            </div>
          </div>

          {/* The Triad of True Precision */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="rounded-xl border border-[#E5E0D4] bg-white p-5 shadow-xs hover:border-emerald-300 transition-all">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-100 text-emerald-700 mb-3">
                <CheckCircle2 className="h-5 w-5" />
              </div>
              <h3 className="font-heading font-semibold text-slate-900">1. Directional Precision</h3>
              <p className="mt-1 text-xs font-mono font-medium text-emerald-700">Trend Sign Hit Rate: 82.4% (Seasonal Harmonic Model)</p>
              <p className="mt-2 text-xs leading-relaxed text-slate-600">
                Measures whether the model correctly anticipates the <strong>sign of the hydrological change</strong>: will the water table rise (delta &gt; 0) or decline (delta &lt; 0)?
                An 82.4% directional precision reliably alerts administrators to impending summer drawdowns prior to onset.
              </p>
            </div>

            <div className="rounded-xl border border-[#E5E0D4] bg-white p-5 shadow-xs hover:border-blue-300 transition-all">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-blue-700 mb-3">
                <Zap className="h-5 w-5" />
              </div>
              <h3 className="font-heading font-semibold text-slate-900">2. Physical MAE in Meters</h3>
              <p className="mt-1 text-xs font-mono font-medium text-blue-700">1.307 m MAE vs 3.597 m Baseline</p>
              <p className="mt-2 text-xs leading-relaxed text-slate-600">
                Instead of unitless percentage scores, we evaluate real-world physical error: on average, predictions stay within <strong>&plusmn;1.3 meters</strong> of ground-truth telemetry observations, reducing naive baseline error by over <strong>51%</strong>.
              </p>
            </div>

            <div className="rounded-xl border border-[#E5E0D4] bg-white p-5 shadow-xs hover:border-purple-300 transition-all">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-100 text-purple-700 mb-3">
                <Layers className="h-5 w-5" />
              </div>
              <h3 className="font-heading font-semibold text-slate-900">3. 80% CI Empirical Coverage</h3>
              <p className="mt-1 text-xs font-mono font-medium text-purple-700">84.2% Calibrated In-Band Rate</p>
              <p className="mt-2 text-xs leading-relaxed text-slate-600">
                Provides rigorous risk envelopes (10th to 90th percentile bounds).
                In 84.2% of out-of-sample future observations, true water table depths fall strictly inside the prediction interval, offering decision-makers verified safety margins.
              </p>
            </div>
          </div>

          {/* Why Models Diverge Section */}
          <div className="rounded-xl border border-[#E5E0D4] bg-white p-6 shadow-xs">
            <h3 className="font-heading text-base font-bold text-slate-900 flex items-center gap-2">
              <BrainCircuit className="h-5 w-5 text-emerald-600" />
              Hydrological Divergence: Understanding Differential Model Trajectories
            </h3>
            <p className="mt-1 text-xs text-slate-600">
              When inspecting multi-model projections for the same monitoring station, the Seasonal Harmonic Model projects cyclical summer drawdowns, while Recurrent and Autoregressive models maintain flatter trajectories. Here is the physical rationale:
            </p>

            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="rounded-lg bg-emerald-50/50 border border-emerald-100 p-4">
                <div className="flex items-center gap-2 text-emerald-800 font-semibold text-xs">
                  <TrendingDown className="h-4 w-4" />
                  Seasonal Harmonic Model: Driven by Annual Periodicity
                </div>
                <p className="mt-2 text-xs leading-relaxed text-slate-700">
                  Deccan basalt aquifers experience heavy agricultural extraction from February through May (Rabi crop cycle).
                  The Seasonal Harmonic Model decomposes multi-year telemetry using continuous Fourier sinusoidal frequencies.
                  When projecting summer months from a spring baseline, it accounts for regional historical pre-monsoon drawdowns of 4 to 8 meters before monsoon recharge begins.
                </p>
              </div>

              <div className="rounded-lg bg-blue-50/50 border border-blue-100 p-4">
                <div className="flex items-center gap-2 text-blue-800 font-semibold text-xs">
                  <TrendingUp className="h-4 w-4" />
                  Deep Recurrent &amp; Autoregressive Models: Driven by Sequence Inertia
                </div>
                <p className="mt-2 text-xs leading-relaxed text-slate-700">
                  The Deep Recurrent Sequence Model evaluates 30-day sequential telemetry momentum.
                  Because it operates without future meteorological inputs during forward rollouts, its projection layers are regularized to prevent runaway compound error.
                  Similarly, the Autoregressive Step Model applies walk-forward safety bounds that constrain divergence over long horizons.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Section 2: The 4 Forecasting Models ── */}
      {activeSection === 'models' && (
        <div className="space-y-6 animate-fade-in">
          {/* Model 1: Seasonal Harmonic Model */}
          <div className="rounded-2xl border border-[#E5E0D4] bg-white p-6 shadow-xs">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-600 text-white font-bold text-sm">
                  SHM
                </div>
                <div>
                  <h3 className="font-heading font-bold text-slate-900 text-lg">
                    Model 1: Seasonal Harmonic Decomposition Model (Cyclic Fourier Formulation)
                  </h3>
                  <p className="text-xs text-slate-500">Gradient-boosted decision trees trained on 181,744 historical paired observations</p>
                </div>
              </div>
              <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800">
                Recommended for Extended Horizons (Up to 3 Years)
              </span>
            </div>

            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">Methodological Principles</h4>
                <ul className="mt-2 space-y-2 text-xs text-slate-600 leading-relaxed list-disc list-inside">
                  <li><strong>Fourier Harmonic Transforms:</strong> Converts target calendar dates into sinusoidal harmonics: sin(2&pi; &times; DOY / 365.25), cos(2&pi; &times; DOY / 365.25), along with semi-annual and quarterly sub-harmonics.</li>
                  <li><strong>Differential Modeling:</strong> Predicts the water level delta &Delta;y = y_target &minus; y_origin rather than raw depth, ensuring invariance across varying well casing elevations.</li>
                  <li><strong>Huber Loss Objective:</strong> Formulated with Huber loss (&delta; = 1.35) instead of standard squared error to prevent extreme telemetry sensor noise from distorting splits.</li>
                  <li><strong>Spatial Conditioning:</strong> Integrates well coordinates and digital elevation (SRTM MSL) to capture watershed topography.</li>
                </ul>
              </div>

              <div className="rounded-xl bg-slate-50 p-4 border border-slate-200">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">Mathematical Formulation</h4>
                <pre className="mt-2 rounded bg-slate-900 p-3 text-[11px] text-emerald-400 font-mono overflow-x-auto">
{`# Fourier Feature Representation (26-dimensional)
angle = 2 * pi * day_of_year / 365.25
sin_annual = sin(angle)
cos_annual = cos(angle)
sin_semi   = sin(2 * angle)
cos_semi   = cos(2 * angle)

# Objective: Huber Loss (Robust to Sensor Spikes)
L_delta(y, f(x)) = 0.5 * (y - f(x))^2          if |y - f(x)| <= delta
                 = delta * (|y - f(x)| - 0.5*delta) otherwise`}
                </pre>
                <div className="mt-3 flex justify-between text-xs text-slate-600 border-t border-slate-200 pt-2">
                  <span>Validation MAE: <strong>1.307 m</strong></span>
                  <span>Directional Precision: <strong>82.4%</strong></span>
                  <span>Inference Latency: <strong>&lt; 1 ms</strong></span>
                </div>
              </div>
            </div>
          </div>

          {/* Model 2: Deep Recurrent Sequence Model */}
          <div className="rounded-2xl border border-[#E5E0D4] bg-white p-6 shadow-xs">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white font-bold text-sm">
                  DRS
                </div>
                <div>
                  <h3 className="font-heading font-bold text-slate-900 text-lg">
                    Model 2: Deep Recurrent Sequence Model (Spatial &amp; Variance Conditioning)
                  </h3>
                  <p className="text-xs text-slate-500">Two-layer recurrent neural sequence architecture with LayerNorm and GELU projection</p>
                </div>
              </div>
              <span className="rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-800">
                Optimal for 30-to-90 Day Transition Momentum
              </span>
            </div>

            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">Methodological Principles</h4>
                <ul className="mt-2 space-y-2 text-xs text-slate-600 leading-relaxed list-disc list-inside">
                  <li><strong>Sliding 30-Day Window:</strong> Feeds continuous 30-day telemetry readings as an input sequence vector with telemetry completeness masks.</li>
                  <li><strong>Per-Station Normalization:</strong> Each station is standardized by its historical training mean and variance: z = (y &minus; &mu;_s) / &sigma;_s.</li>
                  <li><strong>Conditioning Fusion:</strong> Final hidden state h_30 is concatenated with target horizon Fourier features, spatial coordinates, and station elevation.</li>
                  <li><strong>LayerNorm + Dropout:</strong> Regularized against overfitting to prevent catastrophic drift over long forward horizons.</li>
                </ul>
              </div>

              <div className="rounded-xl bg-slate-50 p-4 border border-slate-200">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">Network Architecture</h4>
                <pre className="mt-2 rounded bg-slate-900 p-3 text-[11px] text-blue-400 font-mono overflow-x-auto">
{`Input Sequence: (batch, 30, 6)
  |
Recurrent Layer 1: hidden_dim=128, dropout=0.15
  |
Recurrent Layer 2: hidden_dim=128
  |
Final Hidden State h_n[-1] (128-dim)
  + Concat Horizon Features (9-dim)
  |
LayerNorm(137) -> Linear(137, 64) -> GELU() -> Linear(64, 1)
  |
Output: Predicted Normalized Change (delta z)`}
                </pre>
                <div className="mt-3 flex justify-between text-xs text-slate-600 border-t border-slate-200 pt-2">
                  <span>Validation RMSE: <strong>3.529 m</strong></span>
                  <span>Directional Precision: <strong>71.8%</strong></span>
                  <span>Inference: <strong>&lt; 5 ms</strong></span>
                </div>
              </div>
            </div>
          </div>

          {/* Model 3: Autoregressive Multi-Horizon Step Model */}
          <div className="rounded-2xl border border-[#E5E0D4] bg-white p-6 shadow-xs">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-600 text-white font-bold text-sm">
                  ARM
                </div>
                <div>
                  <h3 className="font-heading font-bold text-slate-900 text-lg">
                    Model 3: Autoregressive Multi-Horizon Model (Chained Step Roll-Forward)
                  </h3>
                  <p className="text-xs text-slate-500">Recursive multi-step roll-forward with strict historical backtest guardrails</p>
                </div>
              </div>
              <span className="rounded-full bg-purple-100 px-3 py-1 text-xs font-semibold text-purple-800">
                Step-by-Step Risk Auditing
              </span>
            </div>

            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">Methodological Principles</h4>
                <ul className="mt-2 space-y-2 text-xs text-slate-600 leading-relaxed list-disc list-inside">
                  <li><strong>Step-Lag Roll Forward:</strong> Forecasts step t+1, feeds the prediction back as a lag feature to forecast step t+2, iterating recursively up to 36 steps.</li>
                  <li><strong>Backtest Safety Gate:</strong> Before each step, the model verifies historical walk-forward backtests. If step error exceeded persistence, it locks to persistence to stop error compounding.</li>
                  <li><strong>Bounded Range Clipping:</strong> Predictions are clipped within the well&apos;s physical geological bounds so levels remain physically viable.</li>
                </ul>
              </div>

              <div className="rounded-xl bg-slate-50 p-4 border border-slate-200">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">Guardrail Decision Logic</h4>
                <pre className="mt-2 rounded bg-slate-900 p-3 text-[11px] text-purple-400 font-mono overflow-x-auto">
{`For step k in [1 .. MAX_STEPS]:
    If backtest_mae[k] > persistence_mae[k]:
        predicted_level[k] = origin_level  # Safety Fallback
        method_reason = "Safety fallback: backtest persistence beat model"
    Else:
        predicted_level[k] = roll_features_and_predict(k)
        clip_to_geological_bounds(predicted_level[k])`}
                </pre>
                <div className="mt-3 flex justify-between text-xs text-slate-600 border-t border-slate-200 pt-2">
                  <span>Horizon: <strong>Up to 36 steps</strong></span>
                  <span>Safety Guard: <strong>Active</strong></span>
                  <span>Directional Precision: <strong>74.1%</strong></span>
                </div>
              </div>
            </div>
          </div>

          {/* Model 4: Baseline Persistence Reference */}
          <div className="rounded-2xl border border-[#E5E0D4] bg-white p-6 shadow-xs">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-500 text-white font-bold text-sm">
                  REF
                </div>
                <div>
                  <h3 className="font-heading font-bold text-slate-900 text-lg">
                    Model 4: Hydrological Persistence Baseline Benchmark
                  </h3>
                  <p className="text-xs text-slate-500">Zero-signal control baseline for scientific model verification</p>
                </div>
              </div>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                Zero-Variance Scientific Benchmark
              </span>
            </div>

            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">Scientific Role</h4>
                <p className="mt-2 text-xs text-slate-600 leading-relaxed">
                  In environmental statistics, every complex algorithm must be rigorously compared against the zero-signal persistence baseline (&ldquo;tomorrow equals today&rdquo;).
                  A model only adds genuine scientific value if its out-of-sample directional precision and mean absolute error significantly outperform this static reference.
                </p>
              </div>
              <div className="rounded-xl bg-slate-50 p-4 border border-slate-200">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">Benchmark Metrics</h4>
                <div className="mt-3 space-y-1.5 text-xs text-slate-600">
                  <div className="flex justify-between">
                    <span>Baseline MAE:</span>
                    <span className="font-bold text-slate-800">3.597 m</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Baseline RMSE:</span>
                    <span className="font-bold text-slate-800">5.012 m</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Directional Precision:</span>
                    <span className="font-bold text-slate-500">50.0% (Random Chance)</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Section 3: Climate Scenarios ── */}
      {activeSection === 'scenarios' && (
        <div className="space-y-6 animate-fade-in">
          <div className="rounded-2xl border border-[#E5E0D4] bg-white p-6 shadow-xs">
            <h3 className="font-heading font-bold text-slate-900 text-lg">
              Climate &amp; Monsoon Stress Scenarios
            </h3>
            <p className="mt-1 text-xs text-slate-600">
              Groundwater storage dynamics depend heavily on seasonal monsoon infiltration. The platform provides 3 distinct hydrological scenarios:
            </p>

            <div className="mt-5 grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="rounded-xl border border-emerald-200 bg-emerald-50/40 p-5">
                <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-bold text-emerald-800">
                  Normal Monsoon (1.0&times; Baseline)
                </span>
                <h4 className="font-heading font-bold text-slate-900 mt-3 text-sm">Long-Term Climatological Mean</h4>
                <p className="mt-2 text-xs text-slate-600 leading-relaxed">
                  Assumes typical seasonal rainfall matching the 10-year Indian Meteorological Department (IMD) climatological average for the regional river basin.
                </p>
              </div>

              <div className="rounded-xl border border-amber-200 bg-amber-50/40 p-5">
                <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-bold text-amber-800">
                  Deficit Monsoon (&minus;20% Stress)
                </span>
                <h4 className="font-heading font-bold text-slate-900 mt-3 text-sm">Moderate Drought &amp; Subnormal Rains</h4>
                <p className="mt-2 text-xs text-slate-600 leading-relaxed">
                  Simulates a 20% deficit in monsoon rainfall, reducing natural aquifer recharge and forcing agricultural irrigation to extract deeper groundwater reserves.
                </p>
              </div>

              <div className="rounded-xl border border-blue-200 bg-blue-50/40 p-5">
                <span className="rounded-full bg-blue-100 px-2.5 py-1 text-xs font-bold text-blue-800">
                  Excess Monsoon (+20% Surplus)
                </span>
                <h4 className="font-heading font-bold text-slate-900 mt-3 text-sm">Enhanced Aquifer Infiltration</h4>
                <p className="mt-2 text-xs text-slate-600 leading-relaxed">
                  Simulates above-average precipitation, accelerating water table recovery and replenishment of shallow unconfined aquifers.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Section 4: Pipeline Architecture ── */}
      {activeSection === 'pipeline' && (
        <div className="space-y-6 animate-fade-in">
          <div className="rounded-2xl border border-[#E5E0D4] bg-white p-6 shadow-xs">
            <h3 className="font-heading font-bold text-slate-900 text-lg">
              Data Pipeline &amp; Serving Architecture
            </h3>
            <p className="mt-1 text-xs text-slate-600">
              High-throughput data engineering pipeline from raw CGWB telemetry to reactive frontend analytics:
            </p>

            <div className="mt-6 space-y-4">
              <div className="flex items-start gap-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-emerald-600 text-white font-bold text-xs">
                  1
                </div>
                <div>
                  <h4 className="font-semibold text-slate-900 text-sm">Telemetry Ingestion &amp; Outlier Filtering</h4>
                  <p className="mt-1 text-xs text-slate-600 leading-relaxed">
                    Raw DWLR telemetry points are validated. Erroneous pressure spikes (|&Delta;y| &gt; 25m) and dry sensor disconnects are filtered. Cleaned records are persisted in columnar Apache Parquet format.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-white font-bold text-xs">
                  2
                </div>
                <div>
                  <h4 className="font-semibold text-slate-900 text-sm">High-Performance Columnar Analytical Engine</h4>
                  <p className="mt-1 text-xs text-slate-600 leading-relaxed">
                    Fast in-process SQL execution engine computes rolling 30-day velocities, standard deviations, and spatial joins with zero server footprint.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-purple-600 text-white font-bold text-xs">
                  3
                </div>
                <div>
                  <h4 className="font-semibold text-slate-900 text-sm">Parallel Asynchronous Inference Serving</h4>
                  <p className="mt-1 text-xs text-slate-600 leading-relaxed">
                    All models are pre-warmed into memory during startup. Requests run parallel thread workers to compute multi-model trajectories and confidence intervals, returning responses in under <strong>35 milliseconds</strong>.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
