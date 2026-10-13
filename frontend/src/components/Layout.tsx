import type { ReactNode } from 'react';
import { Activity, BookOpen, BrainCircuit, ChartLine, Map, Waves } from 'lucide-react';

export type DashboardTab = 'overview' | 'map' | 'predictive' | 'advanced' | 'methodology';
type ApiStatus = 'loading' | 'online' | 'error';

interface LayoutProps {
  activeTab: DashboardTab;
  onTabChange: (tab: DashboardTab) => void;
  apiStatus: ApiStatus;
  headerActions?: ReactNode;
  children: ReactNode;
}

const tabs: { id: DashboardTab; label: string; icon: typeof Activity }[] = [
  { id: 'overview', label: 'Overview Dashboard', icon: Activity },
  { id: 'map', label: 'Geospatial Map', icon: Map },
  { id: 'predictive', label: 'Predictive Analytics', icon: ChartLine },
  { id: 'advanced', label: 'Advanced Forecast', icon: BrainCircuit },
  { id: 'methodology', label: 'Methodology & Model Deep-Dive', icon: BookOpen },
];


const statusConfig: Record<ApiStatus, { label: string; dotClass: string }> = {
  loading: { label: 'Checking API', dotClass: 'bg-amber-400 animate-status-pulse' },
  online: { label: 'API connected', dotClass: 'bg-emerald-400 animate-pulse-glow' },
  error: { label: 'API unavailable', dotClass: 'bg-red-500' },
};

export function Layout({ activeTab, onTabChange, apiStatus, headerActions, children }: LayoutProps) {
  const status = statusConfig[apiStatus];

  return (
    <div className="flex h-screen min-h-128 flex-col overflow-hidden bg-surface-base text-text-primary">
      {/* ── Header ── */}
      <header className="z-10 shrink-0 border-b border-glass-border bg-surface-raised/80 backdrop-blur-xl">
        <div className="mx-auto flex min-h-16 max-w-screen-2xl flex-wrap items-center justify-between gap-x-6 gap-y-3 px-4 py-3 sm:px-6">
          {/* Brand */}
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 shadow-lg shadow-emerald-900/20">
              <Waves className="h-5 w-5 text-white" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <h1 className="font-heading truncate text-sm font-semibold text-text-primary sm:text-base">
                Groundwater Intelligence Command Center
              </h1>
              <p className="hidden text-xs text-text-muted sm:block">
                India Groundwater Intelligence &amp; Early Warning Platform
              </p>
            </div>
          </div>

          {/* Right controls */}
          <div className="flex w-full flex-wrap items-center justify-between gap-3 sm:w-auto sm:justify-end">
            <div className="flex items-center gap-2 text-xs text-text-secondary" role="status" aria-live="polite">
              <span
                className={`h-2 w-2 rounded-full ${status.dotClass}`}
                aria-hidden="true"
              />
              {status.label}
            </div>
            {headerActions}
          </div>
        </div>

        {/* ── Navigation tabs ── */}
        <nav className="mx-auto max-w-screen-2xl overflow-x-auto px-4 sm:px-6" aria-label="Primary navigation">
          <div className="flex min-w-max gap-1" role="tablist" aria-label="Dashboard sections">
            {tabs.map(({ id, label, icon: Icon }) => {
              const selected = activeTab === id;
              return (
                <button
                  key={id}
                  id={`tab-${id}`}
                  type="button"
                  role="tab"
                  aria-selected={selected}
                  aria-controls="dashboard-tabpanel"
                  tabIndex={selected ? 0 : -1}
                  onClick={() => onTabChange(id)}
                  onKeyDown={event => {
                    const currentIndex = tabs.findIndex(tab => tab.id === id);
                    const targetIndex = event.key === 'ArrowRight'
                      ? (currentIndex + 1) % tabs.length
                      : event.key === 'ArrowLeft'
                        ? (currentIndex - 1 + tabs.length) % tabs.length
                        : event.key === 'Home'
                          ? 0
                          : event.key === 'End'
                            ? tabs.length - 1
                            : currentIndex;
                    if (targetIndex !== currentIndex) {
                      event.preventDefault();
                      const nextTab = tabs[targetIndex];
                      onTabChange(nextTab.id);
                      document.getElementById(`tab-${nextTab.id}`)?.focus();
                    }
                  }}
                  className={`
                    relative flex items-center gap-2 px-3 py-3 text-xs font-medium transition-all duration-200
                    focus-visible:outline-none focus-glow sm:px-4 sm:text-sm rounded-t-lg
                    ${selected
                      ? 'text-emerald-700 font-semibold bg-emerald-50/80'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/60'
                    }
                  `}
                >
                  <Icon className={`h-4 w-4 ${selected ? 'text-emerald-600' : 'text-slate-500'}`} aria-hidden="true" />
                  {label}
                  {/* Active indicator bar */}
                  <span
                    className={`
                      absolute bottom-0 left-2 right-2 h-0.5 rounded-full transition-all duration-300
                      ${selected
                        ? 'bg-gradient-to-r from-emerald-600 to-teal-600 opacity-100'
                        : 'bg-transparent opacity-0'
                      }
                    `}
                    aria-hidden="true"
                  />
                </button>
              );
            })}
          </div>
        </nav>
      </header>

      {/* ── Main content ── */}
      <main
        id="dashboard-tabpanel"
        role="tabpanel"
        aria-labelledby={`tab-${activeTab}`}
        className="flex min-h-0 flex-1 flex-col"
      >
        {children}
      </main>
    </div>
  );
}