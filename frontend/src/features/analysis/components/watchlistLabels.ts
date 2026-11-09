/** Text for existing owner reasons; never a new status or eligibility decision. */
const setupReasons: Record<string, string> = {
  EODHD_DISABLED:
    'EODHD ist ausgeschaltet. Die Kursquelle muss verfügbar sein, bevor die Einrichtung weiterlaufen kann.',
  EODHD_MAPPING_REQUIRED: 'Für diese Reihe fehlt noch ein EODHD-Mapping.',
  VALIDATED_EODHD_MAPPING_REQUIRED: 'Für diese Reihe fehlt noch ein aktiv geprüftes EODHD-Mapping.',
  MAPPING_CONFIRMATION_PENDING:
    'Die Zuordnung ist vorhanden; ihr Abschlussbeleg wird noch gespeichert.',
  MAPPING_CHANGED_SINCE_WATCHLIST_SETUP:
    'Die Mappingrevision hat sich seit der Einrichtung geändert. Die Datenbasis muss vor der weiteren Aktualisierung geprüft werden.',
  EXISTING_INACTIVE_MAPPING_PRESERVED:
    'Ein vorhandenes inaktives Mapping wurde beibehalten. Es wird nicht automatisch wieder aktiviert.',
  EXISTING_PROVIDER_MAPPING_CONFLICT:
    'Die vorhandene Providerzuordnung widerspricht dieser Katalogidentität.',
  EODHD_PROVIDER_IDENTITY_ALREADY_MAPPED:
    'Diese Providerkennung ist bereits einer anderen Identität zugeordnet.',
  ETF_LISTING_IDENTITY_CONFLICT:
    'Die vorhandene ETF-Notierung passt nicht eindeutig zur Katalogidentität.',
  ETF_MASTER_DATA_INACTIVE: 'Die vorhandenen ETF-Stammdaten sind inaktiv.',
  UNDERLYING_TYPE_CONFLICT: 'Der vorhandene Wertpapiertyp passt nicht zum ETF-Katalogeintrag.',
  TRADING_VENUE_INACTIVE: 'Der erforderliche Handelsplatz ist inaktiv.',
  TRADING_VENUE_INACTIVE_OR_MISSING: 'Der erforderliche aktive Handelsplatz fehlt.',
  TRADING_VENUE_REFERENCE_CONFLICT: 'Der vorhandene Handelsplatz widerspricht dem Quellenbeleg.',
  CURRENCY_INACTIVE: 'Die erforderliche Währung ist inaktiv.',
  CURRENCY_INACTIVE_OR_MISSING: 'Die erforderliche aktive Währung fehlt.',
  CURRENCY_CATALOG_REQUIRED: 'Die erforderliche Währung fehlt im administrierten Währungskatalog.',
  CURRENCY_REFERENCE_CONFLICT: 'Die vorhandene Währungsidentität widerspricht dem Quellenbeleg.',
  MARKET_REFERENCE_INACTIVE: 'Die vorhandene Marktreferenz ist inaktiv.',
  MARKET_REFERENCE_IDENTITY_CONFLICT:
    'Die vorhandene Marktreferenz passt nicht eindeutig zur Katalogidentität.',
  EXISTING_INDEX_RETURN_BASIS_CONFLICT:
    'Eine vorhandene Indexgrundlage widerspricht dem Quellenbeleg. Sie wird nicht automatisch ersetzt.',
  ETF_PROVIDER_IDENTITY_NOT_VALIDATED:
    'Die ETF-Identität wurde vom Provider noch nicht eindeutig bestätigt.',
  INDEX_PROVIDER_IDENTITY_NOT_VALIDATED:
    'Die Indexidentität wurde vom Provider noch nicht eindeutig bestätigt.',
  SETUP_CONCURRENT_MODIFICATION:
    'Die Datenbasis wurde während der Einrichtung geändert. Der aktuelle Stand muss erneut geprüft werden.',
  PROVIDER_IDENTITY_VERIFICATION_FAILED:
    'Die Provideridentität konnte nicht eindeutig bestätigt werden.',
};

export function watchlistSetupReason(reason: string): string {
  return (
    setupReasons[reason] ??
    'Die Datenbasis konnte noch nicht vollständig bestätigt werden. Der genaue Backendgrund steht in den Details.'
  );
}

/** Labels for the existing process-local refresh owner, independent of setup status. */
export function watchlistRefreshStatus(status: string): string {
  const labels: Record<string, string> = {
    PENDING: 'Abruf ausstehend',
    AVAILABLE: 'Abruf erfolgreich',
    MISSING: 'Keine Daten gemeldet',
    BLOCKED: 'Abruf blockiert',
    ERROR: 'Abruf fehlgeschlagen',
    DEFERRED: 'Abruf zurückgestellt',
  };
  return labels[status] ?? status;
}
