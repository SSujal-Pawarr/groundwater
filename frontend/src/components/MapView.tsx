import { useMemo, useCallback, useRef, useState } from 'react';
import Map, { Source, Layer } from 'react-map-gl/maplibre';
import type { MapRef } from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';
import type { CandidateSite } from '../services/api';
import { Layers } from 'lucide-react';

export type MapLayerType = 'condition' | 'alert' | 'drought' | 'flood' | 'stress';

interface MapViewProps {
  sites: CandidateSite[];
  dataset: 'india' | 'maharashtra';
  selectedSiteId: string | null;
  onSiteSelect: (site: CandidateSite) => void;
  onBoundsChange: (bounds: { min_lat: number; max_lat: number; min_lng: number; max_lng: number }) => void;
}

// Carto dark-matter for a proper command-center aesthetic
const CARTO_DARK_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';

export const INDIA_CONDITION_COLORS = {
  EXTREMELY_LOW: '#dc2626',      // deep red
  LOW: '#f97316',                // orange
  NORMAL_RANGE: '#16a34a',       // green
  HIGH: '#2563eb',               // blue
  EXTREMELY_HIGH: '#9333ea',     // purple
  INSUFFICIENT_HISTORY: '#6b7280',// neutral gray
  DEFAULT: '#6b7280'
} as const;

export const MH_ALERT_COLORS = {
  NORMAL: '#16a34a',                        // green
  WATCH: '#eab308',                         // yellow
  WARNING: '#f97316',                       // orange
  CRITICAL_STATISTICAL_DEVIATION: '#dc2626', // red
  DATA_QUALITY_EVENT: '#6b7280',            // neutral gray
  INSUFFICIENT_HISTORY: '#6b7280',          // neutral gray
  SEQUENCE_GAPPED: '#6b7280',               // neutral gray
  DEFAULT: '#6b7280'
} as const;

const DROUGHT_COLORS = {
  NORMAL_TO_WET: '#16a34a',
  WATCH_DEFICIT: '#eab308',
  MODERATE_DEFICIT: '#f97316',
  SEVERE_DEFICIT: '#dc2626',
  INSUFFICIENT_HISTORY: '#6b7280',
  DEFAULT: '#6b7280'
} as const;

const FLOOD_COLORS = {
  LOW: '#16a34a',
  WATCH: '#eab308',
  ELEVATED: '#f97316',
  HIGH: '#dc2626',
  INSUFFICIENT_EVIDENCE: '#6b7280',
  DEFAULT: '#6b7280'
} as const;

const STRESS_COLORS = {
  NORMAL: '#16a34a',
  WATCH: '#eab308',
  MODERATE_STRESS: '#f97316',
  SEVERE_STRESS: '#dc2626',
  INSUFFICIENT_EVIDENCE: '#6b7280',
  DEFAULT: '#6b7280'
} as const;

const INDIA_COLOR_EXPRESSION: any = [
  'match',
  ['coalesce', ['get', 'condition_state'], 'INSUFFICIENT_HISTORY'],
  'EXTREMELY_LOW', INDIA_CONDITION_COLORS.EXTREMELY_LOW,
  'LOW', INDIA_CONDITION_COLORS.LOW,
  'NORMAL_RANGE', INDIA_CONDITION_COLORS.NORMAL_RANGE,
  'HIGH', INDIA_CONDITION_COLORS.HIGH,
  'EXTREMELY_HIGH', INDIA_CONDITION_COLORS.EXTREMELY_HIGH,
  'INSUFFICIENT_HISTORY', INDIA_CONDITION_COLORS.INSUFFICIENT_HISTORY,
  INDIA_CONDITION_COLORS.DEFAULT
];

const MH_COLOR_EXPRESSION: any = [
  'match',
  ['coalesce', ['get', 'alert_event_state'], 'INSUFFICIENT_HISTORY'],
  'NORMAL', MH_ALERT_COLORS.NORMAL,
  'WATCH', MH_ALERT_COLORS.WATCH,
  'WARNING', MH_ALERT_COLORS.WARNING,
  'CRITICAL_STATISTICAL_DEVIATION', MH_ALERT_COLORS.CRITICAL_STATISTICAL_DEVIATION,
  'DATA_QUALITY_EVENT', MH_ALERT_COLORS.DATA_QUALITY_EVENT,
  'INSUFFICIENT_HISTORY', MH_ALERT_COLORS.INSUFFICIENT_HISTORY,
  'SEQUENCE_GAPPED', MH_ALERT_COLORS.SEQUENCE_GAPPED,
  MH_ALERT_COLORS.DEFAULT
];

const DROUGHT_EXPRESSION: any = [
  'match',
  ['coalesce', ['get', 'drought_state'], 'INSUFFICIENT_HISTORY'],
  'NORMAL_TO_WET', DROUGHT_COLORS.NORMAL_TO_WET,
  'WATCH_DEFICIT', DROUGHT_COLORS.WATCH_DEFICIT,
  'MODERATE_DEFICIT', DROUGHT_COLORS.MODERATE_DEFICIT,
  'SEVERE_DEFICIT', DROUGHT_COLORS.SEVERE_DEFICIT,
  'INSUFFICIENT_HISTORY', DROUGHT_COLORS.INSUFFICIENT_HISTORY,
  DROUGHT_COLORS.DEFAULT
];

const FLOOD_EXPRESSION: any = [
  'match',
  ['coalesce', ['get', 'flood_potential_state'], 'INSUFFICIENT_EVIDENCE'],
  'LOW', FLOOD_COLORS.LOW,
  'WATCH', FLOOD_COLORS.WATCH,
  'ELEVATED', FLOOD_COLORS.ELEVATED,
  'HIGH', FLOOD_COLORS.HIGH,
  'INSUFFICIENT_EVIDENCE', FLOOD_COLORS.INSUFFICIENT_EVIDENCE,
  FLOOD_COLORS.DEFAULT
];

const STRESS_EXPRESSION: any = [
  'match',
  ['coalesce', ['get', 'stress_state'], 'INSUFFICIENT_EVIDENCE'],
  'NORMAL', STRESS_COLORS.NORMAL,
  'WATCH', STRESS_COLORS.WATCH,
  'MODERATE_STRESS', STRESS_COLORS.MODERATE_STRESS,
  'SEVERE_STRESS', STRESS_COLORS.SEVERE_STRESS,
  'INSUFFICIENT_EVIDENCE', STRESS_COLORS.INSUFFICIENT_EVIDENCE,
  STRESS_COLORS.DEFAULT
];

const INDIA_LEGEND_ITEMS = [
  { label: 'Extremely Low', color: INDIA_CONDITION_COLORS.EXTREMELY_LOW, state: 'EXTREMELY_LOW' },
  { label: 'Low', color: INDIA_CONDITION_COLORS.LOW, state: 'LOW' },
  { label: 'Normal Range', color: INDIA_CONDITION_COLORS.NORMAL_RANGE, state: 'NORMAL_RANGE' },
  { label: 'High', color: INDIA_CONDITION_COLORS.HIGH, state: 'HIGH' },
  { label: 'Extremely High', color: INDIA_CONDITION_COLORS.EXTREMELY_HIGH, state: 'EXTREMELY_HIGH' },
  { label: 'Insufficient History', color: INDIA_CONDITION_COLORS.INSUFFICIENT_HISTORY, state: 'INSUFFICIENT_HISTORY' },
];

const MH_LEGEND_ITEMS = [
  { label: 'Normal', color: MH_ALERT_COLORS.NORMAL, state: 'NORMAL' },
  { label: 'Watch', color: MH_ALERT_COLORS.WATCH, state: 'WATCH' },
  { label: 'Warning', color: MH_ALERT_COLORS.WARNING, state: 'WARNING' },
  { label: 'Critical Statistical Deviation', color: MH_ALERT_COLORS.CRITICAL_STATISTICAL_DEVIATION, state: 'CRITICAL_STATISTICAL_DEVIATION' },
  { label: 'Data Quality / Insufficient History / Sequence Gapped', color: MH_ALERT_COLORS.DATA_QUALITY_EVENT, state: 'DATA_QUALITY_EVENT' },
];

const DROUGHT_LEGEND = [
  { label: 'Normal to Wet', color: DROUGHT_COLORS.NORMAL_TO_WET },
  { label: 'Watch Deficit', color: DROUGHT_COLORS.WATCH_DEFICIT },
  { label: 'Moderate Deficit', color: DROUGHT_COLORS.MODERATE_DEFICIT },
  { label: 'Severe Deficit', color: DROUGHT_COLORS.SEVERE_DEFICIT },
  { label: 'Insufficient History', color: DROUGHT_COLORS.INSUFFICIENT_HISTORY },
];

const FLOOD_LEGEND = [
  { label: 'Low', color: FLOOD_COLORS.LOW },
  { label: 'Watch', color: FLOOD_COLORS.WATCH },
  { label: 'Elevated', color: FLOOD_COLORS.ELEVATED },
  { label: 'High', color: FLOOD_COLORS.HIGH },
  { label: 'Insufficient Evidence', color: FLOOD_COLORS.INSUFFICIENT_EVIDENCE },
];

const STRESS_LEGEND = [
  { label: 'Normal', color: STRESS_COLORS.NORMAL },
  { label: 'Watch', color: STRESS_COLORS.WATCH },
  { label: 'Moderate Stress', color: STRESS_COLORS.MODERATE_STRESS },
  { label: 'Severe Stress', color: STRESS_COLORS.SEVERE_STRESS },
  { label: 'Insufficient Evidence', color: STRESS_COLORS.INSUFFICIENT_EVIDENCE },
];

export const MapView: React.FC<MapViewProps> = ({ sites, dataset, onSiteSelect, onBoundsChange, selectedSiteId }) => {
  const mapRef = useRef<MapRef>(null);
  const [activeLayer, setActiveLayer] = useState<MapLayerType>('condition');
  const [isLayerMenuOpen, setIsLayerMenuOpen] = useState(false);

  const handleMoveEnd = useCallback(() => {
    if (mapRef.current) {
      const bounds = mapRef.current.getMap().getBounds();
      onBoundsChange({
        min_lat: bounds.getSouth(),
        max_lat: bounds.getNorth(),
        min_lng: bounds.getWest(),
        max_lng: bounds.getEast()
      });
    }
  }, [onBoundsChange]);

  // Build GeoJSON — invalid coords filtered
  const geojson = useMemo(() => ({
    type: 'FeatureCollection' as const,
    features: sites
      .filter(s => s.latitude != null && s.longitude != null && s.latitude !== 0 && s.longitude !== 0)
      .map(site => ({
        type: 'Feature' as const,
        geometry: { type: 'Point' as const, coordinates: [site.longitude!, site.latitude!] },
        properties: { id: site.candidate_site_id, selected: site.candidate_site_id === selectedSiteId, ...site }
      }))
  }), [sites, selectedSiteId]);

  const onClick = useCallback((event: any) => {
    const feature = event.features?.[0];
    if (feature?.layer.id === 'unclustered-point') {
      onSiteSelect(feature.properties as CandidateSite);
    }
  }, [onSiteSelect]);

  const onMouseEnter = useCallback(() => {
    if (mapRef.current) mapRef.current.getMap().getCanvas().style.cursor = 'pointer';
  }, []);

  const onMouseLeave = useCallback(() => {
    if (mapRef.current) mapRef.current.getMap().getCanvas().style.cursor = '';
  }, []);

  const getActiveExpression = () => {
    switch (activeLayer) {
      case 'alert': return MH_COLOR_EXPRESSION;
      case 'drought': return DROUGHT_EXPRESSION;
      case 'flood': return FLOOD_EXPRESSION;
      case 'stress': return STRESS_EXPRESSION;
      case 'condition':
      default:
        return dataset === 'india' ? INDIA_COLOR_EXPRESSION : MH_COLOR_EXPRESSION;
    }
  };

  const getActiveLegend = () => {
    switch (activeLayer) {
      case 'alert': return { title: 'STATISTICAL ALERT', items: MH_LEGEND_ITEMS };
      case 'drought': return { title: 'DROUGHT INTELLIGENCE', items: DROUGHT_LEGEND };
      case 'flood': return { title: 'FLOOD POTENTIAL', items: FLOOD_LEGEND };
      case 'stress': return { title: 'GROUNDWATER STRESS', items: STRESS_LEGEND };
      case 'condition':
      default:
        return dataset === 'india' 
          ? { title: 'GROUNDWATER CONDITION', items: INDIA_LEGEND_ITEMS }
          : { title: 'STATISTICAL ALERT', items: MH_LEGEND_ITEMS };
    }
  };

  const legend = getActiveLegend();

  return (
    <div className="w-full h-full relative">
      <Map
        ref={mapRef}
        initialViewState={{ longitude: 79.0, latitude: 21.0, zoom: 4 }}
        mapStyle={CARTO_DARK_STYLE}
        interactiveLayerIds={['unclustered-point']}
        onClick={onClick}
        onMouseEnter={onMouseEnter}
        onMouseLeave={onMouseLeave}
        onMoveEnd={handleMoveEnd}
      >
        <Source
          id="sites"
          type="geojson"
          data={geojson}
          cluster={true}
          clusterMaxZoom={14}
          clusterRadius={50}
        >
          {/* Cluster circles - strictly neutral blue */}
          <Layer
            id="clusters"
            type="circle"
            filter={['has', 'point_count']}
            paint={{
              'circle-color': [
                'step', ['get', 'point_count'],
                '#334155',   // < 10
                10, '#1e40af',  // 10–99
                100, '#1d4ed8', // 100+
              ],
              'circle-radius': ['step', ['get', 'point_count'], 16, 100, 24, 750, 34],
              'circle-opacity': 0.85,
              'circle-stroke-width': 1,
              'circle-stroke-color': '#475569'
            }}
          />
          {/* Cluster count labels */}
          <Layer
            id="cluster-count"
            type="symbol"
            filter={['has', 'point_count']}
            layout={{
              'text-field': '{point_count_abbreviated}',
              'text-size': 11,
              'text-font': ['Noto Sans Regular']
            }}
            paint={{ 'text-color': '#cbd5e1' }}
          />
          {/* Selected marker halo */}
          <Layer
            id="selected-halo"
            type="circle"
            filter={['all', ['!', ['has', 'point_count']], ['==', ['get', 'selected'], true]]}
            paint={{
              'circle-color': 'transparent',
              'circle-radius': 12,
              'circle-stroke-width': 2,
              'circle-stroke-color': '#60a5fa'
            }}
          />
          {/* Unclustered individual points - state colored */}
          <Layer
            id="unclustered-point"
            type="circle"
            filter={['!', ['has', 'point_count']]}
            paint={{
              'circle-color': getActiveExpression(),
              'circle-radius': ['case', ['==', ['get', 'selected'], true], 7, 5],
              'circle-stroke-width': ['case', ['==', ['get', 'selected'], true], 2, 1],
              'circle-stroke-color': ['case', ['==', ['get', 'selected'], true], '#ffffff', 'rgba(255,255,255,0.6)']
            }}
          />
        </Source>
      </Map>

      {/* Map Layer Control */}
      <div className="absolute top-4 right-4 z-10 pointer-events-auto">
        <div className="relative">
          <button 
            onClick={() => setIsLayerMenuOpen(!isLayerMenuOpen)}
            className="flex items-center gap-2 bg-slate-900/90 backdrop-blur-md border border-slate-800 px-3 py-2 rounded-lg shadow-xl text-xs font-medium text-slate-200 hover:bg-slate-800 transition-colors focus:outline-none"
          >
            <Layers className="w-4 h-4 text-blue-400" />
            <span>Map Layer</span>
          </button>
          
          {isLayerMenuOpen && (
            <div className="absolute top-full right-0 mt-2 w-56 bg-slate-900 border border-slate-700 rounded-lg shadow-2xl py-1 overflow-hidden">
              <div className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500 bg-slate-950/50">
                Intelligence Layers
              </div>
              <button
                onClick={() => { setActiveLayer('condition'); setIsLayerMenuOpen(false); }}
                className={`w-full text-left px-3 py-2 text-xs hover:bg-slate-800 transition-colors ${activeLayer === 'condition' ? 'text-blue-400 bg-blue-900/10' : 'text-slate-300'}`}
              >
                Groundwater Condition
              </button>
              <button
                onClick={() => { setActiveLayer('alert'); setIsLayerMenuOpen(false); }}
                className={`w-full text-left px-3 py-2 text-xs hover:bg-slate-800 transition-colors ${activeLayer === 'alert' ? 'text-blue-400 bg-blue-900/10' : 'text-slate-300'}`}
              >
                Statistical Alerts
              </button>
              <button
                onClick={() => { setActiveLayer('drought'); setIsLayerMenuOpen(false); }}
                className={`w-full text-left px-3 py-2 text-xs hover:bg-slate-800 transition-colors ${activeLayer === 'drought' ? 'text-blue-400 bg-blue-900/10' : 'text-slate-300'}`}
              >
                Drought Intelligence
              </button>
              <button
                onClick={() => { setActiveLayer('flood'); setIsLayerMenuOpen(false); }}
                className={`w-full text-left px-3 py-2 text-xs hover:bg-slate-800 transition-colors ${activeLayer === 'flood' ? 'text-blue-400 bg-blue-900/10' : 'text-slate-300'}`}
              >
                Flood Potential
              </button>
              <button
                onClick={() => { setActiveLayer('stress'); setIsLayerMenuOpen(false); }}
                className={`w-full text-left px-3 py-2 text-xs hover:bg-slate-800 transition-colors ${activeLayer === 'stress' ? 'text-blue-400 bg-blue-900/10' : 'text-slate-300'}`}
              >
                Groundwater Stress
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Map Legend */}
      <div 
        className="absolute bottom-6 left-4 z-10 bg-slate-900/90 backdrop-blur-md border border-slate-800 p-2.5 rounded-lg shadow-xl text-xs max-w-xs pointer-events-auto"
        data-testid="map-legend"
      >
        <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
          {legend.title}
        </div>
        <div className="space-y-1.5">
          {legend.items.map(item => (
            <div key={item.label} className="flex items-center gap-2">
              <span
                className="w-2.5 h-2.5 rounded-full shrink-0"
                style={{ backgroundColor: item.color }}
                aria-hidden="true"
              />
              <span className="text-[11px] text-slate-300 leading-tight">
                {item.label}
              </span>
            </div>
          ))}
        </div>
      </div>
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 bg-slate-900/80 backdrop-blur-sm border border-slate-700/50 px-3 py-1 text-[9px] text-slate-500 rounded-full pointer-events-none">
        Candidate site coordinates are historically unverified and may exhibit geospatial artifacts.
      </div>
    </div>
  );
};

