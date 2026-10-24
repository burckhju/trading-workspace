import { expect, it } from 'vitest';

import { closedTradeFilters } from '../../../test/closedTradesFixtures';
import { sourceLink } from '../../trade/services/sourceView';
import {
  closedContextQuery,
  closedListUrl,
  closedTradeSourceLink,
  parseClosedContext,
  type ClosedReportContext,
} from './closedReportContext';

const context: ClosedReportContext = {
  filters: closedTradeFilters,
  view: 'all',
  page: 2,
  basis: 'a'.repeat(64),
};
const trade = '10000000-0000-4000-8000-000000000001';
const journal = '30000000-0000-4000-8000-000000000001';

it('round-trips only the supported explicit report context, including page and original basis', () => {
  expect(parseClosedContext(closedContextQuery(context))).toEqual({ context, error: null });
  const url = new URL(closedTradeSourceLink(trade, context), 'http://local');
  expect(url.pathname).toBe('/trade-management');
  expect(url.searchParams.get('view')).toBe('sources');
  expect(url.searchParams.get('trade_id')).toBe(trade);
  expect(url.searchParams.get('report_page')).toBe('3');
  expect(parseClosedContext(url.searchParams).context).toEqual(context);
  const pin = new URL(sourceLink(url.searchParams, 'journal_version_id', journal), 'http://local');
  expect(pin.searchParams.get('journal_version_id')).toBe(journal);
  expect(parseClosedContext(pin.searchParams).context).toEqual(context);
  expect(closedListUrl(context)).toMatch(/^\/performance\/closed-trades\?/);
});

it('never carries monetary values or arbitrary external, nested or encoded return destinations', () => {
  const query = closedContextQuery(context);
  query.set('trade_id', trade);
  query.set('returnTo', 'https://evil.invalid/?returnTo=%2F%2Fevil.invalid');
  query.set('total', '999999');
  query.set('workspace_id', 'foreign');
  const pin = new URL(sourceLink(query, 'journal_version_id', journal), 'http://local');
  expect(pin.searchParams.has('returnTo')).toBe(false);
  expect(pin.searchParams.has('total')).toBe(false);
  expect(pin.searchParams.has('workspace_id')).toBe(false);
  expect(new URL(closedListUrl(parseClosedContext(query).context!), 'http://local').origin).toBe(
    'http://local',
  );
});

it.each([
  ['from_date', '2026-02-30'],
  ['from_date', '0000-01-01'],
  ['from_date', '2026-11-01'],
  ['to_date', 'garbage'],
  ['report_currency', ''],
  ['report_currency', 'eur'],
  ['report_timezone', 'not/a-zone'],
  ['report_timezone', 'Europe/Berlin\n'],
  ['report_context', 'realized-gross'],
  ['report_context', 'https://evil.invalid'],
  ['report_page', '0'],
  ['report_page', '-1'],
  ['report_page', '101'],
  ['report_page', '01'],
  ['report_page', '1.5'],
  ['report_view', 'unknown'],
  ['report_basis', 'not-a-fingerprint'],
  ['report_basis', ''],
])('rejects invalid %s=%s without silently selecting a substitute', (key, value) => {
  const query = closedContextQuery(context);
  query.set(key, value);
  expect(parseClosedContext(query)).toEqual({ context: null, error: expect.any(String) });
});

it.each([
  'from_date',
  'to_date',
  'report_currency',
  'report_timezone',
  'report_context',
  'report_page',
  'report_view',
  'report_basis',
])('rejects duplicate %s and retains that rejection through pin navigation', (key) => {
  const query = closedContextQuery(context);
  query.append(key, query.get(key)!);
  query.set('trade_id', trade);
  expect(parseClosedContext(query).error).not.toBeNull();
  expect(
    parseClosedContext(
      new URL(sourceLink(query, 'journal_version_id', journal), 'http://local').searchParams,
    ).error,
  ).not.toBeNull();
});

it('distinguishes absent context, missing required values and an optional absent baseline', () => {
  expect(parseClosedContext(new URLSearchParams())).toEqual({ context: null, error: null });
  for (const key of [
    'from_date',
    'to_date',
    'report_currency',
    'report_timezone',
    'report_context',
  ]) {
    const query = closedContextQuery(context);
    query.delete(key);
    expect(parseClosedContext(query).error).not.toBeNull();
  }
  const noBasis = { ...context, basis: null };
  expect(parseClosedContext(closedContextQuery(noBasis)).context).toEqual(noBasis);
});
