import type { ChartDisplayMode, ChartPoint, ChartSeries } from '../types/charts';

export interface ChartPlotRow {
  date: string;
  day: number;
  values: (number | null)[];
  points: (ChartPoint | null)[];
}

/** Plot coordinates only: all financial values and gap decisions come from the owner. */
export function chartPlotRows(series: ChartSeries[], mode: ChartDisplayMode): ChartPlotRow[] {
  const dates = new Set(series.flatMap((item) => item.points.map((point) => point.trading_date)));
  for (const item of series) {
    item.points.forEach((point) => {
      if (point.gap_before) {
        const previousCalendarDay = new Date(point.trading_date + 'T00:00:00Z');
        previousCalendarDay.setUTCDate(previousCalendarDay.getUTCDate() - 1);
        dates.add(previousCalendarDay.toISOString().slice(0, 10));
      }
    });
  }
  const maps = series.map(
    (item) => new Map(item.points.map((point) => [point.trading_date, point])),
  );
  return [...dates].sort().map((date) => {
    const points = maps.map((map) => map.get(date) ?? null);
    return {
      date,
      day: Date.parse(date + 'T00:00:00Z') / 86400000,
      points,
      values: points.map((point) => {
        if (point?.[mode] == null) return null;
        const coordinate = Number(point[mode]);
        return Number.isFinite(coordinate) ? coordinate : null;
      }),
    };
  });
}
