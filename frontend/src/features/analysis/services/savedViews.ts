export type AnalysisOverviewView = {
  id: string;
  name: string;
  underlyingId: string;
  underlyingLabel: string;
  status: string;
  qualityStatus: string;
  analysisTimeFrom: string;
  analysisTimeTo: string;
  sortBy: string;
  sortDirection: string;
};

const storageKey = 'trading-workspace.analysis-overview-views.v1';

export function loadAnalysisOverviewViews(): AnalysisOverviewView[] {
  try {
    const value = window.localStorage.getItem(storageKey);
    if (!value) return [];
    const parsed: unknown = JSON.parse(value);
    return Array.isArray(parsed) ? parsed.filter(isView) : [];
  } catch {
    return [];
  }
}

export function saveAnalysisOverviewViews(views: AnalysisOverviewView[]): void {
  window.localStorage.setItem(storageKey, JSON.stringify(views));
}

function isView(value: unknown): value is AnalysisOverviewView {
  if (typeof value !== 'object' || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return [
    'id',
    'name',
    'underlyingId',
    'underlyingLabel',
    'status',
    'qualityStatus',
    'analysisTimeFrom',
    'analysisTimeTo',
    'sortBy',
    'sortDirection',
  ].every((key) => typeof candidate[key] === 'string');
}
