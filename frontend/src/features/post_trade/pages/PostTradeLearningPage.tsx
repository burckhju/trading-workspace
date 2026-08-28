import { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { LessonDraftFromEvidence } from '../../learning/components/LessonDraftFromEvidence';
import { lessonReadbackClient } from '../../learning/services/lessonReadbackClient';
import { ft011MaterializationClient } from '../../learning/services/materializationClient';
import type { LessonEvidenceReference } from '../../learning/types/lessonReadback';
import type { Ft011MaterializationStatus } from '../../learning/types/materialization';
import { PostTradeReviewPage } from './PostTradeReviewPage';

export function PostTradeLearningPage() {
  const [searchParams] = useSearchParams();
  const tradeId = searchParams.get('trade_id') ?? '';
  const [status, setStatus] = useState<Ft011MaterializationStatus | null>(null);
  const [lessonReferences, setLessonReferences] = useState<LessonEvidenceReference[]>([]);

  const refreshLessonReferences = useCallback(async (learningEvidenceId: string) => {
    const references = await lessonReadbackClient.listForEvidence(learningEvidenceId);
    setLessonReferences(references);
  }, []);

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

  const learningEvidenceId = status?.learning_evidence_id ?? null;

  return (
    <>
      <PostTradeReviewPage />

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
                    <Link to={`/lessons/${lesson.lesson_id}`} className="text-emerald-300 underline">
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
