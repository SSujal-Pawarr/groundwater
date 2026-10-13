import { TriangleAlert, MapPin, ExternalLink, ArrowRight } from 'lucide-react';

export type AlertType = 'Drought' | 'Flood' | 'Severe Stress';
export type AlertSeverity = 'Critical' | 'Warning';

export interface AlertRecord {
  id: string;
  candidate_site_id: string;
  location: string;
  village?: string;
  district: string;
  region: string;
  stationName: string;
  lat: number;
  lon: number;
  alertType: AlertType;
  severity: AlertSeverity;
  lastUpdated: string;
}

export const SAMPLE_ALERTS: AlertRecord[] = [
  {
    id: 'MH-NAN-008',
    candidate_site_id: 'MH_AALEGAON',
    location: 'Aalegaon Village, Nanded',
    village: 'Aalegaon',
    district: 'Nanded',
    region: 'Maharashtra',
    stationName: 'Aalegaon Telemetry Station',
    lat: 19.15,
    lon: 77.30,
    alertType: 'Flood',
    severity: 'Critical',
    lastUpdated: '2026-10-11T08:45:00+05:30',
  },
  {
    id: 'MH-NAS-014',
    candidate_site_id: 'MH_DUGAON',
    location: 'Dugaon Village, Nashik',
    village: 'Dugaon',
    district: 'Nashik',
    region: 'Maharashtra',
    stationName: 'Dugaon Station',
    lat: 19.99,
    lon: 73.78,
    alertType: 'Flood',
    severity: 'Critical',
    lastUpdated: '2026-10-11T08:20:00+05:30',
  },
  {
    id: 'MH-JAL-027',
    candidate_site_id: 'MH_ERANDOL',
    location: 'Erandol Village, Jalgaon',
    village: 'Erandol',
    district: 'Jalgaon',
    region: 'Maharashtra',
    stationName: 'Erandol Station',
    lat: 20.92,
    lon: 75.33,
    alertType: 'Flood',
    severity: 'Critical',
    lastUpdated: '2026-10-11T07:55:00+05:30',
  },
  {
    id: 'IN-BEE-112',
    candidate_site_id: 'MH_MAJALGAON',
    location: 'Majalgaon Village, Beed',
    village: 'Majalgaon',
    district: 'Beed',
    region: 'Maharashtra',
    stationName: 'Majalgaon Station',
    lat: 19.15,
    lon: 76.22,
    alertType: 'Drought',
    severity: 'Warning',
    lastUpdated: '2026-10-11T07:30:00+05:30',
  },
  {
    id: 'IN-PUN-043',
    candidate_site_id: 'MH_BARAMATI',
    location: 'Baramati Locality, Pune',
    village: 'Baramati',
    district: 'Pune',
    region: 'Maharashtra',
    stationName: 'Baramati Station',
    lat: 18.15,
    lon: 74.58,
    alertType: 'Severe Stress',
    severity: 'Warning',
    lastUpdated: '2026-10-11T06:50:00+05:30',
  },
];

const severityStyles: Record<AlertSeverity, { border: string; bg: string; text: string; glow: string }> = {
  Critical: {
    border: 'border-red-500/40',
    bg: 'bg-red-500/15',
    text: 'text-red-400',
    glow: 'shadow-red-500/20',
  },
  Warning: {
    border: 'border-amber-500/40',
    bg: 'bg-amber-500/15',
    text: 'text-amber-400',
    glow: 'shadow-amber-500/20',
  },
};

const timestampFormatter = new Intl.DateTimeFormat('en-IN', {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  timeZone: 'Asia/Kolkata',
  timeZoneName: 'short',
});

interface Props {
  onSelectAlert?: (alert: AlertRecord, openNewTab?: boolean) => void;
}

export function AlertCenter({ onSelectAlert }: Props) {
  const criticalCount = SAMPLE_ALERTS.filter(alert => alert.severity === 'Critical').length;

  return (
    <section aria-labelledby="alert-center-heading" className="space-y-4 animate-fade-in stagger-2">
      {/* Critical banner */}
      <div className="flex items-start justify-between gap-3 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 shadow-xs" role="status">
        <div className="flex items-start gap-3">
          <TriangleAlert className="mt-0.5 h-5 w-5 shrink-0 text-red-400" aria-hidden="true" />
          <div>
            <p className="text-sm font-semibold text-red-300">
              {criticalCount} Critical Hydrogeological Warnings Active
            </p>
            <p className="mt-0.5 text-xs text-red-400/80">
              Click any village or monitoring station below to automatically zoom and inspect its aquifer status on the Geospatial Map.
            </p>
          </div>
        </div>
      </div>

      {/* Section header */}
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h3 id="alert-center-heading" className="font-heading text-sm font-semibold text-text-primary">
            Aquifer Alert &amp; Anomaly Center
          </h3>
          <p className="mt-1 text-xs text-text-muted">
            Prioritized village monitoring locations with detected groundwater anomalies. Click to investigate.
          </p>
        </div>
        <span className="rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-emerald-400">
          Interactive Geospatial Routing
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto glass-panel rounded-xl border border-glass-border">
        <table className="w-full min-w-[44rem] border-collapse text-left text-sm">
          <caption className="sr-only">Groundwater alerts by village location, alert type, severity, and interactive geospatial routing</caption>
          <thead>
            <tr className="border-b border-glass-border bg-surface-elevated/40">
              <th scope="col" className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-text-muted">Village / Station Location</th>
              <th scope="col" className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-text-muted">Alert Condition</th>
              <th scope="col" className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-text-muted">Severity Rating</th>
              <th scope="col" className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-text-muted">Last Updated</th>
              <th scope="col" className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-text-muted text-right">Geospatial Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-glass-border">
            {SAMPLE_ALERTS.map(alert => {
              const severity = severityStyles[alert.severity];
              return (
                <tr
                  key={alert.id}
                  onClick={() => onSelectAlert?.(alert, false)}
                  className="group transition-all duration-150 hover:bg-emerald-500/10 cursor-pointer"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-500/15 text-emerald-400 group-hover:bg-emerald-500/25 transition-colors">
                        <MapPin className="h-3.5 w-3.5" />
                      </div>
                      <div>
                        <span className="block font-medium text-text-primary group-hover:text-emerald-300 transition-colors">
                          {alert.location}
                        </span>
                        <span className="mt-0.5 block text-xs text-text-muted font-mono">
                          {alert.stationName} · [{alert.candidate_site_id}]
                        </span>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-text-secondary font-medium">
                    {alert.alertType}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-md border px-2 py-0.5 text-xs font-semibold shadow-2xs ${severity.border} ${severity.bg} ${severity.text} ${severity.glow}`}>
                      {alert.severity}
                    </span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-xs text-text-muted">
                    <time dateTime={alert.lastUpdated}>
                      {timestampFormatter.format(new Date(alert.lastUpdated))}
                    </time>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="inline-flex items-center gap-1.5" onClick={e => e.stopPropagation()}>
                      <button
                        type="button"
                        onClick={() => onSelectAlert?.(alert, false)}
                        className="inline-flex items-center gap-1 rounded-lg bg-emerald-600/20 px-2.5 py-1 text-xs font-medium text-emerald-300 border border-emerald-500/30 hover:bg-emerald-600/30 transition-all focus:outline-none focus:ring-1 focus:ring-emerald-400"
                        title="Zoom to station on Geospatial Map"
                      >
                        <span>Inspect on Map</span>
                        <ArrowRight className="h-3 w-3" />
                      </button>
                      <button
                        type="button"
                        onClick={() => onSelectAlert?.(alert, true)}
                        className="rounded-lg p-1 text-text-muted hover:text-text-primary hover:bg-glass-bg-hover transition-colors"
                        title="Open Geospatial Map in new browser window"
                        aria-label={`Open map for ${alert.location} in new tab`}
                      >
                        <ExternalLink className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}