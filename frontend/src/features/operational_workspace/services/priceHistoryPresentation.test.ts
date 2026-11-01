import {
  positionPriceHistory,
  positionPriceSeries,
} from '../../../test/positionPriceHistoryFixtures';
import {
  availableHistoryDays,
  historyAxisTime,
  historyProvider,
  historySourceMode,
  historyVenue,
} from './priceHistoryPresentation';

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

it('names supplied providers while retaining their exact original codes', () => {
  expect(historyProvider('BOERSE_STUTTGART_DELAYED')).toBe(
    'Börse Stuttgart · BOERSE_STUTTGART_DELAYED',
  );
  expect(historyProvider('FRANKFURT_QUOTES')).toBe('Börse Frankfurt · FRANKFURT_QUOTES');
  expect(historyProvider('GETTEX_DELAYED')).toBe('gettex · GETTEX_DELAYED');
  expect(historyProvider('VONTOBEL_MARKETS')).toBe('Vontobel Markets · VONTOBEL_MARKETS');
  expect(historyProvider('MORGAN_STANLEY')).toBe('Morgan Stanley · MORGAN_STANLEY');
  expect(historyProvider('JPMORGAN')).toBe('J.P. Morgan · JPMORGAN');
  expect(historyProvider('UNKNOWN_OR_FUTURE_PROVIDER')).toBe('UNKNOWN_OR_FUTURE_PROVIDER');
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

it('explains supplied source modes without inferring current freshness or replacing unknown codes', () => {
  expect(historySourceMode('DELAYED')).toBe('Zeitverzögerte Quelle (DELAYED)');
  expect(historySourceMode('REALTIME')).toBe('Echtzeitquelle bei Erfassung (REALTIME)');
  expect(historySourceMode('OFFICIAL_WEBSITE')).toBe('Offizielle Website (OFFICIAL_WEBSITE)');
  expect(historySourceMode('OFFICIAL_ISSUER_INDICATION')).toBe(
    'Indikation des Emittenten (OFFICIAL_ISSUER_INDICATION)',
  );
  expect(historySourceMode('OFFICIAL_WEBSITE_LAST_TRADE')).toBe(
    'Letzter Handel von offizieller Website (OFFICIAL_WEBSITE_LAST_TRADE)',
  );
  expect(historySourceMode('OFFICIAL_WEBSITE_PREVIOUS_CLOSE')).toBe(
    'Vorheriger Schlusskurs von offizieller Website (OFFICIAL_WEBSITE_PREVIOUS_CLOSE)',
  );
  expect(historySourceMode('FRANKFURT_DELAYED_MONITORING')).toBe(
    'Zeitverzögerte Frankfurter Monitoringquelle (FRANKFURT_DELAYED_MONITORING)',
  );
  expect(historySourceMode('FRANKFURT_REALTIME_MONITORING')).toBe(
    'Frankfurter Echtzeitquelle bei Erfassung (FRANKFURT_REALTIME_MONITORING)',
  );
  expect(historySourceMode('OFFICIAL_DELAYED_PRETRADE')).toBe(
    'Offizielle zeitverzögerte Vorhandelskurse (OFFICIAL_DELAYED_PRETRADE)',
  );
  expect(historySourceMode('NORMALIZED_SNAPSHOT')).toBe(
    'Vereinheitlichter Quellensnapshot (NORMALIZED_SNAPSHOT)',
  );
  expect(historySourceMode('FUTURE_SOURCE_MODE')).toBe('FUTURE_SOURCE_MODE');
  expect(historySourceMode(null)).toBe('Quellenmodus unbekannt');
});
