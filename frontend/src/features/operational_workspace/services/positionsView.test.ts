import { position } from '../../../test/positionFixture';
import {
  decimalUnits,
  defaultPositionsView as defaults,
  formatUnits,
  hasAlert,
  hasDataProblem,
  money,
  numberLabel,
  pnlClass,
  portfolioTotals,
  positionTone,
  purchaseDate,
  readPositionsView,
  savePositionsView,
  positionsViewKey,
  timeLabel,
  visiblePositions,
} from './positionsView';
import { signalLabel, statusLabel } from './statusLabels';

beforeEach(() => sessionStorage.clear());
it('keeps exact decimals and scientific zero without binary arithmetic or silent precision loss', () => {
  expect(decimalUnits('0.1')! + decimalUnits('0.2')!).toBe(decimalUnits('0.3'));
  expect(decimalUnits('0E-10')).toBe(0n);
  expect(decimalUnits('1.00000000000')).toBe(decimalUnits('1'));
  for (const v of [
    null,
    undefined,
    '',
    'NaN',
    'Infinity',
    '1E100',
    '0.00000000001',
    '1'.repeat(121),
  ])
    expect(decimalUnits(v)).toBeNull();
  expect(formatUnits(decimalUnits('-2.005')!)).toBe('−2,01');
  expect(formatUnits(decimalUnits('9007199254740993.01')!)).toBe('9.007.199.254.740.993,01');
  expect(money(null, 'CHF')).toBe('—');
  expect(money('0', null)).toContain('Währung ungeklärt');
  expect(numberLabel('0')).toBe('0');
  expect(numberLabel('100')).toBe('100');
  expect(numberLabel('0.0000000001')).toBe('0,0000000001');
  expect(numberLabel(null)).toBe('—');
  expect(pnlClass(null)).toBe('text-slate-300');
  expect(pnlClass('0')).toBe('text-slate-300');
});
it('validates stored preferences and tolerates unavailable storage', () => {
  expect(readPositionsView()).toEqual(defaults);
  sessionStorage.setItem(positionsViewKey, 'broken');
  expect(readPositionsView()).toEqual(defaults);
  sessionStorage.setItem(
    positionsViewKey,
    JSON.stringify({ filter: '__proto__', sort: 'oops', page: -5, pageSize: 12 }),
  );
  expect(readPositionsView()).toEqual(defaults);
  const v = {
    ...defaults,
    query: 'USD',
    filter: 'gains' as const,
    sort: 'quantity' as const,
    descending: true,
    pageSize: 50 as const,
    page: 5,
  };
  savePositionsView(v);
  expect(readPositionsView()).toEqual(v);
  const write = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('disabled');
  });
  expect(() => savePositionsView(defaults)).not.toThrow();
  write.mockRestore();
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
    throw new Error('disabled');
  });
  expect(readPositionsView()).toEqual(defaults);
});
it('never turns stale/missing critical projections into a confirmed critical signal', () => {
  const p = position({
    position_signal: {
      ...position().position_signal!,
      quality_status: 'STALE',
      alert_level: 'CRITICAL',
    },
  });
  expect(hasAlert(p)).toBe(false);
  expect(hasDataProblem(p)).toBe(true);
  expect(positionTone(p)).toBe('data');
  expect(
    positionTone(
      position({ position_signal: { ...position().position_signal!, alert_level: 'ATTENTION' } }),
    ),
  ).toBe('attention');
  expect(
    positionTone(
      position({ position_signal: { ...position().position_signal!, alert_level: 'CRITICAL' } }),
    ),
  ).toBe('critical');
  expect(
    positionTone(position({ open_alert_count: 1, open_alert_types: ['TARGET_REACHED'] })),
  ).toBe('attention');
});
it.each(['product', 'purchased', 'quantity', 'value', 'pnl', 'quote'] as const)(
  'sorts %s both ways across the whole list, with missing always last',
  (sort) => {
    const a = position({
      product_name: 'A',
      position_id: 'a',
      open_quantity: 1,
      opened_on: '2026-08-01',
      market_value: '1',
      unrealized_gross_pnl: '-1',
      quote_observed_at: '2026-08-01T09:00:00Z',
    });
    const b = position({
      product_name: 'B',
      position_id: 'b',
      open_quantity: 2,
      opened_on: '2026-08-02',
      market_value: '2',
      unrealized_gross_pnl: '0',
      quote_observed_at: '2026-08-02T09:00:00Z',
    });
    expect(visiblePositions([b, a], { ...defaults, sort })[0]).toBe(a);
    expect(visiblePositions([a, b], { ...defaults, sort, descending: true })[0]).toBe(b);
    if (['value', 'pnl', 'quote'].includes(sort)) {
      const missing = position({
        position_id: 'missing',
        market_value: null,
        unrealized_gross_pnl: null,
        quote_observed_at: null,
      });
      expect(
        visiblePositions([missing, b, a], { ...defaults, sort, descending: true }).at(-1),
      ).toBe(missing);
    }
  },
);
it('separates currencies during sort and counts incomplete valuation groups without fake zeros', () => {
  const eur = position({ position_id: 'eur', market_value: '1', quote_observed_at: null });
  const chf = position({ position_id: 'chf', valuation_currency: 'CHF', market_value: '100' });
  expect(visiblePositions([eur, chf], { ...defaults, sort: 'value', descending: true })[0]).toBe(
    chf,
  );
  const result = portfolioTotals([
    eur,
    chf,
    position({ position_id: 'empty', market_value: null, unrealized_gross_pnl: null }),
  ]);
  expect(result[1][1]).toMatchObject({ count: 2, valued: 1, pnlCount: 1, unknownTime: 1 });
});
it('preserves stored calendar date without timezone conversion and labels all quality states', () => {
  expect(purchaseDate(position({ opened_on: '2026-08-01', opened_at: 'invalid' }))).toBe(
    '2026-08-01',
  );
  expect(purchaseDate(position({ opened_on: null, opened_at: 'invalid' }))).toBeNull();
  expect(purchaseDate(position({ opened_on: null }))).toMatch(/^2026-09-08$/);
  expect(timeLabel('invalid')).toBe('Unbekannt');
  expect(timeLabel(null)).toBe('Unbekannt');
  for (const status of [
    'OK',
    'AVAILABLE',
    'LAST_AVAILABLE',
    'INDICATIVE',
    'STALE',
    'MISSING',
    'INSUFFICIENT',
    'UNAVAILABLE',
    'ERROR',
  ])
    expect(statusLabel(status)).toBeTruthy();
  for (const quality of ['MISSING', 'STALE', 'INSUFFICIENT', 'ERROR'] as const)
    expect(
      signalLabel(
        position({ position_signal: { ...position().position_signal!, quality_status: quality } }),
      ),
    ).toMatch(/Positionssignal:/);
  expect(signalLabel(position({ position_signal: null }))).toContain('nicht verfügbar');
  expect(
    signalLabel(
      position({ position_signal: { ...position().position_signal!, alert_level: 'CRITICAL' } }),
    ),
  ).toContain('Stop erreicht');
  expect(
    signalLabel(
      position({ position_signal: { ...position().position_signal!, alert_level: 'ATTENTION' } }),
    ),
  ).toContain('Gewinnschutz');
});
