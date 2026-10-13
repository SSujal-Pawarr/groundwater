/**
 * Advanced Forecast API Client
 * Connects to the multi-model unlimited horizon forecasting backend
 */

export interface ModelPrediction {
  predicted_level: number;
  predicted_change: number;
  confidence_interval_80: [number | null, number | null] | null;
  method: string;
  test_metrics?: {
    mae?: number;
    rmse?: number;
    r2?: number;
    n?: number;
  };
  scenario_factor_applied?: number;
  n_steps?: number;
  method_reason?: string;
}

export interface TrajectoryPoint {
  date: string;
  predicted_level: number;
  ci_lower?: number | null;
  ci_upper?: number | null;
}

export interface PrecisionBenchmark {
  model_name: string;
  directional_precision_pct: number;
  mae_meters: number;
  ci_coverage_80_pct: number;
  bias_nature: string;
  description: string;
}

export interface DivergenceInfo {
  is_divergent: boolean;
  hydrological_cause: string;
  precision_note?: string;
}

export interface HistoricalObservation {
  date: string;
  water_level: number;
}

export interface AdvancedForecastResponse {
  site_id: string;
  station_name: string;
  district: string;
  lat: number | null;
  lon: number | null;
  origin_date: string;
  origin_water_level: number;
  target_date: string;
  horizon_days: number;
  scenario: 'normal' | 'deficit' | 'excess';
  water_level_unit: string;
  predictions: Record<string, ModelPrediction>;
  trajectories?: Record<string, TrajectoryPoint[]>;
  precision_metrics?: Record<string, PrecisionBenchmark>;
  divergence_info?: DivergenceInfo;
  unavailable_models: string[];
  history: HistoricalObservation[];
}

export interface MapForecastSite {
  site_id: string;
  lat: number | null;
  lon: number | null;
  origin_level: number;
  predicted_level: number;
  predicted_change: number;
  predicted_condition: string;
}

export interface MapForecastResponse {
  model: string;
  target_date: string;
  scenario: string;
  sites: MapForecastSite[];
}

export interface ModelInfo {
  status: string;
  description?: string;
  model_type?: string;
  test_metrics?: {
    mae?: number;
    rmse?: number;
    r2?: number;
  };
  persist_metrics?: {
    mae?: number;
    rmse?: number;
    r2?: number;
  };
  top_features?: Record<string, number>;
  max_steps?: number;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL
  ? import.meta.env.VITE_API_BASE_URL.replace(/\/api\/v1\/?$/, '')
  : (typeof window !== 'undefined'
      ? `${window.location.protocol}//${window.location.hostname}:8000`
      : 'http://localhost:8000');

export async function fetchAdvancedForecast(
  siteId: string,
  targetDate: string,
  scenario: 'normal' | 'deficit' | 'excess' = 'normal',
  models: string[] = ['seasonal_harmonic', 'lstm', 'persistence', 'chained']
): Promise<AdvancedForecastResponse> {
  const params = new URLSearchParams({
    site_id: siteId,
    target_date: targetDate,
    scenario,
    models: models.join(','),
  });

  const response = await fetch(`${API_BASE}/api/v1/maharashtra/advanced-forecast?${params}`);
  if (!response.ok) {
    const errorText = await response.text();
    let detail = `Error ${response.status}`;
    try {
      const parsed = JSON.parse(errorText);
      detail = parsed.detail || detail;
    } catch {
      detail = errorText || detail;
    }
    throw new Error(detail);
  }
  return response.json();
}

export async function fetchAdvancedForecastMap(
  targetDate: string,
  scenario: 'normal' | 'deficit' | 'excess' = 'normal',
  model: string = 'seasonal_harmonic'
): Promise<MapForecastResponse> {
  const params = new URLSearchParams({
    target_date: targetDate,
    scenario,
    model,
  });

  const response = await fetch(`${API_BASE}/api/v1/maharashtra/advanced-forecast/map?${params}`);
  if (!response.ok) {
    const errorText = await response.text();
    let detail = `Error ${response.status}`;
    try {
      const parsed = JSON.parse(errorText);
      detail = parsed.detail || detail;
    } catch {
      detail = errorText || detail;
    }
    throw new Error(detail);
  }
  return response.json();
}

export async function fetchAdvancedForecastModelInfo(): Promise<Record<string, ModelInfo>> {
  const response = await fetch(`${API_BASE}/api/v1/maharashtra/advanced-forecast/models/info`);
  if (!response.ok) {
    throw new Error(`Failed to load model info: ${response.status}`);
  }
  return response.json();
}
