import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { ErrorNotice, LoadingNotice } from '../../market/components/ApiFeedback';
import { lessonReadbackClient } from '../services/lessonReadbackClient';
import type { LessonDetail } from '../types/lessonReadback';

export function LessonDetailPage() {
  const { lessonId = '' } = useParams();
  const [lesson, setLesson] = useState<LessonDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    lessonReadbackClient
      .getLesson(lessonId, controller.signal)
      .then(setLesson)
      .catch((nextError: unknown) => {
        if (!controller.signal.aborted) setError(nextError);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [lessonId]);

  if (loading) return <LoadingNotice label="Lesson wird geladen …" />;
  if (error !== null) return <ErrorNotice error={error} />;
  if (!lesson) return null;

  return (
    <main className="space-y-6">
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
        <h2 className="mt-5 font-semibold">Inhalt</h2>
        <p className="mt-2 whitespace-pre-wrap text-sm text-slate-300">{lesson.content}</p>
      </section>

      <section className="rounded-xl border border-slate-800 p-5">
        <h2 className="font-semibold">Evidence</h2>
        <ul className="mt-3 space-y-2 text-sm">
          {lesson.evidence.map((item) => (
            <li key={item.id} className="rounded-lg border border-slate-800 p-3">
              <span className="font-medium">{item.relation}</span>
              <span className="ml-2 break-all text-slate-400">{item.learning_evidence_id}</span>
            </li>
          ))}
        </ul>
      </section>

      <Link to="/post-trade" className="inline-block text-sm text-emerald-300 underline">
        Zurück zum Post-Trade Review
      </Link>
    </main>
  );
}
