import { afterEach, expect, it, vi } from 'vitest';

import { realizedGrossReport, reportFilters } from '../../../test/realizedGrossFixtures';
import type { RealizedGrossFilters } from '../types/api';
import {
  closedContextKeys,
  closedContextQuery,
  closedFiltersError,
  parseClosedContext,
  preserveClosedContext,
} from './closedReportContext';
import {
  initialPerformanceFilters,
  parseRealizedContext,
  REALIZED_REPORT_MAX_PAGES,
  REALIZED_REPORT_PAGE_SIZE,
  realizedContextQuery,
  realizedReportViews,
  reportFiltersErrors,
  verifyRealizedReport,
  type RealizedReportContext,
} from './performanceReportContext';

const context: RealizedReportContext = {
  filters: reportFilters,
  view: 'usable',
  page: 100,
  basis: 'a'.repeat(64),
};

afterEach(() => vi.useRealTimers());

it.each(realizedReportViews)('round-trips the SELL-specific %s view and baseline', (view) => {
  const selected = { ...context, view };
  expect(parseRealizedContext(realizedContextQuery(selected))).toEqual({
    context: selected,
    error: null,
  });
});

it.each([1, 100, 101, 999, 1000])(
  'accepts SELL page %s under the execution resource contract',
  (page) => {
    const query = realizedContextQuery({ ...context, page: page - 1 });
    expect(parseRealizedContext(query).context?.page).toBe(page - 1);
    expect(REALIZED_REPORT_PAGE_SIZE * REALIZED_REPORT_MAX_PAGES).toBe(20_000);
  },
);

it('keeps the closed parser, its qualified view and its 100-page limit separate', () => {
  expect(parseClosedContext(realizedContextQuery(context)).error).not.toBeNull();
  const closed = { ...context, view: 'qualified' as const, page: 99 };
  expect(parseClosedContext(closedContextQuery(closed)).context).toEqual(closed);
  expect(parseRealizedContext(closedContextQuery(closed)).error).not.toBeNull();
  expect(parseClosedContext(closedContextQuery({ ...closed, page: 100 })).error).not.toBeNull();
  const wrongView = realizedContextQuery(context);
  wrongView.set('report_view', 'qualified');
  expect(parseRealizedContext(wrongView).error).not.toBeNull();
  const wrongClosedView = closedContextQuery(closed);
  wrongClosedView.set('report_view', 'usable');
  expect(parseClosedContext(wrongClosedView).error).not.toBeNull();
});

it.each([
  ['from_date', '2026-02-30'],
  ['from_date', '2026-02-29'],
  ['from_date', '0000-01-01'],
  ['from_date', '2026-10-01'],
  ['from_date', ''],
  ['to_date', 'garbage'],
  ['to_date', '2026-9-30'],
  ['to_date', ''],
  ['report_currency', ''],
  ['report_currency', 'eur'],
  ['report_currency', 'EURO'],
  ['report_timezone', 'not/a-zone'],
  ['report_timezone', 'Europe/Berlin\n'],
  ['report_timezone', 'Europe/Berlin?'],
  ['report_timezone', 'Europe/Berlin#'],
  ['report_timezone', 'Europe\\Berlin'],
  ['report_timezone', 'x'.repeat(65)],
  ['report_timezone', ''],
  ['report_context', 'closed-trades'],
  ['report_context', 'https://example.invalid'],
  ['report_context', ''],
  ['report_page', '0'],
  ['report_page', '-1'],
  ['report_page', '1001'],
  ['report_page', '10000'],
  ['report_page', '01'],
  ['report_page', '1.5'],
  ['report_page', '1e2'],
  ['report_page', ''],
  ['report_view', 'qualified'],
  ['report_view', 'unknown'],
  ['report_view', ''],
  ['report_basis', 'not-a-fingerprint'],
  ['report_basis', 'A'.repeat(64)],
  ['report_basis', ''],
])('rejects explicit invalid %s=%s without selecting a substitute', (key, value) => {
  const query = realizedContextQuery(context);
  query.set(key, value);
  expect(parseRealizedContext(query)).toEqual({ context: null, error: expect.any(String) });
});

it.each(closedContextKeys)('rejects duplicate %s even when both values match', (key) => {
  const query = realizedContextQuery(context);
  query.append(key, query.get(key)!);
  expect(parseRealizedContext(query)).toEqual({ context: null, error: expect.any(String) });
});

it('distinguishes absent context, incomplete explicit context and optional absent row parameters', () => {
  expect(parseRealizedContext(new URLSearchParams())).toEqual({ context: null, error: null });
  expect(parseRealizedContext(new URLSearchParams('unrelated=1'))).toEqual({
    context: null,
    error: null,
  });
  for (const key of [
    'report_context',
    'from_date',
    'to_date',
    'report_currency',
    'report_timezone',
  ]) {
    const query = realizedContextQuery(context);
    query.delete(key);
    expect(parseRealizedContext(query).error).not.toBeNull();
    expect(parseRealizedContext(new URLSearchParams([[key, '']])).error).not.toBeNull();
  }
  const query = realizedContextQuery({ ...context, basis: null });
  query.delete('report_view');
  query.delete('report_page');
  expect(parseRealizedContext(query)).toEqual({
    context: { filters: reportFilters, view: 'candidates', page: 0, basis: null },
    error: null,
  });
});

it('retains a valid non-EUR context for an explicit UI currency error instead of silently rewriting it', () => {
  const usd = { ...context, filters: { ...reportFilters, report_currency: 'USD' } };
  expect(parseRealizedContext(realizedContextQuery(usd))).toEqual({ context: usd, error: null });
  expect(reportFiltersErrors(usd.filters)).toEqual({});
});

it.each(['+01:00', '-0230', '+01', '+0100'])(
  'rejects the fixed offset %s in explicit SELL context and visible filter validation',
  (zone) => {
    const filters = { ...reportFilters, report_timezone: zone };
    expect(reportFiltersErrors(filters)).toEqual({ report_timezone: expect.any(String) });
    expect(parseRealizedContext(realizedContextQuery({ ...context, filters }))).toEqual({
      context: null,
      error: expect.any(String),
    });
    expect(filters.report_timezone).toBe(zone);
  },
);

it('accepts the named IANA zone Etc/GMT+1 without treating its embedded sign as a fixed offset', () => {
  const selected = {
    ...context,
    filters: { ...reportFilters, report_timezone: 'Etc/GMT+1' },
  };
  expect(reportFiltersErrors(selected.filters)).toEqual({});
  expect(parseRealizedContext(realizedContextQuery(selected))).toEqual({
    context: selected,
    error: null,
  });
});

it('serializes no monetary values, workspace identities or arbitrary return URLs', () => {
  const query = realizedContextQuery(context);
  query.set('total', '999999');
  query.set('workspace_id', 'foreign');
  query.set('returnTo', 'https://example.invalid/return');
  const parsed = parseRealizedContext(query).context!;
  const serialized = realizedContextQuery(parsed);
  expect([...serialized.keys()]).toEqual([...closedContextKeys]);
  expect(serialized.has('total')).toBe(false);
  expect(serialized.has('workspace_id')).toBe(false);
  expect(serialized.has('returnTo')).toBe(false);
});

it('does not normalize malformed closed contexts when existing source navigation preserves them', () => {
  const source = closedContextQuery({ ...context, view: 'all', page: 2 });
  source.append('report_context', 'realized-gross');
  source.append('from_date', '');
  const destination = new URLSearchParams('journal_version_id=historical');
  preserveClosedContext(source, destination);
  for (const key of closedContextKeys) expect(destination.getAll(key)).toEqual(source.getAll(key));
  expect(parseClosedContext(destination)).toEqual({ context: null, error: expect.any(String) });
});

it.each([
  ['2026-09-30T22:30:00Z', '2026-10-01', '2026-10-01'],
  ['2026-10-26T23:30:00Z', '2026-10-01', '2026-10-27'],
])('suggests the Berlin calendar month through today at %s', (now, from, to) => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date(now));
  expect(initialPerformanceFilters()).toEqual({
    from_date: from,
    to_date: to,
    report_currency: 'EUR',
    report_timezone: 'Europe/Berlin',
  });
});

it.each([
  ['from_date', ''],
  ['from_date', '0000-01-01'],
  ['from_date', '2026-02-30'],
  ['from_date', '9999-99-99'],
  ['to_date', '2026-9-30'],
  ['to_date', 'invalid'],
  ['report_currency', ''],
  ['report_currency', 'eur'],
  ['report_timezone', ''],
  ['report_timezone', 'not/a-zone'],
  ['report_timezone', 'Europe/Berlin '],
  ['report_timezone', 'x'.repeat(65)],
] satisfies [keyof RealizedGrossFilters, string][])(
  'identifies an invalid %s field without altering its value',
  (field, value) => {
    const filters = { ...reportFilters, [field]: value };
    expect(reportFiltersErrors(filters)[field]).toEqual(expect.any(String));
    expect(closedFiltersError(filters)).not.toBeNull();
    expect(filters[field]).toBe(value);
  },
);

it('reports both reversed dates and permits valid leap dates without computing period boundaries', () => {
  expect(reportFiltersErrors({ ...reportFilters, from_date: '2026-10-01' })).toEqual({
    from_date: 'Von darf nicht nach Bis liegen.',
    to_date: 'Bis darf nicht vor Von liegen.',
  });
  const leap = { ...reportFilters, from_date: '2024-02-29', to_date: '2024-02-29' };
  expect(reportFiltersErrors(leap)).toEqual({});
  expect(
    parseRealizedContext(realizedContextQuery({ ...context, filters: leap })).context?.filters,
  ).toEqual(leap);
  expect(reportFiltersErrors(reportFilters)).toEqual({});
});

it('accepts only an answer bound to the requested SELL definition and complete filter context', () => {
  expect(() => verifyRealizedReport(realizedGrossReport(), reportFilters)).not.toThrow();
  expect(() =>
    verifyRealizedReport(
      realizedGrossReport({ definition_version: 'closed-trade-gross-v1' }),
      reportFilters,
    ),
  ).toThrow(/Verkaufsbericht/);
  const foreignCurrency = realizedGrossReport();
  foreignCurrency.currency.code = 'USD';
  expect(() => verifyRealizedReport(foreignCurrency, reportFilters)).toThrow(/Währung/);
});

it.each([
  ['from_date', '2026-08-01'],
  ['to_date', '2026-10-01'],
  ['report_currency', 'USD'],
  ['report_timezone', 'Etc/UTC'],
] satisfies [keyof RealizedGrossFilters, string][])(
  'rejects an answer with mismatched %s',
  (field, value) => {
    const result = realizedGrossReport({ filters: { ...reportFilters, [field]: value } });
    expect(() => verifyRealizedReport(result, reportFilters)).toThrow(/Bitte erneut lesen/);
  },
);
