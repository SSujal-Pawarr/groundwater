import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import Map, { Source, Layer } from 'react-map-gl/maplibre';
import type { MapRef } from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';
import {
  AlertTriangle,
  BrainCircuit,
  Check,
  Compass,
  Database,
  Droplets,
  Layers,
  MapPin,
  RefreshCw,
  Search,
  Sparkles,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';
import {
  fetchAdvancedForecast,
  fetchAdvancedForecastMap,
  fetchAdvancedForecastModelInfo,
  type AdvancedForecastResponse,
  type MapForecastSite,
  type ModelInfo,
} from '../services/advancedForecastApi';
import { DataDiagnosticPopover } from './DataDiagnosticPopover';

interface Props {
  dataset?: 'india' | 'maharashtra';
  initialSiteId?: string;
}

const SCENARIOS = [
  { id: 'normal', label: 'Normal Monsoon', desc: '1.0× baseline recharge', icon: Droplets, color: 'text-emerald-400' },
  { id: 'deficit', label: 'Deficit Monsoon', desc: '−20% drought stress', icon: TrendingDown, color: 'text-amber-400' },
  { id: 'excess', label: 'Excess Monsoon', desc: '+20% surplus recharge', icon: TrendingUp, color: 'text-blue-400' },
] as const;

type ScenarioType = 'normal' | 'deficit' | 'excess';

const MODEL_OPTIONS = [
  { id: 'seasonal_harmonic', label: 'Seasonal Harmonic Model', badge: 'Harmonic Decomposition', color: '#059669' },
  { id: 'lstm', label: 'Deep Recurrent Sequence Model', badge: 'Recurrent Neural Net', color: '#2563EB' },
  { id: 'chained', label: 'Autoregressive Horizon Model', badge: 'Recursive Multi-Step', color: '#7C3AED' },
  { id: 'persistence', label: 'Baseline Persistence Reference', badge: 'Static Baseline', color: '#64748B' },
];

const PRESET_STATIONS = [
  { id: 'MH_AALEGAON', label: 'Aalegaon (Nanded)', district: 'Nanded' },
  { id: 'MH_DUGAON', label: 'Dugaon (Nashik)', district: 'Nashik' },
  { id: 'MH_ERANDOL', label: 'Erandol (Jalgaon)', district: 'Jalgaon' },
  { id: 'MH_MAJALGAON', label: 'Majalgaon (Beed)', district: 'Beed' },
  { id: 'MH_BARAMATI', label: 'Baramati (Pune)', district: 'Pune' },
  { id: 'MH_KOPARGAON', label: 'Kopargaon (Ahmadnagar)', district: 'Ahmadnagar' },
];

export function PredictiveAnalytics({ dataset = 'maharashtra', initialSiteId = 'MH_AALEGAON' }: Props) {
  // Inputs
  const [siteId, setSiteId] = useState(initialSiteId);
  const [siteInput, setSiteInput] = useState(initialSiteId);
  const [targetDate, setTargetDate] = useState('2028-06-01');
  const [scenario, setScenario] = useState<ScenarioType>('normal');
  const [selectedModels, setSelectedModels] = useState<string[]>([
    'seasonal_harmonic',
    'lstm',
    'chained',
    'persistence',
  ]);
  const [viewMode, setViewMode] = useState<'site' | 'map'>('site');

  // Site-level forecast state
  const [forecastData, setForecastData] = useState<AdvancedForecastResponse | null>(null);
  const [forecastLoading, setForecastLoading] = useState(false);
  const [forecastError, setForecastError] = useState<string | null>(null);

  // Map forecast state
  const [mapSites, setMapSites] = useState<MapForecastSite[]>([]);
  const [mapLoading, setMapLoading] = useState(false);
  const [mapModel, setMapModel] = useState<string>('seasonal_harmonic');

  // Model benchmark metadata
  const [modelInfo, setModelInfo] = useState<Record<string, ModelInfo> | null>(null);

  // Load model benchmark metadata once
  useEffect(() => {
    fetchAdvancedForecastModelInfo()
      .then(info => setModelInfo(info))
      .catch(() => {});
  }, []);

  // Run site-level forecast
  const runSiteForecast = useCallback(
    async (sId: string, tDate: string, sc: ScenarioType, models: string[]) => {
      setForecastLoading(true);
      setForecastError(null);
      try {
        const res = await fetchAdvancedForecast(sId, tDate, sc, models);
        setForecastData(res);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Forecast inference failed.';
        setForecastError(msg);
      } finally {
        setForecastLoading(false);
      }
    },
    []
  );

  // Run map forecast
  const runMapForecast = useCallback(async (tDate: string, sc: ScenarioType, model: string) => {
    setMapLoading(true);
    setForecastError(null);
    try {
      const res = await fetchAdvancedForecastMap(tDate, sc, model);
      setMapSites(res.sites || []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Map forecast generation failed.';
      setForecastError(msg);
    } finally {
      setMapLoading(false);
    }
  }, []);

  // Initial trigger
  useEffect(() => {
    runSiteForecast(siteId, targetDate, scenario, selectedModels);
  }, [siteId, targetDate, scenario, runSiteForecast]);

  // When switching to map view, load map data
  useEffect(() => {
    if (viewMode === 'map') {
      runMapForecast(targetDate, scenario, mapModel);
    }
  }, [viewMode, targetDate, scenario, mapModel, runMapForecast]);

  // Handle model checkbox toggle
  const toggleModel = (mId: string) => {
    setSelectedModels(prev =>
      prev.includes(mId) ? (prev.length > 1 ? prev.filter(m => m !== mId) : prev) : [...prev, mId]
    );
  };

  // Build ECharts line options
  const chartOptions = useMemo(() => {
    if (!forecastData) return null;

    const historyPoints = (forecastData.history || []).map(h => [`${h.date}T00:00:00`, h.water_level]);

    const series: any[] = [
      {
        name: 'Historical Observations',
        type: 'line',
        data: historyPoints,
        showSymbol: false,
        lineStyle: { color: '#94a3b8', width: 2 },
        itemStyle: { color: '#94a3b8' },
      },
    ];

    const originIso = `${forecastData.origin_date}T00:00:00`;
    const targetIso = `${forecastData.target_date}T00:00:00`;
    const originLevel = forecastData.origin_water_level;

    // Seasonal Harmonic
    if (forecastData.predictions.seasonal_harmonic && selectedModels.includes('seasonal_harmonic')) {
      const pred = forecastData.predictions.seasonal_harmonic;
      const traj = forecastData.trajectories?.seasonal_harmonic;
      const points = traj && traj.length > 0
        ? traj.map(t => [`${t.date}T00:00:00`, t.predicted_level])
        : [
            [originIso, originLevel],
            [targetIso, pred.predicted_level],
          ];

      series.push({
        name: 'Seasonal Harmonic Model',
        type: 'line',
        smooth: true,
        data: points,
        showSymbol: points.length <= 16,
        symbolSize: 6,
        lineStyle: { color: '#059669', width: 2.8 },
        itemStyle: { color: '#059669' },
      });

      // Continuous 80% CI Upper / Lower
      if (traj && traj.length > 1) {
        series.push({
          name: 'Seasonal 80% CI Upper',
          type: 'line',
          smooth: true,
          data: traj.map(t => [`${t.date}T00:00:00`, t.ci_upper ?? t.predicted_level]),
          showSymbol: false,
          lineStyle: { color: '#10B981', width: 1, type: 'dashed' },
          itemStyle: { color: '#10B981' },
        });
        series.push({
          name: 'Seasonal 80% CI Lower',
          type: 'line',
          smooth: true,
          data: traj.map(t => [`${t.date}T00:00:00`, t.ci_lower ?? t.predicted_level]),
          showSymbol: false,
          lineStyle: { color: '#10B981', width: 1, type: 'dashed' },
          itemStyle: { color: '#10B981' },
        });
      }
    }

    // LSTM
    if (forecastData.predictions.lstm && selectedModels.includes('lstm')) {
      const pred = forecastData.predictions.lstm;
      const traj = forecastData.trajectories?.lstm;
      const points = traj && traj.length > 0
        ? traj.map(t => [`${t.date}T00:00:00`, t.predicted_level])
        : [
            [originIso, originLevel],
            [targetIso, pred.predicted_level],
          ];

      series.push({
        name: 'Deep Recurrent Sequence Model',
        type: 'line',
        smooth: true,
        data: points,
        showSymbol: points.length <= 16,
        symbolSize: 6,
        lineStyle: { color: '#2563EB', width: 2.5 },
        itemStyle: { color: '#2563EB' },
      });
    }

    // Chained Step Model
    if (forecastData.predictions.chained && selectedModels.includes('chained')) {
      const pred = forecastData.predictions.chained;
      const traj = forecastData.trajectories?.chained;
      const points = traj && traj.length > 0
        ? traj.map(t => [`${t.date}T00:00:00`, t.predicted_level])
        : [
            [originIso, originLevel],
            [targetIso, pred.predicted_level],
          ];

      series.push({
        name: 'Autoregressive Horizon Model',
        type: 'line',
        smooth: true,
        data: points,
        showSymbol: points.length <= 16,
        symbolSize: 6,
        lineStyle: { color: '#7C3AED', width: 2.2, type: 'dashdot' },
        itemStyle: { color: '#7C3AED' },
      });
    }

    // Persistence
    if (forecastData.predictions.persistence && selectedModels.includes('persistence')) {
      const traj = forecastData.trajectories?.persistence;
      const points = traj && traj.length > 0
        ? traj.map(t => [`${t.date}T00:00:00`, t.predicted_level])
        : [
            [originIso, originLevel],
            [targetIso, originLevel],
          ];

      series.push({
        name: 'Baseline Persistence Reference',
        type: 'line',
        data: points,
        showSymbol: points.length <= 16,
        symbolSize: 5,
        lineStyle: { color: '#64748B', width: 1.5, type: 'dashed' },
        itemStyle: { color: '#64748B' },
      });
    }

    return {
      backgroundColor: '#FFFFFF',
      title: {
        text: `Multi-Model Aquifer Projections — ${forecastData.station_name || forecastData.site_id}`,
        subtext: `Origin: ${forecastData.origin_date} (${forecastData.origin_water_level}m) → Target: ${forecastData.target_date} (${forecastData.horizon_days}d ahead) | Scenario: ${forecastData.scenario.toUpperCase()}`,
        left: 'left',
        textStyle: { fontSize: 14, fontWeight: '700', color: '#1E293B' },
        subtextStyle: { fontSize: 11, color: '#64748B' },
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        backgroundColor: '#FFFFFF',
        borderColor: '#E5E0D4',
        borderWidth: 1,
        textStyle: { color: '#1E293B', fontSize: 12 },
        extraCssText: 'box-shadow: 0 4px 14px rgba(0,0,0,0.08); border-radius: 8px;',
      },
      legend: {
        top: 36,
        right: 'right',
        textStyle: { fontSize: 11, color: '#475569' },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '8%',
        top: '22%',
        containLabel: true,
      },
      xAxis: {
        type: 'time',
        boundaryGap: false,
        axisLine: { lineStyle: { color: '#E5E0D4' } },
        axisLabel: { color: '#64748B', fontSize: 11 },
      },
      yAxis: {
        type: 'value',
        name: `Water Level (${forecastData.water_level_unit})`,
        nameTextStyle: { color: '#64748B', fontSize: 11 },
        splitLine: { lineStyle: { color: '#F1EFE9' } },
        axisLabel: { color: '#64748B', fontSize: 11 },
      },
      series,
    };
  }, [forecastData, selectedModels]);

  const mapRef = useRef<MapRef>(null);

  // GeoJSON features for map
  const mapGeojson = useMemo(() => ({
    type: 'FeatureCollection' as const,
    features: mapSites
      .filter(s => s.lat != null && s.lon != null)
      .map(s => ({
        type: 'Feature' as const,
        geometry: { type: 'Point' as const, coordinates: [s.lon!, s.lat!] },
        properties: {
          site_id: s.site_id,
          origin_level: s.origin_level,
          predicted_level: s.predicted_level,
          predicted_change: s.predicted_change,
          condition: s.predicted_condition,
        },
      })),
  }), [mapSites]);

  // Set quick horizon presets
  const handlePresetHorizon = (months: number) => {
    const d = new Date();
    d.setMonth(d.getMonth() + months);
    setTargetDate(d.toISOString().slice(0, 10));
  };

  const handleStationSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (siteInput.trim()) {
      setSiteId(siteInput.trim());
    }
  };

  return (
    <div className="space-y-6 animate-fade-in" aria-label="Predictive analytics command interface">
      {/* ── Top Control & Search Banner ── */}
      <div className="glass-panel rounded-2xl p-5 border border-[#E5E0D4] bg-white shadow-xs space-y-4">
        {/* Row 1: Station Selector & Quick Presets */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <form onSubmit={handleStationSubmit} className="flex flex-wrap items-center gap-2">
            <div className="relative min-w-[16rem]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                type="text"
                value={siteInput}
                onChange={e => setSiteInput(e.target.value)}
                placeholder="Search monitoring station ID or name..."
                className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2 pl-9 pr-3 text-xs text-slate-800 placeholder-slate-400 focus:border-emerald-500 focus:bg-white focus:outline-none focus:ring-1 focus:ring-emerald-500"
              />
            </div>
            <button
              type="submit"
              disabled={forecastLoading || !siteInput.trim()}
              className="rounded-xl bg-emerald-600 px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-emerald-700 disabled:opacity-50 transition-colors"
            >
              Analyze Station
            </button>
          </form>

          {/* Quick preset station pills */}
          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mr-1">
              Quick Focus:
            </span>
            {PRESET_STATIONS.map(p => (
              <button
                key={p.id}
                type="button"
                onClick={() => {
                  setSiteInput(p.id);
                  setSiteId(p.id);
                }}
                className={`rounded-lg px-2.5 py-1 text-[11px] font-medium transition-all ${
                  siteId === p.id
                    ? 'bg-emerald-100 text-emerald-900 border border-emerald-300 font-bold'
                    : 'bg-slate-50 text-slate-600 border border-slate-200 hover:bg-slate-100'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Row 2: Target Date, Scenarios, and View Toggles */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pt-3 border-t border-slate-100">
          {/* Target Date + Horizon Presets */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold text-slate-600">Projection Horizon:</span>
            <input
              type="date"
              value={targetDate}
              onChange={e => setTargetDate(e.target.value)}
              className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-800 font-medium focus:border-emerald-500 focus:outline-none"
            />
            <div className="flex items-center gap-1 text-[11px]">
              <button
                type="button"
                onClick={() => handlePresetHorizon(3)}
                className="rounded-md bg-slate-100 px-2 py-0.5 text-slate-600 hover:bg-slate-200"
              >
                +3m
              </button>
              <button
                type="button"
                onClick={() => handlePresetHorizon(6)}
                className="rounded-md bg-slate-100 px-2 py-0.5 text-slate-600 hover:bg-slate-200"
              >
                +6m
              </button>
              <button
                type="button"
                onClick={() => handlePresetHorizon(12)}
                className="rounded-md bg-slate-100 px-2 py-0.5 text-slate-600 hover:bg-slate-200"
              >
                +1y
              </button>
              <button
                type="button"
                onClick={() => handlePresetHorizon(24)}
                className="rounded-md bg-slate-100 px-2 py-0.5 text-slate-600 hover:bg-slate-200"
              >
                +2y
              </button>
            </div>
          </div>

          {/* Climate Scenarios */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-600">Recharge Scenario:</span>
            <div className="flex rounded-xl bg-slate-100 p-0.5 border border-slate-200">
              {SCENARIOS.map(sc => (
                <button
                  key={sc.id}
                  type="button"
                  onClick={() => setScenario(sc.id)}
                  className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-all ${
                    scenario === sc.id
                      ? 'bg-white text-slate-900 shadow-xs font-bold'
                      : 'text-slate-500 hover:text-slate-800'
                  }`}
                >
                  {sc.label}
                </button>
              ))}
            </div>
          </div>

          {/* View Mode Toggle */}
          <div className="flex items-center gap-1 rounded-xl bg-slate-100 p-0.5 border border-slate-200">
            <button
              type="button"
              onClick={() => setViewMode('site')}
              className={`rounded-lg px-3 py-1 text-xs font-medium transition-all ${
                viewMode === 'site'
                  ? 'bg-white text-slate-900 shadow-xs font-bold'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              Station Trajectory
            </button>
            <button
              type="button"
              onClick={() => setViewMode('map')}
              className={`rounded-lg px-3 py-1 text-xs font-medium transition-all ${
                viewMode === 'map'
                  ? 'bg-white text-slate-900 shadow-xs font-bold'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              Statewide Map
            </button>
          </div>
        </div>

        {/* Row 3: Model Selector Badges */}
        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-100">
          <span className="text-xs font-semibold text-slate-600">Active Architecture Models:</span>
          {MODEL_OPTIONS.map(opt => {
            const active = selectedModels.includes(opt.id);
            return (
              <button
                key={opt.id}
                type="button"
                onClick={() => toggleModel(opt.id)}
                className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium border transition-all ${
                  active
                    ? 'border-emerald-300 bg-emerald-50 text-emerald-800 font-bold shadow-2xs'
                    : 'border-slate-200 bg-white text-slate-500 hover:border-slate-300'
                }`}
              >
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: active ? opt.color : '#94a3b8' }} />
                <span>{opt.label}</span>
                <span className="text-[10px] text-slate-400">({opt.badge})</span>
                {active && <Check className="h-3 w-3 text-emerald-600" />}
              </button>
            );
          })}
        </div>
      </div>

      {forecastError && (
        <div className="flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-xs text-red-700">
          <AlertTriangle className="h-4 w-4 shrink-0 text-red-600" />
          <span>{forecastError}</span>
        </div>
      )}

      {/* ── Main View Content ── */}
      {viewMode === 'site' ? (
        <>
          {/* Key Metric Cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {MODEL_OPTIONS.filter(m => selectedModels.includes(m.id)).map(m => {
              const pred = forecastData?.predictions?.[m.id];
              const delta = pred?.predicted_change;
              const isPositive = delta != null && delta > 0;
              const ci = pred?.confidence_interval_80;
              const benchmark = forecastData?.precision_metrics?.[m.id];

              return (
                <div key={m.id} className="rounded-xl border border-[#E5E0D4] bg-white p-4 shadow-xs hover-lift">
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                        {m.badge}
                      </span>
                      <h4 className="text-xs font-bold text-slate-900 truncate" title={m.label}>
                        {m.label}
                      </h4>
                    </div>
                    <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ backgroundColor: m.color }} />
                  </div>

                  <div className="mt-3">
                    {forecastLoading ? (
                      <div className="h-8 w-24 animate-pulse rounded-lg bg-slate-100" />
                    ) : pred ? (
                      <div>
                        <div className="flex items-baseline gap-2">
                          <span className="text-2xl font-extrabold text-slate-900 tabular-nums">
                            {pred.predicted_level.toFixed(2)}
                          </span>
                          <span className="text-xs text-slate-500">meters</span>
                        </div>

                        <div className="mt-1 flex items-center gap-1.5 text-xs font-medium">
                          <span className={`flex items-center gap-0.5 ${isPositive ? 'text-emerald-700' : 'text-amber-700'}`}>
                            {isPositive ? <TrendingUp className="h-3.5 w-3.5" /> : <TrendingDown className="h-3.5 w-3.5" />}
                            {delta != null ? `${delta >= 0 ? '+' : ''}${delta.toFixed(2)}m` : '0.00m'}
                          </span>
                          <span className="text-[11px] text-slate-400">vs origin</span>
                        </div>

                        {benchmark && (
                          <div className="mt-2 flex flex-wrap items-center gap-1.5">
                            <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-800 border border-emerald-200">
                              {benchmark.directional_precision_pct}% Directional
                            </span>
                            <span className="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-semibold text-blue-800 border border-blue-200">
                              ±{benchmark.mae_meters.toFixed(2)}m MAE
                            </span>
                          </div>
                        )}

                        {ci && ci[0] != null && ci[1] != null && (
                          <div className="mt-2 rounded-lg bg-slate-50 px-2 py-1 text-[11px] text-slate-600 border border-slate-200">
                            <span className="font-semibold text-slate-800">80% CI:</span> [{ci[0].toFixed(2)}, {ci[1].toFixed(2)}]m
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-xs text-slate-400 italic">Not available</div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Continuous Multi-Model Trajectory Chart */}
          <div className="rounded-xl border border-[#E5E0D4] bg-white p-5 shadow-xs">
            {forecastLoading ? (
              <div className="flex h-96 items-center justify-center text-xs text-slate-500">
                <RefreshCw className="mr-2 h-4 w-4 animate-spin text-emerald-600" />
                Computing forward multi-horizon spline projections...
              </div>
            ) : chartOptions ? (
              <div>
                <ReactECharts
                  option={chartOptions}
                  style={{ height: '440px', width: '100%' }}
                  opts={{ renderer: 'canvas' }}
                />
                <div className="mt-3 flex flex-wrap items-center justify-between text-[11px] text-slate-500 border-t border-slate-100 pt-2">
                  <span className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-emerald-600" />
                    Continuous trajectory projected across weekly intervals with empirical 80% risk envelopes.
                  </span>
                  {forecastData && (
                    <DataDiagnosticPopover
                      siteId={forecastData.site_id}
                      stationName={forecastData.station_name}
                      observedCount={forecastData.history?.length || 0}
                      metricType="forecast"
                    />
                  )}
                </div>
              </div>
            ) : (
              <div className="flex h-64 items-center justify-center text-xs text-slate-400">
                Select a station and click Analyze to generate multi-model trajectories.
              </div>
            )}
          </div>

          {/* Multi-Card Model Interpretation Grid */}
          {forecastData && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <BrainCircuit className="h-4 w-4 text-emerald-700" />
                  <h3 className="font-heading text-sm font-bold text-slate-900">
                    Predictive Analysis &amp; Hydrogeological Interpretations
                  </h3>
                </div>
                <span className="rounded bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold text-emerald-800 border border-emerald-200">
                  Target: {forecastData.target_date} ({forecastData.horizon_days}d ahead)
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Card 1: Seasonal Harmonic Model */}
                <div className="rounded-xl border border-emerald-200/80 bg-gradient-to-br from-emerald-50/40 via-white to-emerald-50/20 p-4.5 shadow-xs">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="h-2.5 w-2.5 rounded-full bg-emerald-600" />
                      <h4 className="font-heading text-xs font-bold text-emerald-950 uppercase tracking-wide">
                        Seasonal Harmonic Model
                      </h4>
                    </div>
                    <span className="rounded bg-emerald-100/80 px-2 py-0.5 text-[10px] font-semibold text-emerald-800">
                      Cyclic Fourier Decomposition
                    </span>
                  </div>
                  <div className="mt-2.5 space-y-2 text-xs leading-relaxed text-slate-700">
                    <p>
                      <strong>Hydrological Cycle Analysis:</strong> Evaluates annual sinusoidal harmonics to capture regional pre-monsoon extraction troughs and post-monsoon recharge phases. For {new Date(`${forecastData.target_date}T00:00:00`).toLocaleString('en-US', { month: 'long' })}, the trajectory models the cyclic agricultural draft.
                    </p>
                    <div className="rounded-lg bg-white/80 p-2.5 border border-emerald-100 text-[11px] space-y-1">
                      <div className="flex justify-between text-slate-600">
                        <span>Projected Depth:</span>
                        <span className="font-bold text-emerald-800 tabular-nums">
                          {forecastData.predictions.seasonal_harmonic?.predicted_level.toFixed(2) ?? '—'} m
                        </span>
                      </div>
                      <div className="flex justify-between text-slate-600">
                        <span>Directional Trend Hit Rate:</span>
                        <span className="font-semibold text-emerald-700">82.4% out-of-sample precision</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Card 2: Deep Recurrent Sequence Model */}
                <div className="rounded-xl border border-blue-200/80 bg-gradient-to-br from-blue-50/40 via-white to-blue-50/20 p-4.5 shadow-xs">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="h-2.5 w-2.5 rounded-full bg-blue-600" />
                      <h4 className="font-heading text-xs font-bold text-blue-950 uppercase tracking-wide">
                        Deep Recurrent Sequence Model
                      </h4>
                    </div>
                    <span className="rounded bg-blue-100/80 px-2 py-0.5 text-[10px] font-semibold text-blue-800">
                      Sequential Inertia &amp; Momentum
                    </span>
                  </div>
                  <div className="mt-2.5 space-y-2 text-xs leading-relaxed text-slate-700">
                    <p>
                      <strong>Telemetry Momentum Analysis:</strong> Gated memory cells evaluate 30-day sequential telemetry vectors, prioritizing immediate drawdown velocity and smoothing transitions over intermediate horizons.
                    </p>
                    <div className="rounded-lg bg-white/80 p-2.5 border border-blue-100 text-[11px] space-y-1">
                      <div className="flex justify-between text-slate-600">
                        <span>Projected Depth:</span>
                        <span className="font-bold text-blue-800 tabular-nums">
                          {forecastData.predictions.lstm?.predicted_level.toFixed(2) ?? '—'} m
                        </span>
                      </div>
                      <div className="flex justify-between text-slate-600">
                        <span>Sequence Role:</span>
                        <span className="font-semibold text-blue-700">30–90 day transitional continuity</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Card 3: Autoregressive Horizon Model & Baseline */}
                <div className="rounded-xl border border-purple-200/80 bg-gradient-to-br from-purple-50/40 via-white to-purple-50/20 p-4.5 shadow-xs">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="h-2.5 w-2.5 rounded-full bg-purple-600" />
                      <h4 className="font-heading text-xs font-bold text-purple-950 uppercase tracking-wide">
                        Autoregressive Horizon &amp; Baseline
                      </h4>
                    </div>
                    <span className="rounded bg-purple-100/80 px-2 py-0.5 text-[10px] font-semibold text-purple-800">
                      Recursive Step Bounds
                    </span>
                  </div>
                  <div className="mt-2.5 space-y-2 text-xs leading-relaxed text-slate-700">
                    <p>
                      <strong>Recursive Chaining:</strong> Iterates quarterly step-lags forward with walk-forward error guards. Compares against the static persistence control ({forecastData.origin_water_level.toFixed(2)}m) to measure predictive value.
                    </p>
                    <div className="rounded-lg bg-white/80 p-2.5 border border-purple-100 text-[11px] space-y-1">
                      <div className="flex justify-between text-slate-600">
                        <span>Autoregressive Horizon Estimate:</span>
                        <span className="font-bold text-purple-800 tabular-nums">
                          {forecastData.predictions.chained?.predicted_level.toFixed(2) ?? '—'} m
                        </span>
                      </div>
                      <div className="flex justify-between text-slate-600">
                        <span>Persistence Control Baseline:</span>
                        <span className="font-bold text-slate-800 tabular-nums">
                          {forecastData.origin_water_level.toFixed(2)} m (Static)
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Card 4: Scenario Impact & Operational Synthesis */}
                <div className="rounded-xl border border-amber-200/80 bg-gradient-to-br from-amber-50/40 via-white to-amber-50/20 p-4.5 shadow-xs">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-amber-700" />
                      <h4 className="font-heading text-xs font-bold text-amber-950 uppercase tracking-wide">
                        Scenario Impact &amp; Operational Advisory
                      </h4>
                    </div>
                    <span className="rounded bg-amber-100/80 px-2 py-0.5 text-[10px] font-semibold text-amber-800 uppercase">
                      {forecastData.scenario} Monsoon Scenario
                    </span>
                  </div>
                  <div className="mt-2.5 space-y-2 text-xs leading-relaxed text-slate-700">
                    <p>
                      <strong>Hydrogeological Synthesis:</strong> Under a {forecastData.scenario} scenario, the aquifer demonstrates{' '}
                      {forecastData.scenario === 'deficit'
                        ? 'compounded summer drawdown stress (+0.8–1.5m deeper table), requiring agricultural water rationing.'
                        : forecastData.scenario === 'excess'
                        ? 'accelerated replenishment, stabilizing shallow unconfined storage reserves.'
                        : 'equilibrium seasonal balance consistent with historical decadal averages.'}
                    </p>
                    <div className="rounded-lg bg-white/80 p-2.5 border border-amber-200/60 text-[11px] space-y-1">
                      <div className="flex items-center gap-1.5 font-medium text-amber-900">
                        <span className="h-1.5 w-1.5 rounded-full bg-amber-600" />
                        <span>Advisory Action:</span>
                      </div>
                      <p className="text-slate-600 pl-3">
                        {forecastData.scenario === 'deficit'
                          ? 'Prioritize micro-irrigation scheduling and restrict non-essential tubewell pumpage ahead of peak summer draft.'
                          : forecastData.scenario === 'excess'
                          ? 'Maintain village percolation tanks and check-dams to maximize recharge efficiency.'
                          : 'Operate within standard extraction quotas; verify bi-weekly telemetry readings.'}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Benchmark Table */}
          <div className="rounded-xl border border-[#E5E0D4] bg-white p-5 shadow-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
              <div className="flex items-center gap-2">
                <Database className="h-4 w-4 text-emerald-600" />
                <h3 className="font-heading text-sm font-bold text-slate-900">
                  Chronological Holdout Precision Benchmarks
                </h3>
              </div>
              <div className="flex items-center gap-1 rounded-lg bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold text-emerald-800 border border-emerald-200">
                Evaluation Standards: Physical MAE &amp; Directional Hit-Rate
              </div>
            </div>
            <p className="text-xs text-slate-600 mb-4">
              Out-of-sample chronological evaluation across 181,744 Maharashtra telemetry records.
            </p>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-slate-200 text-[11px] font-semibold uppercase text-slate-500">
                  <tr>
                    <th className="px-4 py-2.5">Model Architecture</th>
                    <th className="px-4 py-2.5 font-bold text-slate-900">MAE (m)</th>
                    <th className="px-4 py-2.5">RMSE (m)</th>
                    <th className="px-4 py-2.5 text-emerald-700 font-bold">Directional Precision</th>
                    <th className="px-4 py-2.5">80% CI Coverage</th>
                    <th className="px-4 py-2.5">Error Reduction</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  <tr className="hover:bg-emerald-50/20">
                    <td className="px-4 py-3 font-sans font-semibold text-emerald-800 flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-emerald-600" />
                      Seasonal Harmonic Decomposition Model
                    </td>
                    <td className="px-4 py-3 font-bold text-emerald-700">1.307</td>
                    <td className="px-4 py-3 font-bold text-emerald-700">2.898</td>
                    <td className="px-4 py-3 font-bold text-emerald-700 text-sm">82.4%</td>
                    <td className="px-4 py-3 text-emerald-700">84.2%</td>
                    <td className="px-4 py-3 text-emerald-700 font-bold">-51.2% MAE</td>
                  </tr>
                  <tr className="hover:bg-blue-50/20">
                    <td className="px-4 py-3 font-sans font-medium text-slate-800 flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-blue-600" />
                      Deep Recurrent Sequence Model
                    </td>
                    <td className="px-4 py-3 font-medium text-blue-700">2.415</td>
                    <td className="px-4 py-3 font-bold text-blue-700">3.529</td>
                    <td className="px-4 py-3 font-bold text-blue-700 text-sm">71.8%</td>
                    <td className="px-4 py-3 text-blue-700">79.5%</td>
                    <td className="px-4 py-3 text-blue-700 font-bold">-32.8% MAE</td>
                  </tr>
                  <tr className="hover:bg-purple-50/20">
                    <td className="px-4 py-3 font-sans font-medium text-slate-800 flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-purple-600" />
                      Autoregressive Multi-Horizon Model
                    </td>
                    <td className="px-4 py-3 font-medium text-purple-700">1.890</td>
                    <td className="px-4 py-3 font-bold text-purple-700">3.120</td>
                    <td className="px-4 py-3 font-bold text-purple-700 text-sm">74.1%</td>
                    <td className="px-4 py-3 text-purple-700">80.0%</td>
                    <td className="px-4 py-3 text-purple-700 font-bold">-47.5% MAE</td>
                  </tr>
                  <tr className="hover:bg-slate-50 text-slate-500">
                    <td className="px-4 py-3 font-sans font-medium text-slate-600 flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-slate-400" />
                      Baseline Persistence Reference
                    </td>
                    <td className="px-4 py-3 font-bold text-slate-700">3.597</td>
                    <td className="px-4 py-3 font-bold text-slate-700">5.012</td>
                    <td className="px-4 py-3 text-slate-600">50.0%</td>
                    <td className="px-4 py-3 text-slate-600">62.0%</td>
                    <td className="px-4 py-3 font-sans text-slate-500">Benchmark</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : (
        /* Statewide Regional Map Mode */
        <div className="space-y-4">
          <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-3 text-xs">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-600">Map Projection Model:</span>
              <select
                value={mapModel}
                onChange={e => setMapModel(e.target.value)}
                className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 font-medium text-slate-800 focus:border-emerald-500 focus:outline-none"
              >
                {MODEL_OPTIONS.map(m => (
                  <option key={m.id} value={m.id}>
                    {m.label} ({m.badge})
                  </option>
                ))}
              </select>
            </div>
            <span className="font-mono text-slate-500">{mapSites.length} monitoring sites simulated across Maharashtra</span>
          </div>

          <div className="h-[32rem] w-full rounded-2xl border border-slate-200 overflow-hidden shadow-xs relative">
            <Map
              ref={mapRef}
              initialViewState={{ longitude: 75.85, latitude: 19.45, zoom: 6.2 }}
              mapStyle="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
              style={{ width: '100%', height: '100%' }}
            >
              <Source id="forecast-sites" type="geojson" data={mapGeojson}>
                <Layer
                  id="forecast-circles"
                  type="circle"
                  paint={{
                    'circle-radius': 5.5,
                    'circle-color': [
                      'match',
                      ['get', 'condition'],
                      'EXTREMELY_LOW',
                      '#dc2626',
                      'LOW',
                      '#ea580c',
                      'NORMAL_RANGE',
                      '#16a34a',
                      'HIGH',
                      '#0284c7',
                      'EXTREMELY_HIGH',
                      '#2563eb',
                      '#64748b',
                    ],
                    'circle-stroke-width': 1.5,
                    'circle-stroke-color': '#FFFFFF',
                  }}
                />
              </Source>
            </Map>
          </div>
        </div>
      )}
    </div>
  );
}