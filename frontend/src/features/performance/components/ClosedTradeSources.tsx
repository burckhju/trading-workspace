import { useState } from 'react';
import { Link } from 'react-router-dom';

import { classificationText, closedTradeReasonText } from '../services/closedTradesPresentation';
import { executionTimeText, moneyText } from '../services/presentation';
import type { ClosedTradeItem, ClosedTradeReport, ClosedTradeSellContribution } from '../types/api';
import { ReportSourceEntry } from './ReportSourceEntry';

const periodText: Record<ClosedTradeSellContribution['period_status'], string> = {
  IN_PERIOD: 'Verkauf innerhalb des Berichtszeitraums',
  OUTSIDE_PERIOD: 'Verkauf außerhalb des Berichtszeitraums',
  PERIOD_AMBIGUOUS: 'Zeitraum dieses Verkaufs mehrdeutig',
  PERIOD_UNKNOWN: 'Zeitraum dieses Verkaufs unbekannt',
};

export function ClosedTradeSources({
  item,
  report,
  showEditorLink = true,
}: {
  item: ClosedTradeItem;
  report: ClosedTradeReport;
  showEditorLink?: boolean;
}) {
  const [showHistory, setShowHistory] = useState(false);
  const tradeSources = report.sources.filter((source) => source.trade_id === item.trade_id);
  const byId = new Map(tradeSources.map((source) => [source.execution_id, source]));
  return (
    <section
      aria-label={`Herkunft Trade ${item.trade_id}`}
      className="mt-4 space-y-4 border-t border-slate-700 pt-4"
    >
      <header>
        <h3 className="font-semibold">Vollständiges Tradeergebnis und Buchungshistorie</h3>
        <p className="mt-1 text-sm text-slate-400">
          Alle Werte und Quellen stammen aus derselben Berichtsantwort. Frühere Verkäufe gehören zum
          Gesamtverlauf, auch wenn sie außerhalb des gewählten Zeitraums liegen. Ausschließlich der
          tatsächliche Vollabschluss bestimmt die Zuordnung des Trades.
        </p>
      </header>
      <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
        <div>
          <dt className="text-slate-400">Vollständiges Tradeergebnis · Anzeige</dt>
          <dd>
            {item.status === 'EXCLUDED'
              ? 'Ausgeschlossen aus dieser Auswahl'
              : moneyText(item.realized_gross_pnl_display, item.currency_code)}
          </dd>
        </div>
        <div>
          <dt className="text-slate-400">Vollständiges Tradeergebnis · ungerundet</dt>
          <dd className="break-all">
            <code>
              {item.status === 'EXCLUDED'
                ? 'Ausgeschlossen aus dieser Auswahl'
                : (item.realized_gross_pnl ?? 'Nicht berechenbar')}
            </code>
            {item.realized_gross_pnl !== null && ` ${item.currency_code}`}
          </dd>
        </div>
        <div>
          <dt className="text-slate-400">Klassifikation nach ungerundetem Ergebnis</dt>
          <dd>
            {item.classification === null
              ? 'Keine Klassifikation'
              : classificationText[item.classification]}
          </dd>
        </div>
      </dl>
      {item.status === 'NOT_COMPUTABLE' && (
        <p className="rounded-lg border border-amber-800 p-3 text-sm text-amber-300">
          Dieser Trade hat kein vollständig qualifiziertes Ergebnis. Eventuell bekannte einzelne
          SELL-Beiträge unten sind Herkunftsdetails; sie ergeben keinen Trade-Teilbetrag und gehen
          nicht in die Berichtsteilsumme oder die positiven, negativen und neutralen Zähler ein.
        </p>
      )}
      <div>
        <h4 className="font-medium">Alle wirksamen SELL-Beiträge im Gesamtverlauf</h4>
        <p className="mt-1 text-sm text-slate-400">
          Die bestehende Positionsrechnung liefert jeden Beitrag und seine Kostenbasis. Eine belegte
          Währung am letzten Verkauf allein belegt keine einheitliche Währung des Gesamttrades.
        </p>
        {item.sell_contributions.length === 0 && (
          <p className="mt-3 text-sm">Keine zuverlässig projizierbaren SELL-Beiträge vorhanden.</p>
        )}
        <ol aria-label="Wirksame SELL-Beiträge des gesamten Trades" className="mt-3 space-y-3">
          {item.sell_contributions.map((sale) => (
            <li
              key={sale.execution_id}
              aria-label={`SELL-Beitrag ${sale.execution_id}`}
              className="rounded-lg border border-slate-700 p-3 text-sm"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="font-medium">
                    {sale.is_closing ? 'Tatsächlicher Vollabschluss' : 'Früherer Teilverkauf'} ·{' '}
                    {sale.quantity} Stück
                  </p>
                  <p className="mt-1">{executionTimeText(sale, report.filters.report_timezone)}</p>
                  <p className="mt-1 text-xs text-slate-400">
                    {periodText[sale.period_status]} · Beitrag zum Gesamtverlauf
                  </p>
                </div>
                <p className="font-semibold">
                  {sale.status === 'EXCLUDED'
                    ? 'Außerhalb der Währungsauswahl'
                    : moneyText(sale.realized_gross_pnl_delta_display, sale.currency_code)}
                </p>
              </div>
              {sale.reasons.map((reason) => (
                <p key={reason} className="mt-2 text-amber-300">
                  {closedTradeReasonText(reason)}
                </p>
              ))}
              <details className="mt-3">
                <summary className="cursor-pointer">Präziser Einzelbeitrag und Kostenbasis</summary>
                <dl className="mt-3 grid gap-3 sm:grid-cols-2">
                  <div>
                    <dt className="text-slate-400">Beitrag · ungerundet</dt>
                    <dd className="break-all">
                      <code>{sale.realized_gross_pnl_delta ?? 'Nicht berechenbar'}</code>
                      {sale.realized_gross_pnl_delta !== null && ` ${sale.currency_code}`}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-400">Average Cost vor Verkauf · je Stück</dt>
                    <dd className="break-all">
                      <code>{sale.average_cost_per_unit ?? 'Nicht berechenbar'}</code>
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-400">Kostenbasis vor / nach Verkauf</dt>
                    <dd className="break-all">
                      <code>{sale.cost_basis_before ?? 'Nicht berechenbar'}</code> /{' '}
                      <code>{sale.cost_basis_after ?? 'Nicht berechenbar'}</code>
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-400">Offene Stückzahl vor / nach Verkauf</dt>
                    <dd>
                      {sale.open_quantity_before} / {sale.open_quantity_after}
                    </dd>
                  </div>
                  {sale.cost_basis_before_close_reset !== null && (
                    <div>
                      <dt className="text-slate-400">Kostenrest vor Abschlussrücksetzung</dt>
                      <dd className="break-all">
                        <code>{sale.cost_basis_before_close_reset}</code>
                      </dd>
                    </div>
                  )}
                </dl>
                <p className="mt-3 break-all text-xs text-slate-400">SELL {sale.execution_id}</p>
                <p className="mt-2 break-all text-xs text-slate-400">
                  Vorherige wirksame Buchungen der Kostenbasis:{' '}
                  {sale.cost_basis_execution_ids.join(', ') || 'Keine'}
                </p>
                <p className="mt-2 break-all text-xs text-slate-400">
                  Verwendete Währungsbelege: {sale.currency_confirmation_ids.join(', ') || 'Keine'}
                </p>
              </details>
            </li>
          ))}
        </ol>
      </div>
      <div>
        <h4 className="font-medium">Wirksame Buchungen · vollständige Herkunft</h4>
        <ol aria-label="Wirksame Trade-Historie" className="mt-3 space-y-3">
          {item.effective_execution_ids.map((id) => {
            const source = byId.get(id);
            return source ? (
              <ReportSourceEntry
                key={id}
                source={source}
                timezone={report.filters.report_timezone}
              />
            ) : (
              <li key={id} role="alert">
                Buchungsquelle {id} fehlt in dieser Antwort. Herkunft ist unvollständig.
              </li>
            );
          })}
        </ol>
      </div>
      <details className="text-sm" onToggle={(event) => setShowHistory(event.currentTarget.open)}>
        <summary className="cursor-pointer">
          Gesamte gelesene Historie einschließlich ersetzter Buchungen ({tradeSources.length})
        </summary>
        <p className="my-2 text-slate-400">
          Historisch ersetzte Buchungen bleiben nachvollziehbar und zählen nicht zusätzlich.
          Währungsbestätigungen zeigen ihre eigene Herkunft und Änderungshistorie.
        </p>
        {showHistory && (
          <ol aria-label="Gesamte Trade-Historie" className="space-y-3">
            {tradeSources.map((source) => (
              <ReportSourceEntry
                key={source.execution_id}
                source={source}
                timezone={report.filters.report_timezone}
              />
            ))}
          </ol>
        )}
      </details>
      <details className="text-sm text-slate-400">
        <summary className="cursor-pointer">Tradeidentität und verwendete Währungsbelege</summary>
        <p className="mt-2 break-all">
          Trade {item.trade_id} · Produkt {item.product_id}
        </p>
        <p className="mt-2 break-all">
          Abschlussbuchung: {item.closing_execution_id ?? 'Nicht zuverlässig bestimmbar'}
        </p>
        <p className="mt-2">
          Ursprung:{' '}
          {item.origin === 'WORKSPACE_SELECTION'
            ? 'Eigener Trade aus Produktauswahl'
            : 'Als eigener Trade erfasste externe Quelle'}
          . Der Produktname ist die heutige Stammdatenanzeige und kein historischer Währungsbeleg.
        </p>
        <ul className="mt-2 list-inside list-disc break-all">
          {item.currency_confirmation_ids.map((id) => (
            <li key={id}>Bestätigung {id}</li>
          ))}
        </ul>
      </details>
      {showEditorLink && (
        <Link
          className="inline-block rounded text-sm text-sky-300 underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
          to={`/trade-management?trade_id=${encodeURIComponent(item.trade_id)}#execution-dates`}
        >
          Buchungen und Währungsbestätigungen im Trade prüfen
        </Link>
      )}
    </section>
  );
}
