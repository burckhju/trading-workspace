import type { RealizedGrossFilters, ReportExecutionTime } from '../types/api';

/** Only localize the server's already rounded string; never parse or recalculate money. */
export function moneyText(value: string | null, currency: string | null): string {
  if (value === null) return 'Nicht berechenbar';
  return `${value.replace('.', ',')} ${currency ?? '(Währung unbekannt)'}`;
}

export function executionTimeText(time: ReportExecutionTime, reportTimezone: string): string {
  if (time.time_precision === 'DATE_ONLY') {
    return `${time.executed_on ?? 'Datum unbekannt'} · Uhrzeit unbekannt · ${time.execution_timezone ?? 'Zeitzone unbekannt'}`;
  }
  if (time.time_precision === 'TIMESTAMP' && time.executed_at !== null) {
    return `${new Intl.DateTimeFormat('de-DE', {
      dateStyle: 'medium',
      timeStyle: 'long',
      timeZone: reportTimezone,
    }).format(new Date(time.executed_at))} · ${reportTimezone}`;
  }
  return 'Ausführungsdatum / Zeitzone nicht ausreichend belegt';
}

const reasons: Record<string, string> = {
  CURRENCY_UNKNOWN: 'Ausführungswährung für Verkauf oder Kostenbasis nicht vollständig belegt',
  CURRENCY_MIXED: 'Unterschiedliche Währungen in Verkauf und Kostenbasis; keine Umrechnung',
  COST_BASIS_SOURCE_INCOMPLETE: 'Herkunft der Kostenbasis unvollständig',
  HISTORY_INVALID: 'Wirksame Ausführungshistorie nicht verwendbar',
  PERIOD_AMBIGUOUS: 'Periodenzugehörigkeit wegen der Datums- / Zeitzonenpräzision mehrdeutig',
  PERIOD_UNKNOWN: 'Periodenzugehörigkeit nicht bestimmbar',
  OTHER_CURRENCY: 'Belegte Ausführungswährung außerhalb der Währungsauswahl',
  OUTSIDE_PERIOD: 'Außerhalb des gewählten Zeitraums',
  TRADE_CANCELLED: 'Trade als Fehleintrag storniert; kein wirtschaftlicher Verkauf',
};

export function reasonText(reason: string): string {
  return reasons[reason] ?? `Nicht qualifiziert (${reason})`;
}

export function filterKey(filters: RealizedGrossFilters): string {
  return [
    filters.from_date,
    filters.to_date,
    filters.report_currency,
    filters.report_timezone,
  ].join('|');
}
