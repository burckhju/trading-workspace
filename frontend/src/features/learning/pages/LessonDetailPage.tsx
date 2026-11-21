import { useCallback, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';

import { PendingNavigationGuard } from '../../../components/PendingNavigationGuard';
import { lessonTradeReturnLink } from '../../../shared/trade-workspace-navigation';
import {
  LessonHypothesisPanel,
  type LessonHypothesisNavigationState,
} from '../../model/components/LessonHypothesisPanel';
import {
  LessonReviewPanel,
  type LessonReviewNavigationState,
} from '../components/LessonReviewPanel';
import { lessonListReturnLink } from '../services/lessonNavigation';

export function LessonDetailPage() {
  const { lessonId = '' } = useParams();
  const [params] = useSearchParams();
  const versions = params.getAll('lesson_version_id');
  if (versions.length > 1 || (versions.length === 1 && !versions[0].trim())) {
    return (
      <section role="alert" className="space-y-3 rounded-xl border border-amber-700 p-5">
        <h1 className="text-xl font-semibold">Erkenntnisversion nicht eindeutig</h1>
        <p>
          Der Versionsverweis ist leer oder mehrfach angegeben. Öffnen Sie den ursprünglichen
          Quellenlink mit genau einer Version.
        </p>
        <Link to="/lessons" className="text-sky-300 underline">
          Zur Erkenntnisliste
        </Link>
      </section>
    );
  }
  return <LessonDetail key={lessonId} lessonId={lessonId} />;
}

function LessonDetail({ lessonId }: { lessonId: string }) {
  const [params] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const versionId = params.get('lesson_version_id') ?? undefined;
  const tradeReturnLink = lessonTradeReturnLink(params);
  const listReturnLink = lessonListReturnLink(params);
  const visibleArea = location.hash === '#model-improvement' ? 'model' : 'lesson';
  const navigation = useRef({
    review: { dirty: false, busy: false },
    hypothesis: { dirty: false, busy: false },
  });
  const [reviewBusy, setReviewBusy] = useState(false);
  const [hypothesisBusy, setHypothesisBusy] = useState(false);
  const onReviewNavigation = useCallback((state: LessonReviewNavigationState) => {
    navigation.current.review = state;
    setReviewBusy(state.busy);
  }, []);
  const onHypothesisNavigation = useCallback((state: LessonHypothesisNavigationState) => {
    navigation.current.hypothesis = state;
    setHypothesisBusy(state.busy);
  }, []);
  const shouldBlock = useCallback(() => {
    const { review, hypothesis } = navigation.current;
    return review.dirty || review.busy || hypothesis.dirty || hypothesis.busy;
  }, []);
  const hypothesisPending = useCallback(() => navigation.current.hypothesis.busy, []);

  return (
    <section className="min-w-0 space-y-6">
      <PendingNavigationGuard shouldBlock={shouldBlock} busy={reviewBusy || hypothesisBusy} />
      <nav aria-label="Erkenntnis-Arbeitsbereiche" className="flex flex-wrap gap-2">
        {(
          [
            ['lesson', '#lesson-history', 'Erkenntnis & Quellen'],
            ['model', '#model-improvement', 'Modellverbesserung'],
          ] as const
        ).map(([area, hash, label]) => (
          <Link
            key={area}
            to={`${location.pathname}${location.search}${hash}`}
            aria-current={visibleArea === area ? 'location' : undefined}
            className={`inline-flex min-h-11 items-center rounded-lg border px-4 py-2 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-300 ${visibleArea === area ? 'border-sky-500 bg-sky-950 text-sky-100' : 'border-slate-700 text-slate-300 hover:border-sky-600'}`}
          >
            {label}
          </Link>
        ))}
      </nav>
      <LessonReviewPanel
        lessonId={lessonId}
        versionId={versionId}
        visibleArea={visibleArea}
        versionHref={(id) => {
          const next = new URLSearchParams(params);
          next.set('lesson_version_id', id);
          return `${location.pathname}?${next}#lesson-history`;
        }}
        onNavigationStateChange={onReviewNavigation}
        actionsDisabled={hypothesisBusy}
        isActionsDisabled={hypothesisPending}
        onSelectVersion={(id) => {
          const next = new URLSearchParams(params);
          next.set('lesson_version_id', id);
          void navigate({
            pathname: location.pathname,
            search: next.toString(),
            hash: '#lesson-history',
          });
        }}
        renderVersionActions={(snapshot, state) => (
          <div key={snapshot.version.id} className="min-w-0 space-y-3">
            <h2 className="text-xl font-semibold">Modellverbesserung</h2>
            <p className="text-sm text-slate-400">
              Ausgangspunkt: Erkenntnisversion {snapshot.version.version}. Hypothesen und
              Änderungsvorschläge behalten diese konkrete Quelle.
            </p>
            <details className="text-xs text-slate-500">
              <summary>Quellenbeleg</summary>
              <p className="mt-2 break-all">
                Governance-Quelle: Lesson-Version {snapshot.version.version} · {snapshot.version.id}
              </p>
            </details>
            <LessonHypothesisPanel
              lessonVersionId={snapshot.version.id}
              actionsDisabled={state.actionsDisabled}
              isActionsDisabled={state.isActionsDisabled}
              onNavigationStateChange={onHypothesisNavigation}
            />
          </div>
        )}
      />
      <Link
        to={tradeReturnLink ?? listReturnLink ?? '/lessons'}
        className="inline-block text-sm text-emerald-300 underline"
      >
        {tradeReturnLink
          ? 'Zurück zum Trade-Arbeitsbereich'
          : listReturnLink?.startsWith('/model-improvements')
            ? 'Zurück zur Modellverbesserung'
            : 'Zurück zur Erkenntnisliste'}
      </Link>
    </section>
  );
}
