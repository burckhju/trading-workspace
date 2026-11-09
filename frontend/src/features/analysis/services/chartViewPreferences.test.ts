import { beforeEach, describe, expect, it, vi } from 'vitest';
import { loadChartViewPreferences, saveChartViewPreferences } from './chartViewPreferences';

beforeEach(() => window.localStorage.clear());

describe('chart presentation preferences', () => {
  it('restores presentation without persisting a frozen end date or backend membership', () => {
    const value = {
      period: '12',
      field: 'ADJUSTED_CLOSE' as const,
      display: {
        mode: 'change_percent' as const,
        singleKey: 'listing:one',
        hiddenKeys: ['listing:two'],
      },
    };
    saveChartViewPreferences(value);
    expect(loadChartViewPreferences()).toEqual(value);
    expect(Object.keys(loadChartViewPreferences())).toEqual(['period', 'field', 'display']);
  });

  it('does not break the page for invalid or unavailable browser storage', () => {
    window.localStorage.setItem('trading-workspace.market-charts.presentation.v1', '{broken');
    expect(loadChartViewPreferences().period).toBe('3');
    window.localStorage.setItem(
      'trading-workspace.market-charts.presentation.v1',
      JSON.stringify({
        period: 'invalid',
        field: 'other',
        display: { mode: 'profit', singleKey: 8, hiddenKeys: ['a', null, 'b'] },
      }),
    );
    expect(loadChartViewPreferences()).toEqual({
      period: '3',
      field: 'CLOSE',
      display: { mode: null, singleKey: null, hiddenKeys: ['a', 'b'] },
    });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementationOnce(() => {
      throw new Error('unavailable');
    });
    expect(() => saveChartViewPreferences(loadChartViewPreferences())).not.toThrow();
  });
});
