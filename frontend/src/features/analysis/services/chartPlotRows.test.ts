import { describe, expect, it } from 'vitest';
import { chartSeries } from '../../../test/chartFixtures';
import { chartPlotRows } from './chartPlotRows';

describe('chartPlotRows', () => {
  it('preserves backend values and explicit gaps without inventing prices or holiday rules', () => {
    const series = chartSeries();
    series.points = [
      { ...series.points[0], trading_date: '2026-09-04', value: '7688.6222000000' },
      {
        ...series.points[1],
        trading_date: '2026-09-08',
        value: '7353.7284000000',
        gap_before: true,
      },
    ];
    const before = structuredClone(series);
    const rows = chartPlotRows([series], 'value');
    expect(rows.map((row) => [row.date, row.values[0]])).toEqual([
      ['2026-09-04', 7688.6222],
      ['2026-09-07', null],
      ['2026-09-08', 7353.7284],
    ]);
    expect(rows[0].points[0]?.value).toBe('7688.6222000000');
    expect(rows[1].points[0]).toBeNull();
    expect(series).toEqual(before);
    series.points[1].gap_before = false;
    expect(chartPlotRows([series], 'value')).toHaveLength(2);
  });

  it('keeps zero distinct from missing and nonfinite coordinates while retaining original evidence', () => {
    const series = chartSeries();
    series.points[0].value = '0';
    series.points[1].value = null;
    series.points[2].value = '1e999';
    expect(chartPlotRows([series], 'value').map((row) => row.values[0])).toEqual([0, null, null]);
    expect(chartPlotRows([series], 'value')[2].points[0]?.value).toBe('1e999');
    series.points[0].normalized = '79.12345678';
    expect(chartPlotRows([series], 'normalized')[0].values[0]).toBe(79.12345678);
  });
});
