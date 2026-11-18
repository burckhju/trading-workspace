const stages: Record<string, string> = {
  WARNING_DUE: 'Vorwarnung zur dokumentierten Sitzung vor dem Produkttermin',
  EXIT_SESSION_STARTED: 'Dokumentierter Termintag hat begonnen',
  CALENDAR_SESSION_ENDED: 'Dokumentierte Kalendersitzung am Termintag ist beendet',
  WARNING_DAY_REACHED: 'Lokaler Kalendertag der Vorwarnung erreicht',
  DEADLINE_DAY_REACHED: 'Dokumentierter Produkttermin erreicht · tagesgenau',
  DEADLINE_DAY_PASSED: 'Dokumentierter Produkttermin liegt in der Vergangenheit · tagesgenau',
};

export function ProductDeadlineContext({
  context,
  dataUnavailable,
}: {
  context: Record<string, string | null> | null | undefined;
  dataUnavailable: boolean;
}) {
  const dayOnly = context?.calendar_precision === 'DAY_ONLY';
  return (
    <div className="mt-2 space-y-2 text-sm text-slate-400">
      <p>
        Teilumfang: Dokumentierte Produkttermine · {context?.rule_version ?? 'Version nicht belegt'}
      </p>
      <p>
        {dataUnavailable
          ? 'Die Produkttermin-Erinnerung kann mit den gespeicherten Produkt- und Kalenderbelegen nicht beurteilt werden.'
          : context?.deadline_stage && Object.hasOwn(stages, context.deadline_stage)
            ? stages[context.deadline_stage]
            : 'Terminstand nicht eindeutig ausgewiesen'}
      </p>
      <dl className="grid gap-3 sm:grid-cols-2">
        <div>
          <dt>Maßgeblicher Produkttermin</dt>
          <dd>{context?.relevant_product_date ?? 'Nicht belegt'}</dd>
        </div>
        <div>
          <dt>Letzter Handelstag laut Produktbeleg</dt>
          <dd>{context?.last_trading_on ?? 'Nicht belegt'}</dd>
        </div>
        <div>
          <dt>Festgelegter Ausstiegshandelsplatz</dt>
          <dd>{context?.exit_venue_mic ?? 'Nicht belegt'}</dd>
        </div>
        <div>
          <dt>Kalendersitzung für die Erinnerung</dt>
          <dd>{context?.exit_session_date ?? 'Nicht belegt'}</dd>
        </div>
        {dayOnly ? (
          <div>
            <dt>Lokaler Kalendertag der Vorwarnung</dt>
            <dd>{context?.warning_session_date ?? 'Nicht belegt'}</dd>
          </div>
        ) : (
          <>
            <div>
              <dt>Dokumentierter Sitzungsbeginn</dt>
              <dd>{context?.exit_session_opens_at ?? 'Nicht belegt'}</dd>
            </div>
            <div>
              <dt>Dokumentiertes Sitzungsende</dt>
              <dd>{context?.calendar_session_closes_at ?? 'Nicht belegt'}</dd>
            </div>
          </>
        )}
      </dl>
      <p className="text-amber-200">
        {dayOnly
          ? 'Der Tageskalender belegt keine Eröffnungs- oder Schlussuhrzeit und keine produktbezogene letzte Handelsuhrzeit.'
          : 'Produktbezogene letzte Handelsuhrzeit nicht verifiziert. Der Kalenderschluss bestätigt keine ausführbare Produktfrist.'}{' '}
        Diese Erinnerung ist ein Teilumfang; B05 bleibt unvollständig qualifiziert.
      </p>
      <p>
        Unabhängig von einer aktuellen BID-Verfügbarkeit. Ausschließlich ein Prüfhinweis; keine
        Orderfreigabe.
      </p>
      {context?.scheduled_at && <p>Dokumentierter Anlasszeitpunkt: {context.scheduled_at}</p>}
      {dayOnly && context?.scheduled_on && (
        <p>Lokaler Kalendertag des Anlasses: {context.scheduled_on}</p>
      )}
      {context?.source_reference && <p>Produktquelle: {context.source_reference}</p>}
      {(context?.product_verification || context?.calendar_verification) && (
        <p>
          Belegprüfung: Produkt {context.product_verification ?? 'nicht ausgewiesen'} · Kalender{' '}
          {context.calendar_verification ?? 'nicht ausgewiesen'}. Eine dokumentierte menschliche
          Prüfung ist keine unabhängige Systemverifikation.
        </p>
      )}
      {context?.data_problem_reasons && (
        <details className="text-xs">
          <summary className="cursor-pointer">Offene Produkt- oder Kalendervoraussetzungen</summary>
          <p className="mt-1 break-all">{context.data_problem_reasons}</p>
        </details>
      )}
    </div>
  );
}
