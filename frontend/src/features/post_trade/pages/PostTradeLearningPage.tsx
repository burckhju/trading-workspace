import { useCallback, useEffect, useState } from 'react';
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
import { PostTradeReviewPage } from './PostTradeReviewPage';

function tradeReference(id: string): string {
  return `TR-${id.slice(0, 8).toUpperCase()}`;
}

function tradePlanReference(id: string): string {
  return `TP-${id.slice(0, 8).toUpperCase()}`;
}

function materializationKey(tradeId: string, exitReviewVersionId: string | null): string {
  return `ft011-to-ft012:${tradeId}:${exitReviewVersionId ?? 'current'}`;
}

export function PostTradeLearningPage() {
  const [searchParams] = useSearchParams();
  const tradeId = searchParams.get('trade_id') ?? '';
  const [trade, setTrade] = useState<TradeResponse | null>(null);
  const [warrant, setWarrant] = useState<WarrantResponse | null>(null);
  const [status, setStatus] = useState<Ft011MaterializationStatus | null>(null);
  const [lessonReferences, setLessonReferences] = useState<LessonEvidenceReference[]>([]);
  const [materializing, setMaterializing] = useState(false);
  const [materializationError, setMaterializationError] = useState<string | null>(null);

  const refreshLessonReferences = useCallback(async (learningEvidenceId: string) => {
    const references = await lessonReadbackClient.listForEvidence(learningEvidenceId);
    setLessonReferences(references);
  }, []);

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
    if (!tradeId) {
      setStatus(null);
      setLessonReferences([]);
      return undefined;
    }

    const controller = new AbortController();
    ft011MaterializationClient
      .status(tradeId, controller.signal)
      .then(async (nextStatus) => {
        setStatus(nextStatus);
        if (nextStatus.materialized && nextStatus.learning_evidence_id) {
          const references = await lessonReadbackClient.listForEvidence(
            nextStatus.learning_evidence_id,
            controller.signal,
          );
          if (!controller.signal.aborted) setLessonReferences(references);
        } else {
          setLessonReferences([]);
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setStatus(null);
          setLessonReferences([]);
        }
      });

    return () => controller.abort();
  }, [tradeId]);

  const handleMaterialize = useCallback(async () => {
    if (!tradeId || !status?.ready || status.materialized) return;

    setMaterializing(true);
    setMaterializationError(null);
    try {
      const result = await ft011MaterializationClient.materialize(
        tradeId,
        materializationKey(tradeId, status.exit_review_version_id),
      );
      setStatus({
        ...status,
        materialized: true,
        learning_evidence_id: result.learning_evidence_id,
        exit_review_version_id: result.exit_review_version_id,
      });
      setLessonReferences([]);
    } catch (error) {
      setMaterializationError(
        error instanceof Error ? error.message : 'Übergabe an Lessons Learned fehlgeschlagen.',
      );
    } finally {
      setMaterializing(false);
    }
  }, [status, tradeId]);

  const learningEvidenceId = status?.learning_evidence_id ?? null;

  return (
    <>
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
                {status?.materialized
                  ? 'LearningEvidence materialisiert'
                  : 'Noch im Post-Trade-Prozess'}
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

      <PostTradeReviewPage />

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
            disabled={materializing}
            onClick={() => void handleMaterialize()}
          >
            {materializing ? 'Wird übergeben…' : 'An Lessons Learned übergeben'}
          </button>
          {materializationError && (
            <p role="alert" className="mt-3 text-sm text-red-300">
              {materializationError}
            </p>
          )}
        </section>
      )}

      {status?.materialized && learningEvidenceId && (
        <section className="mt-6 rounded-xl border border-slate-800 p-5">
          <h2 className="text-lg font-semibold">FT-012 Learning</h2>
          <p className="mt-2 text-sm text-slate-400">
            Die materialisierte Evidence kann jetzt bewusst interpretiert werden. Es findet keine
            automatische Lesson- oder FT-013-Erzeugung statt.
          </p>

          {lessonReferences.length > 0 ? (
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
              onCreated={() => void refreshLessonReferences(learningEvidenceId)}
            />
          )}
        </section>
      )}
    </>
  );
}
