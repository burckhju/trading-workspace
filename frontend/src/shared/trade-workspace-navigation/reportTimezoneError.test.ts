// @vitest-environment node

import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  parseRealizedContext,
  realizedContextQuery,
  reportFiltersErrors,
  reportTimezoneError,
  type RealizedReportContext,
} from './index';

const timezoneError = 'Bitte eine gültige Berichtszeitzone (IANA) auswählen.';
const context: RealizedReportContext = {
  filters: {
    from_date: '2026-09-01',
    to_date: '2026-09-30',
    report_currency: 'EUR',
    report_timezone: 'America/Los_Angeles',
  },
  view: 'usable',
  page: 100,
  basis: 'a'.repeat(64),
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe('shared report timezone contract', () => {
  it.each([
    'Europe/Berlin',
    'Europe/Vienna',
    'America/Los_Angeles',
    'Asia/Tokyo',
    'Etc/UTC',
    'UTC',
    'Etc/GMT+1',
  ])('accepts the explicit named zone %s without rewriting it', (zone) => {
    const selected = {
      ...context,
      filters: { ...context.filters, report_timezone: zone },
    };
    expect(reportTimezoneError(zone)).toBeUndefined();
    expect(reportFiltersErrors(selected.filters)).toEqual({});
    expect(parseRealizedContext(realizedContextQuery(selected))).toEqual({
      context: selected,
      error: null,
    });
    expect(selected.filters.report_timezone).toBe(zone);
  });

  it.each([
    '',
    'Not/AZone',
    'x'.repeat(65),
    'Europe/Berlin ',
    'Europe/Berlin\n',
    'Europe/Berlin?',
    'Europe/Berlin#',
    'Europe\\Berlin',
    '+01:00',
    '-0230',
    '+01',
    '+0100',
  ])('rejects invalid or fixed-offset zone %j with the unchanged field message', (zone) => {
    const filters = { ...context.filters, report_timezone: zone };
    const query = realizedContextQuery({ ...context, filters });
    const originalQuery = query.toString();

    expect(reportTimezoneError(zone)).toBe(timezoneError);
    expect(reportFiltersErrors(filters)).toEqual({ report_timezone: timezoneError });
    expect(parseRealizedContext(query)).toEqual({
      context: null,
      error: expect.any(String),
    });
    expect(filters.report_timezone).toBe(zone);
    expect(query.toString()).toBe(originalQuery);
  });

  it('validates and restores explicit context without a browser or browser-zone lookup', () => {
    const browserZoneLookup = vi
      .spyOn(Intl.DateTimeFormat.prototype, 'resolvedOptions')
      .mockImplementation(() => {
        throw new Error('No browser timezone is available');
      });

    expect(typeof window).toBe('undefined');
    expect(reportTimezoneError(context.filters.report_timezone)).toBeUndefined();
    expect(reportFiltersErrors(context.filters)).toEqual({});
    expect(parseRealizedContext(realizedContextQuery(context))).toEqual({
      context,
      error: null,
    });
    expect(reportTimezoneError('Not/AZone')).toBe(timezoneError);
    expect(parseRealizedContext(new URLSearchParams())).toEqual({
      context: null,
      error: null,
    });
    expect(browserZoneLookup).not.toHaveBeenCalled();
  });
});
