import { useMemo, useState } from 'react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { chartPlotRows } from '../services/chartPlotRows';
import { withChartSetupContext } from '../../administration/services/referenceDataContext';
import type { ChartWatchlistItem } from '../types/watchlist';
import { chartDate, chartMessage, chartNumber } from './chartLabels';
import type { WatchlistSeriesState } from './useWatchlistSeries';
import { watchlistRefreshStatus, watchlistSetupReason } from './watchlistLabels';

const setupLabels = {
  PENDING: 'Einrichtung ausstehend',
  CONFIGURED: 'Datenbasis eingerichtet',
  BLOCKED: 'Einrichtung blockiert',
};

function publicSource(value: string): string | undefined {
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && !url.username && !url.password ? value : undefined;
  } catch {
    return undefined;
  }
}

export function WatchlistChartCard({
  item,
  state,
  selected,
  comparisonFull,
  onSelect,
  onOpen,
  onRetry,
  chartParams,
}: {
  item: ChartWatchlistItem;
  state: WatchlistSeriesState;
  selected: boolean;
  comparisonFull: boolean;
  onSelect: () => void;
  onOpen: () => void;
  onRetry: () => void;
  chartParams?: URLSearchParams;
}) {
  const series = state.result?.series[0];
  const points = series?.points;
  const rows = useMemo(() => chartPlotRows(series ? [series] : [], 'value'), [series]);
  const [tableOpen, setTableOpen] = useState(false);
  const [page, setPage] = useState(0);
  const last = points?.at(-1);
  const unit = item.kind === 'INDEX' ? 'Indexpunkte' : (series?.currency ?? 'Währung unbekannt');
  const source = publicSource(item.source_url);
  const tablePage = Math.min(page, Math.max(0, Math.ceil((points?.length ?? 0) / 50) - 1));
  const titleId = 'watchlist-title-' + item.code;
  const button = 'rounded border border-slate-600 px-3 py-2 text-sm disabled:opacity-50';
  const returnParams = new URLSearchParams(chartParams);
  returnParams.set('view', 'overview');

  return (
    <article
      aria-labelledby={titleId}
      className="min-w-0 space-y-3 rounded-xl border border-slate-700 bg-slate-900/40 p-4"
    >
      <header className="min-w-0 space-y-1">
        <p className="text-xs text-slate-400">
          {item.group} · {item.kind === 'INDEX' ? 'Direkter Index' : 'ETF'}
        </p>
        <h3 id={titleId} className="break-words text-lg font-semibold">
          {item.name}
        </h3>
        <p className="break-words text-xs text-slate-300">
          {item.ticker ?? item.code} · {item.isin ?? 'Indexreferenz'} ·{' '}
          {item.mic ?? 'Kein Wertpapierlisting'}
        </p>
      </header>

      {series ? (
        <>
          <div className="flex flex-wrap items-baseline gap-x-2">
            <strong className="text-xl tabular-nums">{chartNumber(last?.value ?? null)}</strong>
            <span className="text-sm">{unit}</span>
          </div>
          <p className="text-xs text-slate-300">
            Letzte Beobachtung im Zeitraum: {chartDate(last?.trading_date ?? null)} ·{' '}
            {state.result!.price_field} · EOD
          </p>
          <p className="break-words text-xs text-slate-300">
            Quelle der letzten Beobachtung: {last?.provider ?? 'Nicht belegt'}{' '}
            {last?.provider_symbol ?? ''}
          </p>
          {rows.some((row) => row.values[0] !== null) ? (
            <figure className="min-w-0">
              <div className="h-44 w-full" data-testid={'watchlist-chart-' + item.code}>
                <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                  <LineChart
                    data={rows}
                    accessibilityLayer
                    margin={{ top: 8, right: 8, bottom: 4, left: 0 }}
                    title={item.name + ' · gespeicherte EOD-Kurse'}
                    desc="Eigene Preisachse. Handelstage ohne Kursuhrzeit. Alle Werte und Quellen stehen in der aufklappbaren Tabelle."
                  >
                    <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
                    <XAxis
                      dataKey="day"
                      type="number"
                      allowDecimals={false}
                      domain={['dataMin', 'dataMax']}
                      minTickGap={45}
                      tick={{ fontSize: 11 }}
                      tickFormatter={(day) =>
                        chartDate(new Date(Number(day) * 86400000).toISOString().slice(0, 10))
                      }
                      stroke="#cbd5e1"
                    />
                    <YAxis
                      domain={['auto', 'auto']}
                      width={65}
                      tick={{ fontSize: 11 }}
                      tickFormatter={(value) => chartNumber(Number(value))}
                      stroke="#cbd5e1"
                    />
                    <Tooltip
                      content={({ label, active }) => {
                        if (!active || typeof label !== 'number') return null;
                        const row = rows.find((value) => value.day === label);
                        const point = row?.points[0];
                        return (
                          <div className="max-w-56 break-words rounded border border-slate-500 bg-slate-950 p-2 text-xs">
                            <p>{chartDate(row?.date ?? null)} · EOD</p>
                            <p>
                              {chartNumber(point?.value ?? null)} {unit}
                            </p>
                            <p>
                              {point?.provider ?? 'Keine Beobachtung'}{' '}
                              {point?.provider_symbol ?? ''}
                            </p>
                          </div>
                        );
                      }}
                    />
                    <Line
                      dataKey="values.0"
                      type="linear"
                      stroke="#38bdf8"
                      strokeWidth={2}
                      dot={rows.length < 3}
                      activeDot={{ r: 4 }}
                      connectNulls={false}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <figcaption className="text-xs text-slate-400">
                Eigene Skala · {unit}. Linienlücken bleiben erhalten.
              </figcaption>
            </figure>
          ) : (
            <p className="rounded border border-slate-700 p-3 text-sm">
              Keine darstellbaren Werte für dieses Preisfeld im gewählten Zeitraum.
            </p>
          )}
          <p className="text-xs text-slate-300">
            {chartDate(series.first_date)} – {chartDate(series.last_date)} ·{' '}
            {series.observation_count} Beobachtungen
          </p>
          <p className="text-xs">
            {chartMessage(series.return_basis)} · {state.result!.price_field}
          </p>
          {series.issues.map((issue) => (
            <p key={issue} className="break-words text-xs text-amber-200">
              {chartMessage(issue)}
            </p>
          ))}
        </>
      ) : state.loading ? (
        <p className="rounded border border-slate-700 p-3 text-sm">
          Gespeicherte EOD-Kurse werden gelesen …
        </p>
      ) : state.error ? (
        <div className="space-y-2 rounded border border-amber-800 p-3 text-sm">
          <p className="break-words">Kurse nicht lesbar: {state.error}</p>
          <button type="button" className={button} onClick={onRetry}>
            Kurse erneut lesen
          </button>
        </div>
      ) : (
        <p className="rounded border border-slate-700 p-3 text-sm">
          Noch keine eingerichtete Kursreihe. Gespeicherte Werte werden nach erfolgreicher
          Einrichtung angezeigt.
        </p>
      )}

      <div className="space-y-1 text-xs">
        <p className={item.setup_status === 'BLOCKED' ? 'text-amber-200' : 'text-slate-300'}>
          {setupLabels[item.setup_status]}
        </p>
        {item.setup_reason && (
          <p className="break-words text-amber-200">{watchlistSetupReason(item.setup_reason)}</p>
        )}
        <p>Historie insgesamt bis: {chartDate(item.history.last_date)}</p>
        <p className="break-words">
          Letzter gespeicherter Abruf (UTC): {item.history.last_received_at ?? 'Unbekannt'}
        </p>
      </div>

      <div
        role="group"
        aria-label="EOD-Abrufstatus"
        className="space-y-1 rounded border border-slate-700 p-2 text-xs"
      >
        {item.refresh ? (
          <>
            <p>
              {watchlistRefreshStatus(item.refresh.status)} · {item.refresh.status}
            </p>
            {item.refresh.reason && (
              <p className="break-words">Abrufgrund: {item.refresh.reason}</p>
            )}
            <p className="break-words">
              Abruf geprüft (UTC): {item.refresh.checked_at ?? 'Nicht belegt'}
            </p>
            <p className="break-words">
              Letzter erfolgreicher Abruf im Prozess (UTC):{' '}
              {item.refresh.last_success_at ?? 'Nicht belegt'}
            </p>
            <p className="break-words">
              Nächster geplanter Abruf (UTC): {item.refresh.next_run_at ?? 'Nicht belegt'}
            </p>
            <p>Prozesslokaler Beleg; nach einem Backendneustart nicht fortgeführt.</p>
          </>
        ) : (
          <p>
            Kein Abrufbeleg im aktuellen Backendprozess. Dies trifft keine Aussage über den
            gespeicherten Verlauf.
          </p>
        )}
      </div>

      <div className="flex flex-wrap gap-3 text-sm">
        {source && (
          <a className="text-sky-300 underline" href={source} target="_blank" rel="noreferrer">
            {item.kind === 'INDEX' ? 'Indexquelle' : 'Fondsprofil / Quelle'}
          </a>
        )}
        <button
          type="button"
          className="text-sky-300 underline disabled:opacity-50"
          disabled={!item.target_key}
          onClick={onOpen}
        >
          Detaildiagramm öffnen
        </button>
        {item.setup_status === 'BLOCKED' && (
          <a
            className="text-sky-300 underline"
            href={withChartSetupContext(series?.identity.setup_url ?? '/chart-setup', returnParams)}
          >
            Datenbasis prüfen
          </a>
        )}
      </div>
      <label className="flex items-start gap-2 text-sm">
        <input
          type="checkbox"
          className="mt-1"
          checked={selected}
          disabled={!item.target_key || (!selected && comparisonFull)}
          onChange={onSelect}
        />
        Für Vergleich vormerken
      </label>

      <details
        className="min-w-0 rounded border border-slate-700 p-3"
        onToggle={(event) => setTableOpen(event.currentTarget.open)}
      >
        <summary className="cursor-pointer rounded text-sm font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-300">
          Werte, Quellen und Einrichtung
        </summary>
        {tableOpen && (
          <div className="mt-3 min-w-0 space-y-3 text-xs">
            <dl className="space-y-1 break-words">
              {item.setup_reason && (
                <div>
                  <dt className="inline font-semibold">Backendgrund: </dt>
                  <dd className="inline">{item.setup_reason}</dd>
                </div>
              )}
              <div>
                <dt className="inline font-semibold">Katalogcode: </dt>
                <dd className="inline">{item.code}</dd>
              </div>
              <div>
                <dt className="inline font-semibold">Katalogwährung: </dt>
                <dd className="inline">{item.currency ?? 'Nicht belegt'}</dd>
              </div>
              <div>
                <dt className="inline font-semibold">Mapping: </dt>
                <dd className="inline">
                  {item.mapping
                    ? item.mapping.provider_symbol +
                      ' / ' +
                      item.mapping.provider_exchange_code +
                      ' · ' +
                      item.mapping.status +
                      ' · Revision ' +
                      item.mapping.version
                    : 'Nicht vorhanden'}
                </dd>
              </div>
              <div>
                <dt className="inline font-semibold">Letzter Einrichtungsversuch (UTC): </dt>
                <dd className="inline">{item.last_attempt_at ?? 'Nicht belegt'}</dd>
              </div>
              <div>
                <dt className="inline font-semibold">Einrichtung abgeschlossen (UTC): </dt>
                <dd className="inline">{item.setup_completed_at ?? 'Nicht belegt'}</dd>
              </div>
            </dl>
            <p>
              Aktuelles Mapping und historische Punktquellen sind getrennte Belege. Abrufzeit ist
              keine Kursuhrzeit. Fehlende Quellenaktualisierung bleibt unbekannt.
            </p>
            {series && (
              <>
                <div
                  className="overflow-x-auto"
                  role="region"
                  aria-label={item.name + ': gespeicherte EOD-Werte'}
                  tabIndex={0}
                >
                  <table className="w-full text-left">
                    <caption className="mb-2 text-left">
                      {item.name} · {state.result!.price_field} · {unit} · Originalwerte
                    </caption>
                    <thead>
                      <tr>
                        {[
                          'Handelstag',
                          'Preis',
                          'Herkunft',
                          'Empfangen (UTC)',
                          'Quellenaktualisierung',
                          'Qualität / Hinweise',
                        ].map((title) => (
                          <th key={title} scope="col" className="p-2">
                            {title}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {series.points.slice(tablePage * 50, (tablePage + 1) * 50).map((point) => (
                        <tr key={point.trading_date} className="border-t border-slate-700">
                          <th scope="row" className="whitespace-nowrap p-2">
                            {chartDate(point.trading_date)}
                          </th>
                          <td className="p-2">{point.value ?? '—'}</td>
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
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    className={button}
                    disabled={tablePage === 0}
                    onClick={() => setPage(tablePage - 1)}
                  >
                    Vorige Werte
                  </button>
                  <span>
                    Seite {tablePage + 1} / {Math.max(1, Math.ceil(series.points.length / 50))}
                  </span>
                  <button
                    type="button"
                    className={button}
                    disabled={(tablePage + 1) * 50 >= series.points.length}
                    onClick={() => setPage(tablePage + 1)}
                  >
                    Weitere Werte
                  </button>
                </div>
              </>
            )}
          </div>
        )}
      </details>
    </article>
  );
}
