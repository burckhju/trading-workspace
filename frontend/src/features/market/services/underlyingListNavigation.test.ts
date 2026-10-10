import { describe, expect, it } from 'vitest';
import {
  readUnderlyingListView,
  underlyingListParams,
  underlyingListUrl,
  underlyingListReturnTo,
  withUnderlyingListReturnTo,
} from './underlyingListNavigation';

describe('underlying list URL state', () => {
  it('round-trips page and all filters, including special characters, without a second state store', () => {
    const view = {
      query: 'Test & Öl + ? #',
      lifecycle: 'ACTIVE' as const,
      venueId: 'venue-test',
      currencyCode: 'EUR',
      offset: 50,
    };
    expect(readUnderlyingListView(underlyingListParams(view))).toEqual(view);
    const listUrl = underlyingListUrl(view);
    const editUrl = withUnderlyingListReturnTo('/underlyings/test/edit', listUrl);
    expect(underlyingListReturnTo(new URLSearchParams(editUrl.split('?')[1]))).toBe(listUrl);
  });
  it.each(['-25', '1', '25.5', 'NaN', 'Infinity', '9007199254741000', '1e2', 'foo', ''])(
    'defaults invalid page offset %s to page one',
    (offset) => {
      expect(readUnderlyingListView(new URLSearchParams({ offset })).offset).toBe(0);
    },
  );
  it.each(['ACTIVE', 'INACTIVE'])('preserves the explicit %s filter', (lifecycle) => {
    expect(readUnderlyingListView(new URLSearchParams({ lifecycle })).lifecycle).toBe(lifecycle);
  });
  it('uses normal list defaults without parameters and ignores unknown lifecycle states', () => {
    expect(
      underlyingListUrl(readUnderlyingListView(new URLSearchParams('lifecycle=UNKNOWN'))),
    ).toBe('/underlyings');
    expect(underlyingListReturnTo(new URLSearchParams())).toBeUndefined();
    expect(underlyingListReturnTo(new URLSearchParams({ returnTo: '/underlyings' }))).toBe(
      '/underlyings',
    );
  });
  it.each([
    'https://evil.invalid',
    '//evil.invalid',
    '/trades',
    '/underlyings/../trades',
    '/underlyings-evil?offset=50',
    '/underlyings/test',
    'javascript:alert(1)',
    '/underlyings\\evil',
  ])('rejects non-list return target %s', (returnTo) => {
    expect(underlyingListReturnTo(new URLSearchParams({ returnTo }))).toBeUndefined();
  });
  it('strips nested return targets and unknown parameters, keeping only the list view', () => {
    const returnTo = '/underlyings?query=Test&offset=25&returnTo=https://evil.invalid&unknown=1';
    expect(underlyingListReturnTo(new URLSearchParams({ returnTo }))).toBe(
      '/underlyings?query=Test&offset=25',
    );
  });
  it('retains provider prefill parameters and leaves standalone links unchanged', () => {
    const url = withUnderlyingListReturnTo(
      '/underlyings/new?source=EODHD&ticker=TEST',
      '/underlyings?offset=50',
    );
    const params = new URLSearchParams(url.split('?')[1]);
    expect(params.get('source')).toBe('EODHD');
    expect(params.get('ticker')).toBe('TEST');
    expect(params.get('returnTo')).toBe('/underlyings?offset=50');
    expect(withUnderlyingListReturnTo('/underlyings/test')).toBe('/underlyings/test');
  });
});
