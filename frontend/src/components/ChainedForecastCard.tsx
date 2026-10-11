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
    <div className="p-4 border-b border-slate-800/50" data-testid="chained-forecast-card">
      <div className="text-[10px] uppercase tracking-widest text-amber-500/80 mb-2 font-medium">
        Rough Estimate to Target Date (no recent data)
      </div>
      {loading ? (
        <div className="animate-pulse h-6 w-32 bg-slate-800 rounded"></div>
      ) : error ? (
        <div className="text-slate-500 text-xs italic">{error}</div>
      ) : !data ? (
        <div className="text-slate-500 text-xs italic">No rough estimate for this site (last reading too far back)</div>
      ) : (
        <div className="flex flex-col gap-3">
          <div>
            <div className="flex items-baseline gap-2 flex-wrap">
              <span className="font-mono text-lg font-bold text-slate-100">{data.predicted_water_level.toFixed(2)}</span>
              <span className="text-slate-500 text-xs">{data.water_level_unit}</span>
              <span className="text-xs text-amber-400 font-medium">for {data.predicted_for_date}</span>
            </div>
            {data.predicted_lower_80 != null && data.predicted_upper_80 != null && (
              <div className="text-xs text-slate-400 mt-0.5">
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
              className="px-2 py-0.5 rounded font-semibold tracking-wide"
              style={{ color: STATE_COLORS[data.predicted_condition_state] ?? '#94a3b8', border: `1px solid ${(STATE_COLORS[data.predicted_condition_state] ?? '#94a3b8')}50` }}
              aria-label={`Estimated condition state: ${label(data.predicted_condition_state)}`}
            >
              {label(data.predicted_condition_state)}
            </span>
          </div>

          <div className="text-[11px] text-slate-400" data-testid="chain-method">
            Method: {data.method === 'persistence_fallback' ? 'last known level (chained model showed no skill in backtest)' : 'chained XGBoost'}
          </div>

          {data.warnings.length > 0 && (
            <ul className="text-[10px] text-amber-500/90 leading-relaxed list-disc pl-4" data-testid="chain-warnings">
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
