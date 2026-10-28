import { useCallback, useEffect, useRef, useState } from 'react';

import { MarketApiError } from '../../market/services/http';
import { tradeManagementApiClient, tradeTimelineChangedEvent } from '../services/client';
import {
  effectiveExecutions,
  executionDateContext,
  executionDateCorrection,
  todayInZone,
} from '../services/executionDateCorrection';
import {
  executionAmountChanges,
  executionAmountCorrection,
  executionPrice,
  executionQuantity,
} from '../services/executionAmountCorrection';
import {
  emptyExecutionCurrency,
  executionCurrencyDeclaration,
  executionCurrencyText,
  type ExecutionCurrencyDraft,
} from '../services/executionCurrency';
import type { TradeTimelineEntryResponse } from '../types/api';
import { ExecutionCurrencyOverride } from './ExecutionCurrencyOverride';
import { ExecutionCurrencyPanel } from './ExecutionCurrencyPanel';
import { ExecutionCurrencySources } from './ExecutionCurrencySources';
import { TradeTimelinePanel } from './TradeTimelinePanel';
import { TradePendingChangesProvider, useTradePendingChanges } from './TradePendingChanges';

interface Props {
  tradeId: string;
  cancelled?: boolean;
  onChanged: () => Promise<void>;
  reloadToken?: number;
  onWriteBlockedChange?: (blocked: boolean) => void;
}
interface Editor {
  kind: 'facts' | 'currency';
  entry: TradeTimelineEntryResponse;
}
interface CorrectionDraft {
  quantity: string;
  price: string;
  date: string;
  keepTime: boolean;
  confirmed: boolean;
  currency: ExecutionCurrencyDraft;
}
interface Recovery {
  targetId: string;
  replacementId?: string;
  confirmed: boolean;
}
interface CurrencyPending {
  dirty: boolean;
  busy: boolean;
  writeBlocked?: boolean;
}
const emptyDraft = (): CorrectionDraft => ({
  quantity: '',
  price: '',
  date: '',
  keepTime: false,
  confirmed: false,
  currency: emptyExecutionCurrency(),
});
function dateLabel(entry: TradeTimelineEntryResponse) {
  return entry.execution_side === 'SELL' ? 'Verkaufsdatum' : 'Kaufdatum';
}
function currencyBasis(entry: TradeTimelineEntryResponse) {
  return JSON.stringify([
    entry.currency_confirmation?.id ?? null,
    entry.currency_resolution ?? null,
  ]);
}
function initialDraft(entry: TradeTimelineEntryResponse): CorrectionDraft {
  const context = executionDateContext(entry);
  if (entry.quantity === null || entry.price_per_unit === null || !entry.execution_side) {
    throw new Error('Die gespeicherte Kauf-/Verkaufsbuchung ist unvollständig.');
  }
  return {
    ...emptyDraft(),
    quantity: String(entry.quantity),
    price: entry.price_per_unit,
    date: context.date,
    keepTime: context.hasTime,
  };
}
function errorText(cause: unknown) {
  return cause instanceof Error ? cause.message : 'Der aktuelle Buchungsstand ist nicht verfügbar.';
}
function validationError(validate: () => unknown): string | null {
  try {
    validate();
    return null;
  } catch (cause) {
    return errorText(cause);
  }
}

/** One read owner for current executions, immutable history and the single pinned editor. */
export function ExecutionDatesPanel(props: Props) {
  return (
    <TradePendingChangesProvider>
      <ExecutionDatesContext key={props.tradeId} {...props} />
    </TradePendingChangesProvider>
  );
}

function ExecutionDatesContext({
  tradeId,
  cancelled = false,
  onChanged,
  reloadToken = 0,
  onWriteBlockedChange,
}: Props) {
  const [entries, setEntries] = useState<TradeTimelineEntryResponse[]>([]);
  const entriesRef = useRef(entries);
  const [view, setView] = useState<'current' | 'history'>('current');
  const [loading, setLoading] = useState(true);
  const loadingRef = useRef(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const loadErrorRef = useRef<string | null>(null);
  const [editor, setEditor] = useState<Editor | null>(null);
  const editorRef = useRef(editor);
  const [draft, setDraft] = useState(emptyDraft);
  const draftRef = useRef(draft);
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  const [reviewing, setReviewing] = useState(false);
  const reviewLock = useRef(false);
  const [currencyPending, setCurrencyPending] = useState<CurrencyPending>({
    dirty: false,
    busy: false,
  });
  const currencyPendingRef = useRef(currencyPending);
  const [recovery, setRecovery] = useState<Recovery | null>(null);
  const recoveryRef = useRef(recovery);
  const [message, setMessage] = useState<string | null>(null);
  const active = useRef(false);
  const readGeneration = useRef(0);
  const writeGeneration = useRef(0);
  const readController = useRef<AbortController | null>(null);
  const region = useRef<HTMLElement>(null);
  const previousEditor = useRef<Editor | null>(null);
  const changedCallback = useRef(onChanged);
  const blockCallback = useRef(onWriteBlockedChange);
  changedCallback.current = onChanged;
  blockCallback.current = onWriteBlockedChange;

  function isDirty() {
    if (recoveryRef.current && !recoveryRef.current.confirmed) return true;
    if (editorRef.current?.kind === 'currency') return currencyPendingRef.current.dirty;
    if (editorRef.current?.kind !== 'facts') return false;
    const original = initialDraft(editorRef.current.entry);
    const current = draftRef.current;
    const amounts = executionAmountChanges(
      editorRef.current.entry,
      current.quantity,
      current.price,
    );
    return (
      amounts.quantity ||
      amounts.price ||
      current.date !== original.date ||
      current.keepTime !== original.keepTime ||
      current.confirmed ||
      Boolean(current.currency.code || current.currency.note)
    );
  }
  const { notify, requestChange, isBusy } = useTradePendingChanges('bookings', {
    isDirty,
    isBusy: () => lock.current || currencyPendingRef.current.busy,
    onDiscard: () => {
      // The requested action owns closing/switching. A currency reload must
      // keep that editor mounted until its own load clears the old draft.
      currencyPendingRef.current = { ...currencyPendingRef.current, dirty: false };
      setCurrencyPending(currencyPendingRef.current);
      const next =
        editorRef.current?.kind === 'facts' ? initialDraft(editorRef.current.entry) : emptyDraft();
      draftRef.current = next;
      setDraft(next);
    },
  });
  const reportBlocked = useCallback(() => {
    blockCallback.current?.(
      lock.current ||
        reviewLock.current ||
        currencyPendingRef.current.busy ||
        Boolean(currencyPendingRef.current.writeBlocked) ||
        Boolean(recoveryRef.current),
    );
    notify();
  }, [notify]);
  function changeDraft(next: CorrectionDraft) {
    draftRef.current = next;
    setDraft(next);
    notify();
  }
  function changeRecovery(next: Recovery | null) {
    recoveryRef.current = next;
    setRecovery(next);
    reportBlocked();
  }
  function clearEditor() {
    editorRef.current = null;
    setEditor(null);
    draftRef.current = emptyDraft();
    setDraft(draftRef.current);
    currencyPendingRef.current = { dirty: false, busy: false };
    setCurrencyPending(currencyPendingRef.current);
    reportBlocked();
  }
  function currencyNeedsReview() {
    if (!currencyPendingRef.current.writeBlocked || currencyPendingRef.current.busy) return false;
    setMessage(
      'Bitte zuerst die Währungsherkunft neu laden oder den unveränderten Bestätigungsversuch abschließen. Der Buchungseditor bleibt bis zur Prüfung erhalten.',
    );
    return true;
  }
  function closeEditor() {
    if (!currencyNeedsReview()) requestChange(clearEditor);
  }
  const load = useCallback(async () => {
    const generation = ++readGeneration.current;
    readController.current?.abort();
    const controller = new AbortController();
    readController.current = controller;
    loadingRef.current = true;
    loadErrorRef.current = null;
    setLoading(true);
    setLoadError(null);
    try {
      const history = await tradeManagementApiClient.timeline(tradeId, controller.signal);
      if (!active.current || controller.signal.aborted || generation !== readGeneration.current)
        return null;
      if (history.some((entry) => entry.trade_id !== tradeId))
        throw new Error('Die gelesenen Buchungen gehören nicht zu diesem Trade. Bitte neu laden.');
      entriesRef.current = history;
      setEntries(history);
      return history;
    } catch (cause) {
      if (!active.current || controller.signal.aborted || generation !== readGeneration.current)
        return null;
      loadErrorRef.current = errorText(cause);
      setLoadError(loadErrorRef.current);
      throw cause;
    } finally {
      if (active.current && !controller.signal.aborted && generation === readGeneration.current) {
        loadingRef.current = false;
        setLoading(false);
      }
    }
  }, [tradeId]);
  useEffect(() => {
    active.current = true;
    void load().catch(() => undefined);
    return () => {
      active.current = false;
      readGeneration.current += 1;
      writeGeneration.current += 1;
      readController.current?.abort();
    };
  }, [load]);
  const previousReload = useRef(reloadToken);
  useEffect(() => {
    if (previousReload.current === reloadToken) return;
    previousReload.current = reloadToken;
    if (!lock.current && !currencyPendingRef.current.busy) void load().catch(() => undefined);
  }, [load, reloadToken]);
  useEffect(() => {
    function changed(event: Event) {
      if ((event as CustomEvent<{ tradeId?: string }>).detail?.tradeId !== tradeId) return;
      // Own writes read once after their receipt; other actions update this
      // shared source without replacing any pinned editor or draft.
      if (!lock.current && !currencyPendingRef.current.busy) void load().catch(() => undefined);
    }
    window.addEventListener(tradeTimelineChangedEvent, changed);
    return () => window.removeEventListener(tradeTimelineChangedEvent, changed);
  }, [load, tradeId]);
  useEffect(() => {
    if (editor?.kind === 'facts')
      region.current?.querySelector<HTMLInputElement>('input[type="date"]')?.focus();
    else if (!editor && previousEditor.current && view === 'current')
      region.current?.focus({ preventScroll: true });
    previousEditor.current = editor;
  }, [editor, view]);
  async function readCurrentStand() {
    const [historyResult, projectionResult] = await Promise.allSettled([
      load(),
      changedCallback.current(),
    ]);
    if (!active.current) return null;
    if (historyResult.status === 'rejected') throw historyResult.reason;
    if (projectionResult.status === 'rejected') throw projectionResult.reason;
    if (!historyResult.value)
      throw new Error('Ein neuerer Leseversuch läuft. Bitte den Buchungsstand nochmals prüfen.');
    return historyResult.value;
  }
  function assertReplacement(history: TradeTimelineEntryResponse[], expected: Recovery) {
    if (!expected.confirmed) return;
    if (
      !history.some(
        (entry) =>
          entry.kind === 'EXECUTION' &&
          entry.id === expected.replacementId &&
          entry.supersedes_id === expected.targetId,
      )
    ) {
      throw new Error(
        'Die Verknüpfung zur ursprünglichen Buchung ist noch nicht im gelesenen Verlauf bestätigt.',
      );
    }
  }
  async function reviewStand() {
    if (isBusy() || reviewLock.current) return;
    reviewLock.current = true;
    setReviewing(true);
    reportBlocked();
    try {
      const expected = recoveryRef.current;
      const history = await readCurrentStand();
      if (!history || !active.current) return;
      if (expected) assertReplacement(history, expected);
      changeRecovery(null);
      if (expected) {
        changeDraft({ ...draftRef.current, confirmed: false });
        setMessage(
          expected.confirmed
            ? 'Gespeicherte Korrektur und aktueller Positionsstand wurden neu gelesen.'
            : 'Buchungsstand neu gelesen. Die genaue Buchung und ihre Historie vor einer weiteren ausdrücklich bestätigten Änderung prüfen.',
        );
      }
    } catch (cause) {
      if (active.current)
        setMessage('Buchungsstand noch nicht vollständig geprüft: ' + errorText(cause));
    } finally {
      if (active.current) {
        reviewLock.current = false;
        setReviewing(false);
        reportBlocked();
      }
    }
  }
  function openEditor(entry: TradeTimelineEntryResponse, kind: Editor['kind']) {
    if (
      cancelled ||
      reviewLock.current ||
      recoveryRef.current ||
      currencyPendingRef.current.writeBlocked ||
      loadingRef.current ||
      loadErrorRef.current
    )
      return;
    requestChange(() => {
      try {
        // Recheck after a delayed discard decision; never choose a successor.
        if (!effectiveExecutions(entriesRef.current).some((item) => item.id === entry.id)) {
          setMessage(
            'Diese Buchung wurde inzwischen ersetzt. Bitte den aktuellen Eintrag auswählen.',
          );
          return;
        }
        const nextDraft = kind === 'facts' ? initialDraft(entry) : emptyDraft();
        const next = { kind, entry };
        editorRef.current = next;
        setEditor(next);
        changeDraft(nextDraft);
        currencyPendingRef.current = { dirty: false, busy: false };
        setCurrencyPending(currencyPendingRef.current);
        setMessage(null);
        reportBlocked();
      } catch (cause) {
        setMessage(errorText(cause));
      }
    });
  }
  async function save() {
    const selected = editorRef.current;
    const currentDraft = draftRef.current;
    if (
      !selected ||
      selected.kind !== 'facts' ||
      !currentDraft.confirmed ||
      cancelled ||
      lock.current ||
      isBusy() ||
      reviewLock.current ||
      currencyPendingRef.current.busy ||
      recoveryRef.current ||
      loadingRef.current ||
      loadErrorRef.current
    )
      return;
    const original = initialDraft(selected.entry);
    const amounts = executionAmountChanges(
      selected.entry,
      currentDraft.quantity,
      currentDraft.price,
    );
    if (
      !amounts.quantity &&
      !amounts.price &&
      currentDraft.date === original.date &&
      currentDraft.keepTime === original.keepTime
    )
      return;
    const effective = effectiveExecutions(entriesRef.current).find(
      (entry) => entry.id === selected.entry.id,
    );
    if (!effective || currencyBasis(effective) !== currencyBasis(selected.entry)) {
      setMessage(
        'Die Buchung oder ihre Währungsquellen haben sich geändert. Bitte den genauen Stand prüfen.',
      );
      return;
    }
    let payload;
    try {
      payload = {
        ...executionAmountCorrection(
          selected.entry,
          currentDraft.date,
          currentDraft.keepTime,
          currentDraft.quantity,
          currentDraft.price,
        ),
        ...executionCurrencyDeclaration(currentDraft.currency),
      };
    } catch (cause) {
      setMessage(errorText(cause));
      return;
    }
    lock.current = true;
    setBusy(true);
    reportBlocked();
    setMessage(null);
    const operation = ++writeGeneration.current;
    const isCurrent = () => active.current && operation === writeGeneration.current;
    let receipt: Recovery | null = null;
    try {
      const response = await tradeManagementApiClient.correctExecution(
        tradeId,
        selected.entry.id,
        payload,
      );
      if (!isCurrent()) return;
      if (
        !response?.execution?.id ||
        response.execution.id === selected.entry.id ||
        response.execution.trade_id !== tradeId
      )
        throw new Error('Die Korrekturantwort lässt sich dieser Buchung nicht sicher zuordnen.');
      receipt = {
        targetId: selected.entry.id,
        replacementId: response.execution.id,
        confirmed: true,
      };
      changeRecovery(receipt);
      clearEditor();
      const history = await readCurrentStand();
      if (!isCurrent() || !history) return;
      assertReplacement(history, receipt);
      changeRecovery(null);
      setMessage('Buchung korrigiert. Die ursprüngliche Buchung bleibt in der Historie erhalten.');
    } catch (cause) {
      if (!isCurrent()) return;
      if (receipt) {
        setMessage(
          'Buchungskorrektur gespeichert, Ansicht noch nicht aktualisiert. Bitte den Buchungsstand prüfen. ' +
            errorText(cause),
        );
      } else {
        const rejected =
          cause instanceof MarketApiError && cause.status >= 400 && cause.status < 500;
        if (!rejected) changeRecovery({ targetId: selected.entry.id, confirmed: false });
        changeDraft({ ...draftRef.current, confirmed: false });
        setMessage(
          'Korrektur nicht bestätigt: ' +
            errorText(cause) +
            ' ' +
            (rejected
              ? 'Bitte die Eingaben und den aktuellen Stand prüfen.'
              : 'Vor weiteren Änderungen den Buchungsstand bewusst prüfen; der Auftrag wird nicht automatisch erneut gesendet.'),
        );
        // A lost response can hide a committed replacement. Read timeline and
        // backend projection first, without automatically retrying the POST.
        try {
          if (rejected) await load();
          else await readCurrentStand();
        } catch {
          /* Preserve the original uncertainty and inputs. */
        }
      }
    } finally {
      if (isCurrent()) {
        lock.current = false;
        setBusy(false);
        reportBlocked();
      }
    }
  }
  const effective = effectiveExecutions(entries);
  const selectedCurrent = editor
    ? effective.find((entry) => entry.id === editor.entry.id)
    : undefined;
  const stale = Boolean(editor && !selectedCurrent);
  const sourceChanged = Boolean(
    editor?.kind === 'facts' &&
      selectedCurrent &&
      currencyBasis(selectedCurrent) !== currencyBasis(editor.entry),
  );
  const context = editor?.kind === 'facts' ? executionDateContext(editor.entry) : null;
  const amountChanges =
    editor?.kind === 'facts'
      ? executionAmountChanges(editor.entry, draft.quantity, draft.price)
      : { quantity: false, price: false };
  const timeChanged = Boolean(
    context && (draft.date !== context.date || draft.keepTime !== context.hasTime),
  );
  const unchanged = !timeChanged && !amountChanges.quantity && !amountChanges.price;
  const quantityError = context ? validationError(() => executionQuantity(draft.quantity)) : null;
  const priceError =
    context && editor
      ? validationError(() => executionPrice(draft.price, editor.entry.price_per_unit!))
      : null;
  const timeError =
    context && editor
      ? validationError(() => executionDateCorrection(editor.entry, draft.date, draft.keepTime))
      : null;
  const invalid = Boolean(quantityError || priceError || timeError);
  const writeBlocked =
    isBusy() ||
    busy ||
    reviewing ||
    currencyPending.busy ||
    Boolean(recovery) ||
    Boolean(currencyPending.writeBlocked);
  const currencyStateChanged = useCallback(
    (next: CurrencyPending) => {
      currencyPendingRef.current = next;
      setCurrencyPending(next);
      reportBlocked();
    },
    [reportBlocked],
  );
  function switchView(next: 'current' | 'history') {
    if (view === next || currencyNeedsReview()) return;
    requestChange(() => {
      clearEditor();
      setView(next);
      region.current?.querySelector<HTMLButtonElement>('#bookings-' + next + '-tab')?.focus();
    });
  }
  function renderEditor() {
    if (!editor) return null;
    const selected = editor.entry;
    const changes: { field: string; previous: string; next: string }[] = [];
    if (context && !invalid) {
      if (amountChanges.quantity)
        changes.push({
          field: 'Menge',
          previous: String(selected.quantity),
          next: String(executionQuantity(draft.quantity)),
        });
      if (amountChanges.price)
        changes.push({
          field: 'Preis je Einheit',
          previous: selected.price_per_unit!,
          next: executionPrice(draft.price, selected.price_per_unit!),
        });
      if (timeChanged) {
        const time = executionDateCorrection(selected, draft.date, draft.keepTime);
        changes.push({
          field: 'Ausführung',
          previous: context.hasTime
            ? selected.occurred_at
            : `${context.date} · ${context.timezone} (Uhrzeit unbekannt)`,
          next:
            'executed_at' in time
              ? time.executed_at
              : `${time.executed_on} · ${time.execution_timezone} (Uhrzeit unbekannt)`,
        });
      }
      if (draft.currency.code.trim())
        changes.push({
          field: 'Währungsbestätigung',
          previous: executionCurrencyText(
            selected.currency_resolution,
            selected.currency_confirmation,
          ),
          next: draft.currency.code.trim().toUpperCase() + ' · ausdrücklich bestätigen',
        });
    }
    return (
      <div className="space-y-3">
        <p className="break-all font-medium">
          Buchung {selected.id} · {selected.execution_side}
          {editor.kind === 'currency' && (
            <>
              {' '}
              · {selected.quantity} Stück · Preis {selected.price_per_unit}
            </>
          )}
        </p>
        {stale && (
          <p role="alert">
            Diese Buchung wurde bereits ersetzt. Bitte den aktuellen Eintrag auswählen.
          </p>
        )}
        {editor.kind === 'currency' ? (
          <ExecutionCurrencyPanel
            editor
            tradeId={tradeId}
            executionId={selected.id}
            confirmation={
              selectedCurrent
                ? selectedCurrent.currency_confirmation
                : selected.currency_confirmation
            }
            resolution={
              selectedCurrent ? selectedCurrent.currency_resolution : selected.currency_resolution
            }
            readOnly={cancelled || stale}
            disabled={loading || reviewing || Boolean(loadError) || Boolean(recovery)}
            isWriteBlocked={isBusy}
            onChanged={async () => {
              await readCurrentStand();
            }}
            onPendingChange={currencyStateChanged}
            requestChange={requestChange}
            onClose={closeEditor}
          />
        ) : context && !cancelled ? (
          <form
            aria-label="Buchung korrigieren"
            className="space-y-3"
            onSubmit={(event) => {
              event.preventDefault();
              void save();
            }}
          >
            <p className="text-sm text-slate-400">
              Diese Korrektur berichtigt die bestehende Buchung. Das Original bleibt in der
              Historie; es wird kein zusätzlicher Kauf oder Verkauf erfasst. Trade, Produkt und
              Richtung bleiben fest zugeordnet.
            </p>
            <p className="text-sm text-slate-400">
              Währung:{' '}
              {executionCurrencyText(selected.currency_resolution, selected.currency_confirmation)}
            </p>
            <ExecutionCurrencySources resolution={selected.currency_resolution} />
            {sourceChanged && (
              <div role="alert" className="space-y-2 text-amber-300">
                <p>
                  Die Währungsquellen haben sich geändert. Die Eingaben bleiben erhalten; bitte die
                  neue Herkunft bewusst prüfen.
                </p>
                <p>
                  Neu gelesen:{' '}
                  {executionCurrencyText(
                    selectedCurrent?.currency_resolution,
                    selectedCurrent?.currency_confirmation,
                  )}
                </p>
                <ExecutionCurrencySources resolution={selectedCurrent?.currency_resolution} />
                <button
                  type="button"
                  disabled={writeBlocked || loading || Boolean(loadError)}
                  className="rounded border p-2"
                  onClick={() => {
                    if (!selectedCurrent) return;
                    const next = {
                      ...editor,
                      entry: {
                        ...selected,
                        currency_resolution: selectedCurrent.currency_resolution,
                        currency_confirmation: selectedCurrent.currency_confirmation,
                      },
                    };
                    editorRef.current = next;
                    setEditor(next);
                    changeDraft({ ...draftRef.current, confirmed: false });
                  }}
                >
                  Neu gelesene Währungsherkunft geprüft
                </button>
              </div>
            )}
            <div className="grid min-w-0 gap-3 sm:grid-cols-2">
              <div className="min-w-0">
                <label htmlFor="execution-correction-quantity" className="block">
                  Menge
                </label>
                <input
                  id="execution-correction-quantity"
                  type="text"
                  inputMode="numeric"
                  required
                  value={draft.quantity}
                  disabled={writeBlocked || stale}
                  aria-invalid={Boolean(quantityError)}
                  aria-describedby={
                    quantityError ? 'execution-correction-quantity-error' : undefined
                  }
                  onChange={(event) =>
                    changeDraft({
                      ...draftRef.current,
                      quantity: event.target.value,
                      confirmed: false,
                    })
                  }
                  className="mt-1 block w-full min-w-0 rounded border bg-slate-950 p-2"
                />
                {quantityError && (
                  <p
                    id="execution-correction-quantity-error"
                    role="alert"
                    className="mt-1 text-sm text-amber-300"
                  >
                    {quantityError}
                  </p>
                )}
              </div>
              <div className="min-w-0">
                <label htmlFor="execution-correction-price" className="block">
                  Preis je Einheit
                </label>
                <input
                  id="execution-correction-price"
                  type="text"
                  inputMode="decimal"
                  required
                  value={draft.price}
                  disabled={writeBlocked || stale}
                  aria-invalid={Boolean(priceError)}
                  aria-describedby={
                    priceError
                      ? 'execution-correction-price-error'
                      : 'execution-correction-price-help'
                  }
                  onChange={(event) =>
                    changeDraft({
                      ...draftRef.current,
                      price: event.target.value,
                      confirmed: false,
                    })
                  }
                  className="mt-1 block w-full min-w-0 rounded border bg-slate-950 p-2"
                />
                <p id="execution-correction-price-help" className="mt-1 text-xs text-slate-400">
                  Dezimalpunkt oder Dezimalkomma, ohne Tausendertrennzeichen.
                </p>
                {priceError && (
                  <p
                    id="execution-correction-price-error"
                    role="alert"
                    className="mt-1 text-sm text-amber-300"
                  >
                    {priceError}
                  </p>
                )}
              </div>
            </div>
            <label className="block">
              {dateLabel(selected)} korrigieren
              <input
                aria-label={dateLabel(selected) + ' korrigieren'}
                type="date"
                required
                max={todayInZone(context.timezone)}
                value={draft.date}
                disabled={writeBlocked || stale}
                aria-invalid={Boolean(timeError)}
                aria-describedby={timeError ? 'execution-correction-time-error' : undefined}
                onChange={(event) =>
                  changeDraft({ ...draftRef.current, date: event.target.value, confirmed: false })
                }
                className="mt-1 block max-w-full rounded border bg-slate-950 p-2"
              />
            </label>
            {timeError && (
              <p
                id="execution-correction-time-error"
                role="alert"
                className="text-sm text-amber-300"
              >
                {timeError}
              </p>
            )}
            <p className="text-sm text-slate-400">
              Zeitzone: {context.timezone}. Maßgeblich ist die tatsächliche Ausführung, nicht das
              Eingabedatum.
            </p>
            {context.hasTime && (
              <label className="block">
                <input
                  type="checkbox"
                  checked={draft.keepTime}
                  disabled={writeBlocked || stale}
                  onChange={(event) =>
                    changeDraft({
                      ...draftRef.current,
                      keepTime: event.target.checked,
                      confirmed: false,
                    })
                  }
                />{' '}
                Bisherige Uhrzeit beibehalten (
                {new Date(selected.occurred_at).toLocaleTimeString('de-DE')})
                <span className="mt-1 block break-all text-xs text-slate-400">
                  Genauer gespeicherter Zeitpunkt: {selected.occurred_at}
                </span>
              </label>
            )}
            {!draft.keepTime && (
              <p className="text-sm text-amber-300">
                Es wird nur das bestätigte Datum gespeichert. Die genaue Uhrzeit gilt als unbekannt.
              </p>
            )}
            <ExecutionCurrencyOverride
              key={selected.id}
              value={draft.currency}
              onChange={(currency) =>
                changeDraft({ ...draftRef.current, currency, confirmed: false })
              }
              disabled={writeBlocked || stale || sourceChanged}
              correction
            />
            {!invalid && changes.length > 0 && !unchanged && (
              <table className="w-full table-fixed text-left text-sm">
                <caption className="mb-2 text-left font-medium">Geänderte Buchungsdaten</caption>
                <thead>
                  <tr>
                    <th scope="col" className="w-1/4 p-1">
                      Feld
                    </th>
                    <th scope="col" className="p-1">
                      Alt
                    </th>
                    <th scope="col" className="p-1">
                      Neu
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {changes.map((change) => (
                    <tr key={change.field}>
                      <th scope="row" className="break-words p-1 align-top font-normal">
                        {change.field}
                      </th>
                      <td className="break-all p-1 align-top">{change.previous}</td>
                      <td className="break-all p-1 align-top">{change.next}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {unchanged && Boolean(draft.currency.code || draft.currency.note) && (
              <p className="text-sm text-amber-300">
                Für eine reine Währungsbestätigung bitte „Währung prüfen / bestätigen“ öffnen.
              </p>
            )}
            <label className="block">
              <input
                type="checkbox"
                checked={draft.confirmed}
                disabled={writeBlocked || stale || sourceChanged || invalid}
                onChange={(event) =>
                  changeDraft({ ...draftRef.current, confirmed: event.target.checked })
                }
              />{' '}
              Ich bestätige die geänderten Buchungsdaten dieser Buchung.
            </label>
            <div className="flex flex-wrap gap-3">
              <button
                type="submit"
                disabled={
                  writeBlocked ||
                  loading ||
                  Boolean(loadError) ||
                  stale ||
                  sourceChanged ||
                  invalid ||
                  Boolean(unchanged) ||
                  !draft.confirmed ||
                  !draft.date
                }
                className="rounded border border-sky-700 p-2 disabled:opacity-50"
              >
                Korrektur speichern
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={closeEditor}
                className="rounded border p-2"
              >
                Abbrechen
              </button>
              <button
                type="button"
                disabled={writeBlocked}
                onClick={() => openEditor(selectedCurrent ?? selected, 'currency')}
                className="rounded border p-2"
              >
                Währung prüfen / bestätigen
              </button>
            </div>
          </form>
        ) : (
          <p>Stornierter Trade: Diese Buchung ist schreibgeschützt.</p>
        )}
      </div>
    );
  }
  return (
    <section
      ref={region}
      id="execution-dates"
      tabIndex={-1}
      aria-label="Kauf- und Verkaufsdaten"
      className="min-w-0 rounded-xl border border-slate-800 p-5"
    >
      <h2 className="text-lg font-semibold">Buchungen</h2>
      <p className="mt-2 text-sm text-slate-400">
        Kauf-, Nachkauf- und Verkaufsbuchungen mit ihren Ausführungsdaten und Währungsquellen.
        Menge, Preis und Datum lassen sich direkt an der gewählten aktuellen Buchung berichtigen.
        Die Währungsbestätigung bleibt ein eigener Vorgang.
      </p>
      {cancelled && (
        <p className="mt-3">
          Stornierter Trade: Buchungen und Historie sind schreibgeschützt. Die Stornierung ist kein
          Verkauf.
        </p>
      )}
      <div role="tablist" aria-label="Buchungsansicht" className="mt-4 flex flex-wrap gap-2">
        {(['current', 'history'] as const).map((tab) => (
          <button
            key={tab}
            type="button"
            role="tab"
            id={'bookings-' + tab + '-tab'}
            aria-selected={view === tab}
            aria-controls={'bookings-' + tab}
            tabIndex={view === tab ? 0 : -1}
            className={
              'rounded border px-3 py-2 ' +
              (view === tab ? 'border-sky-600 bg-sky-950' : 'border-slate-700')
            }
            onClick={() => switchView(tab)}
            onKeyDown={(event) => {
              if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
              event.preventDefault();
              switchView(
                event.key === 'Home'
                  ? 'current'
                  : event.key === 'End'
                    ? 'history'
                    : view === 'current'
                      ? 'history'
                      : 'current',
              );
            }}
          >
            {tab === 'current' ? 'Aktuelle Buchungen' : 'Historie'}
          </button>
        ))}
      </div>
      {message && (
        <p role="status" className="mt-3">
          {message}
        </p>
      )}
      {loading && (
        <p role="status" className="mt-3">
          Buchungsdaten werden geladen…
        </p>
      )}
      {loadError && (
        <p role="alert" className="mt-3">
          {loadError} Der letzte gelesene Stand ist nicht als aktuell bestätigt.
        </p>
      )}
      {recovery && (
        <p role="alert" className="mt-3 text-amber-300">
          {recovery.confirmed
            ? 'Die Speicherung ist bestätigt. Vor weiteren Änderungen müssen Historie und Position erfolgreich neu gelesen werden.'
            : 'Der Ausgang des Korrekturauftrags ist unklar. Weitere Änderungen bleiben bis zur bewussten Prüfung gesperrt.'}
        </p>
      )}
      <button
        type="button"
        disabled={isBusy() || busy || currencyPending.busy || loading || reviewing}
        onClick={() => void reviewStand()}
        className="mt-3 rounded border p-2"
      >
        {recovery?.confirmed
          ? 'Lesestand erneut laden'
          : recovery
            ? 'Buchungsstand prüfen'
            : 'Buchungsdaten neu laden'}
      </button>
      <div
        role="tabpanel"
        id={'bookings-' + view}
        aria-labelledby={'bookings-' + view + '-tab'}
        className="mt-4 space-y-3"
      >
        {view === 'history' ? (
          <TradeTimelinePanel entries={entries} />
        ) : (
          <>
            {!loading && !loadError && effective.length === 0 && (
              <p>Keine Kauf-/Verkaufsbuchungen vorhanden.</p>
            )}
            {[...effective, ...(stale && editor ? [editor.entry] : [])].map((entry) => (
              <article
                key={entry.id}
                aria-label={
                  stale && editor?.entry.id === entry.id
                    ? 'Ersetzte Bearbeitungsbasis'
                    : 'Buchung ' + entry.id
                }
                className={
                  'min-w-0 rounded border p-3 ' +
                  (stale && editor?.entry.id === entry.id ? 'border-amber-700' : 'border-slate-800')
                }
              >
                {stale && editor?.entry.id === entry.id && (
                  <p className="mb-3 text-sm text-amber-300">
                    Veraltete Bearbeitungsbasis · keine aktuelle Buchung
                  </p>
                )}
                {editor?.entry.id === entry.id ? (
                  renderEditor()
                ) : (
                  <>
                    <p className="break-words font-medium">
                      {dateLabel(entry)} · {entry.quantity ?? '—'} Stück · Preis{' '}
                      {entry.price_per_unit ?? '—'}
                    </p>
                    <p className="mt-1 text-sm">
                      Ausgeführt:{' '}
                      {entry.executed_on ? (
                        entry.executed_on + ' (Uhrzeit unbekannt, ' + entry.execution_timezone + ')'
                      ) : (
                        <time dateTime={entry.occurred_at}>
                          {new Date(entry.occurred_at).toLocaleString('de-DE')} ·{' '}
                          {entry.occurred_at}
                        </time>
                      )}
                    </p>
                    <p className="mt-1 break-all text-xs text-slate-400">
                      Erfasst:{' '}
                      <time dateTime={entry.recorded_at}>
                        {new Date(entry.recorded_at).toLocaleString('de-DE')}
                      </time>{' '}
                      · Buchung {entry.id}
                    </p>
                    <p className="mt-2 text-sm">
                      {executionCurrencyText(
                        entry.currency_resolution,
                        entry.currency_confirmation,
                      )}
                    </p>
                    <ExecutionCurrencySources resolution={entry.currency_resolution} />
                    {!cancelled && (
                      <div className="mt-2 flex flex-wrap gap-2">
                        <button
                          type="button"
                          disabled={writeBlocked || loading || Boolean(loadError)}
                          onClick={() => openEditor(entry, 'facts')}
                          className="rounded border p-2"
                        >
                          {entry.execution_side === 'SELL' ? 'Verkauf' : 'Kauf'} korrigieren
                        </button>
                        <button
                          type="button"
                          disabled={writeBlocked || loading || Boolean(loadError)}
                          onClick={() => openEditor(entry, 'currency')}
                          className="rounded border p-2"
                        >
                          Währung prüfen / bestätigen
                        </button>
                      </div>
                    )}
                  </>
                )}
              </article>
            ))}
          </>
        )}
      </div>
    </section>
  );
}
