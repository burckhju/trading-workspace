import { useState } from 'react';
import { Link } from 'react-router-dom';

import { ExecutionCurrencySources } from '../../trade/components/ExecutionCurrencySources';
import { executionCurrencyText } from '../../trade/services/executionCurrency';
import { executionTimeText, moneyText } from '../services/presentation';
import type { RealizedGrossItem, RealizedGrossReport, RealizedGrossSource } from '../types/api';

function SourceEntry({ source, timezone }: { source: RealizedGrossSource; timezone: string }) {
  const confirmation = source.currency_confirmation;
  return (
    <li
      aria-label={`Buchungsquelle ${source.execution_id}`}
      className="min-w-0 rounded-lg border border-slate-700 p-3"
    >
      <div className="flex flex-wrap justify-between gap-2">
        <p className="font-medium">
          {source.side} · {source.quantity} Stück
        </p>
        <span className="text-xs text-slate-400">
          {source.is_effective ? 'wirksam' : 'historisch ersetzt'}
        </span>
      </div>
      <p className="mt-1 text-sm">Ausgeführt: {executionTimeText(source, timezone)}</p>
      <p className="mt-1 text-sm">
        Gespeicherter Stückpreis: <code>{source.price_per_unit ?? 'unbekannt'}</code>{' '}
        {source.currency_resolution?.currency_code ??
          confirmation?.currency_code ??
          '· Ausführungswährung unbekannt'}
      </p>
      <p className="mt-1 text-xs text-slate-400">
        Erfasst: {source.recorded_at} · durch {source.recorded_by}
      </p>
      <p className="mt-1 break-all text-xs text-slate-400">
        Buchung {source.execution_id} · Produkt {source.product_id}
      </p>
      {source.supersedes_execution_id && (
        <p className="mt-1 break-all text-xs text-amber-300">
          Ersetzt Buchung {source.supersedes_execution_id}
        </p>
      )}
      {source.superseded_by_execution_id && (
        <p className="mt-1 break-all text-xs text-amber-300">
          Ersetzt durch {source.superseded_by_execution_id}; zählt nicht zusätzlich.
        </p>
      )}
      <div className="mt-3 border-t border-slate-800 pt-2 text-sm">
        {confirmation ? (
          <>
            <p>Währung {confirmation.currency_code} ausdrücklich vom Nutzer bestätigt.</p>
            <p className="text-xs text-slate-400">
              Bestätigt: {confirmation.confirmed_at} · durch {confirmation.confirmed_by}
            </p>
            {confirmation.note && <p>Beleg / Erläuterung: {confirmation.note}</p>}
            <p className="break-all text-xs text-slate-400">Bestätigung {confirmation.id}</p>
          </>
        ) : (
          <p>Ausführungswährung: {executionCurrencyText(source.currency_resolution)}</p>
        )}
        <ExecutionCurrencySources resolution={source.currency_resolution} />
        {source.currency_history.length > 0 && (
          <details className="mt-2">
            <summary className="cursor-pointer">
              Währungshistorie ({source.currency_history.length})
            </summary>
            <ol className="mt-2 space-y-2">
              {source.currency_history.map((entry) => (
                <li key={entry.id} className="break-words border-l border-slate-700 pl-3 text-xs">
                  <p>
                    {entry.currency_code} ·{' '}
                    {entry.id === confirmation?.id ? 'aktuell' : 'historisch ersetzt'} ·
                    ausdrücklich bestätigt
                  </p>
                  <p>
                    {entry.confirmed_at} · durch {entry.confirmed_by}
                  </p>
                  {entry.note && <p>{entry.note}</p>}
                  <p className="break-all">Bestätigung {entry.id}</p>
                  {entry.supersedes_confirmation_id && (
                    <p className="break-all">Ersetzt {entry.supersedes_confirmation_id}</p>
                  )}
                </li>
              ))}
            </ol>
          </details>
        )}
      </div>
      {source.time_precision === 'DATE_ONLY' && (
        <details className="mt-2 text-xs text-slate-400">
          <summary className="cursor-pointer">Datumspräzision</summary>
          <p>
            Das gespeicherte Kalenderdatum und seine Zeitzone bleiben erhalten. Es ist keine
            tatsächliche Ausführungsuhrzeit bekannt.
          </p>
          <p>
            Möglicher Zeitbereich: {source.possible_start_at ?? 'unbekannt'} bis ausschließlich{' '}
            {source.possible_end_at ?? 'unbekannt'}.
          </p>
        </details>
      )}
    </li>
  );
}

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
            <SourceEntry key={id} source={source} timezone={report.filters.report_timezone} />
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
              <SourceEntry
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
