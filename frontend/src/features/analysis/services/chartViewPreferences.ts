import type { ChartDisplayState } from '../types/charts';

export interface ChartViewPreferences {
  period: string;
  field: 'CLOSE' | 'ADJUSTED_CLOSE';
  display: ChartDisplayState;
}

const storageKey = 'trading-workspace.market-charts.presentation.v1';
export const chartPeriods = ['1', '3', '6', '12', '36', 'all'];

export function loadChartViewPreferences(): ChartViewPreferences {
  const fallback: ChartViewPreferences = {
    period: '3',
    field: 'CLOSE',
    display: { mode: null, singleKey: null, hiddenKeys: [] },
  };
  try {
    const raw: unknown = JSON.parse(window.localStorage.getItem(storageKey) ?? 'null');
    if (!raw || typeof raw !== 'object') return fallback;
    const value = raw as Record<string, unknown>;
    const display = value.display as Partial<ChartDisplayState> | undefined;
    return {
      period:
        typeof value.period === 'string' && chartPeriods.includes(value.period)
          ? value.period
          : fallback.period,
      field: value.field === 'ADJUSTED_CLOSE' ? 'ADJUSTED_CLOSE' : 'CLOSE',
      display: {
        mode:
          display?.mode && ['value', 'normalized', 'change_percent'].includes(display.mode)
            ? display.mode
            : null,
        singleKey: typeof display?.singleKey === 'string' ? display.singleKey : null,
        hiddenKeys: Array.isArray(display?.hiddenKeys)
          ? display.hiddenKeys.filter((key): key is string => typeof key === 'string').slice(0, 4)
          : [],
      },
    };
  } catch {
    return fallback;
  }
}

/** Only presentation is saved here. Workspace membership belongs to the backend. */
export function saveChartViewPreferences(value: ChartViewPreferences): void {
  try {
    window.localStorage.setItem(storageKey, JSON.stringify(value));
  } catch {
    // Browser storage can be unavailable; the current view remains fully usable.
  }
}
