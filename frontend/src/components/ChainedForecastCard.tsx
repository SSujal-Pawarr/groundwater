import { useEffect, useState } from 'react';
import { fetchChainedForecast } from '../services/api';
import type { ChainedForecast } from '../services/api';

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

export function ChainedForecastCard({ siteId, dataset }: Props) {
  const [data, setData] = useState<ChainedForecast | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    setData(null);
    fetchChainedForecast(siteId, dataset)
      .then((d) => { if (mounted) setData(d); })
      .catch(() => { if (mounted) setError('Estimate unavailable'); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [siteId, dataset]);

  return (
    <div className="border-b border-slate-200 py-4" data-testid="chained-forecast-card">
      <div className="mb-2 text-[10px] font-medium uppercase text-emerald-800">
        Rough Estimate to Target Date (no recent data)
      </div>
      {loading ? (
        <div className="h-6 w-32 animate-pulse bg-slate-200"></div>
      ) : error ? (
        <div className="text-slate-500 text-xs italic">{error}</div>
      ) : !data ? (
        <div className="text-slate-500 text-xs italic">No rough estimate for this site (last reading too far back)</div>
      ) : (
        <div className="flex flex-col gap-3">
          <div>
            <div className="flex items-baseline gap-2 flex-wrap">
              <span className="font-mono text-lg font-bold text-slate-800">{data.predicted_water_level.toFixed(2)}</span>
              <span className="text-slate-500 text-xs">{data.water_level_unit}</span>
              <span className="text-xs text-amber-400 font-medium">for {data.predicted_for_date}</span>
            </div>
            {data.predicted_lower_80 != null && data.predicted_upper_80 != null && (
              <div className="mt-0.5 text-xs text-slate-600">
                80% range {data.predicted_lower_80.toFixed(2)} to {data.predicted_upper_80.toFixed(2)}
                {data.interval_basis.startsWith('extrapolated') ? ' (extrapolated, wider than measured)' : ''}
              </div>
            )}
            <div className="text-xs text-slate-500 mt-0.5">
              Rolled forward {data.n_steps} × {data.step_months} month(s) from the last reading on {data.origin_date}
              ({data.origin_water_level.toFixed(2)}); data ends {data.data_through}.
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="text-slate-500">Estimated state</span>
            <span
              className="border border-emerald-600 px-2 py-0.5 font-semibold"
              style={{ color: STATE_COLORS[data.predicted_condition_state] ?? '#94a3b8', border: `1px solid ${(STATE_COLORS[data.predicted_condition_state] ?? '#94a3b8')}50` }}
              aria-label={`Estimated condition state: ${label(data.predicted_condition_state)}`}
            >
              {label(data.predicted_condition_state)}
            </span>
          </div>

          <div className="text-[11px] text-slate-600" data-testid="chain-method">
            Method: {data.method === 'persistence_fallback' ? 'last known level (chained model showed no skill in backtest)' : 'chained XGBoost'}
          </div>

          {data.warnings.length > 0 && (
            <ul className="list-disc pl-4 text-[10px] leading-relaxed text-emerald-800" data-testid="chain-warnings">
              {data.warnings.map((w) => <li key={w}>{w}</li>)}
            </ul>
          )}
          <p className="text-[10px] text-slate-500 leading-relaxed">
            ESTIMATED WITHOUT RECENT DATA — built from past patterns only; uncertainty grows with every step.
          </p>
        </div>
      )}
    </div>
  );
}
