import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { describe, test, expect, vi } from 'vitest';
import { MapView, INDIA_CONDITION_COLORS, MH_ALERT_COLORS } from './MapView';
import type { CandidateSite } from '../services/api';

// Mock react-map-gl/maplibre to inspect MapLibre paint expressions and layer properties in JSDOM
vi.mock('react-map-gl/maplibre', () => {
  return {
    default: ({ children }: any) => <div data-testid="maplibre-map">{children}</div>,
    Source: ({ children, id, data, cluster }: any) => (
      <div 
        data-testid={`source-${id}`} 
        data-cluster={String(cluster)} 
        data-geojson={JSON.stringify(data)}
      >
        {children}
      </div>
    ),
    Layer: ({ id, paint, filter }: any) => (
      <div
        data-testid={`layer-${id}`}
        data-paint={JSON.stringify(paint)}
        data-filter={JSON.stringify(filter)}
      />
    ),
  };
});

describe('M8.5-A MapView State Visualization & Legend Tests', () => {
  const dummySites: CandidateSite[] = [
    { candidate_site_id: 'IND_1', latitude: 20.0, longitude: 78.0, condition_state: 'EXTREMELY_LOW' },
    { candidate_site_id: 'IND_2', latitude: 21.0, longitude: 79.0, condition_state: 'LOW' },
    { candidate_site_id: 'IND_3', latitude: 22.0, longitude: 80.0, condition_state: 'NORMAL_RANGE' },
    { candidate_site_id: 'IND_4', latitude: 23.0, longitude: 81.0, condition_state: 'HIGH' },
    { candidate_site_id: 'IND_5', latitude: 24.0, longitude: 82.0, condition_state: 'EXTREMELY_HIGH' },
    { candidate_site_id: 'IND_6', latitude: 25.0, longitude: 83.0, condition_state: 'INSUFFICIENT_HISTORY' },
    { candidate_site_id: 'MH_1', latitude: 19.0, longitude: 74.0, alert_event_state: 'NORMAL' },
    { candidate_site_id: 'MH_2', latitude: 19.5, longitude: 74.5, alert_event_state: 'WATCH' },
    { candidate_site_id: 'MH_3', latitude: 19.8, longitude: 75.0, alert_event_state: 'WARNING' },
    { candidate_site_id: 'MH_4', latitude: 20.1, longitude: 75.5, alert_event_state: 'CRITICAL_STATISTICAL_DEVIATION' },
    { candidate_site_id: 'MH_5', latitude: 20.3, longitude: 76.0, alert_event_state: 'DATA_QUALITY_EVENT' },
    { candidate_site_id: 'MH_6', latitude: 20.5, longitude: 76.5, alert_event_state: 'SEQUENCE_GAPPED' },
  ];

  test('1. India EXTREMELY_LOW marker -> red styling (#dc2626)', () => {
    expect(INDIA_CONDITION_COLORS.EXTREMELY_LOW).toBe('#dc2626');
    const { getByTestId } = render(
      <MapView
        sites={dummySites}
        dataset="india"
        selectedSiteId={null}
        onSiteSelect={() => {}}
        onBoundsChange={() => {}}
      />
    );
    const pointLayer = getByTestId('layer-unclustered-point');
    const paint = JSON.parse(pointLayer.getAttribute('data-paint') || '{}');
    const colorExpr = paint['circle-color'];
    expect(colorExpr).toContain('EXTREMELY_LOW');
    expect(colorExpr).toContain('#dc2626');
  });

  test('2. India LOW marker -> orange styling (#f97316)', () => {
    expect(INDIA_CONDITION_COLORS.LOW).toBe('#f97316');
    const { getByTestId } = render(
      <MapView sites={dummySites} dataset="india" selectedSiteId={null} onSiteSelect={() => {}} onBoundsChange={() => {}} />
    );
    const paint = JSON.parse(getByTestId('layer-unclustered-point').getAttribute('data-paint') || '{}');
    expect(paint['circle-color']).toContain('LOW');
    expect(paint['circle-color']).toContain('#f97316');
  });

  test('3. India NORMAL_RANGE marker -> green styling (#16a34a)', () => {
    expect(INDIA_CONDITION_COLORS.NORMAL_RANGE).toBe('#16a34a');
    const { getByTestId } = render(
      <MapView sites={dummySites} dataset="india" selectedSiteId={null} onSiteSelect={() => {}} onBoundsChange={() => {}} />
    );
    const paint = JSON.parse(getByTestId('layer-unclustered-point').getAttribute('data-paint') || '{}');
    expect(paint['circle-color']).toContain('NORMAL_RANGE');
    expect(paint['circle-color']).toContain('#16a34a');
  });

  test('4. India HIGH marker -> blue styling (#2563eb)', () => {
    expect(INDIA_CONDITION_COLORS.HIGH).toBe('#2563eb');
    const { getByTestId } = render(
      <MapView sites={dummySites} dataset="india" selectedSiteId={null} onSiteSelect={() => {}} onBoundsChange={() => {}} />
    );
    const paint = JSON.parse(getByTestId('layer-unclustered-point').getAttribute('data-paint') || '{}');
    expect(paint['circle-color']).toContain('HIGH');
    expect(paint['circle-color']).toContain('#2563eb');
  });

  test('5. India EXTREMELY_HIGH marker -> purple styling (#9333ea)', () => {
    expect(INDIA_CONDITION_COLORS.EXTREMELY_HIGH).toBe('#9333ea');
    const { getByTestId } = render(
      <MapView sites={dummySites} dataset="india" selectedSiteId={null} onSiteSelect={() => {}} onBoundsChange={() => {}} />
    );
    const paint = JSON.parse(getByTestId('layer-unclustered-point').getAttribute('data-paint') || '{}');
    expect(paint['circle-color']).toContain('EXTREMELY_HIGH');
    expect(paint['circle-color']).toContain('#9333ea');
  });

  test('6. India INSUFFICIENT_HISTORY marker -> neutral gray styling (#6b7280)', () => {
    expect(INDIA_CONDITION_COLORS.INSUFFICIENT_HISTORY).toBe('#6b7280');
    const { getByTestId } = render(
      <MapView sites={dummySites} dataset="india" selectedSiteId={null} onSiteSelect={() => {}} onBoundsChange={() => {}} />
    );
    const paint = JSON.parse(getByTestId('layer-unclustered-point').getAttribute('data-paint') || '{}');
    expect(paint['circle-color']).toContain('INSUFFICIENT_HISTORY');
    expect(paint['circle-color']).toContain('#6b7280');
  });

  test('7. Maharashtra NORMAL -> green styling (#16a34a)', () => {
    expect(MH_ALERT_COLORS.NORMAL).toBe('#16a34a');
    const { getByTestId } = render(
      <MapView sites={dummySites} dataset="maharashtra" selectedSiteId={null} onSiteSelect={() => {}} onBoundsChange={() => {}} />
    );
    const paint = JSON.parse(getByTestId('layer-unclustered-point').getAttribute('data-paint') || '{}');
    expect(paint['circle-color']).toContain('NORMAL');
    expect(paint['circle-color']).toContain('#16a34a');
  });

  test('8. Maharashtra WATCH -> yellow styling (#eab308)', () => {
    expect(MH_ALERT_COLORS.WATCH).toBe('#eab308');
    const { getByTestId } = render(
      <MapView sites={dummySites} dataset="maharashtra" selectedSiteId={null} onSiteSelect={() => {}} onBoundsChange={() => {}} />
    );
    const paint = JSON.parse(getByTestId('layer-unclustered-point').getAttribute('data-paint') || '{}');
    expect(paint['circle-color']).toContain('WATCH');
    expect(paint['circle-color']).toContain('#eab308');
  });

  test('9. Maharashtra WARNING -> orange styling (#f97316)', () => {
    expect(MH_ALERT_COLORS.WARNING).toBe('#f97316');
    const { getByTestId } = render(
      <MapView sites={dummySites} dataset="maharashtra" selectedSiteId={null} onSiteSelect={() => {}} onBoundsChange={() => {}} />
    );
    const paint = JSON.parse(getByTestId('layer-unclustered-point').getAttribute('data-paint') || '{}');
    expect(paint['circle-color']).toContain('WARNING');
    expect(paint['circle-color']).toContain('#f97316');
  });

  test('10. Maharashtra CRITICAL_STATISTICAL_DEVIATION -> red styling (#dc2626)', () => {
    expect(MH_ALERT_COLORS.CRITICAL_STATISTICAL_DEVIATION).toBe('#dc2626');
    const { getByTestId } = render(
      <MapView sites={dummySites} dataset="maharashtra" selectedSiteId={null} onSiteSelect={() => {}} onBoundsChange={() => {}} />
    );
    const paint = JSON.parse(getByTestId('layer-unclustered-point').getAttribute('data-paint') || '{}');
    expect(paint['circle-color']).toContain('CRITICAL_STATISTICAL_DEVIATION');
    expect(paint['circle-color']).toContain('#dc2626');
  });

  test('11. Maharashtra data-quality states -> neutral gray styling (#6b7280)', () => {
    expect(MH_ALERT_COLORS.DATA_QUALITY_EVENT).toBe('#6b7280');
    expect(MH_ALERT_COLORS.INSUFFICIENT_HISTORY).toBe('#6b7280');
    expect(MH_ALERT_COLORS.SEQUENCE_GAPPED).toBe('#6b7280');
    const { getByTestId } = render(
      <MapView sites={dummySites} dataset="maharashtra" selectedSiteId={null} onSiteSelect={() => {}} onBoundsChange={() => {}} />
    );
    const paint = JSON.parse(getByTestId('layer-unclustered-point').getAttribute('data-paint') || '{}');
    expect(paint['circle-color']).toContain('DATA_QUALITY_EVENT');
    expect(paint['circle-color']).toContain('SEQUENCE_GAPPED');
    expect(paint['circle-color']).toContain('#6b7280');
  });

  test('12. Clusters remain neutral emerald (independent of site states)', () => {
    const { getByTestId } = render(
      <MapView sites={dummySites} dataset="india" selectedSiteId={null} onSiteSelect={() => {}} onBoundsChange={() => {}} />
    );
    const clusterLayer = getByTestId('layer-clusters');
    const paint = JSON.parse(clusterLayer.getAttribute('data-paint') || '{}');
    const clusterColor = JSON.stringify(paint['circle-color']);
    // Cluster shades use the dashboard's official green accent.
    expect(clusterColor).toContain('point_count');
    expect(clusterColor).toContain('#166534');
    expect(clusterColor).toContain('#14532d');
    expect(clusterColor).not.toContain('condition_state');
    expect(clusterColor).not.toContain('alert_event_state');
  });

  test('13. Selected marker retains state color + selection halo exists', () => {
    const { getByTestId } = render(
      <MapView sites={dummySites} dataset="india" selectedSiteId="IND_1" onSiteSelect={() => {}} onBoundsChange={() => {}} />
    );
    const haloLayer = getByTestId('layer-selected-halo');
    expect(haloLayer).toBeInTheDocument();
    const haloPaint = JSON.parse(haloLayer.getAttribute('data-paint') || '{}');
    expect(haloPaint['circle-stroke-color']).toBe('#047857');

    // GeoJSON feature properties have selected: true for IND_1
    const source = getByTestId('source-sites');
    const geojson = JSON.parse(source.getAttribute('data-geojson') || '{}');
    const selectedFeature = geojson.features.find((f: any) => f.properties.id === 'IND_1');
    expect(selectedFeature.properties.selected).toBe(true);
    expect(selectedFeature.properties.condition_state).toBe('EXTREMELY_LOW');
  });

  test('14. Correct legend for India', () => {
    render(
      <MapView sites={dummySites} dataset="india" selectedSiteId={null} onSiteSelect={() => {}} onBoundsChange={() => {}} />
    );
    const legend = screen.getByTestId('map-legend');
    expect(legend).toBeInTheDocument();
    expect(screen.getByText('GROUNDWATER CONDITION')).toBeInTheDocument();
    expect(screen.getByText('Extremely Low')).toBeInTheDocument();
    expect(screen.getByText('Low')).toBeInTheDocument();
    expect(screen.getByText('Normal Range')).toBeInTheDocument();
    expect(screen.getByText('High')).toBeInTheDocument();
    expect(screen.getByText('Extremely High')).toBeInTheDocument();
    expect(screen.getByText('Insufficient History')).toBeInTheDocument();
  });

  test('15. Correct legend for Maharashtra', () => {
    render(
      <MapView sites={dummySites} dataset="maharashtra" selectedSiteId={null} onSiteSelect={() => {}} onBoundsChange={() => {}} />
    );
    const legend = screen.getByTestId('map-legend');
    expect(legend).toBeInTheDocument();
    expect(screen.getByText('STATISTICAL ALERT')).toBeInTheDocument();
    expect(screen.getByText('Normal')).toBeInTheDocument();
    expect(screen.getByText('Watch')).toBeInTheDocument();
    expect(screen.getByText('Warning')).toBeInTheDocument();
    expect(screen.getByText('Critical Statistical Deviation')).toBeInTheDocument();
    expect(screen.getByText('Data Quality / Insufficient History / Sequence Gapped')).toBeInTheDocument();
  });

  test('16. No drought/flood/scarcity/water shortage/risk terminology in legends or UI', () => {
    const { container: indiaContainer } = render(
      <MapView sites={dummySites} dataset="india" selectedSiteId={null} onSiteSelect={() => {}} onBoundsChange={() => {}} />
    );
    const indiaText = indiaContainer.textContent?.toLowerCase() || '';
    expect(indiaText).not.toContain('drought');
    expect(indiaText).not.toContain('flood');
    expect(indiaText).not.toContain('scarcity');
    expect(indiaText).not.toContain('water shortage');
    expect(indiaText).not.toContain('risk');

    const { container: mhContainer } = render(
      <MapView sites={dummySites} dataset="maharashtra" selectedSiteId={null} onSiteSelect={() => {}} onBoundsChange={() => {}} />
    );
    const mhText = mhContainer.textContent?.toLowerCase() || '';
    expect(mhText).not.toContain('drought');
    expect(mhText).not.toContain('flood');
    expect(mhText).not.toContain('scarcity');
    expect(mhText).not.toContain('water shortage');
    expect(mhText).not.toContain('risk');
  });

  test('17. No combined risk score or combined state fields', () => {
    const { getByTestId } = render(
      <MapView sites={dummySites} dataset="india" selectedSiteId={null} onSiteSelect={() => {}} onBoundsChange={() => {}} />
    );
    const source = getByTestId('source-sites');
    const geojson = JSON.parse(source.getAttribute('data-geojson') || '{}');
    for (const f of geojson.features) {
      expect(f.properties).not.toHaveProperty('risk');
      expect(f.properties).not.toHaveProperty('risk_score');
      expect(f.properties).not.toHaveProperty('severity');
      expect(f.properties).not.toHaveProperty('groundwater_risk');
      expect(f.properties).not.toHaveProperty('combined_state');
    }
  });
});
