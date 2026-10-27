import { useState } from 'react';
import { Link } from 'react-router-dom';

import { ClosedTradeSources } from './ClosedTradeSources';
import { ClosedTradeStatistics } from './ClosedTradeStatistics';
import { ClosedTradeSummary } from './ClosedTradeSummary';
import {
  CLOSED_REPORT_PAGE_SIZE,
  closedTradeSourceLink,
  type ClosedReportContext,
  type ClosedReportView,
} from '../services/closedReportContext';
import {
  classificationText,
  closedTradeGroupText,
  closedTradeReasonText,
} from '../services/closedTradesPresentation';
import { executionTimeText, moneyText } from '../services/presentation';
import type { ClosedTradeReport } from '../types/api';

const inputClass =
  'mt-1 block w-full min-w-0 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2';
const buttonClass =
  'rounded-lg border border-slate-600 px-3 py-2 text-sm disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400';
const PAGE_SIZE = CLOSED_REPORT_PAGE_SIZE;

export function ClosedTradesReportView({
  report,
  context,
  onContext,
}: {
  report: ClosedTradeReport;
  context: ClosedReportContext | null;
  onContext: (context: ClosedReportContext) => void;
}) {
  const view = context?.view ?? 'candidates';
  const requestedPage = context?.page ?? 0;
  const navigateView = (nextView: ClosedReportView, nextPage: number) =>
    onContext({
      filters: report.filters,
      basis: report.basis.id,
      view: nextView,
      page: nextPage,
    });
  const [expanded, setExpanded] = useState<string | null>(null);
  const { counts, filters } = report;
  const items = report.items.filter((item) => {
    if (view === 'qualified') return item.status === 'USABLE';
    if (view === 'unresolved') return item.status === 'NOT_COMPUTABLE';
    if (view === 'excluded') return item.status === 'EXCLUDED';
    if (view === 'candidates') return item.status !== 'EXCLUDED';
    return true;
  });
  const pages = Math.max(1, Math.ceil(items.length / PAGE_SIZE));
  const page = Math.min(requestedPage, pages - 1);
  const visible = items.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  return (
    <div className="space-y-6" aria-label="Abschlussbericht">
      <ClosedTradeSummary report={report} />
      <ClosedTradeStatistics report={report} />
      <section aria-labelledby="closed-trades-items-title" className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 id="closed-trades-items-title" className="text-lg font-semibold">
              Trades und vollständige Ergebnisse
            </h2>
            <p className="mt-1 text-sm text-slate-400">
              Ein Eintrag je Trade-ID. Quellen zeigen den gesamten wirksamen Verlauf und historische
              Korrekturen.
            </p>
          </div>
          <label className="text-sm">
            Zeilen anzeigen
            <select
              className={inputClass}
              value={view}
              onChange={(event) => {
                navigateView(event.target.value as ClosedReportView, 0);
                setExpanded(null);
              }}
            >
              <option value="candidates">
                Relevante / ungeklärte Fälle ({counts.qualified + counts.unresolved})
              </option>
              <option value="qualified">Qualifizierte Trades ({counts.qualified})</option>
              <option value="unresolved">Datenlücken ({counts.unresolved})</option>
              <option value="excluded">
                Ausschlüsse ({counts.examined - counts.qualified - counts.unresolved})
              </option>
              <option value="all">Alle geprüften Trades ({counts.examined})</option>
            </select>
          </label>
        </div>
        {requestedPage !== page && (
          <p role="status">
            Die ursprüngliche Seite {requestedPage + 1} ist im neu gelesenen Stand nicht mehr
            verfügbar. Angezeigt wird Seite {page + 1}; Zeitraum und Zeilenfilter bleiben erhalten.
          </p>
        )}
        {items.length === 0 && (
          <p className="rounded-lg border border-slate-800 p-4 text-sm">
            Keine Trades in diesem Zeilenfilter. Die Berichtssumme, Kennzahlen und Datenabdeckung
            oben bleiben unverändert.
          </p>
        )}
        <div className="space-y-3">
          {visible.map((item) => (
            <article
              key={item.trade_id}
              aria-label={`Trade ${item.trade_id}`}
              className="min-w-0 rounded-xl border border-slate-800 p-4"
            >
              <div className="grid gap-4 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1.5fr)_minmax(0,1fr)_auto]">
                <div>
                  <h3 className="break-words font-medium">
                    {item.product_name ?? 'Produktname nicht verfügbar'}
                  </h3>
                  <Link
                    className="mt-1 inline-block break-all rounded text-xs text-sky-300 underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
                    to={closedTradeSourceLink(item.trade_id, {
                      filters: report.filters,
                      basis: report.basis.id,
                      view,
                      page,
                    })}
                  >
                    Trade {item.trade_id} prüfen
                  </Link>
                  <p className="mt-2 text-xs text-slate-400">Tatsächlicher Vollabschluss</p>
                  <p className="mt-1 text-sm">
                    {item.closing_time
                      ? executionTimeText(item.closing_time, filters.report_timezone)
                      : item.group === 'OPEN'
                        ? 'Noch nicht abgeschlossen'
                        : item.group === 'CANCELLED'
                          ? 'Storno ist kein wirtschaftlicher Abschluss'
                          : 'Nicht zuverlässig bestimmbar'}
                  </p>
                </div>
                <div>
                  <p
                    className={
                      item.status === 'USABLE'
                        ? 'text-sm text-sky-300'
                        : item.status === 'NOT_COMPUTABLE'
                          ? 'text-sm text-amber-300'
                          : 'text-sm text-slate-300'
                    }
                  >
                    {closedTradeGroupText[item.group]}
                  </p>
                  {item.reasons.map((reason) => (
                    <p key={reason} className="mt-1 text-sm text-slate-400">
                      {closedTradeReasonText(reason)}
                    </p>
                  ))}
                </div>
                <div>
                  <p className="text-xs text-slate-400">Gesamtes Bruttoergebnis</p>
                  <p className="mt-1 break-words font-semibold">
                    {item.status === 'EXCLUDED'
                      ? 'Nicht in der Summe'
                      : moneyText(item.realized_gross_pnl_display, item.currency_code)}
                  </p>
                  <p className="mt-1 text-sm">
                    {item.classification === null
                      ? 'Keine Klassifikation'
                      : classificationText[item.classification]}
                  </p>
                </div>
                <button
                  type="button"
                  className={`${buttonClass} self-start`}
                  aria-expanded={expanded === item.trade_id}
                  onClick={() => setExpanded(expanded === item.trade_id ? null : item.trade_id)}
                >
                  {expanded === item.trade_id ? 'Quellen schließen' : 'Quellen und Gesamtverlauf'}
                </button>
              </div>
              {expanded === item.trade_id && <ClosedTradeSources item={item} report={report} />}
            </article>
          ))}
        </div>
        {items.length > 0 && (
          <nav
            aria-label="Berichtsseiten"
            className="flex flex-wrap items-center justify-between gap-3 text-sm"
          >
            <p>
              Seite {page + 1} von {pages} · {items.length} Trades in diesem Filter · Summen, Zähler
              und Kennzahlen gelten für die gesamte Auswahl.
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                className={buttonClass}
                disabled={page === 0}
                onClick={() => {
                  navigateView(view, page - 1);
                  setExpanded(null);
                }}
              >
                Vorherige Seite
              </button>
              <button
                type="button"
                className={buttonClass}
                disabled={page + 1 >= pages}
                onClick={() => {
                  navigateView(view, page + 1);
                  setExpanded(null);
                }}
              >
                Nächste Seite
              </button>
            </div>
          </nav>
        )}
      </section>
      <details className="rounded-xl border border-slate-800 p-4 text-sm">
        <summary className="cursor-pointer font-medium">
          Auswertungsdefinition und Quellenstand
        </summary>
        <div className="mt-3 space-y-2 text-slate-400">
          <p>
            Definition: {report.definition_version}. Der wirksame SELL, der die vorher positive
            offene Stückzahl auf null reduziert, bestimmt den Abschlusszeitraum. Das gesamte
            Bruttoergebnis umfasst sämtliche wirksamen SELL-Beiträge dieses Trades; frühere Perioden
            werden nicht abgeschnitten.
          </p>
          <p>
            Brutto vor Gebühren, Kommissionen und Steuern. Alle benötigten Kaufkosten und sämtliche
            Verkaufserlöse müssen vollständig in derselben belegten Währung vorliegen. Keine
            automatische Währungsumrechnung.
          </p>
          <p>
            Aktuell bekannte, wirksame korrigierte Fakten: Eine Korrektur von Preis, Menge, Datum
            oder Währungsherkunft kann Ergebnis, Abschlussperiode oder Abschlusseignung verändern.
            Ein damaliger Wissensstand wird nicht rekonstruiert.
          </p>
          <p>
            Berichtszone: {filters.report_timezone}. Inklusive Kalendertage bilden das Intervall von{' '}
            {report.interval_start_at} bis ausschließlich {report.interval_end_at}. Datum ohne
            Uhrzeit bleibt Datum. Mehrdeutige Zugehörigkeit wird nicht als sicherer
            Periodenabschluss gezählt.
          </p>
          <p>
            Quellen gelesen von {report.basis.read_started_at} bis {report.basis.read_completed_at};
            berechnet am {report.basis.calculated_at}. Diese Zeiten sind keine Ausführungszeiten.
          </p>
          <p className="break-all">
            Quellenstand: <code>{report.basis.id}</code>
          </p>
          <p>
            Summen, Kennzahlen, Zähler, Zeilen und Quellen gehören zu dieser einen Antwort. Lokale
            Seiten und Quelldetails lesen keine neuen Daten. Ein erneutes Lesen oder der Sprung in
            die Trade-Historie kann einen neueren Stand zeigen.
          </p>
        </div>
      </details>
    </div>
  );
}
