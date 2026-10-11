import type { AlertState } from '../services/api';

export const ALERT_CONFIG: Record<AlertState, { color: string; bgColor: string; borderColor: string; icon: string; label: string; description: string }> = {
  NORMAL: {
    color: '#64748b',
    bgColor: 'rgba(100, 116, 139, 0.12)',
    borderColor: 'rgba(100, 116, 139, 0.3)',
    icon: '●',
    label: 'Normal',
    description: 'Within expected range'
  },
  WATCH: {
    color: '#fbbf24',
    bgColor: 'rgba(251, 191, 36, 0.12)',
    borderColor: 'rgba(251, 191, 36, 0.3)',
    icon: '◆',
    label: 'Watch',
    description: 'Approaching threshold'
  },
  WARNING: {
    color: '#f97316',
    bgColor: 'rgba(249, 115, 22, 0.12)',
    borderColor: 'rgba(249, 115, 22, 0.3)',
    icon: '▲',
    label: 'Warning',
    description: 'Threshold exceeded'
  },
  CRITICAL_STATISTICAL_DEVIATION: {
    color: '#ef4444',
    bgColor: 'rgba(239, 68, 68, 0.12)',
    borderColor: 'rgba(239, 68, 68, 0.3)',
    icon: '■',
    label: 'Critical Statistical Deviation',
    description: 'Statistically significant anomaly'
  },
  DATA_QUALITY_EVENT: {
    color: '#9ca3af',
    bgColor: 'rgba(156, 163, 175, 0.12)',
    borderColor: 'rgba(156, 163, 175, 0.3)',
    icon: '⬡',
    label: 'Data Quality Event',
    description: 'Observation quality flag raised'
  },
  INSUFFICIENT_HISTORY: {
    color: '#60a5fa',
    bgColor: 'rgba(96, 165, 250, 0.12)',
    borderColor: 'rgba(96, 165, 250, 0.3)',
    icon: '○',
    label: 'Insufficient History',
    description: 'Insufficient historical baseline'
  },
  SEQUENCE_GAPPED: {
    color: '#38bdf8',
    bgColor: 'rgba(56, 189, 248, 0.12)',
    borderColor: 'rgba(56, 189, 248, 0.3)',
    icon: '⋯',
    label: 'Sequence Gapped',
    description: 'Temporal gap in observations'
  }
};

export const getAlertColor = (state: AlertState): string => {
  return ALERT_CONFIG[state]?.color ?? '#000000';
};

export const getAlertLabel = (state: AlertState): string => {
  return ALERT_CONFIG[state]?.label ?? state.replace(/_/g, ' ');
};

export const getAlertConfig = (state: AlertState) => {
  return ALERT_CONFIG[state] ?? {
    color: '#000000', bgColor: 'transparent', borderColor: '#000000',
    icon: '?', label: state, description: ''
  };
};
