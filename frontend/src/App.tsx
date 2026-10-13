import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AlertCircle, Loader2, Search, X } from 'lucide-react';
import { AlertCenter, SAMPLE_ALERTS, type AlertRecord } from './components/AlertCenter';
import { InvestigationPanel } from './components/InvestigationPanel';
import { Layout, type DashboardTab } from './components/Layout';
import { MapView } from './components/MapView';
import { PredictiveAnalytics } from './components/PredictiveAnalytics';
import { AdvancedForecastTab } from './components/AdvancedForecastTab';
import { MethodologyTab } from './components/MethodologyTab';
import { fetchIndiaSites, fetchMHSites } from './services/api';
import type { BBox, CandidateSite } from './services/api';


function App() {
  const [activeTab, setActiveTab] = useState<DashboardTab>('overview');
  const [dataset, setDataset] = useState<'india' | 'maharashtra'>('maharashtra');
  const [sites, setSites] = useState<CandidateSite[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [bounds, setBounds] = useState<BBox | undefined>();
  const [selectedSite, setSelectedSite] = useState<CandidateSite | null>(null);
  const [stateFilter, setStateFilter] = useState('');
  const [districtFilter, setDistrictFilter] = useState('');
  const [searchText, setSearchText] = useState('');
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadSites = useCallback(async (
    currentDataset: 'india' | 'maharashtra',
    currentBounds?: BBox,
    currentState?: string,
    currentDistrict?: string,
  ) => {
    try {
      setLoading(true);
      setError(null);
      const data = currentDataset === 'india'
        ? await fetchIndiaSites(currentBounds, currentState || undefined)
        : await fetchMHSites(currentBounds, currentDistrict || undefined);
      setSites(data);
    } catch (loadError) {
      const message = loadError instanceof Error ? loadError.message : '';
      setError(message === 'Failed to fetch'
        ? 'Failed to fetch sites. Is the backend running?'
        : `Failed to fetch sites. ${message || 'Is the backend running?'}`);
      setSites([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSites(dataset, bounds, stateFilter, districtFilter);
  }, [dataset, stateFilter, districtFilter, loadSites]);

  // Check URL parameters on mount (e.g., when launched from external link or new tab)
  useEffect(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      const tabParam = params.get('tab');
      const siteParam = params.get('site');
      const districtParam = params.get('district');
      if (tabParam === 'map') {
        setActiveTab('map');
        setDataset('maharashtra');
        if (districtParam) setDistrictFilter(districtParam);
        if (siteParam) {
          const matchedAlert = SAMPLE_ALERTS.find(a => a.candidate_site_id === siteParam || a.id === siteParam);
          setSelectedSite({
            candidate_site_id: siteParam,
            station_name: matchedAlert?.stationName || matchedAlert?.location || siteParam,
            district: districtParam || matchedAlert?.district || 'Maharashtra',
            state: 'Maharashtra',
            latitude: matchedAlert?.lat ?? 19.5,
            longitude: matchedAlert?.lon ?? 75.5,
            alert_event_state: 'CRITICAL_STATISTICAL_DEVIATION',
            condition_state: 'EXTREMELY_LOW',
          });
        }
      }
    } catch {
      // Ignore URL parsing errors
    }
  }, []);

  const handleAlertSelect = useCallback((alert: AlertRecord, openNewTab?: boolean) => {
    if (openNewTab) {
      const siteParam = alert.candidate_site_id || alert.id;
      const url = `${window.location.origin}${window.location.pathname}?tab=map&site=${encodeURIComponent(siteParam)}&district=${encodeURIComponent(alert.district || '')}`;
      window.open(url, '_blank');
      return;
    }
    setActiveTab('map');
    setDataset('maharashtra');
    if (alert.district) {
      setDistrictFilter(alert.district);
    }
    const matched = sites.find(s =>
      s.candidate_site_id === alert.candidate_site_id ||
      (s.district && s.district.toLowerCase() === alert.district.toLowerCase())
    );
    if (matched) {
      setSelectedSite(matched);
    } else {
      setSelectedSite({
        candidate_site_id: alert.candidate_site_id,
        station_name: alert.stationName || alert.location,
        district: alert.district,
        state: 'Maharashtra',
        latitude: alert.lat,
        longitude: alert.lon,
        alert_event_state: alert.severity === 'Critical' ? 'CRITICAL_STATISTICAL_DEVIATION' : 'WARNING',
        condition_state: alert.alertType === 'Flood' ? 'EXTREMELY_HIGH' : 'EXTREMELY_LOW',
        drought_state: alert.alertType === 'Drought' ? 'SEVERE_DEFICIT' : 'NORMAL_TO_WET',
        flood_potential_state: alert.alertType === 'Flood' ? 'HIGH' : 'LOW',
        stress_state: alert.alertType === 'Severe Stress' ? 'SEVERE_STRESS' : 'NORMAL',
      });
    }
  }, [sites]);

  useEffect(() => () => {
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
  }, []);

  const handleBoundsChange = useCallback((newBounds: BBox) => {
    setBounds(newBounds);
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(() => {
      loadSites(dataset, newBounds, stateFilter, districtFilter);
    }, 500);
  }, [dataset, loadSites, stateFilter, districtFilter]);

  const handleDatasetChange = (newDataset: 'india' | 'maharashtra') => {
    if (newDataset === dataset) return;
    setDataset(newDataset);
    setSelectedSite(null);
    setSites([]);
    setStateFilter('');
    setDistrictFilter('');
    setSearchText('');
  };

  const handleTabChange = (tab: DashboardTab) => {
    setActiveTab(tab);
    if (tab !== 'map') setSelectedSite(null);
  };

  const clearFilters = () => {
    setStateFilter('');
    setDistrictFilter('');
    setSearchText('');
  };

  const isIndia = dataset === 'india';
  const datasetLabel = isIndia ? 'Historical Candidate Sites' : 'Telemetry Stations';
  const activeFilter = isIndia ? stateFilter : districtFilter;
  const filterPlaceholder = isIndia ? 'Filter by state' : 'Filter by district';
  const displayedSites = useMemo(() => {
    const query = searchText.trim().toLowerCase();
    if (!query) return sites;
    return sites.filter(site => (
      site.candidate_site_id.toLowerCase().includes(query)
      || site.station_name?.toLowerCase().includes(query)
      || site.district?.toLowerCase().includes(query)
    ));
  }, [sites, searchText]);
  const mappedSiteCount = sites.filter(site => site.latitude != null && site.longitude != null).length;
  const conditionSiteCount = sites.filter(site => site.condition_state != null).length;
  const alertSiteCount = sites.filter(site => site.alert_event_state != null && site.alert_event_state !== 'NORMAL').length;
  const apiStatus = loading ? 'loading' : error ? 'error' : 'online';

  const headerActions = (
    <div className="flex flex-wrap items-center gap-1 rounded-lg bg-glass-bg p-1" role="group" aria-label="Dataset selection">
      <button
        type="button"
        aria-pressed={isIndia}
        onClick={() => handleDatasetChange('india')}
        className={`rounded-md px-3 py-1.5 text-xs font-medium transition-all duration-200 focus-visible:outline-none focus-glow ${isIndia
          ? 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-lg shadow-emerald-900/30'
          : 'text-text-secondary hover:text-text-primary hover:bg-glass-bg-hover'
        }`}
      >
        India Overview
      </button>
      <button
        type="button"
        aria-pressed={!isIndia}
        onClick={() => handleDatasetChange('maharashtra')}
        className={`rounded-md px-3 py-1.5 text-xs font-medium transition-all duration-200 focus-visible:outline-none focus-glow ${!isIndia
          ? 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-lg shadow-emerald-900/30'
          : 'text-text-secondary hover:text-text-primary hover:bg-glass-bg-hover'
        }`}
      >
        Maharashtra Telemetry
      </button>
    </div>
  );

  /* ── Stat card data ── */
  const stats = [
    { label: 'Sites returned', value: sites.length, gradient: 'from-emerald-500/20 to-teal-500/10', accent: 'text-emerald-400' },
    { label: 'Mapped locations', value: mappedSiteCount, gradient: 'from-blue-500/20 to-cyan-500/10', accent: 'text-blue-400' },
    { label: 'With condition data', value: conditionSiteCount, gradient: 'from-violet-500/20 to-purple-500/10', accent: 'text-violet-400' },
    { label: 'Non-normal alerts', value: alertSiteCount, gradient: 'from-amber-500/20 to-orange-500/10', accent: 'text-amber-400' },
  ];

  return (
    <Layout
      activeTab={activeTab}
      onTabChange={handleTabChange}
      apiStatus={apiStatus}
      headerActions={headerActions}
    >
      {/* ═══════════════════════════════════════════════════════════
          OVERVIEW TAB
         ═══════════════════════════════════════════════════════════ */}
      {activeTab === 'overview' && (
        <section className="h-full overflow-y-auto bg-surface-base" aria-label="Overview dashboard">
          <div className="mx-auto max-w-7xl space-y-8 px-4 py-6 sm:px-6 lg:px-8 animate-fade-in">
            {/* Page header */}
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-emerald-400">National groundwater monitoring</p>
                <h2 className="font-heading mt-1 text-2xl font-bold text-text-primary">Overview Dashboard</h2>
                <p className="mt-1 max-w-2xl text-sm text-text-secondary">
                  Deterministic site intelligence for {isIndia ? 'historical India observations' : 'Maharashtra telemetry'}.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setActiveTab('map')}
                className="btn-primary rounded-lg px-4 py-2 text-sm"
              >
                Open geospatial map
              </button>
            </div>

            {/* Error banner */}
            {error && (
              <div className="flex items-start gap-3 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300 animate-fade-in" role="alert">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-400" aria-hidden="true" />
                <p>{error}</p>
              </div>
            )}

            {/* Alert Center */}
            <AlertCenter onSelectAlert={handleAlertSelect} />

            {/* ── Stat cards ── */}
            <section aria-labelledby="coverage-heading">
              <div className="mb-3 flex items-center justify-between">
                <h3 id="coverage-heading" className="font-heading text-sm font-semibold text-text-primary">Dataset coverage</h3>
                {loading && <span className="text-xs text-text-muted animate-status-pulse">Updating…</span>}
              </div>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {stats.map((stat, i) => (
                  <div
                    key={stat.label}
                    className={`glass-panel rounded-xl p-4 hover-lift stagger-${i + 1} animate-fade-in`}
                  >
                    <div className={`absolute inset-0 rounded-xl bg-gradient-to-br ${stat.gradient} opacity-50`} />
                    <div className="relative">
                      <dt className="text-xs text-text-muted">{stat.label}</dt>
                      <dd className={`mt-1 font-heading text-2xl font-bold tabular-nums ${stat.accent}`}>{stat.value}</dd>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* Data context */}
            <section className="border-t border-glass-border pt-5" aria-labelledby="data-context-heading">
              <h3 id="data-context-heading" className="font-heading text-sm font-semibold text-text-primary">Data context</h3>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-text-secondary">
                {isIndia
                  ? 'India observations are historical and periodic. Candidate-site identifiers are analytical groupings; they are not verified physical station identities.'
                  : 'Maharashtra records are telemetry-oriented observations. Persistence forecasts describe the next valid observation and should not be interpreted as an official warning.'}
              </p>
            </section>
          </div>
        </section>
      )}

      {/* ═══════════════════════════════════════════════════════════
          MAP TAB
         ═══════════════════════════════════════════════════════════ */}
      {activeTab === 'map' && (
        <section className="flex min-h-0 flex-1 bg-surface-base" aria-label="Geospatial map">
          {/* ── Sidebar ── */}
          <aside className="z-1 flex w-48 shrink-0 flex-col border-r border-glass-border bg-surface-raised/80 backdrop-blur-xl sm:w-64 lg:w-72" aria-label="Site explorer">
            <div className="border-b border-glass-border p-4">
              <h2 className="font-heading text-xs font-semibold uppercase tracking-wider text-text-muted">{datasetLabel}</h2>
              <label className="sr-only" htmlFor="region-filter">{filterPlaceholder}</label>
              <div className="relative mt-3">
                <input
                  id="region-filter"
                  type="text"
                  placeholder={filterPlaceholder}
                  value={activeFilter}
                  onChange={event => isIndia ? setStateFilter(event.target.value) : setDistrictFilter(event.target.value)}
                  onKeyDown={event => {
                    if (event.key === 'Enter') loadSites(dataset, bounds, stateFilter, districtFilter);
                  }}
                  className="input-dark w-full rounded-lg px-3 py-2 pr-8 text-sm"
                />
                {activeFilter && (
                  <button
                    type="button"
                    onClick={() => isIndia ? setStateFilter('') : setDistrictFilter('')}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary transition-colors"
                    aria-label="Clear region filter"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
              <label className="sr-only" htmlFor="site-search">Search sites</label>
              <div className="relative mt-2">
                <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" aria-hidden="true" />
                <input
                  id="site-search"
                  type="search"
                  placeholder="Search ID, station, district"
                  value={searchText}
                  onChange={event => setSearchText(event.target.value)}
                  className="input-dark w-full rounded-lg py-2 pl-8 pr-3 text-sm"
                />
              </div>
              {(activeFilter || searchText) && (
                <button type="button" onClick={clearFilters} className="mt-2 text-xs font-medium text-emerald-400 underline underline-offset-2 hover:text-emerald-300 transition-colors">
                  Clear filters
                </button>
              )}
            </div>

            <div className="border-b border-glass-border px-4 py-2 text-xs text-text-muted" aria-live="polite">
              {loading ? (
                <span className="inline-flex items-center gap-2"><Loader2 className="h-3.5 w-3.5 animate-spin text-emerald-400" /> Loading sites</span>
              ) : error ? (
                <span className="text-red-400">Site data unavailable. See map details.</span>
              ) : (
                <><strong className="font-semibold text-text-primary">{displayedSites.length}</strong> {isIndia ? 'sites' : 'stations'} in view</>
              )}
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto" role="list" aria-label="Sites in current view">
              {!loading && !error && displayedSites.length > 0 ? displayedSites.slice(0, 200).map(site => (
                <button
                  key={site.candidate_site_id}
                  type="button"
                  role="listitem"
                  onClick={() => setSelectedSite(site)}
                  aria-pressed={selectedSite?.candidate_site_id === site.candidate_site_id}
                  aria-label={`Select site ${site.candidate_site_id}`}
                  className={`
                    w-full border-b border-glass-border px-4 py-3 text-left transition-all duration-150
                    hover:bg-glass-bg-hover focus-visible:outline-none focus-glow
                    ${selectedSite?.candidate_site_id === site.candidate_site_id
                      ? 'border-l-2 border-l-emerald-400 bg-emerald-500/10'
                      : ''
                    }
                  `}
                >
                  <span className="block truncate font-mono text-xs font-medium text-text-primary">{site.candidate_site_id}</span>
                  {site.station_name && <span className="mt-1 block truncate text-xs text-text-secondary">{site.station_name}</span>}
                  {(site.district || site.state) && <span className="block truncate text-xs text-text-muted">{[site.district, site.state].filter(Boolean).join(', ')}</span>}
                </button>
              )) : !loading && !error ? (
                <p className="px-4 py-5 text-sm text-text-muted">
                  {searchText || activeFilter ? 'No sites match these filters.' : 'No sites are available in this view.'}
                </p>
              ) : null}
              {!loading && displayedSites.length > 200 && (
                <p className="border-t border-glass-border px-4 py-3 text-xs text-text-muted">Showing the first 200 sites. Zoom in to narrow the results.</p>
              )}
            </div>
          </aside>

          {/* ── Map area ── */}
          <div className="relative min-w-0 flex-1 bg-surface-base">
            <MapView
              sites={sites}
              dataset={dataset}
              selectedSiteId={selectedSite?.candidate_site_id ?? null}
              selectedSite={selectedSite}
              onSiteSelect={setSelectedSite}
              onBoundsChange={handleBoundsChange}
            />
            {!loading && (error || sites.length === 0) && (
              <div className="pointer-events-none absolute inset-x-4 top-4 flex justify-center">
                <div className="glass-panel max-w-lg rounded-xl px-4 py-3" role={error ? 'alert' : 'status'}>
                  <h3 className="text-sm font-semibold text-text-primary">{error ? 'Site data unavailable' : 'No sites in this map view'}</h3>
                  <p className="mt-1 text-xs leading-relaxed text-text-secondary">{error || 'Zoom out or move the map to explore monitoring sites.'}</p>
                </div>
              </div>
            )}
            {selectedSite && (
              <InvestigationPanel
                site={selectedSite}
                dataset={dataset}
                onClose={() => setSelectedSite(null)}
                onReturnToOverview={() => setActiveTab('overview')}
                onSelectAlertSite={siteId => {
                  const alert = SAMPLE_ALERTS.find(a => a.candidate_site_id === siteId || a.id === siteId);
                  if (alert) handleAlertSelect(alert, false);
                }}
              />
            )}
          </div>
        </section>
      )}

      {/* ═══════════════════════════════════════════════════════════
          PREDICTIVE TAB
         ═══════════════════════════════════════════════════════════ */}
      {activeTab === 'predictive' && (
        <section className="h-full overflow-y-auto bg-surface-base" aria-label="Predictive analytics">
          <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6 lg:px-8 animate-fade-in">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-emerald-400">Model outputs</p>
              <h2 className="font-heading mt-1 text-2xl font-bold text-text-primary">Predictive Analytics</h2>
              <p className="mt-1 max-w-3xl text-sm leading-6 text-text-secondary">
                Forecasts are site-specific statistical estimates. They are not official groundwater warnings or guarantees of future water supply.
              </p>
            </div>

            {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300" role="alert">{error}</div>}
            <PredictiveAnalytics dataset={dataset} initialSiteId={selectedSite?.candidate_site_id} />
          </div>
        </section>
      )}

      {/* ═══════════════════════════════════════════════════════════
          ADVANCED TAB
         ═══════════════════════════════════════════════════════════ */}
      {activeTab === 'advanced' && (
        <section className="h-full overflow-hidden bg-surface-base" aria-label="Advanced multi-model forecast">
          <AdvancedForecastTab initialSiteId={selectedSite?.candidate_site_id} />
        </section>
      )}

      {/* ═══════════════════════════════════════════════════════════
          METHODOLOGY TAB
         ═══════════════════════════════════════════════════════════ */}
      {activeTab === 'methodology' && (
        <section className="h-full overflow-y-auto bg-surface-base" aria-label="Methodology and model deep-dive">
          <MethodologyTab />
        </section>
      )}
    </Layout>

  );
}

export default App;
