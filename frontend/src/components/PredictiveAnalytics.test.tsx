import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { PredictiveAnalytics } from './PredictiveAnalytics';
import { fetchMaharashtraRegressionForecast } from '../services/api';
import type { MaharashtraRegressionForecast } from '../services/api';

vi.mock('../services/api', async importOriginal => {
  const actual = await importOriginal<typeof import('../services/api')>();
  return {
    ...actual,
    fetchMaharashtraRegressionForecast: vi.fn(),
  };
});

vi.mock('echarts-for-react', () => ({
  default: ({ option }: { option: { series: Array<{ name: string; lineStyle: { type?: string } }> } }) => (
    <div
      data-testid="forecast-chart"
      data-series={JSON.stringify(option.series.map(series => ({ name: series.name, lineType: series.lineStyle.type || 'solid' })))}
    />
  ),
}));

const fixture: MaharashtraRegressionForecast = {
  region: 'maharashtra',
  target_date: '2026-10-12',
  data_through: '2026-05-30',
  max_target_date: '2027-01-30',
  step_months: 1,
  source_age_days: 0,
  water_level_unit: 'meters',
  locations: [{
    candidate_site_id: 'MH_TEST_A',
    station_name: 'TEST STATION A',
    district: 'Nashik',
    state: 'Maharashtra',
    latitude: 19,
    longitude: 74,
    origin_water_level: 10,
    predicted_water_level: 12.5,
    predicted_change: 2.5,
    predicted_lower_80: 8,
    predicted_upper_80: 16,
    forecast_origin_date: '2026-05-30',
    requested_target_date: '2026-10-12',
    predicted_for_date: '2026-10-12',
    method: 'chained_xgboost',
    method_reason: 'Backtest skill over persistence',
    n_steps: 5,
    step_months: 1,
    predicted_condition_state: 'NORMAL_RANGE',
    predicted_state_confidence: 0.7,
    predicted_condition_probabilities: { NORMAL_RANGE: 0.7 },
    trained_regression_water_level: 11.5,
    direct_m17_water_level: null,
    warnings: [],
    path_levels: [
      { date: '2026-05-30', level: 10 },
      { date: '2026-06-30', level: 10.4 },
      { date: '2026-07-30', level: 10.8 },
      { date: '2026-08-30', level: 11.2 },
      { date: '2026-09-30', level: 11.8 },
      { date: '2026-10-12', level: 12.5 },
    ],
  }],
  selected_location: {
    candidate_site_id: 'MH_TEST_A',
    station_name: 'TEST STATION A',
    district: 'Nashik',
    state: 'Maharashtra',
    latitude: 19,
    longitude: 74,
    origin_water_level: 10,
    forecast_origin_date: '2026-02-14',
    last_observation_date: '2026-02-14',
    target_date: '2026-10-12',
    requested_target_date: '2026-10-12',
    predicted_for_date: '2026-10-12',
    predicted_water_level: 12.5,
    predicted_change: 2.5,
    predicted_lower_80: 8,
    predicted_upper_80: 16,
    method: 'chained_xgboost',
    method_reason: 'Backtest skill over persistence',
    n_steps: 5,
    step_months: 1,
    predicted_condition_state: 'NORMAL_RANGE',
    predicted_state_confidence: 0.7,
    predicted_condition_probabilities: { NORMAL_RANGE: 0.7 },
    trained_regression_water_level: 11.5,
    direct_m17_water_level: null,
    warnings: [],
    path_levels: [
      { date: '2026-05-30', level: 10 },
      { date: '2026-06-30', level: 10.4 },
      { date: '2026-07-30', level: 10.8 },
      { date: '2026-08-30', level: 11.2 },
      { date: '2026-09-30', level: 11.8 },
      { date: '2026-10-12', level: 12.5 },
    ],
    history: [
      { date: '2026-05-28', water_level: 9.8 },
      { date: '2026-05-29', water_level: 9.9 },
      { date: '2026-05-30', water_level: 10 },
    ],
  },
  models: {
    chained_m17: { available: true, target_date: '2026-10-12' },
    trained_gradient_boosting: { available: true, trained_target_date: '2026-10-12', model_file: 'maharashtra_level_h135.joblib' },
    direct_m17: { available: false, trained_target_date: '2026-06-30' },
  },
  chain_backtest: {},
  unsupported_targets: {
    flood_probability: 'Flood probability is not available from this model.',
    stress_state: 'Structural stress is not predicted by this model.',
  },
};

describe('PredictiveAnalytics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(fetchMaharashtraRegressionForecast).mockImplementation(async (date, siteId) => ({
      ...fixture,
      target_date: date || fixture.target_date,
      selected_location: siteId ? {
        ...fixture.selected_location!,
        target_date: date || fixture.target_date,
        requested_target_date: date || fixture.target_date,
        predicted_for_date: date || fixture.target_date,
      } : null,
    }));
  });

  test('loads selected-site forecast and renders a dashed prediction series', async () => {
    render(<PredictiveAnalytics dataset="maharashtra" />);

    expect(await screen.findByText('Observed and estimated groundwater level')).toBeInTheDocument();
    expect(screen.getByText('12.50')).toBeInTheDocument();
    expect(screen.getByText('+2.50 meters')).toBeInTheDocument();
    expect(screen.getByTestId('forecast-chart')).toHaveAttribute('data-series', JSON.stringify([
      { name: 'Observed groundwater level', lineType: 'solid' },
      { name: 'M17 chained estimate', lineType: 'dashed' },
      { name: 'Trained Gradient Boosting', lineType: 'dotted' },
    ]));
    expect(screen.getByText(/Flood probability is not available/)).toBeInTheDocument();
    await waitFor(() => expect(fetchMaharashtraRegressionForecast).toHaveBeenCalledWith(undefined, 'MH_TEST_A'));
  });

  test('does not request a Maharashtra model for India', () => {
    render(<PredictiveAnalytics dataset="india" />);

    expect(screen.getByText(/available for Maharashtra telemetry only/i)).toBeInTheDocument();
    expect(fetchMaharashtraRegressionForecast).not.toHaveBeenCalled();
  });

  test('submits a requested target date to the API', async () => {
    render(<PredictiveAnalytics dataset="maharashtra" />);
    await screen.findByText('Observed and estimated groundwater level');
    fireEvent.change(screen.getByLabelText('Target date'), { target: { value: '2026-10-13' } });
    fireEvent.click(screen.getByRole('button', { name: 'Update' }));

    await waitFor(() => expect(fetchMaharashtraRegressionForecast).toHaveBeenCalledWith('2026-10-13', 'MH_TEST_A'));
  });
});