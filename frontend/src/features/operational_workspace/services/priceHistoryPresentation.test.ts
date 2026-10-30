import {
  positionPriceHistory,
  positionPriceSeries,
} from '../../../test/positionPriceHistoryFixtures';
import { availableHistoryDays, historyAxisTime, historyVenue } from './priceHistoryPresentation';

it('uses original time and the report clock for available periods, never receipt time or an execution marker', () => {
  const report = positionPriceHistory();
  expect(availableHistoryDays(report)).toEqual(['90']);
  const point = report.series[0].points[0];
  report.series[0].points = [{ ...point, observed_at: '2026-10-23T12:00:00Z' }];
  expect(availableHistoryDays(report)).toEqual(['7', '31', '90']);
  report.series[0].points = [{ ...point, observed_at: '2026-10-23T11:59:59Z' }];
  expect(availableHistoryDays(report)).toEqual(['31', '90']);
  report.series[0].points = [{ ...point, observed_at: '2026-10-31T08:00:00Z' }];
  expect(availableHistoryDays(report)).toEqual([]);
  report.series[0].points = [{ ...point, observed_at: '2025-10-30T12:00:00Z' }];
  expect(availableHistoryDays(report)).toEqual([]);
});

it('shows distinct intraday UTC times, seconds for short spans and years for multi-year history', () => {
  const start = Date.parse('2026-10-25T00:30:00Z');
  const end = Date.parse('2026-10-25T02:30:00Z');
  expect(historyAxisTime(start, start, end)).toBe('00:30');
  expect(historyAxisTime(end, start, end)).toBe('02:30');
  expect(historyAxisTime(start + 15000, start, start + 30000)).toBe('00:30:15');
  const previousYear = Date.parse('2025-10-25T00:30:00Z');
  expect(historyAxisTime(previousYear, previousYear, end)).toBe('25.10.2025');
  expect(historyAxisTime(end, previousYear, end)).toBe('25.10.2026');
  expect(historyAxisTime(start, start, end + 8 * 86400000)).toBe('25.10.');
  expect(historyAxisTime(start, NaN, end)).toBe('Unbekannt');
});

it('distinguishes intraday ticks across short multi-day windows instead of repeating the same date', () => {
  const start = Date.parse('2026-09-10T08:00:00Z');
  const end = Date.parse('2026-09-12T08:00:00Z');
  expect(historyAxisTime(Date.parse('2026-09-11T06:00:00Z'), start, end)).toBe('11.09. 06:00');
  expect(historyAxisTime(Date.parse('2026-09-11T18:00:00Z'), start, end)).toBe('11.09. 18:00');
});

it('preserves missing venue fields from an older response without deriving them from provider or ISIN', () => {
  expect(
    historyVenue(positionPriceSeries({ venue_mic: undefined, provider_exchange_code: undefined })),
  ).toBe('Handelsplatz nicht belegt');
  expect(
    historyVenue(positionPriceSeries({ venue_mic: 'ISSUER', provider_exchange_code: 'ISSUER' })),
  ).toBe('Emittentenquelle · kein Börsenhandelsplatz · Providersegment: ISSUER');
});
