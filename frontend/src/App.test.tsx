import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import App from './App';
import * as api from './services/api';
import { vi, describe, test, expect, beforeEach } from 'vitest';

// Mock MapView to avoid MapLibre WebGL errors in JSDOM
vi.mock('./components/MapView', () => ({
  MapView: ({ sites, onSiteSelect }: any) => (
    <div data-testid="mock-map">
      {sites.map((site: any) => (
        <button
          key={site.candidate_site_id}
          data-testid={`site-marker-${site.candidate_site_id}`}
          onClick={() => onSiteSelect(site)}
        >
          {site.candidate_site_id}
        </button>
      ))}
    </div>
  )
}));

// Mock echarts to avoid canvas errors in JSDOM
vi.mock('echarts-for-react', () => ({
  default: () => <div data-testid="mock-echarts" />
}));

const openMapTab = () => fireEvent.click(screen.getByRole('tab', { name: 'Geospatial Map' }));

describe('Groundwater Intelligence Command Center', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api, 'fetchIndiaSites').mockResolvedValue([]);
    vi.spyOn(api, 'fetchMHSites').mockResolvedValue([]);
    vi.spyOn(api, 'fetchIndiaCondition').mockResolvedValue({
      candidate_site_id: 'dummy',
      water_level_raw: 5,
      condition_state: 'NORMAL_RANGE',
      percentile: 50.0,
      historical_sample_count: 30,
      historical_reference_group: 'RABI_WINTER',
      condition_method_version: 'v1',
      water_level_unit: 'UNKNOWN'
    });
    vi.spyOn(api, 'fetchMHCondition').mockResolvedValue({
      candidate_site_id: 'dummy',
      water_level_raw: 5,
      condition_state: 'NORMAL_RANGE',
      percentile: 50.0,
      historical_sample_count: 30,
      historical_reference_group: 'MONTH_01',
      condition_method_version: 'v1',
      water_level_unit: 'meters'
    });
    vi.spyOn(api, 'fetchMHForecast').mockResolvedValue({
      candidate_site_id: 'dummy',
      latest_observation_timestamp: '2026-04-08T18:00:00Z',
      latest_water_level: 5,
      predicted_next_water_level: 5,
      water_level_unit: 'meters',
      forecast_type: 'NEXT_VALID_OBSERVATION',
      forecast_method: 'PERSISTENCE',
      model_version: 'persistence-v1'
    });
  });

  test('1. Application loads with correct product title', async () => {
    render(<App />);
    // Title uses mixed-case now
    expect(screen.getByText(/Groundwater Intelligence Command Center/i)).toBeInTheDocument();
  });

  test('MapView mounts only while the Geospatial Map tab is active', async () => {
    render(<App />);
    expect(screen.queryByTestId('mock-map')).not.toBeInTheDocument();

    openMapTab();
    expect(await screen.findByTestId('mock-map')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: 'Predictive Analytics' }));
    expect(screen.queryByTestId('mock-map')).not.toBeInTheDocument();
  });

  test('Primary tabs support arrow-key navigation', () => {
    render(<App />);
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Overview Dashboard' }), { key: 'ArrowRight' });

    expect(screen.getByRole('tab', { name: 'Geospatial Map' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByTestId('mock-map')).toBeInTheDocument();
  });

  test('2, 3. Dataset selection works (India / Maharashtra)', async () => {
    vi.spyOn(api, 'fetchIndiaSites').mockResolvedValue([
      { candidate_site_id: 'IND-1', latitude: 20, longitude: 79 }
    ]);
    const fetchMHSpy = vi.spyOn(api, 'fetchMHSites').mockResolvedValue([
      { candidate_site_id: 'MH-1', latitude: 19, longitude: 75, station_name: 'Pune' }
    ]);

    render(<App />);
    openMapTab();

    expect(await screen.findByText(/Historical Candidate Sites/i)).toBeInTheDocument();

    // Switch to Maharashtra
    fireEvent.click(screen.getByText(/Maharashtra Telemetry/i));
    expect(await screen.findByText(/Telemetry Stations/i)).toBeInTheDocument();
    expect(fetchMHSpy).toHaveBeenCalled();
  });

  test('4, 5, 10. Selecting a site opens investigation panel with correct dataset label', async () => {
    // India site
    vi.spyOn(api, 'fetchIndiaSites').mockResolvedValue([
      { candidate_site_id: 'IND-1', latitude: 20, longitude: 79 }
    ]);
    vi.spyOn(api, 'fetchIndiaAlerts').mockResolvedValue([
      {
        observation_date: '2023-01-01',
        analytical_season: 'pre-monsoon',
        water_level_raw: 10,
        historical_reference: 10,
        historical_std: 1,
        standardized_score: 0,
        historical_sample_count: 10,
        instantaneous_state: 'NORMAL',
        alert_event_state: 'NORMAL',
        detector_version: 'v1'
      }
    ]);

    const { unmount } = render(<App />);
    openMapTab();
    const indMarker = await screen.findByTestId('site-marker-IND-1');
    fireEvent.click(indMarker);
    expect(await screen.findByText('Historical Candidate Site')).toBeInTheDocument();
    unmount();

    // MH site
    vi.spyOn(api, 'fetchMHSites').mockResolvedValue([
      { candidate_site_id: 'MH-1', latitude: 19, longitude: 75 }
    ]);
    vi.spyOn(api, 'fetchMHAlerts').mockResolvedValue([
      {
        observation_timestamp: '2023-01-01T00:00:00Z',
        water_level_raw: 5,
        historical_reference: 5,
        deviation: 0,
        historical_std: 1,
        standardized_score: 0,
        time_since_previous_obs_hours: 6,
        instantaneous_state: 'NORMAL',
        alert_event_state: 'NORMAL',
        detector_version: 'v1'
      }
    ]);

    render(<App />);
    openMapTab();
    fireEvent.click(screen.getByText(/Maharashtra Telemetry/i));
    const mhMarker = await screen.findByTestId('site-marker-MH-1');
    fireEvent.click(mhMarker);
    expect(await screen.findByText('Telemetry Station')).toBeInTheDocument();
  });

  test('6, 7, 8, 9. Alert states render using exact M6 vocabulary', async () => {
    vi.spyOn(api, 'fetchIndiaSites').mockResolvedValue([
      { candidate_site_id: 'IND-ALERTS', latitude: 20, longitude: 79 }
    ]);
    vi.spyOn(api, 'fetchIndiaAlerts').mockResolvedValue([
      {
        observation_date: '2023-01-01',
        analytical_season: 'pre', water_level_raw: 10,
        historical_reference: 10, historical_std: 1, standardized_score: 0, historical_sample_count: 10,
        instantaneous_state: 'CRITICAL_STATISTICAL_DEVIATION',
        alert_event_state: 'CRITICAL_STATISTICAL_DEVIATION',
        detector_version: 'v1'
      }
    ]);

    render(<App />);
    openMapTab();
    const marker = await screen.findByTestId('site-marker-IND-ALERTS');
    fireEvent.click(marker);
    // Alert label is now "Critical Statistical Deviation" (title-cased from ALERT_CONFIG)
    expect(await screen.findByText(/Critical Statistical Deviation/i)).toBeInTheDocument();
  });

  test('Condition successfully renders EXTREMELY_LOW with percentile and separates from M6', async () => {
    vi.spyOn(api, 'fetchIndiaSites').mockResolvedValue([
      { candidate_site_id: 'IND-COND', latitude: 20, longitude: 79 }
    ]);
    vi.spyOn(api, 'fetchIndiaAlerts').mockResolvedValue([
      {
        observation_date: '2023-01-01', analytical_season: 'pre', water_level_raw: 10,
        historical_reference: 10, historical_std: 1, standardized_score: 0, historical_sample_count: 10,
        instantaneous_state: 'NORMAL', alert_event_state: 'NORMAL', detector_version: 'v1'
      }
    ]);
    vi.spyOn(api, 'fetchIndiaCondition').mockResolvedValue({
      candidate_site_id: 'IND-COND',
      observation_date: '2023-01-01',
      analytical_season: 'pre',
      water_level_raw: 10,
      condition_state: 'EXTREMELY_LOW',
      percentile: 2.5,
      historical_sample_count: 35,
      historical_reference_group: 'RABI',
      condition_method_version: 'v1',
      water_level_unit: 'UNKNOWN'
    });

    render(<App />);
    openMapTab();
    fireEvent.click(await screen.findByTestId('site-marker-IND-COND'));
    
    // Condition section
    expect(await screen.findByText('EXTREMELY LOW')).toBeInTheDocument();
    expect(await screen.findByText('2.5')).toBeInTheDocument();
    expect(await screen.findByText('35')).toBeInTheDocument();
    
    // Check separation: M6 alert is still there
    expect(await screen.findByText('Normal')).toBeInTheDocument();

    // Check no combined score
    expect(screen.queryByText(/risk score/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/drought score/i)).not.toBeInTheDocument();
  });

  test('Condition INSUFFICIENT_HISTORY renders explanation and no fake numbers', async () => {
    vi.spyOn(api, 'fetchIndiaSites').mockResolvedValue([
      { candidate_site_id: 'IND-COND-2', latitude: 20, longitude: 79 }
    ]);
    vi.spyOn(api, 'fetchIndiaAlerts').mockResolvedValue([]);
    vi.spyOn(api, 'fetchIndiaCondition').mockResolvedValue({
      candidate_site_id: 'IND-COND-2',
      water_level_raw: 10,
      condition_state: 'INSUFFICIENT_HISTORY',
      percentile: null,
      historical_sample_count: 2,
      historical_reference_group: 'RABI',
      condition_method_version: 'v1',
      water_level_unit: 'UNKNOWN'
    });

    render(<App />);
    openMapTab();
    fireEvent.click(await screen.findByTestId('site-marker-IND-COND-2'));
    
    expect(await screen.findByText('INSUFFICIENT HISTORY')).toBeInTheDocument();
    expect(await screen.findByText(/Insufficient historical observations for statistical condition/i)).toBeInTheDocument();
    
    // Percentile label should not be present if value is null
    expect(screen.queryByText('Percentile')).not.toBeInTheDocument();
  });

  test('Condition API failure does not break investigation panel or map', async () => {
    vi.spyOn(api, 'fetchIndiaSites').mockResolvedValue([
      { candidate_site_id: 'IND-COND-FAIL', latitude: 20, longitude: 79 }
    ]);
    vi.spyOn(api, 'fetchIndiaAlerts').mockResolvedValue([
       {
        observation_date: '2023-01-01', analytical_season: 'pre', water_level_raw: 10,
        historical_reference: 10, historical_std: 1, standardized_score: 0, historical_sample_count: 10,
        instantaneous_state: 'NORMAL', alert_event_state: 'NORMAL', detector_version: 'v1'
      }
    ]);
    vi.spyOn(api, 'fetchIndiaCondition').mockRejectedValue(new Error('API Down'));

    render(<App />);
    openMapTab();
    fireEvent.click(await screen.findByTestId('site-marker-IND-COND-FAIL'));
    
    expect(await screen.findByText('Condition unavailable')).toBeInTheDocument();
    
    // Alert and Location still rendered
    expect(await screen.findByText('Normal')).toBeInTheDocument();
    expect(await screen.findByText('Location')).toBeInTheDocument();
  });

  test('12, 13. API failures render useful error state', async () => {
    vi.spyOn(api, 'fetchIndiaSites').mockRejectedValue(new Error('Network error'));

    render(<App />);
    // Error message updated in M8.1
    expect(await screen.findByText(/Failed to fetch sites/i)).toBeInTheDocument();
  });

  test('13. Empty API response renders correct viewport message', async () => {
    vi.spyOn(api, 'fetchIndiaSites').mockResolvedValue([]);
    render(<App />);
    openMapTab();
    // The count "0" is in its own span, then "sites in view" in a sibling span
    // Just check the count node appears and the label text is present
    const countEl = await screen.findByText('0');
    expect(countEl).toBeInTheDocument();
    expect(screen.getByText(/site.*in view/i)).toBeInTheDocument();
  });

  test('14. API base URL is defined', () => {
    expect(api.API_BASE_URL).toBeDefined();
  });

  test('15, 16. No unexpected prediction UI outside of MH Persistence Forecast', () => {
    render(<App />);
    expect(screen.queryByText(/AI Forecast/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Drought Prediction/i)).not.toBeInTheDocument();
  });

  test('Maharashtra site renders Forecast with NEXT_VALID_OBSERVATION semantics', async () => {
    vi.spyOn(api, 'fetchMHSites').mockResolvedValue([{ candidate_site_id: 'MH-1', latitude: 19, longitude: 75 }]);
    vi.spyOn(api, 'fetchMHAlerts').mockResolvedValue([]);
    vi.spyOn(api, 'fetchMHForecast').mockResolvedValue({
      candidate_site_id: 'MH-1',
      latest_observation_timestamp: '2026-04-08T18:00:00Z',
      latest_water_level: 8.5,
      predicted_next_water_level: 8.5,
      water_level_unit: 'meters',
      forecast_type: 'NEXT_VALID_OBSERVATION',
      forecast_method: 'PERSISTENCE',
      model_version: 'persistence-v1'
    });
    render(<App />);
    openMapTab();
    fireEvent.click(screen.getByText(/Maharashtra Telemetry/i));
    fireEvent.click(await screen.findByTestId('site-marker-MH-1'));

    expect(await screen.findByText('Next-Observation Forecast')).toBeInTheDocument();
    expect(await screen.findByText('8.500')).toBeInTheDocument();
    expect(await screen.findByText('Method: Persistence')).toBeInTheDocument();
    expect(await screen.findByText(/Uses the latest valid groundwater level as the prediction for the next valid observation/i)).toBeInTheDocument();
    
    // Check isolation
    expect(screen.queryByText(/6-Hour Forecast/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/AI Forecast/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/risk score/i)).not.toBeInTheDocument();
  });

  test('Forecast failure renders Forecast unavailable isolated from other components', async () => {
    vi.spyOn(api, 'fetchMHSites').mockResolvedValue([{ candidate_site_id: 'MH-2', latitude: 19, longitude: 75 }]);
    vi.spyOn(api, 'fetchMHAlerts').mockResolvedValue([]);
    vi.spyOn(api, 'fetchMHCondition').mockResolvedValue({
      candidate_site_id: 'MH-2', water_level_raw: 10, condition_state: 'NORMAL_RANGE', percentile: 50,
      historical_sample_count: 35, historical_reference_group: 'MONTH_01', condition_method_version: 'v1', water_level_unit: 'meters'
    });
    vi.spyOn(api, 'fetchMHForecast').mockRejectedValue(new Error('API Down'));

    render(<App />);
    openMapTab();
    fireEvent.click(screen.getByText(/Maharashtra Telemetry/i));
    fireEvent.click(await screen.findByTestId('site-marker-MH-2'));

    expect(await screen.findByText('Forecast unavailable')).toBeInTheDocument();
    expect(await screen.findByText('NORMAL RANGE')).toBeInTheDocument(); // Condition didn't break
  });

  test('India site does not display fake forecast', async () => {
    vi.spyOn(api, 'fetchIndiaSites').mockResolvedValue([{ candidate_site_id: 'IND-1', latitude: 20, longitude: 79 }]);
    vi.spyOn(api, 'fetchIndiaAlerts').mockResolvedValue([]);
    render(<App />);
    openMapTab();
    fireEvent.click(await screen.findByTestId('site-marker-IND-1'));

    expect(screen.queryByText('Next-Observation Forecast')).not.toBeInTheDocument();
  });
});
