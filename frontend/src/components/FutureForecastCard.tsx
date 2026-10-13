import { useEffect, useState } from 'react';
import { fetchFutureForecast } from '../services/api';
import type { FutureForecast } from '../services/api';
import { DataDiagnosticPopover } from './DataDiagnosticPopover';

interface Props {
  siteId: string;
  dataset: 'india' | 'maharashtra';
}

const STATE_COLORS: Record<string, string> = {
  EXTREMELY_LOW: '#ef4444',
  LOW: '#f97316',
  NORMAL_RANGE: '#10b981',
  HIGH: '#3b82f6',
  EXTREMELY_HIGH: '#8b5cf6',
};
const label = (s: string) => s.replace(/_/g, ' ');

export function FutureForecastCard({ siteId, dataset }: Props) {
  const [data, setData] = useState<FutureForecast | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    setData(null);
    fetchFutureForecast(siteId, dataset)
      .then((d) => { if (mounted) setData(d); })
      .catch(() => { if (mounted) setError('Future forecast unavailable'); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [siteId, dataset]);

  const horizonText = (m: number) => (m === 1 ? '1 month' : `${m} months`);
  const isChainedFallback = data?.forecast_source === 'chained_fallback';

  return (
    <div className="border-b border-slate-200 py-4" data-testid="future-forecast-card">
      <div className="text-[10px] uppercase tracking-widest text-slate-500 mb-2 font-medium">
        {isChainedFallback ? 'Recursive Multi-Horizon Estimate' : 'Multi-Horizon Hydrogeological Forecast'}{data ? ` — ${horizonText(data.horizon_months)} ahead` : ''}
      </div>
      {loading ? (
        <div className="animate-pulse flex flex-col gap-2">
          <div className="h-6 w-28 bg-slate-200"></div>
          <div className="mt-1 h-4 w-48 bg-slate-200"></div>
        </div>
      ) : error ? (
        <div className="text-slate-500 text-xs italic">{error}</div>
      ) : !data ? (
        <div className="text-slate-500 text-xs italic">No future forecast for this site</div>
      ) : (
        <div className="flex flex-col gap-3">
          <div>
            <div className="flex items-baseline gap-2">
              <span className="font-mono text-lg font-bold text-slate-800">{data.predicted_water_level.toFixed(2)}</span>
              <span className="text-slate-500 text-xs">{data.water_level_unit}</span>
              <span className="text-xs font-medium text-emerald-800">by {data.predicted_for_date || data.target_date}</span>
            </div>
            <div className="mt-0.5 text-xs text-slate-600">
              {data.predicted_lower_80 != null && data.predicted_upper_80 != null
                ? <>80% range {data.predicted_lower_80.toFixed(2)} to {data.predicted_upper_80.toFixed(2)} · </>
                : null}
              change {data.predicted_change >= 0 ? '+' : ''}{data.predicted_change.toFixed(2)} from {data.origin_water_level.toFixed(2)} (last reading: {data.origin_date})
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="text-slate-500">Predicted state</span>
            <span
              className="border border-emerald-600 px-2 py-0.5 font-semibold"
              style={{ color: STATE_COLORS[data.predicted_condition_state] ?? '#94a3b8', border: `1px solid ${(STATE_COLORS[data.predicted_condition_state] ?? '#94a3b8')}50` }}
              aria-label={`Predicted condition state: ${label(data.predicted_condition_state)}`}
            >
              {label(data.predicted_condition_state)}
            </span>
            {data.predicted_state_confidence != null && (
              <span className="text-slate-500">({(data.predicted_state_confidence * 100).toFixed(0)}% confidence; now {label(data.current_condition_state)})</span>
            )}
          </div>

          {data.predicted_condition_state === 'INSUFFICIENT_HISTORY' ? (
            <div className="space-y-1.5">
              <p className="text-[11px] text-slate-500 leading-relaxed">
                Prior observations for this seasonal window are below standard parametric thresholds. The predicted level above is estimated using available regional harmonics.
              </p>
              <DataDiagnosticPopover
                siteId={siteId}
                metricType="condition"
                sparsePredictionAvailable={true}
              />
            </div>
          ) : (
          <div className="flex flex-col gap-1">
            {Object.entries(data.predicted_condition_probabilities).map(([state, p]) => p == null ? null : (
              <div key={state} className="flex items-center gap-2 text-[10px] text-slate-600">
                <span className="w-28 shrink-0">{label(state)}</span>
                <div className="h-1.5 flex-1 bg-slate-200">
                  <div className="h-1.5" style={{ width: `${Math.round(p * 100)}%`, backgroundColor: STATE_COLORS[state] ?? '#94a3b8' }} />
                </div>
                <span className="w-8 text-right font-mono">{(p * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
          )}

          {isChainedFallback && (
            <div className="border-l-4 border-yellow-600 bg-yellow-50 px-3 py-2 text-[11px] text-yellow-900">
              <p>Direct forecast unavailable for this site; showing the chained fallback. Requested {data.requested_target_date}; estimate step lands on {data.predicted_for_date || data.target_date}.</p>
              {data.forecast_reason && <p className="mt-1">{data.forecast_reason}</p>}
              {data.warnings && data.warnings.length > 0 && (
                <ul className="mt-1 list-disc pl-4">{data.warnings.map(warning => <li key={warning}>{warning}</li>)}</ul>
              )}
            </div>
          )}

          <p className="text-[10px] text-slate-500 leading-relaxed">
            Statistical forecast of the measured water-level value, not a physical or supply guarantee.
            {dataset === 'india' ? ' India water-level unit and datum are not documented in the source data.' : ''}
          </p>
        </div>
      )}
    </div>
  );
}
