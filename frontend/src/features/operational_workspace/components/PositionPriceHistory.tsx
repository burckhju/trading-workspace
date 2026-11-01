import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import type { PositionPriceHistoryDays, PositionPriceHistoryReport } from '../positionPriceHistory';
import { readPositionPriceHistory } from '../services/positionPriceHistory';
import {
  availableHistoryDays,
  historyTime,
  priceHistoryLabel,
  type PriceHistoryEvidenceSelection,
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
  const [evidenceSelection, setEvidenceSelection] = useState<PriceHistoryEvidenceSelection | null>(
    null,
  );
  const requestGeneration = useRef(0);
  const [state, setState] = useState<{
    report: PositionPriceHistoryReport | null;
    error: boolean;
  }>({ report: null, error: false });
  useEffect(() => {
    const controller = new AbortController();
    const generation = ++requestGeneration.current;
    const isCurrent = () => generation === requestGeneration.current && !controller.signal.aborted;
    readPositionPriceHistory(tradeId, positionId, days, controller.signal)
      .then((report) => {
        if (isCurrent()) {
          setState({ report, error: false });
          if (days === 'all') setAvailableDays(availableHistoryDays(report));
        }
      })
      .catch(() => {
        if (isCurrent()) setState({ report: null, error: true });
      });
    return () => {
      requestGeneration.current += 1;
      controller.abort();
    };
  }, [tradeId, positionId, days, attempt]);
  const { report, error } = state;
  const series = report?.series.filter((item) => item.points.length > 0) ?? [];
  const visibleSeries = series.filter((item) => !hiddenSeriesIds.includes(item.id));
  // Visibility never requalifies executions or removes their currency panel.
  const currencies = [...new Set(series.map((item) => item.currency))];
  const pointCount = series.reduce((count, item) => count + item.points.length, 0);
  const visiblePointCount = visibleSeries.reduce((count, item) => count + item.points.length, 0);
  return (
    <section
      aria-label="Positionskursverlauf"
      className="min-w-0 space-y-4 break-words rounded-xl border border-slate-700 bg-slate-950/40 p-3 sm:p-4"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="font-semibold text-white">Historischer Positionskurs</h3>
        <label className="flex min-w-0 max-w-full flex-wrap items-center gap-2 text-xs">
          Zeitraum
          <select
            className="min-w-0 max-w-full rounded border border-slate-600 bg-slate-950 p-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400"
            value={days}
            onChange={(event) => {
              setState({ report: null, error: false });
              setEvidenceSelection(null);
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
            className="rounded border border-slate-600 px-3 py-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400"
            onClick={() => {
              setState({ report: null, error: false });
              setEvidenceSelection(null);
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
            {pointCount === 1 ? 'gelieferter Marktkurspunkt' : 'gelieferte Marktkurspunkte'}.
            <span className="block">
              Angefragter Zeitraum:{' '}
              {report.window_start ? historyTime(report.window_start) : 'Alle gespeicherten Kurse'}
              {' bis '}
              {historyTime(report.window_end)}.
            </span>
          </p>
          <p className="text-xs text-slate-300">
            Eine vollständige Handelszeitabdeckung ist nicht belegt. Kauf- und Verkaufsbuchungen
            zählen nicht als Marktkurspunkte. Gespeicherte Qualität beschreibt den Erfassungsstand,
            keine heutige Handelbarkeit.
          </p>
          {report.truncated && (
            <p className="rounded border border-amber-800 p-3 text-amber-200">
              Begrenzter Ausschnitt: {report.samples_considered} von {report.samples_available}{' '}
              gespeicherten Stichproben geprüft (Grenze {report.sample_limit}). Ältere Belege können
              fehlen. Dieser Ausschnitt belegt keine vollständige Historie.
            </p>
          )}
          {pointCount > 0 && (
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs text-slate-400">
                Zur Anzeige ausgewählt: {visiblePointCount} von {pointCount} gelieferten
                Marktkurspunkten. Originalbelege und Buchungen bleiben vollständig erreichbar.
              </p>
              <button
                type="button"
                className="rounded border border-slate-600 px-3 py-2 text-xs focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400"
                onClick={() => setHiddenSeriesIds([])}
              >
                Alle Kursquellen anzeigen
              </button>
            </div>
          )}
          {pointCount > 0 && visibleSeries.length === 0 && (
            <p role="status" className="rounded border border-slate-700 p-4 text-slate-300">
              Alle Kursquellen sind für das Diagramm ausgeblendet. Das ist Ihre Darstellungswahl;
              die gespeicherten Kursbelege und Kauf-/Verkaufsereignisse sind weiterhin erreichbar.
              Mit „Alle Kursquellen anzeigen“ stellen Sie die Ansicht wieder her.
            </p>
          )}
          {pointCount === 0 ? (
            <p className="rounded border border-slate-700 p-4 text-slate-300">
              Keine zeitlich und fachlich zuordenbaren Kursdaten vorhanden.
            </p>
          ) : (
            <Suspense fallback={<p>Diagramm wird geladen …</p>}>
              {currencies.map((currency) => (
                <PositionPricePlot
                  key={currency}
                  currency={currency}
                  series={series.filter((item) => item.currency === currency)}
                  events={report.events}
                  hiddenSeriesIds={hiddenSeriesIds}
                  onToggleSeries={(seriesId) =>
                    setHiddenSeriesIds((previous) =>
                      previous.includes(seriesId)
                        ? previous.filter((id) => id !== seriesId)
                        : [...previous, seriesId],
                    )
                  }
                  onInspectEvidence={(target) =>
                    setEvidenceSelection((previous) => ({
                      target,
                      requestId: (previous?.requestId ?? 0) + 1,
                    }))
                  }
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
          <PositionPriceHistoryEvidence
            key={`${days}:${attempt}`}
            report={report}
            selection={evidenceSelection}
          />
          <details className="min-w-0 rounded border border-slate-700 p-3 text-xs">
            <summary className="cursor-pointer font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400">
              Erfassung und Lesegrenzen
            </summary>
            <p className="mt-3 text-slate-300">
              {!report.truncated && (
                <>
                  {report.samples_considered} von {report.samples_available} gespeicherten
                  Stichproben geprüft (Grenze {report.sample_limit}).{' '}
                </>
              )}
              Zuerst werden die neuesten Stichproben nach Erfassungsreihenfolge geprüft, danach das
              Originalzeitfenster. Vorhandene letzte erfolgreiche Kurse kommen gesondert hinzu.
              Stichproben, Marktkurspunkte und Ausführungen haben unterschiedliche Zählgrundlagen.
            </p>
            <p className="mt-2 text-slate-400">
              Erste gespeicherte Stichprobe: {historyTime(report.collection_started_at)}. Das ist
              kein Beginn vollständiger Kursversorgung. Wiederholte gespeicherte Kurse ergeben keine
              zusätzlichen Originalkurszeiten. Ein letzter gespeicherter Kurs kann der einzige
              belegte Punkt sein.
            </p>
            <p className="mt-2 break-all text-slate-400">
              Erfassungsverfahren: {report.sampling_policy}
            </p>
          </details>
        </>
      )}
    </section>
  );
}
