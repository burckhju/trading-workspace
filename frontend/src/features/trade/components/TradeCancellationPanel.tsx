import { useRef, useState } from 'react';

import { tradeManagementApiClient } from '../services/client';
import type { CancellationPreview, TradeResponse } from '../types/api';

export function TradeCancellationPanel({
  trade,
  productName,
  onChanged,
}: {
  trade: TradeResponse;
  productName: string;
  onChanged: () => Promise<void>;
}) {
  const [preview, setPreview] = useState<CancellationPreview | null>(null);
  const [reason, setReason] = useState('');
  const [retained, setRetained] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  const [message, setMessage] = useState<string | null>(null);

  async function inspect() {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setMessage(null);
    setPreview(null);
    setConfirmed(false);
    setRetained('');
    try {
      setPreview(await tradeManagementApiClient.cancellationPreview(trade.id));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Stornovorschau nicht verfügbar.');
    } finally {
      setBusy(false);
      lock.current = false;
    }
  }
  async function cancel() {
    if (!preview || !confirmed || !reason.trim() || lock.current) return;
    lock.current = true;
    setBusy(true);
    setMessage(null);
    try {
      await tradeManagementApiClient.cancel(trade.id, {
        expected_product_id: preview.product_id,
        expected_state_token: preview.state_token,
        reason: reason.trim(),
        confirmed: true,
        duplicate_of_trade_id: retained || null,
      });
      setPreview(null);
      setConfirmed(false);
      await onChanged();
      setMessage(
        'Fehleingabe storniert. Kein Verkauf, keine Broker-Order. Die Historie bleibt erhalten.',
      );
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Stornierung fehlgeschlagen.');
      setPreview(null);
      setConfirmed(false);
    } finally {
      setBusy(false);
      lock.current = false;
    }
  }
  return (
    <section className="rounded-xl border border-rose-900 p-5" aria-label="Fehleingabe stornieren">
      <h2 className="text-lg font-semibold">Fehleingabe stornieren</h2>
      <p className="mt-2 text-sm">
        {productName} · Trade {trade.id}
      </p>
      <p className="mt-2 text-sm text-slate-400">
        Nur für einen irrtümlich erfassten Kauf. Kein Verkauf, keine Order und keine Löschung der
        Historie.
      </p>
      {trade.cancelled_at ? (
        <p role="status" className="mt-3 text-amber-300">
          STORNIERT am {new Date(trade.cancelled_at).toLocaleString('de-DE')}:{' '}
          {trade.cancellation_reason}. Dieser Eintrag zählt nicht zum Bestand oder zur
          Gewinn-/Verlustauswertung.
        </p>
      ) : (
        <button
          type="button"
          disabled={busy}
          onClick={() => void inspect()}
          className="mt-3 rounded border border-rose-700 p-2"
        >
          Stornierung prüfen
        </button>
      )}
      {message && (
        <p role="status" className="mt-3">
          {message}
        </p>
      )}
      {preview && !trade.cancelled_at && (
        <div className="mt-4 space-y-3">
          <p>
            Geprüfter Trade: {preview.trade_id} · ursprüngliche offene Menge:{' '}
            {preview.open_quantity} · Einstand gesamt: {preview.cost_basis}
          </p>
          {preview.executions?.map((execution) => (
            <p key={execution.id} className="text-sm text-slate-400">
              {execution.side} · {execution.quantity} Stück · Preis {execution.price_per_unit} ·
              Ausgeführt{' '}
              {execution.executed_on ?? new Date(execution.executed_at).toLocaleString('de-DE')}
              {execution.executed_on && ` (Uhrzeit unbekannt, ${execution.execution_timezone})`} ·
              Erfasst {new Date(execution.recorded_at).toLocaleString('de-DE')}
            </p>
          ))}
          {preview.blockers.map((value) => (
            <p role="alert" key={value}>
              {value}
            </p>
          ))}
          {preview.can_cancel && (
            <>
              <label className="block">
                Stornogrund
                <textarea
                  aria-label="Stornogrund"
                  value={reason}
                  maxLength={1000}
                  onChange={(e) => setReason(e.target.value)}
                  className="mt-1 block w-full rounded border bg-slate-950 p-2"
                />
              </label>
              {preview.other_open_trade_ids.length > 0 && (
                <label className="block">
                  Bei Doppelbuchung: beizubehaltender Trade
                  <select
                    aria-label="Beizubehaltender Trade"
                    value={retained}
                    onChange={(e) => setRetained(e.target.value)}
                    className="mt-1 block w-full rounded border bg-slate-950 p-2"
                  >
                    <option value="">Keine Dubletten-Zuordnung</option>
                    {preview.other_open_trade_ids.map((id) => (
                      <option key={id} value={id}>
                        {id}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              <label className="block">
                <input
                  type="checkbox"
                  checked={confirmed}
                  onChange={(e) => setConfirmed(e.target.checked)}
                />{' '}
                Ich bestätige, dass genau dieser Trade eine Fehleingabe ist.
              </label>
              <button
                type="button"
                disabled={busy || !confirmed || !reason.trim()}
                onClick={() => void cancel()}
                className="rounded border border-rose-700 p-2 disabled:opacity-50"
              >
                Fehleingabe verbindlich stornieren
              </button>
            </>
          )}
          <button
            type="button"
            disabled={busy}
            onClick={() => {
              setPreview(null);
              setConfirmed(false);
            }}
            className="ml-3 rounded border p-2"
          >
            Abbrechen
          </button>
        </div>
      )}
    </section>
  );
}
