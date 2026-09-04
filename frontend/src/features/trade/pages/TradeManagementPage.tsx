import { FormEvent, useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { TradeAlertsPanel } from '../../alert/components/TradeAlertsPanel';
import { postTradeApiClient } from '../../post_trade/services/client';
import { postTradeErrorMessage } from '../../post_trade/services/errors';
import { warrantApiClient } from '../../product/services/client';
import type { WarrantResponse } from '../../product/types/api';
import { tradeManagementApiClient } from '../services/client';
import type {
  PositionResponse,
  TradeManagementStateResponse,
  TradeResponse,
} from '../types/api';

function formatNumber(value: string): string {
  return new Intl.NumberFormat('de-DE', {
    maximumFractionDigits: 10,
  }).format(Number(value));
}

function formatDateTime(value: string | null): string {
  return value ? new Date(value).toLocaleString('de-DE') : '—';
}

function tradeReference(id: string): string {
  return `TR-${id.slice(0, 8).toUpperCase()}`;
}

function tradePlanReference(id: string): string {
  return `TP-${id.slice(0, 8).toUpperCase()}`;
}

export function TradeManagementPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [lookupId, setLookupId] = useState(searchParams.get('trade_id') ?? '');
  const [tradeId, setTradeId] = useState(searchParams.get('trade_id') ?? '');
  const [trade, setTrade] = useState<TradeResponse | null>(null);
  const [warrant, setWarrant] = useState<WarrantResponse | null>(null);
  const [position, setPosition] = useState<PositionResponse | null>(null);
  const [management, setManagement] = useState<TradeManagementStateResponse | null>(null);
  const [saleQuantity, setSaleQuantity] = useState('');
  const [salePrice, setSalePrice] = useState('');
  const [stopPrice, setStopPrice] = useState('');
  const [targetPrice, setTargetPrice] = useState('');
  const [thesis, setThesis] = useState('');
  const [note, setNote] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function refresh(id: string, signal?: AbortSignal) {
    const [nextTrade, nextPosition, nextManagement] = await Promise.all([
      tradeManagementApiClient.trade(id, signal),
      tradeManagementApiClient.position(id, signal),
      tradeManagementApiClient.managementState(id, signal),
    ]);
    const nextWarrant = await warrantApiClient.get(nextTrade.product_id, signal);
    setTrade(nextTrade);
    setWarrant(nextWarrant);
    setPosition(nextPosition);
    setManagement(nextManagement);
    setStopPrice(nextManagement.stop_price ?? '');
    setTargetPrice(nextManagement.target_price ?? '');
    setThesis(nextManagement.thesis ?? '');
  }

  useEffect(() => {
    if (!tradeId) return undefined;
    const controller = new AbortController();
    setBusy(true);
    setMessage(null);
    refresh(tradeId, controller.signal)
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setMessage(error instanceof Error ? error.message : 'Trade konnte nicht geladen werden.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setBusy(false);
      });
    return () => controller.abort();
  }, [tradeId]);

  function lookupTrade(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const id = lookupId.trim();
    if (!id) return;
    setSearchParams({ trade_id: id });
    setTradeId(id);
  }

  async function mutate(action: () => Promise<unknown>, successMessage: string) {
    if (!tradeId) return;
    setBusy(true);
    setMessage(null);
    try {
      await action();
      await refresh(tradeId);
      setMessage(successMessage);
    } catch (error: unknown) {
      setMessage(
        error instanceof Error ? error.message : 'Änderung konnte nicht gespeichert werden.',
      );
    } finally {
      setBusy(false);
    }
  }

  async function startPostTradeObservation() {
    if (!tradeId || !position?.is_closed) return;

    setBusy(true);
    setMessage(null);

    try {
      await postTradeApiClient.startObservation(tradeId);
      void navigate(`/post-trade?trade_id=${encodeURIComponent(tradeId)}`);
    } catch (error: unknown) {
      setMessage(postTradeErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function recordSale(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const quantity = Number(saleQuantity);
    if (!Number.isInteger(quantity) || quantity <= 0 || !salePrice) return;

    await mutate(
      () =>
        tradeManagementApiClient.sell(tradeId, {
          quantity,
          price_per_unit: salePrice,
        }),
      'Verkauf wurde erfasst und die Position neu projiziert.',
    );
    setSaleQuantity('');
    setSalePrice('');
  }

  return (
    <main className="space-y-6">
      <header>
        <p className="text-xs uppercase tracking-wide text-slate-500">FT-010</p>
        <h1 className="mt-1 text-2xl font-semibold">Trade Management</h1>
        <p className="mt-2 text-sm text-slate-400">
          Position, wirtschaftliche SELL-Executions und Management-Entscheidungen bleiben getrennte
          fachliche Fakten.
        </p>
      </header>

      <form onSubmit={lookupTrade} className="rounded-xl border border-slate-800 p-5">
        <label className="block text-sm font-medium" htmlFor="trade-id">
          Trade-ID
        </label>
        <div className="mt-2 flex flex-col gap-2 sm:flex-row">
          <input
            id="trade-id"
            value={lookupId}
            onChange={(event) => setLookupId(event.target.value)}
            className="min-w-0 flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
            placeholder="UUID des Trades"
          />
          <button
            type="submit"
            disabled={busy || lookupId.trim() === ''}
            className="rounded-lg border border-slate-600 px-4 py-2 disabled:opacity-50"
          >
            Laden
          </button>
        </div>
      </form>

      {message && (
        <div role="status" className="rounded-xl border border-slate-700 bg-slate-900 p-4 text-sm">
          {message}
        </div>
      )}

      {trade && warrant && position && (
        <section className="rounded-xl border border-sky-900 bg-sky-950/20 p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-sky-400">Aktiver Trade</p>
              <h2 className="mt-1 text-xl font-semibold">
                {tradeReference(trade.id)} · {warrant.display_name}
              </h2>
              <p className="mt-1 text-sm text-slate-400">
                {warrant.isin ? `ISIN ${warrant.isin}` : 'Keine ISIN'}
                {warrant.wkn ? ` · WKN ${warrant.wkn}` : ''}
              </p>
            </div>
            <span className="rounded-full border border-sky-800 px-3 py-1 text-xs">
              {position.is_closed ? 'CLOSED' : 'OPEN'}
            </span>
          </div>
          <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <dt className="text-slate-500">Ursprung</dt>
              <dd className="mt-1 font-medium">
                {trade.origin === 'WORKSPACE_SELECTION' ? 'Workspace-Produktauswahl' : 'Extern'}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">TradePlan</dt>
              <dd className="mt-1 font-medium">
                {trade.trade_plan_id ? tradePlanReference(trade.trade_plan_id) : 'Kein TradePlan'}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Offene Menge</dt>
              <dd className="mt-1 font-medium">{position.open_quantity}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Nächster Schritt</dt>
              <dd className="mt-1 font-medium">
                {position.is_closed
                  ? 'Nachbeobachtung starten'
                  : 'Alerts prüfen und Stop/Target aktiv managen'}
              </dd>
            </div>
          </dl>
          <details className="mt-4 text-xs text-slate-500">
            <summary className="cursor-pointer">Technische Provenance anzeigen</summary>
            <div className="mt-2 space-y-1 break-all">
              <p>Trade-ID {trade.id}</p>
              <p>Produkt-ID {trade.product_id}</p>
              {trade.trade_plan_id && <p>TradePlan-ID {trade.trade_plan_id}</p>}
              {trade.trade_plan_version_id && <p>TradePlanVersion-ID {trade.trade_plan_version_id}</p>}
              {trade.product_selection_id && <p>ProductSelection-ID {trade.product_selection_id}</p>}
            </div>
          </details>
        </section>
      )}

      {position && (
        <>
          <section className="rounded-xl border border-slate-800 p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Position</p>
                <h2 className="mt-1 text-lg font-semibold">
                  {position.is_closed ? 'CLOSED' : 'OPEN'}
                </h2>
              </div>
              <span className="rounded-full border border-slate-700 px-3 py-1 text-xs">
                {position.open_quantity} offen
              </span>
            </div>
            <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <dt className="text-slate-500">Cost Basis</dt>
                <dd className="mt-1 font-medium">{formatNumber(position.cost_basis)}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Average Entry</dt>
                <dd className="mt-1 font-medium">{formatNumber(position.average_entry_price)}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Realized gross P&amp;L</dt>
                <dd className="mt-1 font-medium">{formatNumber(position.realized_gross_pnl)}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Closed at</dt>
                <dd className="mt-1 font-medium">{formatDateTime(position.closed_at)}</dd>
              </div>
            </dl>
          </section>

          <TradeAlertsPanel tradeId={tradeId} />

          <form
            onSubmit={(event) => void recordSale(event)}
            className="rounded-xl border border-slate-800 p-5"
          >
            <h2 className="text-lg font-semibold">SELL erfassen</h2>
            <p className="mt-1 text-xs text-slate-500">
              Partial und Full Exit werden aus Menge und aktueller effektiver Execution-Historie
              abgeleitet.
            </p>
            {position.is_closed ? (
              <div className="mt-4 space-y-3">
                <p className="text-sm text-slate-400">
                  Die Position ist geschlossen. Weitere SELL-Executions sind nicht verfügbar.
                </p>

                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void startPostTradeObservation()}
                  className="rounded-lg border border-emerald-700 px-4 py-2 disabled:opacity-50"
                >
                  Nachbeobachtung starten
                </button>
              </div>
            ) : (
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <label className="text-sm">
                  <span className="text-slate-400">Menge</span>
                  <input
                    aria-label="Verkaufsmenge"
                    type="number"
                    min="1"
                    max={position.open_quantity}
                    step="1"
                    value={saleQuantity}
                    onChange={(event) => setSaleQuantity(event.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
                  />
                </label>
                <label className="text-sm">
                  <span className="text-slate-400">Preis je Einheit</span>
                  <input
                    aria-label="Verkaufspreis"
                    type="number"
                    min="0"
                    step="any"
                    value={salePrice}
                    onChange={(event) => setSalePrice(event.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
                  />
                </label>
                <button
                  type="submit"
                  disabled={busy || saleQuantity === '' || salePrice === ''}
                  className="rounded-lg border border-slate-600 px-4 py-2 sm:col-span-2 disabled:opacity-50"
                >
                  SELL speichern
                </button>
              </div>
            )}
          </form>
        </>
      )}

      {management && position && (
        <section className="rounded-xl border border-slate-800 p-5">
          <h2 className="text-lg font-semibold">Aktueller Management-Zustand</h2>
          <p className="mt-1 text-xs text-slate-500">
            Abgeleitet aus der effektiven Management-Event-Historie; der ursprüngliche TradePlan
            wird nicht verändert.
          </p>

          <div className="mt-5 grid gap-5 lg:grid-cols-2">
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void mutate(
                  () => tradeManagementApiClient.changeStop(tradeId, { price: stopPrice }),
                  'Stop wurde aktualisiert.',
                );
              }}
              className="space-y-2"
            >
              <label className="block text-sm" htmlFor="stop-price">
                Stop
              </label>
              <input
                id="stop-price"
                type="number"
                min="0"
                step="any"
                required
                value={stopPrice}
                onChange={(event) => setStopPrice(event.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
              />
              <button disabled={busy} className="rounded-lg border border-slate-600 px-3 py-2">
                Stop speichern
              </button>
            </form>

            <form
              onSubmit={(event) => {
                event.preventDefault();
                void mutate(
                  () => tradeManagementApiClient.changeTarget(tradeId, { price: targetPrice }),
                  'Target wurde aktualisiert.',
                );
              }}
              className="space-y-2"
            >
              <label className="block text-sm" htmlFor="target-price">
                Target
              </label>
              <input
                id="target-price"
                type="number"
                min="0"
                step="any"
                required
                value={targetPrice}
                onChange={(event) => setTargetPrice(event.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
              />
              <button disabled={busy} className="rounded-lg border border-slate-600 px-3 py-2">
                Target speichern
              </button>
            </form>

            <form
              onSubmit={(event) => {
                event.preventDefault();
                void mutate(
                  () => tradeManagementApiClient.updateThesis(tradeId, { text: thesis }),
                  'These wurde aktualisiert.',
                );
              }}
              className="space-y-2 lg:col-span-2"
            >
              <label className="block text-sm" htmlFor="thesis">
                Aktuelle These
              </label>
              <textarea
                id="thesis"
                required
                maxLength={4000}
                value={thesis}
                onChange={(event) => setThesis(event.target.value)}
                className="min-h-28 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
              />
              <button disabled={busy} className="rounded-lg border border-slate-600 px-3 py-2">
                These speichern
              </button>
            </form>

            <form
              onSubmit={(event) => {
                event.preventDefault();
                const text = note.trim();
                if (!text) return;
                void mutate(
                  () => tradeManagementApiClient.addNote(tradeId, { text }),
                  'Management-Notiz wurde hinzugefügt.',
                ).then(() => setNote(''));
              }}
              className="space-y-2 lg:col-span-2"
            >
              <label className="block text-sm" htmlFor="management-note">
                Neue Management-Notiz
              </label>
              <textarea
                id="management-note"
                required
                maxLength={4000}
                value={note}
                onChange={(event) => setNote(event.target.value)}
                className="min-h-24 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
              />
              <button disabled={busy} className="rounded-lg border border-slate-600 px-3 py-2">
                Notiz hinzufügen
              </button>
            </form>
          </div>

          <div className="mt-6">
            <h3 className="font-medium">Management-Notizen</h3>
            {management.notes.length === 0 ? (
              <p className="mt-2 text-sm text-slate-400">Noch keine Management-Notizen.</p>
            ) : (
              <ol className="mt-3 space-y-2">
                {management.notes.map((item, index) => (
                  <li
                    key={`${index}-${item}`}
                    className="rounded-lg border border-slate-800 p-3 text-sm"
                  >
                    {item}
                  </li>
                ))}
              </ol>
            )}
          </div>
        </section>
      )}
    </main>
  );
}
