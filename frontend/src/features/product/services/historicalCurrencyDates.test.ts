import { afterEach, describe, expect, it, vi } from 'vitest';
import { historicalCurrencyDayWindow } from './historicalCurrencyDates';

afterEach(() => vi.unstubAllEnvs());
describe('explicitly labelled browser-zone historical days', () => {
  it('uses local calendar midnights rather than interpreting the date as UTC', () => {
    vi.stubEnv('TZ', 'Europe/Berlin');
    expect(historicalCurrencyDayWindow('2026-10-01', '2026-10-28')).toEqual({
      valid_from: '2026-09-30T22:00:00.000Z',
      valid_to: '2026-10-28T23:00:00.000Z',
    });
  });
  it.each([
    ['2026-03-29', 23],
    ['2026-10-25', 25],
  ])('keeps the full DST transition day %s', (day, hours) => {
    vi.stubEnv('TZ', 'Europe/Berlin');
    const window = historicalCurrencyDayWindow(String(day), String(day));
    expect((Date.parse(window.valid_to) - Date.parse(window.valid_from)) / 3600000).toBe(hours);
  });
  it('uses the actual browser zone and handles year boundaries', () => {
    vi.stubEnv('TZ', 'America/New_York');
    expect(historicalCurrencyDayWindow('2026-12-31', '2026-12-31')).toEqual({
      valid_from: '2026-12-31T05:00:00.000Z',
      valid_to: '2027-01-01T05:00:00.000Z',
    });
  });
  it.each([
    ['2026-02-30', '2026-03-01'],
    ['2026-10-28', '2026-10-01'],
    ['', '2026-10-01'],
  ])('rejects invalid source days %s / %s', (from, through) => {
    expect(() => historicalCurrencyDayWindow(from, through)).toThrow();
  });
});
