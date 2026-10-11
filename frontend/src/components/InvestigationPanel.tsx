import { useEffect, useState, useRef } from 'react';
import ReactECharts from 'echarts-for-react';
import { fetchIndiaAlerts, fetchMHAlerts, fetchIndiaCondition, fetchMHCondition, fetchMHForecast, fetchAnalytics } from '../services/api';
import type { CandidateSite, IndiaAlert, MHAlert, GroundwaterCondition, ConditionState, PersistenceForecast } from '../services/api';
import { getAlertConfig } from '../utils/alertUtils';
import { X, MapPin, Calendar, Droplets, TrendingUp, ArrowDownToLine, ArrowDown, CheckCircle2, ArrowUp, ArrowUpToLine, Info, Activity, BarChart2, ShieldCheck, BookOpen } from 'lucide-react';
import { AdvancedAnalytics } from './AdvancedAnalytics';
import { FutureForecastCard } from './FutureForecastCard';
import { ChainedForecastCard } from './ChainedForecastCard';

interface Props {
  site: CandidateSite;
  dataset: 'india' | 'maharashtra';
  onClose: () => void;
}

function AlertBadge({ state }: { state: string }) {
  const cfg = getAlertConfig(state as any);
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-semibold tracking-wide"
      style={{ color: cfg.color, backgroundColor: cfg.bgColor, border: `1px solid ${cfg.borderColor}` }}
      aria-label={`Alert state: ${cfg.label}`}
    >
      <span aria-hidden="true" style={{ fontSize: '0.6rem' }}>{cfg.icon}</span>
      {cfg.label}
    </span>
  );
}

function MetaRow({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null;
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] uppercase tracking-wider text-slate-500 font-medium">{label}</span>
      <span className="text-sm text-slate-200">{value}</span>
    </div>
  );
}

function getConditionConfig(state: ConditionState) {
  switch (state) {
    case 'EXTREMELY_LOW': return { label: 'EXTREMELY LOW', color: '#ef4444', bgColor: '#7f1d1d20', borderColor: '#ef444450', icon: <ArrowDownToLine className="w-3 h-3" /> };
    case 'LOW': return { label: 'LOW', color: '#f97316', bgColor: '#9a341220', borderColor: '#f9731650', icon: <ArrowDown className="w-3 h-3" /> };
    case 'NORMAL_RANGE': return { label: 'NORMAL RANGE', color: '#10b981', bgColor: '#065f4620', borderColor: '#10b98150', icon: <CheckCircle2 className="w-3 h-3" /> };
    case 'HIGH': return { label: 'HIGH', color: '#3b82f6', bgColor: '#1e3a8a20', borderColor: '#3b82f650', icon: <ArrowUp className="w-3 h-3" /> };
    case 'EXTREMELY_HIGH': return { label: 'EXTREMELY HIGH', color: '#8b5cf6', bgColor: '#4c1d9520', borderColor: '#8b5cf650', icon: <ArrowUpToLine className="w-3 h-3" /> };
    case 'INSUFFICIENT_HISTORY': return { label: 'INSUFFICIENT HISTORY', color: '#94a3b8', bgColor: '#33415520', borderColor: '#64748b50', icon: <Info className="w-3 h-3" /> };
    default: return { label: state, color: '#94a3b8', bgColor: '#33415520', borderColor: '#64748b50', icon: <Info className="w-3 h-3" /> };
  }
}

function ConditionBadge({ state }: { state: ConditionState }) {
  const cfg = getConditionConfig(state);
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-semibold tracking-wide"
      style={{ color: cfg.color, backgroundColor: cfg.bgColor, border: `1px solid ${cfg.borderColor}` }}
      aria-label={`Condition state: ${cfg.label}`}
    >
      <span aria-hidden="true" className="flex items-center">{cfg.icon}</span>
      {cfg.label}
    </span>
  );
}

export const InvestigationPanel: React.FC<Props> = ({ site, dataset, onClose }) => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<(IndiaAlert | MHAlert)[]>([]);
  const [error, setError] = useState<string | null>(null);
  
  const [condition, setCondition] = useState<GroundwaterCondition | null>(null);
  const [conditionLoading, setConditionLoading] = useState(true);
  const [conditionError, setConditionError] = useState<string | null>(null);

  const [forecast, setForecast] = useState<PersistenceForecast | null>(null);
  const [forecastLoading, setForecastLoading] = useState(true);
  const [forecastError, setForecastError] = useState<string | null>(null);

  const [analytics, setAnalytics] = useState<any | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(true);

  const [activeTab, setActiveTab] = useState<'overview' | 'analytics' | 'methodology'>('overview');

  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let mounted = true;

    const loadAlerts = async () => {
      try {
        setLoading(true);
        setError(null);
        setData([]);
        let results: (IndiaAlert | MHAlert)[];
        if (dataset === 'india') {
          const r = await fetchIndiaAlerts(site.candidate_site_id);
          r.sort((a, b) => a.observation_date.localeCompare(b.observation_date));
          results = r;
        } else {
          const r = await fetchMHAlerts(site.candidate_site_id);
          r.sort((a, b) => a.observation_timestamp.localeCompare(b.observation_timestamp));
          results = r;
        }
        if (mounted) setData(results);
      } catch {
        if (mounted) setError('Failed to load observation data.');
      } finally {
        if (mounted) setLoading(false);
      }
    };

    const loadCondition = async () => {
      try {
        setConditionLoading(true);
        setConditionError(null);
        setCondition(null);
        const cond = dataset === 'india' 
          ? await fetchIndiaCondition(site.candidate_site_id)
          : await fetchMHCondition(site.candidate_site_id);
        if (mounted) setCondition(cond);
      } catch {
        if (mounted) setConditionError('Condition unavailable');
      } finally {
        if (mounted) setConditionLoading(false);
      }
    };

    const loadForecast = async () => {
      if (dataset === 'india') {
        setForecastLoading(false);
        setForecast(null);
        return;
      }
      try {
        setForecastLoading(true);
        setForecastError(null);
        setForecast(null);
        const f = await fetchMHForecast(site.candidate_site_id);
        if (mounted) setForecast(f);
      } catch {
        if (mounted) setForecastError('Forecast unavailable');
      } finally {
        if (mounted) setForecastLoading(false);
      }
    };

    const loadAnalytics = async () => {
      try {
        setAnalyticsLoading(true);
        const a = await fetchAnalytics(site.candidate_site_id, dataset);
        if (mounted) setAnalytics(a);
      } catch {
        if (mounted) setAnalytics(null);
      } finally {
        if (mounted) setAnalyticsLoading(false);
      }
    };

    loadAlerts();
    loadCondition();
    loadForecast();
    loadAnalytics();

    return () => { mounted = false; };
  }, [site, dataset]);

  // Focus trap on open
  useEffect(() => {
    panelRef.current?.focus();
  }, [site]);

  const isIndia = dataset === 'india';
  const latest = data.length > 0 ? data[data.length - 1] : null;
  const latestIndia = isIndia && latest ? (latest as IndiaAlert) : null;
  const latestMH = !isIndia && latest ? (latest as MHAlert) : null;

  // Build chart series
  const chartData = data.map(d => {
    const dateVal = isIndia
      ? new Date((d as IndiaAlert).observation_date).getTime()
      : new Date((d as MHAlert).observation_timestamp).getTime();
    return [dateVal, d.water_level_raw];
  });

  const chartOptions = {
    animation: false,
    tooltip: {
      trigger: isIndia ? 'item' : 'axis',
      backgroundColor: '#0f172a',
      borderColor: '#334155',
      textStyle: { color: '#f8fafc', fontSize: 11 },
      formatter: isIndia
        ? (params: any) => {
            const d = data[params.dataIndex] as IndiaAlert;
            const val = d.water_level_raw != null ? d.water_level_raw.toFixed(3) : 'N/A';
            const cfg = getAlertConfig(d.alert_event_state);
            return `<div style="line-height:1.8">
              <div style="color:#94a3b8;font-size:10px">${d.observation_date}</div>
              <div>Season: <b>${d.analytical_season ?? '—'}</b></div>
              <div>Level: <b>${val}</b></div>
              <div>State: <span style="color:${cfg.color}">${cfg.icon} ${cfg.label}</span></div>
            </div>`;
          }
        : (params: any) => {
            const p = Array.isArray(params) ? params[0] : params;
            const d = data[p.dataIndex] as MHAlert;
            const val = d.water_level_raw != null ? d.water_level_raw.toFixed(3) + ' m' : 'N/A';
            const cfg = getAlertConfig(d.alert_event_state);
            return `<div style="line-height:1.8">
              <div style="color:#94a3b8;font-size:10px">${d.observation_timestamp?.split('T')[0]}</div>
              <div>Level: <b>${val}</b></div>
              <div>State: <span style="color:${cfg.color}">${cfg.icon} ${cfg.label}</span></div>
            </div>`;
          }
    },
    grid: { top: 8, right: 12, bottom: isIndia ? 30 : 48, left: 48 },
    xAxis: {
      type: 'time',
      axisLabel: {
        color: '#64748b',
        fontSize: 9,
        hideOverlap: true,
        formatter: (val: number) => {
          const d = new Date(val);
          return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
        }
      },
      splitLine: { show: false },
      axisLine: { lineStyle: { color: '#1e293b' } }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#64748b', fontSize: 9 },
      splitLine: { lineStyle: { type: 'dashed' as const, color: '#1e293b' } },
      scale: true
    },
    dataZoom: isIndia ? [] : [
      { type: 'inside' as const, start: 0, end: 100 },
      { type: 'slider' as const, show: true, bottom: 2, height: 10, borderColor: 'transparent', backgroundColor: '#1e293b', fillerColor: '#334155' }
    ],
    series: [
      isIndia
        ? {
            // India: SCATTER plot — explicitly no line connecting observations
            type: 'scatter' as const,
            name: 'Water Level',
            data: chartData,
            symbolSize: 6,
            itemStyle: { color: '#3b82f6', borderColor: '#60a5fa', borderWidth: 1 },
            emphasis: { itemStyle: { symbolSize: 10, color: '#60a5fa' } }
          }
        : {
            // Maharashtra: line chart, gaps remain visible via connectNulls:false
            type: 'line' as const,
            name: 'Water Level',
            data: chartData,
            connectNulls: false,
            showSymbol: false,
            lineStyle: { color: '#3b82f6', width: 1.5 },
            itemStyle: { color: '#3b82f6' },
            areaStyle: { color: 'rgba(59, 130, 246, 0.06)' }
          }
    ]
  };

  // Build geographic identity string
  const geoIdentity = [site.district, site.state].filter(Boolean).join(', ') || null;
  const detailLine = isIndia
    ? [site.block, site.village].filter(Boolean).join(', ') || null
    : [site.subdistrict].filter(Boolean).join(', ') || null;

  const historyLabel = isIndia ? 'HISTORICAL OBSERVATIONS' : 'TELEMETRY HISTORY';
  const yAxisLabel = isIndia ? 'Water Level (Unknown Units)' : 'Water Level (Meters)';
  const emptyLabel = isIndia ? 'No historical observations available.' : 'No telemetry observations available.';
  const loadingLabel = isIndia ? 'Loading observations…' : 'Loading telemetry…';

  return (
    <div
      ref={panelRef}
      tabIndex={-1}
      role="dialog"
      aria-label={`Investigation panel for ${site.candidate_site_id}`}
      className="absolute top-0 right-0 h-full bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col z-20"
      style={{ width: '22rem' }}
    >
      {/* Panel Header */}
      <div className="flex items-start justify-between p-4 border-b border-slate-800 gap-2">
        <div className="min-w-0">
          <div className="text-[10px] uppercase tracking-widest text-slate-500 mb-1 font-medium">
            {isIndia ? 'Historical Candidate Site' : 'Telemetry Station'}
          </div>
          <h2
            className="text-sm font-mono font-bold text-slate-100 truncate"
            title={site.candidate_site_id}
          >
            {site.candidate_site_id}
          </h2>
          {site.station_name && (
            <div className="text-xs text-slate-300 mt-0.5 truncate">{site.station_name}</div>
          )}
          {geoIdentity && (
            <div className="flex items-center gap-1 mt-1">
              <MapPin className="w-3 h-3 text-slate-500 shrink-0" aria-hidden="true" />
              <span className="text-xs text-slate-400 truncate">{geoIdentity}</span>
            </div>
          )}
          {detailLine && (
            <div className="text-xs text-slate-500 mt-0.5 ml-4">{detailLine}</div>
          )}
        </div>
        <button
          onClick={onClose}
          className="p-1 hover:bg-slate-800 rounded shrink-0 focus:outline-none focus:ring-2 focus:ring-blue-500"
          aria-label="Close investigation panel"
        >
          <X className="w-4 h-4 text-slate-400" />
        </button>
      </div>

      <div className="flex border-b border-slate-800">
        <button
          onClick={() => setActiveTab('overview')}
          className={`flex-1 py-2 text-[11px] font-medium flex items-center justify-center gap-1.5 transition-colors focus:outline-none ${activeTab === 'overview' ? 'text-blue-400 border-b-2 border-blue-500 bg-blue-500/5' : 'text-slate-500 hover:text-slate-300'}`}
        >
          <Activity className="w-3.5 h-3.5" />
          Overview
        </button>
        <button
          onClick={() => setActiveTab('analytics')}
          className={`flex-1 py-2 text-[11px] font-medium flex items-center justify-center gap-1.5 transition-colors focus:outline-none ${activeTab === 'analytics' ? 'text-blue-400 border-b-2 border-blue-500 bg-blue-500/5' : 'text-slate-500 hover:text-slate-300'}`}
        >
          <BarChart2 className="w-3.5 h-3.5" />
          Analytics
        </button>
        <button
          onClick={() => setActiveTab('methodology')}
          className={`flex-1 py-2 text-[11px] font-medium flex items-center justify-center gap-1.5 transition-colors focus:outline-none ${activeTab === 'methodology' ? 'text-blue-400 border-b-2 border-blue-500 bg-blue-500/5' : 'text-slate-500 hover:text-slate-300'}`}
        >
          <BookOpen className="w-3.5 h-3.5" />
          Methodology
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {activeTab === 'overview' ? (
          <>
            {/* Groundwater Condition Section */}
        <div className="p-4 border-b border-slate-800/50">
          <div className="text-[10px] uppercase tracking-widest text-slate-500 mb-2 font-medium">Groundwater Condition</div>
          {conditionLoading ? (
            <div className="animate-pulse flex flex-col gap-2">
               <div className="h-5 w-28 bg-slate-800 rounded"></div>
               <div className="h-4 w-40 bg-slate-800 rounded mt-1"></div>
            </div>
          ) : conditionError ? (
            <div className="text-slate-500 text-xs italic">{conditionError}</div>
          ) : condition ? (
            <div className="flex flex-col gap-2">
              <div>
                <ConditionBadge state={condition.condition_state} />
              </div>
              
              {condition.condition_state === 'INSUFFICIENT_HISTORY' ? (
                <div className="text-xs text-slate-400 mt-1">
                  Insufficient historical observations for statistical condition classification.
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-x-4 gap-y-2 mt-2">
                  {condition.percentile != null && (
                    <MetaRow label="Percentile" value={`${condition.percentile.toFixed(1)}`} />
                  )}
                  {condition.historical_sample_count != null && (
                    <MetaRow label="Historical Obs." value={`${condition.historical_sample_count}`} />
                  )}
                  {condition.historical_reference_group && (
                    <MetaRow label="Reference Group" value={condition.historical_reference_group.replace(/_/g, ' ')} />
                  )}
                  {condition.condition_method_version && (
                    <MetaRow label="Method Version" value={condition.condition_method_version} />
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="text-slate-500 text-xs italic">Condition unavailable</div>
          )}
        </div>

        {/* Statistical Alert Section */}
        {latest && (
          <div className="p-4 border-b border-slate-800/50">
            <div className="text-[10px] uppercase tracking-widest text-slate-500 mb-2 font-medium">Statistical Alert</div>
            <div className="flex items-start justify-between gap-2">
              <AlertBadge state={latest.alert_event_state} />
              <div className="text-right text-xs text-slate-500">
                {latestIndia && (
                  <>
                    <div className="flex items-center gap-1 justify-end">
                      <Calendar className="w-3 h-3" aria-hidden="true" />
                      <span>{latestIndia.observation_date}</span>
                    </div>
                    {latestIndia.analytical_season && (
                      <div className="text-slate-600 capitalize">{latestIndia.analytical_season}</div>
                    )}
                  </>
                )}
                {latestMH && (
                  <div className="flex items-center gap-1 justify-end">
                    <Calendar className="w-3 h-3" aria-hidden="true" />
                    <span>{latestMH.observation_timestamp?.split('T')[0]}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Latest reading */}
            {latest.water_level_raw != null && (
              <div className="mt-2 flex items-center gap-2">
                <Droplets className="w-3 h-3 text-blue-400 shrink-0" aria-hidden="true" />
                <span className="text-xs text-slate-400">
                  {latest.water_level_raw.toFixed(3)}
                  <span className="text-slate-600 ml-1">{isIndia ? '(units unknown)' : 'm'}</span>
                </span>
                {latest.historical_reference != null && (
                  <span className="text-xs text-slate-600">
                    · ref {latest.historical_reference.toFixed(3)}
                  </span>
                )}
              </div>
            )}

            {/* Standardized score — only if present and numeric */}
            {latest.standardized_score != null && isFinite(latest.standardized_score) && (
              <div className="mt-1 flex items-center gap-2">
                <TrendingUp className="w-3 h-3 text-slate-500 shrink-0" aria-hidden="true" />
                <span className="text-xs text-slate-500">
                  z-score: <span className="text-slate-400 font-mono">{latest.standardized_score.toFixed(2)}</span>
                </span>
              </div>
            )}
          </div>
        )}

        {/* Next-Observation Forecast Section */}
        {!isIndia && (
          <div className="p-4 border-b border-slate-800/50">
            <div className="text-[10px] uppercase tracking-widest text-slate-500 mb-2 font-medium">Next-Observation Forecast</div>
            {forecastLoading ? (
              <div className="animate-pulse flex flex-col gap-2">
                 <div className="h-6 w-28 bg-slate-800 rounded"></div>
                 <div className="h-4 w-48 bg-slate-800 rounded mt-1"></div>
              </div>
            ) : forecastError ? (
              <div className="text-slate-500 text-xs italic">{forecastError}</div>
            ) : forecast ? (
              <div className="flex flex-col gap-2">
                <div className="flex items-center gap-2 text-sm text-slate-200">
                  <Droplets className="w-4 h-4 text-blue-400 shrink-0" aria-hidden="true" />
                  <span className="font-mono text-lg font-bold">{forecast.predicted_next_water_level.toFixed(3)}</span>
                  <span className="text-slate-500 text-xs mt-0.5">{forecast.water_level_unit}</span>
                </div>
                <div className="text-xs text-slate-400 mt-1">
                  <span className="font-semibold text-slate-300">Method: Persistence</span>
                  <p className="mt-0.5 leading-relaxed">Uses the latest valid groundwater level as the prediction for the next valid observation.</p>
                </div>
              </div>
            ) : (
              <div className="text-slate-500 text-xs italic">Forecast not available for this dataset</div>
            )}
          </div>
        )}

        {/* M17: multi-horizon future forecast (additive) */}
        <FutureForecastCard siteId={site.candidate_site_id} dataset={dataset} />
        <ChainedForecastCard siteId={site.candidate_site_id} dataset={dataset} />

        {/* Geographic Metadata */}
        <div className="p-4 border-b border-slate-800/50">
          <div className="text-[10px] uppercase tracking-widest text-slate-500 mb-2 font-medium">Location</div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-2">
            <MetaRow label="State" value={site.state} />
            <MetaRow label="District" value={site.district} />
            {isIndia && <MetaRow label="Block" value={site.block} />}
            {isIndia && <MetaRow label="Village" value={site.village} />}
            {!isIndia && <MetaRow label="Subdistrict" value={site.subdistrict} />}
          </div>
        </div>

        {/* Intelligence Models */}
        <div className="p-4 border-b border-slate-800/50">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-[10px] uppercase tracking-widest text-slate-500 mb-1 font-medium">Project Groundwater Drought Intelligence</div>
              {analyticsLoading ? (
                 <div className="h-4 w-20 bg-slate-800 rounded animate-pulse"></div>
              ) : (
                 <div className="text-xs font-semibold text-slate-200">{analytics?.cross_intelligence?.drought?.replace(/_/g, ' ') || 'UNAVAILABLE'}</div>
              )}
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-widest text-slate-500 mb-1 font-medium">Groundwater Flood Potential</div>
              {analyticsLoading ? (
                 <div className="h-4 w-20 bg-slate-800 rounded animate-pulse"></div>
              ) : (
                 <div className="text-xs font-semibold text-slate-200">{analytics?.cross_intelligence?.flood_potential?.replace(/_/g, ' ') || 'UNAVAILABLE'}</div>
              )}
            </div>
            <div className="col-span-2">
              <div className="text-[10px] uppercase tracking-widest text-slate-500 mb-1 font-medium">Groundwater Stress</div>
              {analyticsLoading ? (
                 <div className="h-4 w-20 bg-slate-800 rounded animate-pulse"></div>
              ) : (
                 <div className="text-xs font-semibold text-slate-200">{analytics?.cross_intelligence?.stress?.replace(/_/g, ' ') || 'UNAVAILABLE'}</div>
              )}
            </div>
          </div>
        </div>

        {/* Data Quality */}
        <div className="p-4 border-b border-slate-800/50 bg-slate-950/30">
          <div className="flex items-center gap-1.5 mb-2 text-[10px] uppercase tracking-widest text-slate-500 font-medium">
            <ShieldCheck className="w-3.5 h-3.5" />
            Data Quality & Provenance
          </div>
          {analyticsLoading ? (
            <div className="space-y-2 animate-pulse">
               <div className="h-3 w-3/4 bg-slate-800 rounded"></div>
               <div className="h-3 w-1/2 bg-slate-800 rounded"></div>
            </div>
          ) : analytics?.data_quality ? (
            <div className="grid grid-cols-2 gap-2 text-xs">
              <MetaRow label="Valid Obs." value={String(analytics.data_quality.valid_observation_count || 0)} />
              <MetaRow label="Excluded (Quality)" value={String(analytics.data_quality.invalid_observation_count || 0)} />
              <MetaRow label="Handling" value="Strict chronological sequence" />
              <MetaRow label="Provenance" value="Deterministic Analytics" />
            </div>
          ) : (
            <div className="text-xs text-slate-500 italic">Quality metrics unavailable</div>
          )}
        </div>

        {/* Chart Section */}
        <div className="p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="text-[10px] uppercase tracking-widest text-slate-500 font-medium">
              {historyLabel}
            </div>
            <div className="text-[9px] text-slate-600">{yAxisLabel}</div>
          </div>

          {loading ? (
            <div className="h-52 flex items-center justify-center text-slate-600 text-xs">{loadingLabel}</div>
          ) : error ? (
            <div className="h-52 flex items-center justify-center text-red-400 text-xs" role="alert">{error}</div>
          ) : data.length === 0 ? (
            <div className="h-52 flex items-center justify-center text-slate-600 text-xs">{emptyLabel}</div>
          ) : (
            <div className="h-52 w-full">
              <ReactECharts
                option={chartOptions}
                style={{ height: '100%', width: '100%' }}
                notMerge={true}
              />
            </div>
          )}

          {/* Data count */}
          {data.length > 0 && !loading && (
            <div className="text-[9px] text-slate-600 mt-1 text-right">
              {data.length} observation{data.length !== 1 ? 's' : ''}
            </div>
          )}
        </div>
          </>
        ) : activeTab === 'analytics' ? (
          <div className="p-4">
            <AdvancedAnalytics site={site} dataset={dataset} />
          </div>
        ) : (
          <div className="p-4 text-xs text-slate-300 leading-relaxed space-y-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-200 mb-1">Data Sources</h3>
              <ul className="list-disc pl-4 space-y-1 text-slate-400">
                <li><strong className="text-slate-300">India:</strong> Historical/periodic groundwater observations.</li>
                <li><strong className="text-slate-300">Maharashtra:</strong> Higher-frequency DWLR telemetry.</li>
                <li><strong className="text-slate-300">Weather:</strong> ERA5-based historical weather used in experimental weather ML.</li>
              </ul>
            </div>
            
            <div className="pt-2 border-t border-slate-800">
              <h3 className="text-sm font-semibold text-slate-200 mb-1">Important Limitations</h3>
              <ul className="list-disc pl-4 space-y-2 text-slate-400">
                <li>India water-level unit is strictly unknown (no assumptions made).</li>
                <li>Reference datum (e.g., surface vs MSL) is unknown across all records.</li>
                <li>India observations are highly periodic; do not imply telemetry.</li>
                <li>Maharashtra operational forecast is persistence-based.</li>
                <li>Weather ML is highly experimental.</li>
                <li><strong className="text-slate-300">Flood potential is not confirmed physical flooding</strong>, only groundwater saturation capability.</li>
                <li><strong className="text-slate-300">Drought intelligence is project-defined</strong>; it is NOT an official administrative drought declaration.</li>
                <li><strong className="text-slate-300">Stress is not official scarcity</strong>; there is no demand-side groundwater consumption dataset available.</li>
                <li>Statistical alerts are causal anomaly flags, not emergency warnings.</li>
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
