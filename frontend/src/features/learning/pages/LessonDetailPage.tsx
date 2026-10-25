import { useCallback, useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';

import { ErrorNotice, LoadingNotice } from '../../market/components/ApiFeedback';
import { LessonHypothesisPanel } from '../../model/components/LessonHypothesisPanel';
import { LessonReviewPanel } from '../components/LessonReviewPanel';
import { JournalEvidenceOrigin } from '../components/JournalEvidenceOrigin';
import { lessonReadbackClient } from '../services/lessonReadbackClient';
import type { LessonDetail } from '../types/lessonReadback';

export function LessonDetailPage() {
  const { lessonId = '' } = useParams();
  const [params] = useSearchParams();
  const versionId = params.get('lesson_version_id') ?? undefined;
  return (
    <LessonDetail
      key={`${lessonId}:${versionId ?? ''}`}
      lessonId={lessonId}
      versionId={versionId}
    />
  );
}

function LessonDetail({ lessonId, versionId }: { lessonId: string; versionId?: string }) {
  const [refresh, setRefresh] = useState(0);
  const onChanged = useCallback(() => setRefresh((n) => n + 1), []);
  const [lesson, setLesson] = useState<LessonDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    const controller = new AbortController();
    if (refresh === 0) setLoading(true);
    setError(null);

    lessonReadbackClient
      .getLesson(lessonId, controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) setLesson(value);
      })
      .catch((nextError: unknown) => {
        if (!controller.signal.aborted) setError(nextError);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [lessonId, refresh]);

  if (loading) return <LoadingNotice label="Lesson wird geladen …" />;
  if (error !== null && !lesson)
    return (
      <>
        <ErrorNotice error={error} />
        <button onClick={onChanged}>Lesson erneut laden</button>
      </>
    );
  if (!lesson) return null;

  return (
    <main className="space-y-6">
      {error !== null && (
        <>
          <ErrorNotice error={error} />
          <p>Aktueller Lesson-Lesestand nicht aktualisiert.</p>
          <button onClick={onChanged}>Lesson erneut laden</button>
        </>
      )}
      <header>
        <p className="text-xs uppercase tracking-wide text-slate-500">FT-012 Lesson</p>
        <h1 className="mt-1 text-2xl font-semibold">{lesson.title}</h1>
        <p className="mt-2 text-sm text-slate-400">
          Version {lesson.version} · {lesson.current_state}
        </p>
      </header>

      <section className="rounded-xl border border-slate-800 p-5">
        <dl className="grid gap-4 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-slate-500">Kategorie</dt>
            <dd className="mt-1 font-medium">{lesson.main_category}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Current Version</dt>
            <dd className="mt-1 break-all font-medium">{lesson.current_version_id}</dd>
          </div>
        </dl>
        <h2 className="mt-5 font-semibold">Inhalt des aktuellen Lesson-Stands</h2>
        <p className="mt-2 whitespace-pre-wrap text-sm text-slate-300">{lesson.content}</p>
      </section>

      <section className="rounded-xl border border-slate-800 p-5">
        <h2 className="font-semibold">Evidence</h2>
        <ul className="mt-3 space-y-2 text-sm">
          {lesson.evidence.map((item) => (
            <li key={item.id} className="rounded-lg border border-slate-800 p-3">
              <span className="font-medium">{item.relation}</span>
              <span className="ml-2 break-all text-slate-400">{item.learning_evidence_id}</span>
              <JournalEvidenceOrigin
                key={`${item.learning_evidence_id}:${refresh}`}
                evidenceId={item.learning_evidence_id}
              />
            </li>
          ))}
        </ul>
      </section>

      <LessonReviewPanel
        lessonId={lessonId}
        initialVersionId={versionId}
        onChanged={onChanged}
        renderVersionActions={(snapshot) => (
          <div key={snapshot.version.id} className="min-w-0 space-y-3">
            <p className="break-all text-sm">
              Governance-Quelle: Lesson-Version {snapshot.version.version} · {snapshot.version.id}
            </p>
            <Link
              to={`/lessons/${lessonId}?lesson_version_id=${snapshot.version.id}#lesson-history`}
              className="text-sm text-emerald-300 underline"
            >
              Genau diese Lesson-Version öffnen
            </Link>
            <LessonHypothesisPanel lessonVersionId={snapshot.version.id} />
          </div>
        )}
      />

      <Link to="/post-trade" className="inline-block text-sm text-emerald-300 underline">
        Zurück zum Post-Trade Review
      </Link>
    </main>
  );
}
