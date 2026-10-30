import { useState } from 'react';
import type { PositionPriceHistoryReport } from '../positionPriceHistory';
import {
  historyPrice,
  historyTime,
  priceHistoryLabel,
  priceKindLabel,
} from '../services/priceHistoryPresentation';

export function PositionPriceHistoryEvidence({ report }: { report: PositionPriceHistoryReport }) {
  const [page, setPage] = useState(0);
  const rows = report.series
    .flatMap((series) => series.points.map((point) => ({ series, point })))
    .sort((a, b) => Date.parse(a.point.observed_at) - Date.parse(b.point.observed_at));
  const pages = Math.max(1, Math.ceil(rows.length / 50));
  return (
    <>
      {rows.length > 0 && (
        <details className="min-w-0 space-y-3 rounded border border-slate-700 p-3">
          <summary className="cursor-pointer font-semibold">Kursdaten und Quellen</summary>
          <p className="text-xs text-slate-400 sm:hidden">
            Die Tabelle lässt sich seitlich scrollen, um alle Quellenangaben zu lesen.
          </p>
          <div
            className="overflow-x-auto"
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
                {rows.slice(page * 50, (page + 1) * 50).map(({ series, point }) => (
                  <tr key={`${series.id}:${point.id}`} className="border-t border-slate-700">
                    <th scope="row" className="whitespace-nowrap p-2 align-top font-normal">
                      <time dateTime={point.observed_at}>{historyTime(point.observed_at)}</time>
                      <span className="block text-slate-400">{point.observed_at}</span>
                    </th>
                    <td className="whitespace-nowrap p-2 align-top">
                      {historyPrice(point.price)} {series.currency}
                      <span className="block">{priceKindLabel[series.price_kind]}</span>
                    </td>
                    <td className="max-w-xs break-all p-2 align-top">
                      {series.provider} · {series.source_mode ?? 'Quellenmodus unbekannt'}
                      <span className="block">ISIN {series.isin}</span>
                      <span className="block">Notierung: {series.warrant_listing_id}</span>
                      <span className="block">Quellsegment: {series.identity_key}</span>
                    </td>
                    <td className="whitespace-nowrap p-2 align-top">
                      Empfangen:{' '}
                      <time dateTime={point.retrieved_at}>{historyTime(point.retrieved_at)}</time>
                      <span className="block">
                        Erfasst:{' '}
                        {point.captured_at ? (
                          <time dateTime={point.captured_at}>{historyTime(point.captured_at)}</time>
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
              disabled={page === 0}
              onClick={() => setPage(page - 1)}
              className="rounded border px-3 py-2 disabled:opacity-40"
            >
              Vorige Kurspunkte
            </button>
            <span>
              Seite {page + 1} / {pages}
            </span>
            <button
              type="button"
              disabled={page + 1 >= pages}
              onClick={() => setPage(page + 1)}
              className="rounded border px-3 py-2 disabled:opacity-40"
            >
              Weitere Kurspunkte
            </button>
          </div>
        </details>
      )}
      <details className="min-w-0 space-y-3 rounded border border-slate-700 p-3">
        <summary className="cursor-pointer font-semibold">Kauf- und Verkaufsereignisse</summary>
        <p className="text-xs text-slate-400">
          Aktuell gültige Buchungen dieser Position. Ein Datumsbeleg wird ohne angenommene Uhrzeit
          aufgeführt. Nur belegte Uhrzeit und Ausführungswährung erlauben einen Diagrammmarker.
        </p>
        {report.events.length === 0 ? (
          <p>Keine zuordenbaren Kauf-/Verkaufsereignisse im gewählten Zeitraum.</p>
        ) : (
          <ul className="space-y-3">
            {report.events.map((event) => (
              <li key={event.id} className="break-words border-t border-slate-700 pt-2">
                <p>
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
                {!event.plottable && (
                  <p className="text-amber-200">
                    Kein Diagrammmarker:{' '}
                    {event.reason
                      ? priceHistoryLabel(event.reason)
                      : 'Zeit oder Währung nicht ausreichend belegt'}
                    .
                  </p>
                )}
                <p className="break-all text-xs text-slate-400">
                  Buchung {event.id} · Währungsherkunft: {event.currency_source}
                </p>
              </li>
            ))}
          </ul>
        )}
      </details>
    </>
  );
}
