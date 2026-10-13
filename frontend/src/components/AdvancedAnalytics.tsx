import { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import type { CandidateSite } from '../services/api';
import { DataDiagnosticPopover } from './DataDiagnosticPopover';

interface AnalyticsData {
  candidate_site_id: string;
  region: string;
  observation_summary: any;
  water_level_statistics: any;
  trend: any;
  seasonal: any;
  cross_intelligence: any;
  year_over_year: any;
}

interface Props {
  site: CandidateSite;
  dataset: 'india' | 'maharashtra';
}

const API_BASE = typeof window !== 'undefined'
  ? `${window.location.protocol}//${window.location.hostname}:8000/api/v1`
  : 'http://127.0.0.1:8000/api/v1';

export const AdvancedAnalytics: React.FC<Props> = ({ site, dataset }) => {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [trajectory, setTrajectory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    
    const fetchAnalytics = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const region = dataset === 'india' ? 'india' : 'maharashtra';
        const id = site.candidate_site_id;
        
        const [anRes, trajRes] = await Promise.all([
          fetch(`${API_BASE}/${region}/candidate-sites/${id}/analytics`).then(r => r.json()),
          fetch(`${API_BASE}/${region}/candidate-sites/${id}/percentile-trajectory`).then(r => r.json()),
        ]);
        
        if (!mounted) return;
        
        setData(anRes);
        setTrajectory(trajRes.points || []);
        
      } catch (err) {
        if (mounted) setError('Failed to load advanced analytics.');
      } finally {
        if (mounted) setLoading(false);
      }
    };
    
    fetchAnalytics();
    return () => { mounted = false; };
  }, [site, dataset]);

  if (loading) {
    return <div className="p-4 text-xs text-slate-500 animate-pulse">Loading analytics...</div>;
  }
  if (error) {
    return <div className="p-4 text-xs text-red-400">{error}</div>;
  }

  if (!data || data.observation_summary?.error) {
    return (
      <div className="p-4 space-y-2">
        <div className="text-xs text-slate-500 italic">
          Insufficient historical observations for deep parametric analytics.
        </div>
        <DataDiagnosticPopover
          siteId={site.candidate_site_id}
          stationName={site.station_name}
          metricType="condition"
          sparsePredictionAvailable={true}
        />
      </div>
    );
  }

  // Trajectory chart
  const trajOptions = {
    animation: false,
    tooltip: { trigger: 'axis', backgroundColor: '#ffffff', borderColor: '#cbd5e1', textStyle: { color: '#1e293b', fontSize: 11 } },
    grid: { top: 8, right: 12, bottom: 20, left: 30 },
    xAxis: { type: 'category', data: trajectory.map(t => t.timestamp?.split('T')[0]), axisLabel: { color: '#64748b', fontSize: 9 } },
    yAxis: { type: 'value', min: 0, max: 1, axisLabel: { color: '#64748b', fontSize: 9 } },
    series: [{
      data: trajectory.map(t => t.historical_percentile),
      type: 'line',
      smooth: true,
      showSymbol: false,
      itemStyle: { color: '#047857' },
      areaStyle: { color: 'rgba(4, 120, 87, 0.08)' }
    }]
  };

  return (
    <div className="flex flex-col gap-4">
      
      {/* Site Statistics */}
      <div className="border-y border-slate-200 py-3">
        <div className="text-[10px] uppercase tracking-widest text-slate-500 mb-2 font-medium">Descriptive Stats</div>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div><span className="text-slate-600">Mean:</span> <span className="text-slate-800">{data.water_level_statistics?.mean?.toFixed(2)}</span></div>
          <div><span className="text-slate-600">Median:</span> <span className="text-slate-800">{data.water_level_statistics?.median?.toFixed(2)}</span></div>
          <div><span className="text-slate-600">Min:</span> <span className="text-slate-800">{data.water_level_statistics?.minimum?.toFixed(2)}</span></div>
          <div><span className="text-slate-600">Max:</span> <span className="text-slate-800">{data.water_level_statistics?.maximum?.toFixed(2)}</span></div>
        </div>
      </div>
      
      {/* Trend */}
      {data.trend && (
        <div className="border-b border-slate-200 py-3">
          <div className="text-[10px] uppercase tracking-widest text-slate-500 mb-2 font-medium">Historical Trend</div>
          <div className="text-xs">
            <div><span className="text-slate-600">Direction:</span> <span className="font-semibold text-slate-800">{data.trend.trend_direction}</span></div>
            {data.trend.trend_rate != null && (
              <div><span className="text-slate-600">Rate:</span> <span className="text-slate-800">{data.trend.trend_rate.toFixed(4)} / day</span></div>
            )}
            {data.trend.r_squared != null && (
              <div><span className="text-slate-600">R²:</span> <span className="text-slate-800">{data.trend.r_squared.toFixed(2)}</span></div>
            )}
          </div>
        </div>
      )}

      {/* Trajectory */}
      {trajectory.length > 0 && (
        <div className="border-b border-slate-200 py-3">
          <div className="text-[10px] uppercase tracking-widest text-slate-500 mb-2 font-medium">Percentile Trajectory</div>
          <div className="h-40 w-full">
            <ReactECharts option={trajOptions} style={{ height: '100%', width: '100%' }} notMerge={true} />
          </div>
        </div>
      )}

      {/* Cross Intelligence */}
      {data.cross_intelligence && (
        <div className="border-b border-slate-200 py-3">
          <div className="text-[10px] uppercase tracking-widest text-slate-500 mb-2 font-medium">Cross Intelligence</div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            {Object.entries(data.cross_intelligence).filter(([k]) => k !== 'candidate_site_id').map(([k, v]) => (
              <div key={k}>
                <span className="capitalize text-slate-600">{k.replace(/_/g, ' ')}:</span>{' '}
                <span className="text-slate-800">{String(v)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
};
