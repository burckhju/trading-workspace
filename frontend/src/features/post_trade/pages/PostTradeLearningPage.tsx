import { Ft011EvidenceHistory } from '../../learning/components/Ft011EvidenceHistory';
import { TradeJournalPanel } from '../../learning/components/TradeJournalPanel';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';

import { PendingNavigationGuard } from '../../../components/PendingNavigationGuard';

import { LessonDraftFromEvidence } from '../../learning/components/LessonDraftFromEvidence';
import { lessonReadbackClient } from '../../learning/services/lessonReadbackClient';
import { ft011MaterializationClient } from '../../learning/services/materializationClient';
import type { LessonEvidenceReference } from '../../learning/types/lessonReadback';
import type { Ft011MaterializationStatus } from '../../learning/types/materialization';
import { warrantApiClient } from '../../product/services/client';
import type { WarrantResponse } from '../../product/types/api';
import { tradeManagementApiClient } from '../../trade/services/client';
import type { TradeResponse } from '../../trade/types/api';
import {
  TradeWorkspaceNavigation,
  tradeLessonLink,
  tradeWorkspaceLink,
} from '../../../shared/trade-workspace-navigation';
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

type NavigationState = { dirty: boolean; pending: boolean };
type NavigationParticipant = 'journal' | 'review' | 'lesson' | 'materialization';

export function PostTradeLearningPage() {
  const [searchParams] = useSearchParams();
  const tradeIds = searchParams.getAll('trade_id');
  const tradeId = tradeIds[0] ?? '';
  const invalidSourceTrade =
    searchParams.has('journal_version_id') && (tradeIds.length !== 1 || !tradeId.trim());
  const states = useRef(new Map<NavigationParticipant, NavigationState>());
  const [busy, setBusy] = useState(false);
  const [discardVersion, setDiscardVersion] = useState(0);
  const report = useCallback((participant: NavigationParticipant, state: NavigationState) => {
    states.current.set(participant, state);
    setBusy([...states.current.values()].some((value) => value.pending));
  }, []);
  const isContextPending = useCallback(
    () => [...states.current.values()].some((value) => value.pending),
    [],
  );
  const shouldBlock = useCallback(
    () => [...states.current.values()].some((value) => value.dirty || value.pending),
    [],
  );
  const discard = useCallback(() => {
    if ([...states.current.values()].some((value) => value.pending)) return;
    states.current.clear();
    setDiscardVersion((version) => version + 1);
  }, []);
  return (
    <>
      <PendingNavigationGuard shouldBlock={shouldBlock} busy={busy} onDiscard={discard} />
      {invalidSourceTrade ? (
        <section role="alert" className="space-y-3 rounded-xl border border-amber-700 p-5">
          <h1 className="text-xl font-semibold">Journalquelle nicht eindeutig</h1>
          <p>
            Die angefragte Journalversion benötigt genau eine nichtleere Trade-ID. Bitte den
            Quellenlink prüfen und mit seinem ursprünglichen Trade öffnen.
          </p>
        </section>
      ) : (
        <PostTradeLearningContent
          key={tradeId}
          tradeId={tradeId}
          report={report}
          discardVersion={discardVersion}
          isContextPending={isContextPending}
        />
      )}
    </>
  );
}

function PostTradeLearningContent({
  tradeId,
  report,
  discardVersion,
  isContextPending,
}: {
  tradeId: string;
  report: (participant: NavigationParticipant, state: NavigationState) => void;
  discardVersion: number;
  isContextPending: () => boolean;
}) {
  const [query] = useSearchParams();
  const location = useLocation();
  // Hash navigation changes presentation only. All three owners stay mounted,
  // with the exact search string (including historical pins) untouched.
  const area =
    location.hash === '#trade-journal'
      ? 'journal'
      : location.hash === '#trade-lessons'
        ? 'lessons'
        : ['#post-trade-review', '#trade-review'].includes(location.hash)
          ? 'review'
          : query.has('journal_version_id') || query.get('tab') === 'reflection'
            ? 'journal'
            : 'review';
  const [trade, setTrade] = useState<TradeResponse | null>(null);
  const [warrant, setWarrant] = useState<WarrantResponse | null>(null);
  const [status, setStatus] = useState<Ft011MaterializationStatus | null>(null);
  const [statusValid, setStatusValid] = useState(false);
  const [completedRefreshVersion, setCompletedRefreshVersion] = useState<number | null>(null);
  const [lessonFormSourceId, setLessonFormSourceId] = useState<string | null>(null);
  const createdLessonSourceId = useRef<string | null>(null);
  const directLessonState = useRef<NavigationState>({ dirty: false, pending: false });
  const lessonResolution = useRef<{
    sourceId: string | null;
    references: LessonEvidenceReference[] | null;
  }>({ sourceId: null, references: null });
  const reportJournal = useCallback((state: NavigationState) => report('journal', state), [report]);
  const reportReview = useCallback((state: NavigationState) => report('review', state), [report]);
  const reportLesson = useCallback(
    (state: NavigationState) => {
      directLessonState.current = state;
      report('lesson', state);
      const resolved = lessonResolution.current;
      if (!state.dirty && !state.pending && resolved.references !== null) {
        setLessonFormSourceId(
          resolved.references.length === 0 || createdLessonSourceId.current === resolved.sourceId
            ? resolved.sourceId
            : null,
        );
      }
    },
    [report],
  );
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
      report('materialization', { dirty: false, pending: false });
    };
  }, [report]);

  const learningEvidenceId = status?.materialized ? status.learning_evidence_id : null;
  lessonResolution.current = {
    sourceId: learningEvidenceId,
    references:
      statusValid &&
      completedRefreshVersion === refreshVersion &&
      lessonSourceId === learningEvidenceId &&
      !lessonReadbackError
        ? lessonReferences
        : null,
  };

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
    setStatusValid(false);
    if (!tradeId) return undefined;

    const controller = new AbortController();
    ft011MaterializationClient
      .status(tradeId, controller.signal)
      .then((nextStatus) => {
        if (!controller.signal.aborted) {
          setStatus(nextStatus);
          setStatusValid(true);
          setCompletedRefreshVersion(refreshVersion);
        }
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
    if (createdLessonSourceId.current !== learningEvidenceId) createdLessonSourceId.current = null;
    if (!learningEvidenceId) return undefined;

    const controller = new AbortController();
    lessonReadbackClient
      .listForEvidence(learningEvidenceId, controller.signal)
      .then((references) => {
        if (!controller.signal.aborted) {
          setLessonReferences(references);
          if (!directLessonState.current.dirty && !directLessonState.current.pending) {
            // Keep the confirmed creation result available while its references refresh.
            setLessonFormSourceId(
              references.length === 0 || createdLessonSourceId.current === learningEvidenceId
                ? learningEvidenceId
                : null,
            );
          }
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setLessonReadbackError('Lesson-Verweise konnten nicht geladen werden.');
        }
      });

    return () => controller.abort();
  }, [learningEvidenceId, lessonRefreshVersion, refreshVersion]);

  const handleMaterialize = useCallback(async () => {
    if (
      !tradeId ||
      !status?.ready ||
      status.materialized ||
      !status.exit_review_version_id ||
      mutationPending.current ||
      !statusValid ||
      completedRefreshVersion !== refreshVersion
    ) {
      return;
    }

    mutationPending.current = true;
    report('materialization', { dirty: false, pending: true });
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
        setStatusValid(false);
        setMaterializing(false);
        report('materialization', { dirty: false, pending: false });
        refreshLearningState();
      }
    }
  }, [
    completedRefreshVersion,
    refreshLearningState,
    refreshVersion,
    report,
    status,
    statusValid,
    tradeId,
  ]);

  return (
    <div className="min-w-0 w-full space-y-6">
      {!trade && (
        <header className="space-y-2">
          <h1 className="text-2xl font-semibold">Trade-Nachbereitung</h1>
          <p className="text-sm text-slate-400">
            Nachbeobachtung, persönliche Reflexion und Erkenntnisse zu einem Trade.
          </p>
        </header>
      )}
      {trade && (
        <TradeWorkspaceNavigation
          tradeId={trade.id}
          view="journal"
          cancelled={Boolean(trade.cancelled_at)}
          showObjectLinks={false}
        />
      )}
      {trade && (
        <section className="mb-6 rounded-xl border border-sky-900 bg-sky-950/20 p-5">
          <p className="text-xs uppercase tracking-wide text-sky-400">
            Lessons Learned · Trade-Nachbereitung
          </p>
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
                {trade.origin === 'WORKSPACE_SELECTION' ? 'Produktauswahl im Workspace' : 'Extern'}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Tradeplan</dt>
              <dd className="mt-1 font-medium">
                {trade.trade_plan_id ? tradePlanReference(trade.trade_plan_id) : 'Kein Tradeplan'}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Quelle für Erkenntnisse</dt>
              <dd className="mt-1 font-medium">
                {materializationError
                  ? 'Quellenstand nicht verfügbar'
                  : status === null || !statusValid || completedRefreshVersion !== refreshVersion
                    ? 'Übergabestatus wird geprüft'
                    : status.materialized
                      ? 'Reviewquelle übernommen'
                      : status.ready
                        ? 'Aktueller Reviewstand noch nicht übergeben'
                        : 'Neue Übergabe derzeit nicht bereit'}
              </dd>
              {materializationError && area !== 'lessons' && (
                <dd className="mt-1">
                  <Link
                    className="text-amber-200 underline"
                    to={`${location.pathname}${location.search}#trade-lessons`}
                  >
                    Quellenproblem prüfen
                  </Link>
                </dd>
              )}
            </div>
          </dl>
          <details className="mt-4 text-xs text-slate-500">
            <summary className="cursor-pointer">Technische Herkunft anzeigen</summary>
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

      {tradeId && (
        <nav aria-label="Nachbereitung dieses Trades" className="flex flex-wrap gap-2">
          {(
            [
              ['review', '#post-trade-review', 'Nachbeobachtung & Exit Review'],
              ['journal', '#trade-journal', 'Journal'],
              ['lessons', '#trade-lessons', 'Erkenntnisse'],
            ] as const
          ).map(([value, hash, label]) => (
            <Link
              key={value}
              to={`${location.pathname}${location.search}${hash}`}
              aria-current={area === value ? 'location' : undefined}
              className={`inline-flex min-h-11 items-center rounded-lg border px-4 py-2 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-300 ${area === value ? 'border-sky-500 bg-sky-950 text-sky-100' : 'border-slate-700 text-slate-300 hover:border-sky-600'}`}
            >
              {label}
            </Link>
          ))}
        </nav>
      )}

      <section
        id="post-trade-review"
        tabIndex={-1}
        hidden={Boolean(tradeId) && area !== 'review'}
        className="space-y-5"
      >
        {tradeId && query.has('review_version_id') && (
          <p className="text-sm text-slate-400">
            Hier wird der aktuelle Exit Review bearbeitet. Die verlinkte historische Reviewversion
            ist in der Quellenansicht verfügbar.{' '}
            <Link
              className="text-sky-400 underline"
              to={tradeWorkspaceLink('sources', tradeId, query, '#trade-review-sources')}
            >
              Historische Reviewquelle öffnen
            </Link>
          </p>
        )}

        <PostTradeReviewPage
          onLearningStateChanged={refreshLearningState}
          externalRefreshVersion={refreshVersion}
          showMaterializationAction={false}
          onNavigationStateChange={reportReview}
          isContextPending={isContextPending}
          discardVersion={discardVersion}
        />
      </section>

      {tradeId && (
        <section
          id="trade-journal"
          tabIndex={-1}
          aria-label="Persönliche Reflexion"
          hidden={area !== 'journal'}
          className="space-y-6"
        >
          <TradeJournalPanel
            key={tradeId}
            tradeId={tradeId}
            refreshVersion={refreshVersion}
            onNavigationStateChange={reportJournal}
            isContextPending={isContextPending}
            discardVersion={discardVersion}
          />
        </section>
      )}

      <section
        id="trade-lessons"
        tabIndex={-1}
        hidden={!tradeId || area !== 'lessons'}
        className="space-y-6"
        aria-label="Erkenntnisse zu diesem Trade"
      >
        <header className="space-y-2">
          <h2 className="text-xl font-semibold">Erkenntnisse zu diesem Trade</h2>
          <p className="text-sm text-slate-400">
            Leiten Sie aus einer freigegebenen Reviewquelle eine eigenständige Erkenntnis ab.
            Reflexionen zu einer Journalversion bleiben im Journal verknüpft.
          </p>
          <Link className="text-sm text-sky-300 underline" to="/lessons">
            Alle Erkenntnisse ansehen
          </Link>
        </header>
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
            <h3 className="text-lg font-semibold">Reviewquelle übernehmen</h3>
            <p className="mt-2 text-sm text-slate-300">
              Der Exit Review ist finalisiert. Übernehmen Sie diesen festen Quellenstand, bevor Sie
              daraus eine Erkenntnis ableiten.
            </p>
            <button
              type="button"
              className="mt-4 rounded-lg bg-amber-500 px-4 py-2 text-sm font-medium text-slate-950 disabled:opacity-50"
              disabled={
                materializing ||
                !statusValid ||
                completedRefreshVersion !== refreshVersion ||
                !status.exit_review_version_id
              }
              onClick={() => void handleMaterialize()}
            >
              {materializing ? 'Wird übergeben…' : 'An Lessons Learned übergeben'}
            </button>
            <details className="mt-3 break-all text-xs text-slate-400">
              <summary>Quellenbeleg</summary>
              <p>ExitReviewVersion: {status.exit_review_version_id ?? 'Nicht verfügbar'}</p>
            </details>
          </section>
        )}

        {(learningEvidenceId || lessonFormSourceId) && (
          <section className="mt-6 rounded-xl border border-slate-800 p-5">
            <h3 className="text-lg font-semibold">Erkenntnis aus der Reviewquelle</h3>
            <p className="mt-2 text-sm text-slate-400">
              Interpretieren Sie die übernommene Quelle oder öffnen Sie die bereits daraus
              abgeleiteten Erkenntnisse.
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
                        to={tradeLessonLink(
                          lesson.lesson_id,
                          lesson.current_version_id,
                          tradeId,
                          query,
                        )}
                        className="text-emerald-300 underline"
                      >
                        {lesson.title} · {lesson.current_state}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            {!learningEvidenceId && lessonFormSourceId && (
              <p role="status" className="mt-3 text-sm text-amber-200">
                Die Eingaben bleiben an der bisherigen Evidence {lessonFormSourceId} gebunden. Die
                aktuelle Übergabe ist noch nicht als Lessonquelle bestätigt.
              </p>
            )}
            {lessonFormSourceId && (
              <LessonDraftFromEvidence
                lessonHref={(id) => tradeLessonLink(id, null, tradeId, query)}
                learningEvidenceId={learningEvidenceId ?? lessonFormSourceId}
                disabled={
                  !statusValid ||
                  completedRefreshVersion !== refreshVersion ||
                  !learningEvidenceId ||
                  lessonSourceId !== learningEvidenceId ||
                  lessonReferences === null ||
                  lessonReadbackError !== null
                }
                onNavigationStateChange={reportLesson}
                isContextPending={isContextPending}
                discardVersion={discardVersion}
                onCreated={() => {
                  createdLessonSourceId.current = lessonFormSourceId;
                  refreshLessonReferences();
                }}
              />
            )}
          </section>
        )}
      </section>
    </div>
  );
}
