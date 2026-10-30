import type {
  PositionPriceHistoryDays,
  PositionPriceHistoryReport,
  PositionPriceKind,
  PositionPriceSeries,
} from '../positionPriceHistory';

export const priceKindLabel: Record<PositionPriceKind, string> = {
  BID: 'Geldkurs',
  ASK: 'Briefkurs',
  LAST_TRADE: 'Letzter Handel',
  PREVIOUS_CLOSE: 'Vorheriger Schlusskurs',
};

const labels: Record<string, string> = {
  TWO_SIDED_WITHIN_AGE_LIMIT: 'Geld/Brief bei Erfassung innerhalb der Altersgrenze',
  ONE_SIDED: 'Nur eine Kursseite belegt',
  REFERENCE_ONLY: 'Indikativer Referenzkurs',
  TIMESTAMP_UNKNOWN: 'Originalkurszeit unbekannt',
  TIME_INCONSISTENT: 'Zeitpunkte widersprüchlich',
  STALE: 'Bei Erfassung veraltet',
  AGE_POLICY_UNKNOWN: 'Altersgrenze unbekannt',
  REQUEST_FAILED: 'Abruf oder Validierung fehlgeschlagen',
  NO_QUOTE: 'Kein Kurs gespeichert',
  IDENTITY_MISMATCH: 'Kursidentität stimmt nicht mit der Position überein',
  INVALID_QUOTE: 'Kursbeleg nicht verwendbar',
  INVALID_OBSERVATION: 'Gespeicherter Kursbeleg unvollständig oder ungültig',
  INVALID_PRICE: 'Kein gültiger positiver Preis',
  CURRENCY_UNKNOWN: 'Währung nicht belegt',
  EXECUTION_CURRENCY_UNKNOWN: 'Ausführungswährung nicht belegt',
  EXECUTION_TIME_UNKNOWN: 'Genaue Ausführungszeit nicht belegt',
  DATE_ONLY: 'Nur Ausführungsdatum bekannt',
  OUTSIDE_WINDOW: 'Originalzeit außerhalb des gewählten Zeitraums',
  DUPLICATE_QUOTE: 'Wiederholter Kursbeleg',
  DUPLICATE_OBSERVATION: 'Doppelte Beobachtung ausgelassen',
  NO_PRICE: 'Kein belegter Kurspreis',
  NO_MATCHING_QUOTE_CURRENCY: 'Kein Kurssegment mit gleicher belegter Währung',
};

export function priceHistoryLabel(code: string): string {
  return labels[code] ?? code;
}

export function historyTime(value: string | null): string {
  if (!value) return 'Unbekannt';
  return `${new Date(value).toLocaleString('de-DE', {
    timeZone: 'UTC',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })} UTC`;
}

// Preserve the decimal supplied by the backend in evidence tables and tooltips.
// Only chart coordinates are converted to binary floating point.
export function historyPrice(value: string): string {
  return value.replace('.', ',');
}

export function historyVenue(series: PositionPriceSeries): string {
  const venue =
    series.venue_mic === 'ISSUER' ||
    (!series.venue_mic && series.provider_exchange_code === 'ISSUER')
      ? 'Emittentenquelle · kein Börsenhandelsplatz'
      : series.venue_mic
        ? `Handelsplatz: ${series.venue_mic} (MIC)`
        : 'Handelsplatz nicht belegt';
  return series.provider_exchange_code
    ? `${venue} · Providersegment: ${series.provider_exchange_code}`
    : venue;
}

/** Short windows are offered only after the all-history read proves a price in them. */
export function availableHistoryDays(
  report: PositionPriceHistoryReport,
): PositionPriceHistoryDays[] {
  const end = Date.parse(report.window_end);
  const times = report.series.flatMap((series) =>
    series.points.map((point) => Date.parse(point.observed_at)),
  );
  return (['7', '31', '90'] as const).filter((days) =>
    times.some((time) => time >= end - Number(days) * 86400000 && time <= end),
  );
}

export function historyAxisTime(value: number, start: number, end: number): string {
  if (![value, start, end].every(Number.isFinite)) return 'Unbekannt';
  const date = new Date(value);
  const first = new Date(start);
  const last = new Date(end);
  if (first.toISOString().slice(0, 10) === last.toISOString().slice(0, 10)) {
    return date.toLocaleTimeString('de-DE', {
      timeZone: 'UTC',
      hour: '2-digit',
      minute: '2-digit',
      ...(end - start < 60000 ? { second: '2-digit' as const } : {}),
    });
  }
  const day = date.toLocaleDateString('de-DE', {
    timeZone: 'UTC',
    day: '2-digit',
    month: '2-digit',
    ...(first.getUTCFullYear() !== last.getUTCFullYear() ? { year: 'numeric' as const } : {}),
  });
  if (end - start <= 7 * 86400000) {
    const time = date.toLocaleTimeString('de-DE', {
      timeZone: 'UTC',
      hour: '2-digit',
      minute: '2-digit',
      ...(end - start < 60000 ? { second: '2-digit' as const } : {}),
    });
    return `${day} ${time}`;
  }
  return day;
}
