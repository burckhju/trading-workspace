import { useEffect, useRef, useState } from 'react';

import { tradeManagementApiClient } from '../services/client';
import type { CancellationPreview, TradeResponse } from '../types/api';
import { useTradePendingChanges } from './TradePendingChanges';

interface Props {
  trade: TradeResponse;
  productName: string;
  onChanged: () => Promise<void>;
  isWriteBlocked?: () => boolean;
}
interface Draft {
  reason: string;
  retained: string;
  confirmed: boolean;
}
const emptyDraft = (): Draft => ({ reason: '', retained: '', confirmed: false });

export function TradeCancellationPanel(props: Props) {
  return <TradeCancellationContext key={props.trade.id} {...props} />;
}

function TradeCancellationContext({ trade, productName, onChanged, isWriteBlocked }: Props) {
  const [preview, setPreview] = useState<CancellationPreview | null>(null);
  const [draft, setDraft] = useState(emptyDraft);
  const draftRef = useRef(draft);
  const { reason, retained, confirmed } = draft;
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  const writing = useRef(false);
  const active = useRef(true);
  const generation = useRef(0);
  const [message, setMessage] = useState<string | null>(null);
  const { notify, isBusy, requestChange } = useTradePendingChanges('trade-cancellation', {
    isBusy: () => writing.current,
    isDirty: () =>
      Boolean(draftRef.current.reason || draftRef.current.retained || draftRef.current.confirmed),
    onDiscard: () => resetDraft(),
  });

  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
      generation.current += 1;
    };
  }, []);

  function changeDraft(value: Partial<Draft>) {
    if (writing.current) return;
    draftRef.current = { ...draftRef.current, ...value };
    setDraft(draftRef.current);
    notify();
  }
  function resetDraft() {
    draftRef.current = emptyDraft();
    setDraft(draftRef.current);
  }

  async function inspect() {
    if (lock.current || isBusy() || trade.cancelled_at) return;
    lock.current = true;
    const operation = ++generation.current;
    const current = () => active.current && operation === generation.current;
    setBusy(true);
    setMessage(null);
    setPreview(null);
    resetDraft();
    try {
      const next = await tradeManagementApiClient.cancellationPreview(trade.id);
      if (!current()) return;
      if (next.trade_id !== trade.id || next.product_id !== trade.product_id)
        throw new Error('Die Stornovorschau gehört nicht zu diesem Trade. Bitte erneut prüfen.');
      setPreview(next);
    } catch (error) {
      if (current())
        setMessage(error instanceof Error ? error.message : 'Stornovorschau nicht verfügbar.');
    } finally {
      lock.current = false;
      if (current()) setBusy(false);
    }
  }
  async function cancel() {
    const submitted = draftRef.current;
    if (
      !preview ||
      !preview.can_cancel ||
      !submitted.confirmed ||
      !submitted.reason.trim() ||
      lock.current ||
      isBusy() ||
      isWriteBlocked?.() ||
      trade.cancelled_at
    )
      return;
    lock.current = true;
    writing.current = true;
    notify();
    const operation = ++generation.current;
    const current = () => active.current && operation === generation.current;
    setBusy(true);
    setMessage(null);
    let saved = false;
    try {
      await tradeManagementApiClient.cancel(trade.id, {
        expected_product_id: preview.product_id,
        expected_state_token: preview.state_token,
        reason: submitted.reason.trim(),
        confirmed: true,
        duplicate_of_trade_id: submitted.retained || null,
      });
      if (!current()) return;
      saved = true;
      setPreview(null);
      resetDraft();
      await onChanged();
      if (current())
        setMessage(
          'Fehleingabe storniert. Kein Verkauf, keine Broker-Order. Die Historie bleibt erhalten.',
        );
    } catch (error) {
      if (current()) {
        const detail = error instanceof Error ? error.message : 'Stornierung bitte prüfen.';
        setMessage(
          saved
            ? `Stornierung gespeichert, Ansicht noch nicht aktualisiert. Bitte neu laden. ${detail}`
            : detail,
        );
        setPreview(null);
        draftRef.current = { ...draftRef.current, confirmed: false };
        setDraft(draftRef.current);
      }
    } finally {
      lock.current = false;
      writing.current = false;
      if (current()) {
        setBusy(false);
        notify();
      }
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
          disabled={busy || isBusy()}
          onClick={() => requestChange(() => void inspect())}
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
                  disabled={busy}
                  maxLength={1000}
                  onChange={(e) => changeDraft({ reason: e.target.value })}
                  className="mt-1 block w-full rounded border bg-slate-950 p-2"
                />
              </label>
              {preview.other_open_trade_ids.length > 0 && (
                <label className="block">
                  Bei Doppelbuchung: beizubehaltender Trade
                  <select
                    aria-label="Beizubehaltender Trade"
                    value={retained}
                    disabled={busy}
                    onChange={(e) => changeDraft({ retained: e.target.value })}
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
                  disabled={busy}
                  onChange={(e) => changeDraft({ confirmed: e.target.checked })}
                />{' '}
                Ich bestätige, dass genau dieser Trade eine Fehleingabe ist.
              </label>
              <button
                type="button"
                disabled={busy || isBusy() || isWriteBlocked?.() || !confirmed || !reason.trim()}
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
            onClick={() =>
              requestChange(() => {
                setPreview(null);
                resetDraft();
              })
            }
            className="ml-3 rounded border p-2"
          >
            Abbrechen
          </button>
        </div>
      )}
    </section>
  );
}
