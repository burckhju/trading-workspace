import { lazy, Suspense, useEffect, useState } from 'react';
import type { PositionPriceHistoryDays, PositionPriceHistoryReport } from '../positionPriceHistory';
import { readPositionPriceHistory } from '../services/positionPriceHistory';
import {
  availableHistoryDays,
  historyTime,
  priceHistoryLabel,
  priceKindLabel,
  historyVenue,
} from '../services/priceHistoryPresentation';
import { PositionPriceHistoryEvidence } from './PositionPriceHistoryEvidence';

// Keep chart dependencies out of the initial workspace bundle. Evidence remains
// readable if the optional diagram module cannot be loaded.
const PositionPricePlot = lazy(async () => {
  try {
    const module = await import('./PositionPricePlot');
    return { default: module.PositionPricePlot };
  } catch {
    return {
      default: function ChartUnavailable() {
        return (
          <p role="alert">
            Das Diagramm konnte nicht geladen werden. Alle belegten Werte stehen unter „Kursdaten
            und Quellen“.
          </p>
        );
      },
    };
  }
});

interface Props {
  tradeId: string;
  positionId: string;
  reloadToken?: number;
}

export function PositionPriceHistory(props: Props) {
  return (
    <History key={`${props.tradeId}:${props.positionId}:${props.reloadToken ?? 0}`} {...props} />
  );
}

function History({ tradeId, positionId }: Props) {
  const [days, setDays] = useState<PositionPriceHistoryDays>('all');
  const [availableDays, setAvailableDays] = useState<PositionPriceHistoryDays[]>([]);
  const [attempt, setAttempt] = useState(0);
  // A missing ID is visible by default. Only explicit user choices hide a series.
  const [hiddenSeriesIds, setHiddenSeriesIds] = useState<string[]>([]);
  const [state, setState] = useState<{
    report: PositionPriceHistoryReport | null;
    error: boolean;
  }>({ report: null, error: false });
  useEffect(() => {
    const controller = new AbortController();
    readPositionPriceHistory(tradeId, positionId, days, controller.signal)
      .then((report) => {
        if (!controller.signal.aborted) {
          setState({ report, error: false });
          if (days === 'all') setAvailableDays(availableHistoryDays(report));
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) setState({ report: null, error: true });
      });
    return () => controller.abort();
  }, [tradeId, positionId, days, attempt]);
  const { report, error } = state;
  const series = report?.series.filter((item) => item.points.length > 0) ?? [];
  const visibleSeries = series.filter((item) => !hiddenSeriesIds.includes(item.id));
  const currencies = [...new Set(visibleSeries.map((item) => item.currency))];
  const pointCount = series.reduce((count, item) => count + item.points.length, 0);
  const visiblePointCount = visibleSeries.reduce((count, item) => count + item.points.length, 0);
  return (
    <section
      aria-label="Positionskursverlauf"
      className="min-w-0 space-y-4 rounded-xl border border-slate-700 bg-slate-950/40 p-3 sm:p-4"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="font-semibold text-white">Historischer Positionskurs</h3>
        <label className="min-w-0 text-xs">
          Zeitraum
          <select
            className="ml-2 max-w-full rounded border border-slate-600 bg-slate-950 p-2"
            value={days}
            onChange={(event) => {
              setState({ report: null, error: false });
              setDays(event.target.value as PositionPriceHistoryDays);
            }}
          >
            <option value="all">Alle gespeicherten Kurse</option>
            {(['7', '31', '90'] as const).map((range) => (
              <option key={range} value={range} disabled={!availableDays.includes(range)}>
                {range} Tage
              </option>
            ))}
          </select>
        </label>
      </div>
      <p className="text-slate-300">
        Gespeicherte Einzelbeobachtungen. Zwischen den Punkten ist kein Kursverlauf belegt.
      </p>
      <p className="text-xs text-slate-400">
        Kurze Zeiträume sind nur wählbar, wenn darin gespeicherte Originalkurse belegt sind.
      </p>
      {!report && !error && <p aria-live="polite">Gespeicherte Kurse werden geladen …</p>}
      {error && (
        <div className="space-y-2">
          <p role="alert">Kursverlauf konnte nicht geladen werden.</p>
          <button
            type="button"
            className="rounded border border-slate-600 px-3 py-2"
            onClick={() => {
              setState({ report: null, error: false });
              setAttempt(attempt + 1);
            }}
          >
            Kursverlauf erneut laden
          </button>
        </div>
      )}
      {report && (
        <>
          <p className="text-xs text-slate-400">
            ISIN {report.isin ?? 'nicht hinterlegt'} · {pointCount}{' '}
            {pointCount === 1 ? 'belegter Kurspunkt' : 'belegte Kurspunkte'}.
            <span className="block">
              Zeitraum:{' '}
              {report.window_start ? historyTime(report.window_start) : 'Alle gespeicherten Kurse'}
              {' bis '}
              {historyTime(report.window_end)}.
            </span>
          </p>
          {report.truncated && (
            <p className="rounded border border-amber-800 p-3 text-amber-200">
              Begrenzter Ausschnitt: {report.samples_considered} von {report.samples_available}{' '}
              gespeicherten Stichproben geprüft (Grenze {report.sample_limit}). Ältere Belege können
              fehlen. Dieser Ausschnitt belegt keine vollständige Historie.
            </p>
          )}
          {series.length > 1 && (
            <fieldset className="min-w-0 space-y-2 rounded border border-slate-700 p-3">
              <legend className="px-1 font-semibold">Sichtbare Kursquellen</legend>
              <p className="text-xs text-slate-400">
                Nur die Diagrammansicht wird gefiltert. Originalbelege und Buchungen bleiben
                vollständig erreichbar. {visiblePointCount} von {pointCount} Kurspunkten sichtbar.
              </p>
              <div className="flex flex-wrap gap-2">
                {series.map((item) => (
                  <label key={item.id} className="flex max-w-full items-start gap-2 rounded border border-slate-700 p-2 text-xs">
                    <input
                      type="checkbox"
                      className="mt-0.5 accent-sky-400"
                      checked={!hiddenSeriesIds.includes(item.id)}
                      onChange={(event) =>
                        setHiddenSeriesIds((previous) =>
                          event.target.checked
                            ? previous.filter((id) => id !== item.id)
                            : [...previous, item.id],
                        )
                      }
                    />
                    <span className="min-w-0 break-words">
                      {item.provider} · {priceKindLabel[item.price_kind]} · {item.currency} · Quellsegment {item.identity_key}
                      <span className="block text-slate-400">{historyVenue(item)}</span>
                      <span className="block text-slate-400">{item.source_mode ?? 'Quellenmodus unbekannt'}</span>
                    </span>
                  </label>
                ))}
              </div>
              <button
                type="button"
                className="rounded border border-slate-600 px-3 py-2 text-xs focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-400"
                onClick={() => setHiddenSeriesIds([])}
              >
                Alle Kursquellen anzeigen
              </button>
            </fieldset>
          )}
          {pointCount === 0 ? (
            <p className="rounded border border-slate-700 p-4 text-slate-300">
              Keine zeitlich und fachlich zuordenbaren Kursdaten vorhanden.
            </p>
          ) : visibleSeries.length === 0 ? (
            <p role="status" className="rounded border border-slate-700 p-4 text-slate-300">
              Alle Kursquellen sind für das Diagramm ausgeblendet. Die gespeicherten
              Kursbelege sind weiterhin unter „Kursdaten und Quellen“ erreichbar.
            </p>
          ) : (
            <Suspense fallback={<p>Diagramm wird geladen …</p>}>
              {currencies.map((currency) => (
                <PositionPricePlot
                  key={currency}
                  currency={currency}
                  series={visibleSeries.filter((item) => item.currency === currency)}
                  events={report.events}
                />
              ))}
            </Suspense>
          )}
          {Object.entries(report.excluded).some(([, count]) => count > 0) && (
            <div className="space-y-1 text-xs text-amber-200">
              <p>Nicht als Kurspunkt darstellbare Belege:</p>
              <ul className="list-disc pl-5">
                {Object.entries(report.excluded)
                  .filter(([, count]) => count > 0)
                  .map(([reason, count]) => (
                    <li key={reason}>
                      {priceHistoryLabel(reason)}: {count}
                    </li>
                  ))}
              </ul>
            </div>
          )}
          <PositionPriceHistoryEvidence key={`${days}:${attempt}`} report={report} />
          <p className="text-xs text-slate-400">
            Erste gespeicherte Stichprobe: {historyTime(report.collection_started_at)}. Eine
            vollständige Handelszeitabdeckung ist nicht belegt. Wiederholte gespeicherte Kurse
            ergeben keine zusätzlichen Originalkurszeiten. Quellen- und Preisarten bleiben getrennt.
            Ein letzter gespeicherter Kurs kann der einzige belegte Punkt sein.
          </p>
        </>
      )}
    </section>
  );
}
