import { useEffect, useId, useMemo, useRef, useState } from 'react';
import type {
  PositionPriceHistoryReport,
  PositionPricePoint,
  PositionPriceSeries,
} from '../positionPriceHistory';
import {
  historyPrice,
  historyProvider,
  historySourceMode,
  historyTime,
  historyVenue,
  priceHistoryLabel,
  priceKindLabel,
  type PriceHistoryEvidenceSelection,
} from '../services/priceHistoryPresentation';

const focusStyle = 'focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-sky-300';
const controlFocus =
  'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300';

function PointIdentifiers({
  series,
  point,
}: {
  series: PositionPriceSeries;
  point: PositionPricePoint;
}) {
  return (
    <>
      <span className="block">ISIN {series.isin}</span>
      <span className="block">Notierung: {series.warrant_listing_id}</span>
      <span className="block">Quellsegment: {series.identity_key}</span>
      <span className="block">Serien-ID: {series.id}</span>
      <span className="block">Punkt-ID: {point.id}</span>
    </>
  );
}

export function PositionPriceHistoryEvidence({
  report,
  selection,
}: {
  report: PositionPriceHistoryReport;
  selection?: PriceHistoryEvidenceSelection | null;
}) {
  const evidenceId = useId();
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<
    (PriceHistoryEvidenceSelection & { report: PositionPriceHistoryReport }) | null
  >(null);
  const handledRequest = useRef<number | null>(null);
  const pointsDetails = useRef<HTMLDetailsElement>(null);
  const eventsDetails = useRef<HTMLDetailsElement>(null);
  const pointCard = useRef<HTMLElement>(null);
  const eventRows = useRef(new Map<string, HTMLLIElement>());
  const eventSources = useRef(new Map<string, HTMLDetailsElement>());
  const rows = useMemo(
    () =>
      report.series
        .flatMap((series) => series.points.map((point) => ({ series, point })))
        .sort((a, b) => Date.parse(a.point.observed_at) - Date.parse(b.point.observed_at)),
    [report.series],
  );
  const pages = Math.max(1, Math.ceil(rows.length / 50));
  const currentPage = Math.min(page, pages - 1);
  const selectedTarget =
    selected?.report === report && selected.requestId === selection?.requestId
      ? selected.target
      : null;
  const selectedPointIndex =
    selectedTarget?.kind === 'point'
      ? rows.findIndex(
          ({ series, point }) =>
            series.id === selectedTarget.seriesId && point.id === selectedTarget.pointId,
        )
      : -1;
  const selectedPoint = rows[selectedPointIndex];

  useEffect(() => {
    if (!selection || handledRequest.current === selection.requestId) return;
    // Consume this explicit action once, even if its target is no longer present.
    // A later response must not turn an obsolete action into a focus change.
    handledRequest.current = selection.requestId;
    const target = selection.target;
    if (target.kind === 'point') {
      const index = rows.findIndex(
        ({ series, point }) => series.id === target.seriesId && point.id === target.pointId,
      );
      if (index < 0) return;
      if (pointsDetails.current) pointsDetails.current.open = true;
      setPage(Math.floor(index / 50));
    } else {
      if (!report.events.some((event) => event.id === target.eventId)) return;
      if (eventsDetails.current) eventsDetails.current.open = true;
      const source = eventSources.current.get(target.eventId);
      if (source) source.open = true;
    }
    setSelected({ ...selection, report });
  }, [report, rows, selection]);

  useEffect(() => {
    if (selected?.report !== report || selected.requestId !== selection?.requestId) return;
    const target = selected.target;
    if (target.kind === 'point') pointCard.current?.focus();
    else eventRows.current.get(target.eventId)?.focus();
  }, [report, selected, selection?.requestId]);

  return (
    <>
      {rows.length > 0 && (
        <details
          ref={pointsDetails}
          className="min-w-0 space-y-3 rounded border border-slate-700 p-3"
        >
          <summary className={`cursor-pointer font-semibold ${controlFocus}`}>
            Kursdaten und Quellen
          </summary>
          {selectedPoint && (
            <section
              ref={pointCard}
              id={`${evidenceId}-selected-point`}
              tabIndex={-1}
              aria-labelledby={`${evidenceId}-selected-point-heading`}
              className={`min-w-0 space-y-2 rounded border border-sky-700 bg-slate-900 p-3 text-sm ${focusStyle}`}
            >
              <h4 id={`${evidenceId}-selected-point-heading`} className="font-semibold">
                Ausgewählter Originalkursbeleg
              </h4>
              <p className="break-words font-medium text-slate-100">
                {historyPrice(selectedPoint.point.price)} {selectedPoint.series.currency} ·{' '}
                {priceKindLabel[selectedPoint.series.price_kind]}
              </p>
              <p className="break-words">
                {historyProvider(selectedPoint.series.provider)} ·{' '}
                {historySourceMode(selectedPoint.series.source_mode)}
              </p>
              <p className="break-words">{historyVenue(selectedPoint.series)}</p>
              <p>
                Originalkurszeit:{' '}
                <time dateTime={selectedPoint.point.observed_at}>
                  {historyTime(selectedPoint.point.observed_at)}
                </time>
                <span className="block break-all text-xs text-slate-300">
                  {selectedPoint.point.observed_at}
                </span>
              </p>
              <p className="text-xs text-slate-300">
                {priceHistoryLabel(selectedPoint.point.status)}. Derselbe Originalbeleg steht auf
                Tabellenseite {Math.floor(selectedPointIndex / 50) + 1}.
              </p>
              <details className="min-w-0 text-xs text-slate-300">
                <summary className={`cursor-pointer py-2 ${controlFocus}`}>
                  Technische Angaben zum ausgewählten Kursbeleg
                </summary>
                <div className="space-y-1 break-all">
                  <PointIdentifiers series={selectedPoint.series} point={selectedPoint.point} />
                  <p>
                    Quellenmodus: {selectedPoint.series.source_mode ?? 'Quellenmodus unbekannt'}
                  </p>
                  <p>
                    Empfangen:{' '}
                    <time dateTime={selectedPoint.point.retrieved_at}>
                      {historyTime(selectedPoint.point.retrieved_at)}
                    </time>{' '}
                    ({selectedPoint.point.retrieved_at})
                  </p>
                  <p>
                    Erfasst:{' '}
                    {selectedPoint.point.captured_at ? (
                      <>
                        <time dateTime={selectedPoint.point.captured_at}>
                          {historyTime(selectedPoint.point.captured_at)}
                        </time>{' '}
                        ({selectedPoint.point.captured_at})
                      </>
                    ) : (
                      'Kein Stichprobenzeitpunkt'
                    )}
                  </p>
                  <p>
                    Speicherung: {selectedPoint.point.storage} · Zeitbasis:{' '}
                    {selectedPoint.point.quote_time_basis ?? 'Keine Zusatzangabe'}
                  </p>
                </div>
              </details>
            </section>
          )}
          <p className="text-xs text-slate-300 sm:hidden">
            Die Tabelle lässt sich seitlich scrollen, um alle Quellenangaben zu lesen.
          </p>
          <div
            className={`min-w-0 overflow-x-auto ${controlFocus}`}
            tabIndex={0}
            role="region"
            aria-label="Historische Kursdaten"
          >
            <table className="w-full min-w-[56rem] text-left text-xs">
              <caption className="mb-2 text-left">Originalkurse und gespeicherte Herkunft</caption>
              <thead>
                <tr>
                  {[
                    'Originalkurszeit',
                    'Kurs',
                    'Herkunft',
                    'Empfangen / erfasst',
                    'Qualität und Zeitbasis',
                  ].map((title) => (
                    <th scope="col" key={title} className="p-2 align-top">
                      {title}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows
                  .slice(currentPage * 50, (currentPage + 1) * 50)
                  .map(({ series, point }, index) => (
                    <tr
                      key={JSON.stringify([series.id, point.id])}
                      id={`${evidenceId}-point-${currentPage * 50 + index}`}
                      className={`border-t border-slate-700 ${selectedPointIndex === currentPage * 50 + index ? 'bg-slate-800' : ''}`}
                    >
                      <th scope="row" className="whitespace-nowrap p-2 align-top font-normal">
                        <time dateTime={point.observed_at}>{historyTime(point.observed_at)}</time>
                        <span className="block text-slate-300">{point.observed_at}</span>
                      </th>
                      <td className="whitespace-nowrap p-2 align-top">
                        {historyPrice(point.price)} {series.currency}
                        <span className="block">{priceKindLabel[series.price_kind]}</span>
                      </td>
                      <td className="max-w-xs break-all p-2 align-top">
                        {series.provider} · {series.source_mode ?? 'Quellenmodus unbekannt'}
                        <span className="block">{historyVenue(series)}</span>
                        <PointIdentifiers series={series} point={point} />
                      </td>
                      <td className="whitespace-nowrap p-2 align-top">
                        Empfangen:{' '}
                        <time dateTime={point.retrieved_at}>{historyTime(point.retrieved_at)}</time>
                        <span className="block">
                          Erfasst:{' '}
                          {point.captured_at ? (
                            <time dateTime={point.captured_at}>
                              {historyTime(point.captured_at)}
                            </time>
                          ) : (
                            'Kein Stichprobenzeitpunkt'
                          )}
                        </span>
                        <span className="block">
                          {point.storage === 'RETAINED'
                            ? 'Zuletzt erfolgreich gespeicherter Kurs'
                            : 'Gespeicherte Stichprobe'}
                        </span>
                      </td>
                      <td className="p-2 align-top">
                        {priceHistoryLabel(point.status)}
                        <span className="block">
                          {point.quote_time_basis ?? 'Keine Zusatzangabe'}
                        </span>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <button
              type="button"
              disabled={currentPage === 0}
              onClick={() => setPage(currentPage - 1)}
              className={`min-h-11 rounded border px-3 py-2 disabled:opacity-40 ${controlFocus}`}
            >
              Vorige Kurspunkte
            </button>
            <span>
              Seite {currentPage + 1} / {pages}
            </span>
            <button
              type="button"
              disabled={currentPage + 1 >= pages}
              onClick={() => setPage(currentPage + 1)}
              className={`min-h-11 rounded border px-3 py-2 disabled:opacity-40 ${controlFocus}`}
            >
              Weitere Kurspunkte
            </button>
          </div>
        </details>
      )}
      <details
        ref={eventsDetails}
        className="min-w-0 space-y-3 rounded border border-slate-700 p-3"
      >
        <summary className={`cursor-pointer font-semibold ${controlFocus}`}>
          Kauf- und Verkaufsereignisse
        </summary>
        <p className="text-xs text-slate-300">
          Aktuell gültige Buchungen dieser Position. Ein Datumsbeleg wird ohne angenommene Uhrzeit
          aufgeführt. Nur belegte Uhrzeit und Ausführungswährung erlauben einen Diagrammmarker.
          Ausführungspreise sind Buchungsbelege, keine Marktbeobachtungen.
        </p>
        {report.events.length === 0 ? (
          <p>Keine zuordenbaren Kauf-/Verkaufsereignisse im gewählten Zeitraum.</p>
        ) : (
          <ul className="space-y-3">
            {report.events.map((event, index) => (
              <li
                key={event.id}
                id={`${evidenceId}-event-${index}`}
                ref={(element) => {
                  if (element) eventRows.current.set(event.id, element);
                  else eventRows.current.delete(event.id);
                }}
                tabIndex={-1}
                className={`min-w-0 space-y-2 break-words rounded border border-slate-700 p-3 ${focusStyle}`}
              >
                <p className="font-medium text-slate-100">
                  {event.side === 'BUY' ? 'Kauf' : 'Verkauf'} · {event.quantity} Stück ·{' '}
                  {historyPrice(event.price)} {event.currency ?? 'Währung unbekannt'}
                </p>
                <p>
                  {event.executed_on ? (
                    <>
                      Ausgeführt am {event.executed_on} · Uhrzeit unbekannt ·{' '}
                      {event.execution_timezone ?? 'Zeitzone unbekannt'}
                    </>
                  ) : event.occurred_at ? (
                    <>
                      Ausgeführt:{' '}
                      <time dateTime={event.occurred_at}>{historyTime(event.occurred_at)}</time>
                    </>
                  ) : (
                    'Ausführungszeit nicht belegt'
                  )}
                </p>
                <p className="text-xs text-slate-300">
                  {event.executed_on
                    ? 'Präzision: Datum ohne Uhrzeit'
                    : event.occurred_at
                      ? 'Präzision: Datum und Uhrzeit überliefert'
                      : 'Präzision: nicht belegt'}
                  {!event.executed_on && (
                    <> · Zeitzone des Belegs: {event.execution_timezone ?? 'nicht angegeben'}</>
                  )}
                </p>
                {event.occurred_at && (
                  <p className="break-all text-xs text-slate-300">
                    Originalzeit: {event.occurred_at}
                  </p>
                )}
                {!event.plottable && (
                  <p className="text-amber-200">
                    Kein Diagrammmarker:{' '}
                    {event.reason
                      ? priceHistoryLabel(event.reason)
                      : 'Zeit oder Währung nicht ausreichend belegt'}
                    .
                  </p>
                )}
                <details
                  ref={(element) => {
                    if (element) eventSources.current.set(event.id, element);
                    else eventSources.current.delete(event.id);
                  }}
                  className="min-w-0 text-xs text-slate-300"
                >
                  <summary className={`cursor-pointer py-2 ${controlFocus}`}>
                    Buchungsbeleg und Währungsherkunft
                  </summary>
                  <p className="break-all">
                    Buchung {event.id} · Währungsherkunft: {event.currency_source}
                  </p>
                </details>
              </li>
            ))}
          </ul>
        )}
      </details>
    </>
  );
}
