import { useEffect, useRef, useState } from 'react';

import { captureRequest, executionTime, finishCapture, localToday } from '../services/capture';
import { tradeManagementApiClient } from '../services/client';
import {
  emptyExecutionCurrency,
  executionCurrencyDeclaration,
  type ExecutionCurrencyDraft,
} from '../services/executionCurrency';
import { ExecutionCurrencyOverride } from './ExecutionCurrencyOverride';
import { ExecutionDateInput } from './ExecutionDateInput';
import { useTradePendingChanges } from './TradePendingChanges';

interface Props {
  tradeId: string;
  onChanged: () => Promise<void>;
  isWriteBlocked?: () => boolean;
}
interface Draft {
  quantity: string;
  price: string;
  date: string;
  time: string;
  currency: ExecutionCurrencyDraft;
}

export function AdditionalPurchasePanel(props: Props) {
  return <AdditionalPurchaseContext key={props.tradeId} {...props} />;
}

function AdditionalPurchaseContext({ tradeId, onChanged, isWriteBlocked }: Props) {
  const [draft, setDraft] = useState<Draft>(() => ({
    quantity: '',
    price: '',
    date: localToday(),
    time: '',
    currency: emptyExecutionCurrency(),
  }));
  const draftRef = useRef(draft);
  const initialDate = useRef(draft.date);
  const { quantity, price, date, time, currency } = draft;
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  const active = useRef(true);
  const [message, setMessage] = useState<string | null>(null);
  const { notify, isBusy } = useTradePendingChanges('additional-purchase', {
    isBusy: () => lock.current,
    isDirty: () => {
      const value = draftRef.current;
      return Boolean(
        value.quantity ||
          value.price ||
          value.date !== initialDate.current ||
          value.time ||
          value.currency.code ||
          value.currency.note,
      );
    },
    onDiscard: () => resetDraft(),
  });

  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
    };
  }, []);

  function changeDraft(value: Partial<Draft>) {
    if (lock.current) return;
    draftRef.current = { ...draftRef.current, ...value };
    setDraft(draftRef.current);
    notify();
  }
  function resetDraft() {
    draftRef.current = {
      quantity: '',
      price: '',
      date: initialDate.current,
      time: '',
      currency: emptyExecutionCurrency(),
    };
    setDraft(draftRef.current);
  }

  async function submit() {
    if (lock.current || isBusy() || isWriteBlocked?.()) return;
    const submitted = draftRef.current;
    const amount = Number(submitted.quantity);
    if (!Number.isInteger(amount) || amount <= 0 || !submitted.price.trim()) return;
    lock.current = true;
    notify();
    setBusy(true);
    setMessage(null);
    const scope = `additional:${tradeId}`;
    let saved = false;
    try {
      const payload = {
        quantity: amount,
        price_per_unit: submitted.price.trim().replace(',', '.'),
        ...executionTime(submitted.date, submitted.time),
        ...executionCurrencyDeclaration(submitted.currency),
      };
      await tradeManagementApiClient.purchaseAdditional(tradeId, {
        ...payload,
        request_id: captureRequest(scope, payload),
      });
      if (!active.current) return;
      finishCapture(scope);
      saved = true;
      initialDate.current = submitted.date;
      resetDraft();
      await onChanged();
      if (active.current) setMessage('Nachkauf beim bestehenden Trade erfasst.');
    } catch (error) {
      if (active.current) {
        const detail = error instanceof Error ? error.message : 'Nachkauf bitte prüfen.';
        setMessage(
          saved
            ? `Nachkauf gespeichert, Ansicht noch nicht aktualisiert. Bitte neu laden. ${detail}`
            : detail,
        );
      }
    } finally {
      lock.current = false;
      if (active.current) {
        setBusy(false);
        notify();
      }
    }
  }
  return (
    <form
      aria-label="Nachkauf erfassen"
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
      <fieldset disabled={busy} className="mt-4 grid min-w-0 gap-3 sm:grid-cols-3">
        <label>
          Nachkaufmenge
          <input
            aria-label="Nachkaufmenge"
            required
            type="number"
            min="1"
            step="1"
            value={quantity}
            onChange={(e) => changeDraft({ quantity: e.target.value })}
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
            onChange={(e) => changeDraft({ price: e.target.value })}
            className="block w-full rounded border bg-slate-950 p-2"
          />
        </label>
        <ExecutionDateInput
          label="Nachkaufdatum"
          date={date}
          time={time}
          onDate={(value) => changeDraft({ date: value })}
          onTime={(value) => changeDraft({ time: value })}
        />
      </fieldset>
      <ExecutionCurrencyOverride
        value={currency}
        onChange={(value) => changeDraft({ currency: value })}
        disabled={busy}
      />
      <button disabled={busy || isBusy() || isWriteBlocked?.()} className="mt-3 rounded border p-2">
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
