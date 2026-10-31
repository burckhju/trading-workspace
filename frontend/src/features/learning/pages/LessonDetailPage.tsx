import { useCallback, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';

import { PendingNavigationGuard } from '../../../components/PendingNavigationGuard';
import { lessonTradeReturnLink } from '../../trade/services/workspaceNavigation';
import {
  LessonHypothesisPanel,
  type LessonHypothesisNavigationState,
} from '../../model/components/LessonHypothesisPanel';
import {
  LessonReviewPanel,
  type LessonReviewNavigationState,
} from '../components/LessonReviewPanel';

export function LessonDetailPage() {
  const { lessonId = '' } = useParams();
  return <LessonDetail key={lessonId} lessonId={lessonId} />;
}

function LessonDetail({ lessonId }: { lessonId: string }) {
  const [params] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const versionId = params.get('lesson_version_id') ?? undefined;
  const tradeReturnLink = lessonTradeReturnLink(params);
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
    <main className="min-w-0 space-y-6">
      <PendingNavigationGuard shouldBlock={shouldBlock} busy={reviewBusy || hypothesisBusy} />
      <LessonReviewPanel
        lessonId={lessonId}
        versionId={versionId}
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
            <p className="break-all text-sm">
              Governance-Quelle: Lesson-Version {snapshot.version.version} · {snapshot.version.id}
            </p>
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
        to={tradeReturnLink ?? '/post-trade'}
        className="inline-block text-sm text-emerald-300 underline"
      >
        {tradeReturnLink ? 'Zurück zum Trade-Arbeitsbereich' : 'Zurück zum Post-Trade Review'}
      </Link>
    </main>
  );
}
