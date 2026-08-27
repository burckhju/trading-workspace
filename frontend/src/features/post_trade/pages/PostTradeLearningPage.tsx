import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { LessonDraftFromEvidence } from '../../learning/components/LessonDraftFromEvidence';
import { ft011MaterializationClient } from '../../learning/services/materializationClient';
import type { Ft011MaterializationStatus } from '../../learning/types/materialization';
import { PostTradeReviewPage } from './PostTradeReviewPage';

export function PostTradeLearningPage() {
  const [searchParams] = useSearchParams();
  const tradeId = searchParams.get('trade_id') ?? '';
  const [status, setStatus] = useState<Ft011MaterializationStatus | null>(null);

  useEffect(() => {
    if (!tradeId) {
      setStatus(null);
      return undefined;
    }

    const controller = new AbortController();
    ft011MaterializationClient
      .status(tradeId, controller.signal)
      .then(setStatus)
      .catch(() => {
        if (!controller.signal.aborted) setStatus(null);
      });

    return () => controller.abort();
  }, [tradeId]);

  return (
    <>
      <PostTradeReviewPage />

      {status?.materialized && status.learning_evidence_id && (
        <section className="mt-6 rounded-xl border border-slate-800 p-5">
          <h2 className="text-lg font-semibold">FT-012 Learning</h2>
          <p className="mt-2 text-sm text-slate-400">
            Die materialisierte Evidence kann jetzt bewusst interpretiert werden. Es findet keine
            automatische Lesson- oder FT-013-Erzeugung statt.
          </p>
          <LessonDraftFromEvidence learningEvidenceId={status.learning_evidence_id} />
        </section>
      )}
    </>
  );
}
