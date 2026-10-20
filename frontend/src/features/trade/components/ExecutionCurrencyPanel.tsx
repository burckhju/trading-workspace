import { useEffect, useRef, useState } from 'react';

import { MarketApiError } from '../../market/services/http';
import { captureRequest, finishCapture } from '../services/capture';
import { tradeManagementApiClient } from '../services/client';
import {
  emptyExecutionCurrency,
  executionCurrencyDeclaration,
  executionCurrencyText,
} from '../services/executionCurrency';
import type {
  ExecutionCurrencyConfirmation,
  ExecutionCurrencyHistory,
  ExecutionCurrencyResolution,
} from '../types/api';
import { ExecutionCurrencyInput } from './ExecutionCurrencyInput';
import { ExecutionCurrencySources } from './ExecutionCurrencySources';

interface Props {
  tradeId: string;
  executionId: string;
  confirmation?: ExecutionCurrencyConfirmation | null;
  resolution?: ExecutionCurrencyResolution | null;
  readOnly?: boolean;
  onChanged?: () => Promise<void>;
}

export function ExecutionCurrencyPanel(props: Props) {
  return <ExecutionCurrencyContext key={`${props.tradeId}:${props.executionId}`} {...props} />;
}

async function readHistory(tradeId: string, executionId: string, signal: AbortSignal) {
  const result = await tradeManagementApiClient.executionCurrencyHistory(
    tradeId,
    executionId,
    signal,
  );
  if (
    (result.current && result.current.execution_id !== executionId) ||
    result.history.some((entry) => entry.execution_id !== executionId)
  ) {
    throw new Error(
      'Die gelesene Währungsherkunft gehört nicht zu dieser Buchung. Bitte neu laden.',
    );
  }
  return result;
}

function ExecutionCurrencyContext({
  tradeId,
  executionId,
  confirmation,
  resolution,
  readOnly = false,
  onChanged,
}: Props) {
  const [opened, setOpened] = useState(false);
  const [history, setHistory] = useState<ExecutionCurrencyHistory | null>(null);
  const [draft, setDraft] = useState(emptyExecutionCurrency);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [needsReload, setNeedsReload] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const active = useRef(true);
  const generation = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const lock = useRef(false);
  const parentBasis = JSON.stringify([confirmation?.id ?? null, resolution ?? null]);
  const previousParentBasis = useRef(parentBasis);

  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
      generation.current += 1;
      controller.current?.abort();
    };
  }, []);

  useEffect(() => {
    if (previousParentBasis.current === parentBasis || saving) return;
    previousParentBasis.current = parentBasis;
    if (
      !opened ||
      (history &&
        parentBasis ===
          JSON.stringify([history.current?.id ?? null, history.currency_resolution ?? null]))
    )
      return;
    // Another BUY confirmation can change an already opened SELL's provenance.
    // Keep the write pin unavailable until the user reads that changed basis.
    generation.current += 1;
    controller.current?.abort();
    setHistory(null);
    setLoading(false);
    setNeedsReload(true);
    setMessage(null);
    setError(
      'Die Währungsquellen dieser Buchung haben sich geändert. Bitte die Währungsherkunft neu laden.',
    );
  }, [parentBasis, history, opened, saving]);

  async function load() {
    if (lock.current) return;
    const current = ++generation.current;
    controller.current?.abort();
    const requestController = new AbortController();
    controller.current = requestController;
    setOpened(true);
    setLoading(true);
    setHistory(null);
    setDraft(emptyExecutionCurrency());
    setEditing(false);
    setError(null);
    setMessage(null);
    try {
      const result = await readHistory(tradeId, executionId, requestController.signal);
      if (!active.current || requestController.signal.aborted || current !== generation.current)
        return;
      setHistory(result);
      setNeedsReload(false);
    } catch (cause) {
      if (!active.current || requestController.signal.aborted || current !== generation.current)
        return;
      setError(
        cause instanceof Error ? cause.message : 'Währungsherkunft konnte nicht geladen werden.',
      );
    } finally {
      if (active.current && !requestController.signal.aborted && current === generation.current) {
        setLoading(false);
      }
    }
  }

  async function save() {
    if (lock.current || !history || !draft.code.trim() || loading || needsReload || readOnly)
      return;
    let declaration;
    try {
      declaration = executionCurrencyDeclaration(draft).currency_confirmation;
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Bitte die Währungsangabe prüfen.');
      return;
    }
    if (!declaration) return;
    lock.current = true;
    setSaving(true);
    setError(null);
    setMessage(null);
    const scope = `execution-currency:${tradeId}:${executionId}`;
    const payload = {
      ...declaration,
      supersedes_confirmation_id: history.current?.id ?? null,
    };
    const current = ++generation.current;
    controller.current?.abort();
    const requestController = new AbortController();
    controller.current = requestController;
    let persisted = false;
    try {
      const result = await tradeManagementApiClient.confirmExecutionCurrency(tradeId, executionId, {
        ...payload,
        request_id: captureRequest(scope, payload),
      });
      if (result.execution_id !== executionId)
        throw new Error(
          'Die Antwort gehört nicht zu dieser Buchung. Den aktuellen Stand vor einer weiteren Bestätigung prüfen.',
        );
      finishCapture(scope);
      persisted = true;
      if (!active.current || requestController.signal.aborted || current !== generation.current)
        return;
      // A successful idempotent replay can return an already superseded receipt.
      // Only a new history read establishes the currently effective confirmation.
      setHistory(null);
      setDraft(emptyExecutionCurrency());
      setEditing(false);
      setNeedsReload(true);
      setLoading(true);
      const refreshed = await readHistory(tradeId, executionId, requestController.signal);
      if (!active.current || requestController.signal.aborted || current !== generation.current)
        return;
      setHistory(refreshed);
      setNeedsReload(false);
      setMessage(
        refreshed.current?.id === result.id
          ? 'Währung bestätigt. Eine erneute Auswertung berücksichtigt den dann wirksamen Quellenstand.'
          : 'Speicherung bestätigt. Inzwischen gilt ein anderer Bestätigungsstand; angezeigt wird die neu gelesene Herkunft.',
      );
      try {
        await onChanged?.();
      } catch {
        if (active.current && !requestController.signal.aborted && current === generation.current) {
          setMessage(
            'Währung gespeichert. Die übrigen Buchungen konnten noch nicht aktualisiert werden. Bitte die Buchungsdaten neu laden.',
          );
        }
      }
    } catch (cause) {
      if (!active.current || requestController.signal.aborted || current !== generation.current)
        return;
      if (persisted) {
        setHistory(null);
        setNeedsReload(true);
        setError(
          'Speicherung bestätigt, aktueller Bestätigungsstand aber nicht verfügbar. Währungsherkunft neu laden, bevor eine weitere Bestätigung erfolgt.' +
            (cause instanceof Error ? ` ${cause.message}` : ''),
        );
      } else if (cause instanceof MarketApiError && cause.status === 409) {
        setNeedsReload(true);
        setDraft(emptyExecutionCurrency());
        setError(
          'Der Buchungs- oder Bestätigungsstand hat sich geändert. Herkunft neu laden und vor einer weiteren Bestätigung prüfen.',
        );
      } else {
        setError(
          cause instanceof Error
            ? cause.message
            : 'Bestätigung nicht bestätigt. Derselbe unveränderte Versuch kann erneut gesendet werden.',
        );
      }
    } finally {
      lock.current = false;
      if (active.current && !requestController.signal.aborted && current === generation.current) {
        setSaving(false);
        setLoading(false);
      }
    }
  }

  const current = opened ? history?.current : confirmation;
  const currentResolution = opened ? history?.currency_resolution : resolution;
  const inherited =
    currentResolution?.source === 'PRIOR_BUYS' ||
    currentResolution?.source === 'REPLACED_EXECUTION';
  return (
    <section
      aria-label="Ausführungswährung und Herkunft"
      className="mt-3 border-t border-slate-800 pt-3"
    >
      <p className="text-sm">
        Ausführungswährung:{' '}
        <strong>
          {opened && !history
            ? loading
              ? 'Bestätigungsstand wird gelesen…'
              : 'Aktueller Bestätigungsstand nicht verfügbar'
            : executionCurrencyText(currentResolution, current)}
        </strong>
      </p>
      <button
        type="button"
        disabled={saving}
        onClick={() => void load()}
        className="mt-2 rounded border border-slate-700 p-2 text-sm disabled:opacity-50"
      >
        {opened
          ? 'Währungsherkunft neu laden'
          : readOnly || inherited
            ? 'Währungsherkunft ansehen'
            : 'Währung prüfen / bestätigen'}
      </button>
      {opened && (
        <div className="mt-3 space-y-3">
          {loading && <p role="status">Währungsherkunft wird geladen…</p>}
          {error && (
            <p role="alert" className="text-sm text-amber-300">
              {error}
            </p>
          )}
          {message && (
            <p role="status" className="text-sm">
              {message}
            </p>
          )}
          {history && !loading && (
            <>
              <p className="text-sm text-slate-400">
                {history.current
                  ? `Gelesene Bestätigung: ${history.current.currency_code}, bestätigt am ${new Date(history.current.confirmed_at).toLocaleString('de-DE')}. Eine Änderung ersetzt genau diese Bestätigung; sie bleibt historisch erhalten.`
                  : inherited
                    ? 'Für diese Buchung gilt die übernommene Währung. Es ist keine zusätzliche Bestätigung nötig.'
                    : 'Für diese konkrete Buchung liegt keine eigene Währungsbestätigung vor.'}
              </p>
              <ExecutionCurrencySources resolution={currentResolution} />
              {!readOnly && inherited && !editing && (
                <button
                  type="button"
                  onClick={() => setEditing(true)}
                  className="rounded border border-slate-700 px-3 py-2 text-sm"
                >
                  Abweichende Währung angeben
                </button>
              )}
              {!readOnly && (!inherited || editing) && (
                <form
                  aria-label="Ausführungswährung bestätigen"
                  onSubmit={(event) => {
                    event.preventDefault();
                    void save();
                  }}
                >
                  <ExecutionCurrencyInput
                    value={draft}
                    onChange={setDraft}
                    disabled={saving || needsReload}
                  />
                  <button
                    type="submit"
                    disabled={saving || needsReload || !draft.code.trim()}
                    className="mt-3 rounded border border-sky-700 p-2 text-sm disabled:opacity-50"
                  >
                    {saving
                      ? 'Bestätigung wird gespeichert…'
                      : history.current
                        ? 'Währungsbestätigung ersetzen'
                        : 'Währungsbestätigung speichern'}
                  </button>
                </form>
              )}
              <details className="text-sm">
                <summary className="cursor-pointer">
                  Bisherige Bestätigungen ({history.history.length})
                </summary>
                {history.history.length === 0 ? (
                  <p className="mt-2">Keine Bestätigungen gespeichert.</p>
                ) : (
                  <ol className="mt-2 space-y-2">
                    {history.history.map((item) => (
                      <li key={item.id} className="break-words rounded border border-slate-800 p-2">
                        <p>
                          {item.currency_code} ·{' '}
                          {item.id === history.current?.id ? 'aktuell' : 'historisch ersetzt'} ·
                          ausdrücklich vom Nutzer bestätigt
                        </p>
                        <p>
                          Bestätigt: {new Date(item.confirmed_at).toLocaleString('de-DE')} · durch{' '}
                          {item.confirmed_by}
                        </p>
                        {item.note && <p>Beleg / Erläuterung: {item.note}</p>}
                        <p className="text-xs text-slate-400">
                          Bestätigung {item.id} · Buchung {item.execution_id}
                        </p>
                        {item.supersedes_confirmation_id && (
                          <p className="text-xs text-slate-400">
                            Ersetzt {item.supersedes_confirmation_id}
                          </p>
                        )}
                      </li>
                    ))}
                  </ol>
                )}
              </details>
            </>
          )}
        </div>
      )}
    </section>
  );
}
