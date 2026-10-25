import { FormEvent, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { Link, UNSAFE_DataRouterContext, useNavigate, useSearchParams } from 'react-router-dom';

import { MarketApiError } from '../../market/services/http';
import { PendingNavigationGuard } from '../../../components/PendingNavigationGuard';
import { TradePlanContentForm } from '../forms/TradePlanContentForm';
import { createEmptyTradePlanContent } from '../forms/content';
import { tradePlanApiClient } from '../services/client';
import { loadTradePlanOrigin, type TradePlanOriginContext } from '../services/originContext';
import { isTradePlanDetailResponse } from '../services/responseContext';
import type { CreateTradePlanRequest, TradePlanContentRequest } from '../types/api';
import { ExistingTradePlanPage } from './ExistingTradePlanPage';

function CreateTradePlanForm() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const dataRouter = useContext(UNSAFE_DataRouterContext);
  const contextKey = searchParams.toString();
  const [origin, setOrigin] = useState<TradePlanOriginContext | null>(null);
  const [content, setContent] = useState<TradePlanContentRequest>(createEmptyTradePlanContent);
  const [loading, setLoading] = useState(true);
  const [contextError, setContextError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const dirty = useRef(false);
  const mutation = useRef(false);
  const active = useRef(true);
  const shouldBlock = useCallback(() => dirty.current || mutation.current, []);

  useEffect(() => {
    active.current = true;
    const controller = new AbortController();
    setLoading(true);
    setContextError(null);
    setOrigin(null);
    void loadTradePlanOrigin(new URLSearchParams(contextKey), controller.signal)
      .then((resolved) => {
        if (!controller.signal.aborted) setOrigin(resolved);
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setContextError(
            error instanceof Error ? error.message : 'Der Ursprung konnte nicht geladen werden.',
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => {
      active.current = false;
      controller.abort();
    };
  }, [contextKey]);

  function changeOrigin() {
    if (mutation.current) return;
    if (
      !dataRouter &&
      dirty.current &&
      !window.confirm(
        'Ungespeicherte Planänderungen verwerfen und einen anderen Ursprung auswählen?',
      )
    )
      return;
    setSearchParams(new URLSearchParams());
  }

  async function createPlan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!origin || loading || mutation.current || uncertain) return;
    mutation.current = true;
    setBusy(true);
    setMessage(null);
    const request: CreateTradePlanRequest =
      origin.type === 'MANUAL'
        ? { ...content, origin_type: 'MANUAL', underlying_id: origin.underlying.id }
        : {
            ...content,
            origin_type: 'CANDIDATE_EVALUATION',
            candidate_id: origin.candidateId,
            candidate_evaluation_id: origin.evaluation.id,
          };
    try {
      const created = await tradePlanApiClient.create(request);
      if (!active.current) return;
      if (
        !isTradePlanDetailResponse(created) ||
        !created.plan.id ||
        !created.latest_version.id ||
        created.latest_version.status !== 'DRAFT' ||
        created.plan.underlying_id !== origin.underlying.id ||
        created.plan.origin_type !== origin.type ||
        created.latest_version.trade_plan_id !== created.plan.id ||
        (origin.type === 'CANDIDATE_EVALUATION' &&
          (created.plan.candidate_id !== origin.candidateId ||
            created.plan.candidate_evaluation_id !== origin.evaluation.id)) ||
        (origin.type === 'MANUAL' &&
          (created.plan.candidate_id !== null || created.plan.candidate_evaluation_id !== null))
      ) {
        setUncertain(true);
        setMessage(
          'Die Speicherung wurde beantwortet, aber die zurückgegebenen Referenzen passen nicht zum gewählten Ursprung. Bitte den Plan in der Übersicht prüfen; die Anlage wird nicht wiederholt.',
        );
        return;
      }
      dirty.current = false;
      mutation.current = false;
      void navigate(
        {
          pathname: '/trade-plans',
          search: new URLSearchParams({
            trade_plan_id: created.plan.id,
            trade_plan_version_id: created.latest_version.id,
          }).toString(),
        },
        {
          replace: true,
          state: {
            confirmedTradePlan: created,
            confirmationMessage: 'TradePlan wurde als DRAFT erstellt.',
          },
        },
      );
    } catch (error: unknown) {
      if (!active.current) return;
      const unknownResult = !(error instanceof MarketApiError && error.status < 500);
      setUncertain(unknownResult);
      setMessage(
        unknownResult
          ? 'Der Abschluss der Speicherung ist unklar. Die Eingaben bleiben erhalten. Bitte zuerst in der TradePlan-Übersicht prüfen; es erfolgt keine automatische Wiederholung.'
          : error instanceof Error
            ? error.message
            : 'TradePlan konnte nicht erstellt werden. Die Eingaben bleiben erhalten.',
      );
    } finally {
      mutation.current = false;
      if (active.current) setBusy(false);
    }
  }

  return (
    <div className="min-w-0 space-y-5">
      <PendingNavigationGuard shouldBlock={shouldBlock} busy={busy} />
      {loading && <p role="status">Planungsursprung wird geladen …</p>}
      {contextError && (
        <section className="space-y-3 rounded-xl border border-rose-800 p-5">
          <p role="alert">{contextError}</p>
          <button type="button" onClick={changeOrigin} className="rounded-lg border px-3 py-2">
            Ursprung neu auswählen
          </button>
          <Link to="/candidates" className="ml-3 underline">
            Zu den Kandidaten
          </Link>
        </section>
      )}
      {!loading && !contextError && origin && (
        <>
          <section
            className="rounded-xl border border-sky-900 bg-sky-950/20 p-5"
            aria-label="Gebundener Planungsursprung"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-xs uppercase tracking-wide text-slate-400">
                  Basiswert ·{' '}
                  {origin.type === 'MANUAL' ? 'Manueller Ursprung' : 'Kandidatenursprung'}
                </p>
                <h2 className="mt-1 break-words text-xl font-semibold">{origin.underlying.name}</h2>
                <p className="mt-1 text-sm text-slate-400">
                  {[
                    origin.underlying.primary_listing?.ticker,
                    origin.underlying.isin,
                    origin.underlying.wkn,
                  ]
                    .filter(Boolean)
                    .join(' · ')}
                </p>
                {origin.type === 'CANDIDATE_EVALUATION' && (
                  <p className="mt-3 text-sm">
                    CandidateEvaluation · Version {origin.evaluation.version} ·{' '}
                    {origin.evaluation.qualification} ·{' '}
                    {new Date(origin.evaluation.evaluated_at).toLocaleString('de-DE')}
                  </p>
                )}
              </div>
              <button
                type="button"
                disabled={busy}
                onClick={changeOrigin}
                className="rounded-lg border border-slate-600 px-3 py-2 text-sm disabled:opacity-40"
              >
                Ursprung wechseln
              </button>
            </div>
            <details className="mt-4 text-xs text-slate-500">
              <summary className="cursor-pointer">Technische Referenzen anzeigen</summary>
              <div className="mt-2 space-y-1 break-all">
                <p>Underlying-ID: {origin.underlying.id}</p>
                {origin.type === 'CANDIDATE_EVALUATION' && (
                  <>
                    <p>Candidate-ID: {origin.candidateId}</p>
                    <p>CandidateEvaluation-ID: {origin.evaluation.id}</p>
                  </>
                )}
              </div>
            </details>
          </section>
          <form
            onSubmit={(event) => void createPlan(event)}
            className="space-y-5 rounded-xl border border-slate-800 p-5"
          >
            <div>
              <h2 className="text-lg font-semibold">Planinhalt erfassen</h2>
              <p className="mt-1 text-sm text-slate-400">
                LONG-Planung für den gewählten Ursprung. Freigabe erfolgt nach der Anlage
                ausdrücklich für diese Version.
              </p>
            </div>
            <TradePlanContentForm
              value={content}
              disabled={busy}
              onChange={(value) => {
                if (mutation.current) return;
                dirty.current = true;
                setContent(value);
              }}
            />
            {message && (
              <p role="alert" className="rounded-lg border border-amber-700 p-3 text-sm">
                {message}
              </p>
            )}
            <div className="flex flex-wrap gap-3">
              <button
                disabled={busy || uncertain}
                type="submit"
                className="rounded-lg border border-sky-700 px-4 py-2 text-sm disabled:opacity-40"
              >
                {busy ? 'TradePlan wird gespeichert …' : 'TradePlan als DRAFT erstellen'}
              </button>
              {uncertain && (
                <Link
                  to="/trade-plans/overview"
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-lg border px-3 py-2 text-sm"
                >
                  TradePlan-Übersicht prüfen
                </Link>
              )}
            </div>
          </form>
        </>
      )}
    </div>
  );
}

/** Creation delegates every stored plan to the same central view used by the workflow route. */
export function TradePlanPage() {
  const [params] = useSearchParams();
  const planId = params.get('trade_plan_id');
  if (planId) return <ExistingTradePlanPage tradePlanId={planId} />;
  return <CreateTradePlanForm key={params.toString()} />;
}
