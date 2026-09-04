import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { tradeManagementApiClient } from '../../trade/services/client';
import type { InitialPurchaseResponse } from '../../trade/types/api';
import { productSelectionApiClient } from '../services/client';
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
}: {
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
          <p className="text-xs uppercase tracking-wide text-slate-500">Warrant</p>
          <h3 className="mt-1 break-all font-semibold">{evaluation.warrant_id}</h3>
          <p className="mt-1 break-all text-xs text-slate-500">
            Listing {evaluation.warrant_listing_id}
          </p>
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
          disabled={disabled || evaluation.eligibility_status !== 'ELIGIBLE'}
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
  const [searchParams] = useSearchParams();
  const initialTradePlanId = searchParams.get('trade_plan_id') ?? '';
  const initialVersionId = searchParams.get('trade_plan_version_id') ?? '';
  const [tradePlanId, setTradePlanId] = useState(initialTradePlanId);
  const [tradePlanVersionId, setTradePlanVersionId] = useState(initialVersionId);
  const [runs, setRuns] = useState<ProductSelectionRunSummaryResponse[]>([]);
  const [detail, setDetail] = useState<ProductSelectionRunDetailResponse | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [pendingSelection, setPendingSelection] = useState<ProductEvaluationResponse | null>(null);
  const [rationale, setRationale] = useState('');
  const [purchaseQuantity, setPurchaseQuantity] = useState('');
  const [purchasePrice, setPurchasePrice] = useState('');
  const [purchase, setPurchase] = useState<InitialPurchaseResponse | null>(null);

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
    if (!initialVersionId) return;
    const controller = new AbortController();
    productSelectionApiClient
      .listForTradePlanVersion(initialVersionId, controller.signal)
      .then(setRuns)
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === 'AbortError')) {
          setMessage(
            error instanceof Error ? error.message : 'Selection Runs konnten nicht geladen werden.',
          );
        }
      });
    return () => controller.abort();
  }, [initialVersionId]);

  async function refreshRuns(versionId: string) {
    const items = await productSelectionApiClient.listForTradePlanVersion(versionId);
    setRuns(items);
    return items;
  }

  async function startRun(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!tradePlanId.trim() || !tradePlanVersionId.trim()) return;
    setBusy(true);
    setMessage(null);
    setPendingSelection(null);
    setPurchase(null);
    try {
      const created = await productSelectionApiClient.start({
        trade_plan_id: tradePlanId.trim(),
        trade_plan_version_id: tradePlanVersionId.trim(),
      });
      setDetail(created);
      await refreshRuns(tradePlanVersionId.trim());
      setMessage('Produktsuche wurde als neuer historischer Selection Run durchgeführt.');
    } catch (error: unknown) {
      setMessage(
        error instanceof Error ? error.message : 'Produktsuche konnte nicht gestartet werden.',
      );
    } finally {
      setBusy(false);
    }
  }

  async function loadRun(runId: string) {
    setBusy(true);
    setMessage(null);
    setPendingSelection(null);
    setPurchase(null);
    try {
      setDetail(await productSelectionApiClient.get(runId));
    } catch (error: unknown) {
      setMessage(
        error instanceof Error ? error.message : 'Selection Run konnte nicht geladen werden.',
      );
    } finally {
      setBusy(false);
    }
  }

  async function confirmSelection() {
    if (!detail || !pendingSelection || busy) return;
    setBusy(true);
    setMessage(null);
    try {
      const updated = await productSelectionApiClient.select(detail.run.id, {
        product_evaluation_id: pendingSelection.id,
        rationale: rationale.trim() || null,
      });
      setDetail(updated);
      setPendingSelection(null);
      setRationale('');
      setPurchase(null);
      setMessage(
        'Produktauswahl wurde dokumentiert. Nächster Schritt: tatsächlichen Kauf als BUY erfassen.',
      );
    } catch (error: unknown) {
      setMessage(
        error instanceof Error ? error.message : 'Produktauswahl konnte nicht gespeichert werden.',
      );
    } finally {
      setBusy(false);
    }
  }

  async function recordPurchase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!detail?.selection || busy) return;
    const quantity = Number(purchaseQuantity);
    if (!Number.isInteger(quantity) || quantity <= 0 || purchasePrice.trim() === '') return;

    setBusy(true);
    setMessage(null);
    try {
      const created = await tradeManagementApiClient.purchaseFromSelection({
        product_selection_id: detail.selection.id,
        quantity,
        price_per_unit: purchasePrice,
      });
      setPurchase(created);
      setMessage(
        `Kauf wurde als BUY erfasst. Trade ${tradeReference(created.trade.id)} und offene Position wurden erstellt.`,
      );
    } catch (error: unknown) {
      setMessage(error instanceof Error ? error.message : 'Kauf konnte nicht erfasst werden.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="w-full space-y-8">
      <div>
        <p className="text-xs uppercase tracking-wide text-slate-500">FT-008</p>
        <h1 className="mt-1 text-2xl font-semibold">Produktauswahl</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-400">
          Transparente Entscheidungshilfe für eine freigegebene TradePlanVersion. Das System
          bewertet und erklärt; die endgültige Produktauswahl bleibt eine separate
          Benutzerentscheidung.
        </p>
      </div>

      {message && <p className="rounded-lg border border-slate-700 p-3 text-sm">{message}</p>}

      <div className="grid gap-8 xl:grid-cols-[21rem_1fr]">
        <aside className="space-y-5">
          <form
            onSubmit={(event) => void startRun(event)}
            className="rounded-xl border border-slate-800 p-5"
          >
            <h2 className="font-semibold">Neuen Selection Run starten</h2>
            <p className="mt-1 text-xs text-slate-500">
              Nur APPROVED TradePlanVersionen sind zulässig.
            </p>
            <label className="mt-4 block text-sm">
              <span className="text-slate-400">TradePlan-ID</span>
              <input
                required
                value={tradePlanId}
                onChange={(event) => setTradePlanId(event.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2"
              />
            </label>
            <label className="mt-3 block text-sm">
              <span className="text-slate-400">TradePlanVersion-ID</span>
              <input
                required
                value={tradePlanVersionId}
                onChange={(event) => setTradePlanVersionId(event.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 p-2"
              />
            </label>
            <button
              disabled={busy}
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
                  onClick={() => void refreshRuns(tradePlanVersionId.trim())}
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
                  onClick={() => void loadRun(run.id)}
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
                    <h2 className="mt-1 text-lg font-semibold">
                      {new Date(detail.run.evaluated_at).toLocaleString('de-DE')}
                    </h2>
                    <p className="mt-1 break-all text-xs text-slate-500">{detail.run.id}</p>
                  </div>
                  <Link
                    to={{
                      pathname: '/trade-plans',
                      search: new URLSearchParams({}).toString(),
                    }}
                    className="rounded-lg border border-slate-700 px-3 py-2 text-xs"
                  >
                    Zu TradePlans
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
                        <dt className="text-slate-500">Warrant</dt>
                        <dd className="break-all">{selectedEvaluation.warrant_id}</dd>
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
                      <h3 className="font-medium">Nächster Schritt: tatsächlichen Kauf erfassen</h3>
                      <p className="mt-1 text-xs text-slate-400">
                        Erst dieser BUY erzeugt den Trade und die offene Position. Die Produktauswahl
                        allein ist noch keine Ausführung.
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
                          <span className="text-slate-400">Tatsächlicher Kaufpreis je Einheit</span>
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
                      <button
                        type="submit"
                        disabled={
                          busy || purchaseQuantity.trim() === '' || purchasePrice.trim() === ''
                        }
                        className="mt-4 rounded-lg border border-sky-700 px-4 py-2 text-sm disabled:opacity-40"
                      >
                        BUY erfassen und Position eröffnen
                      </button>
                    </form>
                  ) : (
                    <div className="mt-5 rounded-lg border border-sky-800 bg-sky-950/30 p-4">
                      <p className="text-xs uppercase tracking-wide text-sky-400">Offene Position</p>
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
                        <span className="font-medium">{item.reason}</span>
                        <p className="mt-1 text-slate-400">{item.explanation}</p>
                        <p className="mt-1 break-all text-xs text-slate-500">{item.warrant_id}</p>
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              <section>
                <div className="mb-3">
                  <h2 className="font-semibold">Produktvergleich</h2>
                  <p className="mt-1 text-xs text-slate-500">
                    Keine automatische Best-Product-Entscheidung. Auswahl ist nur bei ELIGIBLE
                    möglich.
                  </p>
                </div>
                <div className="grid gap-4 lg:grid-cols-2">
                  {detail.evaluations.map((evaluation) => (
                    <EvaluationCard
                      key={evaluation.id}
                      evaluation={evaluation}
                      selected={detail.selection?.product_evaluation_id === evaluation.id}
                      disabled={busy || detail.selection !== null}
                      onChoose={setPendingSelection}
                    />
                  ))}
                </div>
                {detail.evaluations.length === 0 && (
                  <p className="rounded-xl border border-slate-800 p-5 text-sm text-slate-400">
                    Dieser Run enthält keine bewertbaren Listing-Kontexte.
                  </p>
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
            className="w-full max-w-lg rounded-xl border border-slate-700 bg-slate-950 p-6 shadow-2xl"
          >
            <p className="text-xs uppercase tracking-wide text-slate-500">
              Explizite Benutzerentscheidung
            </p>
            <h2 id="selection-confirm-title" className="mt-1 text-lg font-semibold">
              Produkt wirklich auswählen?
            </h2>
            <p className="mt-3 text-sm text-slate-400">
              Die Auswahl wird historisch für genau diesen Selection Run dokumentiert und kann nicht
              still überschrieben werden.
            </p>
            <p className="mt-3 break-all rounded border border-slate-800 p-3 text-xs">
              Evaluation {pendingSelection.id}
            </p>
            <label className="mt-4 block text-sm">
              <span className="text-slate-400">Begründung (optional)</span>
              <textarea
                rows={3}
                maxLength={2000}
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
                disabled={busy}
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
