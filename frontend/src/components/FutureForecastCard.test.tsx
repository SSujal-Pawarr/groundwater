import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { vi, describe, test, expect, beforeEach } from 'vitest';
import * as api from '../services/api';
import { FutureForecastCard } from './FutureForecastCard';

const sample: api.FutureForecast = {
  candidate_site_id: 'MH_X',
  region: 'maharashtra',
  origin_date: '2026-05-30',
  origin_water_level: -10.0,
  horizon_months: 1,
  target_date: '2026-06-30',
  predicted_water_level: -10.5,
  predicted_change: -0.5,
  predicted_lower_80: -12.0,
  predicted_upper_80: -9.0,
  predicted_percentile_vs_history: 80,
  current_condition_state: 'HIGH',
  predicted_condition_state: 'EXTREMELY_HIGH',
  predicted_state_confidence: 0.62,
  predicted_condition_probabilities: { EXTREMELY_LOW: 0.05, LOW: 0.05, NORMAL_RANGE: 0.1, HIGH: 0.18, EXTREMELY_HIGH: 0.62 },
  water_level_unit: 'meters',
  model_version: 'M17-FutureForecast-v1',
  data_through: '2026-05-30',
};

describe('FutureForecastCard', () => {
  beforeEach(() => { vi.restoreAllMocks(); });

  test('renders predicted level, horizon and state', async () => {
    vi.spyOn(api, 'fetchFutureForecast').mockResolvedValue(sample);
    render(<FutureForecastCard siteId="MH_X" dataset="maharashtra" />);
    await waitFor(() => expect(screen.getByText('-10.50')).toBeInTheDocument());
    expect(screen.getByText(/1 month ahead/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Predicted condition state: EXTREMELY HIGH/)).toBeInTheDocument();
  });

  test('labels a chained fallback and explains why direct M17 is unavailable', async () => {
    vi.spyOn(api, 'fetchFutureForecast').mockResolvedValue({
      ...sample,
      forecast_source: 'chained_fallback',
      forecast_method: 'persistence_fallback',
      estimate_label: 'ESTIMATED_WITHOUT_RECENT_DATA',
      requested_target_date: '2026-11-10',
      predicted_for_date: '2026-11-30',
      forecast_reason: 'Chained model did not beat persistence.',
      warnings: ['Recharge data is unavailable.'],
    });
    render(<FutureForecastCard siteId="MH_CHAIN" dataset="maharashtra" />);

    expect(await screen.findByText(/Chained M17 estimate/)).toBeInTheDocument();
    expect(screen.getByText(/Direct forecast unavailable for this site/)).toBeInTheDocument();
    expect(screen.getByText(/Chained model did not beat persistence/)).toBeInTheDocument();
    expect(screen.getByText(/Recharge data is unavailable/)).toBeInTheDocument();
  });

  test('shows neutral message when no forecast exists', async () => {
    vi.spyOn(api, 'fetchFutureForecast').mockResolvedValue(null);
    render(<FutureForecastCard siteId="MH_Y" dataset="maharashtra" />);
    await waitFor(() => expect(screen.getByText(/No future forecast for this site/)).toBeInTheDocument());
  });

  test('degrades gracefully on API error', async () => {
    vi.spyOn(api, 'fetchFutureForecast').mockRejectedValue(new Error('boom'));
    render(<FutureForecastCard siteId="MH_Z" dataset="india" />);
    await waitFor(() => expect(screen.getByText(/Future forecast unavailable/)).toBeInTheDocument());
  });

  test('india card carries the unknown-unit caveat', async () => {
    vi.spyOn(api, 'fetchFutureForecast').mockResolvedValue({ ...sample, region: 'india', horizon_months: 6, water_level_unit: 'unknown' });
    render(<FutureForecastCard siteId="IND_1" dataset="india" />);
    await waitFor(() => expect(screen.getByText(/6 months ahead/)).toBeInTheDocument());
    expect(screen.getByText(/unit and datum are not documented/)).toBeInTheDocument();
  });

  test('insufficient-history state shows explanation and no probability bars', async () => {
    vi.spyOn(api, 'fetchFutureForecast').mockResolvedValue({
      ...sample, predicted_condition_state: 'INSUFFICIENT_HISTORY', predicted_state_confidence: null,
      predicted_condition_probabilities: { EXTREMELY_LOW: null, LOW: null, NORMAL_RANGE: null, HIGH: null, EXTREMELY_HIGH: null },
    });
    render(<FutureForecastCard siteId="IND_2" dataset="india" />);
    await waitFor(() => expect(screen.getByText(/Not enough prior observations/)).toBeInTheDocument());
    expect(screen.queryByText('NORMAL RANGE')).not.toBeInTheDocument();
  });
});
