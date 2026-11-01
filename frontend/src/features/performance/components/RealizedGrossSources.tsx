import { useId, useState } from 'react';

import { NoticeCard } from '../../../shared/notices';
import type { RealizedReportContext } from '../services/performanceReportContext';
import { moneyText } from '../services/presentation';
import { buildRealizedCurrencyNotice } from '../services/realizedCurrencyNotice';
import type { RealizedGrossItem, RealizedGrossReport } from '../types/api';
import { ReportCurrencyEvidence } from './ReportCurrencyEvidence';
import { ReportSourceEntry } from './ReportSourceEntry';

export function RealizedGrossSources({
  item,
  report,
  context,
}: {
  item: RealizedGrossItem;
  report: RealizedGrossReport;
  context: RealizedReportContext;
}) {
  const [showFullHistory, setShowFullHistory] = useState(false);
  const detailsId = useId();
  const notice = buildRealizedCurrencyNotice(item, report, context);
  if (!notice) {
    return (
      <section
        aria-label="Herkunft nicht zuordenbar"
        className="mt-4 rounded-lg border border-slate-700 p-4 text-sm"
      >
        Die ausgewählte Buchung und der Berichtskontext passen nicht zusammen. Die Herkunft kann in
        dieser Ansicht nicht zugeordnet werden.
      </section>
    );
  }
  const tradeSources = report.sources.filter(
    (source) => source.trade_id === item.trade_id && source.product_id === item.product_id,
  );
  const byId = new Map<string, (typeof tradeSources)[number] | null>();
  for (const source of report.sources) {
    byId.set(source.execution_id, byId.has(source.execution_id) ? null : source);
  }
  const sourceIds = [...new Set(tradeSources.map((source) => source.execution_id))];
  const sourceEntry = (id: string) => {
    const source = byId.get(id);
    return source && source.trade_id === item.trade_id && source.product_id === item.product_id ? (
      <ReportSourceEntry
        key={id}
        source={source}
        timezone={report.filters.report_timezone}
        currencyPresentation={<ReportCurrencyEvidence source={source} />}
        priceCurrency={source.currency_resolution?.currency_code ?? null}
      />
    ) : (
      <li key={id} className="rounded-lg border border-slate-700 p-3 text-sm">
        <p>Eine Buchungsquelle ist in dieser Antwort nicht eindeutig zugeordnet.</p>
        <details className="mt-2 min-w-0 text-xs text-slate-400">
          <summary className="cursor-pointer rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400">
            Quellenreferenz
          </summary>
          <p className="mt-2 break-words [overflow-wrap:anywhere]">Buchung {id}</p>
        </details>
      </li>
    );
  };
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
      <NoticeCard notice={notice} headingLevel={4} detailsId={detailsId} />
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
        {prefixIds.map(sourceEntry)}
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
            {sourceIds.map(sourceEntry)}
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
    </section>
  );
}
