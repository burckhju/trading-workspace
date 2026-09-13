import { Link } from 'react-router-dom';
import { purchaseLabels } from '../services/purchaseStatus';
import type { PurchaseStatus, TradePlanOverviewItem } from '../services/overviewClient';

const colors: Record<PurchaseStatus, string> = {
  NOT_STARTED: 'border-slate-600 bg-slate-800 text-slate-200',
  OPEN: 'border-emerald-700 bg-emerald-950/30 text-emerald-200',
  CLOSED: 'border-sky-700 bg-sky-950/30 text-sky-200',
  CANCELLED: 'border-amber-700 bg-amber-950/30 text-amber-200',
  UNKNOWN: 'border-amber-700 bg-amber-950/30 text-amber-200',
};
function dateLabel(day: string | null, time: string | null): string {
  if (day) return day.split('-').reverse().join('.');
  return time && Number.isFinite(Date.parse(time))
    ? new Date(time).toLocaleDateString('de-DE')
    : 'unbekannt';
}

export function PlanPurchaseStatus({ item }: { item: TradePlanOverviewItem }) {
  const progress = item.execution;
  const status = progress?.status ?? 'UNKNOWN';
  const trades = progress?.trades ?? [];
  const open = trades.filter((trade) => trade.status === 'OPEN').length;
  const cancelled = trades.filter((trade) => trade.status === 'CANCELLED').length;
  const unknown = trades.filter((trade) => trade.status === 'UNKNOWN').length;
  return (
    <section
      aria-label="Kaufstatus"
      className="mt-4 space-y-3 rounded-lg border border-slate-700 p-3"
    >
      <p className="text-xs text-slate-400">Kaufstatus · alle Planversionen</p>
      <p>
        <span className={`inline-flex rounded-md border px-3 py-1 text-sm ${colors[status]}`}>
          {purchaseLabels[status]}
        </span>
      </p>
      {!progress && (
        <p className="text-sm text-amber-200">
          Keine Kaufstatusdaten verfügbar. Backend aktualisieren und Übersicht neu laden.
        </p>
      )}
      {trades.some((trade) => trade.trade_plan_version_id !== item.latest_version_id) && (
        <p className="text-sm text-slate-300">
          Aktuelle Version {item.latest_version}: {purchaseLabels[progress!.current_version_status]}
          . Frühere Versionen bleiben unten separat zugeordnet.
        </p>
      )}
      {trades.length > 1 && (
        <p className="text-sm text-slate-300">
          {open} offen · {trades.filter((trade) => trade.status === 'CLOSED').length} abgeschlossen
          · {cancelled} storniert{unknown > 0 ? ` · ${unknown} ungeklärt` : ''}
        </p>
      )}
      {unknown > 0 && (
        <p className="text-sm text-amber-200">
          Bei einem zugeordneten Trade fehlen konsistente Kauf-/Positionsdaten. Trade prüfen.
        </p>
      )}
      {trades.map((trade) => (
        <div key={trade.trade_id} className="space-y-1 border-t border-slate-700 pt-2 text-sm">
          <p className="break-words font-medium">
            {trade.product_name ?? 'Produktname nicht verfügbar'} · Planversion{' '}
            {trade.plan_version ?? 'unbekannt'}
          </p>
          <p className="break-words text-xs text-slate-400">
            WKN {trade.product_wkn ?? '—'} · ISIN {trade.product_isin ?? '—'}
          </p>
          <p>
            {purchaseLabels[trade.status]} · Kaufdatum:{' '}
            {dateLabel(trade.purchased_on, trade.purchased_at)}
          </p>
          {trade.status === 'OPEN' && (
            <p>Offene Stückzahl: {trade.open_quantity?.toLocaleString('de-DE')}</p>
          )}
          {trade.status === 'CLOSED' && (
            <p>Vollständig verkauft: {dateLabel(trade.closed_on, trade.closed_at)}</p>
          )}
          {trade.status === 'CANCELLED' && (
            <p className="text-amber-200">
              Stornierte Fehleingabe; zählt nicht als offene Position.
            </p>
          )}
          <Link
            to={`/trade-management?trade_id=${encodeURIComponent(trade.trade_id)}`}
            className="inline-flex rounded text-sky-200 underline underline-offset-4 focus-visible:outline-2"
          >
            {trade.status === 'OPEN' ? 'Trade verwalten / Nachkauf' : 'Trade und Historie öffnen'}
          </Link>
          <p className="break-all text-xs text-slate-500">Trade-ID: {trade.trade_id}</p>
        </div>
      ))}
    </section>
  );
}
