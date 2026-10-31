import { useEffect, useState } from 'react';

import { executionTime } from '../services/capture';
import { tradeManagementApiClient } from '../services/client';
import { executionCurrencyText, type ExecutionCurrencyDraft } from '../services/executionCurrency';
import type { ExecutionCurrencyPreviewContext, ExecutionCurrencyResolution } from '../types/api';
import { ExecutionCurrencyOverride } from './ExecutionCurrencyOverride';
import { ExecutionCurrencySources } from './ExecutionCurrencySources';

interface Props {
  context: ExecutionCurrencyPreviewContext;
  date: string;
  time: string;
  value: ExecutionCurrencyDraft;
  onChange: (value: ExecutionCurrencyDraft) => void;
  disabled?: boolean;
  reloadToken?: number;
}

type ReadResult = {
  key: string;
} & (
  | { resolution: ExecutionCurrencyResolution; error?: never }
  | { resolution?: never; error: string }
);

/** A preview only displays owner evidence. It never writes into the user's draft. */
export function ExecutionCurrencyPreview(props: Props) {
  const scope =
    'tradeId' in props.context
      ? `trade:${props.context.tradeId}`
      : `product:${props.context.productId}`;
  // Changing product/trade also resets disclosure state, even for an A → B → A journey.
  return <PreviewContext key={scope} {...props} />;
}

function PreviewContext({
  context,
  date,
  time,
  value,
  onChange,
  disabled = false,
  reloadToken = 0,
}: Props) {
  const tradeId = 'tradeId' in context ? context.tradeId : null;
  const productId = 'productId' in context ? context.productId : null;
  const side = context.side;
  const [revision, setRevision] = useState(0);
  const [result, setResult] = useState<ReadResult | null>(null);
  const key = JSON.stringify([tradeId, productId, side, date, time, revision, reloadToken]);
  const current = result?.key === key ? result : null;
  const resolution = current?.resolution;
  const known =
    Boolean(resolution?.currency_code) &&
    resolution?.source !== 'UNKNOWN' &&
    resolution?.source !== 'MIXED' &&
    resolution?.source !== 'CONFLICT';
  const manual = Boolean(value.code || value.note);

  useEffect(() => {
    const controller = new AbortController();
    async function read() {
      try {
        const queryContext: ExecutionCurrencyPreviewContext =
          tradeId !== null ? { tradeId, side } : { productId: productId!, side: 'BUY' };
        const next = await tradeManagementApiClient.executionCurrencyPreview(
          queryContext,
          executionTime(date, time),
          controller.signal,
        );
        if (controller.signal.aborted) return;
        if (
          !next ||
          !Array.isArray(next.source_execution_ids) ||
          !Array.isArray(next.confirmation_ids)
        ) {
          throw new Error('Die Währungsherkunft konnte nicht vollständig gelesen werden.');
        }
        setResult({ key, resolution: next });
      } catch (error) {
        if (!controller.signal.aborted)
          setResult({
            key,
            error:
              error instanceof Error
                ? error.message
                : 'Die Währungsherkunft konnte nicht gelesen werden.',
          });
      }
    }
    void read();
    return () => controller.abort();
  }, [key, tradeId, productId, side, date, time]);

  useEffect(() => {
    function changed(event: Event) {
      if (tradeId && (event as CustomEvent<{ tradeId?: string }>).detail?.tradeId === tradeId) {
        setRevision((value) => value + 1);
      }
    }
    window.addEventListener('trade-timeline-changed', changed);
    return () => window.removeEventListener('trade-timeline-changed', changed);
  }, [tradeId]);

  return (
    <section aria-label="Währung für diese Ausführung" className="mt-4 space-y-2">
      <ExecutionCurrencyOverride
        value={value}
        onChange={onChange}
        disabled={disabled}
        showInput={Boolean(resolution && !known) || (productId !== null && !known)}
        guidance={
          <div className="space-y-2 text-sm">
            {manual && (
              <p>
                Ihre manuelle Währungsangabe wird erst mit dem Speichern bestätigt und hat Vorrang.
              </p>
            )}
            {!current && (
              <p className="text-slate-400">
                Währungsherkunft für das Ausführungsdatum wird geprüft …
              </p>
            )}
            {current?.error && (
              <div className="space-y-2 text-amber-300">
                <p>Währungsherkunft derzeit nicht geprüft. {current.error}</p>
                <button
                  type="button"
                  disabled={disabled}
                  className="rounded border px-3 py-2"
                  onClick={() => setRevision((value) => value + 1)}
                >
                  Währungsherkunft erneut prüfen
                </button>
              </div>
            )}
            {resolution && (
              <>
                <p className={known ? 'text-slate-200' : 'text-amber-300'}>
                  {known ? 'Vorhandene Währung: ' : 'Währung: '}
                  {executionCurrencyText(resolution)}
                </p>
                <ExecutionCurrencySources resolution={resolution} />
                {!known && (
                  <p className="text-amber-300">
                    Bitte einen passenden historischen Beleg prüfen oder die tatsächliche
                    Ausführungswährung angeben. Ohne Klärung bleibt die Währung unbekannt oder
                    widersprüchlich.
                  </p>
                )}
                {known && (
                  <p className="text-xs text-slate-400">
                    Für dieses Datum aus vorhandenen Quellen ermittelt; beim Speichern wird die
                    Herkunft erneut geprüft. Eine erneute Währungseingabe ist nicht nötig.
                  </p>
                )}
              </>
            )}
          </div>
        }
      />
    </section>
  );
}
