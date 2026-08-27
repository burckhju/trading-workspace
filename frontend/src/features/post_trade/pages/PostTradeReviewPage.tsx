import { FormEvent, useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { ft011MaterializationClient } from '../../learning/services/materializationClient';
import type { Ft011MaterializationStatus } from '../../learning/types/materialization';
import { ErrorNotice, LoadingNotice } from '../../market/components/ApiFeedback';
import { postTradeApiClient } from '../services/client';
import { postTradeErrorMessage } from '../services/errors';
import type {
  ExitReviewAssessment,
  ExitReviewResponse,
  HandoffResponse,
  ObservationEvidenceResponse,
  ObservationResponse,
} from '../types/api';

function formatNumber(value: string | null): string {
  if (value === null) return '—';
  return new Intl.NumberFormat('de-DE', {
    maximumFractionDigits: 10,
  }).format(Number(value));
}

function formatDate(value: string | null): string {
  return value ? new Date(`${value}T00:00:00`).toLocaleDateString('de-DE') : '—';
}

function formatDateTime(value: string | null): string {
  return value ? new Date(value).toLocaleString('de-DE') : '—';
}

export function PostTradeReviewPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [lookupId, setLookupId] = useState(searchParams.get('trade_id') ?? '');
  const [tradeId, setTradeId] = useState(searchParams.get('trade_id') ?? '');

  const [observation, setObservation] = useState<ObservationResponse | null>(null);
  const [evidence, setEvidence] = useState<ObservationEvidenceResponse | null>(null);
  const [handoff, setHandoff] = useState<HandoffResponse | null>(null);
  const [materializationStatus, setMaterializationStatus] =
    useState<Ft011MaterializationStatus | null>(null);

  const [review, setReview] = useState<ExitReviewResponse | null>(null);
  const [history, setHistory] = useState<ExitReviewResponse[]>([]);

  const [timing, setTiming] = useState<ExitReviewAssessment>('GOOD');
  const [processAdherence, setProcessAdherence] = useState<ExitReviewAssessment>('GOOD');
  const [riskDecision, setRiskDecision] = useState<ExitReviewAssessment>('GOOD');
  const [overallExitDecision, setOverallExitDecision] = useState<ExitReviewAssessment>('GOOD');
  const [rationale, setRationale] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState<string | null>(null);

  function hydrateReviewForm(nextReview: ExitReviewResponse | null) {
    if (!nextReview) return;

    setTiming(nextReview.timing ?? 'GOOD');
    setProcessAdherence(nextReview.process_adherence ?? 'GOOD');
    setRiskDecision(nextReview.risk_decision ?? 'GOOD');
    setOverallExitDecision(nextReview.overall_exit_decision ?? 'GOOD');
    setRationale(nextReview.rationale ?? '');
  }

  const refresh = useCallback(async (id: string, signal?: AbortSignal) => {
    const nextObservation = await postTradeApiClient.observation(id, signal);

    setObservation(nextObservation);

    const [nextEvidence, nextHandoff, nextHistory, nextMaterializationStatus] = await Promise.all([
      postTradeApiClient.evidence(id, signal),
      postTradeApiClient.handoff(id, signal),
      postTradeApiClient.reviewHistory(id, signal),
      ft011MaterializationClient.status(id, signal),
    ]);

    setEvidence(nextEvidence);
    setHandoff(nextHandoff);
    setHistory(nextHistory);
    setMaterializationStatus(nextMaterializationStatus);

    try {
      const nextReview = await postTradeApiClient.review(id, signal);
      setReview(nextReview);
      hydrateReviewForm(nextReview);
    } catch {
      setReview(null);
    }
  }, []);

  useEffect(() => {
    if (!tradeId) return undefined;

    const controller = new AbortController();
    setLoading(true);
    setError(null);

    refresh(tradeId, controller.signal)
      .catch((nextError: unknown) => {
        if (!controller.signal.aborted) setError(new Error(postTradeErrorMessage(nextError)));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [refresh, tradeId]);

  function lookupTrade(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const id = lookupId.trim();
    if (!id) return;

    setSearchParams({ trade_id: id });
    setTradeId(id);
  }

  async function startObservation() {
    if (!tradeId) return;

    setLoading(true);
    setError(null);
    setMessage(null);

    try {
      await postTradeApiClient.startObservation(tradeId);
      await refresh(tradeId);
      setMessage('Nachbeobachtung wurde gestartet.');
    } catch (nextError: unknown) {
      setError(new Error(postTradeErrorMessage(nextError)));
    } finally {
      setLoading(false);
    }
  }

  async function createDraft() {
    if (!tradeId) return;

    setLoading(true);
    setError(null);
    setMessage(null);

    try {
      const nextReview = await postTradeApiClient.createReviewDraft(tradeId);
      setReview(nextReview);
      hydrateReviewForm(nextReview);
      await refresh(tradeId);
      setMessage('Exit-Review-Entwurf wurde angelegt.');
    } catch (nextError: unknown) {
      setError(new Error(postTradeErrorMessage(nextError)));
    } finally {
      setLoading(false);
    }
  }

  async function saveDraft() {
    if (!tradeId || !review) return;

    setLoading(true);
    setError(null);
    setMessage(null);

    try {
      const nextReview = await postTradeApiClient.updateReviewDraft(tradeId, {
        timing,
        process_adherence: processAdherence,
        risk_decision: riskDecision,
        overall_exit_decision: overallExitDecision,
        rationale,
      });
      setReview(nextReview);
      hydrateReviewForm(nextReview);
      setMessage('Exit-Review-Entwurf wurde gespeichert.');
    } catch (nextError: unknown) {
      setError(new Error(postTradeErrorMessage(nextError)));
    } finally {
      setLoading(false);
    }
  }

  async function finalizeReview() {
    if (!tradeId || !review || rationale.trim() === '') return;

    setLoading(true);
    setError(null);
    setMessage(null);

    try {
      await postTradeApiClient.updateReviewDraft(tradeId, {
        timing,
        process_adherence: processAdherence,
        risk_decision: riskDecision,
        overall_exit_decision: overallExitDecision,
        rationale,
      });

      const nextReview = await postTradeApiClient.finalizeReview(tradeId);
      setReview(nextReview);
      hydrateReviewForm(nextReview);
      await refresh(tradeId);
      setMessage('Exit Review wurde finalisiert.');
    } catch (nextError: unknown) {
      setError(new Error(postTradeErrorMessage(nextError)));
    } finally {
      setLoading(false);
    }
  }

  async function revalidateReview() {
    if (!tradeId) return;

    setLoading(true);
    setError(null);
    setMessage(null);

    try {
      const nextReview = await postTradeApiClient.revalidateReview(tradeId);
      setReview(nextReview);
      hydrateReviewForm(nextReview);
      await refresh(tradeId);
      setMessage('Review wurde erneut geprüft.');
    } catch (nextError: unknown) {
      setError(new Error(postTradeErrorMessage(nextError)));
    } finally {
      setLoading(false);
    }
  }

  async function materializeLearningEvidence() {
    if (!tradeId || !handoff?.ready || materializationStatus?.materialized) return;

    setLoading(true);
    setError(null);
    setMessage(null);

    try {
      await ft011MaterializationClient.materialize(tradeId, `post-trade-${tradeId}-${Date.now()}`);
      await refresh(tradeId);
      setMessage('FT-011 LearningEvidence wurde in FT-012 materialisiert.');
    } catch (nextError: unknown) {
      setError(new Error(postTradeErrorMessage(nextError)));
    } finally {
      setLoading(false);
    }
  }

  const counterfactual = evidence?.counterfactual;
  const reviewReadOnly = review?.status === 'FINALIZED';

  return (
    <main className="space-y-6">
      <header>
        <p className="text-xs uppercase tracking-wide text-slate-500">FT-011</p>
        <h1 className="mt-1 text-2xl font-semibold">Post-Trade Review</h1>
        <p className="mt-2 text-sm text-slate-400">
          Tatsächlicher Exit und nachgelagerte Underlying-Beobachtung bleiben getrennte Fakten.
        </p>
      </header>

      <form onSubmit={lookupTrade} className="rounded-xl border border-slate-800 p-5">
        <label htmlFor="post-trade-id" className="block text-sm font-medium">
          Trade-ID
        </label>

        <div className="mt-2 flex flex-col gap-2 sm:flex-row">
          <input
            id="post-trade-id"
            value={lookupId}
            onChange={(event) => setLookupId(event.target.value)}
            placeholder="UUID des geschlossenen Trades"
            className="min-w-0 flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
          />

          <button
            type="submit"
            disabled={loading || lookupId.trim() === ''}
            className="rounded-lg border border-slate-600 px-4 py-2 disabled:opacity-50"
          >
            Laden
          </button>
        </div>
      </form>

      {loading && <LoadingNotice label="Post-Trade-Daten werden geladen …" />}
      {error !== null && <ErrorNotice error={error} />}

      {message && (
        <div role="status" className="rounded-xl border border-slate-700 bg-slate-900 p-4 text-sm">
          {message}
        </div>
      )}

      {tradeId && observation === null && !loading && error !== null && (
        <section className="rounded-xl border border-slate-800 p-5">
          <h2 className="text-lg font-semibold">Nachbeobachtung</h2>
          <p className="mt-2 text-sm text-slate-400">
            Für einen vollständig geschlossenen Trade kann die Nachbeobachtung explizit gestartet
            werden.
          </p>
          <button
            type="button"
            onClick={() => void startObservation()}
            className="mt-4 rounded-lg border border-slate-600 px-4 py-2"
          >
            Nachbeobachtung starten
          </button>
        </section>
      )}

      {observation && (
        <section className="rounded-xl border border-slate-800 p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Observation</p>
              <h2 className="mt-1 text-lg font-semibold">{observation.status}</h2>
            </div>

            <span className="rounded-full border border-slate-700 px-3 py-1 text-sm">
              {observation.available_observation_count}/{observation.target_observation_count}
            </span>
          </div>

          <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <dt className="text-slate-500">Vorhanden</dt>
              <dd className="mt-1 font-medium">{observation.available_observation_count}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Fehlend</dt>
              <dd className="mt-1 font-medium">{observation.missing_observation_count}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Gestartet</dt>
              <dd className="mt-1 font-medium">{formatDateTime(observation.started_at)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Abgeschlossen</dt>
              <dd className="mt-1 font-medium">{formatDateTime(observation.completed_at)}</dd>
            </div>
          </dl>
        </section>
      )}

      {evidence && (
        <>
          <section className="rounded-xl border border-slate-800 p-5">
            <h2 className="text-lg font-semibold">Kontext</h2>

            <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-3">
              <div>
                <dt className="text-slate-500">Warrant</dt>
                <dd className="mt-1 font-medium">{evidence.product_context?.warrant_id ?? '—'}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Underlying</dt>
                <dd className="mt-1 font-medium">
                  {evidence.product_context?.underlying_id ?? '—'}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">Warrant-Maturity</dt>
                <dd className="mt-1 font-medium">
                  {formatDate(evidence.product_context?.maturity_date ?? null)}
                </dd>
              </div>
            </dl>

            {evidence.product_context?.maturity_date && (
              <p className="mt-4 rounded-lg border border-amber-800 bg-amber-950/40 p-3 text-sm text-amber-200">
                Die Warrant-Maturity begrenzt nicht die 20 Underlying-EOD-Beobachtungen. Es wird
                keine virtuelle Warrant-P&amp;L nach Maturity berechnet.
              </p>
            )}
          </section>

          <div className="grid gap-6 xl:grid-cols-2">
            <section className="rounded-xl border border-slate-800 p-5">
              <p className="text-xs uppercase tracking-wide text-slate-500">Actual</p>
              <h2 className="mt-1 text-lg font-semibold">Tatsächlicher Exit</h2>

              <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-slate-500">Full Exit</dt>
                  <dd className="mt-1 font-medium">
                    {formatDateTime(evidence.actual_exit.full_exit_at)}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Realized gross P&amp;L</dt>
                  <dd className="mt-1 font-medium">
                    {formatNumber(evidence.actual_exit.realized_gross_pnl)}
                  </dd>
                </div>
              </dl>

              <h3 className="mt-5 font-medium">Exit-Executions</h3>
              <ul className="mt-2 space-y-2 text-sm">
                {evidence.actual_exit.executions.map((execution) => (
                  <li
                    key={execution.execution_id}
                    className="rounded-lg border border-slate-800 p-3"
                  >
                    {formatNumber(execution.quantity)} × {formatNumber(execution.price_per_unit)} ·{' '}
                    {formatDateTime(execution.executed_at)}
                  </li>
                ))}
              </ul>
            </section>

            <section className="rounded-xl border border-slate-800 p-5">
              <p className="text-xs uppercase tracking-wide text-slate-500">Counterfactual</p>
              <h2 className="mt-1 text-lg font-semibold">Underlying-Nachbeobachtung</h2>

              <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-3">
                <div>
                  <dt className="text-slate-500">Highest High</dt>
                  <dd className="mt-1 font-medium">
                    {formatNumber(counterfactual?.highest_high?.value ?? null)}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Lowest Low</dt>
                  <dd className="mt-1 font-medium">
                    {formatNumber(counterfactual?.lowest_low?.value ?? null)}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Final Close</dt>
                  <dd className="mt-1 font-medium">
                    {formatNumber(counterfactual?.final_close?.value ?? null)}
                  </dd>
                </div>
              </dl>

              <div className="mt-5">
                <h3 className="font-medium">Ursprünglicher Plan</h3>
                <p className="mt-2 text-sm text-slate-400">
                  Stop: {formatNumber(evidence.planning_context.original_stop)}
                </p>
                <p className="mt-1 text-sm text-slate-400">
                  Targets:{' '}
                  {evidence.planning_context.original_targets.length > 0
                    ? evidence.planning_context.original_targets.map(formatNumber).join(', ')
                    : '—'}
                </p>
              </div>

              <div className="mt-5">
                <h3 className="font-medium">Spätere Management-Level</h3>
                {evidence.management_levels.length === 0 ? (
                  <p className="mt-2 text-sm text-slate-400">Keine späteren Level dokumentiert.</p>
                ) : (
                  <ul className="mt-2 space-y-2 text-sm">
                    {evidence.management_levels.map((level) => (
                      <li key={level.event_id} className="rounded-lg border border-slate-800 p-3">
                        {level.kind}: {formatNumber(level.numeric_value)} ·{' '}
                        {formatDateTime(level.effective_at)}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </section>
          </div>
        </>
      )}

      {observation?.is_complete && (
        <section className="rounded-xl border border-slate-800 p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Exit Review</p>
              <h2 className="mt-1 text-lg font-semibold">
                {review ? `Version ${review.version}` : 'Noch kein Review'}
              </h2>
            </div>

            {review && (
              <div className="flex gap-2">
                <span className="rounded-full border border-slate-700 px-3 py-1 text-xs">
                  {review.status}
                </span>
                <span className="rounded-full border border-slate-700 px-3 py-1 text-xs">
                  {review.currentness}
                </span>
              </div>
            )}
          </div>

          {!review ? (
            <button
              type="button"
              onClick={() => void createDraft()}
              disabled={loading}
              className="mt-4 rounded-lg border border-slate-600 px-4 py-2 disabled:opacity-50"
            >
              Exit Review anlegen
            </button>
          ) : (
            <>
              {review.currentness === 'STALE' && (
                <div className="mt-4 rounded-lg border border-amber-800 bg-amber-950/40 p-4 text-sm text-amber-200">
                  <p>Dieser Review ist STALE und muss erneut geprüft werden.</p>
                  <button
                    type="button"
                    onClick={() => void revalidateReview()}
                    disabled={loading}
                    className="mt-3 rounded-lg border border-amber-700 px-3 py-2 disabled:opacity-50"
                  >
                    Review erneut prüfen
                  </button>
                </div>
              )}

              <div className="mt-5 grid gap-4 sm:grid-cols-2">
                {[
                  ['Timing', timing, setTiming],
                  ['Process adherence', processAdherence, setProcessAdherence],
                  ['Risk decision', riskDecision, setRiskDecision],
                  ['Overall exit decision', overallExitDecision, setOverallExitDecision],
                ].map(([label, value, setter]) => (
                  <label key={label as string} className="text-sm">
                    <span className="text-slate-400">{label as string}</span>
                    <select
                      value={value as ExitReviewAssessment}
                      disabled={reviewReadOnly || loading}
                      onChange={(event) =>
                        (setter as (value: ExitReviewAssessment) => void)(
                          event.target.value as ExitReviewAssessment,
                        )
                      }
                      className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
                    >
                      <option value="GOOD">GOOD</option>
                      <option value="ACCEPTABLE">ACCEPTABLE</option>
                      <option value="IMPROVABLE">IMPROVABLE</option>
                      <option value="NOT_ASSESSABLE">NOT_ASSESSABLE</option>
                    </select>
                  </label>
                ))}
              </div>

              <label className="mt-4 block text-sm">
                <span className="text-slate-400">Begründung</span>
                <textarea
                  aria-label="Review-Begründung"
                  value={rationale}
                  disabled={reviewReadOnly || loading}
                  onChange={(event) => setRationale(event.target.value)}
                  className="mt-1 min-h-32 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
                />
              </label>

              {reviewReadOnly ? (
                <p className="mt-4 text-sm text-slate-400">
                  Finalisierte Reviews sind schreibgeschützt.
                </p>
              ) : (
                <div className="mt-4 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => void saveDraft()}
                    disabled={loading}
                    className="rounded-lg border border-slate-600 px-4 py-2 disabled:opacity-50"
                  >
                    Entwurf speichern
                  </button>

                  <button
                    type="button"
                    onClick={() => void finalizeReview()}
                    disabled={loading || rationale.trim() === ''}
                    className="rounded-lg border border-emerald-700 px-4 py-2 disabled:opacity-50"
                  >
                    Review finalisieren
                  </button>
                </div>
              )}
            </>
          )}
        </section>
      )}

      {history.length > 0 && (
        <section className="rounded-xl border border-slate-800 p-5">
          <h2 className="text-lg font-semibold">Review-Historie</h2>

          <ol className="mt-4 space-y-3">
            {history.map((item) => (
              <li
                key={item.current_version_id}
                className="rounded-lg border border-slate-800 p-4 text-sm"
              >
                <div className="flex flex-wrap justify-between gap-2">
                  <span>Version {item.version}</span>
                  <span>
                    {item.status} · {item.currentness}
                  </span>
                </div>
                <p className="mt-2 text-slate-400">{item.rationale || 'Keine Begründung.'}</p>
              </li>
            ))}
          </ol>
        </section>
      )}

      {handoff && (
        <section className="rounded-xl border border-slate-800 p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold">FT-012 Handoff</h2>
              <p className="mt-2 text-sm">
                {handoff.ready ? 'Bereit für FT-012.' : `Noch nicht bereit: ${handoff.reason}`}
              </p>
            </div>

            {materializationStatus?.materialized && (
              <span className="rounded-full border border-emerald-700 px-3 py-1 text-xs text-emerald-300">
                MATERIALIZED
              </span>
            )}
          </div>

          {materializationStatus?.materialized ? (
            <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-slate-500">LearningEvidence</dt>
                <dd className="mt-1 break-all font-medium">
                  {materializationStatus.learning_evidence_id}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">ExitReviewVersion</dt>
                <dd className="mt-1 break-all font-medium">
                  {materializationStatus.exit_review_version_id}
                </dd>
              </div>
            </dl>
          ) : (
            <button
              type="button"
              onClick={() => void materializeLearningEvidence()}
              disabled={loading || !handoff.ready || materializationStatus?.ready !== true}
              className="mt-4 rounded-lg border border-emerald-700 px-4 py-2 disabled:opacity-50"
            >
              Als LearningEvidence materialisieren
            </button>
          )}
        </section>
      )}
    </main>
  );
}
