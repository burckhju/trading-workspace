const labels: Record<string, string> = {
  NO_CONFIRMED_SAVED_QUOTE_SOURCE: 'Eine bestätigte, gespeicherte Kursquelle fehlt.',
  REVIEW_BID_MISSING: 'Die Quelle liefert keinen verwendbaren Geldkurs.',
  REVIEW_BID_INVALID: 'Der gelieferte Geldkurs ist nicht verwendbar.',
  REVIEW_QUOTE_REFRESH_FAILED: 'Der letzte Kursabruf ist fehlgeschlagen.',
  REVIEW_PRICE_SUPPLY_INTERRUPTED: 'Die Kursversorgung ist unterbrochen.',
  PRODUCT_PRICE_SCALE_EVIDENCE_MISSING: 'Ein ausreichender Produktmaßstabsbeleg fehlt.',
  SESSION_EVIDENCE_MISSING: 'Geeignete Kalenderbelege für die Basiswertsitzungen fehlen.',
  SESSION_BINDING_MISSING: 'Die Bindung an den Basiswertkalender fehlt.',
  SESSION_DAYS_MISSING: 'Der Kalender deckt die erforderlichen Sitzungen nicht ab.',
  EXECUTION_CURRENCY_UNQUALIFIED: 'Die historische Ausführungswährung ist nicht belegt.',
  EXECUTION_BID_CURRENCY_MISMATCH:
    'Ausführungswährung und Geldkurswährung widersprechen sich; der Vergleich ist gesperrt.',
  REVIEW_PRODUCT_SCALE_OWNER_MISMATCH:
    'Produktmaßstab und wirtschaftliche Kaufbasis passen nicht zusammen; der Vergleich ist gesperrt.',
  PRODUCT_SCALE_INDICATION_BINDING_MISMATCH:
    'Produktmaßstab und Kursquelle passen nicht zusammen; der Vergleich ist gesperrt.',
  REVIEW_SOURCE_STATUS_CONFLICT:
    'Die Statusbeobachtungen widersprechen sich; der Vergleich ist gesperrt.',
  REVIEW_LATER_NEGATIVE_STATUS_OBSERVED:
    'Nach dem Kurs wurde ein negativer Marktstatus beobachtet; der Vergleich ist gesperrt.',
  REVIEW_NEGATIVE_STATUS_RECEIVED_AFTER_INDICATION:
    'Nach der Indikation wurde ein negativer Marktstatus empfangen; der Vergleich ist gesperrt.',
  REVIEW_RECOVERY_EVIDENCE_WEAKER:
    'Der spätere Kurs hat eine schwächere Belegqualität und beendet den bestehenden Verlusthinweis nicht.',
  REVIEW_RECOVERY_SOURCE_NOT_COMPARABLE:
    'Die spätere Kursquelle ist für eine Entwarnung nicht vergleichbar. Der Verlusthinweis bleibt offen.',
  REVIEW_TWENTIETH_SESSION_NOT_COMPLETED:
    'Die 20. Basiswertsitzung war zum ausgewiesenen Zeitbezug noch nicht abgeschlossen.',
  INDICATIVE_BID_BELOW_GROSS_ENTRY:
    'Der indikative Geldkurs liegt unter dem persönlichen Bruttoeinstand.',
  INDICATIVE_BID_AT_OR_ABOVE_GROSS_ENTRY:
    'Der indikative Geldkurs erreicht oder überschreitet den persönlichen Bruttoeinstand.',
  POSITION_CLOSED_OR_CANCELLED: 'Die Position ist geschlossen oder storniert.',
};

export function indicativeReasonLabel(reason: string): string {
  return Object.hasOwn(labels, reason) ? labels[reason] : `Gemeldete Voraussetzung: ${reason}`;
}
