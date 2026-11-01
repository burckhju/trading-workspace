import { useEffect, useRef, useState } from 'react';
import type {
  PositionPriceEvent,
  PositionPricePoint,
  PositionPriceSeries,
} from '../positionPriceHistory';
import {
  historyPrice,
  historyProvider,
  historyTime,
  priceKindLabel,
  type PriceHistoryEvidenceTarget,
} from '../services/priceHistoryPresentation';

export interface PriceHistoryPlotDatum {
  time: number;
  value: number;
  target: PriceHistoryEvidenceTarget;
  number: number;
  sourceNumber?: number;
  point?: PositionPricePoint;
  series?: PositionPriceSeries;
  event?: PositionPriceEvent;
}

export interface PriceHistoryPlotSelection {
  time: number;
  value: number;
  sequence: number;
}

const controlClass =
  'rounded border border-slate-600 px-3 py-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300 disabled:opacity-40';
const pageSize = 20;

export function PositionPricePointAccess({
  currency,
  displayed,
  original,
  selection,
  hiddenSeriesIds,
  onClearSelection,
  onInspectEvidence,
}: {
  currency: string;
  displayed: PriceHistoryPlotDatum[];
  original: PriceHistoryPlotDatum[];
  selection: PriceHistoryPlotSelection | null;
  hiddenSeriesIds: readonly string[];
  onClearSelection: () => void;
  onInspectEvidence: (target: PriceHistoryEvidenceTarget) => void;
}) {
  const sequence = selection?.sequence ?? null;
  const [pagination, setPagination] = useState({ sequence, page: 0 });
  const page = pagination.sequence === sequence ? pagination.page : 0;
  const details = useRef<HTMLDetailsElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const inspected = useRef(false);
  const rows = [
    ...(selection
      ? original.filter((datum) => datum.time === selection.time && datum.value === selection.value)
      : displayed),
  ].sort((a, b) => a.time - b.time);
  const pages = Math.max(1, Math.ceil(rows.length / pageSize));
  const currentPage = Math.min(page, pages - 1);
  useEffect(() => {
    if ((selection || inspected.current) && details.current) {
      details.current.open = true;
      heading.current?.focus();
    }
    if (selection) inspected.current = true;
  }, [selection]);
  return (
    <details ref={details} className="min-w-0 space-y-3 rounded border border-slate-700 p-3">
      <summary className="cursor-pointer rounded font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-300">
        Punkte und Buchungen auswählen ({currency})
      </summary>
      <h5
        ref={heading}
        tabIndex={-1}
        className="rounded font-semibold focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-sky-300"
      >
        {selection ? 'Belege an diesem Diagrammpunkt' : 'Angezeigte Punkte und Buchungen'}:{' '}
        {rows.length}
      </h5>
      <p className="text-xs text-slate-300">
        {selection
          ? 'Alle gelieferten Einzelbelege mit denselben Diagrammkoordinaten, einschließlich ausgeblendeter Quellen. Originalwerte und Zeiten bleiben getrennt.'
          : 'Jeder angezeigte Punkt ist auch ohne Hover erreichbar. Die Auswahl öffnet seinen Originalbeleg; überlagerte Punkte bleiben einzeln auswählbar.'}
      </p>
      {selection && (
        <button type="button" className={controlClass} onClick={onClearSelection}>
          Alle angezeigten Punkte auswählen
        </button>
      )}
      {rows.length === 0 ? (
        <p>Derzeit keine angezeigten Punkte oder Buchungsmarker in {currency}.</p>
      ) : (
        <ol aria-label={`Einzelbelege ${currency}`} className="space-y-2">
          {rows.slice(currentPage * pageSize, (currentPage + 1) * pageSize).map((datum) => (
            <li key={JSON.stringify(datum.target)}>
              <button
                type="button"
                className={`${controlClass} w-full min-w-0 break-words text-left text-xs`}
                onClick={() => onInspectEvidence(datum.target)}
              >
                {datum.point && datum.series ? (
                  <>
                    <span className="block font-semibold">
                      Quelle {datum.sourceNumber}, Kurspunkt {datum.number}:{' '}
                      {historyProvider(datum.series.provider)}
                    </span>
                    <span className="block">
                      {priceKindLabel[datum.series.price_kind]} · {historyPrice(datum.point.price)}{' '}
                      {datum.series.currency}
                    </span>
                    <span className="block">
                      Originalkurszeit:{' '}
                      <time dateTime={datum.point.observed_at}>
                        {historyTime(datum.point.observed_at)}
                      </time>
                    </span>
                    <span className="block break-all text-slate-300">
                      {datum.point.observed_at}
                    </span>
                    {hiddenSeriesIds.includes(datum.series.id) && (
                      <span className="block">Quelle im Diagramm ausgeblendet</span>
                    )}
                  </>
                ) : datum.event ? (
                  <>
                    <span className="block font-semibold">
                      {datum.event.side === 'BUY' ? 'Kauf' : 'Verkauf'}, Buchung {datum.number} ·{' '}
                      {datum.event.quantity} Stück
                    </span>
                    <span className="block">
                      {historyPrice(datum.event.price)} {datum.event.currency} · Buchungspreis
                    </span>
                    <span className="block">
                      Ausführung:{' '}
                      <time dateTime={datum.event.occurred_at ?? undefined}>
                        {historyTime(datum.event.occurred_at)}
                      </time>
                    </span>
                    <span className="block break-all text-slate-300">
                      {datum.event.occurred_at}
                    </span>
                    <span className="block">Währungsherkunft: {datum.event.currency_source}</span>
                  </>
                ) : null}
                <span className="mt-1 block underline">Originalbeleg anzeigen</span>
              </button>
            </li>
          ))}
        </ol>
      )}
      {pages > 1 && (
        <nav
          aria-label={`Einzelbelege ${currency} blättern`}
          className="flex flex-wrap items-center gap-3 text-xs"
        >
          <button
            type="button"
            className={controlClass}
            disabled={currentPage === 0}
            onClick={() => setPagination({ sequence, page: currentPage - 1 })}
          >
            Vorige Einzelbelege
          </button>
          <span>
            Auswahlseite {currentPage + 1} / {pages}
          </span>
          <button
            type="button"
            className={controlClass}
            disabled={currentPage + 1 >= pages}
            onClick={() => setPagination({ sequence, page: currentPage + 1 })}
          >
            Weitere Einzelbelege
          </button>
        </nav>
      )}
    </details>
  );
}
