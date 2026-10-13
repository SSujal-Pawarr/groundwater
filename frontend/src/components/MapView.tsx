import { useMemo, useCallback, useRef, useState, useEffect } from 'react';
import Map, { Source, Layer, NavigationControl } from 'react-map-gl/maplibre';
import type { MapRef } from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';
import type { CandidateSite } from '../services/api';
import { Layers, ZoomIn, ZoomOut, RotateCcw, MapPin, Crosshair, Globe } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export type MapLayerType = 'condition' | 'alert' | 'drought' | 'flood' | 'stress';

interface MapViewProps {
  sites: CandidateSite[];
  dataset: 'india' | 'maharashtra';
  selectedSiteId: string | null;
  selectedSite?: CandidateSite | null;
  onSiteSelect: (site: CandidateSite) => void;
  onBoundsChange: (bounds: { min_lat: number; max_lat: number; min_lng: number; max_lng: number }) => void;
}

const CARTO_DARK_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';
const CARTO_LIGHT_STYLE = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json';

export const MAHARASHTRA_DISTRICTS = [
  { name: 'All Maharashtra', coords: [75.71, 19.75] as [number, number], zoom: 6.8 },
  { name: 'Ahmednagar (Ahilyanagar)', coords: [74.7496, 19.0948] as [number, number], zoom: 9.5 },
  { name: 'Akola', coords: [77.0082, 20.7002] as [number, number], zoom: 10 },
  { name: 'Amravati', coords: [77.7523, 20.9374] as [number, number], zoom: 10 },
  { name: 'Chhatrapati Sambhajinagar', coords: [75.3433, 19.8762] as [number, number], zoom: 10 },
  { name: 'Beed', coords: [75.7554, 18.9891] as [number, number], zoom: 10 },
  { name: 'Bhandara', coords: [79.6545, 21.1681] as [number, number], zoom: 10 },
  { name: 'Buldhana', coords: [76.1804, 20.5292] as [number, number], zoom: 10 },
  { name: 'Chandrapur', coords: [79.2961, 19.9615] as [number, number], zoom: 10 },
  { name: 'Dhule', coords: [74.7749, 20.9042] as [number, number], zoom: 10 },
  { name: 'Gadchiroli', coords: [80.0039, 20.1809] as [number, number], zoom: 9.5 },
  { name: 'Gondia', coords: [80.1961, 21.4598] as [number, number], zoom: 10 },
  { name: 'Hingoli', coords: [77.1408, 19.7173] as [number, number], zoom: 10 },
  { name: 'Jalgaon', coords: [75.5626, 21.0077] as [number, number], zoom: 10 },
  { name: 'Jalna', coords: [75.8830, 19.8410] as [number, number], zoom: 10 },
  { name: 'Kolhapur', coords: [74.2433, 16.7050] as [number, number], zoom: 10 },
  { name: 'Latur', coords: [76.5604, 18.4088] as [number, number], zoom: 10 },
  { name: 'Mumbai City & Suburban', coords: [72.8777, 19.0760] as [number, number], zoom: 10.5 },
  { name: 'Nagpur', coords: [79.0882, 21.1458] as [number, number], zoom: 10 },
  { name: 'Nanded', coords: [77.3197, 19.1383] as [number, number], zoom: 10 },
  { name: 'Nandurbar', coords: [74.2372, 21.3688] as [number, number], zoom: 10 },
  { name: 'Nashik', coords: [73.7898, 19.9975] as [number, number], zoom: 10 },
  { name: 'Dharashiv (Osmanabad)', coords: [76.0423, 18.1861] as [number, number], zoom: 10 },
  { name: 'Palghar', coords: [72.7689, 19.6967] as [number, number], zoom: 10 },
  { name: 'Parbhani', coords: [76.7748, 19.2610] as [number, number], zoom: 10 },
  { name: 'Pune', coords: [73.8567, 18.5204] as [number, number], zoom: 10 },
  { name: 'Raigad', coords: [73.1812, 18.5158] as [number, number], zoom: 10 },
  { name: 'Ratnagiri', coords: [73.3120, 16.9902] as [number, number], zoom: 10 },
  { name: 'Sangli', coords: [74.5815, 16.8524] as [number, number], zoom: 10 },
  { name: 'Satara', coords: [73.9903, 17.6805] as [number, number], zoom: 10 },
  { name: 'Sindhudurg', coords: [73.7142, 16.1158] as [number, number], zoom: 10 },
  { name: 'Solapur', coords: [75.9064, 17.6599] as [number, number], zoom: 10 },
  { name: 'Thane', coords: [72.9781, 19.2183] as [number, number], zoom: 10 },
  { name: 'Wardha', coords: [78.6022, 20.7453] as [number, number], zoom: 10 },
  { name: 'Washim', coords: [77.1352, 20.1118] as [number, number], zoom: 10 },
  { name: 'Yavatmal', coords: [78.1232, 20.3888] as [number, number], zoom: 10 },
];

export const INDIA_REGIONS = [
  { name: 'All India View', coords: [78.9629, 20.5937] as [number, number], zoom: 4.2 },
  { name: 'North India (Delhi, Punjab, Haryana, UP)', coords: [77.2090, 28.6139] as [number, number], zoom: 6.2 },
  { name: 'West India (Maharashtra, Gujarat, Rajasthan)', coords: [74.5000, 21.0000] as [number, number], zoom: 6.2 },
  { name: 'South India (Karnataka, AP, Telangana, TN)', coords: [77.5946, 14.5000] as [number, number], zoom: 6.2 },
  { name: 'East India (Bihar, West Bengal, Odisha)', coords: [85.5000, 23.5000] as [number, number], zoom: 6.2 },
  { name: 'Central India (Madhya Pradesh, Chhattisgarh)', coords: [78.5000, 22.5000] as [number, number], zoom: 6.2 },
];

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

export const MapView: React.FC<MapViewProps> = ({ sites, dataset, onSiteSelect, onBoundsChange, selectedSiteId, selectedSite }) => {
  const mapRef = useRef<MapRef>(null);
  const { isDark } = useTheme();
  const [activeLayer, setActiveLayer] = useState<MapLayerType>('condition');
  const [isLayerMenuOpen, setIsLayerMenuOpen] = useState(false);
  const [selectedDistrict, setSelectedDistrict] = useState<string>('');

  // Initial center depending on dataset
  const initialCenter = useMemo(() => {
    return dataset === 'india' ? { longitude: 79.0, latitude: 21.0, zoom: 4.2 } : { longitude: 75.71, latitude: 19.75, zoom: 6.8 };
  }, [dataset]);

  // Reset district dropdown when dataset flips
  useEffect(() => {
    setSelectedDistrict('');
  }, [dataset]);

  // Smooth camera control helper
  const flyToCoords = useCallback((coords: [number, number], zoom: number) => {
    if (!mapRef.current) return;
    const map = mapRef.current.getMap?.() ?? (mapRef.current as any);
    if (map && typeof map.flyTo === 'function') {
      map.flyTo({
        center: coords,
        zoom,
        duration: 900,
        essential: true,
      });
    }
  }, []);

  const handleZoomIn = useCallback(() => {
    if (!mapRef.current) return;
    const map = mapRef.current.getMap?.() ?? (mapRef.current as any);
    if (map && typeof map.zoomIn === 'function') {
      map.zoomIn({ duration: 300 });
    }
  }, []);

  const handleZoomOut = useCallback(() => {
    if (!mapRef.current) return;
    const map = mapRef.current.getMap?.() ?? (mapRef.current as any);
    if (map && typeof map.zoomOut === 'function') {
      map.zoomOut({ duration: 300 });
    }
  }, []);

  const handleResetView = useCallback(() => {
    setSelectedDistrict('');
    if (dataset === 'india') {
      flyToCoords([78.9629, 20.5937], 4.2);
    } else {
      flyToCoords([75.71, 19.75], 6.8);
    }
  }, [dataset, flyToCoords]);

  const handleDistrictChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    setSelectedDistrict(val);
    if (!val) return;

    if (dataset === 'maharashtra') {
      const match = MAHARASHTRA_DISTRICTS.find(d => d.name === val);
      if (match) flyToCoords(match.coords, match.zoom);
    } else {
      const match = INDIA_REGIONS.find(r => r.name === val);
      if (match) flyToCoords(match.coords, match.zoom);
    }
  }, [dataset, flyToCoords]);

  // Automatically fly to selected site when selectedSite or selectedSiteId changes
  useEffect(() => {
    if (!mapRef.current) return;
    const target = selectedSite || sites.find(s => s.candidate_site_id === selectedSiteId);
    if (target && target.longitude != null && target.latitude != null && target.longitude !== 0 && target.latitude !== 0) {
      try {
        const map = mapRef.current.getMap?.() ?? (mapRef.current as any);
        if (map && typeof map.flyTo === 'function') {
          const currentZoom = typeof map.getZoom === 'function' ? map.getZoom() : 5;
          map.flyTo({
            center: [target.longitude, target.latitude],
            zoom: Math.max(currentZoom, 10.5),
            duration: 1100,
            essential: true
          });
        }
      } catch {
        // Safe guard if map is mounting
      }
    }
  }, [selectedSiteId, selectedSite, sites]);

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

  // Build GeoJSON — invalid coords filtered and selectedSite guaranteed
  const geojson = useMemo(() => {
    const list = [...sites];
    if (selectedSite && !list.some(s => s.candidate_site_id === selectedSite.candidate_site_id)) {
      list.push(selectedSite);
    }
    return {
      type: 'FeatureCollection' as const,
      features: list
        .filter(s => s.latitude != null && s.longitude != null && s.latitude !== 0 && s.longitude !== 0)
        .map(site => ({
          type: 'Feature' as const,
          geometry: { type: 'Point' as const, coordinates: [site.longitude!, site.latitude!] },
          properties: { id: site.candidate_site_id, selected: site.candidate_site_id === selectedSiteId, ...site }
        }))
    };
  }, [sites, selectedSiteId, selectedSite]);

  // Interactive click: cluster expansion or station inspection
  const onClick = useCallback((event: any) => {
    const feature = event.features?.[0];
    if (!feature) return;

    if (feature.layer.id === 'clusters') {
      const clusterId = feature.properties?.cluster_id;
      const map = mapRef.current?.getMap?.() ?? (mapRef.current as any);
      if (!map) return;
      const source = map.getSource('sites') as any;
      if (source && typeof source.getClusterExpansionZoom === 'function') {
        source.getClusterExpansionZoom(clusterId, (err: any, zoom: number) => {
          if (err) return;
          map.easeTo({
            center: feature.geometry.coordinates,
            zoom: Math.min(zoom + 0.6, 15.5),
            duration: 600,
            essential: true
          });
        });
      }
      return;
    }

    if (feature.layer.id === 'unclustered-point') {
      onSiteSelect(feature.properties as CandidateSite);
    }
  }, [onSiteSelect]);

  const onMouseEnter = useCallback(() => {
    if (mapRef.current) {
      const map = mapRef.current.getMap?.() ?? (mapRef.current as any);
      if (map?.getCanvas) map.getCanvas().style.cursor = 'pointer';
    }
  }, []);

  const onMouseLeave = useCallback(() => {
    if (mapRef.current) {
      const map = mapRef.current.getMap?.() ?? (mapRef.current as any);
      if (map?.getCanvas) map.getCanvas().style.cursor = '';
    }
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
    <div className="w-full h-full relative overflow-hidden">
      <Map
        ref={mapRef}
        initialViewState={initialCenter}
        mapStyle={isDark ? CARTO_DARK_STYLE : CARTO_LIGHT_STYLE}
        interactiveLayerIds={['clusters', 'unclustered-point']}
        onClick={onClick}
        onMouseEnter={onMouseEnter}
        onMouseLeave={onMouseLeave}
        onMoveEnd={handleMoveEnd}
        reuseMaps={true}
      >
        <Source
          id="sites"
          type="geojson"
          data={geojson}
          cluster={true}
          clusterMaxZoom={14}
          clusterRadius={50}
        >
          {/* Cluster circles use the dashboard's primary green accent. */}
          <Layer
            id="clusters"
            type="circle"
            filter={['has', 'point_count']}
            paint={{
              'circle-color': [
                'step', ['get', 'point_count'],
                '#059669',
                10, '#047857',
                100, '#065f46',
              ],
              'circle-radius': ['step', ['get', 'point_count'], 16, 100, 24, 750, 34],
              'circle-opacity': 0.9,
              'circle-stroke-width': 1.5,
              'circle-stroke-color': 'rgba(255,255,255,0.4)'
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
            paint={{ 'text-color': '#ffffff' }}
          />
          {/* Selected marker halo */}
          <Layer
            id="selected-halo"
            type="circle"
            filter={['all', ['!', ['has', 'point_count']], ['==', ['get', 'selected'], true]]}
            paint={{
              'circle-color': 'transparent',
              'circle-radius': 14,
              'circle-stroke-width': 2.5,
              'circle-stroke-color': '#10B981'
            }}
          />
          {/* Unclustered individual points - state colored */}
          <Layer
            id="unclustered-point"
            type="circle"
            filter={['!', ['has', 'point_count']]}
            paint={{
              'circle-color': getActiveExpression(),
              'circle-radius': ['case', ['==', ['get', 'selected'], true], 7.5, 5.5],
              'circle-stroke-width': ['case', ['==', ['get', 'selected'], true], 2.5, 1],
              'circle-stroke-color': ['case', ['==', ['get', 'selected'], true], '#ffffff', 'rgba(255,255,255,0.7)']
            }}
          />
        </Source>

        {/* Native Navigation Control with Compass */}
        <NavigationControl position="bottom-right" showCompass={true} visualizePitch={true} />
      </Map>

      {/* ── Floating Fast Zoom & Quick Navigation Toolbar (Top-Left) ── */}
      <div className="absolute top-4 left-4 z-10 pointer-events-auto flex flex-wrap items-center gap-2">
        {/* Quick Zoom Presets */}
        <div className="glass-panel flex items-center gap-1 rounded-xl p-1 shadow-lg">
          <button
            type="button"
            onClick={() => flyToCoords([75.71, 19.75], 6.8)}
            className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-text-primary hover:bg-glass-bg-hover hover:text-emerald-400 transition-all focus:outline-none"
            title="Focus on Maharashtra telemetry view"
          >
            <Crosshair className="h-3.5 w-3.5 text-emerald-400" />
            <span className="hidden sm:inline">Maharashtra</span>
          </button>

          <button
            type="button"
            onClick={() => flyToCoords([78.9629, 20.5937], 4.2)}
            className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-text-primary hover:bg-glass-bg-hover hover:text-blue-400 transition-all focus:outline-none"
            title="Focus on All-India overview"
          >
            <Globe className="h-3.5 w-3.5 text-blue-400" />
            <span className="hidden sm:inline">India</span>
          </button>
        </div>

        {/* District / Regional Quick Jump Dropdown */}
        <div className="glass-panel flex items-center gap-1.5 rounded-xl px-2.5 py-1 shadow-lg">
          <MapPin className="h-3.5 w-3.5 text-amber-400 shrink-0" />
          <select
            value={selectedDistrict}
            onChange={handleDistrictChange}
            className="bg-transparent text-xs font-medium text-text-primary focus:outline-none cursor-pointer py-1 pr-1 max-w-[11rem] sm:max-w-[14rem]"
            aria-label="Quick jump to district or region"
          >
            <option value="" className="bg-surface-raised text-text-primary">
              {dataset === 'maharashtra' ? '⚡ Quick Jump District…' : '⚡ Quick Jump Region…'}
            </option>
            {dataset === 'maharashtra'
              ? MAHARASHTRA_DISTRICTS.map(d => (
                  <option key={d.name} value={d.name} className="bg-surface-raised text-text-primary">
                    {d.name}
                  </option>
                ))
              : INDIA_REGIONS.map(r => (
                  <option key={r.name} value={r.name} className="bg-surface-raised text-text-primary">
                    {r.name}
                  </option>
                ))}
          </select>
        </div>

        {/* Step Zoom (+ / -) & Reset Controls */}
        <div className="glass-panel flex items-center rounded-xl p-1 shadow-lg">
          <button
            type="button"
            onClick={handleZoomIn}
            className="rounded-lg p-1.5 text-text-primary hover:bg-glass-bg-hover hover:text-emerald-400 transition-all focus:outline-none"
            title="Step Zoom In (+)"
            aria-label="Zoom in"
          >
            <ZoomIn className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={handleZoomOut}
            className="rounded-lg p-1.5 text-text-primary hover:bg-glass-bg-hover hover:text-emerald-400 transition-all focus:outline-none"
            title="Step Zoom Out (-)"
            aria-label="Zoom out"
          >
            <ZoomOut className="h-3.5 w-3.5" />
          </button>
          <div className="h-3.5 w-px bg-glass-border mx-0.5" />
          <button
            type="button"
            onClick={handleResetView}
            className="rounded-lg p-1.5 text-text-muted hover:bg-glass-bg-hover hover:text-text-primary transition-all focus:outline-none"
            title="Reset View"
            aria-label="Reset map view"
          >
            <RotateCcw className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* ── Map Layer Control (Top-Right) ── */}
      <div className="absolute top-4 right-4 z-10 pointer-events-auto">
        <div className="relative">
          <button 
            onClick={() => setIsLayerMenuOpen(!isLayerMenuOpen)}
            className="glass-panel flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold text-text-primary hover:bg-glass-bg-hover transition-colors focus-visible:outline-none focus-glow shadow-lg cursor-pointer"
          >
            <Layers className="w-4 h-4 text-emerald-400" />
            <span>Map Layer</span>
          </button>
          
          {isLayerMenuOpen && (
            <div className="absolute top-full right-0 mt-2 w-56 glass-panel rounded-xl py-1 overflow-hidden shadow-2xl">
              <div className="border-b border-glass-border bg-surface-elevated/50 px-3 py-1.5 text-[10px] font-semibold uppercase text-text-muted">
                Intelligence Layers
              </div>
              <button
                onClick={() => { setActiveLayer('condition'); setIsLayerMenuOpen(false); }}
                className={`w-full px-3 py-2 text-left text-xs transition-colors hover:bg-glass-bg-hover ${activeLayer === 'condition' ? 'bg-emerald-500/15 text-emerald-400 font-bold' : 'text-text-secondary'}`}
              >
                Groundwater Condition
              </button>
              <button
                onClick={() => { setActiveLayer('alert'); setIsLayerMenuOpen(false); }}
                className={`w-full px-3 py-2 text-left text-xs transition-colors hover:bg-glass-bg-hover ${activeLayer === 'alert' ? 'bg-emerald-500/15 text-emerald-400 font-bold' : 'text-text-secondary'}`}
              >
                Statistical Alerts
              </button>
              <button
                onClick={() => { setActiveLayer('drought'); setIsLayerMenuOpen(false); }}
                className={`w-full px-3 py-2 text-left text-xs transition-colors hover:bg-glass-bg-hover ${activeLayer === 'drought' ? 'bg-emerald-500/15 text-emerald-400 font-bold' : 'text-text-secondary'}`}
              >
                Drought Intelligence
              </button>
              <button
                onClick={() => { setActiveLayer('flood'); setIsLayerMenuOpen(false); }}
                className={`w-full px-3 py-2 text-left text-xs transition-colors hover:bg-glass-bg-hover ${activeLayer === 'flood' ? 'bg-emerald-500/15 text-emerald-400 font-bold' : 'text-text-secondary'}`}
              >
                Flood Potential
              </button>
              <button
                onClick={() => { setActiveLayer('stress'); setIsLayerMenuOpen(false); }}
                className={`w-full px-3 py-2 text-left text-xs transition-colors hover:bg-glass-bg-hover ${activeLayer === 'stress' ? 'bg-emerald-500/15 text-emerald-400 font-bold' : 'text-text-secondary'}`}
              >
                Groundwater Stress
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ── Map Legend (Bottom-Left) ── */}
      <div 
        className="absolute bottom-6 left-4 z-10 max-w-xs glass-panel rounded-xl p-3 text-xs pointer-events-auto shadow-lg"
        data-testid="map-legend"
      >
        <div className="mb-2 text-[10px] font-semibold uppercase text-text-muted">
          {legend.title}
        </div>
        <div className="space-y-1.5">
          {legend.items.map(item => (
            <div key={item.label} className="flex items-center gap-2">
              <span
                className="w-2.5 h-2.5 rounded-full shrink-0 shadow-sm"
                style={{ backgroundColor: item.color, boxShadow: `0 0 4px ${item.color}40` }}
                aria-hidden="true"
              />
              <span className="text-[11px] leading-tight text-text-secondary">
                {item.label}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 glass-panel rounded-lg px-3 py-1 text-[9px] text-text-muted pointer-events-none hidden sm:block">
        Candidate site coordinates are historically unverified and may exhibit geospatial artifacts.
      </div>
    </div>
  );
};
