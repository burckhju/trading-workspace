import type { RealizedGrossItem } from '../types/api';

export interface SellPlotCoordinate {
  value: number | null;
  explanation: string;
}

/**
 * Presentation only: no money totals, rounding, currency resolution or period
 * qualification. Exact backend strings remain the source of every money label.
 * The bounded coordinate range keeps linear-scale arithmetic finite and stable.
 */
export function sellPlotCoordinate(
  item: RealizedGrossItem,
  reportCurrency: string,
): SellPlotCoordinate {
  if (item.status === 'EXCLUDED') {
    return { value: null, explanation: 'Ausgeschlossen · kein Punkt' };
  }
  if (item.status !== 'USABLE') {
    return { value: null, explanation: 'Ungeklärt · kein Geldpunkt' };
  }
  if (
    item.period_status !== 'IN_PERIOD' ||
    item.currency_code !== reportCurrency ||
    item.realized_gross_pnl_delta === null ||
    item.realized_gross_pnl_delta_display === null
  ) {
    return { value: null, explanation: 'Kein qualifizierter Geldwert für diese Grafik' };
  }
  const raw = item.realized_gross_pnl_delta;
  const validDecimal = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/u.test(raw);
  const value = Number(raw);
  const nonzero = /[1-9]/u.test(raw.split(/[eE]/u)[0]);
  if (
    !validDecimal ||
    !Number.isFinite(value) ||
    (value === 0 && nonzero) ||
    Math.abs(value) > 1e100 ||
    (value !== 0 && Math.abs(value) < 1e-100)
  ) {
    return {
      value: null,
      explanation: 'Außerhalb der grafischen Zahlendarstellung · Originalwert bleibt erhalten',
    };
  }
  return {
    value,
    explanation:
      value === 0 ? 'Exakter Nullbeitrag · Punkt auf der Nulllinie' : 'Einzelner Geldpunkt',
  };
}

/** A stable axis across local pages; extrema are graphical bounds, never a sum. */
export function sellPlotExtent(coordinates: SellPlotCoordinate[]): number {
  return (
    coordinates.reduce(
      (extent, coordinate) => Math.max(extent, Math.abs(coordinate.value ?? 0)),
      0,
    ) || 1
  );
}
