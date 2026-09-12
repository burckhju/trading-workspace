import { useRef, useState } from 'react';

import { captureRequest, executionTime, finishCapture, localToday } from '../services/capture';
import { tradeManagementApiClient } from '../services/client';
import { ExecutionDateInput } from './ExecutionDateInput';

export function AdditionalPurchasePanel({
  tradeId,
  onChanged,
}: {
  tradeId: string;
  onChanged: () => Promise<void>;
}) {
  const [quantity, setQuantity] = useState('');
  const [price, setPrice] = useState('');
  const [date, setDate] = useState(localToday);
  const [time, setTime] = useState('');
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  const [message, setMessage] = useState<string | null>(null);
  async function submit() {
    if (lock.current) return;
    const amount = Number(quantity);
    if (!Number.isInteger(amount) || amount <= 0 || !price.trim()) return;
    lock.current = true;
    setBusy(true);
    setMessage(null);
    const scope = `additional:${tradeId}`;
    try {
      const payload = {
        quantity: amount,
        price_per_unit: price.trim().replace(',', '.'),
        ...executionTime(date, time),
      };
      await tradeManagementApiClient.purchaseAdditional(tradeId, {
        ...payload,
        request_id: captureRequest(scope, payload),
      });
      finishCapture(scope);
      setQuantity('');
      setPrice('');
      setTime('');
      await onChanged();
      setMessage('Nachkauf beim bestehenden Trade erfasst.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Nachkauf fehlgeschlagen.');
    } finally {
      setBusy(false);
      lock.current = false;
    }
  }
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
      className="rounded-xl border border-slate-800 p-5"
    >
      <h2 className="text-lg font-semibold">Nachkauf erfassen</h2>
      <p className="mt-2 text-sm text-slate-400">
        Ein tatsächlicher weiterer Kauf wird diesem offenen Trade zugeordnet. Kein zweiter Trade und
        keine Broker-Order.
      </p>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <label>
          Nachkaufmenge
          <input
            aria-label="Nachkaufmenge"
            required
            type="number"
            min="1"
            step="1"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            className="block w-full rounded border bg-slate-950 p-2"
          />
        </label>
        <label>
          Nachkaufpreis
          <input
            aria-label="Nachkaufpreis"
            required
            type="number"
            min="0"
            step="any"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            className="block w-full rounded border bg-slate-950 p-2"
          />
        </label>
        <ExecutionDateInput
          label="Nachkaufdatum"
          date={date}
          time={time}
          onDate={setDate}
          onTime={setTime}
        />
      </div>
      <button disabled={busy} className="mt-3 rounded border p-2">
        Nachkauf speichern
      </button>
      {message && (
        <p role="status" className="mt-3">
          {message}
        </p>
      )}
    </form>
  );
}
