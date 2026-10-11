import { useEffect, useState, useCallback, useRef } from 'react';
import { fetchIndiaSites, fetchMHSites } from './services/api';
import type { CandidateSite, BBox } from './services/api';
import { MapView } from './components/MapView';
import { InvestigationPanel } from './components/InvestigationPanel';

import { Waves, Loader2, Search, X as XIcon, AlertCircle } from 'lucide-react';

function App() {
  const [dataset, setDataset] = useState<'india' | 'maharashtra'>('india');
  const [sites, setSites] = useState<CandidateSite[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [bounds, setBounds] = useState<BBox | undefined>();
  const [selectedSite, setSelectedSite] = useState<CandidateSite | null>(null);

  // Filter state — only using fields the API actually supports
  const [stateFilter, setStateFilter] = useState('');       // India: ?state=
  const [districtFilter, setDistrictFilter] = useState(''); // MH: ?district=
  const [searchText, setSearchText] = useState('');         // Client-side site ID search

  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadSites = useCallback(async (
    currentDataset: 'india' | 'maharashtra',
    currentBounds?: BBox,
    currentState?: string,
    currentDistrict?: string
  ) => {
    try {
      setLoading(true);
      setError(null);

      const data = currentDataset === 'india'
        ? await fetchIndiaSites(currentBounds, currentState || undefined)
        : await fetchMHSites(currentBounds, currentDistrict || undefined);

      setSites(data);
    } catch {
      setError('Failed to fetch sites. Is the backend running?');
      setSites([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load on dataset or filter change
  useEffect(() => {
    setSelectedSite(null);
    loadSites(dataset, bounds, stateFilter, districtFilter);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataset, stateFilter, districtFilter]);

  const handleBoundsChange = useCallback((newBounds: BBox) => {
    setBounds(newBounds);
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(() => {
      loadSites(dataset, newBounds, stateFilter, districtFilter);
    }, 500);
  }, [dataset, loadSites, stateFilter, districtFilter]);

  const handleDatasetToggle = (newDataset: 'india' | 'maharashtra') => {
    if (newDataset === dataset) return;
    setDataset(newDataset);
    setSelectedSite(null);
    setSites([]);
    setStateFilter('');
    setDistrictFilter('');
    setSearchText('');
  };

  const clearFilter = () => {
    setStateFilter('');
    setDistrictFilter('');
    setSearchText('');
  };

  // Client-side search by site ID or station name (only on already-loaded viewport results)
  const displayedSites = searchText.trim()
    ? sites.filter(s => {
        const q = searchText.toLowerCase();
        return (
          s.candidate_site_id.toLowerCase().includes(q) ||
          (s.station_name && s.station_name.toLowerCase().includes(q)) ||
          (s.district && s.district.toLowerCase().includes(q))
        );
      })
    : sites;

  const isIndia = dataset === 'india';
  const datasetLabel = isIndia ? 'Historical Candidate Sites' : 'Telemetry Stations';
  const activeFilter = isIndia ? stateFilter : districtFilter;
  const filterPlaceholder = isIndia ? 'Filter by state…' : 'Filter by district…';

  return (
    <div className="flex flex-col h-screen bg-slate-950 text-slate-50 overflow-hidden">

      {/* Header */}
      <header className="h-14 border-b border-slate-800 bg-slate-900 flex items-center justify-between px-4 z-10 shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2.5">
            <Waves className="w-5 h-5 text-cyan-400" aria-hidden="true" />
            <div className="flex flex-col">
              <h1 className="font-semibold text-xs tracking-widest text-slate-200 uppercase">
                Groundwater Intelligence Command Center
              </h1>
              <span className="text-[10px] text-slate-400 font-medium">India Groundwater Intelligence & Early Warning Platform</span>
            </div>
          </div>
          
          <div className="h-8 w-px bg-slate-800 mx-2"></div>
          
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5">
              <div className={`w-1.5 h-1.5 rounded-full ${error ? 'bg-red-500' : 'bg-emerald-500'}`}></div>
              <span className="text-[10px] text-slate-400 font-medium uppercase">{error ? 'API ERROR' : 'API ONLINE'}</span>
            </div>
            <div className="text-[10px] text-slate-500 font-medium">
              Data: {isIndia ? 'Historical / Periodic' : 'Telemetry / Historical'}
            </div>
          </div>
        </div>

        {/* Dataset switcher */}
        <div
          className="flex items-center bg-slate-950 rounded p-0.5 border border-slate-800"
          role="tablist"
          aria-label="Dataset selection"
        >
          <button
            role="tab"
            aria-selected={isIndia}
            onClick={() => handleDatasetToggle('india')}
            className={`px-3 py-1 text-xs font-medium rounded transition-colors focus:outline-none focus:ring-1 focus:ring-blue-500 ${
              isIndia ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            India Overview
          </button>
          <button
            role="tab"
            aria-selected={!isIndia}
            onClick={() => handleDatasetToggle('maharashtra')}
            className={`px-3 py-1 text-xs font-medium rounded transition-colors focus:outline-none focus:ring-1 focus:ring-blue-500 ${
              !isIndia ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Maharashtra Telemetry
          </button>
        </div>
      </header>

      {/* Main */}
      <div className="flex flex-1 relative overflow-hidden">

        {/* Left Sidebar */}
        <aside
          className="w-60 bg-slate-900 border-r border-slate-800 flex flex-col z-10 shrink-0"
          aria-label="Site explorer"
        >
          {/* Sidebar header */}
          <div className="px-3 pt-3 pb-2 border-b border-slate-800">
            <div className="text-[10px] uppercase tracking-widest text-slate-500 font-medium mb-2">
              {datasetLabel}
            </div>

            {/* API-backed filter */}
            <div className="relative mb-2">
              <input
                type="text"
                placeholder={filterPlaceholder}
                value={activeFilter}
                onChange={e => {
                  if (isIndia) setStateFilter(e.target.value);
                  else setDistrictFilter(e.target.value);
                }}
                onKeyDown={e => {
                  if (e.key === 'Enter') {
                    loadSites(dataset, bounds, stateFilter, districtFilter);
                  }
                }}
                className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1 text-xs text-slate-300 placeholder:text-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                aria-label={filterPlaceholder}
              />
              {activeFilter && (
                <button
                  onClick={() => {
                    if (isIndia) setStateFilter(''); else setDistrictFilter('');
                  }}
                  className="absolute right-1.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                  aria-label="Clear filter"
                >
                  <XIcon className="w-3 h-3" />
                </button>
              )}
            </div>

            {/* Client-side text search */}
            <div className="relative">
              <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-600" aria-hidden="true" />
              <input
                type="text"
                placeholder="Search ID / name…"
                value={searchText}
                onChange={e => setSearchText(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded pl-6 pr-2.5 py-1 text-xs text-slate-300 placeholder:text-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                aria-label="Search site ID or station name"
              />
              {searchText && (
                <button
                  onClick={() => setSearchText('')}
                  className="absolute right-1.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                  aria-label="Clear search"
                >
                  <XIcon className="w-3 h-3" />
                </button>
              )}
            </div>

            {(activeFilter || searchText) && (
              <button
                onClick={clearFilter}
                className="mt-1.5 text-[10px] text-slate-500 hover:text-slate-300 underline underline-offset-2"
              >
                Clear all filters
              </button>
            )}
          </div>

          {/* Viewport summary */}
          <div className="px-3 py-2 border-b border-slate-800/50 bg-slate-950/30">
            {loading ? (
              <div className="flex items-center gap-1.5 text-slate-600">
                <Loader2 className="w-3 h-3 animate-spin" />
                <span className="text-xs">Loading…</span>
              </div>
            ) : error ? (
              <div className="flex items-center gap-1.5 text-red-400 text-xs" role="alert">
                <AlertCircle className="w-3 h-3 shrink-0" />
                <span>{error}</span>
              </div>
            ) : (
              <div className="text-xs text-slate-500">
                <span className="text-slate-300 font-semibold tabular-nums">{displayedSites.length}</span>
                {searchText && sites.length !== displayedSites.length && (
                  <span> of {sites.length}</span>
                )}
                <span> {isIndia ? 'site' : 'station'}{displayedSites.length !== 1 ? 's' : ''} in view</span>
              </div>
            )}
          </div>

          {/* Site list */}
          <div className="flex-1 overflow-y-auto" role="list" aria-label="Sites in current viewport">
            {!loading && !error && displayedSites.length > 0 ? (
              displayedSites.slice(0, 200).map(site => (
                <button
                  key={site.candidate_site_id}
                  role="listitem"
                  onClick={() => setSelectedSite(site)}
                  className={`w-full text-left px-3 py-2 border-b border-slate-800/40 hover:bg-slate-800/50 transition-colors focus:outline-none focus:bg-slate-800/50 ${
                    selectedSite?.candidate_site_id === site.candidate_site_id
                      ? 'bg-blue-900/30 border-l-2 border-l-blue-500'
                      : ''
                  }`}
                  aria-pressed={selectedSite?.candidate_site_id === site.candidate_site_id}
                  aria-label={`Select site ${site.candidate_site_id}`}
                >
                  <div
                    className="text-xs font-mono text-slate-300 truncate"
                    title={site.candidate_site_id}
                  >
                    {site.candidate_site_id}
                  </div>
                  {site.station_name && (
                    <div className="text-[10px] text-slate-500 truncate mt-0.5">{site.station_name}</div>
                  )}
                  {(site.district || site.state) && (
                    <div className="text-[10px] text-slate-600 truncate">
                      {[site.district, site.state].filter(Boolean).join(', ')}
                    </div>
                  )}
                </button>
              ))
            ) : !loading && !error ? (
              <div className="p-3 text-xs text-slate-600 italic">
                {searchText || activeFilter ? 'No sites match the current filter.' : 'Move the map to explore sites.'}
              </div>
            ) : null}
            {!loading && displayedSites.length > 200 && (
              <div className="px-3 py-2 text-[10px] text-slate-600 italic border-t border-slate-800/40">
                Showing first 200 of {displayedSites.length}. Zoom in for more precise results.
              </div>
            )}
          </div>
        </aside>

        {/* Map */}
        <div className="flex-1 relative">
          <MapView
            sites={sites}
            dataset={dataset}
            selectedSiteId={selectedSite?.candidate_site_id ?? null}
            onSiteSelect={setSelectedSite}
            onBoundsChange={handleBoundsChange}
          />
        </div>

        {/* Investigation Drawer */}
        {selectedSite && (
          <InvestigationPanel
            site={selectedSite}
            dataset={dataset}
            onClose={() => setSelectedSite(null)}
          />
        )}
        

      </div>
    </div>
  );
}

export default App;
