import { FormEvent, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { Link, UNSAFE_DataRouterContext, useSearchParams } from 'react-router-dom';

import { PendingNavigationGuard } from '../../../components/PendingNavigationGuard';

import { ExecutionDateInput } from '../../trade/components/ExecutionDateInput';
import { ExecutionCurrencyPreview } from '../../trade/components/ExecutionCurrencyPreview';
import {
  emptyExecutionCurrency,
  executionCurrencyDeclaration,
  executionCurrencyText,
} from '../../trade/services/executionCurrency';
import {
  captureRequest,
  executionTime,
  finishCapture,
  localToday,
} from '../../trade/services/capture';
import { MarketApiError } from '../../market/services/http';
import { tradeManagementApiClient } from '../../trade/services/client';
import type { InitialPurchaseResponse } from '../../trade/types/api';
import { selectionRepairUrl } from '../../product/services/selectionRepairContext';
import { SelectionProductIdentity } from '../components/SelectionProductIdentity';
import { useSelectionReferenceData } from '../services/useSelectionReferenceData';
import { productSelectionApiClient } from '../services/client';
import {
  assertRunContext,
  loadSelectionPlanContext,
  selectionRoute,
  type SelectionPlanContext,
} from '../services/planContext';
import type {
  CriterionResultResponse,
  EligibilityStatus,
  EvaluationMetricResponse,
  ProductEvaluationResponse,
  ProductSelectionRunDetailResponse,
  ProductSelectionRunSummaryResponse,
} from '../types/api';

function eligibilityClass(status: EligibilityStatus): string {
  if (status === 'ELIGIBLE') return 'border-emerald-700 text-emerald-300';
  if (status === 'INELIGIBLE') return 'border-rose-800 text-rose-300';
  return 'border-amber-700 text-amber-300';
}

function criterionClass(outcome: CriterionResultResponse['outcome']): string {
  if (outcome === 'FULFILLED') return 'text-emerald-300';
  if (outcome === 'NOT_FULFILLED') return 'text-rose-300';
  if (outcome === 'NOT_EVALUABLE') return 'text-amber-300';
  return 'text-slate-400';
}

function metricLabel(metric: EvaluationMetricResponse): string {
  if (metric.value === null) return '—';
  return `${metric.value}${metric.unit ? ` ${metric.unit}` : ''}`;
}

function tradeReference(id: string): string {
  return `TR-${id.slice(0, 8).toUpperCase()}`;
}

function EvaluationCard({
  evaluation,
  selected,
  disabled,
  onChoose,
  references,
}: {
  references: ReturnType<typeof useSelectionReferenceData>;
  evaluation: ProductEvaluationResponse;
  selected: boolean;
  disabled: boolean;
  onChoose: (evaluation: ProductEvaluationResponse) => void;
}) {
  const bid = evaluation.metrics.find((metric) => metric.metric_id === 'bid');
  const ask = evaluation.metrics.find((metric) => metric.metric_id === 'ask');
  const spread = evaluation.metrics.find((metric) => metric.metric_id.includes('spread'));

  return (
    <article
      className={`rounded-xl border p-5 ${
        selected ? 'border-sky-600 bg-sky-950/20' : 'border-slate-800'
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">Produkt</p>
          <SelectionProductIdentity
            productId={evaluation.warrant_id}
            product={references.products[evaluation.warrant_id]}
            loading={references.loading}
            heading
          />
          <details className="mt-2 text-xs text-slate-500">
            <summary className="cursor-pointer">Technische Listing-ID</summary>
            <p className="mt-1 break-all">Listing {evaluation.warrant_listing_id}</p>
          </details>
        </div>
        <span
          className={`rounded-full border px-3 py-1 text-xs ${eligibilityClass(
            evaluation.eligibility_status,
          )}`}
        >
          {evaluation.eligibility_status}
        </span>
      </div>

      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-slate-500">Bid</dt>
          <dd>{bid ? metricLabel(bid) : '—'}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Ask</dt>
          <dd>{ask ? metricLabel(ask) : '—'}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Spread</dt>
          <dd>{spread ? metricLabel(spread) : '—'}</dd>
        </div>
      </dl>

      {evaluation.reasons.length > 0 && (
        <div className="mt-4 rounded-lg border border-slate-800 bg-slate-950/40 p-3">
          <p className="text-xs uppercase tracking-wide text-slate-500">Begründung</p>
          <ul className="mt-2 space-y-1 text-sm text-slate-300">
            {evaluation.reasons.map((reason) => (
              <li key={reason}>• {reason}</li>
            ))}
          </ul>
        </div>
      )}

      <details className="mt-4 rounded-lg border border-slate-800 p-3">
        <summary className="cursor-pointer text-sm font-medium">Bewertungsdetails</summary>
        <div className="mt-4 space-y-4">
          <section>
            <h4 className="text-xs uppercase tracking-wide text-slate-500">Kriterien</h4>
            <ul className="mt-2 space-y-2">
              {evaluation.criteria.map((criterion) => (
                <li key={criterion.criterion_id} className="rounded border border-slate-800 p-3">
                  <div className="flex flex-wrap justify-between gap-2 text-sm">
                    <span className="font-medium">{criterion.criterion_id}</span>
                    <span className={criterionClass(criterion.outcome)}>{criterion.outcome}</span>
                  </div>
                  <p className="mt-1 text-sm text-slate-400">{criterion.explanation}</p>
                  {(criterion.actual_value || criterion.expected_value) && (
                    <p className="mt-1 text-xs text-slate-500">
                      Ist {criterion.actual_value ?? '—'} · Erwartet{' '}
                      {criterion.expected_value ?? '—'}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          </section>

          <section>
            <h4 className="text-xs uppercase tracking-wide text-slate-500">Daten / Inputs</h4>
            <ul className="mt-2 space-y-2 text-sm">
              {evaluation.inputs.map((input) => (
                <li
                  key={`${input.name}-${input.source}`}
                  className="rounded border border-slate-800 p-3"
                >
                  <div className="flex flex-wrap justify-between gap-2">
                    <span className="font-medium">{input.name}</span>
                    <span className="text-slate-400">{input.availability}</span>
                  </div>
                  <p className="mt-1 text-slate-400">
                    {input.value ?? 'kein Wert'} · Quelle {input.source}
                    {input.quality ? ` · Qualität ${input.quality}` : ''}
                  </p>
                </li>
              ))}
            </ul>
          </section>

          {evaluation.metrics.length > 0 && (
            <section>
              <h4 className="text-xs uppercase tracking-wide text-slate-500">Kennzahlen</h4>
              <ul className="mt-2 space-y-2 text-sm">
                {evaluation.metrics.map((metric) => (
                  <li key={metric.metric_id} className="rounded border border-slate-800 p-3">
                    <div className="flex flex-wrap justify-between gap-2">
                      <span className="font-medium">{metric.metric_id}</span>
                      <span>{metricLabel(metric)}</span>
                    </div>
                    <p className="mt-1 text-xs text-slate-500">
                      {metric.origin} · {metric.source}
                      {metric.formula_or_rule ? ` · ${metric.formula_or_rule}` : ''}
                    </p>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      </details>

      <div className="mt-4 flex justify-end">
        <button
          type="button"
          disabled={disabled || evaluation.eligibility_status === 'INELIGIBLE'}
          onClick={() => onChoose(evaluation)}
          className="rounded-lg border border-emerald-700 px-3 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-40"
        >
          {selected ? 'Ausgewählt' : 'Dieses Produkt auswählen'}
        </button>
      </div>
    </article>
  );
}

export function ProductSelectionPage() {
  const references = useSelectionReferenceData();
  const dataRouter = useContext(UNSAFE_DataRouterContext);
  const [searchParams, setSearchParams] = useSearchParams();
  const contextKey = searchParams.toString();
  const currentContext = useRef({ key: contextKey, revision: 0 });
  if (currentContext.current.key !== contextKey) {
    currentContext.current = { key: contextKey, revision: currentContext.current.revision + 1 };
  }
  const contextRevision = currentContext.current.revision;
  const [loadedContext, setContext] = useState<
    (SelectionPlanContext & { routeKey: string; revision: number }) | null
  >(null);
  const context =
    loadedContext?.routeKey === contextKey && loadedContext.revision === contextRevision
      ? loadedContext
      : null;
  const [contextLoading, setContextLoading] = useState(true);
  const [readRevision, setReadRevision] = useState(0);
  const [contextError, setContextError] = useState<string | null>(null);
  // Carry only a confirmed POST result through its canonical run URL. A failed
  // history refresh must never discard that receipt or repeat the write.
  const confirmedNavigation = useRef<{
    routeKey: string;
    detail: ProductSelectionRunDetailResponse;
    context: SelectionPlanContext;
  } | null>(null);
  const interactionLock = useRef(false);
  const mounted = useRef(true);
  const tradePlanId = context?.detail.plan.id ?? '';
  const tradePlanVersionId = context?.version.id ?? '';
  const canStart = context?.version.status === 'APPROVED';
  const [runs, setRuns] = useState<ProductSelectionRunSummaryResponse[]>([]);
  const [loadedRun, setLoadedRun] = useState<{
    routeKey: string;
    revision: number;
    value: ProductSelectionRunDetailResponse;
  } | null>(null);
  const detail =
    loadedRun?.routeKey === contextKey && loadedRun.revision === contextRevision
      ? loadedRun.value
      : null;
  const setDetail = useCallback(
    (value: ProductSelectionRunDetailResponse | null) => {
      setLoadedRun(value ? { routeKey: contextKey, revision: contextRevision, value } : null);
    },
    [contextKey, contextRevision],
  );
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [pendingSelection, setPendingSelection] = useState<ProductEvaluationResponse | null>(null);
  const [rationale, setRationale] = useState('');
  const [purchaseQuantity, setPurchaseQuantity] = useState('');
  const [purchasePrice, setPurchasePrice] = useState('');
  const initialPurchaseDate = useRef(localToday());
  const [purchaseDate, setPurchaseDate] = useState(initialPurchaseDate.current);
  const [purchaseTime, setPurchaseTime] = useState('');
  const [purchaseCurrency, setPurchaseCurrency] = useState(emptyExecutionCurrency);
  const [existingTradeId, setExistingTradeId] = useState<string | null>(null);
  const purchaseLock = useRef(false);
  const [purchase, setPurchase] = useState<InitialPurchaseResponse | null>(null);

  useEffect(() => {
    setPurchaseCurrency(emptyExecutionCurrency());
  }, [detail?.selection?.id]);

  const counts = useMemo(() => {
    const evaluations = detail?.evaluations ?? [];
    return {
      eligible: evaluations.filter((item) => item.eligibility_status === 'ELIGIBLE').length,
      ineligible: evaluations.filter((item) => item.eligibility_status === 'INELIGIBLE').length,
      notEvaluable: evaluations.filter((item) => item.eligibility_status === 'NOT_EVALUABLE')
        .length,
    };
  }, [detail]);

  const selectedEvaluation = useMemo(() => {
    if (!detail?.selection) return null;
    return (
      detail.evaluations.find(
        (evaluation) => evaluation.id === detail.selection?.product_evaluation_id,
      ) ?? null
    );
  }, [detail]);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const hasUnsavedInputs = Boolean(
    pendingSelection ||
      rationale ||
      (!purchase &&
        (purchaseQuantity ||
          purchasePrice ||
          purchaseDate !== initialPurchaseDate.current ||
          purchaseTime ||
          purchaseCurrency.code ||
          purchaseCurrency.note)),
  );

  useEffect(() => {
    const controller = new AbortController();
    const route = selectionRoute(new URLSearchParams(contextKey));
    const receipt =
      confirmedNavigation.current?.routeKey === contextKey ? confirmedNavigation.current : null;
    confirmedNavigation.current = null;
    setContext(null);
    setContextError(null);
    setDetail(null);
    setRuns([]);
    setMessage(
      receipt ? 'Produktsuche wurde als neuer historischer Selection Run durchgeführt.' : null,
    );
    setPendingSelection(null);
    setRationale('');
    setPurchase(null);
    setPurchaseQuantity('');
    setPurchasePrice('');
    setPurchaseTime('');
    initialPurchaseDate.current = localToday();
    setPurchaseDate(initialPurchaseDate.current);
    setPurchaseCurrency(emptyExecutionCurrency());
    setExistingTradeId(null);
    interactionLock.current = false;
    purchaseLock.current = false;
    setBusy(false);
    if (route.kind === 'invalid') {
      setContextLoading(false);
      setContextError(route.message);
      return () => controller.abort();
    }
    setContextLoading(true);
    async function load() {
      try {
        let planId = route.kind === 'invalid' ? '' : route.planId;
        let versionId = route.kind === 'invalid' ? '' : route.versionId;
        let loadedRun: ProductSelectionRunDetailResponse | null = receipt?.detail ?? null;
        if (route.kind === 'run') {
          loadedRun =
            loadedRun ?? (await productSelectionApiClient.get(route.runId, controller.signal));
          assertRunContext(loadedRun, {
            runId: route.runId,
            planId: route.planId || undefined,
            versionId: route.versionId || undefined,
          });
          if (controller.signal.aborted) return;
          planId = loadedRun.run.trade_plan_id;
          versionId = loadedRun.run.trade_plan_version_id;
          // A saved run stays readable even when its plan cannot currently be reloaded.
          setDetail(loadedRun);
        }
        const loaded =
          receipt?.context ??
          (await loadSelectionPlanContext(planId, versionId, controller.signal));
        if (loadedRun)
          assertRunContext(loadedRun, {
            planId,
            versionId,
            underlyingId: loaded.detail.plan.underlying_id,
          });
        if (controller.signal.aborted) return;
        setContext({ ...loaded, routeKey: contextKey, revision: contextRevision });
        try {
          const items = await productSelectionApiClient.listForTradePlanVersion(
            versionId,
            controller.signal,
          );
          if (controller.signal.aborted) return;
          if (
            items.some(
              (item) => item.trade_plan_id !== planId || item.trade_plan_version_id !== versionId,
            )
          ) {
            throw new Error('Die geladenen Runs gehören nicht zur ausgewählten Planversion.');
          }
          setRuns(items);
        } catch (error: unknown) {
          if (!controller.signal.aborted)
            setMessage(
              receipt
                ? `Selection Run wurde gespeichert. Nur das Neuladen der Historie ist fehlgeschlagen: ${error instanceof Error ? error.message : 'Unbekannter Lesefehler'}`
                : error instanceof Error
                  ? error.message
                  : 'Historische Runs konnten nicht geladen werden.',
            );
        }
      } catch (error: unknown) {
        if (!controller.signal.aborted)
          setContextError(
            error instanceof Error
              ? error.message
              : 'Die angeforderte Planversion konnte nicht geladen werden.',
          );
      } finally {
        if (!controller.signal.aborted) setContextLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [contextKey, contextRevision, readRevision, setDetail]);

  function isCurrent(key: string) {
    return (
      mounted.current &&
      currentContext.current.key === key &&
      currentContext.current.revision === contextRevision
    );
  }

  function mayLeaveContext(navigation = false) {
    if (interactionLock.current || busy) return false;
    if (navigation && dataRouter) return true;
    return (
      !hasUnsavedInputs ||
      window.confirm('Ungespeicherte Eingaben verwerfen und den Kontext wechseln?')
    );
  }

  async function refreshRuns(versionId: string, key = contextKey) {
    const items = await productSelectionApiClient.listForTradePlanVersion(versionId);
    if (!isCurrent(key)) return;
    if (
      items.some(
        (item) => item.trade_plan_id !== tradePlanId || item.trade_plan_version_id !== versionId,
      )
    ) {
      throw new Error('Die geladenen Runs gehören nicht zur ausgewählten Planversion.');
    }
    setRuns(items);
  }

  async function reloadRuns() {
    if (interactionLock.current || !tradePlanVersionId) return;
    const key = contextKey;
    interactionLock.current = true;
    setBusy(true);
    try {
      await refreshRuns(tradePlanVersionId, key);
    } catch (error: unknown) {
      if (isCurrent(key))
        setMessage(
          error instanceof Error ? error.message : 'Historische Runs konnten nicht geladen werden.',
        );
    } finally {
      if (isCurrent(key)) {
        interactionLock.current = false;
        setBusy(false);
      }
    }
  }

  async function startRun(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!context || !canStart || contextLoading || interactionLock.current) return;
    if (!mayLeaveContext()) return;
    const key = contextKey;
    interactionLock.current = true;
    setBusy(true);
    setMessage(null);
    try {
      const created = await productSelectionApiClient.start({
        trade_plan_id: tradePlanId,
        trade_plan_version_id: tradePlanVersionId,
      });
      if (!isCurrent(key)) return;
      assertRunContext(created, {
        planId: tradePlanId,
        versionId: tradePlanVersionId,
        underlyingId: context.detail.plan.underlying_id,
      });
      setDetail(created);
      setPendingSelection(null);
      setRationale('');
      setPurchase(null);
      setPurchaseQuantity('');
      setPurchasePrice('');
      setPurchaseTime('');
      initialPurchaseDate.current = localToday();
      setPurchaseDate(initialPurchaseDate.current);
      setPurchaseCurrency(emptyExecutionCurrency());
      setExistingTradeId(null);
      setMessage('Produktsuche wurde als neuer historischer Selection Run durchgeführt.');
      const runSearch = new URLSearchParams({ run_id: created.run.id });
      if (runSearch.toString() !== contextKey) {
        confirmedNavigation.current = {
          routeKey: runSearch.toString(),
          detail: created,
          context: { detail: context.detail, version: context.version },
        };
        interactionLock.current = false;
        setBusy(false);
        setSearchParams(runSearch, { replace: true });
        return;
      }
      try {
        await refreshRuns(tradePlanVersionId, key);
      } catch (error: unknown) {
        if (isCurrent(key))
          setMessage(
            `Selection Run wurde gespeichert. Nur das Neuladen der Historie ist fehlgeschlagen: ${error instanceof Error ? error.message : 'Unbekannter Lesefehler'}`,
          );
      }
    } catch (error: unknown) {
      if (isCurrent(key))
        setMessage(
          error instanceof Error ? error.message : 'Produktsuche konnte nicht gestartet werden.',
        );
    } finally {
      if (isCurrent(key)) {
        interactionLock.current = false;
        setBusy(false);
      }
    }
  }

  function loadRun(runId: string) {
    const next = new URLSearchParams({ run_id: runId });
    const sameContext = next.toString() === contextKey;
    // Reloading this URL does not invoke the router's navigation blocker.
    if (!mayLeaveContext(!sameContext)) return;
    if (sameContext) {
      interactionLock.current = true;
      setBusy(true);
      setReadRevision((revision) => revision + 1);
    } else {
      setSearchParams(next);
    }
  }

  async function confirmSelection() {
    if (
      !detail ||
      !pendingSelection ||
      busy ||
      contextLoading ||
      contextError ||
      interactionLock.current
    )
      return;
    if (pendingSelection.eligibility_status === 'NOT_EVALUABLE' && rationale.trim() === '') return;
    const key = contextKey;
    interactionLock.current = true;
    setBusy(true);
    setMessage(null);
    try {
      const updated = await productSelectionApiClient.select(detail.run.id, {
        product_evaluation_id: pendingSelection.id,
        rationale: rationale.trim() || null,
      });
      if (!isCurrent(key)) return;
      assertRunContext(updated, {
        runId: detail.run.id,
        planId: detail.run.trade_plan_id,
        versionId: detail.run.trade_plan_version_id,
        underlyingId: detail.run.underlying_id,
      });
      setDetail(updated);
      setPendingSelection(null);
      setRationale('');
      setPurchase(null);
      setMessage(
        'Produktauswahl wurde dokumentiert. Nächster Schritt: tatsächlichen Kauf als BUY erfassen.',
      );
    } catch (error: unknown) {
      if (isCurrent(key))
        setMessage(
          error instanceof Error
            ? error.message
            : 'Produktauswahl konnte nicht gespeichert werden.',
        );
    } finally {
      if (isCurrent(key)) {
        interactionLock.current = false;
        setBusy(false);
      }
    }
  }

  async function recordPurchase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      !detail?.selection ||
      busy ||
      contextLoading ||
      contextError ||
      interactionLock.current ||
      purchaseLock.current ||
      purchase
    )
      return;
    const quantity = Number(purchaseQuantity);
    if (!Number.isInteger(quantity) || quantity <= 0 || purchasePrice.trim() === '') return;

    const key = contextKey;
    interactionLock.current = true;
    purchaseLock.current = true;
    setBusy(true);
    setMessage(null);
    try {
      const scope = `selection:${detail.selection.id}`;
      const payload = {
        product_selection_id: detail.selection.id,
        quantity,
        price_per_unit: purchasePrice.trim().replace(',', '.'),
        ...executionTime(purchaseDate, purchaseTime),
        ...executionCurrencyDeclaration(purchaseCurrency),
      };
      const created = await tradeManagementApiClient.purchaseFromSelection({
        ...payload,
        request_id: captureRequest(scope, payload),
      });
      finishCapture(scope);
      if (!isCurrent(key)) return;
      setPurchase(created);
      setPurchaseCurrency(emptyExecutionCurrency());
      setMessage(
        `Kauf wurde als BUY erfasst. Trade ${tradeReference(created.trade.id)} und offene Position wurden erstellt.`,
      );
    } catch (error: unknown) {
      if (!isCurrent(key)) return;
      if (error instanceof MarketApiError && error.response.code === 'OPEN_TRADE_EXISTS') {
        const id = error.response.details.find(
          (item) => typeof item.context?.existing_trade_id === 'string',
        )?.context?.existing_trade_id;
        if (typeof id === 'string') setExistingTradeId(id);
      }
      setMessage(error instanceof Error ? error.message : 'Kauf konnte nicht erfasst werden.');
    } finally {
      if (isCurrent(key)) {
        setBusy(false);
        purchaseLock.current = false;
        interactionLock.current = false;
      }
    }
  }

  return (
    <div
      className="w-full space-y-8"
      onClickCapture={(event) => {
        const target = event.target;
        if (
          target instanceof Element &&
          target.closest('a') &&
          !dataRouter &&
          !mayLeaveContext(true)
        )
          event.preventDefault();
      }}
    >
      <PendingNavigationGuard
        shouldBlock={() =>
          !confirmedNavigation.current && (interactionLock.current || hasUnsavedInputs)
        }
        busy={busy}
      />
      <div>
        <p className="text-xs uppercase tracking-wide text-slate-500">FT-008</p>
        <h1 className="mt-1 text-2xl font-semibold">Produktauswahl</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-400">
          Transparente Entscheidungshilfe für eine freigegebene TradePlanVersion. Das System
          bewertet und erklärt; die endgültige Produktauswahl bleibt eine separate
          Benutzerentscheidung.
        </p>
      </div>

      {message && !pendingSelection && (
        <p role="status" className="rounded-lg border border-slate-700 p-3 text-sm">
          {message}
        </p>
      )}
      <p className="text-xs text-slate-500">
        Produktnamen, WKN, ISIN und Basiswertnamen stammen aus den aktuellen Stammdaten. Die
        historische Bewertung und die dokumentierte Produktauswahl bleiben unverändert.
      </p>
      {references.errors.length > 0 && (
        <div role="status" className="rounded-lg border border-amber-800 p-3 text-sm">
          <p>{references.errors.join(' ')} Technische IDs bleiben zur Prüfung sichtbar.</p>
          <button type="button" onClick={references.reload} className="mt-2 underline">
            Bezeichnungen erneut laden
          </button>
        </div>
      )}

      <div className="grid gap-8 xl:grid-cols-[21rem_1fr]">
        <aside className="space-y-5">
          <form
            onSubmit={(event) => void startRun(event)}
            className="rounded-xl border border-slate-800 p-5"
          >
            <h2 className="font-semibold">Planversion für die Produktauswahl</h2>
            {contextLoading && (
              <p role="status" className="mt-3 text-sm">
                Planversion wird geladen …
              </p>
            )}
            {contextError && (
              <p role="alert" className="mt-3 text-sm text-rose-200">
                {contextError}
              </p>
            )}
            {context && (
              <>
                <p className="mt-3 break-words font-medium">
                  TradePlan für{' '}
                  {references.plans[tradePlanId]?.underlying_name ||
                    'Basiswertname nicht verfügbar'}
                </p>
                <p className="mt-2 text-sm">
                  Version {context.version.version} · {context.version.status}
                </p>
                <p className="mt-1 text-xs text-slate-400">
                  {context.detail.plan.origin_type === 'MANUAL'
                    ? 'Manueller Ursprung'
                    : 'Ursprung aus gespeicherter Kandidatenbewertung'}
                </p>
                {!canStart && (
                  <p className="mt-3 text-sm text-amber-200">
                    Diese Version ist nicht mehr APPROVED. Historische Runs bleiben lesbar. Für eine
                    neue Bewertung eine freigegebene Version auswählen.
                  </p>
                )}
                <Link
                  className="mt-3 inline-block text-sm text-sky-300 underline"
                  to={`/trade-plans?${new URLSearchParams({ trade_plan_id: tradePlanId, trade_plan_version_id: tradePlanVersionId })}`}
                >
                  Ausgewählte Planversion ansehen
                </Link>
                <details className="mt-3 break-all text-xs text-slate-500">
                  <summary className="cursor-pointer">Technische Planreferenzen</summary>
                  <p>TradePlan-ID {tradePlanId}</p>
                  <p>TradePlanVersion-ID {tradePlanVersionId}</p>
                </details>
              </>
            )}
            <button
              type="button"
              disabled={busy}
              className="mt-4 text-sm text-sky-300 underline disabled:opacity-40"
              onClick={() => {
                if (mayLeaveContext(true)) setSearchParams({});
              }}
            >
              Anderen Plan auswählen
            </button>
            <button
              disabled={busy || contextLoading || !canStart}
              type="submit"
              className="mt-4 w-full rounded-lg border border-sky-700 px-3 py-2 text-sm disabled:opacity-40"
            >
              Produkte neu bewerten
            </button>
          </form>

          <section className="rounded-xl border border-slate-800 p-5">
            <div className="flex items-center justify-between gap-2">
              <h2 className="font-semibold">Historische Runs</h2>
              {tradePlanVersionId.trim() && (
                <button
                  type="button"
                  className="text-xs text-sky-400"
                  disabled={busy || contextLoading}
                  onClick={() => void reloadRuns()}
                >
                  Aktualisieren
                </button>
              )}
            </div>
            <div className="mt-3 space-y-2">
              {runs.map((run) => (
                <button
                  type="button"
                  key={run.id}
                  disabled={busy}
                  onClick={() => loadRun(run.id)}
                  className={`w-full rounded-lg border p-3 text-left text-sm ${
                    detail?.run.id === run.id ? 'border-sky-600 bg-sky-950/20' : 'border-slate-800'
                  }`}
                >
                  <span className="block">
                    {new Date(run.evaluated_at).toLocaleString('de-DE')}
                  </span>
                  <span className="mt-1 block break-all text-xs text-slate-500">{run.id}</span>
                </button>
              ))}
              {runs.length === 0 && (
                <p className="text-sm text-slate-500">Noch keine Runs geladen.</p>
              )}
            </div>
          </section>
        </aside>

        <div>
          {detail ? (
            <div className="space-y-6">
              <section className="rounded-xl border border-slate-800 p-5">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">Selection Run</p>
                    <p className="mt-1 break-words font-semibold">
                      Basiswert:{' '}
                      {references.plans[detail.run.trade_plan_id]?.underlying_name ||
                        (references.loading ? 'wird geladen …' : 'Name nicht verfügbar')}
                    </p>
                    <h2 className="mt-1 text-lg font-semibold">
                      {new Date(detail.run.evaluated_at).toLocaleString('de-DE')}
                    </h2>
                    <p className="mt-1 break-all text-xs text-slate-500">{detail.run.id}</p>
                  </div>
                  <Link
                    to={{
                      pathname: '/trade-plans',
                      search: new URLSearchParams({
                        trade_plan_id: detail.run.trade_plan_id,
                        trade_plan_version_id: detail.run.trade_plan_version_id,
                      }).toString(),
                    }}
                    className="rounded-lg border border-slate-700 px-3 py-2 text-xs"
                  >
                    Ursprüngliche Planversion ansehen
                  </Link>
                </div>
                <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-4">
                  <div>
                    <dt className="text-slate-500">Betrachtet</dt>
                    <dd className="text-lg font-semibold">{detail.evaluations.length}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Eligible</dt>
                    <dd className="text-lg font-semibold text-emerald-300">{counts.eligible}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Ineligible</dt>
                    <dd className="text-lg font-semibold text-rose-300">{counts.ineligible}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Nicht bewertbar</dt>
                    <dd className="text-lg font-semibold text-amber-300">{counts.notEvaluable}</dd>
                  </div>
                </dl>
              </section>

              {detail.selection && (
                <section className="rounded-xl border border-emerald-800 bg-emerald-950/20 p-5">
                  <p className="text-xs uppercase tracking-wide text-emerald-400">
                    Benutzerentscheidung
                  </p>
                  <h2 className="mt-1 font-semibold">Produkt ausgewählt</h2>
                  {selectedEvaluation && (
                    <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                      <div>
                        <dt className="text-slate-500">Ausgewähltes Produkt</dt>
                        <dd>
                          <SelectionProductIdentity
                            productId={selectedEvaluation.warrant_id}
                            product={references.products[selectedEvaluation.warrant_id]}
                            loading={references.loading}
                          />
                        </dd>
                      </div>
                      <div>
                        <dt className="text-slate-500">Listing</dt>
                        <dd className="break-all">{selectedEvaluation.warrant_listing_id}</dd>
                      </div>
                    </dl>
                  )}
                  <p className="mt-3 break-all text-xs text-slate-500">
                    Selection {detail.selection.id} · Evaluation{' '}
                    {detail.selection.product_evaluation_id}
                  </p>
                  <p className="mt-1 text-xs text-slate-400">
                    {new Date(detail.selection.selected_at).toLocaleString('de-DE')} · Actor{' '}
                    {detail.selection.selected_by}
                  </p>
                  {detail.selection.rationale && (
                    <p className="mt-3 text-sm text-slate-300">{detail.selection.rationale}</p>
                  )}

                  {!purchase ? (
                    <form
                      onSubmit={(event) => void recordPurchase(event)}
                      className="mt-5 rounded-lg border border-slate-700 bg-slate-950/50 p-4"
                    >
                      <fieldset disabled={busy || contextLoading || Boolean(contextError)}>
                        <h3 className="font-medium">
                          Nächster Schritt: tatsächlichen Kauf erfassen
                        </h3>
                        {selectedEvaluation && (
                          <p className="mt-2 break-words text-sm font-medium">
                            Kauf für:{' '}
                            {references.products[selectedEvaluation.warrant_id]?.display_name ||
                              'Produktname nicht verfügbar'}
                          </p>
                        )}
                        {existingTradeId && (
                          <p role="alert">
                            Offener Trade vorhanden.{' '}
                            <Link
                              className="underline"
                              to={`/trade-management?trade_id=${encodeURIComponent(existingTradeId)}`}
                            >
                              Bestehenden Trade öffnen und Nachkauf erfassen
                            </Link>
                            . Es wurde nichts zusätzlich gebucht.
                          </p>
                        )}
                        <ExecutionDateInput
                          label="Kaufdatum"
                          date={purchaseDate}
                          time={purchaseTime}
                          onDate={setPurchaseDate}
                          onTime={setPurchaseTime}
                        />
                        <p className="mt-1 text-xs text-slate-400">
                          Erst dieser BUY erzeugt den Trade und die offene Position. Die
                          Produktauswahl allein ist noch keine Ausführung.
                        </p>
                        <div className="mt-4 grid gap-3 sm:grid-cols-2">
                          <label className="text-sm">
                            <span className="text-slate-400">Kaufmenge</span>
                            <input
                              aria-label="Kaufmenge"
                              type="number"
                              min="1"
                              step="1"
                              required
                              value={purchaseQuantity}
                              onChange={(event) => setPurchaseQuantity(event.target.value)}
                              className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2"
                            />
                          </label>
                          <label className="text-sm">
                            <span className="text-slate-400">
                              Tatsächlicher Kaufpreis je Einheit
                            </span>
                            <input
                              aria-label="Kaufpreis"
                              inputMode="decimal"
                              required
                              value={purchasePrice}
                              onChange={(event) => setPurchasePrice(event.target.value)}
                              placeholder="z. B. 2,35"
                              className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2"
                            />
                          </label>
                        </div>
                        {selectedEvaluation && (
                          <ExecutionCurrencyPreview
                            context={{ productId: selectedEvaluation.warrant_id, side: 'BUY' }}
                            date={purchaseDate}
                            time={purchaseTime}
                            value={purchaseCurrency}
                            onChange={setPurchaseCurrency}
                            disabled={busy}
                          />
                        )}
                        <button
                          type="submit"
                          disabled={
                            busy || purchaseQuantity.trim() === '' || purchasePrice.trim() === ''
                          }
                          className="mt-4 rounded-lg border border-sky-700 px-4 py-2 text-sm disabled:opacity-40"
                        >
                          BUY erfassen und Position eröffnen
                        </button>
                      </fieldset>
                    </form>
                  ) : (
                    <div className="mt-5 rounded-lg border border-sky-800 bg-sky-950/30 p-4">
                      <p className="text-xs uppercase tracking-wide text-sky-400">
                        Offene Position
                      </p>
                      <h3 className="mt-1 text-lg font-semibold">
                        {tradeReference(purchase.trade.id)}
                      </h3>
                      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
                        <div>
                          <dt className="text-slate-500">BUY-Menge</dt>
                          <dd>{purchase.execution.quantity}</dd>
                        </div>
                        <div>
                          <dt className="text-slate-500">Kaufpreis</dt>
                          <dd>{purchase.execution.price_per_unit}</dd>
                        </div>
                        <div>
                          <dt className="text-slate-500">Ausführungswährung</dt>
                          <dd>
                            {executionCurrencyText(
                              purchase.execution.currency_resolution,
                              purchase.execution.currency_confirmation,
                            )}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-slate-500">Cost Basis</dt>
                          <dd>{purchase.position.cost_basis}</dd>
                        </div>
                        <div>
                          <dt className="text-slate-500">Offen</dt>
                          <dd>{purchase.position.open_quantity}</dd>
                        </div>
                      </dl>
                      <p className="mt-4 text-sm text-slate-300">
                        Die Position ist jetzt die wirtschaftliche Wahrheit. Im Trade Management
                        werden Position, Stop/Target, Verkäufe und Alerts gemeinsam sichtbar. Die
                        serverseitige Überwachung läuft gemäß der konfigurierten
                        Position-Monitoring-Einstellung.
                      </p>
                      <Link
                        to={{
                          pathname: '/trade-management',
                          search: new URLSearchParams({ trade_id: purchase.trade.id }).toString(),
                        }}
                        className="mt-4 inline-block rounded-lg border border-violet-700 px-4 py-2 text-sm"
                      >
                        Position verwalten und Monitoring öffnen
                      </Link>
                      <details className="mt-4 text-xs text-slate-500">
                        <summary className="cursor-pointer">Technische Trade-ID anzeigen</summary>
                        <p className="mt-2 break-all">{purchase.trade.id}</p>
                      </details>
                    </div>
                  )}
                </section>
              )}

              {detail.universe_omissions.length > 0 && (
                <section className="rounded-xl border border-amber-800/70 p-5">
                  <h2 className="font-semibold">Nicht in die Bewertung gelangt</h2>
                  <p className="mt-1 text-xs text-slate-500">
                    Diese Produkte wurden nicht still gefiltert; der Universe-Grund bleibt
                    dokumentiert.
                  </p>
                  <ul className="mt-3 space-y-2 text-sm">
                    {detail.universe_omissions.map((item) => (
                      <li
                        key={`${item.warrant_id}-${item.reason}`}
                        className="rounded border border-slate-800 p-3"
                      >
                        <span className="font-medium">
                          {item.reason === 'NO_LISTING'
                            ? 'Notierung fehlt'
                            : item.reason === 'NO_EFFECTIVE_TERMS'
                              ? 'Gültige Produktbedingungen fehlen'
                              : item.reason}
                        </span>
                        <p className="mt-1 text-slate-400">{item.explanation}</p>
                        <Link
                          to={selectionRepairUrl(detail.run.id, item.warrant_id)}
                          className="mt-2 inline-block text-sky-300 underline"
                        >
                          {item.reason === 'NO_LISTING'
                            ? 'Notierung ergänzen'
                            : 'Produktstammdaten prüfen'}
                        </Link>
                        <SelectionProductIdentity
                          productId={item.warrant_id}
                          product={references.products[item.warrant_id]}
                          loading={references.loading}
                        />
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              <section>
                <div className="mb-3">
                  <h2 className="font-semibold">Produktvergleich</h2>
                  <p className="mt-1 text-xs text-slate-500">
                    INELIGIBLE bleibt gesperrt. Nicht bewertbare Produkte können mit expliziter
                    Begründung bewusst ausgewählt werden.
                  </p>
                </div>
                <div className="grid gap-4 lg:grid-cols-2">
                  {detail.evaluations.map((evaluation) => (
                    <EvaluationCard
                      key={evaluation.id}
                      evaluation={evaluation}
                      references={references}
                      selected={detail.selection?.product_evaluation_id === evaluation.id}
                      disabled={
                        busy || contextLoading || Boolean(contextError) || detail.selection !== null
                      }
                      onChoose={(evaluation) => {
                        setMessage(null);
                        setPendingSelection(evaluation);
                      }}
                    />
                  ))}
                </div>
                {detail.evaluations.length === 0 && (
                  <div className="space-y-3 rounded-xl border border-amber-800 p-5 text-sm">
                    <p>
                      {detail.universe_omissions.length > 0
                        ? 'Die oben genannten Stammdaten fehlen in diesem Bewertungslauf. Ein fehlender Kurs ist nicht die Ursache dieser Auslassungen.'
                        : 'In diesem Bewertungslauf ist kein Optionsschein enthalten. Produktidentität und Zuordnung zum Plan-Basiswert in den vorhandenen Stammdaten prüfen.'}
                    </p>
                    <p>
                      Nach der Pflege „Produkte neu bewerten“ wählen. Dieser historische Lauf bleibt
                      unverändert. Fehlende Bewertungsdaten können anschließend über die bestehende
                      Begründung und Bestätigung behandelt werden.
                    </p>
                    {detail.universe_omissions.length === 0 && (
                      <Link
                        to={selectionRepairUrl(detail.run.id)}
                        className="inline-block text-sky-300 underline"
                      >
                        Optionsscheinstammdaten prüfen
                      </Link>
                    )}
                  </div>
                )}
              </section>
            </div>
          ) : (
            <p className="rounded-xl border border-slate-800 p-5 text-sm text-slate-400">
              Starte einen Selection Run oder lade einen historischen Run. Ergebnisse, fehlende
              Daten und Ausschlussgründe erscheinen anschließend hier.
            </p>
          )}
        </div>
      </div>

      {pendingSelection && detail && !detail.selection && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4">
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="selection-confirm-title"
            onKeyDown={(event) => {
              if (event.key === 'Escape' && !busy) {
                setPendingSelection(null);
                setRationale('');
              }
              if (event.key !== 'Tab') return;
              const controls = [
                ...event.currentTarget.querySelectorAll<HTMLButtonElement | HTMLTextAreaElement>(
                  'button:not(:disabled), textarea:not(:disabled)',
                ),
              ];
              const first = controls[0];
              const last = controls.at(-1);
              if (event.shiftKey && document.activeElement === first && last) {
                event.preventDefault();
                last.focus();
              } else if (!event.shiftKey && document.activeElement === last && first) {
                event.preventDefault();
                first.focus();
              }
            }}
            className="max-h-[calc(100dvh-2rem)] w-full max-w-lg overflow-y-auto rounded-xl border border-slate-700 bg-slate-950 p-6 shadow-2xl"
          >
            <p className="text-xs uppercase tracking-wide text-slate-500">
              Explizite Benutzerentscheidung
            </p>
            <h2 id="selection-confirm-title" className="mt-1 text-lg font-semibold">
              Produkt wirklich auswählen?
            </h2>
            {message && (
              <p
                role="alert"
                className="mt-3 rounded-lg border border-rose-800 p-3 text-sm text-rose-200"
              >
                {message}
              </p>
            )}
            <p className="mt-3 text-sm text-slate-400">
              Die Auswahl wird historisch für genau diesen Selection Run dokumentiert und kann nicht
              still überschrieben werden.
            </p>
            {pendingSelection.eligibility_status === 'NOT_EVALUABLE' && (
              <div className="mt-3 rounded-lg border border-amber-700 bg-amber-950/30 p-3 text-sm text-amber-200">
                <p className="font-medium">Bewertung unvollständig</p>
                <p className="mt-1">
                  Mindestens eine Prüfung konnte wegen fehlender Daten oder Konfiguration nicht
                  abgeschlossen werden. Die Auswahl ist möglich, muss aber ausdrücklich begründet
                  werden.
                </p>
                {pendingSelection.reasons.length > 0 && (
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-xs">
                    {pendingSelection.reasons.map((reason) => (
                      <li key={reason}>{reason}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
            <div className="mt-3 rounded border border-slate-800 p-3">
              <SelectionProductIdentity
                productId={pendingSelection.warrant_id}
                product={references.products[pendingSelection.warrant_id]}
                loading={references.loading}
              />
              <details className="mt-2 text-xs text-slate-500">
                <summary className="cursor-pointer">Technische Auswahlreferenzen</summary>
                <p className="mt-1 break-all">Evaluation {pendingSelection.id}</p>
                <p className="mt-1 break-all">Listing {pendingSelection.warrant_listing_id}</p>
              </details>
            </div>
            <label className="mt-4 block text-sm">
              <span className="text-slate-400">
                Begründung
                {pendingSelection.eligibility_status === 'NOT_EVALUABLE'
                  ? ' (erforderlich bei nicht bewertbar)'
                  : ' (optional)'}
              </span>
              <textarea
                autoFocus
                disabled={busy}
                rows={3}
                maxLength={2000}
                required={pendingSelection.eligibility_status === 'NOT_EVALUABLE'}
                value={rationale}
                onChange={(event) => setRationale(event.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2"
              />
            </label>
            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                disabled={busy}
                onClick={() => {
                  setPendingSelection(null);
                  setRationale('');
                }}
                className="rounded-lg border border-slate-700 px-3 py-2 text-sm disabled:opacity-40"
              >
                Abbrechen
              </button>
              <button
                type="button"
                disabled={
                  busy ||
                  contextLoading ||
                  Boolean(contextError) ||
                  (pendingSelection.eligibility_status === 'NOT_EVALUABLE' &&
                    rationale.trim() === '')
                }
                onClick={() => void confirmSelection()}
                className="rounded-lg border border-emerald-700 px-3 py-2 text-sm disabled:opacity-40"
              >
                Auswahl dokumentieren
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
