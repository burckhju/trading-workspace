import { Ft011EvidenceHistory } from '../../learning/components/Ft011EvidenceHistory';
import { TradeJournalPanel } from '../../learning/components/TradeJournalPanel';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { LessonDraftFromEvidence } from '../../learning/components/LessonDraftFromEvidence';
import { lessonReadbackClient } from '../../learning/services/lessonReadbackClient';
import { ft011MaterializationClient } from '../../learning/services/materializationClient';
import type { LessonEvidenceReference } from '../../learning/types/lessonReadback';
import type { Ft011MaterializationStatus } from '../../learning/types/materialization';
import { warrantApiClient } from '../../product/services/client';
import type { WarrantResponse } from '../../product/types/api';
import { tradeManagementApiClient } from '../../trade/services/client';
import type { TradeResponse } from '../../trade/types/api';
import { postTradeErrorMessage } from '../services/errors';
import { PostTradeReviewPage } from './PostTradeReviewPage';

function tradeReference(id: string): string {
  return `TR-${id.slice(0, 8).toUpperCase()}`;
}

function tradePlanReference(id: string): string {
  return `TP-${id.slice(0, 8).toUpperCase()}`;
}

function materializationKey(tradeId: string, exitReviewVersionId: string): string {
  return `ft011-to-ft012:v2:${tradeId}:${exitReviewVersionId}`;
}

export function PostTradeLearningPage() {
  const [searchParams] = useSearchParams();
  const tradeId = searchParams.get('trade_id') ?? '';
  return <PostTradeLearningContent key={tradeId} tradeId={tradeId} />;
}

function PostTradeLearningContent({ tradeId }: { tradeId: string }) {
  const [trade, setTrade] = useState<TradeResponse | null>(null);
  const [warrant, setWarrant] = useState<WarrantResponse | null>(null);
  const [status, setStatus] = useState<Ft011MaterializationStatus | null>(null);
  const [lessonReferences, setLessonReferences] = useState<LessonEvidenceReference[] | null>(null);
  const [lessonSourceId, setLessonSourceId] = useState<string | null>(null);
  const [lessonReadbackError, setLessonReadbackError] = useState<string | null>(null);
  const [refreshVersion, setRefreshVersion] = useState(0);
  const [lessonRefreshVersion, setLessonRefreshVersion] = useState(0);
  const mounted = useRef(false);
  const mutationPending = useRef(false);
  const [materializing, setMaterializing] = useState(false);
  const [materializationError, setMaterializationError] = useState<string | null>(null);

  const refreshLearningState = useCallback(() => {
    setRefreshVersion((value) => value + 1);
  }, []);

  const refreshLessonReferences = useCallback(() => {
    setLessonReferences(null);
    setLessonRefreshVersion((value) => value + 1);
  }, []);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const learningEvidenceId = status?.materialized ? status.learning_evidence_id : null;

  useEffect(() => {
    if (!tradeId) {
      setTrade(null);
      setWarrant(null);
      return undefined;
    }

    const controller = new AbortController();
    tradeManagementApiClient
      .trade(tradeId, controller.signal)
      .then(async (nextTrade) => {
        if (controller.signal.aborted) return;
        setTrade(nextTrade);
        try {
          const nextWarrant = await warrantApiClient.get(nextTrade.product_id, controller.signal);
          if (!controller.signal.aborted) setWarrant(nextWarrant);
        } catch {
          if (!controller.signal.aborted) setWarrant(null);
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setTrade(null);
          setWarrant(null);
        }
      });

    return () => controller.abort();
  }, [tradeId]);

  useEffect(() => {
    setStatus(null);
    if (!tradeId) return undefined;

    const controller = new AbortController();
    ft011MaterializationClient
      .status(tradeId, controller.signal)
      .then((nextStatus) => {
        if (!controller.signal.aborted) setStatus(nextStatus);
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setMaterializationError('Der Learning-Übergabestatus konnte nicht geladen werden.');
        }
      });

    return () => controller.abort();
  }, [tradeId, refreshVersion]);

  useEffect(() => {
    setLessonReferences(null);
    setLessonReadbackError(null);
    setLessonSourceId(learningEvidenceId);
    if (!learningEvidenceId) return undefined;

    const controller = new AbortController();
    lessonReadbackClient
      .listForEvidence(learningEvidenceId, controller.signal)
      .then((references) => {
        if (!controller.signal.aborted) setLessonReferences(references);
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setLessonReadbackError('Lesson-Verweise konnten nicht geladen werden.');
        }
      });

    return () => controller.abort();
  }, [learningEvidenceId, lessonRefreshVersion]);

  const handleMaterialize = useCallback(async () => {
    if (
      !tradeId ||
      !status?.ready ||
      status.materialized ||
      !status.exit_review_version_id ||
      mutationPending.current
    ) {
      return;
    }

    mutationPending.current = true;
    setMaterializing(true);
    setMaterializationError(null);
    try {
      await ft011MaterializationClient.materialize(
        tradeId,
        materializationKey(tradeId, status.exit_review_version_id),
        status.exit_review_version_id,
      );
    } catch (error) {
      if (mounted.current) {
        setMaterializationError(postTradeErrorMessage(error));
      }
    } finally {
      mutationPending.current = false;
      if (mounted.current) {
        // A response/replay is not a fresh READY or CURRENT assessment.
        setStatus(null);
        setMaterializing(false);
        refreshLearningState();
      }
    }
  }, [refreshLearningState, status, tradeId]);

  return (
    <div className="min-w-0 w-full space-y-6">
      {trade && (
        <section className="mb-6 rounded-xl border border-sky-900 bg-sky-950/20 p-5">
          <p className="text-xs uppercase tracking-wide text-sky-400">Post-Trade-Kontext</p>
          <div className="mt-1 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h1 className="text-xl font-semibold">
                {tradeReference(trade.id)}
                {warrant ? ` · ${warrant.display_name}` : ''}
              </h1>
              {warrant && (
                <p className="mt-1 text-sm text-slate-400">
                  {warrant.isin ? `ISIN ${warrant.isin}` : 'Keine ISIN'}
                  {warrant.wkn ? ` · WKN ${warrant.wkn}` : ''}
                </p>
              )}
            </div>
            <span className="rounded-full border border-sky-800 px-3 py-1 text-xs">
              Nachbeobachtung &amp; Review
            </span>
          </div>
          <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-3">
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
              <dt className="text-slate-500">Learning-Übergang</dt>
              <dd className="mt-1 font-medium">
                {status === null
                  ? 'Übergabestatus wird geprüft'
                  : status.materialized
                    ? 'LearningEvidence materialisiert'
                    : status.ready
                      ? 'Aktueller Reviewstand noch nicht übergeben'
                      : 'Neue Übergabe derzeit nicht bereit'}
              </dd>
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
            </div>
          </details>
        </section>
      )}

      <PostTradeReviewPage
        onLearningStateChanged={refreshLearningState}
        externalRefreshVersion={refreshVersion}
        showMaterializationAction={false}
      />

      {tradeId && (
        <TradeJournalPanel key={tradeId} tradeId={tradeId} refreshVersion={refreshVersion} />
      )}

      {tradeId && (
        <Ft011EvidenceHistory
          key={`evidence:${tradeId}`}
          tradeId={tradeId}
          refreshVersion={refreshVersion}
        />
      )}

      {materializationError && (
        <div role="alert" className="mt-3 text-sm text-red-300">
          <p>{materializationError}</p>
          <button
            type="button"
            className="mt-2 underline"
            disabled={materializing}
            onClick={() => {
              setMaterializationError(null);
              refreshLearningState();
            }}
          >
            Übergabestatus erneut laden
          </button>
        </div>
      )}

      {status?.ready && !status.materialized && (
        <section className="mt-6 rounded-xl border border-amber-800 bg-amber-950/20 p-5">
          <h2 className="text-lg font-semibold">Lessons Learned</h2>
          <p className="mt-2 text-sm text-slate-300">
            Das Exit Review ist finalisiert. Übergib es bewusst als unveränderliche Evidence an
            FT-012, bevor du daraus eine Lesson ableitest.
          </p>
          <button
            type="button"
            className="mt-4 rounded-lg bg-amber-500 px-4 py-2 text-sm font-medium text-slate-950 disabled:opacity-50"
            disabled={materializing || !status.exit_review_version_id}
            onClick={() => void handleMaterialize()}
          >
            {materializing ? 'Wird übergeben…' : 'An Lessons Learned übergeben'}
          </button>
          <p className="mt-3 break-all text-xs text-slate-400">
            ExitReviewVersion: {status.exit_review_version_id ?? 'Nicht verfügbar'}
          </p>
        </section>
      )}

      {status?.materialized && learningEvidenceId && (
        <section className="mt-6 rounded-xl border border-slate-800 p-5">
          <h2 className="text-lg font-semibold">FT-012 Learning</h2>
          <p className="mt-2 text-sm text-slate-400">
            Die materialisierte Evidence kann jetzt bewusst interpretiert werden. Es findet keine
            automatische Lesson- oder FT-013-Erzeugung statt.
          </p>

          {lessonSourceId === learningEvidenceId && lessonReadbackError ? (
            <div role="alert" className="mt-4 text-sm text-red-300">
              <p>{lessonReadbackError}</p>
              <button type="button" onClick={refreshLessonReferences} className="mt-2 underline">
                Lesson-Verweise erneut laden
              </button>
            </div>
          ) : lessonSourceId !== learningEvidenceId || lessonReferences === null ? (
            <p role="status" className="mt-4 text-sm text-slate-400">
              Lesson-Verweise werden geladen …
            </p>
          ) : lessonReferences.length > 0 ? (
            <div className="mt-5 rounded-lg border border-emerald-800 p-4">
              <p className="font-medium text-emerald-300">Bereits interpretiert</p>
              <p className="mt-1 text-sm text-slate-400">
                Diese Evidence wird bereits von {lessonReferences.length} Lesson
                {lessonReferences.length === 1 ? '' : 's'} referenziert.
              </p>
              <ul className="mt-3 space-y-2 text-sm">
                {lessonReferences.map((lesson) => (
                  <li key={lesson.lesson_id}>
                    <Link
                      to={`/lessons/${lesson.lesson_id}`}
                      className="text-emerald-300 underline"
                    >
                      {lesson.title} · {lesson.current_state}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <LessonDraftFromEvidence
              learningEvidenceId={learningEvidenceId}
              onCreated={refreshLessonReferences}
            />
          )}
        </section>
      )}
    </div>
  );
}
