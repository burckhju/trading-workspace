import { useRef, useState } from 'react';
import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { PositionPriceEvent, PositionPriceSeries } from '../positionPriceHistory';
import {
  historyPrice,
  historyProvider,
  historyTime,
  historyVenue,
  historyAxisTime,
  priceHistoryLabel,
  priceKindLabel,
  historySourceMode,
  type PriceHistoryEvidenceTarget,
} from '../services/priceHistoryPresentation';
import {
  PositionPricePointAccess,
  type PriceHistoryPlotDatum,
  type PriceHistoryPlotSelection,
} from './PositionPricePointAccess';

const colors = ['#38bdf8', '#fbbf24', '#c084fc', '#34d399', '#fb7185', '#e2e8f0'];
// Execution markers keep their own shapes even when many market series exist.
const shapes = ['circle', 'square', 'diamond', 'star'] as const;
const shapeNames = ['Kreis', 'Quadrat', 'Raute', 'Stern'];

function PlotTooltip({ datum }: { datum: PriceHistoryPlotDatum }) {
  const { point, series, event } = datum;
  return (
    <div className="max-w-xs break-words rounded border border-slate-500 bg-slate-950 p-3 text-xs text-slate-100">
      {point && series ? (
        <>
          <p className="font-semibold">
            {priceKindLabel[series.price_kind]}: {historyPrice(point.price)} {series.currency}
          </p>
          <p>
            Originalkurszeit:{' '}
            <time dateTime={point.observed_at}>{historyTime(point.observed_at)}</time>
          </p>
          <p>
            Quelle {datum.sourceNumber}: {historyProvider(series.provider)}
          </p>
          <p>{historyVenue(series)}</p>
          <p>{priceHistoryLabel(point.status)}</p>
          <p>{historySourceMode(series.source_mode)}</p>
        </>
      ) : event ? (
        <>
          <p className="font-semibold">
            {event.side === 'BUY' ? 'Kauf' : 'Verkauf'} · {historyPrice(event.price)}{' '}
            {event.currency}
          </p>
          <p>Ausführung: {historyTime(event.occurred_at)}</p>
          <p>{event.quantity} Stück · erfasste Ausführung, kein Marktkurs</p>
        </>
      ) : null}
    </div>
  );
}

export function PositionPricePlot({
  currency,
  series,
  events,
  hiddenSeriesIds,
  onToggleSeries,
  onInspectEvidence,
}: {
  currency: string;
  series: PositionPriceSeries[];
  events: PositionPriceEvent[];
  hiddenSeriesIds: readonly string[];
  onToggleSeries: (seriesId: string) => void;
  onInspectEvidence: (target: PriceHistoryEvidenceTarget) => void;
}) {
  const [selection, setSelection] = useState<PriceHistoryPlotSelection | null>(null);
  const selectionSequence = useRef(0);
  const marketData = series.flatMap((item, sourceIndex) =>
    item.points.map(
      (point, pointIndex): PriceHistoryPlotDatum => ({
        time: Date.parse(point.observed_at),
        value: Number(point.price),
        target: { kind: 'point', seriesId: item.id, pointId: point.id },
        number: pointIndex + 1,
        sourceNumber: sourceIndex + 1,
        point,
        series: item,
      }),
    ),
  );
  // Marker eligibility stays with the server and never depends on source visibility.
  const eventData = events.flatMap((event, index): PriceHistoryPlotDatum[] =>
    event.plottable && event.currency === currency && event.occurred_at
      ? [
          {
            time: Date.parse(event.occurred_at),
            value: Number(event.price),
            target: { kind: 'event', eventId: event.id },
            number: index + 1,
            event,
          },
        ]
      : [],
  );
  const finiteCoordinates = (datum: PriceHistoryPlotDatum) =>
    Number.isFinite(datum.time) && Number.isFinite(datum.value);
  const selectedMarket = marketData.filter((datum) => !hiddenSeriesIds.includes(datum.series!.id));
  const visibleMarket = selectedMarket.filter(finiteCoordinates);
  const markers = eventData.filter(finiteCoordinates);
  const displayed = [...visibleMarket, ...markers];
  const original = [...marketData, ...eventData].filter(finiteCoordinates);
  const unavailableCoordinates = selectedMarket.length + eventData.length - displayed.length;
  const quoteTimes = marketData.map((datum) => datum.time).filter(Number.isFinite);
  const quoteStart = quoteTimes.reduce((earliest, time) => Math.min(earliest, time), Infinity);
  const quoteEnd = quoteTimes.reduce((latest, time) => Math.max(latest, time), -Infinity);
  const [axisStart, axisEnd] = displayed.reduce(
    ([start, end], datum) => [Math.min(start, datum.time), Math.max(end, datum.time)],
    [Infinity, -Infinity],
  );
  const selectCoordinates = (datum: PriceHistoryPlotDatum) => {
    selectionSequence.current += 1;
    setSelection({
      time: datum.time,
      value: datum.value,
      sequence: selectionSequence.current,
    });
  };
  const sourceLegend = (
    <fieldset className="min-w-0 space-y-2 rounded border border-slate-700 p-3">
      <legend className="px-1 font-semibold">Kursquellen {currency} auswählen</legend>
      <p className="text-xs text-slate-300">
        Nur Marktserien werden ein- oder ausgeblendet. Buchungen und Originalbelege bleiben
        erhalten. Quellnummern und Formen ergänzen die Farben; bei vielen Quellen wiederholen sich
        Symbole.
      </p>
      <ul
        className="grid min-w-0 gap-2 text-xs sm:grid-cols-2"
        aria-label={`Kursquellen ${currency}`}
      >
        {series.map((item, index) => (
          <li key={item.id} className="min-w-0 rounded border border-slate-700 p-2">
            <label className="flex min-w-0 cursor-pointer items-start gap-2">
              <input
                type="checkbox"
                checked={!hiddenSeriesIds.includes(item.id)}
                onChange={() => onToggleSeries(item.id)}
                className="mt-1 shrink-0 accent-sky-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
              />
              <span className="min-w-0 break-words">
                <span className="font-semibold" style={{ color: colors[index % colors.length] }}>
                  Quelle {index + 1}: {historyProvider(item.provider)} ·{' '}
                  {priceKindLabel[item.price_kind]} · {currency}
                </span>
                <span className="block">{historyVenue(item)}</span>
                <span className="block">{historySourceMode(item.source_mode)}</span>
                <span className="block">
                  {shapeNames[index % shapes.length]} ·{' '}
                  {hiddenSeriesIds.includes(item.id) ? 'Ausgeblendet' : 'Sichtbar'} ·{' '}
                  {item.points.length}{' '}
                  {item.points.length === 1 ? 'gelieferter Kurspunkt' : 'gelieferte Kurspunkte'}
                </span>
              </span>
            </label>
            <details className="mt-2 min-w-0 text-slate-300">
              <summary className="cursor-pointer rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-300">
                Quellenkennung {index + 1}
              </summary>
              <p className="break-all">Serie: {item.id}</p>
              <p className="break-all">Quellsegment: {item.identity_key}</p>
              <p className="break-all">
                Notierung: {item.warrant_listing_id} · ISIN {item.isin}
              </p>
              <p className="break-all">Quellenmodus: {item.source_mode ?? 'unbekannt'}</p>
            </details>
          </li>
        ))}
      </ul>
    </fieldset>
  );
  return (
    <section aria-label={`Kursbeobachtungen ${currency}`} className="min-w-0 space-y-3">
      <h4 className="font-semibold">Handelswährung: {currency}</h4>
      <p className="break-words text-xs text-slate-300">
        Preisarten: {[...new Set(series.map((item) => priceKindLabel[item.price_kind]))].join(', ')}
        {' · '}
        {currency} · {series.filter((item) => !hiddenSeriesIds.includes(item.id)).length} von{' '}
        {series.length} Kursquellen ausgewählt;{' '}
        {series.filter((item) => hiddenSeriesIds.includes(item.id)).length} ausgeblendet.
      </p>
      {series.length > 6 ? (
        <details className="min-w-0 space-y-3 rounded border border-slate-700 p-3">
          <summary className="cursor-pointer rounded break-words font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-300">
            Kursquellen {currency} ein-/ausblenden ({series.length})
          </summary>
          {sourceLegend}
        </details>
      ) : (
        sourceLegend
      )}
      {Number.isFinite(quoteStart) && Number.isFinite(quoteEnd) && (
        <p className="text-xs text-slate-400">
          Belegte Kurszeiten aller gelieferten Quellen:{' '}
          {historyTime(new Date(quoteStart).toISOString())}
          {quoteStart !== quoteEnd && ` bis ${historyTime(new Date(quoteEnd).toISOString())}`}.
        </p>
      )}
      {unavailableCoordinates > 0 && (
        <p className="text-xs text-amber-200">
          {unavailableCoordinates} ausgewählte Belege lassen sich nicht als endliche
          Diagrammkoordinaten darstellen; Originalbelege bleiben in der Kursdatentabelle und
          Ereignisliste erreichbar.
        </p>
      )}
      {displayed.length > 0 ? (
        <div className="h-72 w-full min-w-0" data-testid="position-price-chart">
          <ResponsiveContainer width="100%" height="100%" minWidth={0}>
            <ScatterChart
              accessibilityLayer
              margin={{ top: 12, right: 12, bottom: 12, left: 0 }}
              title={`Historische Kursbeobachtungen in ${currency}`}
              desc="Gespeicherte Einzelpunkte ohne Verbindungslinien. Originalbelege können unter Punkte und Buchungen auswählen ohne Hover geöffnet werden."
            >
              <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
              <XAxis
                dataKey="time"
                name="Originalkurszeit (UTC)"
                type="number"
                domain={['dataMin', 'dataMax']}
                tickFormatter={(value: number) => historyAxisTime(value, axisStart, axisEnd)}
                tick={{ fontSize: 11 }}
                tickCount={4}
                tickMargin={8}
                minTickGap={28}
                height={44}
                stroke="#cbd5e1"
              />
              <YAxis
                dataKey="value"
                name="Preis"
                type="number"
                domain={['auto', 'auto']}
                tickFormatter={(value: number) =>
                  value.toLocaleString('de-DE', { maximumFractionDigits: 4 })
                }
                width={64}
                tick={{ fontSize: 12 }}
                tickMargin={8}
                stroke="#cbd5e1"
              />
              <Tooltip
                cursor={{ strokeDasharray: '3 3' }}
                content={({ active, payload }) =>
                  active && payload?.[0]?.payload ? (
                    <PlotTooltip datum={payload[0].payload as PriceHistoryPlotDatum} />
                  ) : null
                }
              />
              {series.map(
                (item, index) =>
                  !hiddenSeriesIds.includes(item.id) && (
                    <Scatter
                      key={item.id}
                      name={`${item.provider} · ${priceKindLabel[item.price_kind]}`}
                      data={visibleMarket.filter((datum) => datum.series!.id === item.id)}
                      fill={colors[index % colors.length]}
                      shape={shapes[index % shapes.length]}
                      line={false}
                      isAnimationActive={false}
                      onClick={(entry) => selectCoordinates(entry.payload as PriceHistoryPlotDatum)}
                      cursor="pointer"
                    />
                  ),
              )}
              {(['BUY', 'SELL'] as const).map((side) => (
                <Scatter
                  key={side}
                  name={side === 'BUY' ? 'Kaufbuchung' : 'Verkaufsbuchung'}
                  data={markers.filter((datum) => datum.event!.side === side)}
                  fill={side === 'BUY' ? '#a3e635' : '#fb7185'}
                  shape={side === 'BUY' ? 'triangle' : 'cross'}
                  line={false}
                  isAnimationActive={false}
                  onClick={(entry) => selectCoordinates(entry.payload as PriceHistoryPlotDatum)}
                  cursor="pointer"
                />
              ))}
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p className="text-xs text-slate-300">
          Derzeit keine ausgewählten Diagrammpunkte in {currency}. Originalbelege bleiben
          erreichbar.
        </p>
      )}
      <p className="text-xs text-slate-400">
        Zeitachse: belegte Originalkurszeit in UTC. Handelswährungen bleiben getrennt; keine
        Umrechnung.
        {markers.length > 0 &&
          ' Dreieck grün: Kauf. Kreuz rosa: Verkauf. Buchungspreise sind keine Marktbeobachtungen.'}
      </p>
      <PositionPricePointAccess
        currency={currency}
        displayed={displayed}
        original={original}
        selection={selection}
        hiddenSeriesIds={hiddenSeriesIds}
        onClearSelection={() => setSelection(null)}
        onInspectEvidence={onInspectEvidence}
      />
    </section>
  );
}
