const labels: Record<string, string> = {
  AVAILABLE: 'Auswertbar',
  NOT_EVALUABLE: 'Nicht auswertbar',
  LIMITED: 'Eingeschränkt',
  INITIALIZED: 'Erster Zustand – kein belegter Trendbruch',
  CONFIRMING: 'Wechsel wird bestätigt',
  CROSSED_BELOW: 'Wechsel unter SMA20 bestätigt',
  CROSSED_ABOVE: 'Wechsel über SMA20 bestätigt',
  UNCHANGED: 'Trendzustand unverändert',
  SAME_OR_OLDER_SESSION: 'Kein zusätzlicher Handelstag',
  ABOVE: 'Über SMA20',
  BELOW: 'Unter SMA20',
  IN_BAND: 'Im Hystereseband',
  UNINITIALIZED: 'Noch kein qualifizierter Zustand',
  FAVORABLE: 'Richtung für dieses Produkt günstig',
  UNFAVORABLE: 'Richtung für dieses Produkt ungünstig',
  NEUTRAL: 'Keine klare Richtung',
  DIRECTION_UNKNOWN: 'Call/Put nicht bestätigt',
  NEED_21_COMPLETED_ADJUSTED_CLOSES:
    'Mindestens 21 abgeschlossene bereinigte Tageskurse erforderlich',
  EOD_STALE: 'Basiswertdaten veraltet',
  MISSING_SESSION_OR_UNVERIFIED_HOLIDAY: 'Sitzung fehlt oder Feiertag nicht verifiziert',
  ADJUSTED_CLOSE_MISSING: 'Bereinigter Schlusskurs fehlt',
  EOD_QUALITY_LIMITED: 'Qualität der Tagesreihe eingeschränkt',
  QUALIFIED_COMPLETED_OBSERVATIONS: 'Abgeschlossene Tagesreihe qualifiziert',
  DATA_NOT_KNOWN_AT_EVALUATION: 'Daten am Auswertungsstichtag noch nicht bekannt',
  PRODUCT_TERMS_OR_PRIMARY_LISTING_MISSING: 'Produkt oder eindeutiges Hauptlisting fehlt',
  PRODUCT_HISTORY_NOT_AVAILABLE: 'Echte Optionsschein-Kurshistorie fehlt',
  EOD_SESSION_CLOSE_INSTANT_UNVERIFIED:
    'Exakter Schlusskurszeitpunkt des Basiswerts nicht verifiziert',
  SOURCE_TIME_OR_TIMEZONE_UNKNOWN: 'Originalkurszeit oder Zeitzone unbekannt',
  LATEST_REFRESH_NOT_OBSERVED_BY_PERSISTED_READER:
    'Letzter Abrufstatus in der gespeicherten Quote nicht belegt',
  QUOTE_RETAINED_OR_REFRESH_FAILED: 'Letzte Quote übernommen oder Abruf fehlgeschlagen',
  QUOTE_STALE: 'Optionsscheinquote veraltet',
  ASK_MISSING: 'Briefseite fehlt',
  POSITIVE_BID_MISSING: 'Positive Geldseite fehlt',
  BID_VOLUME_UNKNOWN: 'Geldvolumen unbekannt',
  ASK_VOLUME_UNKNOWN: 'Briefvolumen unbekannt',
  BID_VOLUME_ZERO: 'Geldvolumen null',
  ASK_VOLUME_ZERO: 'Briefvolumen null',
  NO_CONFIRMED_SAVED_QUOTE_SOURCE: 'Keine bestätigte Kursquelle',
  CORPORATE_ACTION_OR_ADJUSTMENT_CHANGE:
    'ATR wegen Kapitalmaßnahme oder Bereinigungswechsel begrenzt',
  FIRST_SNAPSHOT_IS_NOT_A_TREND_BREAK: 'Erster Snapshot ohne belegten Zustandswechsel',
  NO_ADDITIONAL_CONFIRMATION_SESSION: 'Wiederholter Handelstag zählt nicht als Bestätigung',
  CONFIRMED_SESSION_STATE: 'Qualifizierter fortlaufender Sitzungszustand',
  CONFIRMATION_RESTARTED_AFTER_GAP: 'Bestätigung nach Datenlücke neu begonnen',
};
export const riskLabel = (code: string) => labels[code] ?? `Datenhinweis: ${code}`;
export const riskPercent = (value: string | null) =>
  value === null
    ? 'Nicht auswertbar'
    : new Intl.NumberFormat('de-DE', { style: 'percent', maximumFractionDigits: 2 }).format(
        Number(value),
      );
