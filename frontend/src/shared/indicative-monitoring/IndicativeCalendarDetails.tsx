export function IndicativeCalendarDetails({
  dayPrecision,
  quality,
  verification,
}: {
  dayPrecision?: string | null;
  quality?: string | null;
  verification?: string | null;
}) {
  if (!dayPrecision && !quality && !verification) return null;
  return (
    <div className="space-y-1 text-xs text-amber-200">
      {dayPrecision === 'CONSERVATIVE_DATE_BOUND' && (
        <p>Sitzungszahl konservativ; Kaufdatum ohne genaue Uhrzeit.</p>
      )}
      {quality === 'CURRENT_DOCUMENT_REFERENCE_MARKET_ASSUMED' && (
        <p>
          Referenzmarkt aus aktuellem Produktdokument angenommen; das historische Basiswertlisting
          ist nicht unabhängig belegt.
        </p>
      )}
      {quality === 'DOCUMENTED' && <p>Dokumentierte Kalenderbindung.</p>}
      {verification === 'ENGINEERING_REVIEW_OF_ORIGINAL_CALENDAR_NOT_INDEPENDENT_VERIFICATION' && (
        <p>Originalkalender technisch geprüft; keine unabhängige Systemverifikation.</p>
      )}
      {verification === 'MANUAL_DOCUMENT_REVIEW_NOT_INDEPENDENT_VERIFICATION' && (
        <p>Dokumentierte menschliche Kalenderprüfung; keine unabhängige Systemverifikation.</p>
      )}
    </div>
  );
}
