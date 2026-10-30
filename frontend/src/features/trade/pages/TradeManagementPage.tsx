import { FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';

import { TradeSourcesView } from '../components/TradeSourcesView';
import { sourceLink } from '../services/sourceView';

import { PositionRiskPanel } from '../../alert/components/PositionRiskPanel';
import { TradeAlertsPanel } from '../../alert/components/TradeAlertsPanel';
import { PositionPriceHistory } from '../../operational_workspace';
import { postTradeApiClient } from '../../post_trade/services/client';
import { postTradeErrorMessage } from '../../post_trade/services/errors';
import { warrantApiClient } from '../../product/services/client';
import type { WarrantResponse } from '../../product/types/api';
import { tradeManagementApiClient } from '../services/client';
import { PriceBindingInput } from '../components/PriceBindingInput';
import type { PriceBinding } from '../types/api';
import { ExecutionDatesPanel } from '../components/ExecutionDatesPanel';
import { TradeCancellationPanel } from '../components/TradeCancellationPanel';
import { AdditionalPurchasePanel } from '../components/AdditionalPurchasePanel';
import {
  TradePendingChangesProvider,
  useTradePendingChanges,
} from '../components/TradePendingChanges';
import { ExecutionDateInput } from '../components/ExecutionDateInput';
import { ExecutionCurrencyOverride } from '../components/ExecutionCurrencyOverride';
import {
  emptyExecutionCurrency,
  executionCurrencyDeclaration,
} from '../services/executionCurrency';
import { captureRequest, executionTime, finishCapture, localToday } from '../services/capture';
import type { PositionResponse, TradeManagementStateResponse, TradeResponse } from '../types/api';

function formatNumber(value: string | null | undefined): string {
  if (value == null || value.trim() === '' || !Number.isFinite(Number(value)))
    return 'Nicht verfügbar';
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

/** Input and navigation handlers share the same value before React renders again. */
function useDraft<T>(initial: T | (() => T)) {
  const [value, setValue] = useState(initial);
  const current = useRef(value);
  const update = useCallback((next: T) => {
    current.current = next;
    setValue(next);
  }, []);
  return [value, update, current] as const;
}

function sameBinding(left: PriceBinding | null, right: PriceBinding | null) {
  return JSON.stringify(left) === JSON.stringify(right);
}

class SupersededTradeReadError extends Error {
  constructor() {
    super(
      'Ein neuerer Trade-Leseversuch hat diesen Readback ersetzt. Bitte den Buchungsstand erneut prüfen.',
    );
  }
}

export function TradeManagementPage() {
  const [searchParams] = useSearchParams();
  const tradeId = searchParams.get('trade_id') ?? '';
  const location = useLocation();
  if (searchParams.get('view') === 'sources') {
    return <TradeSourcesView key={`${location.key}:${location.search}`} query={searchParams} />;
  }

  // URL identity owns the entire transaction context, including child forms.
  // Reset synchronously on trade changes, not after a render of stale holdings.
  return (
    <TradePendingChangesProvider key={tradeId}>
      <TradeManagementContext tradeId={tradeId} />
    </TradePendingChangesProvider>
  );
}

function TradeManagementContext({ tradeId }: { tradeId: string }) {
  const navigate = useNavigate();
  const { hash } = useLocation();
  const [, setSearchParams] = useSearchParams();
  const [lookupId, setLookupId] = useState(tradeId);
  const active = useRef(false);
  const [trade, setTrade] = useState<TradeResponse | null>(null);
  const [warrant, setWarrant] = useState<WarrantResponse | null>(null);
  const [position, setPosition] = useState<PositionResponse | null>(null);
  const [management, setManagement] = useState<TradeManagementStateResponse | null>(null);
  const [saleQuantity, setSaleQuantity, saleQuantityRef] = useDraft('');
  const [salePrice, setSalePrice, salePriceRef] = useDraft('');
  const [saleDate, setSaleDate, saleDateRef] = useDraft(localToday);
  const initialSaleDate = useRef(saleDate);
  const [saleTime, setSaleTime, saleTimeRef] = useDraft('');
  const [saleCurrency, setSaleCurrency, saleCurrencyRef] = useDraft(emptyExecutionCurrency);
  const saleLock = useRef(false);
  const writeLock = useRef(false);
  const readGeneration = useRef(0);
  const readController = useRef<AbortController | null>(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [historyReloadToken, setHistoryReloadToken] = useState(0);
  const [stopPrice, setStopPrice, stopPriceRef] = useDraft('');
  const [stopBinding, setStopBinding, stopBindingRef] = useDraft<PriceBinding | null>(null);
  const [targetBinding, setTargetBinding, targetBindingRef] = useDraft<PriceBinding | null>(null);
  const [targetPrice, setTargetPrice, targetPriceRef] = useDraft('');
  const [thesis, setThesis, thesisRef] = useDraft('');
  const [note, setNote, noteRef] = useDraft('');
  const managementBasis = useRef<TradeManagementStateResponse | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [pageBusy, setBusy] = useState(false);
  const [bookingBlocked, setBookingBlocked] = useState(false);
  const bookingBlockedRef = useRef(false);
  const isBookingWriteBlocked = useCallback(() => bookingBlockedRef.current, []);
  const onWriteBlockedChange = useCallback((blocked: boolean) => {
    bookingBlockedRef.current = blocked;
    setBookingBlocked(blocked);
  }, []);
  const { notify, isBusy: isContextBusy } = useTradePendingChanges('trade-management', {
    isBusy: () => writeLock.current || saleLock.current,
    isDirty: () => {
      const basis = managementBasis.current;
      return Boolean(
        saleQuantityRef.current ||
          salePriceRef.current ||
          saleDateRef.current !== initialSaleDate.current ||
          saleTimeRef.current ||
          saleCurrencyRef.current.code ||
          saleCurrencyRef.current.note ||
          noteRef.current ||
          (basis &&
            (stopPriceRef.current !== (basis.stop_price ?? '') ||
              !sameBinding(stopBindingRef.current, basis.stop_price_binding ?? null) ||
              targetPriceRef.current !== (basis.target_price ?? '') ||
              !sameBinding(targetBindingRef.current, basis.target_price_binding ?? null) ||
              thesisRef.current !== (basis.thesis ?? ''))),
      );
    },
    onDiscard: () => {
      setSaleQuantity('');
      setSalePrice('');
      setSaleDate(initialSaleDate.current);
      setSaleTime('');
      setSaleCurrency(emptyExecutionCurrency());
      setNote('');
      const basis = managementBasis.current;
      setStopPrice(basis?.stop_price ?? '');
      setStopBinding(basis?.stop_price_binding ?? null);
      setTargetPrice(basis?.target_price ?? '');
      setTargetBinding(basis?.target_price_binding ?? null);
      setThesis(basis?.thesis ?? '');
    },
  });
  const busy = pageBusy || bookingBlocked || isContextBusy();

  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
      readGeneration.current += 1;
      readController.current?.abort();
    };
  }, []);

  const refresh = useCallback(
    async (id: string, signal?: AbortSignal) => {
      if (!active.current) return;
      if (signal?.aborted) throw new SupersededTradeReadError();
      const generation = ++readGeneration.current;
      readController.current?.abort();
      const controller = new AbortController();
      readController.current = controller;
      const abort = () => controller.abort();
      signal?.addEventListener('abort', abort, { once: true });
      const assertCurrent = () => {
        if (controller.signal.aborted || generation !== readGeneration.current)
          throw new SupersededTradeReadError();
      };
      try {
        const [nextTrade, nextPosition, nextManagement] = await Promise.all([
          tradeManagementApiClient.trade(id, controller.signal),
          tradeManagementApiClient.position(id, controller.signal),
          tradeManagementApiClient.managementState(id, controller.signal),
        ]);
        if (!active.current) return;
        assertCurrent();
        if (
          nextTrade.id !== id ||
          nextPosition.trade_id !== id ||
          nextManagement.trade_id !== id ||
          nextPosition.product_id !== nextTrade.product_id
        )
          throw new Error('Der gelesene Stand gehört nicht zu diesem Trade. Bitte erneut laden.');
        const nextWarrant = await warrantApiClient.get(nextTrade.product_id, controller.signal);
        if (!active.current) return;
        assertCurrent();
        if (nextWarrant.id !== nextTrade.product_id)
          throw new Error('Das gelesene Produkt gehört nicht zu diesem Trade. Bitte erneut laden.');
        setTrade(nextTrade);
        setWarrant(nextWarrant);
        setPosition(nextPosition);
        setManagement(nextManagement);
        const basis = managementBasis.current;
        // A booking refresh must not reset another form's unfinished management input.
        // Treat price and its binding as one draft so their instrument context stays together.
        if (
          !basis ||
          (stopPriceRef.current === (basis.stop_price ?? '') &&
            sameBinding(stopBindingRef.current, basis.stop_price_binding ?? null))
        ) {
          setStopPrice(nextManagement.stop_price ?? '');
          setStopBinding(nextManagement.stop_price_binding ?? null);
        }
        if (
          !basis ||
          (targetPriceRef.current === (basis.target_price ?? '') &&
            sameBinding(targetBindingRef.current, basis.target_price_binding ?? null))
        ) {
          setTargetPrice(nextManagement.target_price ?? '');
          setTargetBinding(nextManagement.target_price_binding ?? null);
        }
        if (!basis || thesisRef.current === (basis.thesis ?? ''))
          setThesis(nextManagement.thesis ?? '');
        managementBasis.current = nextManagement;
        // Only the history view is invalidated by a successful readback. The
        // booking editor owns its concurrent timeline read and recovery state.
        if (basis) setHistoryReloadToken((token) => token + 1);
      } catch (error) {
        if (active.current) {
          // A booking readback must not count an aborted/superseded projection
          // as success, even if a newer attempt subsequently fails.
          assertCurrent();
          throw error;
        }
      } finally {
        signal?.removeEventListener('abort', abort);
      }
    },
    [
      setStopPrice,
      setStopBinding,
      setTargetPrice,
      setTargetBinding,
      setThesis,
      stopPriceRef,
      stopBindingRef,
      targetPriceRef,
      targetBindingRef,
      thesisRef,
    ],
  );

  useEffect(() => {
    if (!tradeId) return undefined;
    const controller = new AbortController();
    setBusy(true);
    setMessage(null);
    refresh(tradeId, controller.signal)
      .catch((error: unknown) => {
        if (!controller.signal.aborted && !(error instanceof SupersededTradeReadError)) {
          setMessage(error instanceof Error ? error.message : 'Trade konnte nicht geladen werden.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setBusy(false);
      });
    return () => controller.abort();
  }, [tradeId, refresh]);

  useEffect(() => {
    if (!trade || !position || !['#sale-capture', '#execution-dates'].includes(hash)) return;
    const target = document.getElementById(hash.slice(1));
    target?.scrollIntoView?.({ block: 'start' });
    target?.focus({ preventScroll: true });
  }, [hash, trade, position]);

  function lookupTrade(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const id = lookupId.trim();
    if (!id) return;
    if (pageBusy || isContextBusy()) return;
    if (id === tradeId) {
      setReloadToken((token) => token + 1);
      setBusy(true);
      setMessage(null);
      void refresh(id)
        .catch((error: unknown) => {
          if (active.current && !(error instanceof SupersededTradeReadError))
            setMessage(
              error instanceof Error ? error.message : 'Trade konnte nicht geladen werden.',
            );
        })
        .finally(() => {
          if (active.current) setBusy(false);
        });
    } else setSearchParams({ trade_id: id });
  }

  async function mutate(
    action: () => Promise<unknown>,
    successMessage: string,
    field: 'stop' | 'target' | 'thesis' | 'note',
  ) {
    if (
      !tradeId ||
      trade?.cancelled_at ||
      busy ||
      bookingBlockedRef.current ||
      isContextBusy() ||
      writeLock.current ||
      saleLock.current
    )
      return;
    writeLock.current = true;
    notify();
    setBusy(true);
    setMessage(null);
    const submitted = {
      stop_price: stopPriceRef.current,
      stop_price_binding: stopBindingRef.current,
      target_price: targetPriceRef.current,
      target_price_binding: targetBindingRef.current,
      thesis: thesisRef.current,
      note: noteRef.current,
    };
    let saved = false;
    try {
      await action();
      saved = true;
      if (!active.current) return;
      const basis = managementBasis.current;
      if (basis) {
        if (field === 'stop')
          managementBasis.current = {
            ...basis,
            stop_price: submitted.stop_price,
            stop_price_binding: submitted.stop_price_binding,
          };
        if (field === 'target')
          managementBasis.current = {
            ...basis,
            target_price: submitted.target_price,
            target_price_binding: submitted.target_price_binding,
          };
        if (field === 'thesis') managementBasis.current = { ...basis, thesis: submitted.thesis };
      }
      if (field === 'note' && noteRef.current === submitted.note) setNote('');
      await refresh(tradeId);
      if (active.current) setMessage(successMessage);
    } catch (error: unknown) {
      if (active.current) {
        const detail = error instanceof Error ? error.message : 'Ansicht bitte prüfen.';
        setMessage(
          saved ? `Änderung gespeichert, Ansicht noch nicht aktualisiert. ${detail}` : detail,
        );
      }
    } finally {
      writeLock.current = false;
      if (active.current) {
        setBusy(false);
        notify();
      }
    }
  }

  async function startPostTradeObservation() {
    if (
      !tradeId ||
      !position?.is_closed ||
      trade?.cancelled_at ||
      bookingBlockedRef.current ||
      isContextBusy() ||
      writeLock.current
    )
      return;

    writeLock.current = true;
    notify();
    setBusy(true);
    setMessage(null);

    try {
      await postTradeApiClient.startObservation(tradeId);
      if (active.current) {
        writeLock.current = false;
        notify();
        void navigate(`/post-trade?trade_id=${encodeURIComponent(tradeId)}`);
      }
    } catch (error: unknown) {
      if (active.current) setMessage(postTradeErrorMessage(error));
    } finally {
      writeLock.current = false;
      if (active.current) {
        setBusy(false);
        notify();
      }
    }
  }

  async function submitSale(quantity: number, successMessage: string) {
    if (
      !tradeId ||
      !salePrice ||
      saleLock.current ||
      writeLock.current ||
      isContextBusy() ||
      bookingBlockedRef.current ||
      trade?.cancelled_at
    )
      return;
    saleLock.current = true;
    notify();
    setBusy(true);
    setMessage(null);
    const scope = `sale:${tradeId}`;
    let saved = false;
    try {
      const payload = {
        quantity,
        price_per_unit: salePrice.trim().replace(',', '.'),
        ...executionTime(saleDate, saleTime),
        ...executionCurrencyDeclaration(saleCurrency),
      };
      await tradeManagementApiClient.sell(tradeId, {
        ...payload,
        request_id: captureRequest(scope, payload),
      });
      saved = true;
      if (!active.current) return;
      finishCapture(scope);
      setSaleQuantity('');
      setSalePrice('');
      setSaleTime('');
      setSaleCurrency(emptyExecutionCurrency());
      initialSaleDate.current = saleDateRef.current;
      await refresh(tradeId);
      if (active.current) setMessage(successMessage);
    } catch (error) {
      if (active.current) {
        const detail = error instanceof Error ? error.message : 'Verkauf bitte prüfen.';
        setMessage(
          saved ? `Verkauf gespeichert, Ansicht noch nicht aktualisiert. ${detail}` : detail,
        );
      }
    } finally {
      saleLock.current = false;
      if (active.current) {
        setBusy(false);
        notify();
      }
    }
  }

  async function recordSale(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const quantity = Number(saleQuantity);
    if (!Number.isInteger(quantity) || quantity <= 0 || !salePrice) return;

    await submitSale(quantity, 'Teilverkauf wurde erfasst und die Position neu projiziert.');
  }

  async function closePosition() {
    if (!position || position.is_closed || position.open_quantity <= 0 || !salePrice) return;

    await submitSale(
      position.open_quantity,
      'Vollständiger Verkauf wurde erfasst und die Position neu projiziert.',
    );
  }

  return (
    <main className="min-w-0 w-full space-y-6 [overflow-wrap:anywhere]">
      <header>
        <p className="text-xs uppercase tracking-wide text-slate-500">FT-010</p>
        <h1 className="mt-1 text-2xl font-semibold">Trade Management</h1>
        <p className="mt-2 text-sm text-slate-400">
          Position, wirtschaftliche SELL-Executions und Management-Entscheidungen bleiben getrennte
          fachliche Fakten.
        </p>
      </header>

      {trade && (
        <Link
          className="text-sky-400 underline"
          target="_blank"
          rel="noopener noreferrer"
          to={sourceLink(new URLSearchParams({ trade_id: trade.id }))}
        >
          Quellen und dokumentierte Reflexion lesen (neuer Tab)
        </Link>
      )}

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
            disabled={pageBusy || isContextBusy() || lookupId.trim() === ''}
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
        <section
          aria-label="Trade und Position"
          className="rounded-xl border border-sky-900 bg-sky-950/20 p-5"
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-sky-400">Trade und Position</p>
              <h2 className="mt-1 text-xl font-semibold">
                {tradeReference(trade.id)} · {warrant.display_name}
              </h2>
              <p className="mt-1 text-sm text-slate-400">
                {warrant.isin ? `ISIN ${warrant.isin}` : 'Keine ISIN'}
                {warrant.wkn ? ` · WKN ${warrant.wkn}` : ''}
              </p>
            </div>
            <h3 className="rounded-full border border-sky-800 px-3 py-1 text-xs">
              {trade.cancelled_at ? 'CANCELLED' : position.is_closed ? 'CLOSED' : 'OPEN'}
            </h3>
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
              <dd className="mt-1 font-medium">
                {trade.cancelled_at
                  ? 'Storniert – kein Bestand'
                  : (position.open_quantity ?? 'Nicht verfügbar')}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Nächster Schritt</dt>
              <dd className="mt-1 font-medium">
                {trade.cancelled_at
                  ? 'Stornierung und Historie prüfen'
                  : position.is_closed
                    ? 'Nachbeobachtung starten'
                    : 'Alerts prüfen und Stop/Target aktiv managen'}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Kaufdatum / eröffnet</dt>
              <dd className="mt-1 font-medium">
                {position.opened_on
                  ? `${position.opened_on} (Uhrzeit unbekannt)`
                  : formatDateTime(position.opened_at)}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Verkaufsdatum / geschlossen</dt>
              <dd className="mt-1 font-medium">
                {position.closed_on
                  ? `${position.closed_on} (Uhrzeit unbekannt)`
                  : formatDateTime(position.closed_at)}
              </dd>
            </div>
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
          </dl>
          <details className="mt-4 text-xs text-slate-500">
            <summary className="cursor-pointer">Technische Provenance anzeigen</summary>
            <div className="mt-2 space-y-1 break-all">
              <p>Trade-ID {trade.id}</p>
              <p>Produkt-ID {trade.product_id}</p>
              {trade.trade_plan_id && <p>TradePlan-ID {trade.trade_plan_id}</p>}
              {trade.trade_plan_version_id && (
                <p>TradePlanVersion-ID {trade.trade_plan_version_id}</p>
              )}
              {trade.product_selection_id && (
                <p>ProductSelection-ID {trade.product_selection_id}</p>
              )}
            </div>
          </details>
          {!trade.cancelled_at && (
            <div className="mt-5 min-w-0">
              <PositionPriceHistory
                tradeId={trade.id}
                positionId={position.id}
                reloadToken={historyReloadToken}
              />
            </div>
          )}
        </section>
      )}

      {position && trade && (
        <ExecutionDatesPanel
          key={`dates-${trade.id}`}
          tradeId={trade.id}
          productId={trade.product_id}
          cancelled={Boolean(trade.cancelled_at)}
          reloadToken={reloadToken}
          onWriteBlockedChange={onWriteBlockedChange}
          onChanged={() => refresh(trade.id)}
        />
      )}

      {position && trade && !trade.cancelled_at && (
        <>
          <PositionRiskPanel tradeId={tradeId} />
          <TradeAlertsPanel tradeId={tradeId} />
          {!position.is_closed && (
            <fieldset disabled={bookingBlocked} className="min-w-0">
              <AdditionalPurchasePanel
                key={trade.id}
                tradeId={tradeId}
                isWriteBlocked={isBookingWriteBlocked}
                onChanged={() => refresh(tradeId)}
              />
            </fieldset>
          )}

          <form
            id="sale-capture"
            tabIndex={-1}
            aria-label="Verkauf erfassen"
            onSubmit={(event) => void recordSale(event)}
            className="rounded-xl border border-slate-800 p-5"
          >
            <h2 className="text-lg font-semibold">Verkauf erfassen</h2>
            <p className="mt-1 text-xs text-slate-500">
              Hier wird eine bereits erfolgte Ausführung dokumentiert. Es wird keine Broker-Order
              gesendet. Teil- und Vollausstieg werden aus der effektiven Execution-Historie
              abgeleitet.
            </p>
            {position.is_closed ? (
              <div className="mt-4 space-y-3">
                <p className="text-sm text-slate-400">
                  Die Position ist geschlossen. Weitere Verkäufe können nicht erfasst werden.
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
              <fieldset disabled={busy} className="mt-4 min-w-0 space-y-4">
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  <label className="text-sm">
                    <span className="text-slate-400">Verkaufte Stückzahl</span>
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
                    <span className="mt-1 block text-xs text-slate-500">
                      Maximal {position.open_quantity} Stück offen.
                    </span>
                  </label>
                  <label className="text-sm">
                    <span className="text-slate-400">Verkaufspreis je Einheit</span>
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
                  <ExecutionDateInput
                    label="Verkaufsdatum"
                    date={saleDate}
                    time={saleTime}
                    onDate={setSaleDate}
                    onTime={setSaleTime}
                  />
                </div>

                <ExecutionCurrencyOverride
                  value={saleCurrency}
                  onChange={setSaleCurrency}
                  disabled={busy}
                />

                <div className="grid gap-3 sm:grid-cols-2">
                  <button
                    type="submit"
                    disabled={busy || saleQuantity === '' || salePrice === ''}
                    className="rounded-lg border border-slate-600 px-4 py-2 disabled:opacity-50"
                  >
                    Teilverkauf erfassen
                  </button>
                  <button
                    type="button"
                    disabled={busy || salePrice === ''}
                    onClick={() => void closePosition()}
                    className="rounded-lg border border-amber-700 px-4 py-2 disabled:opacity-50"
                  >
                    Position vollständig schließen
                  </button>
                </div>
                <p className="text-xs text-slate-500">
                  „Position vollständig schließen“ erfasst einen Verkauf über alle aktuell{' '}
                  {position.open_quantity} offenen Stück. Die Reststückzahl muss nicht manuell
                  eingegeben werden.
                </p>
              </fieldset>
            )}
          </form>
        </>
      )}

      {management && position && !trade?.cancelled_at && (
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
                  () =>
                    tradeManagementApiClient.changeStop(tradeId, {
                      price: stopPrice,
                      price_binding: stopBinding,
                    }),
                  'Stop wurde aktualisiert.',
                  'stop',
                );
              }}
              className="space-y-2"
            >
              {warrant && (
                <PriceBindingInput
                  label="Stop"
                  value={stopBinding}
                  warrantId={warrant.id}
                  underlyingId={warrant.underlying_id}
                  onChange={setStopBinding}
                />
              )}
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
              <button
                disabled={busy || !stopBinding || !/^[A-Z]{3}$/.test(stopBinding.currency)}
                className="rounded-lg border border-slate-600 px-3 py-2"
              >
                Stop speichern
              </button>
            </form>

            <form
              onSubmit={(event) => {
                event.preventDefault();
                void mutate(
                  () =>
                    tradeManagementApiClient.changeTarget(tradeId, {
                      price: targetPrice,
                      price_binding: targetBinding,
                    }),
                  'Target wurde aktualisiert.',
                  'target',
                );
              }}
              className="space-y-2"
            >
              {warrant && (
                <PriceBindingInput
                  label="Target"
                  value={targetBinding}
                  warrantId={warrant.id}
                  underlyingId={warrant.underlying_id}
                  onChange={setTargetBinding}
                />
              )}
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
              <button
                disabled={busy || !targetBinding || !/^[A-Z]{3}$/.test(targetBinding.currency)}
                className="rounded-lg border border-slate-600 px-3 py-2"
              >
                Target speichern
              </button>
            </form>

            <form
              onSubmit={(event) => {
                event.preventDefault();
                void mutate(
                  () => tradeManagementApiClient.updateThesis(tradeId, { text: thesis }),
                  'These wurde aktualisiert.',
                  'thesis',
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
                  'note',
                );
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
      {trade && warrant && (
        <div className="min-w-0">
          <TradeCancellationPanel
            key={trade.id}
            trade={trade}
            productName={warrant.display_name}
            isWriteBlocked={isBookingWriteBlocked}
            onChanged={() => refresh(tradeId)}
          />
        </div>
      )}
    </main>
  );
}
