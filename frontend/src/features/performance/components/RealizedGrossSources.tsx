import { useState } from 'react';
import { Link } from 'react-router-dom';

import { moneyText } from '../services/presentation';
import type { RealizedGrossItem, RealizedGrossReport } from '../types/api';
import { ReportSourceEntry } from './ReportSourceEntry';

export function RealizedGrossSources({
  item,
  report,
}: {
  item: RealizedGrossItem;
  report: RealizedGrossReport;
}) {
  const [showFullHistory, setShowFullHistory] = useState(false);
  const tradeSources = report.sources.filter((source) => source.trade_id === item.trade_id);
  const byId = new Map(tradeSources.map((source) => [source.execution_id, source]));
  const prefixIds = [...new Set([...item.cost_basis_execution_ids, item.execution_id])];
  return (
    <section
      aria-label={`Herkunft SELL ${item.execution_id}`}
      className="mt-4 space-y-4 border-t border-slate-700 pt-4"
    >
      <header>
        <h3 className="font-semibold">Einzelbeitrag und vollständige Kostenbasis-Herkunft</h3>
        <p className="mt-1 text-sm text-slate-400">
          Alle folgenden Werte und Quellen stammen aus derselben Berichtsantwort. Eine spätere
          erneute Abfrage kann einen anderen korrigierten Stand zeigen.
        </p>
      </header>
      <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
        <div>
          <dt className="text-slate-400">Beitrag · Anzeige</dt>
          <dd>{moneyText(item.realized_gross_pnl_delta_display, item.currency_code)}</dd>
        </div>
        <div>
          <dt className="text-slate-400">Beitrag · ungerundeter Wert</dt>
          <dd className="break-all">
            <code>{item.realized_gross_pnl_delta ?? 'Nicht berechenbar'}</code>
            {item.realized_gross_pnl_delta !== null && ` ${item.currency_code}`}
          </dd>
        </div>
        <div>
          <dt className="text-slate-400">Average Cost vor Verkauf · je Stück</dt>
          <dd className="break-all">
            <code>{item.average_cost_per_unit ?? 'Nicht berechenbar'}</code>
            {item.average_cost_per_unit !== null && ` ${item.currency_code}`}
          </dd>
        </div>
        <div>
          <dt className="text-slate-400">Kostenbasis vor Verkauf</dt>
          <dd className="break-all">
            <code>{item.cost_basis_before ?? 'Nicht berechenbar'}</code>
            {item.cost_basis_before !== null && ` ${item.currency_code}`}
          </dd>
        </div>
        <div>
          <dt className="text-slate-400">Kostenbasis nach Verkauf</dt>
          <dd className="break-all">
            <code>{item.cost_basis_after ?? 'Nicht berechenbar'}</code>
            {item.cost_basis_after !== null && ` ${item.currency_code}`}
          </dd>
        </div>
        <div>
          <dt className="text-slate-400">Offene Stückzahl vor / nach Verkauf</dt>
          <dd>
            {item.open_quantity_before ?? 'unbekannt'} / {item.open_quantity_after ?? 'unbekannt'}
          </dd>
        </div>
        {item.cost_basis_before_close_reset !== null && (
          <div>
            <dt className="text-slate-400">Kostenrest vor Abschlussrücksetzung</dt>
            <dd className="break-all">
              <code>{item.cost_basis_before_close_reset}</code> {item.currency_code}
            </dd>
          </div>
        )}
      </dl>
      <p className="text-sm text-slate-400">
        Average Cost und Beitrag werden aus der wirksamen Historie bis zu diesem Verkauf berechnet.
        Frühere Teilverkäufe und Nachkäufe gehören dazu, auch außerhalb des Berichtszeitraums.{' '}
        Frühere Verkäufe belegen die Bestandsentwicklung; ihre Erlöswährung ist kein
        Kaufkostenbeleg.
      </p>
      <h4 className="font-medium">Vorherige wirksame Buchungen und dieser Verkauf</h4>
      <ol aria-label="Kostenbasispräfix und Verkauf" className="space-y-3">
        {prefixIds.map((id) => {
          const source = byId.get(id);
          return source ? (
            <ReportSourceEntry key={id} source={source} timezone={report.filters.report_timezone} />
          ) : (
            <li key={id} role="alert">
              Buchungsquelle {id} fehlt in dieser Antwort. Herkunft ist unvollständig.
            </li>
          );
        })}
      </ol>
      <details
        className="text-sm"
        onToggle={(event) => setShowFullHistory(event.currentTarget.open)}
      >
        <summary className="cursor-pointer">
          Gesamte gelesene Trade-Historie einschließlich ersetzter und späterer Buchungen (
          {tradeSources.length})
        </summary>
        <p className="my-2 text-slate-400">
          Spätere Buchungen sind Kontext; sie fließen nicht in die Kostenbasis dieses Verkaufs ein.
          Historisch ersetzte Buchungen werden nicht zusätzlich gezählt.
        </p>
        {showFullHistory && (
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
        <summary className="cursor-pointer">Identitäten und verwendete Währungsbelege</summary>
        <p className="mt-2 break-all">
          Trade {item.trade_id} · Produkt {item.product_id} · SELL {item.execution_id}
        </p>
        <p>Produktname ist die heutige Stammdatenanzeige und kein historischer Währungsbeleg.</p>
        <p>
          Ursprung:{' '}
          {item.origin === 'WORKSPACE_SELECTION'
            ? 'Eigener Trade aus Produktauswahl'
            : 'Als eigener Trade erfasste externe Quelle'}
          .
        </p>
        <ul className="mt-2 list-inside list-disc break-all">
          {item.currency_confirmation_ids.map((id) => (
            <li key={id}>Bestätigung {id}</li>
          ))}
        </ul>
      </details>
      <Link
        className="inline-block rounded text-sm text-sky-300 underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
        to={`/trade-management?trade_id=${encodeURIComponent(item.trade_id)}#execution-dates`}
      >
        Buchungen und Währungsbestätigungen im Trade prüfen
      </Link>
    </section>
  );
}
