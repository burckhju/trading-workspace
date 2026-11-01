import { describe, expect, it } from 'vitest';

import { closedContextKeys } from './context';
import { reportReturnLink } from './reportReturn';
import {
  parseRealizedContext,
  realizedListUrl,
  realizedTradeLink,
  type RealizedReportContext,
} from './realizedReportNavigation';

const filters = {
  from_date: '2026-09-01',
  to_date: '2026-09-30',
  report_currency: 'EUR',
  report_timezone: 'America/New_York',
};

function query(kind: 'closed-trades' | 'realized-gross') {
  return new URLSearchParams({
    report_context: kind,
    ...filters,
    report_view: kind === 'closed-trades' ? 'qualified' : 'usable',
    report_page: kind === 'closed-trades' ? '2' : '101',
    report_basis: 'b'.repeat(64),
  });
}

describe('report return navigation', () => {
  it.each(['closed-trades', 'realized-gross'] as const)(
    'returns to the original %s selection, including after URL copy and reload',
    (kind) => {
      const original = query(kind);
      const carried = new URLSearchParams(original);
      carried.set('trade_id', 'trade-1');
      carried.set('view', 'sources');
      carried.set('journal_version_id', 'historical-journal');
      carried.set('returnTo', 'https://example.invalid/foreign');
      carried.set('total', '999999');
      const destination = reportReturnLink(new URLSearchParams(carried.toString()));
      expect(destination?.label).toBe(
        kind === 'closed-trades'
          ? 'Zur ursprünglichen Abschlussauswahl'
          : 'Zur ursprünglichen Verkaufsauswahl',
      );
      const url = new URL(destination!.href, 'https://workspace.test');
      expect(url.pathname).toBe(`/performance/${kind}`);
      expect(Object.fromEntries(url.searchParams)).toEqual(Object.fromEntries(original));
      expect(carried.get('journal_version_id')).toBe('historical-journal');
      expect(carried.get('returnTo')).toBe('https://example.invalid/foreign');
    },
  );

  it.each(closedContextKeys)('rejects a duplicate %s for either report type', (key) => {
    for (const kind of ['closed-trades', 'realized-gross'] as const) {
      const repeated = query(kind);
      repeated.append(key, repeated.get(key)!);
      expect(reportReturnLink(repeated)).toBeNull();
    }
  });

  it.each([
    ['report_context', 'unknown'],
    ['report_context', 'https://example.invalid'],
    ['from_date', '2026-02-30'],
    ['to_date', '2026-08-31'],
    ['report_timezone', 'not/a-zone'],
    ['report_currency', 'eur'],
    ['report_view', 'qualified'],
    ['report_page', '1001'],
    ['report_basis', 'not-a-basis'],
  ])('does not replace an invalid SELL %s=%s with a different report', (key, value) => {
    const invalid = query('realized-gross');
    invalid.set(key, value);
    expect(reportReturnLink(invalid)).toBeNull();
  });

  it('keeps the closed 100-page limit separate from the valid SELL page 1000', () => {
    const closed = query('closed-trades');
    closed.set('report_page', '101');
    expect(reportReturnLink(closed)).toBeNull();
    const sale = query('realized-gross');
    sale.set('report_page', '1000');
    const url = new URL(reportReturnLink(sale)!.href, 'https://workspace.test');
    expect(url.pathname).toBe('/performance/realized-gross');
    expect(url.searchParams.get('report_page')).toBe('1000');
  });

  it('provides no return destination for absent or incomplete context', () => {
    expect(reportReturnLink(new URLSearchParams('trade_id=trade-1'))).toBeNull();
    for (const kind of ['closed-trades', 'realized-gross'] as const) {
      const incomplete = query(kind);
      incomplete.delete('from_date');
      expect(reportReturnLink(incomplete)).toBeNull();
    }
  });

  it('keeps an explicit non-EUR choice for the owner to qualify instead of changing the currency', () => {
    const usd = query('realized-gross');
    usd.set('report_currency', 'USD');
    const url = new URL(reportReturnLink(usd)!.href, 'https://workspace.test');
    expect(url.searchParams.get('report_currency')).toBe('USD');
  });
});

it('takes a sale to its exact trade bookings and returns to the applied report selection', () => {
  const context: RealizedReportContext = {
    filters,
    view: 'usable',
    page: 100,
    basis: 'b'.repeat(64),
  };
  const link = realizedTradeLink('trade/with?a&b', context);
  const tradeUrl = new URL(link, 'https://workspace.test');
  expect(tradeUrl.pathname).toBe('/trade-management');
  expect(tradeUrl.hash).toBe('#execution-dates');
  expect(tradeUrl.searchParams.get('trade_id')).toBe('trade/with?a&b');
  expect(parseRealizedContext(tradeUrl.searchParams)).toEqual({ context, error: null });
  expect(reportReturnLink(tradeUrl.searchParams)?.href).toBe(realizedListUrl(context));
  expect(Object.fromEntries(tradeUrl.searchParams)).toEqual({
    report_context: 'realized-gross',
    ...filters,
    report_view: 'usable',
    report_page: '101',
    report_basis: 'b'.repeat(64),
    trade_id: 'trade/with?a&b',
  });
});
