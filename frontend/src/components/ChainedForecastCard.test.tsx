import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { vi, describe, test, expect, beforeEach } from 'vitest';
import * as api from '../services/api';
import { ChainedForecastCard } from './ChainedForecastCard';

const sample: api.ChainedForecast = {
  candidate_site_id: 'MH_X', region: 'maharashtra', estimate_label: 'ESTIMATED_WITHOUT_RECENT_DATA',
  origin_date: '2026-05-30', origin_water_level: -10.0, requested_target_date: '2026-11-10',
  predicted_for_date: '2026-11-30', n_steps: 6, step_months: 1, backtested_steps: 2, data_gap_days: 184,
  method: 'persistence_fallback', method_reason: 'no skill', predicted_water_level: -10.0, predicted_change: 0,
  predicted_lower_80: -14.0, predicted_upper_80: -5.0, interval_basis: 'extrapolated_sqrt_from_2_steps',
  predicted_condition_state: 'NORMAL_RANGE', predicted_state_confidence: 0.5,
  predicted_condition_probabilities: { EXTREMELY_LOW: 0.1, LOW: 0.1, NORMAL_RANGE: 0.5, HIGH: 0.2, EXTREMELY_HIGH: 0.1 },
  water_level_unit: 'meters', warnings: ['forecast path crosses monsoon months (Jun-Sep) that are absent from the training data'],
  path_levels: [], data_through: '2026-05-30',
};

describe('ChainedForecastCard', () => {
  beforeEach(() => { vi.restoreAllMocks(); });

  test('shows the estimate, the no-recent-data label, method and warnings', async () => {
    vi.spyOn(api, 'fetchChainedForecast').mockResolvedValue(sample);
    render(<ChainedForecastCard siteId="MH_X" dataset="maharashtra" />);
    await waitFor(() => expect(screen.getByText('-10.00')).toBeInTheDocument());
    expect(screen.getByText(/ESTIMATED WITHOUT RECENT DATA/)).toBeInTheDocument();
    expect(screen.getByTestId('chain-method')).toHaveTextContent(/no skill in backtest/);
    expect(screen.getByTestId('chain-warnings')).toHaveTextContent(/monsoon/);
    expect(screen.getByText(/extrapolated, wider than measured/)).toBeInTheDocument();
  });

  test('neutral message when no estimate exists', async () => {
    vi.spyOn(api, 'fetchChainedForecast').mockResolvedValue(null);
    render(<ChainedForecastCard siteId="MH_Y" dataset="maharashtra" />);
    await waitFor(() => expect(screen.getByText(/No rough estimate for this site/)).toBeInTheDocument());
  });

  test('degrades gracefully on API error', async () => {
    vi.spyOn(api, 'fetchChainedForecast').mockRejectedValue(new Error('x'));
    render(<ChainedForecastCard siteId="MH_Z" dataset="india" />);
    await waitFor(() => expect(screen.getByText(/Estimate unavailable/)).toBeInTheDocument());
  });

  test('chained method label when the model has skill', async () => {
    vi.spyOn(api, 'fetchChainedForecast').mockResolvedValue({ ...sample, method: 'chained_xgboost', warnings: [], region: 'india' });
    render(<ChainedForecastCard siteId="IND_1" dataset="india" />);
    await waitFor(() => expect(screen.getByTestId('chain-method')).toHaveTextContent('chained XGBoost'));
    expect(screen.queryByTestId('chain-warnings')).not.toBeInTheDocument();
  });
});
