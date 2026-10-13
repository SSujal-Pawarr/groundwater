import React, { useState, useRef, useEffect } from 'react';
import { Info, X, ShieldAlert, Sparkles, Database, CheckCircle2 } from 'lucide-react';

interface Props {
  siteId: string;
  stationName?: string | null;
  observedCount?: number;
  dateRange?: string | null;
  metricType?: 'condition' | 'forecast' | 'stress' | 'general';
  customReason?: string;
  sparsePredictionAvailable?: boolean;
}

export const DataDiagnosticPopover: React.FC<Props> = ({
  siteId,
  stationName,
  observedCount = 0,
  dateRange,
  metricType = 'condition',
  customReason,
  sparsePredictionAvailable = true,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  // Click outside to close
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const getMetricExplanation = () => {
    switch (metricType) {
      case 'condition':
        return {
          title: 'Hydrological Condition Classification Standard',
          threshold: 'Requires ≥15 historical seasonal observations across at least 3 hydrological years.',
          scientificReason:
            'Parametric percentile binning (e.g., distinguishing the 20th vs 80th percentiles) in hard-rock aquifers is statistically unstable with fewer than 15 baseline points.',
          remedy:
            'Rather than abandoning assessment, a calibrated seasonal harmonic baseline is computed using available observations with expanded empirical uncertainty bounds.',
        };
      case 'forecast':
        return {
          title: 'Predictive Sequence Continuity Standard',
          threshold: 'Requires at least 30 consecutive days of recent telemetry observations.',
          scientificReason:
            'Deep recurrent sequence neural networks require a continuous sliding lag vector to establish hydraulic velocity and momentum.',
          remedy:
            'When sequential days have gaps, the platform automatically engages Fourier harmonic cycle modeling and persistence fallback bounds.',
        };
      case 'stress':
        return {
          title: 'Long-Term Structural Aquifer Stress Standard',
          threshold: 'Requires 5+ years of verified seasonal observations.',
          scientificReason:
            'Multi-year structural stress requires separating chronic multi-year drawdown from temporary single-season rainfall deficits.',
          remedy:
            'Short-term stress is estimated from local seasonal percentile deviation while preserving a transparent data provenance flag.',
        };
      default:
        return {
          title: 'Hydrogeological Data Completeness Audit',
          threshold: 'Standard baseline observation density.',
          scientificReason:
            customReason || 'Historical observation frequency is below standard multi-year parametric thresholds.',
          remedy:
            'Available data points are interpolated using regional Fourier harmonics rather than omitting the station.',
        };
    }
  };

  const exp = getMetricExplanation();

  return (
    <div className="relative inline-block" ref={popoverRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="inline-flex items-center gap-1 rounded-md bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-800 border border-amber-200/80 hover:bg-amber-100 hover:border-amber-300 transition-all focus:outline-none focus:ring-1 focus:ring-amber-400"
        aria-label={`View data diagnostics for ${siteId}`}
        aria-expanded={isOpen}
      >
        <Info className="h-3 w-3 text-amber-600" />
        <span>Data Diagnostics</span>
      </button>

      {isOpen && (
        <div
          role="dialog"
          aria-label="Data Diagnostics Details"
          className="absolute z-50 mt-1.5 left-0 w-80 sm:w-96 rounded-xl border border-amber-200 bg-white p-4 shadow-xl text-slate-800 animate-fade-in text-xs"
        >
          {/* Header */}
          <div className="flex items-start justify-between gap-2 border-b border-slate-100 pb-2.5">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-100 text-amber-800 shrink-0">
                <ShieldAlert className="h-4 w-4" />
              </div>
              <div>
                <h4 className="font-heading font-bold text-slate-900 text-xs">
                  {exp.title}
                </h4>
                <p className="text-[10px] text-slate-500 font-mono">
                  {stationName || siteId}
                </p>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="rounded-md p-1 text-slate-400 hover:text-slate-700 hover:bg-slate-100"
              aria-label="Close popover"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>

          {/* Diagnostic Details */}
          <div className="mt-3 space-y-2.5 leading-relaxed text-slate-600 text-[11px]">
            {/* Record Metrics */}
            <div className="rounded-lg bg-slate-50 p-2.5 border border-slate-200 flex justify-between items-center font-mono">
              <div>
                <span className="text-[10px] uppercase text-slate-500 block">Archived Samples</span>
                <span className="font-bold text-slate-900 text-xs">{observedCount} observation{observedCount !== 1 ? 's' : ''}</span>
              </div>
              {dateRange && (
                <div className="text-right">
                  <span className="text-[10px] uppercase text-slate-500 block">Span Window</span>
                  <span className="text-slate-700 text-xs">{dateRange}</span>
                </div>
              )}
            </div>

            {/* Threshold requirement */}
            <div>
              <span className="font-bold text-slate-800 flex items-center gap-1.5 text-xs text-amber-900">
                <Database className="h-3 w-3 text-amber-600" />
                Validation Requirement
              </span>
              <p className="mt-0.5 text-slate-600">{exp.threshold}</p>
            </div>

            {/* Hydrogeological reason */}
            <div>
              <span className="font-bold text-slate-800 flex items-center gap-1.5 text-xs">
                Hydrogeological Context
              </span>
              <p className="mt-0.5 text-slate-600">{exp.scientificReason}</p>
            </div>

            {/* Platform Remedy / Best-effort estimation */}
            {sparsePredictionAvailable && (
              <div className="rounded-lg bg-emerald-50/70 p-2.5 border border-emerald-200/80 text-emerald-950">
                <div className="flex items-center gap-1.5 font-bold text-emerald-900 text-xs">
                  <Sparkles className="h-3.5 w-3.5 text-emerald-600" />
                  Calibrated Sparse-Data Fallback Active
                </div>
                <p className="mt-1 text-[10px] text-emerald-800 leading-normal">
                  {exp.remedy}
                </p>
              </div>
            )}
          </div>

          <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-400">
            <span>Deterministic QC Protocol</span>
            <span className="flex items-center gap-1 text-emerald-700 font-medium">
              <CheckCircle2 className="h-3 w-3" /> Transparent Audit
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
