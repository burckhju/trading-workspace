import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type {
  PositionPriceEvent,
  PositionPricePoint,
  PositionPriceSeries,
} from '../positionPriceHistory';
import {
  historyPrice,
  historyTime,
  priceHistoryLabel,
  priceKindLabel,
} from '../services/priceHistoryPresentation';

const colors = ['#38bdf8', '#fbbf24', '#c084fc', '#34d399', '#fb7185', '#e2e8f0'];
const shapes = ['circle', 'square', 'diamond', 'triangle', 'cross', 'star'] as const;
type PlotDatum = {
  time: number;
  value: number;
  point?: PositionPricePoint;
  series?: PositionPriceSeries;
  event?: PositionPriceEvent;
};

function PlotTooltip({ datum }: { datum: PlotDatum }) {
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
          <p>Quelle: {series.provider}</p>
          <p>{priceHistoryLabel(point.status)}</p>
          <p>{series.source_mode ?? 'Quellenmodus unbekannt'}</p>
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
}: {
  currency: string;
  series: PositionPriceSeries[];
  events: PositionPriceEvent[];
}) {
  const markers = events.filter(
    (event) => event.plottable && event.currency === currency && event.occurred_at,
  );
  return (
    <section aria-label={`Kursbeobachtungen ${currency}`} className="min-w-0 space-y-3">
      <h4 className="font-semibold">Handelswährung: {currency}</h4>
      <ul className="space-y-1 text-xs" aria-label={`Kursquellen ${currency}`}>
        {series.map((item, index) => (
          <li key={item.id}>
            <span style={{ color: colors[index % colors.length] }}>
              {index + 1}. {item.provider} · {priceKindLabel[item.price_kind]}
            </span>{' '}
            · {item.points.length} {item.points.length === 1 ? 'Kurspunkt' : 'Kurspunkte'} ·{' '}
            {item.source_mode ?? 'Quellenmodus unbekannt'}
          </li>
        ))}
      </ul>
      <div className="h-72 w-full min-w-0" data-testid="position-price-chart">
        <ResponsiveContainer width="100%" height="100%" minWidth={0}>
          <ScatterChart
            accessibilityLayer
            margin={{ top: 12, right: 12, bottom: 12, left: 0 }}
            title={`Historische Kursbeobachtungen in ${currency}`}
            desc="Gespeicherte Einzelpunkte ohne Verbindungslinien. Alle Belege stehen in der Kursdatentabelle."
          >
            <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
            <XAxis
              dataKey="time"
              name="Originalkurszeit (UTC)"
              type="number"
              domain={['dataMin', 'dataMax']}
              tickFormatter={(value: number) =>
                new Date(value).toLocaleDateString('de-DE', {
                  timeZone: 'UTC',
                  day: '2-digit',
                  month: '2-digit',
                })
              }
              minTickGap={40}
              stroke="#cbd5e1"
            />
            <YAxis
              dataKey="value"
              name="Preis"
              unit={` ${currency}`}
              type="number"
              domain={['auto', 'auto']}
              tickFormatter={(value: number) =>
                value.toLocaleString('de-DE', { maximumFractionDigits: 4 })
              }
              width={64}
              stroke="#cbd5e1"
            />
            <Tooltip
              cursor={{ strokeDasharray: '3 3' }}
              content={({ active, payload }) =>
                active && payload?.[0]?.payload ? (
                  <PlotTooltip datum={payload[0].payload as PlotDatum} />
                ) : null
              }
            />
            {series.map((item, index) => (
              <Scatter
                key={item.id}
                name={`${item.provider} · ${priceKindLabel[item.price_kind]}`}
                data={item.points.map(
                  (point): PlotDatum => ({
                    time: Date.parse(point.observed_at),
                    value: Number(point.price),
                    point,
                    series: item,
                  }),
                )}
                fill={colors[index % colors.length]}
                shape={shapes[index % shapes.length]}
                line={false}
                isAnimationActive={false}
              />
            ))}
            {(['BUY', 'SELL'] as const).map((side) => (
              <Scatter
                key={side}
                name={side === 'BUY' ? 'Kaufbuchung' : 'Verkaufsbuchung'}
                data={markers
                  .filter((event) => event.side === side)
                  .map(
                    (event): PlotDatum => ({
                      time: Date.parse(event.occurred_at!),
                      value: Number(event.price),
                      event,
                    }),
                  )}
                fill={side === 'BUY' ? '#a3e635' : '#fb7185'}
                shape={side === 'BUY' ? 'triangle' : 'cross'}
                line={false}
                isAnimationActive={false}
              />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <p className="text-xs text-slate-400">
        Zeitachse: belegte Originalkurszeit in UTC. Handelswährungen bleiben getrennt; keine
        Umrechnung.
        {markers.length > 0 &&
          ' Dreieck grün: Kauf. Kreuz rosa: Verkauf. Buchungspreise sind keine Marktbeobachtungen.'}
      </p>
    </section>
  );
}
