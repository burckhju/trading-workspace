import { Component, lazy, Suspense, useMemo, useState, type ReactNode } from 'react';

import { REALIZED_REPORT_PAGE_SIZE } from '../services/performanceReportContext';
import { executionTimeText, moneyText, reasonText } from '../services/presentation';
import { sellPlotCoordinate, sellPlotExtent } from '../services/realizedGrossVisualization';
import type { RealizedGrossItem, RealizedGrossReport } from '../types/api';

class PlotLoadError extends Error {}

const RealizedGrossPlot = lazy(async () => {
  try {
    const module = await import('./RealizedGrossPlot');
    return { default: module.RealizedGrossPlot };
  } catch (cause) {
    throw new PlotLoadError('Optional SELL plot could not load.', { cause });
  }
});

class PlotBoundary extends Component<
  { children: ReactNode },
  { failure: 'load' | 'render' | null }
> {
  state: { failure: 'load' | 'render' | null } = { failure: null };

  static getDerivedStateFromError(error: unknown) {
    return { failure: error instanceof PlotLoadError ? 'load' : 'render' };
  }

  render() {
    return this.state.failure ? (
      <p className="rounded-lg border border-slate-600 p-3 text-sm">
        Das Diagramm konnte nicht {this.state.failure === 'load' ? 'geladen' : 'dargestellt'}{' '}
        werden. Alle SELL-Beiträge und Originalquellen bleiben in der Tabelle erreichbar.
      </p>
    ) : (
      this.props.children
    );
  }
}

const controlClass =
  'rounded-lg border border-slate-600 px-3 py-2 text-sm disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400';

export function RealizedGrossVisualization({
  report,
  onOpenSources,
}: {
  report: RealizedGrossReport;
  onOpenSources: (item: RealizedGrossItem) => void;
}) {
  const [page, setPage] = useState(0);
  const coordinates = useMemo(
    () => report.items.map((item) => sellPlotCoordinate(item, report.currency.code)),
    [report],
  );
  const extent = useMemo(() => sellPlotExtent(coordinates), [coordinates]);
  const start = page * REALIZED_REPORT_PAGE_SIZE;
  const visible = report.items.slice(start, start + REALIZED_REPORT_PAGE_SIZE);
  const pages = Math.max(1, Math.ceil(report.items.length / REALIZED_REPORT_PAGE_SIZE));
  const entries = visible.flatMap((item, index) => {
    const value = coordinates[start + index].value;
    return value === null
      ? []
      : [{ ordinal: start + index + 1, executionId: item.execution_id, value }];
  });
  const { filters, currency, counts } = report;

  return (
    <section
      aria-label="Einzelne SELL-Beiträge"
      className="min-w-0 space-y-4 rounded-xl border border-slate-700 bg-slate-900/50 p-4 sm:p-5"
    >
      <h2 className="text-lg font-semibold">Einzelne SELL-Beiträge</h2>
      <p className="text-sm">
        Realisierter Bruttobeitrag je wirksamer SELL-Ausführung vor Gebühren, Kommissionen und
        Steuern. Auch Teilverkäufe offener Trades sind enthalten. Ein SELL ist kein vollständiges
        Tradeergebnis.
      </p>
      <p className="text-sm text-slate-300">
        {filters.from_date} bis einschließlich {filters.to_date} · {filters.report_timezone} ·{' '}
        {currency.code} · keine Währungsumrechnung.
      </p>
      <p className="text-sm">
        Gesamter Bericht: {counts.examined} wirksame SELLs geprüft · {counts.usable} verwendbare
        Beiträge · {counts.unresolved} ungeklärte Fälle · {counts.excluded} ausgeschlossene SELLs.
        Diese Zähler sind überlappende Sichten und werden nicht addiert. Stornierte Trades sind
        keine SELL-Ereignisse.
      </p>
      {report.summary.status === 'PARTIAL' || report.summary.status === 'NOT_COMPUTABLE' ? (
        <p className="text-sm text-amber-200">
          Die vollständige Bruttosumme ist unbekannt. Vorhandene Einzelpunkte ersetzen keine
          vollständige Auswertung. Ungeklärte Fälle bleiben ohne Geldpunkt in der Tabelle.
        </p>
      ) : report.summary.status === 'EMPTY' ? (
        <p className="text-sm">
          Geprüfte leere Auswahl: keine qualifizierten oder ungeklärten Beiträge in dieser Zeitraum-
          und Währungsauswahl. Eventuelle Ausschlüsse bleiben in der Tabelle sichtbar.
        </p>
      ) : null}
      <p className="text-sm text-slate-300">
        Jede Zeile ist ein eigenes Ereignis in der gelieferten Berichtreihenfolge. Abstände sind
        keine Zeitabstände; es gibt keine Tages- oder Monatssummen. Datum ohne Uhrzeit bleibt mit
        seiner Originalzeitzone in der Tabelle erhalten.
      </p>
      <p className="text-sm" data-testid="sell-visualization-scope">
        Grafischer Ausschnitt und Tabelle: {visible.length ? start + 1 : 0}–{start + visible.length}{' '}
        von {report.items.length} gelieferten SELL-Zeilen. Lokale Seiten und der Zeilenfilter der
        Quellenkarten ändern weder Gesamtwerte noch diese Grundgesamtheit.
      </p>
      {entries.length ? (
        <figure className="min-w-0">
          <figcaption className="mb-2 text-sm text-slate-300">
            Bruttobeitrag in {currency.code} · links negativ, rechts positiv. Exakte Null behält
            ihren eigenen Punkt. Sehr kleine Beträge können bei dieser Skala an der Nulllinie
            erscheinen; der Originalwert in der Tabelle entscheidet. Dieselbe Achsenskala gilt auf
            allen Grafikseiten.
          </figcaption>
          <PlotBoundary>
            <Suspense
              fallback={
                <p className="text-sm">
                  Diagramm wird geladen. Die Datentabelle ist bereits verfügbar.
                </p>
              }
            >
              <RealizedGrossPlot
                entries={entries}
                ordinals={visible.map((_, index) => start + index + 1)}
                extent={extent}
              />
            </Suspense>
          </PlotBoundary>
        </figure>
      ) : (
        <p className="text-sm">Keine grafisch darstellbaren Geldpunkte auf dieser Seite.</p>
      )}
      <p className="text-xs text-slate-400">
        Fehlende Werte erscheinen nicht als Null. Sehr kleine oder große Beträge außerhalb der
        grafischen Zahlendarstellung bleiben vollständig als Originalwerte erhalten. Die
        Grafikgrenze für den absoluten Betrag ist 1e-100 bis 1e100 {currency.code}; exakte Null
        bleibt ebenfalls darstellbar. Die bestehenden Quellen zeigen Kostenbasis, Währungsbelege und
        Korrekturen.
      </p>
      <div
        role="region"
        aria-label="SELL-Datentabelle"
        tabIndex={0}
        className="min-w-0 overflow-x-auto rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
      >
        <table className="w-full min-w-[42rem] table-fixed text-left text-sm">
          <caption className="pb-3 text-left font-medium">SELL-Beiträge und Originalwerte</caption>
          <thead>
            <tr className="border-b border-slate-600">
              <th scope="col" className="w-1/4 p-2">
                Ereignis und Ausführungszeit
              </th>
              <th scope="col" className="w-1/4 p-2">
                Bruttobeitrag · {currency.code}
              </th>
              <th scope="col" className="w-1/4 p-2">
                Status und Darstellung
              </th>
              <th scope="col" className="w-1/4 p-2">
                Originalquellen
              </th>
            </tr>
          </thead>
          <tbody>
            {visible.map((item, index) => {
              const ordinal = start + index + 1;
              return (
                <tr key={item.execution_id} className="border-b border-slate-800 align-top">
                  <th scope="row" className="p-2 font-normal [overflow-wrap:anywhere]">
                    <span className="font-semibold">SELL {ordinal}</span>
                    <span className="mt-1 block">
                      {item.product_name ?? 'Produktname nicht verfügbar'}
                    </span>
                    <span className="mt-1 block">
                      {executionTimeText(item, filters.report_timezone)}
                    </span>
                    <code className="mt-1 block text-xs">{item.execution_id}</code>
                  </th>
                  <td className="p-2 [overflow-wrap:anywhere]">
                    <p>
                      {item.status === 'EXCLUDED'
                        ? 'Nicht in der Summe'
                        : moneyText(item.realized_gross_pnl_delta_display, item.currency_code)}
                    </p>
                    <p className="mt-2 text-xs text-slate-300">
                      Originalwert:{' '}
                      <code>{item.realized_gross_pnl_delta ?? 'Nicht vorhanden'}</code>
                      {item.realized_gross_pnl_delta !== null &&
                        ` ${item.currency_code ?? '(Währung unbekannt)'}`}
                    </p>
                  </td>
                  <td className="p-2 [overflow-wrap:anywhere]">
                    <p>{coordinates[start + index].explanation}</p>
                    {item.reasons.map((reason) => (
                      <p key={reason} className="mt-2 text-slate-300">
                        {reasonText(reason)}
                      </p>
                    ))}
                  </td>
                  <td className="p-2">
                    <button
                      type="button"
                      className={`${controlClass} text-left`}
                      onClick={() => onOpenSources(item)}
                    >
                      Originalquellen zu SELL {ordinal}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <nav
        aria-label="Grafik- und Tabellenseiten"
        className="flex flex-wrap items-center justify-between gap-3 text-sm"
      >
        <p>
          Seite {page + 1} von {pages} · {report.items.length} SELL-Zeilen insgesamt
        </p>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className={controlClass}
            disabled={page === 0}
            onClick={() => setPage(page - 1)}
          >
            Vorherige Grafikseite
          </button>
          <button
            type="button"
            className={controlClass}
            disabled={page + 1 >= pages}
            onClick={() => setPage(page + 1)}
          >
            Nächste Grafikseite
          </button>
        </div>
      </nav>
    </section>
  );
}
