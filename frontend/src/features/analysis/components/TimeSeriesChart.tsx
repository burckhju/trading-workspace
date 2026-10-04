import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { ChartComparison, ChartPoint, ChartSeries } from '../types/charts';
import { chartDate, chartMessage, chartNumber } from './chartLabels';

type Mode = 'value' | 'normalized' | 'change_percent';
type PlotRow = {
  date: string;
  day: number;
  values: (number | null)[];
  points: (ChartPoint | null)[];
};
const colors = ['#38bdf8', '#fbbf24', '#c084fc', '#34d399'];
const dashes = ['', '8 4', '3 3', '10 3 2 3'];

// Only plotting coordinates are converted to binary floats. Alignment, prices,
// normalization and percentages are provided by the backend unchanged.
function plotRows(series: ChartSeries[], mode: Mode): PlotRow[] {
  const dates = new Set(series.flatMap((item) => item.points.map((point) => point.trading_date)));
  for (const item of series) {
    item.points.forEach((point) => {
      if (point.gap_before) {
        const previousCalendarDay = new Date(`${point.trading_date}T00:00:00Z`);
        previousCalendarDay.setUTCDate(previousCalendarDay.getUTCDate() - 1);
        dates.add(previousCalendarDay.toISOString().slice(0, 10));
      }
    });
  }
  const maps = series.map(
    (item) => new Map(item.points.map((point) => [point.trading_date, point])),
  );
  return [...dates].sort().map((date) => {
    const points = maps.map((map) => map.get(date) ?? null);
    return {
      date,
      day: Date.parse(`${date}T00:00:00Z`) / 86400000,
      points,
      values: points.map((point) => (point?.[mode] == null ? null : Number(point[mode]))),
    };
  });
}

export function TimeSeriesChart({ result }: { result: ChartComparison }) {
  const [mode, setMode] = useState<Mode>('value');
  const [single, setSingle] = useState(0);
  const [hidden, setHidden] = useState<string[]>([]);
  const [tableIndex, setTableIndex] = useState(0);
  const [page, setPage] = useState(0);
  const rows = useMemo(() => plotRows(result.series, mode), [result.series, mode]);
  const comparison = mode !== 'value';
  const displayAllowed = !comparison || result.comparison_status === 'READY';
  const visible = result.series
    .map((item, index) => ({ item, index }))
    .filter(({ item, index }) =>
      comparison ? !hidden.includes(item.identity.key) : index === single,
    );
  const selectedTable = result.series[tableIndex] ?? result.series[0];
  const tablePoints = selectedTable?.points.slice(page * 50, (page + 1) * 50) ?? [];
  const unit =
    mode === 'normalized'
      ? 'Basis 100'
      : mode === 'change_percent'
        ? '%'
        : !result.series[single]?.identity.listing_id
          ? 'Indexpunkte'
          : (result.series[single]?.currency ?? 'Währung unbekannt');
  return (
    <section
      aria-label="Kursdiagramm"
      className="space-y-4 rounded-xl border border-slate-700 bg-slate-900/40 p-4 sm:p-6"
    >
      <div className="flex flex-wrap items-end gap-4">
        <label className="text-sm">
          Darstellung
          <select
            value={mode}
            onChange={(event) => setMode(event.target.value as Mode)}
            className="ml-2 rounded border border-slate-600 bg-slate-950 p-2"
          >
            <option value="value">Absolute Einzelserie</option>
            <option value="normalized">Gemeinsamer Start = 100</option>
            <option value="change_percent">Veränderung in %</option>
          </select>
        </label>
        {!comparison && (
          <label className="text-sm">
            Einzelserie
            <select
              value={single}
              onChange={(event) => setSingle(Number(event.target.value))}
              className="ml-2 rounded border border-slate-600 bg-slate-950 p-2"
            >
              {result.series.map((item, index) => (
                <option value={index} key={item.identity.key}>
                  {item.identity.name}
                </option>
              ))}
            </select>
          </label>
        )}
        <span className="text-sm text-slate-300">Einheit: {unit} · EOD</span>
      </div>
      <p className="text-sm text-slate-300">
        Gewählt:{' '}
        {result.requested_start ? chartDate(result.requested_start) : 'Gespeicherte Gesamthistorie'}{' '}
        – {chartDate(result.requested_end)}. Gemeinsames Vergleichsfenster:{' '}
        {chartDate(result.common_start)} – {chartDate(result.common_end)}.
      </p>
      <p className="text-sm text-slate-400">
        Lokale Währungen, keine FX-Bereinigung. Handelstage ohne nachgewiesene Kursuhrzeit. Keine
        Intraday-Daten.
      </p>
      {result.issues.map((issue) => (
        <p className="text-sm text-amber-200" key={issue}>
          {chartMessage(issue)}
        </p>
      ))}
      {result.comparison_status !== 'READY' && (
        <p role="status" className="rounded border border-amber-800 p-3 text-sm text-amber-100">
          {chartMessage(result.comparison_status)}
        </p>
      )}
      {comparison && (
        <fieldset className="flex flex-wrap gap-4">
          <legend className="mb-2 text-sm">Legende – Serien ein-/ausblenden</legend>
          {result.series.map((item, index) => (
            <label key={item.identity.key} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={!hidden.includes(item.identity.key)}
                onChange={() =>
                  setHidden((current) =>
                    current.includes(item.identity.key)
                      ? current.filter((key) => key !== item.identity.key)
                      : [...current, item.identity.key],
                  )
                }
              />
              <span style={{ color: colors[index] }}>
                {index + 1}. {item.identity.name}
              </span>
            </label>
          ))}
        </fieldset>
      )}
      {displayAllowed && rows.length > 0 && visible.length > 0 ? (
        <div className="h-80 w-full" data-testid="time-series-chart">
          <ResponsiveContainer width="100%" height="100%" minWidth={0}>
            <LineChart
              data={rows}
              accessibilityLayer
              margin={{ top: 12, right: 20, bottom: 12, left: 12 }}
              title="EOD-Kursverlauf"
              desc="Pfeiltasten bewegen den Datenzeiger. Alle Werte stehen auch in der Datentabelle."
            >
              <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
              <XAxis
                dataKey="day"
                type="number"
                allowDecimals={false}
                domain={['dataMin', 'dataMax']}
                tickFormatter={(day) =>
                  chartDate(new Date(Number(day) * 86400000).toISOString().slice(0, 10))
                }
                minTickGap={50}
                stroke="#cbd5e1"
              />
              <YAxis
                domain={['auto', 'auto']}
                tickFormatter={(value) => chartNumber(Number(value))}
                width={76}
                stroke="#cbd5e1"
              />
              <Tooltip
                content={({ label, active }) => {
                  if (!active || typeof label !== 'number') return null;
                  const row = rows.find((item) => item.day === label);
                  return (
                    <div className="max-w-xs rounded border border-slate-500 bg-slate-950 p-3 text-xs text-slate-100">
                      <p className="font-semibold">{row ? chartDate(row.date) : '—'} · EOD</p>
                      {visible.map(({ item, index }) => (
                        <div className="mt-2" key={item.identity.key}>
                          <p>
                            {item.identity.name}: {chartNumber(row?.values[index] ?? null)} {unit}
                          </p>
                          <p>
                            Quelle: {row?.points[index]?.provider ?? 'Keine Beobachtung'}{' '}
                            {row?.points[index]?.provider_symbol ?? ''}
                          </p>
                          <p>
                            Preis: {chartNumber(row?.points[index]?.value ?? null)}{' '}
                            {item.identity.listing_id ? item.currency : 'Indexpunkte'}
                          </p>
                        </div>
                      ))}
                    </div>
                  );
                }}
              />
              {visible.map(({ item, index }) => (
                <Line
                  key={item.identity.key}
                  name={item.identity.name}
                  dataKey={`values.${index}`}
                  type="linear"
                  stroke={colors[index]}
                  strokeDasharray={dashes[index]}
                  strokeWidth={2}
                  dot={rows.length < 3}
                  activeDot={{ r: 4 }}
                  connectNulls={false}
                  isAnimationActive={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p className="py-8 text-center text-slate-400">
          Für diese Auswahl ist kein Verlauf darstellbar.
        </p>
      )}
      <div className="grid gap-3 md:grid-cols-2">
        {result.series.map((item) => (
          <article key={item.identity.key} className="rounded border border-slate-700 p-3 text-sm">
            <p className="font-semibold">
              {item.identity.name} {item.identity.instrument_type === 'ETF' ? '· ETF' : ''}
            </p>
            <p className="text-slate-300">
              {item.identity.isin ?? item.identity.reference_code} ·{' '}
              {item.identity.mic ?? 'Indexreferenz'} · {item.currency ?? 'Währung unbekannt'}
            </p>
            <p>
              {chartMessage(item.return_basis)} · {result.price_field}
            </p>
            <p>
              {chartDate(item.first_date)} – {chartDate(item.last_date)} · {item.observation_count}{' '}
              Beobachtungen
            </p>
            {item.missing_comparison_dates.length > 0 && (
              <p className="text-amber-200">
                {item.missing_comparison_dates.length} Vergleichstage ohne Beobachtung.
              </p>
            )}
            {item.issues.map((issue) => (
              <p className="mt-1 text-amber-200" key={issue}>
                {chartMessage(issue)}
              </p>
            ))}
            <Link className="mt-2 inline-block text-sky-300 underline" to={item.identity.setup_url}>
              Datenbasis / Historie einrichten
            </Link>
          </article>
        ))}
      </div>
      <details className="rounded border border-slate-700 p-3">
        <summary className="cursor-pointer font-semibold">
          Datentabelle und Quellen – zugängliche Alternative
        </summary>
        <label className="my-3 block text-sm">
          Tabellenserie
          <select
            value={tableIndex}
            onChange={(event) => {
              setTableIndex(Number(event.target.value));
              setPage(0);
            }}
            className="ml-2 rounded bg-slate-950 p-2"
          >
            {result.series.map((item, index) => (
              <option key={item.identity.key} value={index}>
                {item.identity.name}
              </option>
            ))}
          </select>
        </label>
        <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="EOD-Datentabelle">
          <table className="w-full text-left text-xs">
            <caption className="mb-2 text-left">
              {selectedTable?.identity.name} · {result.price_field} ·{' '}
              {selectedTable?.identity.listing_id ? selectedTable.currency : 'Indexpunkte'}
            </caption>
            <thead>
              <tr>
                {[
                  'Handelstag',
                  'Preis',
                  'Basis 100',
                  'Änderung %',
                  'Herkunft',
                  'Empfangen (UTC)',
                  'Quellenaktualisierung',
                  'Qualität / Hinweise',
                ].map((title) => (
                  <th scope="col" className="p-2" key={title}>
                    {title}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tablePoints.map((point) => (
                <tr key={point.trading_date} className="border-t border-slate-700">
                  <th scope="row" className="whitespace-nowrap p-2">
                    {chartDate(point.trading_date)}
                  </th>
                  <td className="p-2">{chartNumber(point.value)}</td>
                  <td className="p-2">{chartNumber(point.normalized)}</td>
                  <td className="p-2">{chartNumber(point.change_percent)}</td>
                  <td className="p-2">
                    {point.provider} {point.provider_symbol}
                  </td>
                  <td className="p-2">{point.received_at}</td>
                  <td className="p-2">{point.source_updated_at ?? 'Unbekannt'}</td>
                  <td className="p-2">
                    {point.quality} {point.warnings.map(chartMessage).join('; ')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-3 flex items-center gap-3 text-sm">
          <button
            className="rounded border p-2 disabled:opacity-40"
            disabled={page === 0}
            onClick={() => setPage(page - 1)}
          >
            Vorige Werte
          </button>
          <span>
            Seite {page + 1} / {Math.max(1, Math.ceil((selectedTable?.points.length ?? 0) / 50))}
          </span>
          <button
            className="rounded border p-2 disabled:opacity-40"
            disabled={(page + 1) * 50 >= (selectedTable?.points.length ?? 0)}
            onClick={() => setPage(page + 1)}
          >
            Weitere Werte
          </button>
        </div>
      </details>
      <p className="text-xs text-slate-400">
        {result.model_version} · volle EOD-Auflösung, keine Interpolation. Historische Ansichten
        verwenden heute gespeicherte Daten; sie sind kein damaliger Wissensstand.
      </p>
    </section>
  );
}
