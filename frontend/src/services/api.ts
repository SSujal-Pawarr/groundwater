export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ||
  (typeof window !== 'undefined'
    ? `${window.location.protocol}//${window.location.hostname}:8000/api/v1`
    : 'http://localhost:8000/api/v1');

export type AlertState = 
  | 'NORMAL' 
  | 'WATCH' 
  | 'WARNING' 
  | 'CRITICAL_STATISTICAL_DEVIATION' 
  | 'DATA_QUALITY_EVENT' 
  | 'INSUFFICIENT_HISTORY' 
  | 'SEQUENCE_GAPPED';

export type ConditionState = 
  | 'EXTREMELY_LOW' 
  | 'LOW' 
  | 'NORMAL_RANGE' 
  | 'HIGH' 
  | 'EXTREMELY_HIGH' 
  | 'INSUFFICIENT_HISTORY';

export interface GroundwaterCondition {
  candidate_site_id: string;
  observation_date?: string; // India
  observation_timestamp?: string; // MH
  analytical_season?: string; // India
  water_level_raw: number | null;
  condition_state: ConditionState;
  percentile: number | null;
  historical_sample_count: number | null;
  historical_reference_group: string | null;
  condition_method_version: string;
  water_level_unit: string;
}


export interface CandidateSite {
  candidate_site_id: string;
  latitude: number | null;
  longitude: number | null;
  state?: string;
  district?: string;
  block?: string;
  village?: string;
  station_name?: string;
  subdistrict?: string;
  elevation_msl?: number | null;
  condition_state?: ConditionState | null;
  alert_event_state?: AlertState | null;
  drought_state?: string | null;
  flood_potential_state?: string | null;
  stress_state?: string | null;
}

export interface IndiaAlert {
  observation_date: string;
  analytical_season: string;
  water_level_raw: number | null;
  historical_reference: number | null;
  historical_std: number | null;
  standardized_score: number | null;
  historical_sample_count: number | null;
  instantaneous_state: string;
  alert_event_state: AlertState;
  detector_version: string;
}

export interface MHAlert {
  observation_timestamp: string;
  water_level_raw: number | null;
  historical_reference: number | null;
  deviation: number | null;
  historical_std: number | null;
  standardized_score: number | null;
  time_since_previous_obs_hours: number | null;
  instantaneous_state: string;
  alert_event_state: AlertState;
  detector_version: string;
}

export interface BBox {
  min_lat: number;
  max_lat: number;
  min_lng: number;
  max_lng: number;
}

const responseError = async (res: Response, fallback: string): Promise<Error> => {
  try {
    const body = await res.json() as { detail?: string };
    return new Error(body.detail || fallback);
  } catch {
    return new Error(fallback);
  }
};

export const fetchIndiaSites = async (bbox?: BBox, state?: string, limit=5000): Promise<CandidateSite[]> => {
  let url = `${API_BASE_URL}/india/candidate-sites?limit=${limit}`;
  if (bbox) {
    url += `&min_lat=${bbox.min_lat}&max_lat=${bbox.max_lat}&min_lng=${bbox.min_lng}&max_lng=${bbox.max_lng}`;
  }
  if (state) url += `&state=${encodeURIComponent(state)}`;
  const res = await fetch(url);
  if (!res.ok) throw await responseError(res, 'Failed to fetch India sites');
  return res.json();
};

export const fetchMHSites = async (bbox?: BBox, district?: string, limit=5000): Promise<CandidateSite[]> => {
  let url = `${API_BASE_URL}/maharashtra/candidate-sites?limit=${limit}`;
  if (bbox) {
    url += `&min_lat=${bbox.min_lat}&max_lat=${bbox.max_lat}&min_lng=${bbox.min_lng}&max_lng=${bbox.max_lng}`;
  }
  if (district) url += `&district=${encodeURIComponent(district)}`;
  const res = await fetch(url);
  if (!res.ok) throw await responseError(res, 'Failed to fetch Maharashtra sites');
  return res.json();
};

export const fetchIndiaAlerts = async (siteId: string): Promise<IndiaAlert[]> => {
  const url = `${API_BASE_URL}/india/candidate-sites/${encodeURIComponent(siteId)}/alerts?limit=1000`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch India alerts');
  return res.json();
};

export const fetchMHAlerts = async (siteId: string): Promise<MHAlert[]> => {
  const url = `${API_BASE_URL}/maharashtra/candidate-sites/${encodeURIComponent(siteId)}/alerts?limit=1000`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch MH alerts');
  return res.json();
};

export const fetchIndiaCondition = async (siteId: string): Promise<GroundwaterCondition> => {
  const url = `${API_BASE_URL}/india/candidate-sites/${encodeURIComponent(siteId)}/condition`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch India condition');
  return res.json();
};

export const fetchMHCondition = async (siteId: string): Promise<GroundwaterCondition> => {
  const url = `${API_BASE_URL}/maharashtra/candidate-sites/${encodeURIComponent(siteId)}/condition`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch MH condition');
  return res.json();
};

export interface PersistenceForecast {
  candidate_site_id: string;
  latest_observation_timestamp: string;
  latest_water_level: number;
  predicted_next_water_level: number;
  water_level_unit: string;
  forecast_type: 'NEXT_VALID_OBSERVATION';
  forecast_method: 'PERSISTENCE';
  model_version: string;
}

export const fetchMHForecast = async (siteId: string): Promise<PersistenceForecast> => {
  const url = `${API_BASE_URL}/maharashtra/candidate-sites/${encodeURIComponent(siteId)}/forecast`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch MH forecast');
  return res.json();
};

export const fetchAnalytics = async (siteId: string, region: 'india' | 'maharashtra'): Promise<any> => {
  const url = `${API_BASE_URL}/${region}/candidate-sites/${encodeURIComponent(siteId)}/analytics`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch analytics');
  return res.json();
};


// ---------------------------------------------------------------------------
// M17 — Multi-horizon future forecast (XGBoost regressor + future-state classifier)
// ---------------------------------------------------------------------------
export interface FutureForecast {
  candidate_site_id: string;
  region: 'india' | 'maharashtra';
  origin_date: string;
  origin_water_level: number;
  horizon_months: number;
  target_date: string;
  predicted_water_level: number;
  predicted_change: number;
  predicted_lower_80: number | null;
  predicted_upper_80: number | null;
  predicted_percentile_vs_history: number | null;
  current_condition_state: string;
  predicted_condition_state: string;
  predicted_state_confidence: number | null;
  predicted_condition_probabilities: Record<string, number | null>;
  water_level_unit: string;
  model_version: string;
  data_through: string;
  forecast_source?: 'direct_m17' | 'chained_fallback';
  forecast_method?: 'chained_xgboost' | 'persistence_fallback';
  estimate_label?: string;
  forecast_reason?: string;
  requested_target_date?: string;
  predicted_for_date?: string;
  warnings?: string[];
}

/** Resolves to null when no forecast exists for the site (HTTP 404) so the UI can show a neutral message. */
export const fetchFutureForecast = async (siteId: string, region: 'india' | 'maharashtra'): Promise<FutureForecast | null> => {
  const url = `${API_BASE_URL}/${region}/candidate-sites/${encodeURIComponent(siteId)}/future-forecast`;
  const res = await fetch(url);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error('Failed to fetch future forecast');
  return res.json();
};

// ---------------------------------------------------------------------------
// Chained estimate to a target date beyond the end of the data ("estimated without recent data")
// ---------------------------------------------------------------------------
export interface ChainedForecast {
  candidate_site_id: string;
  region: 'india' | 'maharashtra';
  estimate_label: string;
  origin_date: string;
  origin_water_level: number;
  requested_target_date: string;
  predicted_for_date: string;
  n_steps: number;
  step_months: number;
  backtested_steps: number;
  data_gap_days: number;
  method: 'chained_xgboost' | 'persistence_fallback';
  method_reason: string;
  predicted_water_level: number;
  predicted_change: number;
  predicted_lower_80: number | null;
  predicted_upper_80: number | null;
  interval_basis: string;
  predicted_condition_state: string;
  predicted_state_confidence: number | null;
  predicted_condition_probabilities: Record<string, number | null>;
  water_level_unit: string;
  warnings: string[];
  path_levels: { date: string; level: number }[];
  data_through: string;
}

/** Resolves to null when no chained estimate exists for the site (HTTP 404). */
export const fetchChainedForecast = async (siteId: string, region: 'india' | 'maharashtra'): Promise<ChainedForecast | null> => {
  const url = `${API_BASE_URL}/${region}/candidate-sites/${encodeURIComponent(siteId)}/chained-forecast`;
  const res = await fetch(url);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error('Failed to fetch chained forecast');
  return res.json();
};

export interface RegressionForecastPoint {
  date: string;
  water_level: number;
}

export interface RegressionForecastLocation {
  candidate_site_id: string;
  station_name: string | null;
  district: string | null;
  state: string | null;
  latitude: number | null;
  longitude: number | null;
  origin_water_level: number;
  forecast_origin_date: string;
  requested_target_date: string;
  predicted_for_date: string;
  predicted_water_level: number;
  predicted_change: number;
  predicted_lower_80: number | null;
  predicted_upper_80: number | null;
  method: 'chained_xgboost' | 'persistence_fallback';
  method_reason: string;
  n_steps: number;
  step_months: number;
  predicted_condition_state: string;
  predicted_state_confidence: number | null;
  predicted_condition_probabilities: Record<string, number | null>;
  trained_regression_water_level: number | null;
  direct_m17_water_level: number | null;
  warnings: string[];
  path_levels: { date: string; level: number }[];
}

export interface SelectedRegressionForecast extends RegressionForecastLocation {
  forecast_origin_date: string;
  last_observation_date: string;
  target_date: string;
  history: RegressionForecastPoint[];
}

export interface ProjectForecastModelAvailability {
  available: boolean;
  target_date?: string;
  trained_target_date?: string;
  model_file?: string;
}

export interface MaharashtraRegressionForecast {
  region: 'maharashtra';
  target_date: string;
  data_through: string;
  max_target_date: string;
  step_months: number;
  source_age_days: number;
  water_level_unit: string;
  locations: RegressionForecastLocation[];
  selected_location: SelectedRegressionForecast | null;
  models: {
    chained_m17: ProjectForecastModelAvailability;
    trained_gradient_boosting: ProjectForecastModelAvailability;
    direct_m17: ProjectForecastModelAvailability;
  };
  chain_backtest: Record<string, unknown>;
  unsupported_targets: Record<string, string>;
}

const API_ROOT_URL = API_BASE_URL.replace(/\/api\/v1\/?$/, '');

export const fetchMaharashtraRegressionForecast = async (
  targetDate?: string,
  candidateSiteId?: string,
): Promise<MaharashtraRegressionForecast> => {
  const params = new URLSearchParams();
  if (targetDate) params.set('target_date', targetDate);
  if (candidateSiteId) params.set('candidate_site_id', candidateSiteId);
  const query = params.size > 0 ? `?${params.toString()}` : '';
  const response = await fetch(`${API_ROOT_URL}/api/forecast/maharashtra${query}`);
  if (!response.ok) {
    let detail = 'Failed to fetch Maharashtra regression forecast';
    try {
      const body = await response.json() as { detail?: string };
      detail = body.detail || detail;
    } catch {
      // Keep the fallback message when the API response is not JSON.
    }
    throw new Error(detail);
  }
  return response.json();
};
