export const chartMessages: Record<string, string> = {
  READY: 'Vergleich verfügbar',
  CONFIGURED: 'Zugeordnet',
  NO_SECTOR_TAXONOMY: 'Noch keine Sektorsystematik eingerichtet.',
  MISSING_REFERENCE: 'Sektorreferenz fehlt',
  AMBIGUOUS_REFERENCE: 'Mehrere gültige Sektorreferenzen – Zuordnung prüfen',
  INACTIVE_SECTOR: 'Sektor inaktiv',
  INACTIVE_REFERENCE: 'Referenz fehlt oder ist inaktiv',
  AMBIGUOUS_PROXY: 'Mehrere gültige Stellvertreter – Zuordnung prüfen',
  PROXY_IS_NOT_ETF: 'Zugeordneter Stellvertreter ist kein ETF',
  INSUFFICIENT_ASSIGNMENT_QUALITY: 'Zuordnung nicht ausreichend belegt',
  INSUFFICIENT_PROXY_QUALITY: 'ETF-Zuordnung nicht ausreichend belegt',
  SERIES_UNAVAILABLE: 'Mindestens eine Serie fehlt. Kein vollständiger Vergleich möglich.',
  NO_COMMON_DATE: 'Kein gemeinsamer belegter Handelstag im Zeitraum.',
  INCOMPATIBLE_RETURN_BASIS:
    'Unterschiedliche Renditegrundlagen. Preisindex und bereinigte Wertpapierverläufe sind hier nicht vergleichbar.',
  RETURN_BASIS_UNKNOWN:
    'Renditegrundlage nicht belegt. Indexgrundlage in der Einrichtung bestätigen oder einheitliches Preisfeld wählen.',
  INVALID_START_VALUE: 'Am ersten gemeinsamen Tag fehlt ein gültiger positiver Startwert.',
  INSUFFICIENT_COMMON_HISTORY: 'Weniger als zwei gemeinsame Beobachtungstage.',
  INACTIVE_INSTRUMENT: 'Instrument oder Handelsplatz inaktiv',
  NO_MARKET_DATA_INSTRUMENT: 'Marktdatenidentität fehlt – Mapping einrichten',
  MAPPING_NOT_ACTIVE: 'Kein aktives Mapping; gespeicherte Historie ist kein Abrufnachweis',
  POINT_LIMIT_EXCEEDED:
    'Mehr als 10.000 Beobachtungen. Bitte Zeitraum verkürzen; es wurden keine Werte still entfernt.',
  CURRENCY_CONFLICT: 'Währung innerhalb der Serie widersprüchlich',
  DUPLICATE_DATE: 'Mehrdeutige Beobachtungen am selben Tag',
  NO_HISTORY: 'Keine gespeicherte Historie im gewählten Zeitraum',
  STALE_HISTORY: 'Letzte Beobachtung liegt mehr als 7 Kalendertage vor dem gewählten Ende',
  INSUFFICIENT_HISTORY: 'Nur eine Beobachtung vorhanden',
  UNADJUSTED_SPLITS_AND_DIVIDENDS:
    'CLOSE ist nicht split- oder dividendenbereinigt; Kurssprünge sind keine belegte Anlegerrendite.',
  UNOBSERVED_WEEKDAYS:
    'Wochentage ohne Beobachtung: Linien unterbrochen. Feiertage und fehlende Daten sind ohne Börsenkalender nicht unterscheidbar.',
  PRICE_FIELD_MISSING: 'Gewähltes Preisfeld fehlt',
  NON_POSITIVE_PRICE: 'Kein positiver endlicher Preis',
  PRICE_QUALITY_UNUSABLE: 'Preisqualität unzureichend',
  PROVIDER_IDENTITY_CONFLICT:
    'Gespeicherte Herkunft stimmt nicht mit der aktuellen Zuordnung überein',
  LOCAL_CURRENCY_NO_FX: 'Lokale Währungsentwicklungen; keine Umrechnung in eine Anlegerwährung.',
  START_MOVED_TO_COMMON_OBSERVATION: 'Vergleich beginnt am ersten gemeinsamen belegten Tag.',
  NO_UNAMBIGUOUS_PRIMARY_LISTING: 'Keine eindeutige aktive Primärnotierung',
  NO_UNAMBIGUOUS_BENCHMARK: 'Marktbenchmark fehlt oder ist mehrdeutig',
  NO_UNAMBIGUOUS_SECTOR_REFERENCE: 'Sektorvergleich fehlt oder ist nicht eindeutig zugeordnet',
  UNADJUSTED_PRICE_CHANGE: 'Unbereinigte Kursveränderung',
  SPLIT_DIVIDEND_ADJUSTED_CHANGE: 'Split-/dividendenbereinigte Wertpapierentwicklung',
  INDEX_TOTAL_RETURN: 'Total-Return-Index',
  UNKNOWN: 'Grundlage unbekannt',
};

export function chartMessage(code: string): string {
  return chartMessages[code] ?? code;
}

export function chartDate(day: string | null): string {
  if (!day) return '—';
  const [year, month, date] = day.split('-');
  return `${date}.${month}.${year}`;
}

export function chartNumber(value: string | number | null): string {
  if (value === null) return '—';
  return Number(value).toLocaleString('de-DE', { maximumFractionDigits: 4 });
}
