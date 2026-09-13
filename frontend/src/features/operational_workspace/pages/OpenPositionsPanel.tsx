import { Fragment, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import type { OperationalPosition } from '../types';
import { PositionDetails } from '../components/PositionDetails';
import { PositionStatus, QuoteStatus } from '../components/PositionStatus';
import {
  dateLabel,
  defaultPositionsView,
  formatUnits,
  hasAlert,
  hasDataProblem,
  money,
  numberLabel,
  pnlClass,
  portfolioTotals,
  positionFilters,
  positionSorts,
  positionTone,
  purchaseDate,
  readPositionsView,
  savePositionsView,
  timeLabel,
  visiblePositions,
  type PositionFilter,
  type PositionSort,
  type PositionsView,
} from '../services/positionsView';

const rowBorders = {
  critical: 'border-l-rose-400',
  attention: 'border-l-amber-400',
  data: 'border-l-amber-600',
  ok: 'border-l-emerald-500',
};
const control =
  'rounded-lg border border-slate-600 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus-visible:outline-2 focus-visible:outline-sky-300 disabled:opacity-50';

export function OpenPositionsPanel({
  positions,
  signalsLoading = false,
}: {
  positions: OperationalPosition[];
  signalsLoading?: boolean;
}) {
  const [view, setView] = useState(readPositionsView);
  const [expanded, setExpanded] = useState<string | null>(null);
  useEffect(() => savePositionsView(view), [view]);
  const filtered = useMemo(() => visiblePositions(positions, view), [positions, view]);
  const totals = useMemo(() => portfolioTotals(positions), [positions]);
  const pages = Math.max(1, Math.ceil(filtered.length / view.pageSize));
  const page = Math.min(view.page, pages);
  const displayed = filtered.slice((page - 1) * view.pageSize, page * view.pageSize);
  function change(update: Partial<PositionsView>) {
    setView((v) => ({ ...v, ...update, page: 1 }));
  }
  function sortBy(sort: PositionSort) {
    change({ sort, descending: view.sort === sort ? !view.descending : false });
  }
  function header(label: string, sort: PositionSort, classes = '') {
    return (
      <th
        scope="col"
        className={`p-3 text-left font-medium ${classes}`}
        aria-sort={view.sort === sort ? (view.descending ? 'descending' : 'ascending') : undefined}
      >
        <button
          type="button"
          onClick={() => sortBy(sort)}
          className="whitespace-nowrap rounded py-1 focus-visible:outline-2 focus-visible:outline-sky-300"
        >
          {label}{' '}
          <span aria-hidden="true">
            {view.sort === sort ? (view.descending ? '▼' : '▲') : '↕'}
          </span>
        </button>
      </th>
    );
  }
  return (
    <section aria-labelledby="open-positions-heading" className="min-w-0 space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 id="open-positions-heading" className="text-xl font-semibold text-white">
            Offene Positionen · {positions.length}
          </h2>
          <p className="mt-1 text-sm text-slate-400">
            Kompakter Depotstatus · Details öffnen statt lange Karten vergleichen.
          </p>
        </div>
        <p className="text-sm text-slate-300">
          {positions.filter(hasAlert).length} mit fachlichen Hinweisen ·{' '}
          {positions.filter(hasDataProblem).length} mit Datenproblemen
        </p>
      </header>
      <details className="rounded-xl border border-slate-700 bg-slate-900/60 p-3">
        <summary className="cursor-pointer text-sm text-slate-200">
          Bewertungssummen je Währung · gesamter offener Bestand
        </summary>
        <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {totals.map(([currency, total]) => (
            <div key={currency} className="rounded-lg border border-slate-700 p-3 text-sm">
              <h3 className="font-semibold">{currency}</h3>
              <p>
                Marktwert: {total.valued ? `${formatUnits(total.value)} ${currency}` : '—'} ·{' '}
                {total.valued}/{total.count} bewertet
              </p>
              <p>
                Nicht realisierter Brutto-G/V:{' '}
                {total.pnlCount ? `${formatUnits(total.pnl, 2, true)} ${currency}` : '—'} ·{' '}
                {total.pnlCount}/{total.count} verfügbar
              </p>
              <p className="text-amber-200">{total.indicative} Bewertungen indikativ / veraltet</p>
              <p className="text-xs text-slate-400">
                Ältester berücksichtigter Kurs: {timeLabel(total.oldest)} · {total.unknownTime}{' '}
                Kurszeitpunkte unbekannt
              </p>
            </div>
          ))}
        </div>
        <p className="mt-2 text-xs text-slate-400">
          Keine Währungsumrechnung. Fehlende Werte zählen nicht als Null. Summen sind bei
          unvollständiger Abdeckung Teilsummen; nicht aktuelle Bewertungen bleiben indikativ. Filter
          verändern diese Bestandssummen nicht.
        </p>
      </details>
      <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-3">
        <div className="flex flex-wrap gap-3">
          <label className="min-w-0 flex-1 text-sm">
            <span className="mb-1 block text-slate-300">Position suchen</span>
            <input
              type="search"
              value={view.query}
              maxLength={200}
              onChange={(e) => change({ query: e.target.value })}
              placeholder="Produkt, WKN, ISIN oder Basiswert"
              className={`${control} w-full min-w-56`}
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-slate-300">Sortierung</span>
            <select
              value={view.sort}
              onChange={(e) => change({ sort: e.target.value as PositionSort })}
              className={control}
            >
              {Object.entries(positionSorts).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-slate-300">Reihenfolge</span>
            <select
              value={view.descending ? 'desc' : 'asc'}
              onChange={(e) => change({ descending: e.target.value === 'desc' })}
              className={control}
            >
              <option value="asc">Aufsteigend</option>
              <option value="desc">Absteigend</option>
            </select>
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-slate-300">Zeilen pro Seite</span>
            <select
              value={view.pageSize}
              onChange={(e) => change({ pageSize: Number(e.target.value) as 25 | 50 | 100 })}
              className={control}
            >
              {[25, 50, 100].map((n) => (
                <option key={n}>{n}</option>
              ))}
            </select>
          </label>
        </div>
        <div role="group" aria-label="Positionsfilter" className="mt-3 flex flex-wrap gap-2">
          {Object.entries(positionFilters).map(([key, label]) => (
            <button
              key={key}
              type="button"
              aria-pressed={view.filter === key}
              onClick={() => change({ filter: key as PositionFilter })}
              className={`${control} ${view.filter === key ? 'border-sky-400 bg-sky-950 text-sky-100' : ''}`}
            >
              {label}
            </button>
          ))}
          <button
            type="button"
            onClick={() => {
              setExpanded(null);
              setView({ ...defaultPositionsView });
            }}
            className={control}
          >
            Ansicht zurücksetzen
          </button>
        </div>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
        <p role="status" aria-live="polite">
          {filtered.length} Treffer von {positions.length} offenen Positionen · Seite {page} von{' '}
          {pages}
        </p>
        {signalsLoading && (
          <p className="text-sky-200">
            Positionssignale werden ergänzt … Noch fehlende Signale gelten nicht als unauffällig.
          </p>
        )}
      </div>
      <p className="text-xs leading-5 text-slate-300">
        <span className="text-rose-200">! Rot: kritischer Hinweis</span> ·{' '}
        <span className="text-amber-200">! / ? Gelb: Hinweis / Daten prüfen</span> ·{' '}
        <span className="text-sky-200">Blau: indikativer Kurs</span> ·{' '}
        <span className="text-emerald-200">✓ Grün: geprüft unauffällig</span> · Grau: fehlend. G/V
        separat: + grün / − rot, kein Handelssignal.
      </p>
      {positions.some((p) => p.valuation_status !== 'AVAILABLE' || p.analysis_warning) && (
        <p className="rounded-lg border border-amber-900 bg-amber-950/20 p-3 text-sm text-amber-200">
          Indikative, veraltete oder fehlende Kurse sind je Zeile gekennzeichnet. Quelle und
          Kurszeitpunkt unter „Details“. Keine Orderfreigabe.
        </p>
      )}
      {filtered.length === 0 ? (
        <p className="rounded-xl border border-slate-700 p-5">
          {positions.length === 0
            ? 'Keine offenen Positionen vorhanden.'
            : 'Keine Position entspricht der Suche und dem Filter.'}
        </p>
      ) : (
        <div
          role="region"
          aria-label="Positionstabelle, horizontal und vertikal scrollbar"
          tabIndex={0}
          className="max-h-[70vh] min-w-0 overflow-auto rounded-xl border border-slate-700 focus-visible:outline-2 focus-visible:outline-sky-300"
        >
          <table className="w-full border-separate border-spacing-0 text-sm text-slate-200">
            <caption className="sr-only">
              Offene Positionen. Spaltenüberschriften sind sortierbar. Fehlende Werte bleiben
              zuletzt; Geldwerte werden nach Währung gruppiert, nicht umgerechnet.
            </caption>
            <thead className="sticky top-0 z-20 bg-slate-900 text-slate-300">
              <tr>
                {header('Produkt', 'product', 'sticky left-0 z-30 min-w-52 bg-slate-900')}
                {header('Status', 'attention')}
                <th scope="col" className="hidden p-3 text-left font-medium lg:table-cell">
                  Basiswert
                </th>
                {header('Kaufdatum', 'purchased', 'hidden md:table-cell')}
                {header('Stück', 'quantity')}
                <th
                  scope="col"
                  className="hidden whitespace-nowrap p-3 text-right font-medium xl:table-cell"
                >
                  Ø Einstand
                </th>
                {header('Marktwert', 'value')}
                {header('Nicht realisierter G/V', 'pnl')}
                {header('Kursqualität / Zeitpunkt', 'quote')}
                <th scope="col" className="bg-slate-900 p-3 text-left font-medium">
                  Aktionen
                </th>
              </tr>
            </thead>
            <tbody>
              {displayed.map((p) => (
                <Fragment key={p.position_id}>
                  <tr data-position-id={p.position_id} className="group">
                    <th
                      scope="row"
                      className={`sticky left-0 z-10 min-w-52 max-w-72 border-b border-b-slate-800 border-l-4 ${rowBorders[positionTone(p)]} bg-slate-950 p-3 text-left font-normal group-hover:bg-slate-900`}
                    >
                      <span className="block break-words font-semibold text-white">
                        {p.product_name}
                      </span>
                      <span className="mt-1 block text-xs text-slate-400">
                        WKN {p.product_wkn ?? '—'}
                        {p.product_isin ? ` · ${p.product_isin}` : ''}
                      </span>
                    </th>
                    <td className="border-b border-slate-800 p-3">
                      <PositionStatus position={p} />
                      {p.open_alert_count > 0 && (
                        <span className="mt-1 block text-xs">
                          {p.open_alert_count} offene Hinweise
                        </span>
                      )}
                    </td>
                    <td className="hidden border-b border-slate-800 p-3 lg:table-cell">
                      {p.underlying_name ?? p.underlying_symbol ?? '—'}
                    </td>
                    <td className="hidden whitespace-nowrap border-b border-slate-800 p-3 tabular-nums md:table-cell">
                      {dateLabel(purchaseDate(p))}
                    </td>
                    <td className="border-b border-slate-800 p-3 text-right tabular-nums">
                      {p.open_quantity.toLocaleString('de-DE')}
                    </td>
                    <td className="hidden whitespace-nowrap border-b border-slate-800 p-3 text-right tabular-nums xl:table-cell">
                      {numberLabel(p.average_entry_price)}
                    </td>
                    <td className="whitespace-nowrap border-b border-slate-800 p-3 text-right tabular-nums">
                      {money(p.market_value, p.valuation_currency)}
                    </td>
                    <td
                      className={`whitespace-nowrap border-b border-slate-800 p-3 text-right font-medium tabular-nums ${pnlClass(p.unrealized_gross_pnl)}`}
                    >
                      {money(p.unrealized_gross_pnl, p.valuation_currency, true)}
                    </td>
                    <td className="min-w-40 border-b border-slate-800 p-3">
                      <QuoteStatus position={p} />
                      <span className="mt-1 block text-xs text-slate-400">
                        {timeLabel(p.quote_observed_at)}
                      </span>
                    </td>
                    <td className="min-w-40 border-b border-slate-800 p-3">
                      <div className="flex flex-col items-start gap-2">
                        <button
                          type="button"
                          className="rounded text-sky-200 underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-sky-300"
                          aria-expanded={expanded === p.position_id}
                          aria-controls={`position-detail-${p.position_id}`}
                          onClick={() =>
                            setExpanded(expanded === p.position_id ? null : p.position_id)
                          }
                        >
                          {expanded === p.position_id ? 'Details schließen' : 'Details'}
                        </button>
                        <Link
                          to={p.target}
                          className="rounded text-slate-100 underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-sky-300"
                        >
                          Trade verwalten
                        </Link>
                        <Link
                          to={`${p.target}#sale-capture`}
                          className="rounded border border-sky-800 bg-sky-950/40 px-2 py-1 text-sky-100 focus-visible:outline-2 focus-visible:outline-sky-300"
                        >
                          Verkauf erfassen
                        </Link>
                      </div>
                    </td>
                  </tr>
                  {expanded === p.position_id && (
                    <tr id={`position-detail-${p.position_id}`}>
                      <td colSpan={10} className="border-b border-slate-700 bg-slate-900/70">
                        <PositionDetails position={p} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <nav
        aria-label="Positionsseiten"
        className="flex flex-wrap items-center justify-between gap-3 text-sm"
      >
        <span>
          {filtered.length
            ? `${(page - 1) * view.pageSize + 1}–${Math.min(page * view.pageSize, filtered.length)} von ${filtered.length}`
            : '0 Treffer'}
        </span>
        <div className="flex gap-2">
          <button
            type="button"
            disabled={page === 1}
            onClick={() => setView((v) => ({ ...v, page: page - 1 }))}
            className={control}
          >
            Vorherige Seite
          </button>
          <button
            type="button"
            disabled={page === pages}
            onClick={() => setView((v) => ({ ...v, page: page + 1 }))}
            className={control}
          >
            Nächste Seite
          </button>
        </div>
      </nav>
    </section>
  );
}
