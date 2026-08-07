import { beforeEach, describe, expect, it } from 'vitest';

import { loadAnalysisOverviewViews, saveAnalysisOverviewViews } from './savedViews';

describe('analysis overview saved views', () => {
  beforeEach(() => window.localStorage.clear());

  it('persists and restores valid user views', () => {
    const views = [
      {
        id: 'view-1',
        name: 'Gute Analysen',
        underlyingId: 'underlying-1',
        underlyingLabel: 'Siemens AG · SIE',
        status: 'COMPLETED',
        qualityStatus: 'GOOD',
        analysisTimeFrom: '',
        analysisTimeTo: '',
        sortBy: 'latest_analysis_time',
        sortDirection: 'desc',
      },
    ];
    saveAnalysisOverviewViews(views);
    expect(loadAnalysisOverviewViews()).toEqual(views);
  });

  it('returns an empty list for invalid persisted data', () => {
    window.localStorage.setItem('trading-workspace.analysis-overview-views.v1', '{invalid');
    expect(loadAnalysisOverviewViews()).toEqual([]);
  });
});
