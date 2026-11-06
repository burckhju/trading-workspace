import { describe, expect, it } from 'vitest';

import { reportItem } from '../../../test/realizedGrossFixtures';
import type { RealizedGrossItem } from '../types/api';
import { sellPlotCoordinate, sellPlotExtent } from './realizedGrossVisualization';

describe('SELL plotting coordinates preserve owner qualification and original money', () => {
  it.each([
    ['1e100', 1e100],
    ['-1e100', -1e100],
    ['1e-100', 1e-100],
    ['-1e-100', -1e-100],
    ['+1.25E+2', 125],
    ['.125', 0.125],
    ['12.', 12],
    ['12345678901234567890.123456789', 12345678901234567000],
  ] as const)(
    'accepts the finite graphical coordinate for %s without rewriting its strings',
    (raw, value) => {
      const item = reportItem('qualified', {
        realized_gross_pnl_delta: raw,
        realized_gross_pnl_delta_display: '12345678901234567890.12',
      });
      const original = structuredClone(item);

      expect(sellPlotCoordinate(item, 'EUR')).toEqual({
        value,
        explanation: 'Einzelner Geldpunkt',
      });
      expect(item).toEqual(original);
    },
  );

  it.each(['0', '-0.000', '+0e-900', '0e9999'])(
    'retains an exact %s as a real zero point',
    (raw) => {
      const coordinate = sellPlotCoordinate(
        reportItem('true-zero', {
          realized_gross_pnl_delta: raw,
          realized_gross_pnl_delta_display: '0.00',
        }),
        'EUR',
      );

      expect(coordinate.value === 0).toBe(true);
      expect(coordinate.explanation).toBe('Exakter Nullbeitrag · Punkt auf der Nulllinie');
    },
  );

  it.each([
    '1.0001e100',
    '-1.0001e100',
    '9.999e-101',
    '-9.999e-101',
    '1e400',
    '-1e400',
    '1e-400',
    '-1e-400',
    'NaN',
    'Infinity',
    '-Infinity',
    '',
    ' ',
    ' 12',
    '12 ',
    '0x10',
    '1,25',
  ])('keeps %j as table evidence instead of plotting an invented or unstable value', (raw) => {
    const item = reportItem('not-plottable', {
      realized_gross_pnl_delta: raw,
      realized_gross_pnl_delta_display: '0.00',
    });
    const original = structuredClone(item);

    expect(sellPlotCoordinate(item, 'EUR')).toEqual({
      value: null,
      explanation: 'Außerhalb der grafischen Zahlendarstellung · Originalwert bleibt erhalten',
    });
    expect(item).toEqual(original);
  });

  it.each([
    { status: 'EXCLUDED', explanation: 'Ausgeschlossen · kein Punkt' },
    { status: 'NOT_COMPUTABLE', explanation: 'Ungeklärt · kein Geldpunkt' },
  ] as const)('never promotes a supplied amount on a $status item', ({ status, explanation }) => {
    expect(sellPlotCoordinate(reportItem('not-qualified', { status }), 'EUR')).toEqual({
      value: null,
      explanation,
    });
  });

  it.each<Partial<RealizedGrossItem>>([
    { period_status: 'OUTSIDE_PERIOD' },
    { period_status: 'PERIOD_AMBIGUOUS' },
    { period_status: 'PERIOD_UNKNOWN' },
    { currency_code: 'USD' },
    { currency_code: null },
    { realized_gross_pnl_delta: null },
    { realized_gross_pnl_delta_display: null },
  ])('does not replace missing period, currency or value qualification: %j', (overrides) => {
    expect(sellPlotCoordinate(reportItem('inconsistent', overrides), 'EUR')).toEqual({
      value: null,
      explanation: 'Kein qualifizierter Geldwert für diese Grafik',
    });
  });

  it('does not infer EUR or a timestamp for a qualified date-only event', () => {
    const item = reportItem('date-only', {
      time_precision: 'DATE_ONLY',
      executed_at: null,
      executed_on: '2026-09-10',
      execution_timezone: 'America/New_York',
      possible_start_at: '2026-09-10T04:00:00Z',
      possible_end_at: '2026-09-11T04:00:00Z',
      currency_code: 'USD',
    });
    const original = structuredClone(item);

    expect(sellPlotCoordinate(item, 'EUR').value).toBeNull();
    expect(sellPlotCoordinate(item, 'USD').value).toBe(30);
    expect(item).toEqual(original);
    expect(item.executed_at).toBeNull();
  });

  it('uses raw money for a coordinate while preserving backend half-even display strings', () => {
    const positive = reportItem('rounded-positive', {
      realized_gross_pnl_delta: '0.005',
      realized_gross_pnl_delta_display: '0.00',
    });
    const negative = reportItem('rounded-negative', {
      realized_gross_pnl_delta: '-0.005',
      realized_gross_pnl_delta_display: '-0.00',
    });
    expect(sellPlotCoordinate(positive, 'EUR').value).toBe(0.005);
    expect(sellPlotCoordinate(negative, 'EUR').value).toBe(-0.005);
    expect(positive.realized_gross_pnl_delta_display).toBe('0.00');
    expect(negative.realized_gross_pnl_delta_display).toBe('-0.00');
  });
});

describe('graphical scale', () => {
  it('uses extrema of all supplied coordinates, not a financial total or a page aggregate', () => {
    const coordinates = [
      { value: -80, explanation: 'negative' },
      { value: 30, explanation: 'positive' },
      { value: null, explanation: 'unknown' },
      { value: 0, explanation: 'exact zero' },
    ];
    const original = structuredClone(coordinates);
    expect(sellPlotExtent(coordinates)).toBe(80);
    expect(coordinates).toEqual(original);
  });

  it('supplies an axis bound for an empty, unknown-only or exact-zero-only set without inventing data', () => {
    expect(sellPlotExtent([])).toBe(1);
    expect(sellPlotExtent([{ value: null, explanation: 'unknown' }])).toBe(1);
    expect(sellPlotExtent([{ value: 0, explanation: 'exact zero' }])).toBe(1);
  });
});
